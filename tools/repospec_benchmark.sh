#!/bin/bash
# repospec_benchmark.sh — Wrapper for the Python benchmark tool

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/repospec_benchmark.py"

if ! command -v python3 &> /dev/null; then
    echo "Error: python3 is required"
    exit 1
fi

exec python3 "$PYTHON_SCRIPT" "$@"
