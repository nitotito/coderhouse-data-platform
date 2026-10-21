
variable "environment" {
  description = "Entorno donde se despliega Kinesis"
  type        = string
}

variable "stream_name" {
  description = "Nombre base del stream de Kinesis"
  type        = string
  default     = "transactions"
}

variable "shard_count" {
  description = "Cantidad de shards del stream"
  type        = number
  default     = 2

  validation {
    condition     = var.shard_count >= 2
    error_message = "Se requieren al menos 2 shards."
  }
}

variable "data_lake_bucket_arn" {
  description = "ARN del bucket S3 utilizado como Data Lake"
  type        = string
}

variable "data_lake_bucket_name" {
  description = "Nombre del bucket S3 utilizado como Data Lake"
  type        = string
}
