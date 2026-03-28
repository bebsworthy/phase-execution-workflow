"""Shared constants and pure utility functions for the phase workflow manager."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

VERIFY_IDLE_TIMEOUT = 300  # seconds without output before killing verification
VERIFY_FAIL_TAIL_LINES = 30  # lines of output shown to agent on failure

VALID_STEP_STATUSES = {"not_started", "in_progress", "complete", "skipped"}
VALID_PHASE_SIZES = {"small", "medium", "large", "vibe", "audit"}
VALID_PHASE_MODES = {"manual", "auto", "autopilot"}
STEP_ORDER = ["ideas", "brd", "research", "spec", "plan", "build", "check"]

# Steps to auto-skip by phase size.  large = no skips (default).
SIZE_SKIP_STEPS: dict[str, set[str]] = {
    "large": set(),
    "medium": {"ideas"},
    "small": {"ideas", "research"},
    "audit": {"ideas", "research"},
    "vibe": {"ideas", "brd", "research", "spec", "plan"},
}
STEP_FILE = {
    "ideas": "IDEAS.md",
    "brd": "BRD.md",
    "research": "RESEARCH.md",
    "spec": "SPEC.md",
    "plan": "PLAN.md",
}
ID_PREFIX = {
    "ideas": "IDEA-",
    "brd": "FC-",
    "research": "R-",
    "spec": "T-",
    "plan": "PH-",
}
ID_PATTERN = {k: re.compile(rf"{re.escape(v)}(\d+)") for k, v in ID_PREFIX.items()}


def _norm_num(n: int | float) -> int | float:
    """Normalize phase number: 24.0 → 24, but 7.5 stays 7.5."""
    return int(n) if isinstance(n, float) and n == int(n) else n


def kebab_case(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower())
    return re.sub(r"-{2,}", "-", slug).strip("-")


def get_head_sha(root: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, cwd=root,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except FileNotFoundError:
        pass
    return None
