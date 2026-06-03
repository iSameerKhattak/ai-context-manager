output "vpc_id" {
  description = "ID of the VPC"
  value       = module.vpc.vpc_id
}

output "vpc_private_subnets" {
  description = "IDs of the private subnets"
  value       = module.vpc.private_subnets
}

output "vpc_public_subnets" {
  description = "IDs of the public subnets"
  value       = module.vpc.public_subnets
}

output "eks_cluster_name" {
  description = "Name of the EKS cluster"
  value       = module.eks.cluster_name
}

output "eks_cluster_endpoint" {
  description = "EKS cluster API endpoint"
  value       = module.eks.cluster_endpoint
  sensitive   = true
}

output "aurora_endpoint" {
  description = "Aurora PostgreSQL writer endpoint"
  value       = module.aurora.endpoint
  sensitive   = true
}

output "aurora_reader_endpoint" {
  description = "Aurora PostgreSQL reader endpoint"
  value       = module.aurora.reader_endpoint
  sensitive   = true
}

output "redis_endpoint" {
  description = "Redis primary endpoint"
  value       = module.elasticache_redis.primary_endpoint_address
  sensitive   = true
}

output "raw_documents_bucket" {
  description = "S3 bucket for raw documents"
  value       = aws_s3_bucket.raw_documents.id
}

output "exports_bucket" {
  description = "S3 bucket for exports"
  value       = aws_s3_bucket.exports.id
}

output "audit_logs_bucket" {
  description = "S3 bucket for audit logs"
  value       = aws_s3_bucket.audit_logs.id
}

output "secrets_manager_arn" {
  description = "ARN of the app secrets manager secret"
  value       = aws_secretsmanager_secret.app_secrets.arn
}
