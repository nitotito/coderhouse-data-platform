variable "environment" {
  description = "Entorno de despliegue"
  type        = string
}

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
  default     = "artifacts/flink/flink-transactions-1.0.0.jar"
}

variable "parallelism" {
  description = "Paralelismo inicial de la aplicación Flink"
  type        = number
  default     = 1

  validation {
    condition     = var.parallelism >= 1
    error_message = "El paralelismo debe ser al menos 1."
  }
}