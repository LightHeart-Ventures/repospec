# Repospec Marketing Site Infrastructure

This directory contains the Terraform infrastructure for deploying the Repospec marketing site to AWS S3 + CloudFront.

## Architecture

- **S3 Bucket**: Static site content storage
- **CloudFront**: CDN for global distribution and HTTPS
- **Route53**: (Manual setup) DNS routing to CloudFront
- **Access Logs**: CloudFront access logs stored in a separate S3 bucket

## Prerequisites

1. **AWS Account** with `hohertz` profile configured
2. **Terraform** >= 1.0 installed
3. **AWS CLI** configured and authenticated
4. **Domain registered**: repospec.org must be registered in Route53

## Quick Start

### 1. Initialize Terraform

```bash
make terraform-init
```

### 2. Validate Configuration

```bash
make terraform-validate
```

### 3. Plan Deployment

```bash
make terraform-plan
```

Review the plan to ensure all resources are correct.

### 4. Apply Configuration

```bash
make terraform-apply
```

This creates:
- S3 bucket for marketing site content
- S3 bucket for CloudFront logs
- CloudFront distribution
- Origin Access Identity (OAI) for secure access

### 5. Deploy Marketing Site

```bash
make deploy
```

This:
1. Applies Terraform changes
2. Uploads marketing site files to S3
3. Makes them available via CloudFront

## DNS Setup

After applying Terraform, you'll need to create a Route53 alias record to point your domain to CloudFront:

```bash
# Get CloudFront domain
make output-cloudfront

# Get CloudFront zone ID (for Route53 alias)
make output-distribution-id
```

Then manually create an A record in Route53 that aliases to the CloudFront distribution.

## Managing the Site

### Upload New Content

```bash
make upload-site
```

### Invalidate CloudFront Cache

After uploading changes:

```bash
make invalidate-cache
```

This clears the CloudFront cache so updates are visible immediately.

### View All Outputs

```bash
make show-outputs
```

Shows S3 bucket ID, CloudFront domain, and other resource IDs.

## Cleanup

To destroy all AWS resources:

```bash
make terraform-destroy
```

**Warning**: This will delete the S3 buckets and CloudFront distribution.

## Project Structure

```
infra/terraform/
├── main.tf          # S3, CloudFront, and OAI resources
├── variables.tf     # Input variables
├── outputs.tf       # Output values
├── versions.tf      # Provider configuration
└── terraform.tfvars # Variable values
```

## Notes

- CloudFront distribution uses HTTP/2 and HTTP/3 for better performance
- Origin Access Identity ensures only CloudFront can access S3 content
- Access logs are stored with a 30-day retention policy
- S3 versioning is enabled for disaster recovery
- Server-side encryption is enabled on S3 buckets

## Environment Variables

Set these before running Terraform commands:

```bash
export AWS_PROFILE=hohertz
export AWS_REGION=us-east-1
```

Or they will use the defaults in `terraform.tfvars`.
