#!/usr/bin/env python3
"""Phase workflow manager: YAML-based phase tracker with lifecycle commands.

Requires PyYAML. Use the wrapper: bash scripts/pw.sh <command>

This is the CLI entry point. Business logic lives in pw_* modules:
  pw_util.py     — constants, pure helpers
  pw_config.py   — config loading, merging, validation
  pw_tracker.py  — tracker load/save, phase directory, render plan
  pw_gates.py    — verification, traceability, dependencies, set-step-status
  pw_profiles.py — review profile matching and resolution
  pw_ids.py      — FC/AC/T ID extraction from BRD+SPEC
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

# Re-export everything so `import pw` still works for tests and external callers
from pw_util import *      # noqa: F401,F403
from pw_config import *    # noqa: F401,F403
from pw_tracker import *   # noqa: F401,F403
from pw_gates import *     # noqa: F401,F403
from pw_profiles import *  # noqa: F401,F403
from pw_ids import *       # noqa: F401,F403

# Explicit imports for names used directly in this file
from pw_util import (
    VALID_PHASE_SIZES, VALID_PHASE_MODES, VALID_STEP_STATUSES,
    STEP_ORDER, SIZE_SKIP_STEPS, STEP_FILE, ID_PATTERN,
    _norm_num, kebab_case,
)
from pw_config import (
    CONFIG_SCOPES, DEFAULT_CONFIG, _deep_merge,
    load_config, repo_root_from_script,
    cmd_dump_config, cmd_validate_config, cmd_generate_verify_commands,
)
from pw_tracker import (
    load_tracker, save_tracker, find_phase, phase_dir, render_plan,
    detect_step_file_completion,
)
from pw_gates import (
    cmd_set_step_status, _verify_traceability, _check_dependencies,
    _phase_completed_through,
)
from pw_profiles import cmd_resolve_profiles
from pw_ids import cmd_extract_ids


# ---------------------------------------------------------------------------
# Thin command handlers (parser glue — logic is trivial)
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
        "mode": phase.get("mode", "manual"),
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

    brief_file = args.brief_file or ""

    size = args.size or "large"
    mode = getattr(args, "mode", None) or "manual"
    skip_steps = SIZE_SKIP_STEPS.get(size, set())

    phase = {
        "number": _norm_num(args.number),
        "title": args.title,
        "brief": args.brief or "",
        "brief_file": brief_file,
        "refs": refs,
        "status": "not_started",
        "summary": "",
        "depends_on": depends_on,
        "tags": tags,
        "size": size,
        "mode": mode,
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
        # Explicit status filter: show all matching (no windowing)
        phases = [p for p in phases if p.get("status") == args.status]
    elif not getattr(args, "all", False):
        # Default windowing: started + first N not_started
        upcoming = getattr(args, "upcoming", 3) or 3
        started = [p for p in phases if p.get("status") == "started"]
        not_started = [p for p in phases if p.get("status") == "not_started"]
        not_started = not_started[:upcoming]
        phases = sorted(started + not_started, key=lambda p: p["number"])

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


def cmd_next_phase_number(args: argparse.Namespace) -> int:
    root = Path(args.repo_root).resolve() if args.repo_root else repo_root_from_script()
    config = load_config(root)
    data = load_tracker(root, config)
    phases = data.get("phases", [])
    if not phases:
        print(1)
    else:
        max_num = max(p["number"] for p in phases)
        print(_norm_num(int(max_num) + 1))
    return 0


def cmd_next_phase(args: argparse.Namespace) -> int:
    root = Path(args.repo_root).resolve() if args.repo_root else repo_root_from_script()
    config = load_config(root)
    data = load_tracker(root, config)

    phases = sorted(
        [p for p in data.get("phases", []) if p.get("status") != "complete"],
        key=lambda p: p["number"],
    )

    mode_filter = None
    if getattr(args, "mode", None):
        mode_filter = {m.strip() for m in args.mode.split(",") if m.strip()}

    for phase in phases:
        if mode_filter and phase.get("mode", "manual") not in mode_filter:
            continue
        satisfied, _, _ = _check_dependencies(data, phase)
        if not satisfied:
            continue

        first_incomplete = None
        for step in STEP_ORDER:
            status = phase["steps"].get(step, "not_started")
            if status not in ("complete", "skipped"):
                first_incomplete = step
                break

        result = {
            "number": phase["number"],
            "title": phase["title"],
            "mode": phase.get("mode", "manual"),
            "status": phase.get("status", "not_started"),
            "size": phase.get("size", "large"),
            "first_incomplete_step": first_incomplete,
        }

        if args.json:
            print(json.dumps(result, indent=2))
        else:
            step_info = f" (resume at: {first_incomplete})" if first_incomplete else ""
            print(f"Phase {result['number']}: {result['title']} [{result['mode']}]{step_info}")
        return 0

    if args.json:
        print(json.dumps({"none": True}))
    else:
        print("No eligible phase found.")
    return 0


def cmd_set_mode(args: argparse.Namespace) -> int:
    root = Path(args.repo_root).resolve() if args.repo_root else repo_root_from_script()
    config = load_config(root)
    data = load_tracker(root, config)

    phase_num = getattr(args, "phase", None)
    from_num = getattr(args, "from_phase", None)
    to_num = getattr(args, "to_phase", None)

    if phase_num is not None and from_num is not None:
        print("Cannot use both --phase and --from.")
        return 1
    if phase_num is None and from_num is None:
        print("Must provide either --phase or --from.")
        return 1

    # Single phase mode
    if phase_num is not None:
        phase = find_phase(data, phase_num)
        if phase is None:
            print(f"Phase {phase_num} not found in tracker.")
            return 1
        phase["mode"] = args.mode
        save_tracker(root, data, config)
        render_plan(root, data, config)
        print(f"Phase {phase['number']} mode -> {args.mode}")
        return 0

    # Range mode: --from [--to]
    targets = [
        p for p in data.get("phases", [])
        if p["number"] >= from_num
        and (to_num is None or p["number"] <= to_num)
        and p.get("status") != "complete"
    ]
    if not targets:
        print(f"No eligible phases found in range.")
        return 0
    for p in targets:
        p["mode"] = args.mode
        print(f"Phase {p['number']} {p['title']} mode -> {args.mode}")
    save_tracker(root, data, config)
    render_plan(root, data, config)
    print(f"Set {len(targets)} phases to {args.mode}")
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

    # CLI command does strict file-existence checks (unlike the internal helper)
    from_step, to_step = args.from_step, args.to
    if from_step not in ID_PATTERN or to_step not in ID_PATTERN:
        print(f"No traceability pattern defined for '{from_step}' or '{to_step}'.")
        return 1
    for step, label in [(from_step, "Source"), (to_step, "Target")]:
        f = STEP_FILE.get(step)
        if f and not (pdir / f).exists():
            print(f"{label} file not found: {pdir / f}")
            return 1

    ok, covered, missing = _verify_traceability(pdir, from_step, to_step)
    result = {"covered": covered, "missing": missing, "source_count": len(covered) + len(missing)}
    print(json.dumps(result, indent=2))
    return 0 if ok else 1


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

    satisfied, met, unmet = _check_dependencies(data, phase, through)
    result = {"satisfied": satisfied, "met": met, "unmet": unmet}
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


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Phase workflow manager.")
    p.add_argument("--repo-root", help="Override repository root path.")
    sub = p.add_subparsers(dest="command", required=True)

    ap = sub.add_parser("analyze-phase",
                        help="Inspect phase progress: step statuses, artifact file checks, first incomplete step. "
                             "Use before resuming work to know where to pick up.")
    ap.add_argument("--phase", type=float, required=True, help="Phase number to analyze.")
    ap.add_argument("--json", action="store_true", help="Output as JSON (includes phase_dir, size, mode, refs, per-step analysis).")
    ap.set_defaults(func=cmd_analyze_phase)

    add = sub.add_parser("add-phase",
                         help="Add a new phase to the tracker. Creates the phase entry with steps pre-set based on size.")
    add.add_argument("--number", type=float, required=True, help="Phase number (floats like 7.5 allowed for insertion between phases).")
    add.add_argument("--title", required=True, help="Phase title (converted to kebab-case for directory name).")
    add.add_argument("--brief", default=None, help="Phase brief: what this phase delivers and why.")
    add.add_argument("--depends-on", default=None, help="Comma-separated dependency phase numbers (e.g., '3,4').")
    add.add_argument("--tags", default=None, help="Comma-separated tags (e.g., 'frontend,backend'). Controls which council experts activate.")
    add.add_argument("--brief-file", default=None,
                     help="Path to an external document (e.g., plan file, AUDIT-BRIEF.md) for agents to read as primary context.")
    add.add_argument("--refs", default=None,
                     help="Comma-separated reference doc paths (relative to repo root) for agents to resolve finding IDs.")
    add.add_argument("--size", default=None, choices=sorted(VALID_PHASE_SIZES),
                     help="Phase size controls which steps run. small/audit: skip IDEAS+RESEARCH. medium: skip IDEAS. "
                          "large: all steps. vibe: skip all planning (BUILD first). Default: large.")
    add.add_argument("--mode", default=None, choices=sorted(VALID_PHASE_MODES),
                     help="Execution mode. manual: gates require user interaction. auto: sequential, gates still fire. "
                          "autopilot: no user interaction, approval gates skipped. Default: manual.")
    add.set_defaults(func=cmd_add_phase)

    lp = sub.add_parser("list-phases",
                        help="List phases from tracker. Default: active (started) + next 3 upcoming. "
                             "Use --all for all phases, --status to filter explicitly.")
    lp.add_argument("--status", default=None, help="Filter phases by status (not_started, started, complete). Bypasses default windowing.")
    lp.add_argument("--json", action="store_true", help="Output phase data as JSON array.")
    lp.add_argument("--all", action="store_true", help="Show all phases including complete (overrides default windowing).")
    lp.add_argument("--upcoming", type=int, default=3,
                    help="Number of not_started phases to include (default 3). Ignored with --all or --status.")
    lp.set_defaults(func=cmd_list_phases)

    sm = sub.add_parser("set-mode",
                        help="Set phase execution mode. Use --phase for a single phase, or --from [--to] for a range. "
                             "Controls whether approval gates fire (exit 2) or are skipped.")
    sm.add_argument("--phase", type=float, default=None, help="Single phase number.")
    sm.add_argument("--from", type=float, default=None, dest="from_phase",
                    help="Start of range (inclusive). Sets mode on all non-complete phases from this number onward.")
    sm.add_argument("--to", type=float, default=None, dest="to_phase",
                    help="End of range (inclusive). Without --to, sets from --from to the last phase.")
    sm.add_argument("--mode", required=True, choices=sorted(VALID_PHASE_MODES),
                    help="manual: gates require user approval. auto: sequential with gates. autopilot: no user interaction.")
    sm.set_defaults(func=cmd_set_mode)

    sss = sub.add_parser("set-step-status",
                         help="Transition a step's status. This is the main workflow gate — it enforces artifact existence, "
                              "traceability, dependencies, approval gates, and verification. "
                              "Exit 0 = success, exit 1 = hard failure (fix and retry), exit 2 = approval needed (re-run with --force).")
    sss.add_argument("--phase", type=float, required=True, help="Phase number.")
    sss.add_argument("--step", required=True, choices=STEP_ORDER,
                     help="Step to update.")
    sss.add_argument("--status", required=True, choices=sorted(VALID_STEP_STATUSES),
                     help="New status for the step.")
    sss.add_argument("--force", action="store_true",
                     help="Bypass approval gates (after user approval). Does NOT bypass artifact, traceability, or verification gates.")
    sss.set_defaults(func=cmd_set_step_status)

    vt = sub.add_parser("verify-traceability",
                        help="Check that IDs from a source step artifact appear in the target step artifact. "
                             "Normally auto-run by set-step-status on completion; use this for manual checks. Exit 1 if missing IDs found.")
    vt.add_argument("--phase", type=float, required=True, help="Phase number.")
    vt.add_argument("--from", dest="from_step", required=True, choices=[s for s in STEP_ORDER if s in ID_PATTERN],
                    help="Source step whose IDs must be traced.")
    vt.add_argument("--to", required=True, choices=[s for s in STEP_ORDER if s in ID_PATTERN],
                    help="Target step that must reference all source IDs.")
    vt.set_defaults(func=cmd_verify_traceability)

    cd = sub.add_parser("check-dependencies",
                        help="Check if all phases in depends_on are complete (or completed through a step with --through). "
                             "Normally auto-run by set-step-status before BUILD; use this for manual checks. Outputs JSON.")
    cd.add_argument("--phase", type=float, required=True, help="Phase number to check dependencies for.")
    cd.add_argument("--through", default=None, choices=STEP_ORDER,
                    help="Require deps completed through this step only (e.g., 'plan' for concurrent planning). "
                         "Without this flag, deps must be fully complete.")
    cd.set_defaults(func=cmd_check_dependencies)

    pd = sub.add_parser("phase-diff",
                        help="List files changed since phase start_commit (three-dot git diff). "
                             "Use during CHECK to scope council review and alignment checks.")
    pd.add_argument("--phase", type=float, required=True, help="Phase number.")
    pd.set_defaults(func=cmd_phase_diff)

    dc = sub.add_parser("dump-config",
                        help="Output resolved pew.yaml config as compact JSON (defaults merged, empty values stripped). "
                             "Use --scope to limit fields to a specific agent role.")
    dc.add_argument("--scope", default=None, choices=sorted(CONFIG_SCOPES.keys()),
                    help="Limit output to fields relevant to a role: agent (build agents), council (review experts), research (benchmarker/UX).")
    dc.set_defaults(func=cmd_dump_config)

    rp = sub.add_parser("resolve-profiles",
                        help="Match review profiles to changed files based on glob patterns in profile frontmatter. "
                             "Use during BUILD (for dev agents) and CHECK (for council experts).")
    rp.add_argument("--profiles-dir", required=True, help="Path to review-profiles/ directory containing .md profile files.")
    rp.add_argument("--files", default=None, help="Comma-separated list of changed file paths to match against profile globs.")
    rp.add_argument("--summary", action="store_true", help="Output condensed summaries (strips code blocks) instead of full profile content.")
    rp.add_argument("--json", action="store_true", help="Output matched profile metadata (name, path, globs) as JSON instead of content.")
    rp.set_defaults(func=cmd_resolve_profiles)

    ei = sub.add_parser("extract-ids",
                        help="Extract a compact JSON index of FC-nnn, AC-nnn, and T-nnn IDs from BRD.md and SPEC.md. "
                             "Pass this to council experts instead of full artifact content to save context.")
    ei.add_argument("--phase", type=float, required=True, help="Phase number.")
    ei.set_defaults(func=cmd_extract_ids)

    vc = sub.add_parser("validate-config",
                        help="Check pew.yaml exists and is valid. Outputs JSON with 'configured', 'valid', 'errors', 'warnings' fields. "
                             "Run before any workflow command to ensure project is set up.")
    vc.set_defaults(func=cmd_validate_config)

    gvc = sub.add_parser("generate-verify-commands",
                         help="Output verify and e2e commands from pew.yaml config as JSON. "
                              "Use to pass verification commands to build agents.")
    gvc.set_defaults(func=cmd_generate_verify_commands)

    npn = sub.add_parser("next-phase-number",
                         help="Output the next available integer phase number (max existing + 1, or 1 if no phases). "
                              "Use when auto-generating phases (e.g., from audit-to-phases).")
    npn.set_defaults(func=cmd_next_phase_number)

    nph = sub.add_parser("next-phase",
                         help="Find the next eligible phase: non-complete, dependencies satisfied. "
                              "Returns compact JSON with phase number, title, mode, and first incomplete step. "
                              "Use --mode to filter by execution mode (e.g., 'auto,autopilot' for the autopilot loop).")
    nph.add_argument("--mode", default=None,
                     help="Comma-separated mode filter (e.g., 'auto,autopilot'). Without this, returns first eligible regardless of mode.")
    nph.add_argument("--json", action="store_true",
                     help="Output as JSON. Returns {number, title, mode, status, size, first_incomplete_step} or {none: true}.")
    nph.set_defaults(func=cmd_next_phase)

    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
