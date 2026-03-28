"""Extract compact FC/AC/T ID index from BRD and SPEC artifacts."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from pw_config import load_config, repo_root_from_script
from pw_tracker import load_tracker, find_phase, phase_dir


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
