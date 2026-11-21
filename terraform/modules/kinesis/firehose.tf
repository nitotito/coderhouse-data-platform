resource "aws_kinesis_firehose_delivery_stream" "bronze" {
  count = var.enable_firehose ? 1 : 0

  name        = "${var.environment}-transactions-firehose"
  destination = "extended_s3"

  kinesis_source_configuration {
    kinesis_stream_arn = aws_kinesis_stream.transactions.arn
    role_arn           = aws_iam_role.firehose[0].arn
  }

  extended_s3_configuration {
    role_arn   = aws_iam_role.firehose[0].arn
    bucket_arn = var.data_lake_bucket_arn

    prefix              = "ingesta/year=!{timestamp:yyyy}/month=!{timestamp:MM}/day=!{timestamp:dd}/"
    error_output_prefix = "ingesta-errors/!{firehose:error-output-type}/"

    buffering_size     = 5
    buffering_interval = 60

    cloudwatch_logging_options {
      enabled         = true
      log_group_name  = aws_cloudwatch_log_group.firehose[0].name
      log_stream_name = aws_cloudwatch_log_stream.firehose[0].name
    }
  }

  depends_on = [
    aws_iam_role_policy.firehose
  ]
}