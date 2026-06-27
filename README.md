# repospec

**A metadata standard that lets AI agents understand a repository by reading one file instead of crawling thousands.**

An agent drops a single `.repospec.json` at the repo root and gets a curated index of entry points, modules, patterns, features, and conventions — a map of *intent and architecture*, not just symbols.

---

## What

`.repospec.json` is a small, schema-validated JSON file at the repository root. It describes a codebase at the **module/feature** level:

| Section | Answers |
|---------|---------|
| `entrypoints` | Where does execution start? (services, CLIs, workers) |
| `modules` | What are the logical pieces and how do they depend on each other? |
| `patterns` | What are the cross-cutting conventions? (auth, logging, errors) |
| `key_files` | Where are config, migrations, CI, API schemas? |
| `features` | How does a user-facing flow move through the code, end to end? |
| `testing` | How are tests organized and run? |
| `infrastructure` | What are the CI/CD pipelines and infrastructure-as-code (Terraform, CloudFormation, deploy automation)? |
| `dependencies` | Which third-party libs matter, and why? |

All paths are repo-relative; all references use stable anchors (function names, not line numbers).

## Why

AI agents waste time and tokens on **rediscovery** every session — searching for entry points, inferring module structure, hunting for the code behind a feature, and re-deriving architectural decisions. They also **hallucinate file paths** that don't exist.

Existing tools solve adjacent problems: LSP/SCIP find symbols, Bazel/Nx describe the build. repospec fills the gap at the **intent level**, giving an agent a trustworthy orientation map before it touches a single file.

### Benchmark: does it actually help?

We ran the bundled benchmark on [**Ghost**](https://github.com/TryGhost/Ghost) (7,181 files, 66.5 MB, JS/TS) — two agents answer the same 8 code-navigation tasks, one *with* `.repospec.json` in context and one *without*. Across 4 runs:

| Metric | WITH `.repospec.json` | WITHOUT | Result |
|--------|----------------------|---------|--------|
| **Valid file-path references** (accuracy) | ~23% avg (peak 34%) | ~1.4% avg | **~16× more accurate** |
| Valid paths cited (per run) | 7–25 | 0–1 | far more real paths |
| Invalid/hallucinated paths | consistently lower | higher every run | fewer hallucinations |
| Tasks addressed | 8 / 8 | 8 / 8 | both cover the work |
| Extra input tokens to load the spec | +2.4k–3k | — | the cost of the map |

**Takeaway:** an agent given `.repospec.json` points at *real* files an order of magnitude more often and hallucinates fewer paths. The trade-off is a few thousand input tokens to load the map — cheap next to the cost of chasing wrong paths.

> Numbers come from the reference benchmark in [`tools/`](tools/README.md). It's a pure-navigation benchmark (no live tool execution yet) — see the [roadmap](tools/BENCHMARK_ROADMAP.md) for planned task-correctness and tool-call metrics.

## How

1. **Generate** a `.repospec.json` for your repo — feed [PROMPT.md](PROMPT.md) to an agent (Claude, Copilot, etc.) pointed at your codebase.
2. **Validate** it against the schema:
   ```bash
   make validate          # validates ./.repospec.json against schema.json
   make examples          # validates everything in examples/
   ```
3. **Commit** it to the repo root so every agent and teammate benefits.
4. **Maintain** it — auto-generate the mechanical sections (paths, imports) in CI; hand-write the rationale once and update it as the code evolves.

Agents discovering a `.repospec.json` for the first time should read **[AGENT_DISCOVERY_GUIDE.md](AGENT_DISCOVERY_GUIDE.md)** — how to find, validate, use, and sanity-check the metadata.

## Example

```json
{
  "schema": "repospec/v1",
  "name": "checkout-service",
  "summary": "Payment processing and order management",

  "entrypoints": [
    { "name": "api-gateway", "kind": "service", "path": "cmd/gateway/main.go",
      "purpose": "HTTP edge; routes to internal services" }
  ],

  "modules": [
    { "id": "checkout", "path": "internal/checkout/",
      "purpose": "Orchestrates the checkout flow", "depends_on": ["store", "payments"] }
  ],

  "features": [
    { "name": "place-order", "description": "User completes purchase",
      "flow": [
        { "step": "entry",       "file": "cmd/gateway/routes.go",     "fn": "registerCheckout" },
        { "step": "handler",     "file": "internal/checkout/handler.go", "fn": "handleCheckout" },
        { "step": "logic",       "file": "internal/checkout/service.go", "fn": "CompleteOrder" },
        { "step": "persistence", "file": "internal/store/orders.go",   "fn": "CreateOrder" }
      ] }
  ]
}
```

From this one file an agent knows how to run the service, which modules exist and what they do, how a feature flows through the code, and where to start exploring.

## Repository layout

| Path | What it is |
|------|------------|
| [SPEC.md](SPEC.md) | Complete format definition with examples and the maintenance strategy |
| [schema.json](schema.json) | JSON Schema — validate any `.repospec.json` against it |
| [PROMPT.md](PROMPT.md) | Prompts to generate (and discover) `.repospec.json` |
| [AGENT_DISCOVERY_GUIDE.md](AGENT_DISCOVERY_GUIDE.md) | How agents find, interpret, and verify the metadata |
| [`examples/`](examples/) | Sample `.repospec.json` files (Go service, Node app) |
| [`tools/`](tools/README.md) | Reference benchmark that measures the impact on agent navigation |
| [.repospec.json](.repospec.json) | This repo's own metadata (dogfooding) |

## Maintenance strategy

- **Generated sections** (paths, imports): auto-generated from code, regenerated in CI.
- **Hand-written sections** (purpose, rationale): written once, updated as the codebase evolves.
- **CI validation**: schema validation + freshness checks on every commit.
- **Self-healing**: agents fix contradictions they discover and flag stale entries.

See [SPEC.md](SPEC.md#maintenance-strategy) for details.

## FAQ

**Why not just use LSP / SCIP / Bazel?**
LSP finds symbols; Bazel describes the build. repospec describes *intent and architecture at the module level*. They're complementary.

**How do I keep `.repospec.json` up to date?**
Split the file: auto-generate paths/imports, hand-write purpose/rationale, and let CI check freshness.

**Is this standardized?**
It's an open-source format with a reference schema. Adoption is voluntary; no central registry (yet).

**Can I use this for a monorepo?**
Yes. Define `modules` per service/package; each can have its own `entrypoints` and `features`.

## Contributing

Feedback, use cases, and implementations are welcome. Open an issue or PR.

## License

MIT
