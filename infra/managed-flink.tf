module "managed_flink" {
  source = "./modules/managed-flink"

  count = var.enable_ingestion ? 1 : 0

  environment = var.environment

  stream_arn = module.kinesis[0].stream_arn

  artifact_bucket_name = aws_s3_bucket.data_lake.id
  artifact_bucket_arn  = aws_s3_bucket.data_lake.arn

  artifact_key = "artifacts/flink/flink-transactions-1.1.0.jar"

  parallelism = 1

  iceberg_warehouse    = module.lakehouse.warehouse
  iceberg_database_arn = module.lakehouse.database_arn
  iceberg_database     = module.lakehouse.database_name
  iceberg_table        = module.lakehouse.table_name
  aws_region           = var.aws_region
}
