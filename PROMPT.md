# Agent Prompt: Generate `.repospec.json` for a Repository

Use this prompt to instruct an AI agent to analyze your repository and generate a `.repospec.json` file.

---

## Prompt Template

```
You are generating a `.repospec.json` file for a repository.

**Context:**
- `.repospec.json` is a standard metadata format that helps AI agents understand repository structure and navigate code efficiently.
- Read the specification at: https://github.com/LightHeart-Ventures/repospec/blob/main/SPEC.md
- Reference the JSON Schema at: https://github.com/LightHeart-Ventures/repospec/blob/main/schema.json
- Check example files: https://github.com/LightHeart-Ventures/repospec/tree/main/examples

**Your task:**
1. Analyze the repository structure, entry points, modules, and key files.
2. Generate a `.repospec.json` file at the repository root.
3. Validate the JSON against the schema.

**Guidelines:**

### `entrypoints` (Required)
- Identify all entry points: services, CLIs, workers, webhooks, lambdas, etc.
- For each, specify:
  - `name`: Human-readable name
  - `kind`: Type of entry point (service, cli, library, worker, webhook, lambda, batch, middleware, other)
  - `path`: Repo-relative path to the main file or directory
  - `purpose`: One sentence describing what it does and where it fits
  - `start` (optional): Command to run it locally (e.g., `make run`, `npm start`, `cargo run`)

### `modules` (Recommended)
- Break the codebase into logical modules or packages.
- For each module, specify:
  - `id`: Unique identifier (used in `depends_on`)
  - `path`: Repo-relative directory path
  - `purpose`: What problem does this module solve?
  - `depends_on`: IDs of modules it depends on
  - `key_files`: Paths to 2–5 most important files

### `patterns` (Recommended)
- Document cross-cutting concerns: auth, logging, error-handling, caching, etc.
- For each pattern:
  - `concern`: Name of the concern
  - `defined_in`: Path to where it's defined
  - `applied_via` (optional): How/where it's used
  - `convention` (optional): Description of the practice
  - `tags`: Labels for grouping (security, observability, performance, etc.)

### `key_files` (Recommended)
- Map semantic categories to important files:
  - `config`: Configuration files
  - `migrations`: Database migrations
  - `api_schema`: API definitions (OpenAPI, protobuf, GraphQL, etc.)
  - `ci`: CI/CD workflow files
  - `build`: Build/package files (Makefile, package.json, go.mod, etc.)
  - `docker`: Docker/container files
  - `tests`: Test configuration (if not co-located with source)

### `features` (Optional but high-value)
- For 2–5 key user-facing features, trace the code flow:
  - `name`: Feature name
  - `description`: What does it do?
  - `flow`: Array of steps through the code (entry → handler → logic → persistence)
    - Each step: `step` (label), `file` (path), `fn` (function/symbol name, stable anchor)
  - `tests`: Paths to test files covering this feature
  - `tags`: Labels (customer-facing, critical, performance-sensitive, etc.)

### `testing` (Recommended)
- Document how tests are organized:
  - `unit`: Where unit tests live and how they're structured
  - `integration`: Where integration tests live
  - `fixtures`: Where test data and mocks live
  - `run`: Command to run all tests

### `dependencies` (Optional)
- For 3–5 important third-party dependencies, explain why:
  - `name`: Package/library name
  - `why`: Role and importance (e.g., "sqlc: SQL→Go codegen; edit .sql not Go")

### `goals` (Optional)
- List high-level project goals

---

**Output:**
- A valid `.repospec.json` file ready to commit
- Validate against the schema (use `jsonschema` or any JSON Schema validator)
- Ensure all paths exist and are repo-relative
- Ensure all function names (`fn` fields) are accurate and stable (won't change with minor refactors)

**Notes:**
- Use stable anchors (function/symbol names) instead of line numbers — line numbers rot immediately.
- If you're unsure about a module's purpose or dependency, include a note asking the repo owner to review.
- Keep descriptions concise (one sentence per purpose, one line per convention).
- Include only the most important files in `key_files` and `features` — agents should be able to explore from there.

Generate the `.repospec.json` now.
```

---

## How to Use

### Option 1: Interactive with an Agent (e.g., Claude Code, GitHub Copilot)

1. Copy the prompt template above
2. Share it with your agent along with repo context (file tree, README, key source files)
3. Ask the agent to generate `.repospec.json`
4. Review and refine

### Option 2: With `aish` (Anthropic's CLI)

```bash
# If you have aish installed, you can pipe the prompt:
cat PROMPT.md | aish "Generate .repospec.json for my repo at [REPO_PATH]"
```

### Option 3: Programmatic (for Tooling)

Embed this prompt in a script/tool that:
1. Passes the prompt to an agent API (OpenAI, Anthropic, etc.)
2. Includes repo metadata (file tree, package.json, go.mod, etc.) in the context
3. Parses and validates the generated `.repospec.json`
4. Writes it to the repo root

---

## Tips for Best Results

- **Provide repo context:** Share the repo structure, key files, and README with the agent
- **Clarify ambiguities:** If module boundaries or purposes are unclear, ask the agent to ask clarifying questions
- **Iterate:** First pass may miss details; refine based on feedback
- **Validate:** Always validate the generated `.repospec.json` against the schema before committing
- **Review manually:** Check that paths exist, function names are accurate, and descriptions are correct

---

## Example Session

**Agent prompt:**
```
Here's my repository structure:

```
src/
  main.go
  go.mod
internal/
  auth/
    jwt.go
    middleware.go
  checkout/
    handler.go
    service.go
  store/
    db.go
    queries.sql
cmd/
  gateway/
    main.go
  migrate/
    main.go
test/
  integration/
    checkout_test.go
```

My README says: "A Go microservice for payment processing. HTTP gateway routes to internal services."

Use the repospec prompt to generate `.repospec.json` for this repo.
```

**Agent generates:**
```json
{
  "schema": "repospec/v1",
  "name": "payment-service",
  "summary": "Go microservice for payment processing with HTTP gateway and gRPC services",
  "entrypoints": [
    {
      "name": "api-gateway",
      "kind": "service",
      "path": "cmd/gateway/main.go",
      "purpose": "HTTP gateway; routes to internal checkout and payment services"
    },
    {
      "name": "migrate",
      "kind": "cli",
      "path": "cmd/migrate/main.go",
      "purpose": "Database migration tool"
    }
  ],
  ...
}
```

---

## Resources

- [Full Specification](SPEC.md)
- [JSON Schema](schema.json)
- [Examples](examples/)
- [GitHub Repository](https://github.com/LightHeart-Ventures/repospec)

---

## Feedback

If the prompt doesn't generate good results for your repo type, please [open an issue](https://github.com/LightHeart-Ventures/repospec/issues) with:
- Your repo structure (file tree)
- What the agent missed or got wrong
- Suggestions for improving the prompt

Help us make `.repospec.json` better for your use case.
