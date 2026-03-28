"""Review profile parsing, matching, resolution, and summarization."""

from __future__ import annotations

import argparse
import fnmatch
import json
import re
import sys
from pathlib import Path

import yaml


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
