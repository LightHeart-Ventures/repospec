aws_region  = "us-east-1"
environment = "production"
domain_name = "repospec.org"

# Note: S3 bucket is named hohertz-repospec-marketing to match IAM permissions
# The domain alias will still point to repospec.org via Route53
tags = {
  Team        = "platform"
  CostCenter  = "engineering"
  Application = "marketing-site"
}
