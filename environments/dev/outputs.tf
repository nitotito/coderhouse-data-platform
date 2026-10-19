
output "vpc_id" {
  description = "ID de la VPC de desarrollo"
  value       = module.network.vpc_id
}

output "private_subnet_ids" {
  description = "Subredes privadas de desarrollo"
  value       = module.network.private_subnet_ids
}

output "s3_endpoint_id" {
  description = "Endpoint privado de S3"
  value       = module.network.s3_endpoint_id
}

output "processing_role_arn" {
  description = "ARN del rol de procesamiento"
  value       = module.identity.processing_role_arn
}

output "audit_role_arn" {
  description = "ARN del rol de auditoria"
  value       = module.identity.audit_role_arn
}

output "data_lake_bucket_name" {
  description = "Nombre del bucket de datos"
  value       = aws_s3_bucket.data_lake.id
}

