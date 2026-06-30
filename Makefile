.PHONY: help terraform-init terraform-validate terraform-plan terraform-apply terraform-destroy deploy clean

help:
	@echo "Repospec Marketing Site - Terraform Commands"
	@echo ""
	@echo "Available targets:"
	@echo "  terraform-init      Initialize Terraform working directory"
	@echo "  terraform-validate  Validate Terraform configuration"
	@echo "  terraform-fmt       Format Terraform files"
	@echo "  terraform-plan      Show what Terraform would change"
	@echo "  terraform-apply     Apply Terraform changes"
	@echo "  terraform-destroy   Destroy all AWS resources"
	@echo "  deploy              Deploy marketing site to S3 (requires terraform-apply)"
	@echo "  invalidate-cache    Invalidate CloudFront cache"
	@echo "  clean               Remove .terraform directory and lock files"

# Terraform operations
terraform-init:
	@echo "Initializing Terraform..."
	cd infra/terraform && terraform init

terraform-validate:
	@echo "Validating Terraform configuration..."
	cd infra/terraform && terraform validate

terraform-fmt:
	@echo "Formatting Terraform files..."
	cd infra/terraform && terraform fmt -recursive

terraform-plan:
	@echo "Planning Terraform changes..."
	cd infra/terraform && terraform plan -out=tfplan

terraform-apply:
	@echo "Applying Terraform changes..."
	cd infra/terraform && terraform apply tfplan

terraform-destroy:
	@echo "WARNING: This will destroy all AWS resources for this project."
	@echo "Destroying Terraform-managed resources..."
	cd infra/terraform && terraform destroy

# Deployment
deploy: terraform-apply upload-site

upload-site:
	@echo "Uploading marketing site to S3..."
	@BUCKET=$$(cd infra/terraform && terraform output -raw s3_bucket_id) && \
	echo "Uploading to S3 bucket: $$BUCKET" && \
	aws s3 sync marketing-site/ s3://$$BUCKET/ \
		--region us-east-1 \
		--cache-control "max-age=3600" \
		--exclude ".git*" && \
	echo "Upload complete!"

invalidate-cache:
	@echo "Invalidating CloudFront cache..."
	@DIST_ID=$$(cd infra/terraform && terraform output -raw cloudfront_distribution_id) && \
	echo "Invalidating distribution: $$DIST_ID" && \
	aws cloudfront create-invalidation \
		--distribution-id $$DIST_ID \
		--paths "/*" \
		--region us-east-1

# Utilities
clean:
	@echo "Cleaning up Terraform files..."
	rm -rf infra/terraform/.terraform
	rm -f infra/terraform/.terraform.lock.hcl
	rm -f infra/terraform/tfplan
	echo "Cleanup complete!"

# Output helpers
output-bucket:
	cd infra/terraform && terraform output -raw s3_bucket_id

output-cloudfront:
	cd infra/terraform && terraform output -raw cloudfront_domain_name

output-distribution-id:
	cd infra/terraform && terraform output -raw cloudfront_distribution_id

# Development workflow
dev-plan: terraform-init terraform-plan

dev-apply: terraform-init terraform-apply

# Show all outputs
show-outputs:
	cd infra/terraform && terraform output
