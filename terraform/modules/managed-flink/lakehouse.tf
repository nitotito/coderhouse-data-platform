data "aws_caller_identity" "lakehouse" {}
data "aws_partition" "lakehouse" {}

locals {
  glue_catalog_arn = "arn:${data.aws_partition.lakehouse.partition}:glue:${var.aws_region}:${data.aws_caller_identity.lakehouse.account_id}:catalog"
  glue_table_arn   = "arn:${data.aws_partition.lakehouse.partition}:glue:${var.aws_region}:${data.aws_caller_identity.lakehouse.account_id}:table/${var.iceberg_database}/${var.iceberg_table}"
  table_prefix     = "lakehouse/${var.iceberg_database}/${var.iceberg_table}"
}

# Library calls are inside GlueCatalog/S3FileIO rather than direct SDK calls in
# application sources. Scope their documented API permissions explicitly.
data "aws_iam_policy_document" "lakehouse" {
  statement {
    sid       = "ReadLakehouseDatabase"
    actions   = ["glue:GetDatabase"]
    resources = [local.glue_catalog_arn, var.iceberg_database_arn]
  }
  statement {
    sid       = "ManageAggregateTable"
    actions   = ["glue:GetTable", "glue:CreateTable", "glue:UpdateTable"]
    resources = [local.glue_catalog_arn, var.iceberg_database_arn, local.glue_table_arn]
  }
  statement {
    sid       = "LakehouseBucketLocation"
    actions   = ["s3:GetBucketLocation"]
    resources = [var.artifact_bucket_arn]
  }
  statement {
    sid       = "ListAggregatePrefix"
    actions   = ["s3:ListBucket"]
    resources = [var.artifact_bucket_arn]
    condition {
      test     = "StringLike"
      variable = "s3:prefix"
      values   = [local.table_prefix, "${local.table_prefix}/*"]
    }
  }
  statement {
    sid = "ReadWriteIcebergObjects"
    actions = [
      "s3:GetObject", "s3:PutObject", "s3:DeleteObject",
      "s3:AbortMultipartUpload", "s3:ListMultipartUploadParts"
    ]
    resources = ["${var.artifact_bucket_arn}/${local.table_prefix}/*"]
  }
}

resource "aws_iam_role_policy" "lakehouse" {
  name   = "coderhouse-${var.environment}-flink-lakehouse"
  role   = aws_iam_role.flink.id
  policy = data.aws_iam_policy_document.lakehouse.json
}
