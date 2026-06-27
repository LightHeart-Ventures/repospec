# Benchmark Enhancement Roadmap

This document outlines additional metrics and enhancements planned for the repospec benchmark tool.

## Currently Captured

✅ **Repository Statistics**
- Total files, directories, size (MB)
- Language breakdown (Python, JavaScript, Go, etc.)
- Source file and test file counts

✅ **Response Metrics**
- Response length (characters)
- Line count
- Word count
- Tasks mentioned (out of 8)
- Average words per task

✅ **Token Usage**
- Input tokens (when available from Claude CLI)
- Output tokens (when available)
- Percentage savings (WITH vs WITHOUT .repospec.json)

✅ **Tool Invocations**
- Tool call count (inferred from response patterns: function_calls, bash blocks, grep, find, cat, etc.)
- Comparison showing reduction with .repospec.json

✅ **File-Path Accuracy** (NEW)
- Valid path references (paths that exist in repo)
- Invalid path references (hallucinated or incorrect paths)
- Accuracy percentage (valid / total)
- Direct measure of navigation quality

---

## Remaining Enhancements

### Tier 1 — High Value (Directly Prove Impact)

#### 1. **Task Correctness (Ground Truth)**
**What:** Pre-written answer key for each of the 8 benchmark tasks. Score agent responses as pass/fail/partial.

**Why:** Without this, we can't claim one agent performs *better*, only *differently*. This is the proof.

**Implementation:**
- Create `tasks_groundtruth.json` with:
  - Task ID
  - Expected answer(s)
  - Key elements to look for
  - Scoring rubric (pass/fail or 0-100)
- Parse agent responses for correct answers
- Report % tasks answered correctly per agent

**Effort:** Medium (requires domain knowledge of test repo to write good answers)

**Example output:**
```
Task Correctness:
  WITH .repospec.json: 7/8 correct (87.5%)
  WITHOUT .repospec.json: 5/8 correct (62.5%)
  ✓ .repospec.json improved correctness by 25%
```

---

#### 2. **Real Tool-Call / File-Open Logging**
**What:** Instead of inferring tool calls from response patterns, capture actual file opens and tool invocations.

**Why:** Current inference is unreliable. Real logging unlocks:
- Accurate tool call counts
- Steps-to-first-correct-file (how many files opened before finding relevant code)
- Redundant file reads (files opened but not relevant)
- Actual exploration patterns

**Implementation Options:**

*Option A (Harness-based):*
- Modify Claude CLI invocation to log all tool calls to a structured file
- Parse and count by type (file open, grep, find, etc.)
- Calculate metrics from the log

*Option B (Claude API):*
- Switch from CLI to Claude API with full message/tool-use logging
- Capture tool-use JSON directly
- Much more reliable than pattern matching

*Option C (Lightweight):*
- Ask Claude to include a "Tools Used" summary at end of response
- Parse that summary instead of inferring from patterns
- Medium effort, decent reliability

**Effort:** Medium-High (requires harness changes)

**Example output:**
```
Tool-Call Efficiency:
  WITH .repospec.json:
    - Total files opened: 12
    - Unique files: 10
    - Grep calls: 8
    - Find calls: 2
    - Steps to first correct file: 2
    
  WITHOUT .repospec.json:
    - Total files opened: 28
    - Unique files: 21
    - Grep calls: 15
    - Find calls: 8
    - Steps to first correct file: 7
    
  ✓ .repospec.json reduced exploration by 57%
```

---

#### 3. **Per-Task Breakdown**
**What:** Instead of aggregate metrics, break down all measurements (correctness, tool calls, tokens, accuracy) per task.

**Why:** Benefits are almost certainly uneven. Navigation tasks may benefit 80%, while high-level architecture questions benefit 10%. Knowing this is crucial.

**Implementation:**
- Parse responses to identify which section answers which task
- Apply all metrics (correctness, path accuracy, tool calls) per task
- Generate a per-task comparison table

**Effort:** Medium (parsing logic)

**Example output:**
```
| Task | Category | WITH Correct | WITHOUT Correct | Tool Calls (WITH) | Tool Calls (WITHOUT) | Path Accuracy (WITH) |
|------|----------|--------------|-----------------|------------------|----------------------|----------------------|
| 1: Entry Points | Navigation | ✓ | ✓ | 3 | 8 | 100% |
| 2: Modules | Architecture | ✓ | ✗ | 5 | 12 | 95% |
| 3: Auth Pattern | Pattern Finding | ✓ | ✓ | 4 | 7 | 90% |
| ... | ... | ... | ... | ... | ... | ... |
```

---

### Tier 2 — Valuable (Context & Insight)

#### 4. **Hallucination Detection**
**What:** Identify claims about code that don't exist (false positives, made-up file paths, non-existent functions).

**Why:** Often *reduced* by accurate metadata — a strong selling point.

**Implementation:**
- Extract all identifiers (functions, classes, variables, file paths) from responses
- Cross-check against actual repo symbols (via grep or AST parsing)
- Count hallucinations (claims that don't exist)
- Calculate hallucination rate per agent

**Effort:** Medium (requires symbol extraction/validation)

**Example output:**
```
Hallucination Rate:
  WITH .repospec.json: 2 hallucinations (2.3% of claims)
  WITHOUT .repospec.json: 8 hallucinations (9.1% of claims)
  ✓ .repospec.json reduced hallucinations by 75%
```

---

#### 5. **Confusion / Backtracking Indicators**
**What:** Detect phrases like "actually," "let me reconsider," "I was wrong," etc. that suggest the agent got confused and had to restart.

**Why:** Proxy for clarity. .repospec.json should reduce restarts.

**Implementation:**
- Define backtracking keywords/phrases
- Count occurrences in response
- Assume each restart adds ~20% cost overhead
- Estimate "true cost" after accounting for wasted exploration

**Effort:** Low-Medium (regex-based)

**Example output:**
```
Confusion & Restarts:
  WITH .repospec.json: 1 restart (1 phrase indicating reconsideration)
  WITHOUT .repospec.json: 4 restarts (4 phrases indicating reconsideration)
```

---

#### 6. **Wall-Clock Time Per Task**
**What:** Measure elapsed time for each agent run.

**Why:** Intuitive for stakeholders; shows real-world latency improvement.

**Implementation:**
- Timestamp agent invocation start and end
- Report total time and per-task breakdown (if possible)

**Effort:** Low (just add timestamps)

**Example output:**
```
Execution Time:
  WITH .repospec.json: 145 seconds (18 sec/task)
  WITHOUT .repospec.json: 247 seconds (31 sec/task)
  ✓ .repospec.json was 41% faster
```

---

#### 7. **Cost Analysis**
**What:** Calculate total API cost per agent run based on token usage and model.

**Why:** ROI story — "this metadata saves $X per code review."

**Implementation:**
- Accept model pricing as input (or hardcode common models)
- Multiply tokens by price per token
- Sum and compare

**Effort:** Low (just math)

**Example output:**
```
Cost (Claude 3.5 Sonnet @ current pricing):
  WITH .repospec.json: $0.047 (input: $0.031 + output: $0.016)
  WITHOUT .repospec.json: $0.089 (input: $0.052 + output: $0.037)
  ✓ .repospec.json saved 47% on API cost
```

---

### Tier 3 — Nice-to-Have (Lower Priority)

#### 8. **Symbol-Name Correctness**
**What:** Extract function/class names referenced in responses; check if they exist in the cited file.

**Why:** Complements path accuracy; shows if agent knows the actual code.

**Implementation:**
- Extract identifiers from responses
- For each, check if it exists in the cited file (grep/AST)
- Calculate symbol accuracy %

**Effort:** Medium (requires symbol parsing)

---

#### 9. **Confidence Calibration**
**What:** Ask agents to rate confidence in their answers (1-10); check if high-confidence answers are more often correct.

**Why:** Weak signal, but interesting for understanding agent behavior.

**Implementation:**
- Add prompt instruction: "Rate your confidence in each answer (1-10)"
- Extract confidence scores
- Correlate with correctness

**Effort:** Low (prompting) + Medium (correlation analysis)

---

#### 10. **Search Pattern Analysis**
**What:** Count types of searches used (grep, find, exact-match, partial-match, etc.).

**Why:** Reveals agent strategy; may show different approaches with vs without metadata.

**Implementation:**
- Parse tool calls / response text for search patterns
- Categorize (regex, exact, wildcard, etc.)
- Compare distributions

**Effort:** Medium

---

## Implementation Priority

**Phase 1 (Next):**
1. Task correctness + ground truth answer key
2. Real tool-call logging (or lightweight summary-based alternative)

**Phase 2 (Following):**
3. Per-task breakdown
4. Hallucination detection
5. Wall-clock time

**Phase 3 (Refinement):**
6. Backtracking detection
7. Cost analysis
8. Symbol-name correctness

---

## Testing Strategy

1. **Start with a medium-complexity repo** (Ghost, aish, or similar)
2. **Manually create ground-truth answers** for the 8 tasks
3. **Run one benchmark** and validate metrics manually
4. **Iterate on metrics** that add signal vs noise
5. **Publish results** once 3-4 key metrics are solid

---

## Notes

- **Path accuracy (already done)** is the cheapest high-value metric and validates the core hypothesis
- **Task correctness** requires upfront work but is non-negotiable for claiming "better"
- **Real tool logging** is the gateway to the efficiency story (steps-to-correct-file, redundant reads)
- **Per-task breakdown** protects against misleading averages
- Start with these 4, skip the rest until needed
