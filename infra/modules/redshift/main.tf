terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 6.69.1, < 7.0"
    }
  }
}

variable "environment" { type = string }
variable "vpc_id" { type = string }
variable "subnet_ids" { type = list(string) }
variable "region" { type = string }
variable "stream_arn" { type = string }
variable "kinesis_kms_key_arn" { type = string }
variable "lakehouse_bucket" { type = string }
variable "lakehouse_database" { type = string }
variable "lakehouse_table" { type = string }

data "aws_caller_identity" "current" {}
data "aws_partition" "current" {}
locals {
  name       = "coderhouse-${var.environment}-analytics"
  account    = data.aws_caller_identity.current.account_id
  arn_prefix = "arn:${data.aws_partition.current.partition}"
  table_path = "lakehouse/${var.lakehouse_database}/${var.lakehouse_table}"
  glue_root  = "${local.arn_prefix}:glue:${var.region}:${local.account}"
}

# IAM service role, different from the read-only database role in 05_security.sql.
resource "aws_iam_role" "analytics" {
  name = "${local.name}-execution"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = ["redshift.amazonaws.com", "redshift-serverless.amazonaws.com"] }
      Action    = "sts:AssumeRole"
      Condition = {
        # SQL service-role assumption uses the documented Serverless DB-user
        # ExternalId. Require account/region there even if global source context
        # is absent; enforce the global context too whenever AWS supplies it.
        StringLike           = { "sts:ExternalId" = "${local.arn_prefix}:redshift:${var.region}:${local.account}:dbuser:serverless-${local.account}-*/*" }
        StringEqualsIfExists = { "aws:SourceAccount" = local.account }
        ArnLikeIfExists = { "aws:SourceArn" = [
          "${local.arn_prefix}:redshift-serverless:${var.region}:${local.account}:*",
          "${local.arn_prefix}:redshift:${var.region}:${local.account}:*"
        ] }
      }
    }]
  })
}

# Derived from named service operations, not the Flink Java SDK call graph.
resource "aws_iam_role_policy" "read_sources" {
  name = "read-kinesis-and-iceberg"
  role = aws_iam_role.analytics.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "ReadOnlyExistingStream", Effect = "Allow"
        Action   = ["kinesis:DescribeStream", "kinesis:DescribeStreamSummary", "kinesis:ListShards", "kinesis:GetShardIterator", "kinesis:GetRecords"]
        Resource = var.stream_arn
      },
      {
        Sid    = "DiscoverStreamNames", Effect = "Allow"
        Action = "kinesis:ListStreams", Resource = "*"
      },
      {
        Sid      = "DecryptOnlyStream", Effect = "Allow", Action = "kms:Decrypt"
        Resource = var.kinesis_kms_key_arn
        Condition = { StringEquals = {
          "kms:ViaService"                        = "kinesis.${var.region}.amazonaws.com"
          "kms:EncryptionContext:aws:kinesis:arn" = var.stream_arn
        } }
      },
      {
        Sid      = "ReadLakehouseMetadata", Effect = "Allow"
        Action   = ["glue:GetDatabase", "glue:GetTable", "glue:GetPartitions", "glue:GetPartition"]
        Resource = ["${local.glue_root}:catalog", "${local.glue_root}:database/${var.lakehouse_database}", "${local.glue_root}:table/${var.lakehouse_database}/${var.lakehouse_table}"]
      },
      {
        Sid      = "DiscoverLakehouseTables", Effect = "Allow", Action = "glue:GetTables"
        Resource = ["${local.glue_root}:catalog", "${local.glue_root}:database/${var.lakehouse_database}", "${local.glue_root}:table/${var.lakehouse_database}/*"]
      },
      {
        Sid      = "LocateBucket", Effect = "Allow", Action = "s3:GetBucketLocation"
        Resource = "${local.arn_prefix}:s3:::${var.lakehouse_bucket}"
      },
      {
        Sid       = "ListOnlyIceberg", Effect = "Allow", Action = "s3:ListBucket"
        Resource  = "${local.arn_prefix}:s3:::${var.lakehouse_bucket}"
        Condition = { StringLike = { "s3:prefix" = [local.table_path, "${local.table_path}/*"] } }
      },
      {
        Sid      = "ReadOnlyIceberg", Effect = "Allow", Action = ["s3:GetObject", "s3:GetObjectVersion"]
        Resource = "${local.arn_prefix}:s3:::${var.lakehouse_bucket}/${local.table_path}/*"
      }
    ]
  })
}

# No inbound database port: local operators use HTTPS Redshift Data API.
resource "aws_security_group" "warehouse" {
  tags        = { Checkpoint = "6" }
  name_prefix = "${local.name}-"
  description = "Private Redshift; Data API access, no inbound TCP"
  vpc_id      = var.vpc_id
  egress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "kinesis_endpoint" {
  tags        = { Checkpoint = "6" }
  name_prefix = "${local.name}-kds-"
  description = "HTTPS only from Redshift to Kinesis endpoint"
  vpc_id      = var.vpc_id
  ingress {
    from_port       = 443
    to_port         = 443
    protocol        = "tcp"
    security_groups = [aws_security_group.warehouse.id]
  }
}

# Existing private route tables have no NAT. This endpoint is required for KDS.
resource "aws_vpc_endpoint" "kinesis" {
  tags                = { Checkpoint = "6" }
  vpc_id              = var.vpc_id
  service_name        = "com.amazonaws.${var.region}.kinesis-streams"
  vpc_endpoint_type   = "Interface"
  private_dns_enabled = true
  subnet_ids          = var.subnet_ids
  security_group_ids  = [aws_security_group.kinesis_endpoint.id]
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow", Principal = "*"
      Action    = ["kinesis:DescribeStream", "kinesis:DescribeStreamSummary", "kinesis:ListShards", "kinesis:GetShardIterator", "kinesis:GetRecords", "kinesis:ListStreams"]
      Resource  = "*"
      Condition = { ArnEquals = { "aws:PrincipalArn" = aws_iam_role.analytics.arn } }
    }]
  })
}

resource "aws_redshiftserverless_namespace" "analytics" {
  tags                 = { Checkpoint = "6" }
  namespace_name       = local.name
  db_name              = "analytics"
  iam_roles            = [aws_iam_role.analytics.arn]
  default_iam_role_arn = aws_iam_role.analytics.arn
  # IAM temporary credentials via Data API; no password/secret in configuration.
  depends_on = [aws_iam_role_policy.read_sources]
}

resource "aws_redshiftserverless_workgroup" "analytics" {
  tags                 = { Checkpoint = "6" }
  workgroup_name       = local.name
  namespace_name       = aws_redshiftserverless_namespace.analytics.namespace_name
  base_capacity        = 4
  max_capacity         = 4
  publicly_accessible  = false
  enhanced_vpc_routing = false
  subnet_ids           = var.subnet_ids
  security_group_ids   = [aws_security_group.warehouse.id]
  config_parameter {
    parameter_key   = "require_ssl"
    parameter_value = "true"
  }
  depends_on = [aws_vpc_endpoint.kinesis]
}

resource "aws_redshiftserverless_usage_limit" "daily" {
  resource_arn  = aws_redshiftserverless_workgroup.analytics.arn
  usage_type    = "serverless-compute"
  amount        = 8
  period        = "daily"
  breach_action = "deactivate"
}

output "connection" {
  value = {
    workgroup     = aws_redshiftserverless_workgroup.analytics.workgroup_name
    namespace     = aws_redshiftserverless_namespace.analytics.namespace_name
    database      = "analytics"
    endpoint      = aws_redshiftserverless_workgroup.analytics.endpoint
    iam_role_arn  = aws_iam_role.analytics.arn
    workgroup_arn = aws_redshiftserverless_workgroup.analytics.arn
  }
}
