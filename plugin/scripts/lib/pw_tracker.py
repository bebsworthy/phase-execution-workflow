"""Phase tracker: load, save, find, render plan, detect step file completion."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from pw_util import STEP_ORDER, STEP_FILE, _norm_num, kebab_case
from pw_config import DEFAULT_CONFIG


def tracker_path(root: Path, config: dict | None = None) -> Path:
    if config:
        return root / config["paths"]["tracker"]
    return root / DEFAULT_CONFIG["paths"]["tracker"]


def plan_path(root: Path, config: dict | None = None) -> Path:
    if config:
        return root / config["paths"]["plan"]
    return root / DEFAULT_CONFIG["paths"]["plan"]


def load_tracker(root: Path, config: dict | None = None) -> dict:
    path = tracker_path(root, config)
    if not path.exists():
        return {"phases": []}
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if data is None or "phases" not in data or data["phases"] is None:
        return {"phases": []}
    # Ensure each phase has all expected fields
    for phase in data["phases"]:
        phase["number"] = _norm_num(phase["number"])
        phase.setdefault("brief", "")
        phase.setdefault("brief_file", "")
        phase.setdefault("refs", [])
        phase.setdefault("summary", "")
        phase.setdefault("depends_on", [])
        phase.setdefault("tags", [])
        phase.setdefault("size", "large")
        phase.setdefault("mode", "manual")
        phase.setdefault("start_commit", None)
        phase.setdefault("end_commit", None)
        phase.setdefault("steps", {})
        for step in STEP_ORDER:
            phase["steps"].setdefault(step, "not_started")
    return data


def save_tracker(root: Path, data: dict, config: dict | None = None) -> None:
    path = tracker_path(root, config)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.dump(data, default_flow_style=False, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


def find_phase(data: dict, phase_number: int | float) -> dict | None:
    phase_number = _norm_num(phase_number)
    for phase in data.get("phases", []):
        if _norm_num(phase["number"]) == phase_number:
            return phase
    return None


def phase_dir(root: Path, phase: dict, config: dict | None = None) -> Path:
    slug = kebab_case(f"phase-{phase['number']}-{phase['title']}")
    phases_dir = (config or DEFAULT_CONFIG)["paths"]["phases"]
    return root / phases_dir / slug


def render_plan(root: Path, data: dict, config: dict | None = None) -> None:
    path = plan_path(root, config)
    if not path.exists():
        return

    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    table_header_marker = "## 1.1 Phase Status Tracker"
    header_idx = None
    for i, line in enumerate(lines):
        if line.strip().startswith(table_header_marker):
            header_idx = i
            break

    if header_idx is None:
        return

    table_start = None
    table_end = None
    for i in range(header_idx + 1, len(lines)):
        if lines[i].strip().startswith("| Phase"):
            table_start = i
            continue
        if table_start is not None and lines[i].strip().startswith("| ---"):
            continue
        if table_start is not None and lines[i].strip().startswith("|"):
            table_end = i + 1
            continue
        if table_start is not None and not lines[i].strip().startswith("|"):
            break

    if table_start is None:
        table_start = header_idx + 3
        table_end = table_start

    if table_end is None:
        table_end = table_start + 2

    table_lines = [
        "| Phase | Status | Summary | Tags | Depends On |",
        "| ----- | ------ | ------- | ---- | ---------- |",
    ]
    for phase in sorted(data.get("phases", []), key=lambda p: p["number"]):
        title = f"Phase {phase['number']} {phase['title']}"
        status = phase.get("status", "not_started")
        summary = phase.get("summary", "") or ""
        tags = ", ".join(phase.get("tags", []))
        deps = ", ".join(str(d) for d in phase.get("depends_on", []))
        table_lines.append(f"| {title} | {status} | {summary} | {tags} | {deps} |")

    before = lines[:header_idx + 1]
    after_content = lines[table_end:]

    preamble_lines = []
    for i in range(header_idx + 1, min(table_start, len(lines))):
        line = lines[i]
        if not line.strip().startswith("|"):
            preamble_lines.append(line)

    result = before + preamble_lines + table_lines + [""] + after_content
    path.write_text("\n".join(result) + "\n", encoding="utf-8")


def detect_step_file_completion(path: Path) -> tuple[bool, list[str]]:
    if not path.exists():
        return False, [f"missing file: {path.name}"]

    text = path.read_text(encoding="utf-8")
    reasons: list[str] = []

    meta = re.search(r"^status:\s*(\S+)\s*$", text, flags=re.MULTILINE)
    if meta and meta.group(1).strip() == "not_started":
        reasons.append("metadata status is not_started")

    if re.search(r"^- \[ \]", text, flags=re.MULTILINE):
        reasons.append("contains unchecked checklist items")

    return len(reasons) == 0, reasons
