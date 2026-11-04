
terraform {
  required_version = ">= 1.10.0"

  backend "s3" {
    bucket  = "coderhouse-terraform-672049777597"
    key     = "environments/dev/terraform.tfstate"
    region  = "us-east-1"
    profile = "coderhouse-dev"

    encrypt        = true
    dynamodb_table = "coderhouse-terraform-locks"
  }
}
