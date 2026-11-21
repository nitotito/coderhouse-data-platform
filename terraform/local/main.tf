terraform {
  required_version = ">= 1.10"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 6.0" }
  }
}
variable "region" { type = string }
variable "environment" { type = string }
variable "bucket_name" { type = string }
variable "stream_name" { type = string }
variable "shard_count" { type = number }
provider "aws" {
  region                      = var.region
  access_key                  = "test"
  secret_key                  = "test"
  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_requesting_account_id  = true
  s3_use_path_style           = true
}
module "network" {
  source               = "../modules/network"
  environment          = var.environment
  vpc_cidr             = "10.42.0.0/16"
  private_subnet_cidrs = ["10.42.1.0/24", "10.42.2.0/24"]
}
resource "aws_s3_bucket" "lakehouse" { bucket = var.bucket_name }
resource "aws_s3_bucket_versioning" "lakehouse" {
  bucket = aws_s3_bucket.lakehouse.id
  versioning_configuration { status = "Enabled" }
}
resource "aws_s3_bucket_public_access_block" "lakehouse" {
  bucket                  = aws_s3_bucket.lakehouse.id
  block_public_acls       = true
  ignore_public_acls      = true
  block_public_policy     = true
  restrict_public_buckets = true
}
resource "aws_s3_bucket_server_side_encryption_configuration" "lakehouse" {
  bucket = aws_s3_bucket.lakehouse.id
  rule {
    apply_server_side_encryption_by_default { sse_algorithm = "AES256" }
  }
}
module "kinesis" {
  source                = "../modules/kinesis"
  environment           = var.environment
  stream_name           = var.stream_name
  shard_count           = var.shard_count
  data_lake_bucket_name = aws_s3_bucket.lakehouse.id
  data_lake_bucket_arn  = aws_s3_bucket.lakehouse.arn
  enable_firehose       = true
  enable_resource_tags  = false
}
output "stream_arn" { value = module.kinesis.stream_arn }
output "bucket" { value = aws_s3_bucket.lakehouse.id }
