
variable "aws_region" {
  description = "Region AWS donde se desplegara la infraestructura"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Nombre del entorno"
  type        = string
  default     = "dev"
}

variable "vpc_cidr" {
  description = "Bloque CIDR de la VPC"
  type        = string
  default     = "10.10.0.0/16"
}

variable "enable_ingestion" {
  description = "Habilita la infraestructura de ingesta"
  type        = bool
  default     = false
}

variable "aws_profile" {
  type        = string
  default     = null
  description = "Perfil opcional; null usa la cadena normal de credenciales AWS."
}
variable "data_lake_bucket_name" {
  type    = string
  default = null
  validation {
    condition     = var.environment == "dev" || var.data_lake_bucket_name != null
    error_message = "Fuera de dev se exige un bucket unico explicito."
  }
}
variable "lakehouse_database_name" {
  type    = string
  default = "lakehouse_db"
}
variable "artifact_source_path" {
  type    = string
  default = null
}
variable "artifact_key" {
  type    = string
  default = "artifacts/flink/flink-transactions-1.1.0.jar"
}
variable "start_flink" {
  type    = bool
  default = false
}
variable "flink_snapshots_enabled" {
  type    = bool
  default = false
}
variable "harden_flink_trust" {
  type    = bool
  default = false
}
variable "force_destroy_isolated_bucket" {
  type    = bool
  default = false
  validation {
    condition     = !var.force_destroy_isolated_bucket || startswith(var.environment, "cap-")
    error_message = "force_destroy solo se permite en entornos cap- aislados."
  }
}
variable "initialize_platform" {
  type    = bool
  default = false
}
