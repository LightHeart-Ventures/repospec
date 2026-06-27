# repospec Benchmark Tool

Measure the impact of `.repospec.json` on agent code navigation.

## Quick Start

```bash
./repospec_benchmark.sh /path/to/repo
```

This tool:
1. Generates `.repospec.json` for your repository using Claude
2. Creates 8 code-finding test tasks
3. Runs two agents: one WITH `.repospec.json`, one without
4. Compares results (task completion, response depth, accuracy)

## Prerequisites

- Python 3.7+
- `claude` CLI installed: `pip install anthropic-cli`
- `curl` (for fetching PROMPT.md)
- Read access to the target repository

## Output

Results are saved to a timestamped directory with:

- **`generated.repospec.json`** — Claude-generated metadata
- **`agent_with_repospec.log`** — Agent responses WITH .repospec.json
- **`agent_without_repospec.log`** — Agent responses WITHOUT .repospec.json
- **`RESULTS.md`** — Summary metrics and findings

## Example

```bash
$ ./repospec_benchmark.sh /path/to/my-repo

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  repospec Benchmark Tool
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Target repository: /Users/you/projects/myapp
Output directory: ./repospec-benchmark/myapp-20250115-143022
Timeout per run: 300s

[1/4] Generating .repospec.json for target repo...
ℹ Fetching PROMPT.md from repospec repository...
ℹ Extracting repository context...
ℹ Invoking Claude to generate .repospec.json...
✓ Generated .repospec.json

[2/4] Creating code-finding test tasks...
✓ Created 8 test tasks

[3/4] Running agents in parallel...
ℹ Running agent WITH .repospec.json context...
ℹ Running agent WITHOUT .repospec.json context...
✓ Both agents completed

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Benchmark Complete!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Results saved to: ./repospec-benchmark/myapp-20250115-143022

Summary:
  WITH .repospec.json:
    - Words: 2847
    - Tasks addressed: 8/8
  WITHOUT .repospec.json:
    - Words: 1923
    - Tasks addressed: 6/8
  ✓ .repospec.json enabled 2 more task completions
```

## Options

```bash
--output-dir DIR           Output directory for results (default: ./repospec-benchmark)
--timeout SECS             Timeout per agent run (default: 300)
--auth-method METHOD       Authentication method:
                           - api_key: Use ANTHROPIC_API_KEY environment variable
                           - oauth: Use claude.ai subscription (ANTHROPIC_AUTH_TOKEN)
                           - both: Run benchmarks with both auth methods
                           (default: api_key)
--help                    Show help message
```

## Authentication

### API Key (`--auth-method api_key`)
Uses `ANTHROPIC_API_KEY` environment variable. Set it before running:
```bash
export ANTHROPIC_API_KEY=sk-ant-...
./repospec_benchmark.sh /path/to/repo
```

### OAuth (`--auth-method oauth`)
Uses Claude.ai subscription token (`ANTHROPIC_AUTH_TOKEN`). Set it before running:
```bash
export ANTHROPIC_AUTH_TOKEN=...
./repospec_benchmark.sh /path/to/repo --auth-method oauth
```

### Both (`--auth-method both`)
Runs the full benchmark twice — once with each auth method — for direct comparison:
```bash
./repospec_benchmark.sh /path/to/repo --auth-method both
```
Generates separate results files: `RESULTS-api_key.md` and `RESULTS-oauth.md`

## How to Interpret Results

Review the logs manually:
- **WITH .repospec.json:** Should reference the metadata and give organized, focused answers
- **WITHOUT .repospec.json:** More exploratory; may miss key files or take longer to find answers
- **Task coverage:** How many of 8 tasks did each agent complete?
- **Accuracy:** Are file paths and function names correct?

## Next Steps

If `.repospec.json` helps:
- Commit it to your repo
- Share with teammates and agents
- Use as a template in CI/CD

If results are unclear:
- Review the logs for quality differences
- Try with a different, more complex repository
- Adjust the PROMPT.md template
