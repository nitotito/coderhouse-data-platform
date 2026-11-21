variable "enable_redshift" {
  description = "Crear Redshift solo despues de aprobar el plan y su costo."
  type        = bool
  default     = false
  validation {
    condition     = !var.enable_redshift || (var.enable_ingestion && var.redshift_kinesis_kms_key_arn != null)
    error_message = "Redshift requiere enable_ingestion=true y el ARN real de la clave Kinesis."
  }
}

variable "redshift_kinesis_kms_key_arn" {
  description = "ARN verificado de la clave que cifra el stream (no un alias)."
  type        = string
  default     = null
}

module "redshift" {
  count  = var.enable_redshift ? 1 : 0
  source = "./modules/redshift"

  environment         = var.environment
  vpc_id              = module.network.vpc_id
  subnet_ids          = module.network.private_subnet_ids
  region              = var.aws_region
  stream_arn          = var.enable_ingestion ? module.kinesis[0].stream_arn : ""
  kinesis_kms_key_arn = var.redshift_kinesis_kms_key_arn
  lakehouse_bucket    = aws_s3_bucket.data_lake.id
  lakehouse_database  = module.lakehouse.database_name
  lakehouse_table     = module.lakehouse.table_name

}

output "redshift" {
  value = var.enable_redshift ? module.redshift[0].connection : null
}
