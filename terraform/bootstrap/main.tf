terraform {
  required_version = ">= 1.10.0"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 6.0" }
  }
}
variable "environment" { type = string }
variable "aws_region" { type = string }
variable "aws_profile" { type = string }
provider "aws" {
  region  = var.aws_region
  profile = var.aws_profile
}
data "aws_caller_identity" "current" {}
resource "aws_s3_bucket" "state" {
  bucket        = "coderhouse-${var.environment}-tf-${data.aws_caller_identity.current.account_id}"
  force_destroy = true
  tags          = { Project = "coderhouse-data-platform", Environment = var.environment, Purpose = "CapstoneIsolatedState" }
  lifecycle {
    precondition {
      condition     = startswith(var.environment, "cap-")
      error_message = "Este bootstrap solo crea backends cap- nuevos, nunca el backend dev."
    }
  }
}
resource "aws_s3_bucket_versioning" "state" {
  bucket = aws_s3_bucket.state.id
  versioning_configuration { status = "Enabled" }
}
resource "aws_s3_bucket_public_access_block" "state" {
  bucket                  = aws_s3_bucket.state.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
resource "aws_s3_bucket_server_side_encryption_configuration" "state" {
  bucket = aws_s3_bucket.state.id
  rule {
    apply_server_side_encryption_by_default { sse_algorithm = "AES256" }
  }
}
output "bucket" { value = aws_s3_bucket.state.id }
