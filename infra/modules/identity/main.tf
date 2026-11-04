
data "aws_iam_policy_document" "processing_trust" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type = "Service"
      identifiers = [
        "lambda.amazonaws.com",
        "kinesisanalytics.amazonaws.com"
      ]
    }
  }
}

resource "aws_iam_role" "processing" {
  name               = "coderhouse-${var.environment}-processing"
  assume_role_policy = data.aws_iam_policy_document.processing_trust.json
}

data "aws_iam_policy_document" "processing" {
  statement {
    sid       = "ListRawPrefix"
    effect    = "Allow"
    actions   = ["s3:ListBucket"]
    resources = [var.data_lake_bucket_arn]

    condition {
      test     = "StringLike"
      variable = "s3:prefix"
      values = [
        trimsuffix(var.data_prefix, "/"),
        "${trimsuffix(var.data_prefix, "/")}/*"
      ]
    }
  }

  statement {
    sid    = "ReadWriteRawObjects"
    effect = "Allow"

    actions = [
      "s3:GetObject",
      "s3:PutObject"
    ]

    resources = [
      "${var.data_lake_bucket_arn}/${var.data_prefix}*"
    ]
  }
}

resource "aws_iam_role_policy" "processing" {
  name   = "coderhouse-processing-s3"
  role   = aws_iam_role.processing.id
  policy = data.aws_iam_policy_document.processing.json
}

data "aws_caller_identity" "current" {}

data "aws_iam_policy_document" "audit_trust" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "AWS"
      identifiers = [data.aws_caller_identity.current.account_id]
    }

    condition {
      test     = "ArnEquals"
      variable = "aws:PrincipalArn"
      values = [
        "arn:aws:iam::${data.aws_caller_identity.current.account_id}:user/terraform-dev"
      ]
    }
  }
}

resource "aws_iam_role" "audit" {
  name               = "coderhouse-${var.environment}-audit"
  assume_role_policy = data.aws_iam_policy_document.audit_trust.json
}

data "aws_iam_policy_document" "audit" {
  statement {
    sid    = "ReadInfrastructure"
    effect = "Allow"

    actions = [
      "ec2:DescribeVpcs",
      "ec2:DescribeSubnets",
      "ec2:DescribeRouteTables",
      "ec2:DescribeVpcEndpoints"
    ]

    resources = ["*"]
  }

  statement {
    sid       = "ReadDataLakeMetadata"
    effect    = "Allow"
    actions   = ["s3:GetBucketLocation", "s3:GetBucketVersioning"]
    resources = [var.data_lake_bucket_arn]
  }
}

resource "aws_iam_role_policy" "audit" {
  name   = "coderhouse-audit-readonly"
  role   = aws_iam_role.audit.id
  policy = data.aws_iam_policy_document.audit.json
}
