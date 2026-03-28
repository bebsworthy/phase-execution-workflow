"""Gate enforcement: verification runner, traceability, dependencies, step status transitions."""

from __future__ import annotations

import argparse
import collections
import json
import re
import select
import subprocess
import time
from pathlib import Path

from pw_util import (
    VERIFY_IDLE_TIMEOUT, VERIFY_FAIL_TAIL_LINES,
    VALID_STEP_STATUSES, STEP_ORDER, STEP_FILE, ID_PREFIX, ID_PATTERN,
    _norm_num, get_head_sha,
)
from pw_config import load_config, repo_root_from_script
from pw_tracker import load_tracker, save_tracker, find_phase, phase_dir, render_plan


# ---------------------------------------------------------------------------
# run_verification: stream output, idle timeout, log to file
# ---------------------------------------------------------------------------


def run_verification(
    cmd: str,
    cwd: Path,
    pdir: Path,
    idle_timeout: int | None = None,
) -> tuple[int, str]:
    """Run verification command with streaming idle timeout.

    Returns (exit_code, summary_text).  exit_code 0 = passed.
    Full output is written to {pdir}/verify-output.log.
    """
    if idle_timeout is None:
        idle_timeout = VERIFY_IDLE_TIMEOUT
    log_path = pdir / "verify-output.log"
    pdir.mkdir(parents=True, exist_ok=True)
    tail: collections.deque[str] = collections.deque(maxlen=VERIFY_FAIL_TAIL_LINES)

    print(f"Running verification to authorize phase closing, "
          f"full output at {log_path}")

    proc = subprocess.Popen(
        cmd, shell=True, cwd=str(cwd),
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    assert proc.stdout is not None

    with open(log_path, "w") as log_f:
        last_output = time.monotonic()
        while True:
            # poll with 1s granularity
            ready, _, _ = select.select([proc.stdout], [], [], 1.0)
            if ready:
                line = proc.stdout.readline()
                if not line:  # EOF
                    break
                decoded = line.decode("utf-8", errors="replace")
                log_f.write(decoded)
                log_f.flush()
                tail.append(decoded)
                last_output = time.monotonic()
            else:
                # check idle timeout
                if time.monotonic() - last_output > idle_timeout:
                    proc.kill()
                    proc.wait()
                    msg = (f"Verification stalled — no output for "
                           f"{idle_timeout // 60} minutes. Process killed.\n"
                           f"Full output: {log_path}")
                    log_f.write(f"\n--- KILLED: idle timeout ({idle_timeout}s) ---\n")
                    return 1, msg
                # check if process exited (but stdout not yet EOF)
                if proc.poll() is not None:
                    # drain remaining
                    for remaining in proc.stdout:
                        decoded = remaining.decode("utf-8", errors="replace")
                        log_f.write(decoded)
                        tail.append(decoded)
                    break

    proc.wait()

    if proc.returncode == 0:
        return 0, "Verification passed ✓"

    tail_text = "".join(tail).rstrip()
    msg = (f"BLOCKED: Verification failed — exit code {proc.returncode}\n"
           f"Last {VERIFY_FAIL_TAIL_LINES} lines:\n{tail_text}\n"
           f"Full output: {log_path}\n"
           f"Action: Fix the failing tests shown above "
           f"(or read the full log), then retry.")
    return proc.returncode, msg


# ---------------------------------------------------------------------------
# Traceability
# ---------------------------------------------------------------------------


def _verify_traceability(
    pdir: Path, from_step: str, to_step: str,
) -> tuple[bool, list[str], list[str]]:
    """Check ID traceability between step artifacts.

    Returns (ok, covered_ids, missing_ids).
    """
    if from_step not in ID_PATTERN or to_step not in ID_PATTERN:
        return True, [], []  # no pattern defined, skip

    source_file = STEP_FILE.get(from_step)
    target_file = STEP_FILE.get(to_step)
    if not source_file or not target_file:
        return True, [], []

    source_path = pdir / source_file
    target_path = pdir / target_file

    if not source_path.exists() or not target_path.exists():
        return True, [], []  # files missing, other gates handle this

    source_text = source_path.read_text(encoding="utf-8")
    target_text = target_path.read_text(encoding="utf-8")
    source_prefix = ID_PREFIX[from_step]
    source_pattern = ID_PATTERN[from_step]

    if from_step == "ideas":
        selected_blocks = re.findall(r"\[selected\].*", source_text, re.IGNORECASE)
        source_ids: list[str] = []
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
    return len(missing) == 0, covered, missing


# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------


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


def _check_dependencies(
    data: dict, phase: dict, through: str | None = None,
) -> tuple[bool, list, list]:
    """Check if phase dependencies are satisfied.

    Returns (satisfied, met_list, unmet_list).
    """
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

    return len(unmet) == 0, met, unmet


# ---------------------------------------------------------------------------
# cmd_set_step_status — the main workflow gate
# ---------------------------------------------------------------------------


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

    pnum = phase["number"]
    pdir = phase_dir(root, phase, config)
    mode = phase.get("mode", "manual")
    force = getattr(args, "force", False)

    # --- Group D: Config validation ---
    proj_name = config.get("project", {}).get("name", "")
    if proj_name in ("My Project", ""):
        print(f"BLOCKED: PEW is not configured for this project.\n"
              f"Action: Run /pew-init to set up project configuration "
              f"before executing workflow commands.")
        return 1

    # --- in_progress gates ---
    if args.status == "in_progress":
        step_idx = STEP_ORDER.index(args.step)
        for prev_step in STEP_ORDER[:step_idx]:
            prev_status = phase["steps"].get(prev_step, "not_started")
            if prev_status not in ("complete", "skipped"):
                print(
                    f"BLOCKED: Cannot start '{args.step}' for phase {pnum}.\n"
                    f"Prior step '{prev_step}' is '{prev_status}' "
                    f"(must be complete or skipped).\n"
                    f"Action: Complete step '{prev_step}' first, then retry."
                )
                return 1

        # Group C: Dependency check before BUILD
        if args.step == "build":
            satisfied, _, unmet = _check_dependencies(data, phase)
            if not satisfied:
                print(f"BLOCKED: Cannot start 'build' for phase {pnum}.\n"
                      f"Unmet dependencies: phases {unmet} must be complete "
                      f"before building phase {pnum}.\n"
                      f"Action: Complete the dependent phases first, then retry.")
                return 1

        # Group E: BUILD approval gate
        if args.step == "build" and not force:
            gate_enabled = config.get("approval_gates", {}).get("before_build", True)
            if gate_enabled and mode != "autopilot":
                completed = [s for s in STEP_ORDER
                             if phase["steps"].get(s) == "complete"
                             and s in STEP_FILE]
                artifacts = ", ".join(STEP_FILE[s] for s in completed)
                print(f"APPROVAL REQUIRED: Phase {pnum} is ready to build.\n"
                      f"Artifacts completed: {artifacts}\n"
                      f"Action: Present the build approval gate to the user "
                      f"via AskUserQuestion.\n"
                      f"After user approves, re-run this command with --force "
                      f"to proceed.")
                return 2

        # Auto-init: create phase dir + set phase started on first step start
        if phase.get("status") == "not_started":
            pdir.mkdir(parents=True, exist_ok=True)
            phase["status"] = "started"
            sha = get_head_sha(root)
            if sha:
                phase["start_commit"] = sha
            print(f"Auto-initialized Phase {pnum} {phase['title']}")
            print(f"Phase directory: {pdir}")

    # --- completion gates ---
    if args.status == "complete":
        # Group A: Artifact existence check
        if args.step in STEP_FILE:
            artifact = pdir / STEP_FILE[args.step]
            if not artifact.exists() or artifact.stat().st_size == 0:
                print(f"BLOCKED: Cannot complete step '{args.step}' for "
                      f"phase {pnum}.\n"
                      f"Required artifact '{artifact.name}' is missing or "
                      f"empty.\n"
                      f"Action: Spawn the {args.step} agent to generate "
                      f"{artifact.name} in {pdir}/, then retry this command.")
                return 1

        # Group B: Traceability auto-check
        trace_map = {"brd": "ideas", "spec": "brd", "plan": "spec"}
        if args.step in trace_map:
            from_step = trace_map[args.step]
            if phase["steps"].get(from_step) != "skipped":
                ok, _, missing = _verify_traceability(pdir, from_step, args.step)
                if not ok:
                    print(f"BLOCKED: Cannot complete step '{args.step}' for "
                          f"phase {pnum}.\n"
                          f"Traceability check failed ({from_step} → "
                          f"{args.step}): missing IDs {missing}.\n"
                          f"Action: Re-spawn the {args.step} agent to add "
                          f"coverage for the missing IDs, then retry.")
                    return 1

    phase["steps"][args.step] = args.status

    # Auto-close: when check step completes, run verification + approval gate
    if args.step == "check" and args.status == "complete":
        verify_cmd = config.get("commands", {}).get("verify", "")
        if verify_cmd:
            # Skip re-run if verification already passed (e.g., --force after approval gate)
            if force and phase.get("verification_passed"):
                print("Verification already passed ✓ (skipping re-run)")
            else:
                phase["verification_passed"] = False
                rc, msg = run_verification(verify_cmd, root, pdir)
                print(msg)
                if rc != 0:
                    save_tracker(root, data, config)
                    return 1
                phase["verification_passed"] = True
                save_tracker(root, data, config)

        # Group E: CLOSE approval gate (after verification passes)
        if not force:
            gate_enabled = config.get("approval_gates", {}).get("before_close", True)
            if gate_enabled and mode != "autopilot":
                print(f"APPROVAL REQUIRED: Phase {pnum} verification passed, "
                      f"ready to close.\n"
                      f"Action: Present the close approval gate to the user "
                      f"via AskUserQuestion.\n"
                      f"After user approves, re-run this command with --force "
                      f"to proceed.")
                return 2

        phase["status"] = "complete"
        sha = get_head_sha(root)
        if sha:
            phase["end_commit"] = sha
        print(f"Phase {pnum} auto-closed as complete.")

    save_tracker(root, data, config)
    render_plan(root, data, config)

    print(f"Phase {phase['number']} step '{args.step}' -> {args.status}")

    # --- Mode-aware guidance ---
    if args.status == "in_progress":
        if mode == "autopilot":
            print(f"MODE: autopilot — open questions auto-resolved (use recommended option, "
                  f"do NOT call AskUserQuestion). Fix policy: P1 auto-fix, P2 auto-fix then defer, P3 auto-defer.")
        elif mode == "auto":
            print(f"MODE: auto — proceed to next step automatically after this one completes. "
                  f"Approval gates still require user confirmation.")

    if args.step == "check" and args.status == "complete":
        # Phase just closed — find next eligible phase
        remaining = sorted(
            [p for p in data.get("phases", [])
             if p.get("status") != "complete"],
            key=lambda p: p["number"],
        )
        if not remaining:
            print("All phases complete.")
        elif mode in ("auto", "autopilot"):
            # Find next eligible auto/autopilot phase with deps met
            found = False
            for cand in remaining:
                cand_mode = cand.get("mode", "manual")
                if cand_mode not in ("auto", "autopilot"):
                    continue
                satisfied, _, _ = _check_dependencies(data, cand)
                if satisfied:
                    print(f"NEXT: Phase {cand['number']} {cand['title']} is in "
                          f"{cand_mode} mode — start it immediately.")
                    found = True
                    break
            if not found:
                print("Autopilot complete — no more eligible phases in auto/autopilot mode.")

    return 0
