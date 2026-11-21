module "managed_flink" {
  source = "./modules/managed-flink"

  count = var.enable_ingestion ? 1 : 0

  environment = var.environment

  stream_arn = module.kinesis[0].stream_arn

  artifact_bucket_name = aws_s3_bucket.data_lake.id
  artifact_bucket_arn  = aws_s3_bucket.data_lake.arn

  artifact_key            = var.artifact_key
  artifact_object_version = try(aws_s3_object.flink_artifact[0].version_id, null)
  start_application       = var.start_flink
  snapshots_enabled       = var.flink_snapshots_enabled
  harden_trust            = var.harden_flink_trust

  parallelism = 1

  iceberg_warehouse    = module.lakehouse.warehouse
  iceberg_database_arn = module.lakehouse.database_arn
  iceberg_database     = module.lakehouse.database_name
  iceberg_table        = module.lakehouse.table_name
  aws_region           = var.aws_region
}

resource "aws_s3_object" "flink_artifact" {
  count        = var.artifact_source_path == null ? 0 : 1
  bucket       = aws_s3_bucket.data_lake.id
  key          = var.artifact_key
  source       = var.artifact_source_path
  source_hash  = filemd5(var.artifact_source_path)
  content_type = "application/java-archive"
  depends_on   = [aws_s3_bucket_versioning.data_lake, aws_s3_bucket_server_side_encryption_configuration.data_lake]
}

output "flink" {
  value = var.enable_ingestion ? {
    application_name = module.managed_flink[0].application_name
    application_arn  = module.managed_flink[0].application_arn
    log_group_name   = module.managed_flink[0].log_group_name
  } : null
}
