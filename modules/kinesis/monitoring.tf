resource "aws_cloudwatch_log_group" "firehose" {
  name              = "/aws/kinesisfirehose/${var.environment}-transactions"
  retention_in_days = 7
}

resource "aws_cloudwatch_log_stream" "firehose" {
  name           = "S3Delivery"
  log_group_name = aws_cloudwatch_log_group.firehose.name
}

resource "aws_cloudwatch_metric_alarm" "read_throughput" {
  alarm_name          = "${var.environment}-kinesis-read-throughput"
  alarm_description   = "Kinesis read throughput exceeded"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "ReadProvisionedThroughputExceeded"
  namespace           = "AWS/Kinesis"
  period              = 60
  statistic           = "Sum"
  threshold           = 0
  treat_missing_data  = "notBreaching"

  dimensions = {
    StreamName = aws_kinesis_stream.transactions.name
  }
}

resource "aws_cloudwatch_metric_alarm" "write_throughput" {
  alarm_name          = "${var.environment}-kinesis-write-throughput"
  alarm_description   = "Kinesis write throughput exceeded"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "WriteProvisionedThroughputExceeded"
  namespace           = "AWS/Kinesis"
  period              = 60
  statistic           = "Sum"
  threshold           = 0
  treat_missing_data  = "notBreaching"

  dimensions = {
    StreamName = aws_kinesis_stream.transactions.name
  }
}
