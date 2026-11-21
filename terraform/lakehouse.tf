module "lakehouse" {
  source        = "./modules/lakehouse"
  bucket_name   = aws_s3_bucket.data_lake.id
  database_name = var.lakehouse_database_name
}

output "lakehouse" {
  value = {
    catalog_id     = module.lakehouse.catalog_id
    database       = module.lakehouse.database_name
    table          = module.lakehouse.table_name
    warehouse      = module.lakehouse.warehouse
    table_location = module.lakehouse.table_location
  }
}
