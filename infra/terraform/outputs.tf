output "s3_bucket_id" {
  description = "The S3 bucket ID for the marketing site"
  value       = aws_s3_bucket.marketing_site.id
}

output "s3_bucket_arn" {
  description = "The S3 bucket ARN"
  value       = aws_s3_bucket.marketing_site.arn
}

output "cloudfront_domain_name" {
  description = "The CloudFront distribution domain name"
  value       = aws_cloudfront_distribution.marketing_site.domain_name
}

output "cloudfront_distribution_id" {
  description = "The CloudFront distribution ID (for cache invalidation)"
  value       = aws_cloudfront_distribution.marketing_site.id
}

output "cloudfront_distribution_zone_id" {
  description = "The CloudFront distribution hosted zone ID"
  value       = aws_cloudfront_distribution.marketing_site.hosted_zone_id
}

output "s3_regional_domain" {
  description = "The S3 regional domain name"
  value       = aws_s3_bucket.marketing_site.bucket_regional_domain_name
}

output "logs_bucket_id" {
  description = "The S3 bucket for CloudFront logs"
  value       = aws_s3_bucket.cloudfront_logs.id
}
