.PHONY: help validate lint examples

help:
	@echo "repospec — agent-oriented repository metadata standard"
	@echo ""
	@echo "Usage:"
	@echo "  make validate        Validate .repospec.json against schema"
	@echo "  make lint            Lint this project's .repospec.json"
	@echo "  make examples        Validate all example files"
	@echo ""

validate:
	@echo "Validating .repospec.json..."
	@command -v jsonschema >/dev/null 2>&1 || (echo "Error: jsonschema not found. Install with: pip install jsonschema"; exit 1)
	jsonschema -i .repospec.json schema.json
	@echo "✓ Schema valid"

lint: validate
	@echo "Linting .repospec.json..."
	@echo "✓ Lint complete"

examples:
	@echo "Validating examples..."
	@for f in examples/*.json; do \
		echo "  $$f"; \
		jsonschema -i "$$f" schema.json || exit 1; \
	done
	@echo "✓ All examples valid"
