# BFSI Credit Intelligence — Production Terraform
# Region: ap-south-1 (Mumbai) for data residency compliance (DPDP Act 2023)

terraform {
  required_version = ">= 1.6"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.0"
    }
  }
  backend "s3" {
    bucket         = "bfsi-terraform-state-prod"
    key            = "bfsi-credit-intelligence/terraform.tfstate"
    region         = "ap-south-1"
    encrypt        = true
    dynamodb_table = "terraform-state-lock"
  }
}

provider "aws" {
  region = "ap-south-1"
  default_tags {
    tags = {
      Project     = "bfsi-credit-intelligence"
      Environment = var.environment
      Compliance  = "RBI-DPDP-2023"
      ManagedBy   = "Terraform"
    }
  }
}

variable "environment" {
  default = "production"
}

variable "db_password" {
  sensitive = true
}

variable "encryption_key" {
  sensitive = true
}

# VPC with private subnets (data residency in Mumbai)
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "5.0"

  name = "bfsi-vpc"
  cidr = "10.0.0.0/16"
  azs  = ["ap-south-1a", "ap-south-1b", "ap-south-1c"]

  private_subnets  = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
  public_subnets   = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]
  database_subnets = ["10.0.201.0/24", "10.0.202.0/24", "10.0.203.0/24"]

  enable_nat_gateway     = true
  single_nat_gateway     = false
  enable_dns_hostnames   = true
  enable_dns_support     = true

  # VPC flow logs for audit compliance
  enable_flow_log                      = true
  create_flow_log_cloudwatch_iam_role  = true
  create_flow_log_cloudwatch_log_group = true
}

# EKS Cluster
module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "20.0"

  cluster_name    = "bfsi-eks-${var.environment}"
  cluster_version = "1.30"

  vpc_id                         = module.vpc.vpc_id
  subnet_ids                     = module.vpc.private_subnets
  cluster_endpoint_private_access = true
  cluster_endpoint_public_access  = true

  eks_managed_node_groups = {
    general = {
      instance_types = ["m6i.xlarge"]
      min_size       = 3
      max_size       = 20
      desired_size   = 5
      labels = { workload = "general" }
    }
    ml_inference = {
      instance_types = ["c6i.2xlarge"]
      min_size       = 1
      max_size       = 10
      desired_size   = 2
      labels = { workload = "ml-inference" }
      taints = [{
        key    = "ml-workload"
        value  = "true"
        effect = "NO_SCHEDULE"
      }]
    }
  }

  # IRSA for S3, Secrets Manager access
  enable_irsa = true
}

# RDS PostgreSQL 16 — encrypted, multi-AZ for BFSI
resource "aws_db_instance" "bfsi_postgres" {
  identifier        = "bfsi-postgres-${var.environment}"
  engine            = "postgres"
  engine_version    = "16.2"
  instance_class    = "db.r6g.xlarge"
  allocated_storage = 200
  storage_type      = "gp3"
  storage_encrypted = true  # Mandatory for PII data

  db_name  = "bfsi_credit"
  username = "bfsi_admin"
  password = var.db_password

  db_subnet_group_name   = aws_db_subnet_group.bfsi.name
  vpc_security_group_ids = [aws_security_group.rds.id]

  multi_az               = true  # HA for production
  backup_retention_period = 30   # 30-day backup for audit
  deletion_protection    = true
  skip_final_snapshot    = false
  final_snapshot_identifier = "bfsi-postgres-final-${var.environment}"

  # Enable audit logging (required for RBI compliance)
  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]

  performance_insights_enabled          = true
  performance_insights_retention_period = 7
}

resource "aws_db_subnet_group" "bfsi" {
  name       = "bfsi-db-subnet-group"
  subnet_ids = module.vpc.database_subnets
}

# ElastiCache Redis — session cache, Celery broker
resource "aws_elasticache_replication_group" "bfsi_redis" {
  replication_group_id = "bfsi-redis"
  description          = "BFSI session cache and Celery broker"

  node_type            = "cache.r6g.large"
  num_cache_clusters   = 3
  port                 = 6379

  subnet_group_name  = aws_elasticache_subnet_group.bfsi.name
  security_group_ids = [aws_security_group.redis.id]

  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  automatic_failover_enabled = true
}

resource "aws_elasticache_subnet_group" "bfsi" {
  name       = "bfsi-redis-subnet-group"
  subnet_ids = module.vpc.private_subnets
}

# S3 for ML models, documents (encrypted)
resource "aws_s3_bucket" "bfsi_documents" {
  bucket = "bfsi-documents-${var.environment}-${data.aws_caller_identity.current.account_id}"
}

resource "aws_s3_bucket_server_side_encryption_configuration" "documents" {
  bucket = aws_s3_bucket.bfsi_documents.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "aws:kms"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_versioning" "documents" {
  bucket = aws_s3_bucket.bfsi_documents.id
  versioning_configuration { status = "Enabled" }
}

# Block all public access (DPDP compliance)
resource "aws_s3_bucket_public_access_block" "documents" {
  bucket                  = aws_s3_bucket.bfsi_documents.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket" "ml_models" {
  bucket = "bfsi-ml-models-${var.environment}-${data.aws_caller_identity.current.account_id}"
}

resource "aws_s3_bucket_server_side_encryption_configuration" "ml_models" {
  bucket = aws_s3_bucket.ml_models.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "aws:kms"
    }
  }
}

# MSK (Managed Kafka) for document streaming
resource "aws_msk_cluster" "bfsi_kafka" {
  cluster_name           = "bfsi-kafka-${var.environment}"
  kafka_version          = "3.6.0"
  number_of_broker_nodes = 3

  broker_node_group_info {
    instance_type  = "kafka.m5.large"
    client_subnets = module.vpc.private_subnets
    storage_info {
      ebs_storage_info { volume_size = 1000 }
    }
    security_groups = [aws_security_group.kafka.id]
  }

  encryption_info {
    encryption_in_transit {
      client_broker = "TLS"
      in_cluster    = true
    }
  }

  client_authentication {
    sasl { iam = true }
  }

  open_monitoring {
    prometheus {
      jmx_exporter { enabled_in_broker = true }
      node_exporter { enabled_in_broker = true }
    }
  }
}

# Security Groups
resource "aws_security_group" "rds" {
  name   = "bfsi-rds-sg"
  vpc_id = module.vpc.vpc_id
  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [module.eks.node_security_group_id]
  }
  egress { from_port = 0; to_port = 0; protocol = "-1"; cidr_blocks = ["0.0.0.0/0"] }
}

resource "aws_security_group" "redis" {
  name   = "bfsi-redis-sg"
  vpc_id = module.vpc.vpc_id
  ingress {
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [module.eks.node_security_group_id]
  }
  egress { from_port = 0; to_port = 0; protocol = "-1"; cidr_blocks = ["0.0.0.0/0"] }
}

resource "aws_security_group" "kafka" {
  name   = "bfsi-kafka-sg"
  vpc_id = module.vpc.vpc_id
  ingress {
    from_port       = 9098
    to_port         = 9098
    protocol        = "tcp"
    security_groups = [module.eks.node_security_group_id]
  }
  egress { from_port = 0; to_port = 0; protocol = "-1"; cidr_blocks = ["0.0.0.0/0"] }
}

# KMS key for PII encryption
resource "aws_kms_key" "bfsi_pii" {
  description             = "BFSI PII Data Encryption Key"
  deletion_window_in_days = 30
  enable_key_rotation     = true
}

resource "aws_kms_alias" "bfsi_pii" {
  name          = "alias/bfsi-pii-${var.environment}"
  target_key_id = aws_kms_key.bfsi_pii.key_id
}

# AWS Secrets Manager for API keys
resource "aws_secretsmanager_secret" "bfsi_secrets" {
  name                    = "bfsi/${var.environment}/secrets"
  kms_key_id              = aws_kms_key.bfsi_pii.arn
  recovery_window_in_days = 30
}

data "aws_caller_identity" "current" {}

output "eks_cluster_endpoint" { value = module.eks.cluster_endpoint }
output "rds_endpoint" { value = aws_db_instance.bfsi_postgres.endpoint; sensitive = true }
output "redis_endpoint" { value = aws_elasticache_replication_group.bfsi_redis.primary_endpoint_address; sensitive = true }
output "kafka_brokers" { value = aws_msk_cluster.bfsi_kafka.bootstrap_brokers_sasl_iam; sensitive = true }
output "documents_bucket" { value = aws_s3_bucket.bfsi_documents.bucket }
output "ml_models_bucket" { value = aws_s3_bucket.ml_models.bucket }
