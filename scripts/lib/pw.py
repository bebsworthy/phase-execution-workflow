#!/usr/bin/env python3
"""Phase workflow manager: YAML-based phase tracker with lifecycle commands.

Requires PyYAML. Use the wrapper: bash scripts/pw.sh <command>
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

import yaml

VALID_STEP_STATUSES = {"not_started", "in_progress", "complete", "skipped"}
VALID_PHASE_SIZES = {"small", "medium", "large", "vibe"}
STEP_ORDER = ["ideas", "brd", "research", "spec", "plan", "build", "check"]

# Steps to auto-skip by phase size.  large = no skips (default).
SIZE_SKIP_STEPS: dict[str, set[str]] = {
    "large": set(),
    "medium": {"ideas"},
    "small": {"ideas", "research"},
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

DEFAULT_CONFIG: dict = {
    "project": {"name": "My Project", "description": ""},
    "paths": {
        "tracker": "phases/phase-tracker.yaml",
        "plan": "phases/implementation-plan.md",
        "phases": "phases",
        "research": "phases/research",
        "audit_test": "phases/audit/test",
        "audit_ux": "phases/audit/ux",
        "guidelines": "",
    },
    "commands": {"verify": "", "e2e": ""},
    "stack": {
        "description": "",
        "frontend_src": "",
        "component_paths": [],
        "install_commands": {},
    },
    "competitors": [],
    "conventions_file": "",
    "council": {
        "enabled": True,
        "experts": [],
        "max_findings_per_expert": 15,
        "skip_tags": [],
    },
    "approval_gates": {
        "before_build": True,
        "before_close": True,
    },
    "product_review": {
        "enabled": True,
        "app_url": "http://localhost:5173",
        "start_command": "",
    },
}


# ---------------------------------------------------------------------------
# Core helpers
# ---------------------------------------------------------------------------

def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge *override* into a copy of *base*.

    - Dicts are merged recursively.
    - All other types (lists, scalars) in *override* replace *base*.
    """
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_config(root: Path) -> dict:
    """Load pew.yaml from *root* and merge with defaults."""
    config_path = root / "pew.yaml"
    if not config_path.exists():
        return _deep_merge(DEFAULT_CONFIG, {})
    user_config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    return _deep_merge(DEFAULT_CONFIG, user_config)


def repo_root_from_script() -> Path:
    """Find the repo root by walking up from CWD looking for .git or pew.yaml.

    Uses CWD instead of __file__ so this works when the script is installed
    as a plugin (where __file__ is inside ~/.claude/plugins/cache/).
    """
    cwd = Path.cwd()
    for parent in [cwd] + list(cwd.parents):
        if (parent / ".git").exists() or (parent / "pew.yaml").exists():
            return parent
    return cwd


def _norm_num(n: int | float) -> int | float:
    """Normalize phase number: 24.0 → 24, but 7.5 stays 7.5."""
    return int(n) if isinstance(n, float) and n == int(n) else n


def kebab_case(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower())
    return re.sub(r"-{2,}", "-", slug).strip("-")


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
        phase.setdefault("refs", [])
        phase.setdefault("summary", "")
        phase.setdefault("depends_on", [])
        phase.setdefault("tags", [])
        phase.setdefault("size", "large")
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


# ---------------------------------------------------------------------------
# render_plan: YAML -> implementation-plan.md table
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# detect_step_file_completion
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_analyze_phase(args: argparse.Namespace) -> int:
    root = Path(args.repo_root).resolve() if args.repo_root else repo_root_from_script()
    config = load_config(root)
    data = load_tracker(root, config)
    phase = find_phase(data, args.phase)
    if phase is None:
        print(f"Phase {args.phase} not found in tracker.")
        return 1

    pdir = phase_dir(root, phase, config)
    step_analysis: dict[str, dict] = {}

    for step in STEP_ORDER:
        tracker_status = phase["steps"].get(step, "not_started")
        if tracker_status == "skipped":
            step_analysis[step] = {
                "tracker_status": "skipped",
                "complete": True,
                "reasons": [],
            }
        elif step in STEP_FILE:
            file_path = pdir / STEP_FILE[step]
            is_complete, reasons = detect_step_file_completion(file_path)
            step_analysis[step] = {
                "file": str(file_path),
                "exists": file_path.exists(),
                "tracker_status": tracker_status,
                "complete": is_complete and tracker_status == "complete",
                "reasons": reasons,
            }
        else:
            step_analysis[step] = {
                "tracker_status": tracker_status,
                "complete": tracker_status == "complete",
                "reasons": [],
            }

    first_incomplete = None
    for step in STEP_ORDER:
        if not step_analysis[step]["complete"]:
            first_incomplete = step
            break

    result = {
        "phase_number": phase["number"],
        "phase_title": phase["title"],
        "phase_dir": str(pdir),
        "tracker_status": phase["status"],
        "size": phase.get("size", "large"),
        "refs": phase.get("refs", []),
        "steps": step_analysis,
        "first_incomplete_step": first_incomplete,
    }

    if args.json:
        print(json.dumps(result, indent=2))
        return 0

    print(f"Phase {phase['number']}: {phase['title']}")
    print(f"Phase directory: {pdir}")
    print(f"Tracker status: {phase['status']}")
    print("Steps:")
    for step in STEP_ORDER:
        info = step_analysis[step]
        state = "complete" if info["complete"] else "incomplete"
        status_str = f"[{info['tracker_status']}]"
        file_str = f" ({info.get('file', '')})" if "file" in info else ""
        print(f"  {step}: {state} {status_str}{file_str}")
        for reason in info.get("reasons", []):
            print(f"    - {reason}")
    if first_incomplete:
        print(f"First incomplete step: {first_incomplete}")
    else:
        print("All steps complete.")
    return 0


def cmd_add_phase(args: argparse.Namespace) -> int:
    root = Path(args.repo_root).resolve() if args.repo_root else repo_root_from_script()
    config = load_config(root)
    data = load_tracker(root, config)

    if find_phase(data, args.number) is not None:
        print(f"Phase {args.number} already exists in tracker.")
        return 1

    depends_on = []
    if args.depends_on:
        depends_on = [_norm_num(float(x.strip())) for x in args.depends_on.split(",") if x.strip()]

    tags = []
    if args.tags:
        tags = [x.strip() for x in args.tags.split(",") if x.strip()]

    refs = []
    if args.refs:
        refs = [x.strip() for x in args.refs.split(",") if x.strip()]

    size = args.size or "large"
    skip_steps = SIZE_SKIP_STEPS.get(size, set())

    phase = {
        "number": _norm_num(args.number),
        "title": args.title,
        "brief": args.brief or "",
        "refs": refs,
        "status": "not_started",
        "summary": "",
        "depends_on": depends_on,
        "tags": tags,
        "size": size,
        "start_commit": None,
        "end_commit": None,
        "steps": {
            s: ("skipped" if s in skip_steps else "not_started")
            for s in STEP_ORDER
        },
    }
    data["phases"].append(phase)
    data["phases"].sort(key=lambda p: p["number"])

    save_tracker(root, data, config)
    render_plan(root, data, config)

    print(f"Added Phase {args.number} {args.title}")
    return 0


def cmd_list_phases(args: argparse.Namespace) -> int:
    root = Path(args.repo_root).resolve() if args.repo_root else repo_root_from_script()
    config = load_config(root)
    data = load_tracker(root, config)
    phases = data.get("phases", [])

    if args.status:
        phases = [p for p in phases if p.get("status") == args.status]

    if args.json:
        print(json.dumps(phases, indent=2))
        return 0

    if not phases:
        print("No phases found.")
        return 0

    for phase in phases:
        deps = ", ".join(str(d) for d in phase.get("depends_on", []))
        tags = ", ".join(phase.get("tags", []))
        print(f"Phase {phase['number']}: {phase['title']} [{phase['status']}]"
              + (f" deps=[{deps}]" if deps else "")
              + (f" tags=[{tags}]" if tags else ""))
    return 0


def cmd_set_step_status(args: argparse.Namespace) -> int:
    root = Path(args.repo_root).resolve() if args.repo_root else repo_root_from_script()
    config = load_config(root)
    if args.step not in STEP_ORDER:
        print(f"Invalid step '{args.step}'. Expected: {', '.join(STEP_ORDER)}")
        return 1
    if args.status not in VALID_STEP_STATUSES:
        print(f"Invalid status '{args.status}'. Expected: {', '.join(sorted(VALID_STEP_STATUSES))}")
        return 1

    data = load_tracker(root, config)
    phase = find_phase(data, args.phase)
    if phase is None:
        print(f"Phase {args.phase} not found in tracker.")
        return 1

    # When starting a step (in_progress), verify all prior steps are complete
    if args.status == "in_progress":
        step_idx = STEP_ORDER.index(args.step)
        for prev_step in STEP_ORDER[:step_idx]:
            prev_status = phase["steps"].get(prev_step, "not_started")
            if prev_status not in ("complete", "skipped"):
                print(
                    f"Cannot start '{args.step}': prior step '{prev_step}' "
                    f"is '{prev_status}' (must be complete or skipped)."
                )
                return 1

        # Auto-init: create phase dir + set phase started on first step start
        if phase.get("status") == "not_started":
            pdir = phase_dir(root, phase, config)
            pdir.mkdir(parents=True, exist_ok=True)
            phase["status"] = "started"
            sha = get_head_sha(root)
            if sha:
                phase["start_commit"] = sha
            print(f"Auto-initialized Phase {phase['number']} {phase['title']}")
            print(f"Phase directory: {pdir}")

    phase["steps"][args.step] = args.status

    # Auto-close: when check step completes, set phase to complete
    if args.step == "check" and args.status == "complete":
        phase["status"] = "complete"
        sha = get_head_sha(root)
        if sha:
            phase["end_commit"] = sha
        print(f"Phase {phase['number']} auto-closed as complete.")

    save_tracker(root, data, config)
    render_plan(root, data, config)

    print(f"Phase {phase['number']} step '{args.step}' -> {args.status}")
    return 0


def cmd_verify_traceability(args: argparse.Namespace) -> int:
    root = Path(args.repo_root).resolve() if args.repo_root else repo_root_from_script()
    config = load_config(root)
    data = load_tracker(root, config)
    phase = find_phase(data, args.phase)
    if phase is None:
        print(f"Phase {args.phase} not found in tracker.")
        return 1

    pdir = phase_dir(root, phase, config)
    from_step = args.from_step
    to_step = args.to

    if from_step not in ID_PATTERN or to_step not in ID_PATTERN:
        print(f"No traceability pattern defined for '{from_step}' or '{to_step}'.")
        return 1

    source_file = STEP_FILE.get(from_step)
    target_file = STEP_FILE.get(to_step)
    if not source_file or not target_file:
        print(f"No artifact file for '{from_step}' or '{to_step}'.")
        return 1

    source_path = pdir / source_file
    target_path = pdir / target_file

    if not source_path.exists():
        print(f"Source file not found: {source_path}")
        return 1
    if not target_path.exists():
        print(f"Target file not found: {target_path}")
        return 1

    source_text = source_path.read_text(encoding="utf-8")
    target_text = target_path.read_text(encoding="utf-8")
    source_prefix = ID_PREFIX[from_step]
    source_pattern = ID_PATTERN[from_step]

    # For IDEAS, only trace selected items
    if from_step == "ideas":
        selected_blocks = re.findall(r"\[selected\].*", source_text, re.IGNORECASE)
        source_ids = []
        for block in selected_blocks:
            source_ids.extend(
                f"{source_prefix}{m}" for m in source_pattern.findall(block)
            )
    else:
        source_ids = [
            f"{source_prefix}{m}" for m in source_pattern.findall(source_text)
        ]

    source_ids = sorted(set(source_ids))

    def _id_present(sid: str, text: str) -> bool:
        return re.search(rf"{re.escape(sid)}(?!\d)", text) is not None

    covered = [sid for sid in source_ids if _id_present(sid, target_text)]
    missing = [sid for sid in source_ids if not _id_present(sid, target_text)]

    result = {
        "covered": covered,
        "missing": missing,
        "source_count": len(source_ids),
    }
    print(json.dumps(result, indent=2))
    return 0 if not missing else 1


def _phase_completed_through(phase: dict, step: str) -> bool:
    """Check if a phase has completed all steps up to and including *step*.

    Skipped steps count as completed.
    """
    for s in STEP_ORDER:
        status = phase["steps"].get(s, "not_started")
        if status not in ("complete", "skipped"):
            return False
        if s == step:
            return True
    return False


def cmd_check_dependencies(args: argparse.Namespace) -> int:
    root = Path(args.repo_root).resolve() if args.repo_root else repo_root_from_script()
    config = load_config(root)
    data = load_tracker(root, config)
    phase = find_phase(data, args.phase)
    if phase is None:
        print(f"Phase {args.phase} not found in tracker.")
        return 1

    through = getattr(args, "through", None)
    if through and through not in STEP_ORDER:
        print(f"Invalid step '{through}'. Expected: {', '.join(STEP_ORDER)}")
        return 1

    depends_on = phase.get("depends_on", [])
    met = []
    unmet = []

    for dep_num in depends_on:
        dep_phase = find_phase(data, dep_num)
        if dep_phase is None:
            unmet.append(dep_num)
            continue

        if through:
            is_met = _phase_completed_through(dep_phase, through)
        else:
            is_met = dep_phase.get("status") == "complete"

        if is_met:
            met.append(dep_num)
        else:
            unmet.append(dep_num)

    satisfied = len(unmet) == 0
    result = {
        "satisfied": satisfied,
        "met": met,
        "unmet": unmet,
    }
    print(json.dumps(result, indent=2))
    return 0 if satisfied else 1


def cmd_phase_diff(args: argparse.Namespace) -> int:
    root = Path(args.repo_root).resolve() if args.repo_root else repo_root_from_script()
    config = load_config(root)
    data = load_tracker(root, config)
    phase = find_phase(data, args.phase)
    if phase is None:
        print(f"Phase {args.phase} not found in tracker.")
        return 1

    start_commit = phase.get("start_commit")
    if not start_commit:
        print(f"Phase {args.phase} has no start_commit recorded.")
        return 1

    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", f"{start_commit}...HEAD"],
            capture_output=True, text=True, cwd=root,
        )
        if result.returncode != 0:
            print(f"git diff failed: {result.stderr.strip()}")
            return 1
        print(result.stdout.strip())
    except FileNotFoundError:
        print("git not found.")
        return 1
    return 0


CONFIG_SCOPES: dict[str, list[str]] = {
    "agent": ["project", "paths", "stack", "conventions_file"],
    "council": ["project", "paths", "council", "conventions_file"],
    "research": ["project", "paths", "stack", "competitors"],
}


def _strip_empty(obj: object) -> object:
    """Recursively remove keys whose values are empty strings, empty lists, or empty dicts."""
    if isinstance(obj, dict):
        return {k: _strip_empty(v) for k, v in obj.items()
                if v not in ("", [], {})}
    if isinstance(obj, list):
        return [_strip_empty(item) for item in obj]
    return obj


def cmd_dump_config(args: argparse.Namespace) -> int:
    root = Path(args.repo_root).resolve() if args.repo_root else repo_root_from_script()
    config = load_config(root)
    scope = getattr(args, "scope", None)
    if scope and scope in CONFIG_SCOPES:
        config = {k: config[k] for k in CONFIG_SCOPES[scope] if k in config}
    config = _strip_empty(config)
    print(json.dumps(config, separators=(",", ":")))
    return 0


# ---------------------------------------------------------------------------
# resolve-profiles: match review profiles against file list
# ---------------------------------------------------------------------------

def _parse_profile_frontmatter(path: Path) -> dict | None:
    """Parse YAML frontmatter from a review profile markdown file."""
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\s*\n(.*?\n)---\s*\n", text, re.DOTALL)
    if not m:
        return None
    try:
        meta = yaml.safe_load(m.group(1))
    except yaml.YAMLError:
        return None
    if not isinstance(meta, dict):
        return None
    meta["_path"] = str(path)
    meta["_content"] = text[m.end():]
    meta["_raw"] = text
    return meta


def _match_profile(meta: dict, files: list[str]) -> bool:
    """Check if a profile matches the given file list based on keywords and match rules."""
    import fnmatch

    # Match by file_patterns in matches section
    matches = meta.get("matches", {})
    if isinstance(matches, dict):
        file_patterns = matches.get("file_patterns", [])
        if file_patterns:
            for f in files:
                basename = Path(f).name
                for pat in file_patterns:
                    if fnmatch.fnmatch(basename, pat) or fnmatch.fnmatch(f, f"**/{pat}"):
                        return True

    # Match by keywords against file extensions and path segments
    keywords = set(meta.get("keywords", []))
    if not keywords:
        return False

    # Build a set of signals from the file list
    signals: set[str] = set()
    for f in files:
        p = Path(f)
        ext = p.suffix.lstrip(".")
        if ext:
            signals.add(ext)
        for part in p.parts:
            signals.add(part.lower())

    # Extension-to-keyword mapping
    ext_map = {
        "ts": {"typescript", "ts"},
        "tsx": {"typescript", "ts", "react", "tsx", "jsx", "component"},
        "js": {"javascript", "js"},
        "jsx": {"javascript", "js", "react", "jsx", "component"},
        "sql": {"sql", "postgresql", "postgres"},
        "css": {"css", "styling"},
    }
    for ext in signals.copy():
        if ext in ext_map:
            signals.update(ext_map[ext])

    return bool(keywords & signals)


def _resolve_extends(meta: dict, profiles_dir: Path, loaded: dict[str, dict]) -> list[dict]:
    """Resolve profile extends chain, returning parents lowest-priority-first."""
    extends = meta.get("extends", [])
    if not extends:
        return []
    parents: list[dict] = []
    for ext_path in extends:
        full_path = (profiles_dir / ext_path).resolve()
        key = str(full_path)
        if key in loaded:
            parents.append(loaded[key])
            continue
        if full_path.exists():
            parent_meta = _parse_profile_frontmatter(full_path)
            if parent_meta:
                loaded[key] = parent_meta
                grandparents = _resolve_extends(parent_meta, profiles_dir, loaded)
                parents = grandparents + [parent_meta] + parents
    return parents


def _summarize_profile(meta: dict) -> str:
    """Condensed summary: headers + first sentence of rules, no code blocks."""
    content = meta["_content"]
    # Strip code blocks
    content = re.sub(r"```[\s\S]*?```", "", content)

    lines = content.split("\n")
    summary_lines: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#"):
            summary_lines.append(stripped)
            continue
        # Bold items (rules, anti-patterns)
        bold_match = re.match(r"^([-*]\s+)?\*\*(.+?)\*\*[:\s.]*(.*)", stripped)
        if bold_match:
            prefix = bold_match.group(1) or ""
            title = bold_match.group(2)
            rest = bold_match.group(3).strip()
            first_sentence = re.split(r"[.!?]", rest)[0].strip() if rest else ""
            if first_sentence:
                summary_lines.append(f"{prefix}**{title}** — {first_sentence}.")
            else:
                summary_lines.append(f"{prefix}**{title}**")
            continue
        # Checklist items
        if re.match(r"^- \[[ x]\]", stripped):
            summary_lines.append(stripped)

    return "\n".join(summary_lines)


def cmd_resolve_profiles(args: argparse.Namespace) -> int:
    profiles_dir = Path(args.profiles_dir).resolve()
    if not profiles_dir.is_dir():
        print(f"Profiles directory not found: {profiles_dir}", file=sys.stderr)
        return 1

    files = [f.strip() for f in args.files.split(",") if f.strip()] if args.files else []

    # Collect matching profiles (skip _-prefixed files unless pulled via extends)
    all_profiles: list[dict] = []
    for md_file in sorted(profiles_dir.rglob("*.md")):
        if md_file.name.startswith("_"):
            continue
        meta = _parse_profile_frontmatter(md_file)
        if meta and _match_profile(meta, files):
            all_profiles.append(meta)

    if not all_profiles:
        if args.json:
            print(json.dumps({"profiles": [], "output": ""}, indent=2))
        else:
            print("No matching profiles found.")
        return 0

    # Resolve extends chain and deduplicate
    loaded: dict[str, dict] = {}
    resolved: list[dict] = []
    seen_paths: set[str] = set()

    for meta in all_profiles:
        parents = _resolve_extends(meta, profiles_dir, loaded)
        for p in parents:
            if p["_path"] not in seen_paths:
                seen_paths.add(p["_path"])
                resolved.append(p)
        if meta["_path"] not in seen_paths:
            seen_paths.add(meta["_path"])
            resolved.append(meta)

    # Sort by priority (lowest first)
    resolved.sort(key=lambda m: m.get("priority", 99))

    profile_names = [m.get("name", "unknown") for m in resolved]

    if args.json:
        result = {
            "profiles": [
                {"name": m.get("name"), "priority": m.get("priority", 99), "path": m["_path"]}
                for m in resolved
            ],
        }
        print(json.dumps(result, indent=2))
        return 0

    # Output: full or summary
    output_parts: list[str] = []
    for meta in resolved:
        name = meta.get("name", "unknown")
        priority = meta.get("priority", 99)

        if args.summary:
            header = f"## {name} (priority {priority}) — {meta['_path']}"
            summary = _summarize_profile(meta)
            output_parts.append(f"{header}\n{summary}")
        else:
            output_parts.append(meta["_raw"])

    chain = " → ".join(profile_names)
    print(f"Applying: {chain} — {len(resolved)} profiles", file=sys.stderr)
    print("\n\n---\n\n".join(output_parts))
    return 0


# ---------------------------------------------------------------------------
# extract-ids: compact FC/T index from BRD + SPEC
# ---------------------------------------------------------------------------

def cmd_extract_ids(args: argparse.Namespace) -> int:
    root = Path(args.repo_root).resolve() if args.repo_root else repo_root_from_script()
    config = load_config(root)
    data = load_tracker(root, config)
    phase = find_phase(data, args.phase)
    if phase is None:
        print(f"Phase {args.phase} not found in tracker.")
        return 1

    pdir = phase_dir(root, phase, config)
    brd_file = pdir / "BRD.md"
    spec_file = pdir / "SPEC.md"

    result: dict = {
        "brd_file": str(brd_file),
        "spec_file": str(spec_file),
        "capabilities": [],
        "acceptance_criteria": [],
        "tests": [],
    }

    # Extract FC-nnn and AC-nnn from BRD
    if brd_file.exists():
        brd_lines = brd_file.read_text(encoding="utf-8").splitlines()
        seen_fc: set[str] = set()
        seen_ac: set[str] = set()
        for i, line in enumerate(brd_lines, 1):
            for m in re.finditer(r"(FC-\d+)", line):
                fc_id = m.group(1)
                if fc_id in seen_fc:
                    continue
                seen_fc.add(fc_id)
                after_id = line[m.end():].strip().lstrip("|").strip()
                summary = re.sub(r"\|.*", "", after_id).strip() if after_id else ""
                if not summary:
                    summary = line.strip()
                result["capabilities"].append({
                    "id": fc_id,
                    "line": i,
                    "summary": summary[:120],
                })
            for m in re.finditer(r"(AC-\d+)", line):
                ac_id = m.group(1)
                if ac_id in seen_ac:
                    continue
                seen_ac.add(ac_id)
                after_id = line[m.end():].strip().lstrip("|").strip()
                linked_fcs = re.findall(r"FC-\d+", line)
                summary = re.sub(r"\|.*", "", after_id).strip() if after_id else ""
                if not summary:
                    summary = line.strip()
                result["acceptance_criteria"].append({
                    "id": ac_id,
                    "line": i,
                    "summary": summary[:120],
                    "linked_fcs": linked_fcs,
                })

    # Extract T-nnn from SPEC
    if spec_file.exists():
        spec_lines = spec_file.read_text(encoding="utf-8").splitlines()
        seen_t: set[str] = set()
        for i, line in enumerate(spec_lines, 1):
            for m in re.finditer(r"(T-\d+)", line):
                t_id = m.group(1)
                if t_id in seen_t:
                    continue
                seen_t.add(t_id)
                after_id = line[m.end():].strip().lstrip("|").strip()
                summary = re.sub(r"\|.*", "", after_id).strip() if after_id else ""
                if not summary:
                    summary = line.strip()
                fc_match = re.search(r"(FC-\d+)", line)
                linked_fc = fc_match.group(1) if fc_match else None
                result["tests"].append({
                    "id": t_id,
                    "line": i,
                    "summary": summary[:120],
                    "linked_fc": linked_fc,
                })

    print(json.dumps(result, indent=2))
    return 0


def cmd_validate_config(args: argparse.Namespace) -> int:
    root = Path(args.repo_root).resolve() if args.repo_root else repo_root_from_script()
    config_path = root / "pew.yaml"
    errors: list[str] = []
    warnings: list[str] = []

    if not config_path.exists():
        print(json.dumps({
            "valid": False, "configured": False,
            "errors": ["pew.yaml not found"], "warnings": [],
        }, indent=2))
        return 1

    config = load_config(root)

    if config["project"]["name"] in ("My Project", ""):
        errors.append("project.name is not set")

    if not config["commands"]["verify"]:
        warnings.append("commands.verify is empty — verification step will have nothing to run")

    if not config["stack"]["description"]:
        warnings.append("stack.description is empty — review profile matching may be less accurate")

    for key in ("tracker", "plan"):
        p = root / config["paths"][key]
        if not p.parent.exists():
            warnings.append(f"paths.{key} parent directory does not exist: {p.parent}")

    result = {
        "valid": len(errors) == 0,
        "configured": True,
        "errors": errors,
        "warnings": warnings,
    }
    print(json.dumps(result, indent=2))
    return 0 if not errors else 1


def cmd_generate_verify_commands(args: argparse.Namespace) -> int:
    root = Path(args.repo_root).resolve() if args.repo_root else repo_root_from_script()
    config = load_config(root)
    result = {
        "verify": config["commands"].get("verify", ""),
        "e2e": config["commands"].get("e2e", ""),
    }
    print(json.dumps(result, indent=2))
    return 0


def cmd_bump_version(args: argparse.Namespace) -> int:
    """Bump the version in plugin.json and marketplace.json."""
    plugin_root = Path(__file__).resolve().parent.parent.parent
    plugin_dir = plugin_root / ".claude-plugin"

    # plugin.json is the source of truth
    pj = plugin_dir / "plugin.json"
    if not pj.exists():
        print(json.dumps({"error": ".claude-plugin/plugin.json not found"}))
        return 1

    pj_data = json.loads(pj.read_text())
    old_version = pj_data["version"]
    major, minor, patch = (int(x) for x in old_version.split("."))

    bump = getattr(args, "bump", "patch")
    if bump == "major":
        major, minor, patch = major + 1, 0, 0
    elif bump == "minor":
        major, minor, patch = major, minor + 1, 0
    else:
        patch += 1

    new_version = f"{major}.{minor}.{patch}"

    # Update plugin.json
    pj_data["version"] = new_version
    pj.write_text(json.dumps(pj_data, indent=2) + "\n")

    # Update marketplace.json if present
    mp = plugin_dir / "marketplace.json"
    if mp.exists():
        mp_data = json.loads(mp.read_text())
        mp_data["plugins"][0]["version"] = new_version
        mp.write_text(json.dumps(mp_data, indent=2) + "\n")

    print(json.dumps({"old": old_version, "new": new_version}))
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Phase workflow manager.")
    p.add_argument("--repo-root", help="Override repository root path.")
    sub = p.add_subparsers(dest="command", required=True)

    ap = sub.add_parser("analyze-phase", help="Analyze phase step completion.")
    ap.add_argument("--phase", type=float, required=True)
    ap.add_argument("--json", action="store_true")
    ap.set_defaults(func=cmd_analyze_phase)

    add = sub.add_parser("add-phase", help="Add a new phase to the tracker.")
    add.add_argument("--number", type=float, required=True)
    add.add_argument("--title", required=True)
    add.add_argument("--brief", default=None, help="Phase brief: what this phase delivers and why.")
    add.add_argument("--depends-on", default=None, help="Comma-separated dependency phase numbers.")
    add.add_argument("--tags", default=None, help="Comma-separated tags (e.g., frontend,backend).")
    add.add_argument("--refs", default=None,
                     help="Comma-separated reference doc paths (relative to repo root) for agents to read.")
    add.add_argument("--size", default=None, choices=sorted(VALID_PHASE_SIZES),
                     help="Phase size: small skips IDEAS+RESEARCH, medium skips IDEAS, large runs all steps (default: large).")
    add.set_defaults(func=cmd_add_phase)

    lp = sub.add_parser("list-phases", help="List phases from tracker.")
    lp.add_argument("--status", default=None)
    lp.add_argument("--json", action="store_true")
    lp.set_defaults(func=cmd_list_phases)

    sss = sub.add_parser("set-step-status", help="Update individual step status.")
    sss.add_argument("--phase", type=float, required=True)
    sss.add_argument("--step", required=True)
    sss.add_argument("--status", required=True)
    sss.set_defaults(func=cmd_set_step_status)

    vt = sub.add_parser("verify-traceability", help="Check ID traceability between step artifacts.")
    vt.add_argument("--phase", type=float, required=True)
    vt.add_argument("--from", dest="from_step", required=True)
    vt.add_argument("--to", required=True)
    vt.set_defaults(func=cmd_verify_traceability)

    cd = sub.add_parser("check-dependencies", help="Check if phase dependencies are satisfied.")
    cd.add_argument("--phase", type=float, required=True)
    cd.add_argument("--through", default=None,
                    help="Check that dependencies completed through this step (e.g., plan) instead of fully complete.")
    cd.set_defaults(func=cmd_check_dependencies)

    pd = sub.add_parser("phase-diff", help="Show files changed since phase start.")
    pd.add_argument("--phase", type=float, required=True)
    pd.set_defaults(func=cmd_phase_diff)

    dc = sub.add_parser("dump-config", help="Output resolved pew.yaml config as JSON.")
    dc.add_argument("--scope", default=None, choices=sorted(CONFIG_SCOPES.keys()),
                    help="Limit output to fields relevant to a specific role (agent, council, research).")
    dc.set_defaults(func=cmd_dump_config)

    rp = sub.add_parser("resolve-profiles", help="Match and output review profiles for a file list.")
    rp.add_argument("--profiles-dir", required=True, help="Path to review-profiles/ directory.")
    rp.add_argument("--files", default=None, help="Comma-separated list of changed files to match against.")
    rp.add_argument("--summary", action="store_true", help="Output condensed summaries instead of full profiles.")
    rp.add_argument("--json", action="store_true", help="Output matched profile metadata as JSON.")
    rp.set_defaults(func=cmd_resolve_profiles)

    ei = sub.add_parser("extract-ids", help="Extract compact FC/T index from BRD + SPEC.")
    ei.add_argument("--phase", type=float, required=True)
    ei.set_defaults(func=cmd_extract_ids)

    vc = sub.add_parser("validate-config", help="Validate pew.yaml configuration.")
    vc.set_defaults(func=cmd_validate_config)

    gvc = sub.add_parser("generate-verify-commands", help="Output verify/e2e commands from config.")
    gvc.set_defaults(func=cmd_generate_verify_commands)

    bv = sub.add_parser("bump-version", help="Bump plugin version in marketplace.json.")
    bv.add_argument("--bump", default="patch", choices=["patch", "minor", "major"],
                    help="Version component to bump (default: patch).")
    bv.set_defaults(func=cmd_bump_version)

    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
