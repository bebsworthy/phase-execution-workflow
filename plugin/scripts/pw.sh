#!/usr/bin/env bash
# Wrapper for pw.py — auto-creates venv if missing, runs with correct python.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LIB_DIR="$SCRIPT_DIR/lib"
VENV_DIR="$LIB_DIR/.venv"
VENV_PYTHON="$VENV_DIR/bin/python3"

# For dump-config (fired by plugin hooks on every prompt), skip entirely
# if no pew.yaml exists anywhere up the directory tree. This avoids
# bootstrapping the Python venv and wasting context in non-PEW repos.
if [ "${1:-}" = "dump-config" ]; then
  dir="$PWD"
  found=false
  while [ "$dir" != "/" ]; do
    [ -f "$dir/pew.yaml" ] && found=true && break
    dir="$(dirname "$dir")"
  done
  if [ "$found" = "false" ]; then
    exit 0
  fi
fi

if [ ! -f "$VENV_PYTHON" ]; then
  echo "Setting up pw.py venv..." >&2
  python3 -m venv "$VENV_DIR"
  "$VENV_DIR/bin/pip" install -q -r "$LIB_DIR/requirements.txt"
  echo "venv ready." >&2
fi

exec "$VENV_PYTHON" "$LIB_DIR/pw.py" "$@"
