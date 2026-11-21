
data "aws_caller_identity" "platform" {}
resource "aws_s3_bucket" "data_lake" {
  bucket        = coalesce(var.data_lake_bucket_name, "coderhouse-data-lake-${data.aws_caller_identity.platform.account_id}")
  force_destroy = var.force_destroy_isolated_bucket

  tags = {
    Name = "${var.environment}-data-lake"
  }
}

resource "aws_s3_bucket_public_access_block" "data_lake" {
  bucket = aws_s3_bucket.data_lake.id

  block_public_acls       = true
  ignore_public_acls      = true
  block_public_policy     = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "data_lake" {
  bucket = aws_s3_bucket.data_lake.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "data_lake" {
  bucket = aws_s3_bucket.data_lake.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}
