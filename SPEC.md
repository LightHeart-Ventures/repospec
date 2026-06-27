# repospec: A Standard for Agent-Oriented Repository Metadata

## Overview

**repospec** is a minimal, standardized format for describing repository structure, architecture, and organization in a way that helps AI agents navigate code efficiently. Instead of scanning thousands of files to understand a codebase, agents read a single `.repospec.json` file and get a curated index of entry points, modules, patterns, and features.

## Problem Statement

AI coding agents waste significant time and tokens on **rediscovery**:
- Searching for entry points (where does execution start?)
- Inferring module structure and dependencies
- Finding the files relevant to a feature or concern
- Re-deriving architectural decisions and patterns

This happens repeatedly because agents lack a persistent, structured map of the repository. Existing tools (LSP, SCIP, Bazel, Nx) solve overlapping but distinct problems:

| Tool | Level | What it Does |
|---|---|---|
| **LSP / SCIP** | Symbol | Find definitions, references, type info — precise cross-references at identifier granularity |
| **Bazel / Nx** | Build | Describe task graph and project dependencies — how to compile/run; what depends on what at the artifact level |
| **Sitemap / OpenAPI** | Interface | Document exposed services, APIs, data schemas |
| **repospec** | **Intent** | Map modules and features to code — "what is this for, where does it live, how does it fit together?" |

**repospec** fills the intent-level gap: agent orientation at module/feature granularity.

## Design Principles

1. **Minimal and queryable.** The entire index should fit in one file (< 1500 lines) so agents load it whole in one context-window. Semantic queries are emergent (filter JSON yourself).

2. **Cheap to maintain.** The schema is split: generated sections (paths, imports) come from code; hand-written sections (purpose, rationale) capture human intent. Splitting volatility keeps the file fresher.

3. **Human + machine readable.** The format is JSON for parsing, but fields are designed to be readable prose. An agent should understand `.purpose` and `.features` without a code interpreter.

4. **Stable references.** Every link to code uses repo-relative paths and stable anchors (function/symbol names) rather than line numbers. Line numbers rot immediately; stable anchors survive refactoring.

5. **Composable.** The format works for monorepos and single-service repos, polyrepos and nested structures. A monorepo can define modules independently; a single service defines itself at the root.

6. **Non-prescriptive.** This is a *map*, not a constraint. You can have code outside the index (third-party libraries, generated code, experiments). The index is what you *want agents to know about*.

## Format: `.repospec.json`

A single JSON file at the repository root.

### Top-level fields

```json
{
  "schema": "repospec/v1",
  "name": "my-service",
  "version": "1.0.0",
  "description": "...",
  "repository": "https://github.com/org/repo",
  "license": "MIT",
  "summary": "One-line orientation: what is this repo, what does it do?",

  "entrypoints": [ ... ],
  "modules": [ ... ],
  "patterns": [ ... ],
  "key_files": { ... },
  "features": [ ... ],
  "testing": { ... },
  "dependencies": [ ... ]
}
```

### `entrypoints` — The #1 thing an agent needs

Where execution starts. An agent's first question is always "where do I begin?"

```json
"entrypoints": [
  {
    "name": "api-gateway",
    "kind": "service",
    "path": "cmd/gateway/main.go",
    "start": "make run-gateway",
    "purpose": "HTTP edge; routes to internal gRPC services"
  },
  {
    "name": "wctl",
    "kind": "cli",
    "path": "cmd/wctl/main.go",
    "purpose": "Admin CLI; manages users, config, data"
  }
]
```

**Fields:**
- `name` (string, required): Human-readable name of the entry point.
- `kind` (string, required): `service`, `cli`, `library`, `worker`, `webhook`, etc.
- `path` (string, required): Repo-relative path to the main file or directory.
- `start` (string, optional): Command to run it locally (e.g., `make run-gateway`).
- `purpose` (string, required): One sentence: what does this do, where does it fit?

### `modules` — Module structure and purpose

Break the codebase into logical modules (packages, services, layers).

```json
"modules": [
  {
    "id": "auth",
    "path": "internal/auth/",
    "purpose": "JWT issuance/validation, session middleware, RBAC",
    "depends_on": ["store", "config"],
    "key_files": [
      "internal/auth/middleware.go",
      "internal/auth/jwt.go",
      "internal/auth/rbac.go"
    ]
  },
  {
    "id": "store",
    "path": "internal/store/",
    "purpose": "Postgres data access layer (sqlc-generated queries + repository pattern)",
    "depends_on": ["config"],
    "key_files": [
      "internal/store/db.go",
      "internal/store/queries.sql"
    ]
  }
]
```

**Fields:**
- `id` (string, required): Unique identifier within this repo (used in `depends_on`).
- `path` (string, required): Repo-relative directory path.
- `purpose` (string, required): What does this module do? What problem does it solve?
- `depends_on` (string[], optional): IDs of modules this depends on. Helps agents understand the dependency graph.
- `key_files` (string[], optional): Paths to the most important files in this module. Agents start here when exploring.

### `patterns` — Cross-cutting concerns and conventions

Define where patterns and practices are implemented, so agents know where to look and what to follow.

```json
"patterns": [
  {
    "concern": "auth",
    "defined_in": "internal/auth/middleware.go",
    "applied_via": "router.Use(auth.Require)",
    "tags": ["security"],
    "note": "All authenticated routes wrap the handler with auth.Require"
  },
  {
    "concern": "error-handling",
    "defined_in": "internal/errs/errs.go",
    "convention": "Wrap errors with errs.Wrap(); never return raw errors to clients",
    "tags": ["error-handling"]
  },
  {
    "concern": "logging",
    "defined_in": "internal/log/log.go",
    "convention": "Always use structured logging: log.From(ctx).Info(...)",
    "tags": ["observability"]
  }
]
```

**Fields:**
- `concern` (string, required): Name of the cross-cutting concern (auth, logging, error-handling, caching, etc.).
- `defined_in` (string, required): Repo-relative path where the pattern is defined.
- `applied_via` (string, optional): How/where the pattern is used (e.g., middleware registration, import convention).
- `convention` (string, optional): Human-readable description of the pattern/practice.
- `tags` (string[], optional): Labels for grouping (`security`, `observability`, `performance`, etc.).
- `note` (string, optional): Additional context or warnings.

### `key_files` — Important files by category

A fast lookup for "where is X?"

```json
"key_files": {
  "config": ["config/default.yaml", "internal/config/config.go"],
  "migrations": ["db/migrations/"],
  "api_schema": ["proto/widget/v1/", "openapi.yaml"],
  "ci": [".github/workflows/ci.yml"],
  "build": ["Makefile", "go.mod"],
  "secrets": [".env.example"]
}
```

**Values are repo-relative paths; keys are semantic categories** (you define the categories that make sense for your repo).

### `features` — Feature flow: intent-to-code paths

**The highest-value section.** For a feature or user-facing capability, trace the path through the code.

```json
"features": [
  {
    "name": "checkout",
    "description": "User completes purchase and places an order",
    "flow": [
      { "step": "entry", "file": "cmd/gateway/routes.go", "fn": "registerCheckout" },
      { "step": "handler", "file": "internal/checkout/handler.go", "fn": "handleCheckout" },
      { "step": "business-logic", "file": "internal/checkout/service.go", "fn": "CompleteCheckout" },
      { "step": "persistence", "file": "internal/store/orders.go", "fn": "CreateOrder" }
    ],
    "tests": [
      "internal/checkout/service_test.go",
      "test/integration/checkout_test.go"
    ],
    "tags": ["customer-facing", "critical"]
  }
]
```

**Fields:**
- `name` (string, required): Name of the feature.
- `description` (string, required): What does it do?
- `flow` (object[], required): Sequence of steps through the code.
  - `step` (string): Label (entry, handler, logic, persistence, etc.).
  - `file` (string): Repo-relative path.
  - `fn` (string, optional): Function/symbol name (stable anchor).
- `tests` (string[], optional): Paths to test files covering this feature.
- `tags` (string[], optional): Labels (e.g., `customer-facing`, `critical`, `performance-sensitive`).

### `testing` — Test structure and conventions

```json
"testing": {
  "unit": "tests/ directory; each package has *_test.go",
  "integration": "test/integration/ (requires docker-compose.test.yml)",
  "fixtures": "test/fixtures/ (sample data, mocked services)",
  "run": "make test && make test-integration"
}
```

### `dependencies` — Notable third-party dependencies

Not a full dependency tree (let package managers handle that), but a curated list of important/non-obvious deps.

```json
"dependencies": [
  {
    "name": "sqlc",
    "why": "Compile-time SQL-to-Go codegen; edit .sql files not Go"
  },
  {
    "name": "casbin",
    "why": "RBAC policy engine; policies defined in config/rbac.csv"
  }
]
```

## Maintenance Strategy

### Generated vs. Hand-written

Split the file by volatility:

| Section | Source | Rationale |
|---|---|---|
| `entrypoints[].path`, `modules[].path`, `modules[].depends_on`, `key_files` | **Generated** | Derivable from code; high-churn, never hand-code |
| `entrypoints[].purpose`, `modules[].purpose`, `patterns`, `features`, `dependencies[].why` | **Hand-written** | The "why" — only humans know intent |

### CI Validation

1. **Schema validation:** CI runs `jsonschema` to reject invalid `.repospec.json`.
2. **Freshness check:** A `gen-repospec` tool regenerates the mechanical sections. CI fails if there's a diff (forces author to commit changes).
3. **Reference validation:** CI checks that every `path` referenced in `.repospec.json` still exists; warn if a path is stale.

### Regeneration Workflow

```bash
# Regenerate mechanical sections
$ ./tools/gen-repospec --output .repospec.json

# Validate the result
$ jsonschema -i .repospec.json schema/schema.json

# Commit if fresh
$ git add .repospec.json && git commit -m "chore: regenerate .repospec.json"
```

### Self-Healing

Instruct agents: *"If the `.repospec.json` contradicts what you find in the code, fix it in the same PR."* This turns every agent session into maintenance; the index stays fresher than if you had to maintain it manually.

## Examples

See `examples/` directory for `.repospec.json` files for:
- Go microservice
- Node.js web app
- Python monorepo
- Rust library

## JSON Schema

See `schema/schema.json` for the formal JSON Schema definition. Use it to validate `.repospec.json` files in CI and tooling.

## Tooling

### Validator

```bash
$ tools/validate .repospec.json
✓ Schema valid
✓ All file paths exist
⚠ Pattern 'caching' references internal/cache/cache.go:L42, but file not found (stale)
```

### Generator (Reference Implementation)

```bash
$ tools/gen-repospec --source . --output .repospec.json --hand-written-sections-input .repospec.json
```

Merges generated sections (paths, imports, dependencies) with existing hand-written sections (purpose, patterns, features).

## FAQ

### Why not use LSP / SCIP / Bazel for this?

LSP finds symbols; Bazel describes the build graph; repospec describes *intent and architecture at the module level*. They're complementary.

### How do I keep `.repospec.json` fresh?

Split the file: auto-generate paths/imports, hand-write purpose/rationale. CI checks for freshness. Agents fix contradictions.

### Should this replace code comments?

No. Comments explain *how code works*; repospec explains *where code lives and why*. They serve different audiences (readers of the code vs. readers seeking the code).

### Can I use this for a monorepo?

Yes. Define `modules` for each service/package. Each module can have its own `entrypoints` and `features`.

### Is this standardized?

It's an open-source format with a reference schema and implementations. Adoption is voluntary; no central registry or governance (yet).

## Contributing

This is a living standard. Feedback, use cases, and tooling contributions are welcome. Open an issue or PR.

## License

MIT
