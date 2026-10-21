
resource "aws_kinesis_stream" "transactions" {
  name             = "${var.environment}-${var.stream_name}-stream"
  shard_count      = var.shard_count
  retention_period = 24

  stream_mode_details {
    stream_mode = "PROVISIONED"
  }

  encryption_type = "KMS"
  kms_key_id      = "alias/aws/kinesis"

  tags = {
    Name        = "${var.environment}-${var.stream_name}-stream"
    Environment = var.environment
    Project     = "coderhouse-data-platform"
  }
}
