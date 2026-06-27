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
"""

import argparse
import json
import os
import sys
import subprocess
import time
from datetime import datetime
from pathlib import Path


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


def generate_repospec_json(repo_path, output_dir):
    """Generate .repospec.json using Claude."""
    log_step(1, 4, "Generating .repospec.json for target repo...")
    
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

    log_info("Invoking Claude to generate .repospec.json...")
    
    try:
        result = subprocess.run(
            ["claude"],
            input=generation_prompt,
            capture_output=True,
            text=True,
            timeout=90
        )
        
        if result.returncode != 0:
            log_warning(f"Claude returned error")
            return get_minimal_repospec(context), None
        
        output = result.stdout.strip()
        
        # Try to extract JSON
        try:
            import re
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
    
    except subprocess.TimeoutExpired:
        log_error("Claude request timed out")
        return get_minimal_repospec(context), None
    except FileNotFoundError:
        log_error("Claude CLI not found. Install with: pip install anthropic-cli")
        sys.exit(1)


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


def create_test_tasks():
    """Create a set of code-finding test tasks."""
    log_step(2, 4, "Creating code-finding test tasks...")
    
    tasks = [
        "Task 1: List all entry points in this repository. For each, identify the file path and a one-sentence description of its purpose.",
        
        "Task 2: Identify the main modules or packages in this codebase. For each module, describe its purpose and which other modules it depends on.",
        
        "Task 3: Find where authentication/authorization logic is defined. Describe the pattern: how are authenticated requests handled?",
        
        "Task 4: What are the 3-5 key features or capabilities of this system? For each feature, describe the main files involved.",
        
        "Task 5: What are the 3-5 most critical files to understand in this codebase? Why each one?",
        
        "Task 6: Describe the test structure: where are unit tests, integration tests, and test fixtures located?",
        
        "Task 7: What are the major external dependencies and what role does each play in the system?",
        
        "Task 8: If you needed to add a new feature, what files would you need to modify and in what order?"
    ]
    
    log_success("Created 8 test tasks")
    return tasks


def run_agent_with_repospec(repo_path, repospec, tasks, timeout=300):
    """Run agent WITH .repospec.json context."""
    log_info("Running agent WITH .repospec.json context...")
    
    prompt = f"""You are an expert code navigator. You have been given a .repospec.json file that describes a repository structure.

Here's the .repospec.json for the repository:
```json
{json.dumps(repospec, indent=2)}
```

Now, use this as your guide to answer the following tasks. Reference .repospec.json where relevant, then verify by examining the actual repository at: {repo_path}

{chr(10).join(tasks)}

For each task, work systematically using .repospec.json as your starting point. Be specific and reference files/functions by name."""

    try:
        result = subprocess.run(
            ["claude"],
            input=prompt,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result.stdout, result.returncode
    except subprocess.TimeoutExpired:
        return "TIMEOUT", 124
    except FileNotFoundError:
        log_error("Claude CLI not found")
        sys.exit(1)


def run_agent_without_repospec(repo_path, tasks, timeout=300):
    """Run agent WITHOUT .repospec.json context."""
    log_info("Running agent WITHOUT .repospec.json context...")
    
    prompt = f"""You are an expert code navigator. You have been asked to understand a repository by exploring the files directly.

The repository is located at: {repo_path}

Answer the following tasks by examining the code:

{chr(10).join(tasks)}

Work systematically without any pre-generated metadata. Be specific and reference files/functions by name."""

    try:
        result = subprocess.run(
            ["claude"],
            input=prompt,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result.stdout, result.returncode
    except subprocess.TimeoutExpired:
        return "TIMEOUT", 124
    except FileNotFoundError:
        log_error("Claude CLI not found")
        sys.exit(1)


def analyze_response(response, label):
    """Analyze agent response metrics."""
    lines = response.split('\n')
    words = response.split()
    
    tasks_mentioned = sum(1 for i in range(1, 9) if f"Task {i}" in response)
    
    return {
        "label": label,
        "response_length": len(response),
        "lines": len(lines),
        "words": len(words),
        "tasks_mentioned": tasks_mentioned,
        "avg_words_per_task": len(words) // max(1, tasks_mentioned)
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


def print_results(results_dir, with_spec_output, without_spec_output, repo_name, repo_path=None):
    """Print and save benchmark results."""
    log_step(4, 4, "Analyzing results...")
    
    with_metrics = analyze_response(with_spec_output, "WITH .repospec.json")
    without_metrics = analyze_response(without_spec_output, "WITHOUT .repospec.json")
    
    repo_stats = None
    if repo_path:
        repo_stats = quantify_repo(repo_path)
    
    results_file = results_dir / "RESULTS.md"
    
    with open(results_file, 'w') as f:
        f.write("# .repospec.json Benchmark Results\n\n")
        f.write(f"**Repository:** {repo_name}\n")
        f.write(f"**Date:** {datetime.now().isoformat()}\n\n")
        
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
        
        f.write("## Metrics\n\n")
        f.write("| Metric | WITH .repospec.json | WITHOUT .repospec.json | Difference |\n")
        f.write("|--------|---------------------|----------------------|------------|\n")
        
        for key in ["response_length", "lines", "words"]:
            with_val = with_metrics[key]
            without_val = without_metrics[key]
            diff = with_val - without_val
            f.write(f"| {key} | {with_val} | {without_val} | {diff:+d} |\n")
        
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
    print(f"{Colors.GREEN}Benchmark Complete!{Colors.NC}")
    print(f"{Colors.BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Colors.NC}")
    print("")
    print(f"{Colors.YELLOW}Results saved to:{Colors.NC} {results_dir}")
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
    print(f"  WITHOUT .repospec.json:")
    print(f"    - Words: {without_metrics['words']}")
    print(f"    - Tasks addressed: {without_metrics['tasks_mentioned']}/8")
    
    if with_metrics['tasks_mentioned'] > without_metrics['tasks_mentioned']:
        delta = with_metrics['tasks_mentioned'] - without_metrics['tasks_mentioned']
        print(f"  {Colors.GREEN}✓ .repospec.json enabled {delta} more task completions{Colors.NC}")
    
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
    
    log_step(3, 4, "Running agents in parallel...")
    print("")
    
    with_output, _ = run_agent_with_repospec(repo_path, repospec, tasks, args.timeout)
    without_output, _ = run_agent_without_repospec(repo_path, tasks, args.timeout)
    
    (results_dir / "agent_with_repospec.log").write_text(with_output)
    (results_dir / "agent_without_repospec.log").write_text(without_output)
    
    log_success("Both agents completed")
    
    print_results(results_dir, with_output, without_output, repo_path.name, repo_path)


if __name__ == "__main__":
    main()
