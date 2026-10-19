
module "network" {
  source = "../../modules/network"

  environment = var.environment
  vpc_cidr    = var.vpc_cidr

  private_subnet_cidrs = [
    "10.10.1.0/24",
    "10.10.2.0/24"
  ]
}

module "identity" {
  source = "../../modules/identity"

  environment          = var.environment
  data_lake_bucket_arn = aws_s3_bucket.data_lake.arn
  data_prefix          = "raw/"
}

