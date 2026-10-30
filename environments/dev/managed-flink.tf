module "managed_flink" {
  source = "../../modules/managed-flink"

  count = var.enable_ingestion ? 1 : 0

  environment = var.environment

  stream_arn = module.kinesis[0].stream_arn

  artifact_bucket_name = aws_s3_bucket.data_lake.id
  artifact_bucket_arn  = aws_s3_bucket.data_lake.arn

  artifact_key = "artifacts/flink/flink-transactions-1.0.0.jar"

  parallelism = 1
}