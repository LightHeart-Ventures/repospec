#!/usr/bin/env python3
"""
repospec_benchmark.py

Benchmark .repospec.json impact on agent code navigation.

Usage:
    python3 repospec_benchmark.py <target_repo_path> [options]

This tool:
1. Generates .repospec.json for a target repository using Claude
2. Creates a set of code-finding test tasks
3. Runs two agents in parallel: one with .repospec.json context, one without
4. Compares results: response quality, structure, and token usage

DESIGN NOTE:
- This is an advanced benchmark with tool access. Both agents have file reading,
  directory listing, and pattern search capabilities.
- The key independent variable is the presence/absence of .repospec.json.
- Tasks are complex and require analyzing actual code to answer accurately.
- Metrics: token usage, tool invocations, duration, path accuracy.
- This tests whether .repospec.json helps agents navigate repos more efficiently.
"""

import argparse
import json
import os
import sys
import subprocess
import time
import re
from datetime import datetime
from pathlib import Path
import anthropic


class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'


def log_info(msg):
    print(f"{Colors.BLUE}ℹ {msg}{Colors.NC}")


def log_success(msg):
    print(f"{Colors.GREEN}✓ {msg}{Colors.NC}")


def log_warning(msg):
    print(f"{Colors.YELLOW}⚠ {msg}{Colors.NC}")


def log_error(msg):
    print(f"{Colors.RED}✗ {msg}{Colors.NC}")


def log_step(step_num, total, msg):
    print(f"{Colors.YELLOW}[{step_num}/{total}]{Colors.NC} {msg}")


def validate_repo(repo_path):
    """Validate that the path is a valid directory."""
    repo_path = Path(repo_path).resolve()
    if not repo_path.is_dir():
        log_error(f"Repository not found: {repo_path}")
        sys.exit(1)
    return repo_path


def fetch_prompt_md():
    """Fetch PROMPT.md from the repospec GitHub repo."""
    log_info("Fetching PROMPT.md from repospec repository...")
    
    try:
        result = subprocess.run(
            ["curl", "-s", "https://github.com/LightHeart-Ventures/repospec/raw/main/PROMPT.md"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0 and result.stdout:
            return result.stdout
        else:
            log_warning("Failed to fetch PROMPT.md, using fallback template")
            return get_fallback_prompt()
    except Exception as e:
        log_warning(f"Error fetching PROMPT.md: {e}")
        return get_fallback_prompt()


def get_fallback_prompt():
    """Fallback prompt template if PROMPT.md cannot be fetched."""
    return """You are generating a `.repospec.json` file for a repository.

Your task:
1. Analyze the repository structure, entry points, modules, and key files.
2. Generate a valid `.repospec.json` file.
3. Output ONLY valid JSON, no markdown, no explanation.

Sections to include:
- `entrypoints`: Entry points (services, CLIs, workers, etc.)
- `modules`: Logical modules and their purpose
- `patterns`: Cross-cutting concerns (auth, logging, etc.)
- `key_files`: Important files by category
- `features`: Key feature flows through the code (optional)
- `testing`: Test structure and conventions (optional)

Reference: https://github.com/LightHeart-Ventures/repospec/blob/main/SPEC.md"""


def extract_repo_context(repo_path, max_files=100):
    """Extract repository metadata and structure."""
    log_info("Extracting repository context...")
    
    context = {
        "name": repo_path.name,
        "path": str(repo_path),
        "files": [],
        "readmes": [],
        "manifests": [],
    }
    
    # Find key files
    for ext in [".md", ".txt"]:
        for f in repo_path.rglob(f"*{ext}"):
            if ".git" in f.parts or "node_modules" in f.parts:
                continue
            rel_path = f.relative_to(repo_path)
            if f.name.lower().startswith("readme"):
                context["readmes"].append(str(rel_path))
    
    # Find manifests
    manifest_names = ["go.mod", "package.json", "pyproject.toml", "Cargo.toml", "pom.xml"]
    for f in repo_path.rglob("*"):
        if f.name in manifest_names and ".git" not in f.parts:
            context["manifests"].append(str(f.relative_to(repo_path)))
    
    # Find source files
    source_exts = [".go", ".ts", ".js", ".py", ".java", ".rs"]
    for ext in source_exts:
        for f in repo_path.rglob(f"*{ext}"):
            if ".git" in f.parts or "node_modules" in f.parts or "vendor" in f.parts:
                continue
            rel_path = f.relative_to(repo_path)
            context["files"].append(str(rel_path))
            if len(context["files"]) >= max_files:
                break
        if len(context["files"]) >= max_files:
            break
    
    return context


def load_credentials():
    """Load API credentials from environment or ~/.atum/credentials file.
    
    Returns:
        dict with 'oauth_token' (CLAUDE_CODE_OAUTH_TOKEN) and 'api_key' (ANTHROPIC_API_KEY)
    """
    creds = {
        "oauth_token": None,
        "api_key": None,
    }
    
    # Try environment variables first
    creds["oauth_token"] = os.environ.get("CLAUDE_CODE_OAUTH_TOKEN")
    creds["api_key"] = os.environ.get("ANTHROPIC_API_KEY")
    
    # If not in env, try ~/.atum/credentials file
    creds_file = Path.home() / ".atum" / "credentials"
    if creds_file.exists():
        try:
            import configparser
            config = configparser.ConfigParser()
            config.read(creds_file)
            
            # Try to extract tokens from [default] or other sections
            for section in config.sections():
                if not creds["oauth_token"] and config.has_option(section, "claude_code_oauth_token"):
                    creds["oauth_token"] = config.get(section, "claude_code_oauth_token")
                if not creds["api_key"] and config.has_option(section, "anthropic_api_key"):
                    creds["api_key"] = config.get(section, "anthropic_api_key")
        except Exception as e:
            log_warning(f"Error reading credentials file: {e}")
    
    return creds


# Auth/model configuration.
# OAuth (CLAUDE_CODE_OAUTH_TOKEN) is a Claude subscription token: it must be sent
# as a Bearer auth_token (NOT x-api-key), needs the oauth beta header, requires the
# Claude Code identity system prompt, and only exposes subscription model ids.
CLAUDE_CODE_SYSTEM = "You are Claude Code, Anthropic's official CLI for Claude."
OAUTH_BETA_HEADER = "oauth-2025-04-20"
OAUTH_MODEL = "claude-opus-4-5-20251101"
API_MODEL = "claude-opus-4-5-20251101"


def make_client(auth_method, creds):
    """Build an Anthropic client for the given auth method.

    Returns (client, model, system) where `system` is the required system-prompt
    prefix (or None). Returns (None, None, None) if the required credential is missing.
    """
    if auth_method == "oauth":
        tok = creds.get("oauth_token")
        if not tok:
            return None, None, None
        client = anthropic.Anthropic(
            auth_token=tok,
            default_headers={"anthropic-beta": OAUTH_BETA_HEADER},
        )
        return client, OAUTH_MODEL, CLAUDE_CODE_SYSTEM
    else:
        key = creds.get("api_key")
        if not key:
            return None, None, None
        return anthropic.Anthropic(api_key=key), API_MODEL, None


def _create_message(client, model, system, prompt, max_tokens=4096, tools=None):
    """Single-user-message helper that includes the system prompt and tools when provided."""
    kwargs = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }
    if system:
        kwargs["system"] = system
    if tools:
        kwargs["tools"] = tools
    return client.messages.create(**kwargs)



def generate_repospec_json(repo_path, output_dir):
    """Generate .repospec.json using Claude API."""
    log_step(1, 4, "Generating .repospec.json for target repo...")
    
    creds = load_credentials()
    
    # Prefer OAuth (subscription) over API key.
    auth_method = "oauth" if creds.get("oauth_token") else "api_key"
    client, model, system = make_client(auth_method, creds)
    if client is None:
        log_error("No API credentials found. Set CLAUDE_CODE_OAUTH_TOKEN or ANTHROPIC_API_KEY, or add to ~/.atum/credentials")
        return get_minimal_repospec({"name": repo_path.name, "path": str(repo_path), "files": [], "readmes": [], "manifests": []}), None
    
    prompt_md = fetch_prompt_md()
    context = extract_repo_context(repo_path)
    
    # Read README if available
    readme_content = ""
    if context["readmes"]:
        readme_path = repo_path / context["readmes"][0]
        try:
            with open(readme_path) as f:
                readme_content = f.read(800)
        except:
            pass
    
    generation_prompt = f"""{prompt_md}

Here's the repository to analyze:

Repository: {context['name']}
Path: {repo_path}

README (excerpt):
{readme_content if readme_content else '(no README found)'}

Files in repository (sample):
{chr(10).join(context['files'][:30])}

Manifests found:
{chr(10).join(context['manifests']) if context['manifests'] else '(none)'}

Generate the .repospec.json now. Output ONLY valid JSON."""

    log_info("Invoking Claude API to generate .repospec.json...")
    
    try:
        response = _create_message(client, model, system, generation_prompt)
        
        output = response.content[0].text.strip()
        
        # Try to extract JSON
        try:
            json_match = re.search(r'\{[\s\S]*\}', output)
            if json_match:
                repospec = json.loads(json_match.group())
            else:
                repospec = json.loads(output)
            
            log_success("Generated .repospec.json")
            
            output_path = output_dir / "generated.repospec.json"
            with open(output_path, 'w') as f:
                json.dump(repospec, f, indent=2)
            
            return repospec, str(output_path)
        
        except (json.JSONDecodeError, AttributeError):
            log_warning("Could not parse Claude output as JSON")
            return get_minimal_repospec(context), None
    
    except Exception as e:
        log_error(f"Error calling Claude API: {e}")
        return get_minimal_repospec(context), None


def get_minimal_repospec(context):
    """Return a minimal .repospec.json template."""
    return {
        "schema": "repospec/v1",
        "name": context["name"],
        "summary": "Repository structure",
        "entrypoints": [],
        "modules": [],
        "patterns": [],
        "key_files": {},
        "features": []
    }


def get_tools_definition():
    """Return tool definitions for agents to use."""
    return [
        {
            "name": "read_file",
            "description": "Read the contents of a file in the repository. Use to examine source code, configuration files, or documentation.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path to the file (e.g., 'src/main.ts' or 'package.json')"
                    }
                },
                "required": ["path"]
            }
        },
        {
            "name": "list_directory",
            "description": "List files and directories in a folder. Use to explore repository structure and find files.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path to the directory (e.g., 'src' or '.')"
                    }
                },
                "required": ["path"]
            }
        },
        {
            "name": "search_pattern",
            "description": "Search for files or content matching a pattern. Use to find imports, function definitions, or configurations.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Search pattern (e.g., 'import', 'export', 'function', 'async')"
                    },
                    "file_type": {
                        "type": "string",
                        "description": "Limit search to file types (e.g., '.js', '.ts', '.json')"
                    }
                },
                "required": ["pattern"]
            }
        },
        {
            "name": "grep_code",
            "description": "Search for specific code patterns like function definitions, imports, or variable declarations.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "regex": {
                        "type": "string",
                        "description": "Regular expression to search for"
                    },
                    "path": {
                        "type": "string",
                        "description": "Directory to search in (e.g., 'src')"
                    }
                },
                "required": ["regex"]
            }
        }
    ]


def create_test_tasks():
    """Create a set of complex code-finding test tasks."""
    log_step(2, 4, "Creating complex test tasks with tool integration...")
    
    tasks = [
        "Task 1: Identify ALL entry points (main files, CLI handlers, API routes, workers). For each entry point, use tools to examine its contents, determine what it imports, and describe its primary responsibility in 2-3 sentences.",
        
        "Task 2: Map the complete module dependency graph. Use tools to examine package.json/go.mod/pyproject.toml and trace how modules import each other. Identify circular dependencies or highly-coupled modules.",
        
        "Task 3: Locate and analyze authentication/authorization logic. Examine the actual implementation, identify the auth strategy (JWT, OAuth, session-based, etc.), and describe the complete flow from request to authorization decision.",
        
        "Task 4: Trace the critical data flow for 2-3 key features. Use tools to follow how data enters the system, gets processed through modules, and is returned. Identify transformation points and validation steps.",
        
        "Task 5: Conduct a security analysis. Use tools to search for potential vulnerabilities: hardcoded secrets, SQL injection patterns, CORS misconfigurations, unvalidated inputs. Report findings with file locations.",
        
        "Task 6: Analyze test coverage. Use tools to examine test files, identify what's tested vs untested, and estimate coverage percentages by module. Identify gap areas.",
        
        "Task 7: Examine all external dependencies and their versions. For each major dependency, determine what functionality it provides and if there are alternatives being used elsewhere.",
        
        "Task 8: Design a refactoring plan. Identify code smells, tightly-coupled modules, and opportunities for consolidation. Propose which files would need changes and in what order to implement improvements safely."
    ]
    
    log_success("Created 8 complex test tasks with tool integration")
    return tasks


def get_discovery_prompt():
    """Return the discovery prompt for agents unfamiliar with .repospec.json."""
    return """You have access to a `.repospec.json` file in this repository. This is metadata that helps
you understand repository structure efficiently.

**What it is:**
`.repospec.json` is a standard metadata file that describes:
- Where code execution starts (entrypoints)
- What logical modules exist and how they're related
- Cross-cutting patterns (authentication, error handling, etc.)
- How key features flow through the code
- Where tests, migrations, and other important files are

**How to use it:**
1. First, read the entire `.repospec.json` file to get an overview
2. Identify which sections are relevant to your task
3. Use the metadata as a map to guide your exploration
4. Verify key details with actual code files
5. Proceed with your analysis using this structure

**For more details, see:**
https://github.com/LightHeart-Ventures/repospec/blob/main/AGENT_DISCOVERY_GUIDE.md

Now proceed with your analysis tasks below."""


def run_agent_with_repospec(repo_path, repospec, tasks, timeout=300, auth_method="api_key"):
    """Run agent WITH .repospec.json context.
    
    Args:
        auth_method: "api_key" (ANTHROPIC_API_KEY) or "oauth" (CLAUDE_CODE_OAUTH_TOKEN)
    
    Returns:
        (response_text, usage_dict, exit_code) where usage_dict includes duration_seconds
    """
    log_info(f"Running agent WITH .repospec.json context ({auth_method} auth)...")
    
    creds = load_credentials()
    
    client, model, system = make_client(auth_method, creds)
    if client is None:
        missing = "CLAUDE_CODE_OAUTH_TOKEN" if auth_method == "oauth" else "ANTHROPIC_API_KEY"
        log_error(f"{missing} not found. Set env var or add to ~/.atum/credentials")
        return f"ERROR: {missing} not set", {"input_tokens": 0, "output_tokens": 0, "duration_seconds": 0}, 1
    
    discovery_prompt = get_discovery_prompt()
    
    prompt = f"""{discovery_prompt}

Here's the .repospec.json for the repository:
```json
{json.dumps(repospec, indent=2)}
```

Now, use this as your guide to answer the following tasks. The repository content is provided in context.

{chr(10).join(tasks)}

For each task, work systematically using .repospec.json as your starting point. Be specific and reference files/functions by name."""

    start_time = time.time()
    try:
        tools = get_tools_definition()
        response = _create_message(client, model, system, prompt, tools=tools)
        duration = time.time() - start_time
        
        # Extract response text and count tool calls
        response_text = response.content[0].text
        tool_calls = sum(1 for block in response.content if block.type == "tool_use")
        
        usage = {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
            "duration_seconds": duration,
            "tool_calls": tool_calls,
        }
        
        return response_text, usage, 0
    except Exception as e:
        duration = time.time() - start_time
        log_error(f"Error calling Claude API: {e}")
        return f"ERROR: {e}", {"input_tokens": 0, "output_tokens": 0, "duration_seconds": duration, "tool_calls": 0}, 1


def run_agent_without_repospec(repo_path, tasks, timeout=300, auth_method="api_key"):
    """Run agent WITHOUT .repospec.json context.
    
    Args:
        auth_method: "api_key" (ANTHROPIC_API_KEY) or "oauth" (CLAUDE_CODE_OAUTH_TOKEN)
    
    Returns:
        (response_text, usage_dict, exit_code) where usage_dict includes duration_seconds
    """
    log_info(f"Running agent WITHOUT .repospec.json context ({auth_method} auth)...")
    
    creds = load_credentials()
    
    client, model, system = make_client(auth_method, creds)
    if client is None:
        missing = "CLAUDE_CODE_OAUTH_TOKEN" if auth_method == "oauth" else "ANTHROPIC_API_KEY"
        log_error(f"{missing} not found. Set env var or add to ~/.atum/credentials")
        return f"ERROR: {missing} not set", {"input_tokens": 0, "output_tokens": 0, "duration_seconds": 0}, 1
    
    prompt = f"""You are an expert code navigator. You have been asked to understand a repository without any pre-generated metadata.

The repository content is provided in context below.

Answer the following tasks by analyzing the code:

{chr(10).join(tasks)}

Work systematically and carefully. Be specific and reference files/functions by name."""

    start_time = time.time()
    try:
        tools = get_tools_definition()
        response = _create_message(client, model, system, prompt, tools=tools)
        duration = time.time() - start_time
        
        # Extract response text and count tool calls
        response_text = response.content[0].text
        tool_calls = sum(1 for block in response.content if block.type == "tool_use")
        
        usage = {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
            "duration_seconds": duration,
            "tool_calls": tool_calls,
        }
        
        return response_text, usage, 0
    except Exception as e:
        duration = time.time() - start_time
        log_error(f"Error calling Claude API: {e}")
        return f"ERROR: {e}", {"input_tokens": 0, "output_tokens": 0, "duration_seconds": duration, "tool_calls": 0}, 1


def analyze_response(response, label, repo_path=None, usage_dict=None):
    """Analyze agent response metrics.
    
    Args:
        response: The text response from the agent
        label: Label for this response (WITH/WITHOUT .repospec.json)
        repo_path: Path to repo for path validation
        usage_dict: Dict with 'input_tokens', 'output_tokens', 'duration_seconds' from API
    """
    lines = response.split('\n')
    words = response.split()
    
    tasks_mentioned = sum(1 for i in range(1, 9) if f"Task {i}" in response)
    
    # Use provided usage dict from API, or initialize empty
    duration_seconds = usage_dict.get("duration_seconds", 0) if usage_dict else 0
    per_task_duration = (duration_seconds / tasks_mentioned) if tasks_mentioned > 0 else 0
    
    usage = {
        "input_tokens": usage_dict.get("input_tokens") if usage_dict else None,
        "output_tokens": usage_dict.get("output_tokens") if usage_dict else None,
        "tool_calls": usage_dict.get("tool_calls", 0) if usage_dict else 0,
        "duration_seconds": duration_seconds,
        "per_task_duration_seconds": per_task_duration,
    }
    
    # Extract and validate file paths
    accuracy = {
        "valid_paths": 0,
        "invalid_paths": 0,
        "path_accuracy": 0.0
    }
    
    if repo_path:
        # Find repo-relative paths in response
        path_pattern = r'(?:[a-zA-Z_][a-zA-Z0-9_/\-\.]*\.(?:go|py|js|ts|java|rs|rb|php|cs|c|cpp|h|json|yaml|yml|toml|md))'
        paths_found = re.findall(path_pattern, response)
        
        if paths_found:
            repo_files = set()
            for root, dirs, files in os.walk(repo_path):
                if ".git" in root or "node_modules" in root or "vendor" in root:
                    continue
                for f in files:
                    rel_path = os.path.relpath(os.path.join(root, f), repo_path)
                    repo_files.add(rel_path)
            
            for path in paths_found:
                if path in repo_files:
                    accuracy["valid_paths"] += 1
                else:
                    accuracy["invalid_paths"] += 1
            
            total = accuracy["valid_paths"] + accuracy["invalid_paths"]
            if total > 0:
                accuracy["path_accuracy"] = (accuracy["valid_paths"] / total) * 100
    
    return {
        "label": label,
        "response_length": len(response),
        "lines": len(lines),
        "words": len(words),
        "tasks_mentioned": tasks_mentioned,
        "avg_words_per_task": len(words) // max(1, tasks_mentioned),
        "usage": usage,
        "accuracy": accuracy
    }


def quantify_repo(repo_path):
    """Gather statistics about the repository."""
    stats = {
        "total_files": 0,
        "total_dirs": 0,
        "total_size_mb": 0,
        "languages": {},
        "source_files": 0,
        "test_files": 0,
    }
    
    source_exts = {
        ".py": "Python",
        ".js": "JavaScript",
        ".ts": "TypeScript",
        ".go": "Go",
        ".rs": "Rust",
        ".java": "Java",
        ".c": "C",
        ".cpp": "C++",
        ".rb": "Ruby",
        ".php": "PHP",
        ".cs": "C#",
    }
    
    try:
        for root, dirs, files in os.walk(repo_path):
            if ".git" in root or "node_modules" in root or "vendor" in root:
                continue
            
            stats["total_dirs"] += len(dirs)
            
            for f in files:
                stats["total_files"] += 1
                
                file_path = Path(root) / f
                ext = file_path.suffix.lower()
                
                # Track file size
                try:
                    stats["total_size_mb"] += file_path.stat().st_size / (1024 * 1024)
                except:
                    pass
                
                # Track language
                if ext in source_exts:
                    lang = source_exts[ext]
                    stats["languages"][lang] = stats["languages"].get(lang, 0) + 1
                    stats["source_files"] += 1
                
                # Track test files
                if "test" in f.lower() or "spec" in f.lower():
                    stats["test_files"] += 1
    
    except Exception as e:
        log_warning(f"Error scanning repo: {e}")
    
    stats["total_size_mb"] = round(stats["total_size_mb"], 2)
    return stats


def print_results(results_file, with_spec_output, without_spec_output, repo_name, repo_path=None, with_usage=None, without_usage=None, auth_method="api_key"):
    """Print and save benchmark results.
    
    Args:
        results_file: Path to write RESULTS.md to
        auth_method: Authentication method used ("api_key" or "oauth")
    """
    log_step(4, 4, f"Analyzing results ({auth_method} auth)...")
    
    with_metrics = analyze_response(with_spec_output, "WITH .repospec.json", repo_path, with_usage)
    without_metrics = analyze_response(without_spec_output, "WITHOUT .repospec.json", repo_path, without_usage)
    
    repo_stats = None
    if repo_path:
        repo_stats = quantify_repo(repo_path)
    
    with open(results_file, 'w') as f:
        f.write("# .repospec.json Benchmark Results\n\n")
        f.write(f"**Repository:** {repo_name}\n")
        f.write(f"**Date:** {datetime.now().isoformat()}\n")
        f.write(f"**Auth Method:** {auth_method}\n\n")
        
        if repo_stats:
            f.write("## Repository Statistics\n\n")
            f.write(f"- **Total Files:** {repo_stats['total_files']}\n")
            f.write(f"- **Total Directories:** {repo_stats['total_dirs']}\n")
            f.write(f"- **Total Size:** {repo_stats['total_size_mb']} MB\n")
            f.write(f"- **Source Files:** {repo_stats['source_files']}\n")
            f.write(f"- **Test Files:** {repo_stats['test_files']}\n")
            
            if repo_stats['languages']:
                f.write(f"\n**Languages:**\n")
                for lang, count in sorted(repo_stats['languages'].items(), key=lambda x: x[1], reverse=True):
                    f.write(f"- {lang}: {count} files\n")
            
            f.write("\n")
        
        f.write("## Response Metrics\n\n")
        f.write("| Metric | WITH .repospec.json | WITHOUT .repospec.json | Difference |\n")
        f.write("|--------|---------------------|----------------------|------------|\n")
        
        for key in ["response_length", "lines", "words"]:
            with_val = with_metrics[key]
            without_val = without_metrics[key]
            diff = with_val - without_val
            f.write(f"| {key} | {with_val} | {without_val} | {diff:+d} |\n")
        
        f.write("\n## Token & Tool Usage\n\n")
        with_usage = with_metrics.get("usage", {})
        without_usage = without_metrics.get("usage", {})
        
        f.write("| Metric | WITH .repospec.json | WITHOUT .repospec.json | Difference |\n")
        f.write("|--------|---------------------|----------------------|------------|\n")
        
        if with_usage.get("input_tokens") is not None and without_usage.get("input_tokens") is not None:
            with_input = with_usage["input_tokens"]
            without_input = without_usage["input_tokens"]
            diff = without_input - with_input
            pct = (diff / without_input * 100) if without_input > 0 else 0
            f.write(f"| Input Tokens | {with_input} | {without_input} | {diff:+d} ({pct:+.1f}%) |\n")
        else:
            f.write(f"| Input Tokens | (not captured) | (not captured) | — |\n")
        
        if with_usage.get("output_tokens") is not None and without_usage.get("output_tokens") is not None:
            with_output_tokens = with_usage["output_tokens"]
            without_output_tokens = without_usage["output_tokens"]
            diff = without_output_tokens - with_output_tokens
            pct = (diff / without_output_tokens * 100) if without_output_tokens > 0 else 0
            f.write(f"| Output Tokens | {with_output_tokens} | {without_output_tokens} | {diff:+d} ({pct:+.1f}%) |\n")
        else:
            f.write(f"| Output Tokens | (not captured) | (not captured) | — |\n")
        
        f.write(f"| Tool Calls | {with_usage['tool_calls']} | {without_usage['tool_calls']} | {with_usage['tool_calls'] - without_usage['tool_calls']:+d} |\n")
        
        f.write("\n## Duration Metrics\n\n")
        f.write("| Metric | WITH .repospec.json | WITHOUT .repospec.json | Difference |\n")
        f.write("|--------|---------------------|----------------------|------------|\n")
        
        with_duration = with_usage.get("duration_seconds", 0)
        without_duration = without_usage.get("duration_seconds", 0)
        duration_diff = without_duration - with_duration
        duration_pct = (duration_diff / without_duration * 100) if without_duration > 0 else 0
        f.write(f"| Total Duration (s) | {with_duration:.2f} | {without_duration:.2f} | {duration_diff:+.2f} ({duration_pct:+.1f}%) |\n")
        
        with_per_task = with_usage.get("per_task_duration_seconds", 0)
        without_per_task = without_usage.get("per_task_duration_seconds", 0)
        per_task_diff = without_per_task - with_per_task
        per_task_pct = (per_task_diff / without_per_task * 100) if without_per_task > 0 else 0
        f.write(f"| Per-Task Duration (s) | {with_per_task:.3f} | {without_per_task:.3f} | {per_task_diff:+.3f} ({per_task_pct:+.1f}%) |\n")
        
        f.write("\n## Path Accuracy\n\n")
        with_accuracy = with_metrics.get("accuracy", {})
        without_accuracy = without_metrics.get("accuracy", {})
        
        if with_accuracy.get("valid_paths") or without_accuracy.get("valid_paths"):
            f.write("| Metric | WITH .repospec.json | WITHOUT .repospec.json | Difference |\n")
            f.write("|--------|---------------------|----------------------|------------|\n")
            
            with_valid = with_accuracy.get("valid_paths", 0)
            with_invalid = with_accuracy.get("invalid_paths", 0)
            without_valid = without_accuracy.get("valid_paths", 0)
            without_invalid = without_accuracy.get("invalid_paths", 0)
            
            with_total = with_valid + with_invalid
            without_total = without_valid + without_invalid
            
            f.write(f"| Valid Path References | {with_valid} | {without_valid} | {with_valid - without_valid:+d} |\n")
            f.write(f"| Invalid Path References | {with_invalid} | {without_invalid} | {with_invalid - without_invalid:+d} |\n")
            
            with_pct = (with_valid / with_total * 100) if with_total > 0 else 0
            without_pct = (without_valid / without_total * 100) if without_total > 0 else 0
            
            f.write(f"| Accuracy | {with_pct:.1f}% | {without_pct:.1f}% | {with_pct - without_pct:+.1f}% |\n")
        
        f.write("\n## Task Completion\n\n")
        f.write(f"- **WITH .repospec.json:** {with_metrics['tasks_mentioned']}/8 tasks mentioned\n")
        f.write(f"- **WITHOUT .repospec.json:** {without_metrics['tasks_mentioned']}/8 tasks mentioned\n")
        
        if with_metrics['tasks_mentioned'] > without_metrics['tasks_mentioned']:
            f.write(f"\n✅ **Advantage:** .repospec.json +{with_metrics['tasks_mentioned'] - without_metrics['tasks_mentioned']} task completions\n")
        
        f.write("\n## Output Analysis\n\n")
        f.write(f"- Avg words per task (WITH): {with_metrics['avg_words_per_task']}\n")
        f.write(f"- Avg words per task (WITHOUT): {without_metrics['avg_words_per_task']}\n")
        
        f.write("\n## Files Generated\n\n")
        f.write(f"- `generated.repospec.json` - Agent-generated metadata\n")
        f.write(f"- `agent_with_repospec.log` - Output WITH .repospec.json\n")
        f.write(f"- `agent_without_repospec.log` - Output WITHOUT .repospec.json\n")
        f.write(f"- `RESULTS.md` - This summary\n")
    
    log_success("Results saved")
    
    print("")
    print(f"{Colors.BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Colors.NC}")
    print(f"{Colors.GREEN}Benchmark Complete! ({auth_method} auth){Colors.NC}")
    print(f"{Colors.BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Colors.NC}")
    print("")
    print(f"{Colors.YELLOW}Results saved to:{Colors.NC} {results_file}")
    print("")
    
    if repo_stats:
        print(f"{Colors.YELLOW}Repository Stats:{Colors.NC}")
        print(f"  - Files: {repo_stats['total_files']} | Dirs: {repo_stats['total_dirs']} | Size: {repo_stats['total_size_mb']} MB")
        print(f"  - Source: {repo_stats['source_files']} files | Tests: {repo_stats['test_files']} files")
        if repo_stats['languages']:
            langs = ", ".join([f"{k} ({v})" for k, v in sorted(repo_stats['languages'].items(), key=lambda x: x[1], reverse=True)[:3]])
            print(f"  - Top languages: {langs}")
        print("")
    
    print(f"{Colors.YELLOW}Benchmark Summary:{Colors.NC}")
    print(f"  WITH .repospec.json:")
    print(f"    - Words: {with_metrics['words']}")
    print(f"    - Tasks addressed: {with_metrics['tasks_mentioned']}/8")
    print(f"    - Tool calls: {with_metrics['usage']['tool_calls']}")
    print(f"    - Duration: {with_metrics['usage'].get('duration_seconds', 0):.2f}s total | {with_metrics['usage'].get('per_task_duration_seconds', 0):.3f}s/task")
    print(f"  WITHOUT .repospec.json:")
    print(f"    - Words: {without_metrics['words']}")
    print(f"    - Tasks addressed: {without_metrics['tasks_mentioned']}/8")
    print(f"    - Tool calls: {without_metrics['usage']['tool_calls']}")
    print(f"    - Duration: {without_metrics['usage'].get('duration_seconds', 0):.2f}s total | {without_metrics['usage'].get('per_task_duration_seconds', 0):.3f}s/task")
    
    if with_metrics['tasks_mentioned'] > without_metrics['tasks_mentioned']:
        delta = with_metrics['tasks_mentioned'] - without_metrics['tasks_mentioned']
        print(f"  {Colors.GREEN}✓ .repospec.json enabled {delta} more task completions{Colors.NC}")
    
    if with_metrics['usage']['tool_calls'] < without_metrics['usage']['tool_calls']:
        delta = without_metrics['usage']['tool_calls'] - with_metrics['usage']['tool_calls']
        print(f"  {Colors.GREEN}✓ .repospec.json reduced tool calls by {delta}{Colors.NC}")
    
    # Duration comparison
    with_duration = with_metrics['usage'].get('duration_seconds', 0)
    without_duration = without_metrics['usage'].get('duration_seconds', 0)
    if with_duration > 0 and without_duration > 0:
        duration_diff = without_duration - with_duration
        duration_pct = (duration_diff / without_duration * 100)
        if duration_diff > 0.1:  # only show if difference > 100ms
            print(f"  {Colors.GREEN}✓ .repospec.json was {abs(duration_pct):.1f}% faster ({abs(duration_diff):.2f}s saved){Colors.NC}")
        elif duration_diff < -0.1:
            print(f"  {Colors.YELLOW}ℹ .repospec.json was {abs(duration_pct):.1f}% slower ({abs(duration_diff):.2f}s additional){Colors.NC}")
    
    # Path accuracy
    with_accuracy = with_metrics.get("accuracy", {})
    without_accuracy = without_metrics.get("accuracy", {})
    
    if with_accuracy.get("valid_paths") or without_accuracy.get("valid_paths"):
        print(f"\n{Colors.YELLOW}Path Accuracy:{Colors.NC}")
        with_total = with_accuracy.get("valid_paths", 0) + with_accuracy.get("invalid_paths", 0)
        without_total = without_accuracy.get("valid_paths", 0) + without_accuracy.get("invalid_paths", 0)
        
        with_pct = (with_accuracy.get("valid_paths", 0) / with_total * 100) if with_total > 0 else 0
        without_pct = (without_accuracy.get("valid_paths", 0) / without_total * 100) if without_total > 0 else 0
        
        print(f"  - WITH .repospec.json: {with_pct:.1f}% accuracy ({with_accuracy.get('valid_paths', 0)}/{with_total} paths)")
        print(f"  - WITHOUT .repospec.json: {without_pct:.1f}% accuracy ({without_accuracy.get('valid_paths', 0)}/{without_total} paths)")
        
        if with_pct > without_pct:
            print(f"  {Colors.GREEN}✓ .repospec.json improved path accuracy by {with_pct - without_pct:.1f}%{Colors.NC}")
    
    print("")


def main():
    parser = argparse.ArgumentParser(
        description="Benchmark .repospec.json impact on agent code navigation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python3 repospec_benchmark.py /path/to/my-repo
  python3 repospec_benchmark.py /path/to/my-repo --output-dir ./results --timeout 600
"""
    )
    
    parser.add_argument(
        "repo",
        help="Path to the repository to benchmark"
    )
    parser.add_argument(
        "--output-dir",
        default="./repospec-benchmark",
        help="Output directory for results (default: ./repospec-benchmark)"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="Timeout per agent run in seconds (default: 300)"
    )
    parser.add_argument(
        "--auth-method",
        choices=["api_key", "oauth", "both"],
        default="oauth",
        help="Authentication method: 'oauth' (CLAUDE_CODE_OAUTH_TOKEN, claude.ai subscription), 'api_key' (ANTHROPIC_API_KEY), or 'both' (default: oauth)"
    )
    
    args = parser.parse_args()
    
    repo_path = validate_repo(args.repo)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    results_dir = output_dir / f"{repo_path.name}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    results_dir.mkdir(parents=True, exist_ok=True)
    
    print("")
    print(f"{Colors.BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Colors.NC}")
    print(f"{Colors.BLUE}  repospec Benchmark Tool{Colors.NC}")
    print(f"{Colors.BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Colors.NC}")
    print("")
    print(f"{Colors.YELLOW}Target repository:{Colors.NC} {repo_path}")
    print(f"{Colors.YELLOW}Output directory:{Colors.NC} {results_dir}")
    print(f"{Colors.YELLOW}Timeout per run:{Colors.NC} {args.timeout}s")
    print("")
    
    repospec, repospec_file = generate_repospec_json(repo_path, results_dir)
    if repospec_file:
        log_success(f"Saved to {repospec_file}")
    
    tasks = create_test_tasks()
    
    # Determine which auth methods to test
    auth_methods = []
    if args.auth_method == "both":
        auth_methods = ["api_key", "oauth"]
    else:
        auth_methods = [args.auth_method]
    
    # Run benchmarks for each auth method
    for auth_method in auth_methods:
        log_step(3, 4, f"Running agents with {auth_method} auth...")
        print("")
        
        try:
            with_output, with_usage, with_code = run_agent_with_repospec(repo_path, repospec, tasks, args.timeout, auth_method)
            without_output, without_usage, without_code = run_agent_without_repospec(repo_path, tasks, args.timeout, auth_method)
            
            # Save logs with auth method in filename
            auth_suffix = f"-{auth_method}" if args.auth_method == "both" else ""
            (results_dir / f"agent_with_repospec{auth_suffix}.log").write_text(with_output)
            (results_dir / f"agent_without_repospec{auth_suffix}.log").write_text(without_output)
            
            log_success(f"Both agents completed ({auth_method} auth)")
            
            # Generate results
            results_file = f"RESULTS{auth_suffix}.md" if args.auth_method == "both" else "RESULTS.md"
            print_results(results_dir / results_file, with_output, without_output, repo_path.name, repo_path, with_usage, without_usage, auth_method)
        
        except Exception as e:
            log_error(f"Error running benchmark with {auth_method} auth: {e}")
            continue


if __name__ == "__main__":
    main()
