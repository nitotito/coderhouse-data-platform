
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

provider "aws" {
  region  = var.aws_region
  profile = "coderhouse-dev"

  default_tags {
    tags = {
      Project     = "coderhouse-data-platform"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}
