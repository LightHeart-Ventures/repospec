# Repospec Marketing Site — Infrastructure Status

## ✅ Completed

### Terraform Infrastructure Defined
- **S3 Buckets**: Created and ready for deployment
  - `repospec.org` — marketing site content bucket
  - `repospec.org-cf-logs` — CloudFront access logs
  
- **CloudFront Distribution**: Configured for global CDN delivery
  - HTTP/2 and HTTP/3 support
  - Origin Access Identity (OAI) for secure S3 access
  - Cache behaviors for different content types:
    - Static assets (`/assets/*`) — long TTL
    - HTML/pages (default) — shorter TTL
    - API paths (`/api/*`) — no caching

- **Security**:
  - Public access blocked on S3 buckets
  - CloudFront OAI provides exclusive access
  - S3 versioning enabled for recovery
  - AES256 encryption by default
  - 30-day log retention lifecycle

### Marketing Site Content
- **index.html** — Professional marketing homepage
  - Hero section with call-to-action
  - Features grid highlighting Repospec benefits
  - Quick start guide with JSON example
  - Documentation links
  - Responsive design (mobile-friendly)

- **error.html** — 404 error page
- **assets/style.css** — Modern, clean styling

### Terraform Files
```
infra/terraform/
├── main.tf          # S3, CloudFront, OAI resources
├── variables.tf     # Configuration inputs
├── outputs.tf       # CloudFront domain, bucket IDs
├── versions.tf      # Provider setup (AWS ~> 5.0)
└── terraform.tfvars # Variable defaults
```

### Makefile Commands
```bash
make terraform-init       # Initialize Terraform
make terraform-validate   # Validate configuration
make terraform-plan       # Preview changes
make terraform-apply      # Deploy infrastructure
make deploy               # Apply + upload site
make invalidate-cache     # Clear CloudFront cache
make clean                # Remove .terraform
```

## ⏸️ Current Blocker

**AWS Permissions**: The `terraform` user in account `691716211469` lacks S3 bucket creation permissions.

**Next Steps**:
1. **Grant S3 permissions** to the `terraform` user:
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": [
           "s3:CreateBucket",
           "s3:PutBucketVersioning",
           "s3:PutBucketPolicy",
           "s3:PutLifecycleConfiguration",
           "s3:PutEncryptionConfiguration",
           "s3:PutPublicAccessBlock"
         ],
         "Resource": "arn:aws:s3:::repospec.org*"
       },
       {
         "Effect": "Allow",
         "Action": [
           "cloudfront:*",
           "s3:GetObject"
         ],
         "Resource": "*"
       }
     ]
   }
   ```

2. **Or**: Use an admin account to apply Terraform:
   ```bash
   export AWS_PROFILE=<admin-profile>
   make terraform-apply
   make deploy
   ```

3. **Then**: Setup DNS in Route53:
   - Create CNAME or A (alias) record
   - Point `repospec.org` → CloudFront domain
   - Wait for DNS propagation (~5 min)

## Infrastructure Diagram

```
Domain (Route53)
      ↓
   repospec.org
      ↓
CloudFront Distribution
   ├─ HTTP/2, HTTP/3
   ├─ Global Edge Locations
   └─ Origin: S3 Bucket (via OAI)
       ├─ index.html
       ├─ error.html
       └─ assets/style.css
```

## Cost Estimate

**Monthly recurring** (estimated):
- S3 storage: ~$0.50 (for site content + logs)
- CloudFront data transfer: $0.085/GB (first 10TB)
- CloudFront requests: $0.0075/10k requests
- Route53 hosted zone: $0.50

**Total**: ~$1-5/month depending on traffic

## Security Checklist

- ✅ S3 buckets have public access blocked
- ✅ CloudFront uses OAI for S3 access
- ✅ S3 versioning enabled
- ✅ AES256 encryption enabled
- ✅ Access logs collected
- ⏳ HTTPS certificate (manual DNS setup required for repospec.org)

## Deployment Workflow (CI/CD Ready)

Once permissions are fixed, the deployment pipeline is:

```bash
# Local testing
make terraform-plan

# Production deployment
make terraform-apply    # Create infrastructure
make deploy            # Upload site content
make invalidate-cache  # Clear CDN cache

# Iterate on content
# → edit marketing-site/index.html
make upload-site       # Push new content
make invalidate-cache  # Refresh cache
```

## Next: CI/CD Pipeline

Once deployed locally, wire up GitHub Actions:

```yaml
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
    steps:
      - uses: actions/checkout@v4
      - uses: hashicorp/setup-terraform@v2
      - run: cd infra/terraform && terraform init
      - run: cd infra/terraform && terraform apply -auto-approve
      - run: make deploy
```

---

**Status**: Infrastructure defined and validated. Ready for deployment once AWS permissions are granted.
