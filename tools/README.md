# repospec Benchmark Tool

Measure the impact of `.repospec.json` on agent code navigation. Two agents answer the
same 8 code-finding tasks against a target repo — one **with** `.repospec.json` in
context, one **without** — and the tool reports the difference.

## Quick Start

```bash
# OAuth (Claude.ai subscription)
export CLAUDE_CODE_OAUTH_TOKEN=...      # or ANTHROPIC_AUTH_TOKEN
./repospec_benchmark.sh /path/to/repo --auth-method oauth

# or API key
export ANTHROPIC_API_KEY=sk-ant-...
./repospec_benchmark.sh /path/to/repo
```

The wrapper just execs `python3 repospec_benchmark.py "$@"`; you can call the Python
script directly too.

## What it does

1. Generates a `.repospec.json` for the target repo (using `PROMPT.md`).
2. Creates 8 code-finding test tasks (entry points, modules, auth pattern, feature flow, …).
3. Runs two agents in parallel — WITH and WITHOUT the metadata in context.
4. Writes a timestamped results directory and a `RESULTS.md` summary.

## Output

Each run produces a directory under `--output-dir` (default `./repospec-benchmark`):

| File | Contents |
|------|----------|
| `RESULTS.md` | Summary metrics (see below) |
| `generated.repospec.json` | The metadata the tool generated for the repo |
| `agent_with_repospec.log` | Full response WITH `.repospec.json` |
| `agent_without_repospec.log` | Full response WITHOUT `.repospec.json` |

## Metrics

| Metric | Meaning |
|--------|---------|
| **Path accuracy** | Of the file paths the agent cites, how many actually exist (valid / total). The headline signal. |
| Valid / invalid path references | Counts of real vs hallucinated paths cited. |
| Response length / words / lines | Depth of the answer. |
| Input / output tokens | Token cost (loading the spec adds input tokens). |
| Total / per-task duration | Wall-clock time per run and divided across the 8 tasks. |
| Tasks mentioned | How many of the 8 tasks the response addresses. |

> **Scope:** this is a *pure-navigation* benchmark — the agent reasons over the repo
> context it's given; it does not execute live tools. Path accuracy is therefore the
> most reliable signal. Planned upgrades (ground-truth task correctness, real tool-call
> logging, per-task breakdown, hallucination + cost metrics) are tracked in
> [BENCHMARK_ROADMAP.md](BENCHMARK_ROADMAP.md).

## Latest results (Ghost, 7,181 files)

4 OAuth runs against the [Ghost](https://github.com/TryGhost/Ghost) CMS repo:

| Run | Path accuracy WITH | Path accuracy WITHOUT | Valid paths WITH / WITHOUT |
|-----|-------------------:|----------------------:|---------------------------:|
| 1 | 34.2% | 0.0% | 25 / 0 |
| 2 | 17.4% | 1.5% | 8 / 1 |
| 3 | 20.0% | 1.5% | 7 / 1 |
| 4 | 22.6% | 2.4% | 7 / 1 |
| **avg** | **~23.6%** | **~1.4%** | **~12 / ~1** |

Agents WITH `.repospec.json` cited valid file paths ~16× more often and hallucinated
fewer paths every run. Both sides addressed all 8 tasks. Cost of the map: +2.4k–3k input
tokens per run.

## Options

```
--output-dir DIR       Output directory for results (default: ./repospec-benchmark)
--timeout SECS         Timeout per agent run (default: 300)
--auth-method METHOD   api_key | oauth | both (default: api_key)
--help                 Show help
```

`--auth-method both` runs the full benchmark once per auth method and writes separate
`RESULTS-api_key.md` / `RESULTS-oauth.md` files.

## Authentication

| Method | Env var | Notes |
|--------|---------|-------|
| `api_key` | `ANTHROPIC_API_KEY` | Standard Anthropic API key (`sk-ant-…`). |
| `oauth` | `CLAUDE_CODE_OAUTH_TOKEN` (or `ANTHROPIC_AUTH_TOKEN`) | Claude.ai subscription token. |
| `both` | both of the above | Runs each in turn for direct comparison. |

## How agents discover `.repospec.json`

Both benchmark agents are instructed to look for `.repospec.json` at the repo root,
validate it (`"schema": "repospec/v1"`), use it as a map, and verify details against the
real code — mirroring how a real agent would discover it in the wild. See
[../AGENT_DISCOVERY_GUIDE.md](../AGENT_DISCOVERY_GUIDE.md) for the full guidance.

## Interpreting a run

- **WITH** should reference the metadata and give organized, focused, path-accurate answers.
- **WITHOUT** is more exploratory and cites more paths that don't exist.
- If results are unclear, try a larger/more complex repo or tighten the generated spec.

## Prerequisites

- Python 3.8+
- An Anthropic credential (API key or OAuth token, above)
- Read access to the target repository
