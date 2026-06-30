# Marketing Site Deployment Guide

## Summary

✅ **Terraform infrastructure** for S3 + CloudFront has been created and committed to feature branch `feat/marketing-site-infrastructure`.

📋 **Pull Request**: https://github.com/LightHeart-Ventures/repospec/pull/10 (draft)

## What's Included

### 1. Terraform Configuration (`infra/terraform/`)
- **main.tf**: S3 buckets, CloudFront distribution, Origin Access Identity
- **variables.tf**: Configuration inputs (region, domain, tags)
- **outputs.tf**: CloudFront domain, bucket IDs, distribution ID
- **versions.tf**: AWS provider setup (v5.0+)
- **terraform.tfvars**: Default values (repospec.org)

### 2. Marketing Site (`marketing-site/`)
- **index.html**: Professional homepage
  - Hero section with GitHub link
  - Features highlighting Repospec benefits
  - Quick start code example
  - Documentation and community links
- **error.html**: 404 error page
- **assets/style.css**: Modern, responsive design

### 3. Deployment Tools
- **Makefile**: Commands for Terraform and deployment
  - `make terraform-init` — Initialize
  - `make terraform-validate` — Validate config
  - `make terraform-plan` — Preview changes
  - `make terraform-apply` — Deploy infrastructure
  - `make deploy` — Apply + upload site
  - `make invalidate-cache` — Clear CloudFront cache
  - `make upload-site` — Push content updates

- **infra/README.md**: Setup and usage documentation

## Deployment Steps (Once AWS Permissions Fixed)

### Step 1: Grant S3 Permissions
Contact AWS admin to add S3 permissions to `terraform` user in account `691716211469`:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:*",
        "cloudfront:*"
      ],
      "Resource": "*"
    }
  ]
}
```

### Step 2: Deploy Infrastructure
```bash
cd /home/grhohertz/projects/repospec
export AWS_PROFILE=hohertz
make terraform-apply
```

### Step 3: Setup DNS (Route53)
```bash
# Get CloudFront domain
make output-cloudfront
# Output: d123456abcdef.cloudfront.net

# Get distribution hosted zone ID
make output-distribution-id
# Output: Z2FDTNDATAQYW2
```

Then in Route53, create an alias record:
- **Name**: repospec.org
- **Type**: A
- **Alias to CloudFront distribution**
- **Distribution**: d123456abcdef.cloudfront.net
- **Hosted Zone**: Z2FDTNDATAQYW2

### Step 4: Deploy Marketing Site
```bash
make deploy
```

This:
1. Uploads index.html, error.html, and CSS to S3
2. Invalidates CloudFront cache
3. Site is live at https://repospec.org

## Updating the Site

After deployment, update content anytime:

```bash
# Edit marketing-site files
nano marketing-site/index.html

# Push changes
make upload-site
make invalidate-cache
```

## Architecture

```
repospec.org (Route53)
        ↓
    CloudFront CDN
    (HTTP/2, HTTP/3, HTTPS)
        ↓
    S3 Bucket (repospec.org)
        ├─ index.html
        ├─ error.html
        └─ assets/
            └─ style.css

Additional:
├─ Access Logs → S3 (repospec.org-cf-logs)
│  └─ 30-day retention
├─ Origin Access Identity (OAI)
│  └─ Only CloudFront can access S3
└─ Versioning & Encryption
   └─ AES256, S3 versioning enabled
```

## Infrastructure Features

✅ **Security**
- S3 public access blocked
- CloudFront OAI for exclusive S3 access
- AES256 encryption
- Versioning for recovery

✅ **Performance**
- HTTP/2 and HTTP/3 support
- Global CDN via CloudFront
- Optimized cache policies per path
- Compression enabled

✅ **Monitoring**
- CloudFront access logs (30-day retention)
- S3 bucket versioning

✅ **Cost Optimization**
- Static content caching
- Edge location delivery
- No origin costs

## Cost Estimate

**Monthly**:
- S3 storage: ~$0.50
- CloudFront: $0.085/GB + $0.0075/10k requests
- Route53: $0.50
- **Total**: ~$1-5/month (depending on traffic)

## CI/CD Pipeline (Next Step)

Once deployed and verified, wire up GitHub Actions for automated deployments:

```yaml
# .github/workflows/deploy-marketing.yml
name: Deploy Marketing Site
on:
  push:
    branches: [main]
    paths:
      - 'marketing-site/**'
      - 'infra/terraform/**'

jobs:
  deploy:
    runs-on: ubuntu-latest
    env:
      AWS_PROFILE: hohertz
    steps:
      - uses: actions/checkout@v4
      - uses: hashicorp/setup-terraform@v2
      - run: cd infra/terraform && terraform init
      - run: cd infra/terraform && terraform apply -auto-approve
      - run: make deploy
```

## Troubleshooting

**CloudFront still shows old content?**
```bash
make invalidate-cache
# Waits 30 seconds - 5 min for propagation
```

**Need to see what's in S3?**
```bash
aws s3 ls s3://repospec.org/ --recursive --human-readable --summarize
```

**Check CloudFront status?**
```bash
make show-outputs
# Shows all resource IDs and domains
```

## Files Overview

| File | Purpose |
|------|---------|
| `infra/terraform/main.tf` | All AWS resources |
| `infra/terraform/variables.tf` | Configuration inputs |
| `infra/terraform/outputs.tf` | Outputs (URLs, IDs) |
| `infra/terraform/terraform.tfvars` | Variable defaults |
| `marketing-site/index.html` | Homepage |
| `marketing-site/error.html` | 404 page |
| `marketing-site/assets/style.css` | Styling |
| `Makefile` | Deployment commands |
| `DEPLOYMENT_STATUS.md` | Detailed status |
| `infra/README.md` | Setup docs |

---

**Next Action**: Get S3 permissions for `terraform` user, then run `make terraform-apply && make deploy`.
