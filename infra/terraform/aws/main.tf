# VPC
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.15"

  name = "contextclaw-${var.environment}"
  cidr = var.vpc_cidr

  azs             = var.availability_zones
  private_subnets = var.private_subnet_cidrs
  public_subnets  = var.public_subnet_cidrs
  database_subnets = var.data_subnet_cidrs

  enable_nat_gateway   = true
  enable_vpn_gateway   = false
  single_nat_gateway   = var.environment != "prod"
  enable_dns_hostnames = true

  public_subnet_tags = {
    "kubernetes.io/role/elb" = "1"
  }
  private_subnet_tags = {
    "kubernetes.io/role/internal-elb" = "1"
    "karpenter.sh/discovery"          = "contextclaw-${var.environment}"
  }
  database_subnet_tags = {
    "kubernetes.io/role/internal-elb" = "1"
  }
}

# EKS Cluster
module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 20.31"

  cluster_name    = "contextclaw-${var.environment}"
  cluster_version = var.eks_cluster_version

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets

  cluster_endpoint_public_access = var.environment != "prod"

  enable_cluster_creator_admin_permissions = true

  eks_managed_node_groups = {
    api = {
      instance_types = var.api_node_instance_types
      min_size       = var.environment == "prod" ? 3 : 2
      max_size       = 10
      desired_size   = var.environment == "prod" ? 3 : 2
      subnet_ids     = module.vpc.private_subnets
    }
    workers = {
      instance_types = var.worker_node_instance_types
      min_size       = var.environment == "prod" ? 2 : 1
      max_size       = 20
      desired_size   = var.environment == "prod" ? 2 : 1
      subnet_ids     = module.vpc.private_subnets
      taints = {
        worker = {
          key    = "role"
          value  = "worker"
          effect = "NO_SCHEDULE"
        }
      }
    }
  }

  tags = {
    "karpenter.sh/discovery" = "contextclaw-${var.environment}"
  }
}

# RDS Aurora PostgreSQL
module "aurora" {
  source  = "terraform-aws-modules/rds-aurora/aws"
  version = "~> 2.43"

  name = "contextclaw-${var.environment}"

  engine         = "aurora-postgresql"
  engine_version = "16.4"
  instances = {
    writer = {
      instance_class = "db.r6g.large"
    }
    reader = var.environment == "prod" ? {
      instance_class = "db.r6g.large"
    } : {}
  }

  vpc_id                = module.vpc.vpc_id
  subnets               = module.vpc.database_subnets
  create_db_subnet_group = true
  db_subnet_group_name  = "contextclaw-${var.environment}"

  allowed_security_groups = [module.eks.cluster_security_group_id]

  storage_encrypted   = true
  deletion_protection = var.environment == "prod"
  skip_final_snapshot = var.environment != "prod"

  db_parameter_group_name         = "contextclaw-${var.environment}"
  db_cluster_parameter_group_name = "contextclaw-${var.environment}-cluster"
}

# ElastiCache Redis
module "elasticache_redis" {
  source  = "terraform-aws-modules/elasticache/aws"
  version = "~> 1.4"

  cluster_id = "contextclaw-${var.environment}"

  engine_version = "7.1"

  node_type = "cache.r6g.large"
  num_cache_nodes = var.environment == "prod" ? 3 : 1

  subnet_ids = module.vpc.private_subnets
  vpc_id     = module.vpc.vpc_id

  security_group_ids = [module.eks.cluster_security_group_id]

  parameters = [
    { name = "reserved-memory-percent", value = "25" }
  ]

  tags = {
    Environment = var.environment
  }
}

# S3 Buckets
resource "aws_s3_bucket" "raw_documents" {
  bucket = "contextclaw-${var.environment}-raw-documents"
  force_destroy = var.environment != "prod"
}

resource "aws_s3_bucket_versioning" "raw_documents" {
  bucket = aws_s3_bucket.raw_documents.id
  versioning_configuration {
    status = var.environment == "prod" ? "Enabled" : "Suspended"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "raw_documents" {
  bucket = aws_s3_bucket.raw_documents.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "raw_documents" {
  bucket = aws_s3_bucket.raw_documents.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket" "exports" {
  bucket = "contextclaw-${var.environment}-exports"
  force_destroy = var.environment != "prod"
}

resource "aws_s3_bucket_server_side_encryption_configuration" "exports" {
  bucket = aws_s3_bucket.exports.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket" "audit_logs" {
  bucket = "contextclaw-${var.environment}-audit-logs"
  force_destroy = var.environment != "prod"
  object_lock_enabled = true
}

resource "aws_s3_bucket_versioning" "audit_logs" {
  bucket = aws_s3_bucket.audit_logs.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "audit_logs" {
  bucket = aws_s3_bucket.audit_logs.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Secrets Manager
resource "aws_secretsmanager_secret" "app_secrets" {
  name = "contextclaw-${var.environment}-app"
}

# Route53 (if domain configured)
resource "aws_route53_zone" "main" {
  count = var.domain_name != "" ? 1 : 0
  name  = var.domain_name
}

# Outputs
output "eks_cluster_name" {
  value = module.eks.cluster_name
}

output "aurora_endpoint" {
  value = module.aurora.endpoint
}

output "redis_endpoint" {
  value = module.elasticache_redis.primary_endpoint_address
}

output "raw_documents_bucket" {
  value = aws_s3_bucket.raw_documents.id
}
