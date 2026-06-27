# repospec

A standard metadata format for AI agents to efficiently navigate and understand repository structure, architecture, and organization.

Instead of scanning thousands of files, agents read a single `.repospec.json` file at the repo root and get a curated index of entry points, modules, patterns, and features.

## Quick Start

1. **Understand the format:** [SPEC.md](SPEC.md) — complete format definition with examples
2. **Agent using `.repospec.json`?** [AGENT_DISCOVERY_GUIDE.md](AGENT_DISCOVERY_GUIDE.md) — how agents discover, understand, and use the metadata
3. **Generate `.repospec.json`:** [PROMPT.md](PROMPT.md) — prompts to generate metadata from your repo
4. **Validate your `.repospec.json`:** Use `schema.json` with any JSON Schema validator
5. **Examples:** Check `examples/` for sample `.repospec.json` files for different project types

## The Problem

AI agents waste time and tokens on **rediscovery**:
- Searching for entry points
- Inferring module structure
- Finding code relevant to a feature
- Re-deriving architectural decisions

Existing tools (LSP, SCIP, Bazel, Nx) solve overlapping but different problems. repospec fills the gap at the **intent level** — helping agents orient themselves at module/feature granularity.

## Format Overview

A `.repospec.json` file at the repo root contains:

- **`entrypoints`** — Where execution starts (services, CLIs, workers)
- **`modules`** — Logical modules and their purpose
- **`patterns`** — Cross-cutting concerns (auth, logging, error-handling)
- **`key_files`** — Important files by category
- **`features`** — Feature flows traced through the code
- **`testing`** — Test structure and conventions
- **`dependencies`** — Notable third-party libraries and why they matter

All paths are repo-relative; all references use stable anchors (function names, not line numbers).

## Example

```json
{
  "schema": "repospec/v1",
  "name": "checkout-service",
  "summary": "Payment processing and order management",

  "entrypoints": [
    {
      "name": "api-gateway",
      "kind": "service",
      "path": "cmd/gateway/main.go",
      "purpose": "HTTP edge; routes to internal services"
    }
  ],

  "modules": [
    {
      "id": "checkout",
      "path": "internal/checkout/",
      "purpose": "Orchestrates the checkout flow",
      "depends_on": ["store", "payments"]
    }
  ],

  "features": [
    {
      "name": "place-order",
      "description": "User completes purchase",
      "flow": [
        { "step": "entry", "file": "cmd/gateway/routes.go", "fn": "registerCheckout" },
        { "step": "handler", "file": "internal/checkout/handler.go", "fn": "handleCheckout" },
        { "step": "logic", "file": "internal/checkout/service.go", "fn": "CompleteOrder" },
        { "step": "persistence", "file": "internal/store/orders.go", "fn": "CreateOrder" }
      ]
    }
  ]
}
```

An agent reads this once and knows:
- How to run the service
- Which modules exist and what they do
- How a feature flows through the code
- Where to start exploring

## Maintenance

- **Generated sections** (paths, imports): auto-generated from code, regenerated in CI
- **Hand-written sections** (purpose, rationale): written once, updated as the codebase evolves
- **CI validation**: schema validation + freshness checks on every commit
- **Self-healing**: agents fix contradictions they discover

See [SPEC.md](SPEC.md#maintenance-strategy) for details.

## Tooling

Reference implementations for:
- **Validator**: Check `.repospec.json` against schema and validate file paths
- **Generator**: Auto-generate mechanical sections from code
- **Examples**: `.repospec.json` files for common project types (Go, Node.js, Python, Rust)

See `tools/` directory.

## FAQ

**Why not just use LSP / SCIP / Bazel?**  
LSP finds symbols; Bazel describes the build. repospec describes *intent and architecture at the module level*. They're complementary.

**How do I keep `.repospec.json` up to date?**  
Split the file: auto-generate paths/imports, hand-write purpose/rationale. CI checks for freshness.

**Is this standardized?**  
It's an open-source format with a reference schema. Adoption is voluntary; no central registry (yet).

**Can I use this for a monorepo?**  
Yes. Define `modules` for each service/package. Each module can have its own `entrypoints` and `features`.

## Benchmark Tool

Measure the impact of `.repospec.json` on agent code navigation:

```bash
./tools/repospec_benchmark.sh /path/to/repo
```

This tool generates `.repospec.json` for any repository, creates 8 code-finding test tasks, and runs two agents in parallel — one WITH the metadata, one without — to compare efficiency and accuracy.

See [`tools/README.md`](tools/README.md) for details.

## Contributing

Feedback, use cases, and implementations are welcome. Open an issue or PR.

## License

MIT
