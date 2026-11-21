terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 6.0, < 7.0"
    }
  }
}

variable "bucket_name" { type = string }
variable "database_name" {
  type    = string
  default = "lakehouse_db"
}

locals {
  warehouse = "s3://${var.bucket_name}/lakehouse"
}

resource "aws_glue_catalog_database" "lakehouse" {
  name         = var.database_name
  description  = "Pre-entrega 5: agregaciones transaccionales Apache Iceberg"
  location_uri = "${local.warehouse}/${var.database_name}/"

  lifecycle {
    prevent_destroy = true
  }
}

# Iceberg creates the table and atomically owns metadata_location; Terraform must
# never overwrite that pointer with a generic Glue storage_descriptor.
output "database_name" { value = aws_glue_catalog_database.lakehouse.name }
output "database_arn" { value = aws_glue_catalog_database.lakehouse.arn }
output "catalog_id" { value = aws_glue_catalog_database.lakehouse.catalog_id }
output "warehouse" { value = local.warehouse }
output "table_name" { value = "transaction_aggregates" }
output "table_location" {
  value = "${local.warehouse}/${var.database_name}/transaction_aggregates"
}
