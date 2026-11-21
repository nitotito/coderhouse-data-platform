terraform {
  required_version = ">= 1.10.0"
  backend "s3" {}
}
variable "environment" {
  type = string
  validation {
    condition     = can(regex("^cap-[a-z0-9-]{6,20}$", var.environment))
    error_message = "Se exige un nombre cap- unico para impedir apuntar a dev."
  }
}
variable "aws_region" { type = string }
variable "aws_profile" { type = string }
variable "artifact_source_path" { type = string }
variable "kinesis_kms_key_arn" { type = string }
data "aws_caller_identity" "isolated" {}
provider "aws" {
  region  = var.aws_region
  profile = var.aws_profile
}
module "platform" {
  source                        = "./.."
  environment                   = var.environment
  aws_region                    = var.aws_region
  aws_profile                   = var.aws_profile
  enable_ingestion              = true
  enable_redshift               = true
  redshift_kinesis_kms_key_arn  = var.kinesis_kms_key_arn
  data_lake_bucket_name         = "coderhouse-${var.environment}-lake-${data.aws_caller_identity.isolated.account_id}"
  lakehouse_database_name       = replace("${var.environment}_lakehouse", "-", "_")
  artifact_source_path          = var.artifact_source_path
  artifact_key                  = "artifacts/flink/flink-transactions-1.2.0.jar"
  start_flink                   = true
  flink_snapshots_enabled       = true
  harden_flink_trust            = true
  force_destroy_isolated_bucket = true
  initialize_platform           = true
}
output "platform" {
  value = {
    environment = var.environment
    bucket      = module.platform.data_lake_bucket_name
    stream      = module.platform.kinesis_stream_name
    lakehouse   = module.platform.lakehouse
    flink       = module.platform.flink
    redshift    = module.platform.redshift
  }
}
