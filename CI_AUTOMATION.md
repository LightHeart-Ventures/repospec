# CI Automation: Keep `.repospec.json` Fresh on Commit

A self-contained prompt you can hand to an AI agent (Claude Code, Copilot, Cursor, `aish`, …)
to add a GitHub Actions workflow that **regenerates `.repospec.json` automatically — but only
when a commit meaningfully changes the repository's structure** (a "worthy commit"), never on
every trivial push.

> **One-liner to feed any agent** (pointed at your repo):
>
> ```
> Read https://raw.githubusercontent.com/LightHeart-Ventures/repospec/main/CI_AUTOMATION.md
> and follow it to add a GitHub Actions workflow that regenerates this repo's .repospec.json
> on worthy commits.
> ```

The companion prompts for *generating* and *maintaining* the file itself live in
[PROMPT.md](PROMPT.md) (Prompt 2: Generation, Prompt 3: Maintenance). This doc is the
fourth prompt in that family — **CI Automation** — kept separate so it has its own stable URL.

---

## The Prompt

Copy everything in the block below to your agent.

```
You are adding a GitHub Actions workflow that keeps this repository's `.repospec.json`
up to date automatically — but ONLY regenerates it when a commit meaningfully changes
the repository's structure (a "worthy commit"), not on every push.

Background on the format (read these):
- Spec:    https://raw.githubusercontent.com/LightHeart-Ventures/repospec/main/SPEC.md
- Schema:  https://raw.githubusercontent.com/LightHeart-Ventures/repospec/main/schema.json
- Prompts: https://raw.githubusercontent.com/LightHeart-Ventures/repospec/main/PROMPT.md
  (use "Prompt 2: Generation" to create from scratch and "Prompt 3: Maintenance"
   to update an existing file)

Create `.github/workflows/repospec.yml` that:

1. TRIGGER (coarse gate — cheap, runs in the runner itself):
   - on: push to the default branch only
   - paths-ignore the noise so the job never even starts for trivial commits:
       - `.repospec.json` itself (prevents self-trigger loops)
       - `**/*.md`, `docs/**`, `LICENSE`, images/assets
   - also support manual `workflow_dispatch` for on-demand regen.

2. WORTHINESS CHECK (fine gate — a job step that can short-circuit):
   Regenerate ONLY if the push is "worthy". Treat a commit as worthy when ANY of:
     - files were ADDED, DELETED, or RENAMED (structural change), or
     - changes touch entrypoints / build / config / CI / dependency manifests
       (e.g. package.json, go.mod, Cargo.toml, Makefile, Dockerfile, main.*), or
     - the number of changed source files exceeds a threshold (default 5).
   Provide explicit opt-in / opt-out commit-message markers that override the heuristic:
     - `[repospec]`  forces regeneration
     - `[skip repospec]` skips it
   Compute this from `git diff --name-status` of the push range and expose a boolean
   step output; gate the regenerate job on it.

3. LOOP PREVENTION:
   - Skip entirely if the head commit author is the bot (e.g. `github-actions[bot]`)
     or the message contains `[skip ci]` / `[repospec-bot]`.
   - The bot's own commit message must include `[skip ci]`.

4. REGENERATE:
   - Check out the repo, set up whatever AI CLI/agent you use (assume an
     `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` repository secret — reference it, never inline it).
   - Run the agent with the Generation/Maintenance prompt above to (re)build `.repospec.json`.
   - Validate the result against schema.json (fail the job if invalid).

5. PUBLISH — default to a PULL REQUEST, not a direct push to the default branch:
   - If `.repospec.json` changed, open/update a PR (e.g. peter-evans/create-pull-request)
     titled "chore: update .repospec.json" with the diff, so a human reviews structural
     metadata before it lands. (Offer a commented-out "commit directly with [skip ci]"
     variant for repos that prefer auto-commit.)
   - If nothing changed, exit cleanly.

Add least-privilege `permissions:` (contents: write, pull-requests: write only as needed),
pin action versions, and document the required secret in a comment at the top of the file.
Then run the workflow's worthiness logic locally against the last few commits to sanity-check it.
```

---

## Why It's Shaped This Way

| Concern | Mechanism | Why |
|---|---|---|
| Don't run on trivial commits | `paths-ignore` (docs, md, assets) | Cheapest gate — the job never spins up |
| "Worthy" = structural | `git diff --name-status` for add/delete/rename + manifest/entrypoint paths + file-count threshold | Repospec describes *structure*; a typo fix doesn't change the map |
| Human override | `[repospec]` / `[skip repospec]` markers | Heuristics are never perfect; give an escape hatch |
| Infinite loop | ignore `.repospec.json` path + skip bot author + bot commits with `[skip ci]` | The workflow's own commit must not re-trigger the workflow |
| Bad metadata landing silently | open a **PR** instead of pushing to default | Structural metadata deserves a glance before merge |
| Cost / secrets | reference `ANTHROPIC_API_KEY` secret, least-privilege `permissions` | LLM-in-CI costs money and needs a key; keep blast radius small |

The single biggest gotcha is the **self-trigger loop** — ignoring the `.repospec.json` path
*and* having the bot commit with `[skip ci]` are both needed (belt and suspenders).

---

## Reference Workflow (skeleton)

A starting point the agent can adapt. The AI-regeneration step is intentionally left as a
placeholder — swap in whichever agent CLI you use. The gating logic around it is the reusable part.

```yaml
# .github/workflows/repospec.yml
#
# Regenerates .repospec.json on "worthy" commits to the default branch.
# Requires repository secret: ANTHROPIC_API_KEY (or your agent's key).
name: repospec

on:
  push:
    branches: [main]
    paths-ignore:
      - '.repospec.json'
      - '**/*.md'
      - 'docs/**'
      - 'LICENSE'
      - '**/*.png'
      - '**/*.svg'
      - '**/*.jpg'
  workflow_dispatch:

permissions:
  contents: write
  pull-requests: write

concurrency:
  group: repospec-${{ github.ref }}
  cancel-in-progress: true

jobs:
  worthiness:
    runs-on: ubuntu-latest
    # Skip bot-authored commits and explicit skip markers.
    if: >-
      github.actor != 'github-actions[bot]' &&
      !contains(github.event.head_commit.message, '[skip repospec]') &&
      !contains(github.event.head_commit.message, '[repospec-bot]')
    outputs:
      worthy: ${{ steps.gate.outputs.worthy }}
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - id: gate
        shell: bash
        env:
          MSG: ${{ github.event.head_commit.message }}
        run: |
          set -euo pipefail
          # Forced / skipped via commit message.
          if printf '%s' "$MSG" | grep -qF '[repospec]'; then
            echo "worthy=true" >> "$GITHUB_OUTPUT"; exit 0
          fi
          if printf '%s' "$MSG" | grep -qF '[skip repospec]'; then
            echo "worthy=false" >> "$GITHUB_OUTPUT"; exit 0
          fi

          RANGE="${{ github.event.before }}...${{ github.sha }}"
          # First push to a branch has an all-zero "before"; fall back to last commit.
          if ! git rev-parse --quiet --verify "${{ github.event.before }}^{commit}" >/dev/null 2>&1; then
            RANGE="HEAD~1...HEAD"
          fi

          STATUS=$(git diff --name-status "$RANGE")
          echo "$STATUS"

          worthy=false
          # 1) Any add / delete / rename = structural change.
          if printf '%s\n' "$STATUS" | grep -qE '^(A|D|R)'; then
            worthy=true
          fi
          # 2) Touched a manifest / entrypoint / build / CI file.
          if printf '%s\n' "$STATUS" | grep -qiE '(^|/)(package\.json|go\.mod|go\.sum|Cargo\.toml|pyproject\.toml|requirements\.txt|Gemfile|pom\.xml|build\.gradle|Makefile|Dockerfile|main\.[a-z]+|\.github/workflows/)'; then
            worthy=true
          fi
          # 3) More than N changed files.
          THRESHOLD=5
          COUNT=$(printf '%s\n' "$STATUS" | sed '/^$/d' | wc -l)
          if [ "$COUNT" -gt "$THRESHOLD" ]; then
            worthy=true
          fi

          echo "worthy=$worthy" >> "$GITHUB_OUTPUT"
          echo "Decision: worthy=$worthy (changed files: $COUNT)"

  regenerate:
    needs: worthiness
    if: needs.worthiness.outputs.worthy == 'true'
    runs-on: ubuntu-latest
    permissions:
      contents: write
      pull-requests: write
    steps:
      - uses: actions/checkout@v4

      # --- Replace this block with your agent of choice ---------------------
      # Feed PROMPT.md "Prompt 2/3" to your AI CLI to (re)write .repospec.json.
      # The key is provided as a secret and never inlined.
      - name: Regenerate .repospec.json
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: |
          echo "TODO: run your AI agent here to regenerate .repospec.json"
          # e.g. some-agent-cli --prompt-url https://raw.githubusercontent.com/LightHeart-Ventures/repospec/main/PROMPT.md ...
      # ----------------------------------------------------------------------

      - name: Validate against schema
        run: |
          python -m pip install --quiet check-jsonschema
          curl -sSL https://raw.githubusercontent.com/LightHeart-Ventures/repospec/main/schema.json -o /tmp/repospec.schema.json
          check-jsonschema --schemafile /tmp/repospec.schema.json .repospec.json

      - name: Open PR if changed
        uses: peter-evans/create-pull-request@v6
        with:
          commit-message: "chore: update .repospec.json [skip ci]"
          title: "chore: update .repospec.json"
          body: |
            Automated structural-metadata refresh triggered by a worthy commit.
            Review the diff before merging.
          branch: chore/repospec-update
          add-paths: .repospec.json

      # --- Auto-commit variant (uncomment to push directly instead of a PR) -
      # - name: Commit directly
      #   run: |
      #     git config user.name  "github-actions[bot]"
      #     git config user.email "github-actions[bot]@users.noreply.github.com"
      #     git add .repospec.json
      #     git commit -m "chore: update .repospec.json [skip ci]" || exit 0
      #     git push
```

> Pin `peter-evans/create-pull-request` and `actions/checkout` to the latest releases your
> org allows, and confirm your default branch name (`main` vs `master`) in both the trigger
> and the `RANGE` fallback.

---

## Related

- [PROMPT.md](PROMPT.md) — generate & maintain `.repospec.json` (Prompts 1–3)
- [SPEC.md](SPEC.md) — the format definition and maintenance strategy
- [schema.json](schema.json) — validate any `.repospec.json`
- [AGENT_DISCOVERY_GUIDE.md](AGENT_DISCOVERY_GUIDE.md) — how agents find & use the file
