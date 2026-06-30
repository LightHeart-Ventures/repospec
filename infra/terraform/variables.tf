variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
}

variable "domain_name" {
  description = "Domain name for the marketing site"
  type        = string
  default     = "repospec.org"
}

variable "index_document" {
  description = "Index document for S3 bucket"
  type        = string
  default     = "index.html"
}

variable "error_document" {
  description = "Error document for S3 bucket"
  type        = string
  default     = "error.html"
}

variable "enable_https_redirect" {
  description = "Enable HTTP to HTTPS redirect"
  type        = bool
  default     = true
}

variable "tags" {
  description = "Additional tags to apply to all resources"
  type        = map(string)
  default     = {}
}
