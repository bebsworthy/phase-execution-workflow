#!/usr/bin/env bash
# Wrapper for pw.py — auto-creates venv if missing, runs with correct python.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LIB_DIR="$SCRIPT_DIR/lib"
VENV_DIR="$LIB_DIR/.venv"
VENV_PYTHON="$VENV_DIR/bin/python3"

if [ ! -f "$VENV_PYTHON" ]; then
  echo "Setting up pw.py venv..." >&2
  python3 -m venv "$VENV_DIR"
  "$VENV_DIR/bin/pip" install -q -r "$LIB_DIR/requirements.txt"
  echo "venv ready." >&2
fi

exec "$VENV_PYTHON" "$LIB_DIR/pw.py" "$@"
