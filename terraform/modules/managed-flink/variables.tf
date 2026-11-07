variable "environment" {
  description = "Entorno de despliegue"
  type        = string
}

variable "artifact_object_version" {
  type    = string
  default = null
}
variable "start_application" {
  type    = bool
  default = false
}
variable "snapshots_enabled" {
  type    = bool
  default = false
}
variable "harden_trust" {
  type    = bool
  default = false
}

variable "iceberg_warehouse" { type = string }
variable "iceberg_database_arn" { type = string }
variable "iceberg_database" { type = string }
variable "iceberg_table" { type = string }
variable "aws_region" { type = string }

variable "stream_arn" {
  description = "ARN del stream de Kinesis que consume Flink"
  type        = string
}

variable "artifact_bucket_name" {
  description = "Bucket S3 que contiene el JAR de Flink"
  type        = string
}

variable "artifact_bucket_arn" {
  description = "ARN del bucket S3 que contiene el JAR"
  type        = string
}

variable "artifact_key" {
  description = "Ruta del JAR dentro del bucket S3"
  type        = string
  default     = "artifacts/flink/flink-transactions-1.1.0.jar"
}

variable "parallelism" {
  description = "Paralelismo inicial de la aplicaciÃ³n Flink"
  type        = number
  default     = 1

  validation {
    condition     = var.parallelism >= 1
    error_message = "El paralelismo debe ser al menos 1."
  }
}
