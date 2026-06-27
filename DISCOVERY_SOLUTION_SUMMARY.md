# Agent Discovery & Usage Documentation — Complete Solution

## Problem Solved

**Question:** How do agents unfamiliar with `.repospec.json` know how to find it and use it?

**Answer:** Through multi-layered documentation and tool integration:

---

## What Was Added

### 1. 📖 New Guide: `AGENT_DISCOVERY_GUIDE.md` (17.4 KB)

A comprehensive guide for agents learning about `.repospec.json` for the first time.

**Sections:**
- **Discovery** — How to find `.repospec.json` at repo root
- **Understanding** — What each section means (entrypoints, modules, patterns, features, key_files, testing, dependencies)
- **Integration** — How to use it in reasoning process (when starting analysis, writing code, debugging, estimating impact)
- **Verification** — How to spot good vs stale metadata (red flags, good signs)
- **Fallback** — What to do without `.repospec.json` (look for alternatives, infer manually)
- **Workflow** — Recommended process for any agent
- **Tool Integration** — Examples for tools that need to read `.repospec.json`
- **Quick Reference** — Common scenarios and solutions

### 2. 🎯 Updated `PROMPT.md`

Split into two focused prompts:

**Prompt 1: Discovery Prompt**
- For agents encountering `.repospec.json` for the first time
- Explains what it is and why it matters
- Gives step-by-step instructions (read, identify sections, verify, proceed)
- Links to full discovery guide

**Prompt 2: Generation Prompt**
- For creating `.repospec.json` from scratch
- (Existing content restructured and preserved)

### 3. 📚 Updated `README.md`

Reordered quick-start to emphasize agent usage:

**Before:**
1. Read the spec
2. Validate
3. Generate
4. Examples

**After:**
1. Understand format (SPEC.md)
2. **Agent usage (NEW: AGENT_DISCOVERY_GUIDE.md)**
3. Generate metadata (PROMPT.md)
4. Validate
5. Examples

### 4. 🔧 Updated `tools/README.md`

New section: "How Agents Discover `.repospec.json`"
- Explains discovery process
- Notes how benchmark agents are instructed
- Links to full discovery guide

### 5. 🚀 Updated `tools/repospec_benchmark.py`

Added `get_discovery_prompt()` function:
- Generates the discovery prompt for agents
- Both WITH and WITHOUT .repospec.json agents receive it
- Ensures agents know to look for and use the file

**Change:** Agent prompts now include discovery prompt before task instructions

---

## How It Works End-to-End

### Scenario 1: Agent Encounters `.repospec.json` Naturally

```
Agent starts analyzing repo
    ↓
Looks for .repospec.json (per guide)
    ↓
Finds it at repo root
    ↓
Reads AGENT_DISCOVERY_GUIDE.md (linked in prompt)
    ↓
Understands structure (entrypoints, modules, patterns)
    ↓
Uses metadata to guide exploration
    ↓
Verifies key details against actual code
    ↓
Completes task more efficiently
```

### Scenario 2: Agent Gets Discovery Prompt Explicitly

```
Tool (e.g., benchmark) gives discovery prompt
    ↓
Agent learns about .repospec.json
    ↓
Agent checks for file at repo root
    ↓
File found → Use as map
    ↓
File missing → Fall back to alternatives/manual exploration
```

### Scenario 3: Agent Needs to Understand Metadata (After Discovery)

```
Agent encounters unknown section (e.g., "features")
    ↓
Consults AGENT_DISCOVERY_GUIDE.md
    ↓
Finds "features" section explanation with examples
    ↓
Understands structure (name, description, flow, tests)
    ↓
Applies to their task
```

---

## Key Documents & Their Purpose

| Document | Audience | Purpose |
|----------|----------|---------|
| **AGENT_DISCOVERY_GUIDE.md** | Agents (Claude, Copilot, etc.) | Learn how to find, understand, and use `.repospec.json` |
| **PROMPT.md** | Tools, humans, agents | Prompts to generate or understand `.repospec.json` |
| **README.md** | Everyone | High-level overview; points to right docs |
| **tools/README.md** | Benchmark users | How benchmark agents use `.repospec.json` |
| **SPEC.md** | Technical readers | Complete format specification (unchanged) |
| **examples/** | Reference | Sample `.repospec.json` for different project types |

---

## What Agents Learn

After reading the documentation, agents understand:

✅ Where to look for `.repospec.json` (repo root)
✅ How to validate it (check schema version)
✅ What each section means (detailed examples provided)
✅ How to use it (concrete workflow with steps)
✅ How to verify it's correct (spot checks, red flags)
✅ What to do without it (fallback strategies)
✅ How to proceed with confidence (recommended workflow)

---

## Integration Points

### For Benchmark Tool
- Agents receive discovery prompt before analyzing
- Both WITH and WITHOUT agents are trained
- Ensures fair comparison (both know to look for `.repospec.json`)

### For Agent Prompts
- Tools can embed discovery prompt to teach agents
- Agents can link to AGENT_DISCOVERY_GUIDE.md for deep dive
- PROMPT.md provides generation guidance

### For External Tools
- Pseudo-code examples show how to read `.repospec.json`
- JSON schema is definitive reference
- Examples show real-world `.repospec.json` files

---

## Documentation Changes Summary

```
AGENT_DISCOVERY_GUIDE.md (NEW)
├── Discovery: How to find .repospec.json
├── Understanding: What each section means
├── Integration: How to use in reasoning
├── Verification: Spot good vs stale metadata
├── Fallback: What to do without it
├── Workflow: Recommended process
├── Tool Integration: Examples
└── Quick Reference: Common scenarios

PROMPT.md (UPDATED)
├── Prompt 1: Discovery (NEW)
└── Prompt 2: Generation (existing)

README.md (UPDATED)
├── Quick Start (reordered)
└── Link to AGENT_DISCOVERY_GUIDE.md (NEW)

tools/README.md (UPDATED)
├── "How Agents Discover .repospec.json" (NEW)
└── Link to full guide (NEW)

tools/repospec_benchmark.py (UPDATED)
├── get_discovery_prompt() function (NEW)
└── Discovery prompt in agent instructions (UPDATED)
```

---

## Testing the Solution

### Manual Test: Agent Learning Flow

1. **Create a fresh agent** with no knowledge of repospec
2. **Give it the discovery prompt** (from `get_discovery_prompt()`)
3. **Point to AGENT_DISCOVERY_GUIDE.md** for deeper questions
4. **Observe:** Agent should:
   - Look for `.repospec.json` at repo root
   - Read and understand structure
   - Use it to guide exploration
   - Verify key details

### Benchmark Test: WITH vs WITHOUT

1. Run benchmark on a repo with `.repospec.json`
2. Both agents (WITH spec, WITHOUT spec) receive discovery prompt
3. WITH agent uses `.repospec.json` effectively
4. WITHOUT agent falls back to manual exploration
5. Compare efficiency gains

---

## Future Enhancements

The documentation provides a foundation for:

1. **Agent Training** — Embed discovery guide in agent system prompts
2. **Tool Integration** — Generate discovery prompts programmatically
3. **Interactive Learning** — Create interactive tutorials for agents
4. **Community Feedback** — Users can report what agents miss/misunderstand
5. **Multi-Language** — Translate guides for different agent frameworks

---

## Summary

### Problem
Agents unfamiliar with `.repospec.json` wouldn't know to look for it or how to use it.

### Solution
Comprehensive multi-layer documentation:
1. **Prompt layer** — Discovery prompt teaches agents what `.repospec.json` is
2. **Guide layer** — `AGENT_DISCOVERY_GUIDE.md` explains every section with examples
3. **Tool layer** — Benchmark tool bakes discovery into agent instructions
4. **Navigation layer** — README points to right docs for each use case
5. **Integration layer** — Examples show how tools can read `.repospec.json`

### Result
Agents now have a clear, discoverable path to understanding and using `.repospec.json` effectively.

---

## Files Changed

```bash
git log --oneline -1
# 04bd85c docs: add agent discovery and usage guide

git show --stat
# 5 files changed, 653 insertions(+), 8 deletions(-)
#  AGENT_DISCOVERY_GUIDE.md (NEW)      | 478 insertions
#  PROMPT.md                           | +25/-17 lines
#  README.md                           | +5/-3 lines
#  tools/README.md                     | +7/-0 lines
#  tools/repospec_benchmark.py         | +138/-0 lines
```

---

**Status:** ✅ Complete and committed to `fix/benchmark-oauth-auth` branch
