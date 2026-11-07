
terraform {
  required_version = ">= 1.10.0"

  # Partial backend: generated locally from STS identity; never commit state or
  # credentials. Existing dev retains its original bucket/key/locking settings.
  backend "s3" {}
}
