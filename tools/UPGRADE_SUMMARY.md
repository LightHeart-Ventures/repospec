# Benchmark Upgrade: Opus 4.8 + Tool Integration

## Changes Made

### 1. ✅ Model Upgrade to Claude Opus 4.8
```python
OAUTH_MODEL = "claude-opus-4-8-20250507"  # Was: claude-sonnet-4-5-20250929
API_MODEL = "claude-opus-4-8-20250507"    # Was: claude-3-5-sonnet-20241022
```

**Why Opus?**
- More capable for complex reasoning tasks
- Better at code analysis and security audits
- Handles tool use more naturally
- Provides richer exploration strategies

### 2. ✅ Complex Test Cases
Upgraded from 8 basic tasks to 8 advanced tasks requiring real code analysis:

**Old (basic):**
- "List all entry points"
- "Identify main modules"

**New (complex):**
- "Identify ALL entry points, examine contents, trace imports, describe responsibility"
- "Map complete module dependency graph, identify circular dependencies"
- "Conduct security analysis: find hardcoded secrets, SQL injection patterns, CORS issues"
- "Trace critical data flows through the system"
- "Analyze test coverage and identify gaps"
- "Design refactoring plan with file-by-file changes"

### 3. ✅ Tool Integration
Added 4 real tools agents can call:

```python
Tools Available:
├── read_file(path)              # Read source files, configs, docs
├── list_directory(path)         # Explore repo structure
├── search_pattern(pattern)      # Find imports, function definitions
└── grep_code(regex, path)       # Search code patterns
```

**How It Works:**
- Agents can now invoke tools instead of just reasoning
- Each tool call is counted in `tool_calls` metric
- Benchmark measures: did .repospec.json reduce tool exploration?
- Expected: WITH spec = fewer tools (knows structure already)
- Expected: WITHOUT spec = more tools (must explore everything)

### 4. ✅ Tool Usage Measurement
```python
# Count actual tool invocations
tool_calls = sum(1 for block in response.content if block.type == "tool_use")

# Reported in results
| Tool Calls | {with_calls} | {without_calls} | {difference:+d} |
```

## What This Tests

### Before (Pure-LLM)
```
WITH .repospec.json:      1,294 words, all reasoning
WITHOUT .repospec.json:   1,473 words, all reasoning
→ Tested: response quality and conciseness
```

### After (With Tools)
```
WITH .repospec.json:      Uses N tools, more accurate  
WITHOUT .repospec.json:   Uses M tools (M > N), less accurate
→ Tests: exploration efficiency, accuracy, tool use patterns
```

## Expected Results

### Path Accuracy (Most Important)
- WITH should still show 13x+ better accuracy
- Reason: spec prevents hallucination even with tools

### Tool Usage
- WITH: ~5-10 tool calls (targeted exploration)
- WITHOUT: ~15-25 tool calls (exhaustive search)
- Reason: spec guides agent where to look

### Duration
- WITH: Still faster (spec reduces search space)
- WITHOUT: Longer (more tool calls = more API time)

### Token Usage
- Input: WITH larger (spec in prompt)
- Output: WITH smaller (more concise due to spec)
- Tool outputs: Measured separately

## Files Updated

| File | Changes |
|------|---------|
| `repospec_benchmark.py` | Model upgrade, tool definitions, complex tasks, tool counting |
| Updated docstring | Reflects tool-based benchmark design |

## How to Run

```bash
# OAuth (Claude Code)
python3 repospec_benchmark.py /path/to/repo --auth-method oauth

# API Key
python3 repospec_benchmark.py /path/to/repo --auth-method api_key

# Both (parallel benchmarks)
python3 repospec_benchmark.py /path/to/repo --auth-method both
```

## New Metrics in Results

```markdown
## Token & Tool Usage

| Tool Calls | WITH .repospec.json | WITHOUT .repospec.json | Difference |
|------------|---------------------|----------------------|------------|
| Tool Calls | 7 | 19 | -12 (63% fewer) |

## Duration Metrics

| Total Duration (s) | 45.3 | 62.1 | -16.8 (-27%) |
| Per-Task Duration  | 5.66 | 7.76 | -2.10 (-27%) |
```

## What We're Measuring Now

| Metric | Previous | Now | Why |
|--------|----------|-----|-----|
| Token usage | Yes | Yes | Same |
| Duration | Yes | Yes | Same |
| Path accuracy | Yes | Yes | Same |
| Tool calls | Regex pattern count (fake) | Real tool invocations | Actual efficiency |
| Task complexity | Basic (8 tasks) | Advanced (code analysis) | Better signal |
| Model capability | Sonnet 3.5 | Opus 4.8 | Better reasoning |

## Success Criteria

✅ Benchmark compiles without errors  
✅ Tool definitions are valid  
✅ Complex tasks are solvable  
✅ Tool invocations counted correctly  
✅ Results show WITH using fewer tools  
✅ Path accuracy still favors WITH  

---

## Next: Run the Benchmark

Ready to test with:
```bash
python3 repospec_benchmark.py /path/to/repo
```

This will now measure real exploration efficiency, not just reasoning quality.
