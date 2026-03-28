"""Configuration loading, merging, validation, and scoped output."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

from pw_util import _norm_num  # noqa: F401 — re-exported for backward compat

DEFAULT_CONFIG: dict = {
    "project": {"name": "My Project", "description": ""},
    "paths": {
        "tracker": "phases/phase-tracker.yaml",
        "plan": "phases/implementation-plan.md",
        "phases": "phases",
        "research": "phases/research",
        "audit_test": "phases/audit/test",
        "audit_ux": "phases/audit/ux",
        "audit_react": "phases/audit/react",
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

CONFIG_SCOPES: dict[str, list[str]] = {
    "agent": ["project", "paths", "stack", "conventions_file"],
    "council": ["project", "paths", "council", "conventions_file"],
    "research": ["project", "paths", "stack", "competitors"],
}


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
