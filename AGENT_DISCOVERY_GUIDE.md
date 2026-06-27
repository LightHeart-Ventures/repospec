# Agent Discovery & Usage Guide for `.repospec.json`

This guide explains how AI agents can discover, understand, and use `.repospec.json` files to navigate repositories more effectively—even if they've never encountered repospec before.

---

## Table of Contents

1. [Discovery: How to Find `.repospec.json`](#discovery-how-to-find-repospecjson)
2. [Understanding: What Each Section Means](#understanding-what-each-section-means)
3. [Integration: How to Use It in Your Reasoning](#integration-how-to-use-it-in-your-reasoning)
4. [Verification: Checking Correctness](#verification-checking-correctness)
5. [Fallback: What to Do Without `.repospec.json`](#fallback-what-to-do-without-repospecjson)

---

## Discovery: How to Find `.repospec.json`

### Step 1: Check the Repository Root

When you start analyzing a repository:

```
your-task-repo/
├── .repospec.json          ← LOOK HERE FIRST
├── .git/
├── README.md
├── package.json
└── src/
```

**Action:** Always look for `.repospec.json` at the repository root before doing anything else.

### Step 2: Interpret the Presence

- **File exists:** The repository owner has curated metadata. USE IT. It's a signal that this repo wants you to understand its structure efficiently.
- **File missing:** The repository either doesn't use repospec, or it's very new. Fall back to manual exploration (see [Fallback](#fallback-what-to-do-without-repospecjson)).

### Step 3: Validate It's Real Repospec

Once found, check the first line:

```json
{
  "schema": "repospec/v1",
  ...
}
```

If you see `"schema": "repospec/v1"`, this is a standard repospec file. Proceed with confidence.

If the schema field is missing or different, treat it as a non-standard metadata file and ignore it (don't assume its format).

---

## Understanding: What Each Section Means

### `entrypoints` — Where Code Execution Starts

**Purpose:** Tells you every way code in this repo runs (services, CLIs, workers, webhooks, etc.).

**Example:**
```json
{
  "entrypoints": [
    {
      "name": "api-gateway",
      "kind": "service",
      "path": "cmd/gateway/main.go",
      "purpose": "HTTP edge; routes requests to internal services"
    },
    {
      "name": "cli",
      "kind": "cli",
      "path": "cmd/cli/main.go",
      "purpose": "Command-line interface for admin tasks"
    }
  ]
}
```

**How to Use:**
- If someone asks "How does this code run?" → Read `entrypoints`
- To understand code flow → Start at an entry point and follow the modules
- To find where a feature begins → Look for the entry point that handles user input for that feature

### `modules` — Logical Pieces of the Codebase

**Purpose:** Breaks the codebase into understandable chunks, each with a clear job.

**Example:**
```json
{
  "modules": [
    {
      "id": "auth",
      "path": "internal/auth/",
      "purpose": "Handles user authentication (JWT tokens, OAuth flows)",
      "depends_on": ["db"],
      "key_files": [
        "internal/auth/jwt.go",
        "internal/auth/middleware.go"
      ]
    },
    {
      "id": "checkout",
      "path": "internal/checkout/",
      "purpose": "Orchestrates the purchase flow",
      "depends_on": ["auth", "payments", "db"],
      "key_files": [
        "internal/checkout/handler.go",
        "internal/checkout/service.go"
      ]
    }
  ]
}
```

**How to Use:**
- To understand architecture → Read the module list and their dependencies
- To find code related to a feature → Look at which modules are involved (e.g., checkout feature uses `checkout`, `auth`, `payments` modules)
- To avoid reinventing the wheel → Check if a module already does what you need
- To understand coupling → Look at `depends_on` to see which modules rely on each other

### `patterns` — Cross-Cutting Concerns

**Purpose:** Documents shared practices (authentication, logging, error handling, caching) that appear across multiple modules.

**Example:**
```json
{
  "patterns": [
    {
      "concern": "authentication",
      "defined_in": "internal/auth/middleware.go",
      "applied_via": "Wrapped on every HTTP handler via `requireAuth()`",
      "convention": "Add `requireAuth()` wrapper to protected routes",
      "tags": ["security"]
    },
    {
      "concern": "error-handling",
      "defined_in": "internal/errors/handler.go",
      "applied_via": "All handlers catch panics and format errors via `formatError()`",
      "convention": "Don't return raw errors; wrap with `formatError(err)`",
      "tags": ["reliability"]
    }
  ]
}
```

**How to Use:**
- Before writing new code → Check `patterns` to see how similar tasks are already done
- To understand conventions → If you see `requireAuth()` in code, look up the auth pattern
- To maintain consistency → Follow the same pattern when adding similar code
- To find security/reliability practices → Check patterns tagged with `security`, `reliability`, etc.

### `features` — Feature Flows Through Code

**Purpose:** Traces how user-facing features flow through the code, from entry point to database.

**Example:**
```json
{
  "features": [
    {
      "name": "place-order",
      "description": "User completes a purchase",
      "flow": [
        {
          "step": "entry",
          "file": "cmd/gateway/routes.go",
          "fn": "registerCheckout"
        },
        {
          "step": "handler",
          "file": "internal/checkout/handler.go",
          "fn": "HandleCheckout"
        },
        {
          "step": "logic",
          "file": "internal/checkout/service.go",
          "fn": "CompleteOrder"
        },
        {
          "step": "persistence",
          "file": "internal/store/orders.go",
          "fn": "CreateOrder"
        }
      ],
      "tests": [
        "test/checkout_test.go"
      ]
    }
  ]
}
```

**How to Use:**
- To trace a feature end-to-end → Follow the `flow` array step by step
- To find tests for a feature → Look at the `tests` field
- To understand critical paths → Features tagged "critical" or "customer-facing" should get special attention
- To estimate changes → Count the number of files/functions in the flow to understand change scope

### `key_files` — Important Files by Category

**Purpose:** Maps semantic categories (config, migrations, API schema, etc.) to actual files.

**Example:**
```json
{
  "key_files": {
    "config": ["config.yaml", ".env.example"],
    "migrations": ["db/migrations/"],
    "api_schema": ["api/openapi.yaml"],
    "ci": [".github/workflows/test.yml", ".github/workflows/deploy.yml"],
    "build": ["Makefile", "go.mod"],
    "docker": ["Dockerfile", "docker-compose.yml"],
    "tests": ["test/fixtures/"]
  }
}
```

**How to Use:**
- To understand deployment → Look at `ci` and `docker`
- To see what's configurable → Check `config` files
- To understand data changes → Look at `migrations`
- To integrate with this API → Check `api_schema`

### `testing` — How Tests Are Organized

**Purpose:** Explains the test strategy and structure.

**Example:**
```json
{
  "testing": {
    "unit": {
      "location": "*/test.go or */test/* directories",
      "command": "go test ./..."
    },
    "integration": {
      "location": "test/integration/",
      "command": "go test -tags=integration ./test/integration"
    },
    "fixtures": {
      "location": "test/fixtures/",
      "description": "Seed data and mock objects"
    }
  }
}
```

**How to Use:**
- To write new tests → Follow the same structure and naming convention
- To run tests → Use the specified command
- To find test data → Look in `fixtures`
- To add integration tests → See where they live and follow that pattern

### `dependencies` — Why External Libraries Matter

**Purpose:** Explains important third-party libraries and why they're used.

**Example:**
```json
{
  "dependencies": [
    {
      "name": "sqlc",
      "why": "Type-safe SQL codegen. Edit .sql files, not generated Go. Keeps queries in sync with schema."
    },
    {
      "name": "chi",
      "why": "HTTP router. All routes defined in cmd/gateway/routes.go."
    }
  ]
}
```

**How to Use:**
- Before changing SQL → Check if sqlc is used; if so, edit `.sql` files, not Go
- To understand design choices → See why each dependency was chosen
- To avoid duplicate work → Check if a library already does what you're implementing

---

## Integration: How to Use It in Your Reasoning

### When Starting to Analyze a Repo

**Before** exploring files randomly:

1. ✅ Read `.repospec.json` (entire file, takes 2 minutes)
2. ✅ Identify the entry points
3. ✅ Understand the module structure
4. ✅ Note key files and patterns
5. ✅ Then open specific files based on this map

**Example flow:**
> User: "How does authentication work in this repo?"
>
> Agent: 
> 1. Read `.repospec.json` 
> 2. Find pattern: `"concern": "authentication", "defined_in": "internal/auth/middleware.go"`
> 3. Open that file and understand the implementation
> 4. No need to explore 100 files—I know exactly where auth is

### When Writing Code

**Before implementing something:**

1. Check if a module already does it (via `modules` section)
2. Follow the pattern documented in `patterns` section
3. Find similar features in `features` section and mirror their structure
4. Use `key_files` to find configuration / test data locations

### When Debugging

**If something is broken:**

1. Find the entry point from `entrypoints`
2. Follow the feature flow from `features`
3. Identify which module is failing via `modules` dependencies
4. Check the pattern for error handling in `patterns`
5. Run tests from `testing` section

### When Estimating Impact

**Before making a change:**

1. Use `features` to understand all code paths affected
2. Use `modules` + `depends_on` to find ripple effects
3. Check `testing` to know what tests to run
4. Use `patterns` to understand conventions you must maintain

---

## Verification: Checking Correctness

### Trust but Verify

`.repospec.json` is metadata written by humans. It can become stale. If something doesn't match reality:

**Red Flags:**
- A file path in `.repospec.json` doesn't exist → outdated metadata
- A module name is mentioned but not in `modules` section → incomplete
- A function name (`fn` field) doesn't exist in the specified file → file moved
- Dependencies listed are circular (A → B → A) → likely an error

**What to Do:**
- If the file is slightly outdated → note the inconsistency and continue
- If the file is heavily stale → fall back to manual exploration
- Better yet → alert the repo owner to update `.repospec.json` (it's a solvable problem)

### Spotting Good `.repospec.json` Files

✅ **Good signs:**
- Paths all exist and are repo-relative
- Function names are from actual code (verify with a quick file read)
- Dependencies form a reasonable DAG (no cycles)
- Descriptions are specific and actionable
- Schema version is current (`repospec/v1`)

❌ **Bad signs:**
- Paths with absolute or Windows paths
- Function names like `line 42` or "the main function"
- Circular dependencies
- Generic descriptions ("handles stuff")
- Missing schema version

---

## Fallback: What to Do Without `.repospec.json`

If a repository doesn't have `.repospec.json`:

### Step 1: Check for Alternatives

Some repos use similar metadata instead:

```
├── .repospec.json        ← repospec (ideal)
├── architecture.md       ← hand-written docs (good, but stale quickly)
├── mkdocs/              ← structured docs (check here)
├── ARCHITECTURE.md      ← monorepo-specific guide (common in large projects)
├── docs/structure.md    ← buried docs (better than nothing)
└── README.md            ← usually describes the project (read this first)
```

**Action:** Look for architecture docs before diving into code.

### Step 2: Infer Structure Manually

If no metadata exists:

1. **Find entry points:**
   - Look for `main.go`, `index.js`, `__main__.py`, etc.
   - Check `cmd/`, `bin/`, `src/main/` directories
   - Look at package.json `scripts` / `Makefile` / `.github/workflows/`

2. **Identify modules:**
   - Look for directories under `src/`, `internal/`, `lib/`, `packages/`
   - Each directory with its own `__init__.py`, `go.mod`, or `package.json` is likely a module

3. **Find patterns:**
   - Search for common middleware/decorators: `auth`, `logger`, `error`, `cache`
   - Look in `middleware/`, `common/`, `lib/` directories

4. **Trace features:**
   - Pick a user-facing feature
   - Follow it from UI/API → handler → logic → database
   - Note every file and function in the flow

5. **Document as you go:**
   - Keep notes on what you discover
   - Consider creating `.repospec.json` for the repo owner

### Step 3: When to Ask for Help

If the repo is:
- **Small (<20 files):** Manual exploration is fine
- **Medium (20-100 files):** Start with README, README infer structure
- **Large (>100 files):** Manual exploration is risky; ask the owner or contributor for a structure guide

---

## Recommended Agent Workflow

Here's the optimal workflow for any agent analyzing a repository:

```
┌─────────────────────────────────────────────┐
│ 1. Repository Root Check                    │
│    Is .repospec.json present?               │
└────────────────┬──────────────────────────┘
                 │
         ┌───────┴────────┐
         │                │
        YES              NO
         │                │
         ▼                ▼
    ┌──────────┐  ┌──────────────┐
    │ Read &   │  │ Look for     │
    │ Validate │  │ alternatives │
    │ REPOSPEC │  │ (Arch docs)  │
    └────┬─────┘  └──────┬───────┘
         │               │
         └───────┬───────┘
                 │
                 ▼
         ┌──────────────────────┐
         │ Understand Structure │
         │ (Modules, Entry pts) │
         └──────────┬───────────┘
                    │
                    ▼
         ┌──────────────────────┐
         │ Find Relevant Code   │
         │ (Based on task)      │
         └──────────┬───────────┘
                    │
                    ▼
         ┌──────────────────────┐
         │ Verify Against Real  │
         │ Code (Spot Check)    │
         └──────────┬───────────┘
                    │
                    ▼
         ┌──────────────────────┐
         │ Proceed with Task    │
         │ (Code analysis,      │
         │  writing, debugging) │
         └──────────────────────┘
```

---

## Tool Integration Examples

### Example 1: A Tool That Reads `.repospec.json`

If you're building tools (linters, generators, etc.) that need repo structure:

```python
# Pseudo-code
def analyze_repo(repo_path):
    repospec_file = repo_path / ".repospec.json"
    
    if repospec_file.exists():
        spec = json.load(repospec_file)
        if spec.get("schema") == "repospec/v1":
            # Use the spec
            for module in spec["modules"]:
                process_module(module)
            return spec
    
    # Fallback: infer structure
    return infer_structure_manually(repo_path)
```

### Example 2: Prompting an Agent with `.repospec.json`

```
You are analyzing a repository to [TASK].

The repository owner has provided .repospec.json:

```json
{
  "schema": "repospec/v1",
  ...
}
```

Use this metadata as your guide:
1. Identify relevant modules from the modules section
2. Follow feature flows from the features section
3. Check patterns for conventions you should follow
4. Start with entry points if understanding overall structure

Then examine actual code files as needed to [TASK].
```

---

## Summary: Quick Reference

| Situation | What to Do |
|-----------|-----------|
| "How is this repo organized?" | Read `.repospec.json` entrypoints + modules |
| "Where does feature X live?" | Find X in features section, follow the flow |
| "How should I write X?" | Check patterns section for conventions |
| "What's this library for?" | Look in dependencies section |
| "Where are the tests?" | Check testing section |
| "How do I run this?" | Check entrypoints for `start` command |
| ".repospec.json is missing" | Look for alternatives, then infer manually |
| ".repospec.json seems wrong" | Verify a spot-check, use it anyway but be careful |

---

## Contributing

If you find that:
- **This guide is missing something** → open an issue
- **Your tool should read .repospec.json** → follow the examples above
- **You built a helpful tool** → share it so others can use it

See the main [README.md](README.md) for how to contribute.
