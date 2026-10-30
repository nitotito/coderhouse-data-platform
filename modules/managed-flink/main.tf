
data "aws_iam_policy_document" "flink_assume_role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["kinesisanalytics.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "flink" {
  name               = "coderhouse-${var.environment}-flink"
  assume_role_policy = data.aws_iam_policy_document.flink_assume_role.json
}

resource "aws_cloudwatch_log_group" "flink" {
  name              = "/aws/kinesis-analytics/coderhouse-${var.environment}-transactions-flink"
  retention_in_days = 7
}

resource "aws_cloudwatch_log_stream" "flink" {
  name           = "application"
  log_group_name = aws_cloudwatch_log_group.flink.name
}

data "aws_iam_policy_document" "flink_permissions" {
  statement {
    sid    = "ReadKinesisTransactions"
    effect = "Allow"

    actions = [
      "kinesis:DescribeStream",
      "kinesis:DescribeStreamSummary",
      "kinesis:ListShards",
      "kinesis:GetShardIterator",
      "kinesis:GetRecords"
    ]

    resources = [var.stream_arn]
  }

  statement {
    sid    = "ReadApplicationJar"
    effect = "Allow"

    actions = [
      "s3:GetObject",
      "s3:GetObjectVersion"
    ]

    resources = [
      "${var.artifact_bucket_arn}/${var.artifact_key}"
    ]
  }

  statement {
    sid    = "WriteCloudWatchLogs"
    effect = "Allow"

    actions = [
      "logs:DescribeLogStreams",
      "logs:PutLogEvents"
    ]

    resources = [
      "${aws_cloudwatch_log_group.flink.arn}:*"
    ]
  }
}

resource "aws_iam_role_policy" "flink" {
  name   = "coderhouse-${var.environment}-flink-access"
  role   = aws_iam_role.flink.id
  policy = data.aws_iam_policy_document.flink_permissions.json
}

resource "aws_kinesisanalyticsv2_application" "flink" {
  name                   = "coderhouse-${var.environment}-transactions-flink"
  description            = "Procesamiento de transacciones Kinesis con Apache Flink"
  runtime_environment    = "FLINK-2_2"
  service_execution_role = aws_iam_role.flink.arn

  # Crear la aplicacion sin iniciarla automaticamente.
  start_application = false

  application_configuration {
    application_code_configuration {
      code_content_type = "ZIPFILE"

      code_content {
        s3_content_location {
          bucket_arn = var.artifact_bucket_arn
          file_key   = var.artifact_key
        }
      }
    }

    environment_properties {
      property_group {
        property_group_id = "ApplicationProperties"

        property_map = {
          KINESIS_STREAM_ARN = var.stream_arn
        }
      }
    }

    flink_application_configuration {
      checkpoint_configuration {
        configuration_type            = "CUSTOM"
        checkpointing_enabled         = true
        checkpoint_interval           = 60000
        min_pause_between_checkpoints = 5000
      }

      monitoring_configuration {
        configuration_type = "CUSTOM"
        log_level          = "INFO"
        metrics_level      = "APPLICATION"
      }

      parallelism_configuration {
        configuration_type   = "CUSTOM"
        parallelism          = var.parallelism
        parallelism_per_kpu  = 1
        auto_scaling_enabled = false
      }
    }
  }

  cloudwatch_logging_options {
    log_stream_arn = aws_cloudwatch_log_stream.flink.arn
  }

  depends_on = [
    aws_iam_role_policy.flink
  ]

  tags = {
    Name = "coderhouse-${var.environment}-transactions-flink"
  }
}
