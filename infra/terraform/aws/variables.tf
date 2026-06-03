variable "environment" {
  description = "Deployment environment (dev, stage, prod)"
  type        = string
  default     = "dev"
}

variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "List of availability zones"
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b", "us-east-1c"]
}

variable "private_subnet_cidrs" {
  description = "CIDR blocks for private subnets"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for public subnets"
  type        = list(string)
  default     = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]
}

variable "data_subnet_cidrs" {
  description = "CIDR blocks for data subnets (RDS, ElastiCache)"
  type        = list(string)
  default     = ["10.0.201.0/24", "10.0.202.0/24", "10.0.203.0/24"]
}

variable "eks_cluster_version" {
  description = "Kubernetes version for EKS"
  type        = string
  default     = "1.31"
}

variable "api_node_instance_types" {
  description = "EC2 instance types for API node group"
  type        = list(string)
  default     = ["c7g.large", "c7g.xlarge"]
}

variable "worker_node_instance_types" {
  description = "EC2 instance types for worker node group"
  type        = list(string)
  default     = ["m7g.xlarge", "m7g.2xlarge"]
}

variable "domain_name" {
  description = "Root domain for the application"
  type        = string
  default     = "contextclaw.dev"
}
