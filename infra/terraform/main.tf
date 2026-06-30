# S3 bucket for marketing site content
# Using hohertz- prefix to match IAM permissions
resource "aws_s3_bucket" "marketing_site" {
  bucket = "hohertz-repospec-marketing"

  tags = {
    Name = "hohertz-repospec-marketing-site"
  }
}

# Block public access to bucket (CloudFront will provide access)
resource "aws_s3_bucket_public_access_block" "marketing_site" {
  bucket = aws_s3_bucket.marketing_site.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Versioning for the bucket
resource "aws_s3_bucket_versioning" "marketing_site" {
  bucket = aws_s3_bucket.marketing_site.id

  versioning_configuration {
    status = "Enabled"
  }
}

# Server-side encryption for the bucket
resource "aws_s3_bucket_server_side_encryption_configuration" "marketing_site" {
  bucket = aws_s3_bucket.marketing_site.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Bucket policy to allow CloudFront access
resource "aws_s3_bucket_policy" "marketing_site" {
  bucket = aws_s3_bucket.marketing_site.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowCloudFrontAccess"
        Effect = "Allow"
        Principal = {
          AWS = aws_cloudfront_origin_access_identity.marketing_site.iam_arn
        }
        Action   = "s3:GetObject"
        Resource = "${aws_s3_bucket.marketing_site.arn}/*"
      }
    ]
  })
}

# Origin Access Identity for CloudFront
resource "aws_cloudfront_origin_access_identity" "marketing_site" {
  comment = "OAI for hohertz-repospec-marketing"
}

# CloudFront distribution
resource "aws_cloudfront_distribution" "marketing_site" {
  origin {
    domain_name = aws_s3_bucket.marketing_site.bucket_regional_domain_name
    origin_id   = "S3Origin"

    s3_origin_config {
      origin_access_identity = aws_cloudfront_origin_access_identity.marketing_site.cloudfront_access_identity_path
    }
  }

  enabled             = true
  is_ipv6_enabled     = true
  default_root_object = var.index_document
  http_version        = "http2and3"

  default_cache_behavior {
    allowed_methods  = ["GET", "HEAD", "OPTIONS"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "S3Origin"

    cache_policy_id = data.aws_cloudfront_cache_policy.managed_caching_optimized.id
    compress        = true

    viewer_protocol_policy = "redirect-to-https"
  }

  # Cache behavior for assets (long TTL)
  ordered_cache_behavior {
    path_pattern     = "/assets/*"
    allowed_methods  = ["GET", "HEAD", "OPTIONS"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "S3Origin"

    cache_policy_id = data.aws_cloudfront_cache_policy.managed_caching_optimized_static.id
    compress        = true

    viewer_protocol_policy = "redirect-to-https"
  }

  # Cache behavior for API/dynamic content (short TTL)
  ordered_cache_behavior {
    path_pattern     = "/api/*"
    allowed_methods  = ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "S3Origin"

    cache_policy_id = data.aws_cloudfront_cache_policy.managed_caching_disabled.id
    compress        = true

    viewer_protocol_policy = "https-only"
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }

  tags = {
    Name = "hohertz-repospec-distribution"
  }
}

# Managed cache policies for CloudFront
data "aws_cloudfront_cache_policy" "managed_caching_optimized" {
  name = "Managed-CachingOptimized"
}

data "aws_cloudfront_cache_policy" "managed_caching_optimized_static" {
  name = "Managed-CachingOptimized"
}

data "aws_cloudfront_cache_policy" "managed_caching_disabled" {
  name = "Managed-CachingDisabled"
}

# S3 bucket for access logs (optional but recommended)
# Using hohertz- prefix to match IAM permissions
resource "aws_s3_bucket" "cloudfront_logs" {
  bucket = "hohertz-repospec-logs"

  tags = {
    Name = "hohertz-repospec-cloudfront-logs"
  }
}

# Block public access to logs bucket
resource "aws_s3_bucket_public_access_block" "cloudfront_logs" {
  bucket = aws_s3_bucket.cloudfront_logs.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Lifecycle policy to delete old logs
resource "aws_s3_bucket_lifecycle_configuration" "cloudfront_logs" {
  bucket = aws_s3_bucket.cloudfront_logs.id

  rule {
    id     = "DeleteOldLogs"
    status = "Enabled"

    filter {
      prefix = ""
    }

    expiration {
      days = 30
    }
  }
}
