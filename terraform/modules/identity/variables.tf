
variable "environment" {
  description = "Entorno de despliegue"
  type        = string
}
variable "audit_principal_arn" {
  type    = string
  default = null
}

variable "data_lake_bucket_arn" {
  description = "ARN del bucket de datos"
  type        = string
}

variable "data_prefix" {
  description = "Prefijo autorizado dentro del Data Lake"
  type        = string
  default     = "raw/"
}
