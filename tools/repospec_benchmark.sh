#!/bin/bash
# repospec_benchmark.sh — Wrapper for the Python benchmark tool.
# Bootstraps a local virtualenv with the required dependencies, then runs the tool.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/repospec_benchmark.py"
REQUIREMENTS="$SCRIPT_DIR/requirements.txt"
VENV_DIR="${REPOSPEC_VENV:-$SCRIPT_DIR/.venv}"

if ! command -v python3 &> /dev/null; then
    echo "Error: python3 is required" >&2
    exit 1
fi

# Create the virtualenv on first run.
if [ ! -d "$VENV_DIR" ]; then
    echo "Setting up Python virtualenv at $VENV_DIR ..." >&2
    python3 -m venv "$VENV_DIR"
fi

VENV_PY="$VENV_DIR/bin/python"

# Install/refresh dependencies if anthropic is missing.
if ! "$VENV_PY" -c "import anthropic" &> /dev/null; then
    echo "Installing dependencies from requirements.txt ..." >&2
    "$VENV_PY" -m pip install --quiet --upgrade pip
    "$VENV_PY" -m pip install --quiet -r "$REQUIREMENTS"
fi

exec "$VENV_PY" "$PYTHON_SCRIPT" "$@"
