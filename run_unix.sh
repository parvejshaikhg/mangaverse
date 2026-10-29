#!/usr/bin/env bash
# ==============================================================================
# MangaVerse Cross-Platform Launcher for Linux and macOS
# ==============================================================================

set -e

# Change directory to the script's directory
cd "$(dirname "$0")"

echo "========================================================"
echo "  Starting MangaVerse (Linux / macOS Launcher)"
echo "========================================================"

# Determine Python command
if command -v python3 &>/dev/null; then
    PY_CMD="python3"
elif command -v python &>/dev/null; then
    PY_CMD="python"
else
    echo "Error: Python 3 was not found on your system."
    echo "Please install Python 3.10+ to continue."
    exit 1
fi

# Launch MangaVerse with any arguments passed
exec "$PY_CMD" main.py "$@"
