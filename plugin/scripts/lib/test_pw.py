"""Tests for pw.py — phase workflow manager."""

from __future__ import annotations

import json
import subprocess
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

import pw


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """Create a minimal repo structure with tracker and implementation plan."""
    (tmp_path / "phases").mkdir(parents=True)
    tracker = tmp_path / "phases/phase-tracker.yaml"
    tracker.write_text("phases: []\n", encoding="utf-8")

    # Valid config: real project name + gates off for unit test ergonomics
    (tmp_path / "pew.yaml").write_text(
        yaml.dump({
            "project": {"name": "TestProject"},
            "approval_gates": {"before_build": False, "before_close": False},
        }), encoding="utf-8",
    )

    plan = tmp_path / "phases/implementation-plan.md"
    plan.write_text(
        "# Plan\n\n## 1.1 Phase Status Tracker\n\n"
        "| Phase | Status | Summary | Tags | Depends On |\n"
        "| ----- | ------ | ------- | ---- | ---------- |\n\n"
        "## Next Section\n",
        encoding="utf-8",
    )

    # Init a git repo so get_head_sha works
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
    subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "init", "--no-gpg-sign"],
        cwd=tmp_path, capture_output=True,
        env={"GIT_AUTHOR_NAME": "test", "GIT_AUTHOR_EMAIL": "t@t",
             "GIT_COMMITTER_NAME": "test", "GIT_COMMITTER_EMAIL": "t@t",
             "HOME": str(tmp_path), "PATH": "/usr/bin:/bin:/usr/local/bin"},
    )
    return tmp_path


def _run(repo: Path, *cli_args: str) -> tuple[int, str]:
    """Run pw.py via CLI parser, capture stdout, return (exit_code, output)."""
    parser = pw.build_parser()
    args = parser.parse_args(["--repo-root", str(repo), *cli_args])
    import io, contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = args.func(args)
    return code, buf.getvalue()


def _add_phase(repo: Path, number: int | float = 24, title: str = "Search",
               tags: str | None = "frontend,backend",
               depends_on: str | None = None,
               brief: str | None = "Add search",
               refs: str | None = None,
               size: str | None = None,
               brief_file: str | None = None) -> int:
    """Helper to add a phase."""
    cli = ["add-phase", "--number", str(number), "--title", title]
    if tags:
        cli += ["--tags", tags]
    if depends_on:
        cli += ["--depends-on", depends_on]
    if brief:
        cli += ["--brief", brief]
    if refs:
        cli += ["--refs", refs]
    if size:
        cli += ["--size", size]
    if brief_file:
        cli += ["--brief-file", brief_file]
    code, _ = _run(repo, *cli)
    return code


def _complete_step(repo: Path, phase_num: int | float, step: str,
                   title: str = "Search") -> tuple[int, str]:
    """Set step in_progress then complete, creating the artifact file if needed."""
    _run(repo, "set-step-status", "--phase", str(phase_num),
         "--step", step, "--status", "in_progress")
    # Create artifact file so the completion gate passes
    if step in pw.STEP_FILE:
        slug = pw.kebab_case(f"phase-{phase_num}-{title}")
        pdir = repo / "phases" / slug
        pdir.mkdir(parents=True, exist_ok=True)
        (pdir / pw.STEP_FILE[step]).write_text(f"# {step}\nDone.\n")
    return _run(repo, "set-step-status", "--phase", str(phase_num),
                "--step", step, "--status", "complete")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class TestKebabCase:
    def test_simple(self):
        assert pw.kebab_case("Phase 24 Advanced Search") == "phase-24-advanced-search"

    def test_special_chars(self):
        assert pw.kebab_case("Hello, World! #1") == "hello-world-1"

    def test_consecutive_separators(self):
        assert pw.kebab_case("a---b   c") == "a-b-c"

    def test_leading_trailing(self):
        assert pw.kebab_case("  Phase 1  ") == "phase-1"


class TestLoadTracker:
    def test_missing_file(self, tmp_path: Path):
        data = pw.load_tracker(tmp_path)
        assert data == {"phases": []}

    def test_empty_file(self, tmp_path: Path):
        (tmp_path / "phases").mkdir(parents=True)
        (tmp_path / "phases/phase-tracker.yaml").write_text("")
        data = pw.load_tracker(tmp_path)
        assert data == {"phases": []}

    def test_phases_null(self, tmp_path: Path):
        (tmp_path / "phases").mkdir(parents=True)
        (tmp_path / "phases/phase-tracker.yaml").write_text("phases:\n")
        data = pw.load_tracker(tmp_path)
        assert data == {"phases": []}

    def test_defaults_filled(self, tmp_path: Path):
        (tmp_path / "phases").mkdir(parents=True)
        tracker = tmp_path / "phases/phase-tracker.yaml"
        tracker.write_text(yaml.dump({"phases": [{"number": 1, "title": "X", "status": "not_started"}]}))
        data = pw.load_tracker(tmp_path)
        phase = data["phases"][0]
        assert phase["brief"] == ""
        assert phase["refs"] == []
        assert phase["depends_on"] == []
        assert phase["tags"] == []
        assert phase["start_commit"] is None
        assert set(phase["steps"].values()) == {"not_started"}

    def test_roundtrip(self, repo: Path):
        _add_phase(repo, 1, "Test", tags="frontend")
        data = pw.load_tracker(repo)
        assert len(data["phases"]) == 1
        assert data["phases"][0]["title"] == "Test"
        assert data["phases"][0]["tags"] == ["frontend"]


class TestDetectStepFileCompletion:
    def test_missing_file(self, tmp_path: Path):
        ok, reasons = pw.detect_step_file_completion(tmp_path / "NOPE.md")
        assert not ok
        assert "missing file" in reasons[0]

    def test_not_started_status(self, tmp_path: Path):
        f = tmp_path / "IDEAS.md"
        f.write_text("# Ideas\nstatus: not_started\n")
        ok, reasons = pw.detect_step_file_completion(f)
        assert not ok
        assert any("not_started" in r for r in reasons)

    def test_unchecked_items(self, tmp_path: Path):
        f = tmp_path / "PLAN.md"
        f.write_text("# Plan\nstatus: in_progress\n- [ ] TODO item\n- [x] Done\n")
        ok, reasons = pw.detect_step_file_completion(f)
        assert not ok
        assert any("unchecked" in r for r in reasons)

    def test_complete(self, tmp_path: Path):
        f = tmp_path / "BRD.md"
        f.write_text("# BRD\nstatus: complete\n- [x] All done\n")
        ok, reasons = pw.detect_step_file_completion(f)
        assert ok
        assert reasons == []


# ---------------------------------------------------------------------------
# Commands: add-phase
# ---------------------------------------------------------------------------

class TestAddPhase:
    def test_add_and_list(self, repo: Path):
        assert _add_phase(repo) == 0
        code, out = _run(repo, "list-phases")
        assert "Phase 24: Search" in out
        assert "frontend" in out

    def test_duplicate(self, repo: Path):
        _add_phase(repo)
        code, _ = _run(repo, "add-phase", "--number", "24", "--title", "Dup")
        assert code == 1

    def test_sorted_order(self, repo: Path):
        _add_phase(repo, 30, "Later")
        _add_phase(repo, 10, "Earlier")
        data = pw.load_tracker(repo)
        numbers = [p["number"] for p in data["phases"]]
        assert numbers == [10, 30]

    def test_with_dependencies(self, repo: Path):
        _add_phase(repo, 1, "First")
        _add_phase(repo, 2, "Second", depends_on="1")
        data = pw.load_tracker(repo)
        assert data["phases"][1]["depends_on"] == [1]

    def test_renders_plan(self, repo: Path):
        _add_phase(repo)
        plan = (repo / "phases/implementation-plan.md").read_text()
        assert "Phase 24 Search" in plan

    def test_brief_stored(self, repo: Path):
        _add_phase(repo, brief="Full-text search across issues")
        data = pw.load_tracker(repo)
        assert data["phases"][0]["brief"] == "Full-text search across issues"

    def test_refs_stored(self, repo: Path):
        _add_phase(repo, refs="phases/audit/ux/04-audit.md,phases/audit/ux/01-user-goals.md")
        data = pw.load_tracker(repo)
        assert data["phases"][0]["refs"] == [
            "phases/audit/ux/04-audit.md",
            "phases/audit/ux/01-user-goals.md",
        ]

    def test_refs_default_empty(self, repo: Path):
        _add_phase(repo)
        data = pw.load_tracker(repo)
        assert data["phases"][0]["refs"] == []

    def test_brief_file_stored(self, repo: Path):
        _add_phase(repo, brief_file="plans/my-plan.md")
        data = pw.load_tracker(repo)
        assert data["phases"][0]["brief_file"] == "plans/my-plan.md"

    def test_brief_file_default_empty(self, repo: Path):
        _add_phase(repo)
        data = pw.load_tracker(repo)
        assert data["phases"][0]["brief_file"] == ""


# ---------------------------------------------------------------------------
# Commands: next-phase-number
# ---------------------------------------------------------------------------

class TestNextPhaseNumber:
    def test_no_phases(self, repo: Path):
        code, out = _run(repo, "next-phase-number")
        assert code == 0
        assert out.strip() == "1"

    def test_sequential_phases(self, repo: Path):
        _add_phase(repo, 1, "First")
        _add_phase(repo, 2, "Second")
        _add_phase(repo, 3, "Third")
        code, out = _run(repo, "next-phase-number")
        assert code == 0
        assert out.strip() == "4"

    def test_with_decimal_phases(self, repo: Path):
        _add_phase(repo, 1, "First")
        _add_phase(repo, 2.5, "Middle")
        _add_phase(repo, 3, "Third")
        code, out = _run(repo, "next-phase-number")
        assert code == 0
        assert out.strip() == "4"

    def test_single_phase(self, repo: Path):
        _add_phase(repo, 5, "Only")
        code, out = _run(repo, "next-phase-number")
        assert code == 0
        assert out.strip() == "6"


# ---------------------------------------------------------------------------
# Commands: set-step-status
# ---------------------------------------------------------------------------

class TestSetStepStatus:
    def test_set_in_progress(self, repo: Path):
        _add_phase(repo)
        code, out = _run(repo, "set-step-status", "--phase", "24",
                         "--step", "ideas", "--status", "in_progress")
        assert code == 0
        assert "in_progress" in out

    def test_auto_init(self, repo: Path):
        _add_phase(repo)
        code, out = _run(repo, "set-step-status", "--phase", "24",
                         "--step", "ideas", "--status", "in_progress")
        assert "Auto-initialized" in out
        data = pw.load_tracker(repo)
        assert data["phases"][0]["status"] == "started"
        assert data["phases"][0]["start_commit"] is not None
        pdir = pw.phase_dir(repo, data["phases"][0])
        assert pdir.is_dir()

    def test_auto_init_only_once(self, repo: Path):
        _add_phase(repo)
        _run(repo, "set-step-status", "--phase", "24",
             "--step", "ideas", "--status", "in_progress")
        _run(repo, "set-step-status", "--phase", "24",
             "--step", "ideas", "--status", "complete")
        code, out = _run(repo, "set-step-status", "--phase", "24",
                         "--step", "brd", "--status", "in_progress")
        assert "Auto-initialized" not in out

    def test_ordering_enforced(self, repo: Path):
        _add_phase(repo)
        # Try to start brd without completing ideas
        code, out = _run(repo, "set-step-status", "--phase", "24",
                         "--step", "brd", "--status", "in_progress")
        assert code == 1
        assert "Cannot start" in out
        assert "'ideas'" in out

    def test_ordering_allows_skipped(self, repo: Path):
        _add_phase(repo)
        _run(repo, "set-step-status", "--phase", "24",
             "--step", "ideas", "--status", "skipped")
        code, _ = _run(repo, "set-step-status", "--phase", "24",
                       "--step", "brd", "--status", "in_progress")
        assert code == 0

    def test_auto_close(self, repo: Path):
        _add_phase(repo)
        # Complete all steps (with artifacts)
        for step in pw.STEP_ORDER:
            _complete_step(repo, 24, step)
        data = pw.load_tracker(repo)
        assert data["phases"][0]["status"] == "complete"
        assert data["phases"][0]["end_commit"] is not None

    def test_invalid_step(self, repo: Path):
        _add_phase(repo)
        with pytest.raises(SystemExit) as exc_info:
            _run(repo, "set-step-status", "--phase", "24",
                 "--step", "nope", "--status", "in_progress")
        assert exc_info.value.code == 2  # argparse rejects invalid choice

    def test_invalid_status(self, repo: Path):
        _add_phase(repo)
        with pytest.raises(SystemExit) as exc_info:
            _run(repo, "set-step-status", "--phase", "24",
                 "--step", "ideas", "--status", "bad")
        assert exc_info.value.code == 2  # argparse rejects invalid choice

    def test_phase_not_found(self, repo: Path):
        code, out = _run(repo, "set-step-status", "--phase", "999",
                         "--step", "ideas", "--status", "in_progress")
        assert code == 1
        assert "not found" in out


# ---------------------------------------------------------------------------
# Commands: analyze-phase
# ---------------------------------------------------------------------------

class TestAnalyzePhase:
    def test_first_incomplete(self, repo: Path):
        _add_phase(repo)
        code, out = _run(repo, "analyze-phase", "--phase", "24", "--json")
        assert code == 0
        result = json.loads(out)
        assert result["first_incomplete_step"] == "ideas"

    def test_after_some_progress(self, repo: Path):
        _add_phase(repo)
        _run(repo, "set-step-status", "--phase", "24",
             "--step", "ideas", "--status", "in_progress")
        _run(repo, "set-step-status", "--phase", "24",
             "--step", "ideas", "--status", "complete")
        code, out = _run(repo, "analyze-phase", "--phase", "24", "--json")
        result = json.loads(out)
        # ideas is complete in tracker but file doesn't exist — should still show incomplete
        assert result["steps"]["ideas"]["complete"] is False
        assert result["first_incomplete_step"] == "ideas"

    def test_all_complete(self, repo: Path):
        _add_phase(repo)
        # Complete all steps and create artifact files
        pdir = repo / "phases/phase-24-search"
        pdir.mkdir(parents=True)
        for step in pw.STEP_ORDER:
            _run(repo, "set-step-status", "--phase", "24",
                 "--step", step, "--status", "in_progress")
            if step in pw.STEP_FILE:
                (pdir / pw.STEP_FILE[step]).write_text(
                    f"# {step}\nstatus: complete\n- [x] Done\n"
                )
            _run(repo, "set-step-status", "--phase", "24",
                 "--step", step, "--status", "complete")
        code, out = _run(repo, "analyze-phase", "--phase", "24", "--json")
        result = json.loads(out)
        assert result["first_incomplete_step"] is None

    def test_human_output(self, repo: Path):
        _add_phase(repo)
        code, out = _run(repo, "analyze-phase", "--phase", "24")
        assert "Phase 24: Search" in out
        assert "First incomplete step: ideas" in out

    def test_refs_in_json(self, repo: Path):
        _add_phase(repo, refs="docs/audit.md,docs/goals.md")
        code, out = _run(repo, "analyze-phase", "--phase", "24", "--json")
        result = json.loads(out)
        assert result["refs"] == ["docs/audit.md", "docs/goals.md"]

    def test_not_found(self, repo: Path):
        code, out = _run(repo, "analyze-phase", "--phase", "999", "--json")
        assert code == 1


# ---------------------------------------------------------------------------
# Commands: verify-traceability
# ---------------------------------------------------------------------------

class TestVerifyTraceability:
    def _setup_artifacts(self, repo: Path, ideas_text: str, brd_text: str):
        _add_phase(repo)
        pdir = repo / "phases/phase-24-search"
        pdir.mkdir(parents=True, exist_ok=True)
        (pdir / "IDEAS.md").write_text(ideas_text, encoding="utf-8")
        (pdir / "BRD.md").write_text(brd_text, encoding="utf-8")

    def test_all_covered(self, repo: Path):
        self._setup_artifacts(repo,
            "### [selected] IDEA-001: Feature A\n### [selected] IDEA-002: Feature B\n",
            "## Requirements\nCovers IDEA-001 and IDEA-002\n",
        )
        code, out = _run(repo, "verify-traceability", "--phase", "24",
                         "--from", "ideas", "--to", "brd")
        assert code == 0
        result = json.loads(out)
        assert result["missing"] == []
        assert sorted(result["covered"]) == ["IDEA-001", "IDEA-002"]

    def test_missing_ids(self, repo: Path):
        self._setup_artifacts(repo,
            "### [selected] IDEA-001: Feature A\n### [selected] IDEA-002: Feature B\n",
            "## Requirements\nCovers IDEA-001 only\n",
        )
        code, out = _run(repo, "verify-traceability", "--phase", "24",
                         "--from", "ideas", "--to", "brd")
        assert code == 1
        result = json.loads(out)
        assert result["missing"] == ["IDEA-002"]

    def test_rejected_ideas_not_traced(self, repo: Path):
        self._setup_artifacts(repo,
            "### [selected] IDEA-001: Keep\n### [rejected] IDEA-002: Skip\n",
            "## Requirements\nCovers IDEA-001\n",
        )
        code, out = _run(repo, "verify-traceability", "--phase", "24",
                         "--from", "ideas", "--to", "brd")
        assert code == 0
        result = json.loads(out)
        assert "IDEA-002" not in result["covered"]
        assert "IDEA-002" not in result["missing"]

    def test_no_substring_false_positive(self, repo: Path):
        """IDEA-1 should NOT match IDEA-10."""
        self._setup_artifacts(repo,
            "### [selected] IDEA-1: Small\n### [selected] IDEA-10: Big\n",
            "## Requirements\nCovers IDEA-10 only\n",
        )
        code, out = _run(repo, "verify-traceability", "--phase", "24",
                         "--from", "ideas", "--to", "brd")
        assert code == 1
        result = json.loads(out)
        assert "IDEA-1" in result["missing"]
        assert "IDEA-10" in result["covered"]

    def test_missing_source_file(self, repo: Path):
        _add_phase(repo)
        code, out = _run(repo, "verify-traceability", "--phase", "24",
                         "--from", "ideas", "--to", "brd")
        assert code == 1
        assert "not found" in out


# ---------------------------------------------------------------------------
# Commands: check-dependencies
# ---------------------------------------------------------------------------

class TestCheckDependencies:
    def test_no_deps(self, repo: Path):
        _add_phase(repo, 1, "Solo")
        code, out = _run(repo, "check-dependencies", "--phase", "1")
        assert code == 0
        assert json.loads(out)["satisfied"] is True

    def test_met(self, repo: Path):
        _add_phase(repo, 1, "First")
        _add_phase(repo, 2, "Second", depends_on="1")
        # Complete phase 1
        for step in pw.STEP_ORDER:
            _run(repo, "set-step-status", "--phase", "1",
                 "--step", step, "--status", "in_progress")
            _run(repo, "set-step-status", "--phase", "1",
                 "--step", step, "--status", "complete")
        code, out = _run(repo, "check-dependencies", "--phase", "2")
        assert code == 0
        assert json.loads(out)["satisfied"] is True

    def test_unmet(self, repo: Path):
        _add_phase(repo, 1, "First")
        _add_phase(repo, 2, "Second", depends_on="1")
        code, out = _run(repo, "check-dependencies", "--phase", "2")
        assert code == 1
        result = json.loads(out)
        assert result["satisfied"] is False
        assert result["unmet"] == [1]

    def test_through_plan_satisfied(self, repo: Path):
        """Phase 2 can proceed if phase 1 has completed through plan."""
        _add_phase(repo, 1, "First")
        _add_phase(repo, 2, "Second", depends_on="1")
        for step in ["ideas", "brd", "research", "spec", "plan"]:
            _complete_step(repo, 1, step, "First")
        code, out = _run(repo, "check-dependencies", "--phase", "2",
                         "--through", "plan")
        assert code == 0
        assert json.loads(out)["satisfied"] is True

    def test_through_plan_unmet(self, repo: Path):
        """Phase 2 blocked if phase 1 has only completed through research."""
        _add_phase(repo, 1, "First")
        _add_phase(repo, 2, "Second", depends_on="1")
        for step in ["ideas", "brd", "research"]:
            _complete_step(repo, 1, step, "First")
        code, out = _run(repo, "check-dependencies", "--phase", "2",
                         "--through", "plan")
        assert code == 1
        assert json.loads(out)["satisfied"] is False

    def test_through_with_skipped_steps(self, repo: Path):
        """Skipped steps count as completed for --through checks."""
        _run(repo, "add-phase", "--number", "1", "--title", "First", "--size", "small")
        _add_phase(repo, 2, "Second", depends_on="1")
        for step in ["brd", "spec", "plan"]:
            _complete_step(repo, 1, step, "First")
        code, out = _run(repo, "check-dependencies", "--phase", "2",
                         "--through", "plan")
        assert code == 0
        assert json.loads(out)["satisfied"] is True

    def test_through_without_deps_is_satisfied(self, repo: Path):
        _add_phase(repo, 1, "Solo")
        code, out = _run(repo, "check-dependencies", "--phase", "1",
                         "--through", "plan")
        assert code == 0
        assert json.loads(out)["satisfied"] is True


# ---------------------------------------------------------------------------
# Commands: list-phases
# ---------------------------------------------------------------------------

class TestListPhases:
    def test_empty(self, repo: Path):
        code, out = _run(repo, "list-phases")
        assert "No phases found" in out

    def test_filter_by_status(self, repo: Path):
        _add_phase(repo, 1, "A")
        _add_phase(repo, 2, "B")
        _run(repo, "set-step-status", "--phase", "1",
             "--step", "ideas", "--status", "in_progress")
        code, out = _run(repo, "list-phases", "--status", "started")
        assert "Phase 1" in out
        assert "Phase 2" not in out

    def test_json_output(self, repo: Path):
        _add_phase(repo, 1, "A")
        code, out = _run(repo, "list-phases", "--json")
        phases = json.loads(out)
        assert len(phases) == 1
        assert phases[0]["title"] == "A"


# ---------------------------------------------------------------------------
# render_plan
# ---------------------------------------------------------------------------

class TestRenderPlan:
    def test_renders_table(self, repo: Path):
        _add_phase(repo)
        plan = (repo / "phases/implementation-plan.md").read_text()
        assert "| Phase 24 Search |" in plan
        assert "frontend, backend" in plan

    def test_preserves_surrounding_content(self, repo: Path):
        _add_phase(repo)
        plan = (repo / "phases/implementation-plan.md").read_text()
        assert "# Plan" in plan
        assert "## Next Section" in plan

    def test_no_plan_file(self, tmp_path: Path):
        """render_plan should not crash if implementation-plan.md is missing."""
        (tmp_path / "phases").mkdir(parents=True)
        (tmp_path / "phases/phase-tracker.yaml").write_text("phases: []\n")
        pw.render_plan(tmp_path, {"phases": []})  # should not raise


# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------

class TestDeepMerge:
    def test_simple_override(self):
        base = {"a": 1, "b": 2}
        override = {"b": 3}
        assert pw._deep_merge(base, override) == {"a": 1, "b": 3}

    def test_nested_merge(self):
        base = {"paths": {"tracker": "a", "plan": "b"}}
        override = {"paths": {"tracker": "x"}}
        result = pw._deep_merge(base, override)
        assert result["paths"]["tracker"] == "x"
        assert result["paths"]["plan"] == "b"

    def test_list_replaces(self):
        base = {"items": [1, 2]}
        override = {"items": [3]}
        assert pw._deep_merge(base, override) == {"items": [3]}

    def test_new_keys_added(self):
        base = {"a": 1}
        override = {"b": 2}
        assert pw._deep_merge(base, override) == {"a": 1, "b": 2}

    def test_base_not_mutated(self):
        base = {"a": {"x": 1}}
        override = {"a": {"x": 2}}
        pw._deep_merge(base, override)
        assert base["a"]["x"] == 1


class TestLoadConfig:
    def test_defaults_when_no_file(self, tmp_path: Path):
        config = pw.load_config(tmp_path)
        assert config["paths"]["tracker"] == "phases/phase-tracker.yaml"
        assert config["project"]["name"] == "My Project"

    def test_custom_config(self, tmp_path: Path):
        (tmp_path / "pew.yaml").write_text(yaml.dump({
            "project": {"name": "Custom App"},
            "paths": {"tracker": "tracking/phases.yaml"},
        }))
        config = pw.load_config(tmp_path)
        assert config["project"]["name"] == "Custom App"
        assert config["paths"]["tracker"] == "tracking/phases.yaml"
        # Other defaults still present
        assert config["paths"]["plan"] == "phases/implementation-plan.md"

    def test_empty_config_file(self, tmp_path: Path):
        (tmp_path / "pew.yaml").write_text("")
        config = pw.load_config(tmp_path)
        assert config == pw._deep_merge(pw.DEFAULT_CONFIG, {})

    def test_council_defaults(self, tmp_path: Path):
        config = pw.load_config(tmp_path)
        assert config["council"]["enabled"] is True
        assert config["council"]["experts"] == []
        assert config["council"]["max_findings_per_expert"] == 15
        assert config["council"]["skip_tags"] == []

    def test_council_custom(self, tmp_path: Path):
        (tmp_path / "pew.yaml").write_text(yaml.dump({
            "council": {
                "enabled": False,
                "max_findings_per_expert": 10,
                "skip_tags": ["docs-only"],
            },
        }))
        config = pw.load_config(tmp_path)
        assert config["council"]["enabled"] is False
        assert config["council"]["max_findings_per_expert"] == 10
        assert config["council"]["skip_tags"] == ["docs-only"]
        # Default still present
        assert config["council"]["experts"] == []


class TestRepoRootFromScript:
    def test_finds_git_dir_from_cwd(self, tmp_path: Path, monkeypatch):
        """repo_root_from_script walks up from CWD and finds .git."""
        project = tmp_path / "project"
        (project / ".git").mkdir(parents=True)
        nested = project / "a" / "b" / "c"
        nested.mkdir(parents=True)
        monkeypatch.chdir(nested)
        assert pw.repo_root_from_script() == project

    def test_finds_pew_yaml_from_cwd(self, tmp_path: Path, monkeypatch):
        project = tmp_path / "project"
        project.mkdir()
        (project / "pew.yaml").write_text("project:\n  name: Test\n")
        nested = project / "a" / "b"
        nested.mkdir(parents=True)
        monkeypatch.chdir(nested)
        assert pw.repo_root_from_script() == project

    def test_fallback_to_cwd(self, tmp_path: Path, monkeypatch):
        """When no .git or pew.yaml found, falls back to CWD."""
        isolated = tmp_path / "no-markers" / "deep"
        isolated.mkdir(parents=True)
        monkeypatch.chdir(isolated)
        assert pw.repo_root_from_script() == isolated


class TestConfigAwarePaths:
    def test_tracker_path_default(self, tmp_path: Path):
        path = pw.tracker_path(tmp_path)
        assert path == tmp_path / "phases/phase-tracker.yaml"

    def test_tracker_path_custom(self, tmp_path: Path):
        config = pw._deep_merge(pw.DEFAULT_CONFIG, {"paths": {"tracker": "my/tracker.yaml"}})
        path = pw.tracker_path(tmp_path, config)
        assert path == tmp_path / "my/tracker.yaml"

    def test_plan_path_custom(self, tmp_path: Path):
        config = pw._deep_merge(pw.DEFAULT_CONFIG, {"paths": {"plan": "my/plan.md"}})
        path = pw.plan_path(tmp_path, config)
        assert path == tmp_path / "my/plan.md"

    def test_phase_dir_custom(self, tmp_path: Path):
        config = pw._deep_merge(pw.DEFAULT_CONFIG, {"paths": {"phases": "my/phases"}})
        phase = {"number": 1, "title": "Test"}
        pdir = pw.phase_dir(tmp_path, phase, config)
        assert pdir == tmp_path / "my/phases/phase-1-test"


# ---------------------------------------------------------------------------
# Commands: dump-config, generate-verify-commands
# ---------------------------------------------------------------------------

class TestDumpConfig:
    def test_default_config(self, repo: Path):
        code, out = _run(repo, "dump-config")
        assert code == 0
        config = json.loads(out)
        # Fixture writes pew.yaml with project.name = "TestProject"
        assert config["project"]["name"] == "TestProject"
        assert config["paths"]["tracker"] == "phases/phase-tracker.yaml"
        assert config["council"]["enabled"] is True
        assert config["council"]["max_findings_per_expert"] == 15

    def test_custom_config(self, repo: Path):
        (repo / "pew.yaml").write_text(yaml.dump({
            "project": {"name": "My App"},
            "commands": {"verify": "npm test"},
        }))
        code, out = _run(repo, "dump-config")
        assert code == 0
        config = json.loads(out)
        assert config["project"]["name"] == "My App"
        assert config["commands"]["verify"] == "npm test"


class TestGenerateVerifyCommands:
    def test_default_empty(self, repo: Path):
        code, out = _run(repo, "generate-verify-commands")
        assert code == 0
        result = json.loads(out)
        assert result["verify"] == ""
        assert result["e2e"] == ""

    def test_custom_commands(self, repo: Path):
        (repo / "pew.yaml").write_text(yaml.dump({
            "commands": {"verify": "make check", "e2e": "make e2e"},
        }))
        code, out = _run(repo, "generate-verify-commands")
        assert code == 0
        result = json.loads(out)
        assert result["verify"] == "make check"
        assert result["e2e"] == "make e2e"


# ---------------------------------------------------------------------------
# Custom paths end-to-end
# ---------------------------------------------------------------------------

class TestCustomPaths:
    """Verify that commands use config-driven paths instead of hardcoded ones."""

    @pytest.fixture
    def custom_repo(self, tmp_path: Path) -> Path:
        """Create a repo with non-default paths via pew.yaml."""
        (tmp_path / "pew.yaml").write_text(yaml.dump({
            "project": {"name": "CustomPathProject"},
            "approval_gates": {"before_build": False, "before_close": False},
            "paths": {
                "tracker": "workflow/tracker.yaml",
                "plan": "workflow/plan.md",
                "phases": "workflow/phases",
            },
        }))
        (tmp_path / "workflow").mkdir()
        (tmp_path / "workflow/tracker.yaml").write_text("phases: []\n")
        (tmp_path / "workflow/plan.md").write_text(
            "# Plan\n\n## 1.1 Phase Status Tracker\n\n"
            "| Phase | Status | Summary | Tags | Depends On |\n"
            "| ----- | ------ | ------- | ---- | ---------- |\n\n"
            "## Next Section\n",
        )
        subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "init", "--no-gpg-sign"],
            cwd=tmp_path, capture_output=True,
            env={"GIT_AUTHOR_NAME": "test", "GIT_AUTHOR_EMAIL": "t@t",
                 "GIT_COMMITTER_NAME": "test", "GIT_COMMITTER_EMAIL": "t@t",
                 "HOME": str(tmp_path), "PATH": "/usr/bin:/bin:/usr/local/bin"},
        )
        return tmp_path

    def test_add_phase_uses_custom_tracker(self, custom_repo: Path):
        code, _ = _run(custom_repo, "add-phase", "--number", "1", "--title", "Test")
        assert code == 0
        tracker = yaml.safe_load((custom_repo / "workflow/tracker.yaml").read_text())
        assert len(tracker["phases"]) == 1

    def test_add_phase_renders_custom_plan(self, custom_repo: Path):
        _run(custom_repo, "add-phase", "--number", "1", "--title", "Test")
        plan = (custom_repo / "workflow/plan.md").read_text()
        assert "Phase 1 Test" in plan

    def test_set_step_creates_custom_phase_dir(self, custom_repo: Path):
        _run(custom_repo, "add-phase", "--number", "1", "--title", "Test")
        _run(custom_repo, "set-step-status", "--phase", "1",
             "--step", "ideas", "--status", "in_progress")
        assert (custom_repo / "workflow/phases/phase-1-test").is_dir()

    def test_analyze_uses_custom_paths(self, custom_repo: Path):
        _run(custom_repo, "add-phase", "--number", "1", "--title", "Test")
        code, out = _run(custom_repo, "analyze-phase", "--phase", "1", "--json")
        assert code == 0
        result = json.loads(out)
        assert "workflow/phases" in result["phase_dir"]


# ---------------------------------------------------------------------------
# Phase sizing
# ---------------------------------------------------------------------------

class TestPhaseSizing:
    def test_default_size_is_large(self, repo: Path):
        _add_phase(repo)
        data = pw.load_tracker(repo)
        assert data["phases"][0]["size"] == "large"
        # All steps should be not_started
        for step in pw.STEP_ORDER:
            assert data["phases"][0]["steps"][step] == "not_started"

    def test_small_skips_ideas_and_research(self, repo: Path):
        code, _ = _run(repo, "add-phase", "--number", "1", "--title", "Tiny Fix", "--size", "small")
        assert code == 0
        data = pw.load_tracker(repo)
        phase = data["phases"][0]
        assert phase["size"] == "small"
        assert phase["steps"]["ideas"] == "skipped"
        assert phase["steps"]["research"] == "skipped"
        assert phase["steps"]["brd"] == "not_started"
        assert phase["steps"]["spec"] == "not_started"
        assert phase["steps"]["plan"] == "not_started"
        assert phase["steps"]["build"] == "not_started"
        assert phase["steps"]["check"] == "not_started"

    def test_medium_skips_ideas_only(self, repo: Path):
        code, _ = _run(repo, "add-phase", "--number", "1", "--title", "Medium Change", "--size", "medium")
        assert code == 0
        data = pw.load_tracker(repo)
        phase = data["phases"][0]
        assert phase["size"] == "medium"
        assert phase["steps"]["ideas"] == "skipped"
        assert phase["steps"]["research"] == "not_started"
        assert phase["steps"]["brd"] == "not_started"

    def test_audit_skips_ideas_and_research(self, repo: Path):
        code, _ = _run(repo, "add-phase", "--number", "1", "--title", "Fix Critical Tests", "--size", "audit")
        assert code == 0
        data = pw.load_tracker(repo)
        phase = data["phases"][0]
        assert phase["size"] == "audit"
        assert phase["steps"]["ideas"] == "skipped"
        assert phase["steps"]["research"] == "skipped"
        assert phase["steps"]["brd"] == "not_started"
        assert phase["steps"]["spec"] == "not_started"
        assert phase["steps"]["plan"] == "not_started"
        assert phase["steps"]["build"] == "not_started"
        assert phase["steps"]["check"] == "not_started"

    def test_audit_phase_analyze_first_incomplete(self, repo: Path):
        _run(repo, "add-phase", "--number", "1", "--title", "Audit Fix", "--size", "audit")
        code, out = _run(repo, "analyze-phase", "--phase", "1", "--json")
        assert code == 0
        result = json.loads(out)
        assert result["size"] == "audit"
        assert result["first_incomplete_step"] == "brd"

    def test_large_skips_nothing(self, repo: Path):
        code, _ = _run(repo, "add-phase", "--number", "1", "--title", "Big Feature", "--size", "large")
        assert code == 0
        data = pw.load_tracker(repo)
        for step in pw.STEP_ORDER:
            assert data["phases"][0]["steps"][step] == "not_started"

    def test_small_phase_analyze_first_incomplete(self, repo: Path):
        _run(repo, "add-phase", "--number", "1", "--title", "Tiny", "--size", "small")
        code, out = _run(repo, "analyze-phase", "--phase", "1", "--json")
        assert code == 0
        result = json.loads(out)
        assert result["size"] == "small"
        # First incomplete should be brd (ideas and research are skipped)
        assert result["first_incomplete_step"] == "brd"

    def test_small_phase_step_ordering_respects_skipped(self, repo: Path):
        """Starting brd should work on a small phase since ideas is pre-skipped."""
        _run(repo, "add-phase", "--number", "1", "--title", "Tiny", "--size", "small")
        code, _ = _run(repo, "set-step-status", "--phase", "1",
                        "--step", "brd", "--status", "in_progress")
        assert code == 0

    def test_size_in_tracker_defaults(self, tmp_path: Path):
        """Phases loaded from tracker without size field default to large."""
        (tmp_path / "phases").mkdir(parents=True)
        tracker = tmp_path / "phases/phase-tracker.yaml"
        tracker.write_text(yaml.dump({"phases": [{"number": 1, "title": "Old", "status": "not_started"}]}))
        data = pw.load_tracker(tmp_path)
        assert data["phases"][0]["size"] == "large"


# ---------------------------------------------------------------------------
# Verification gate on close
# ---------------------------------------------------------------------------

class TestVerificationGate:
    """Phase close runs config.commands.verify and refuses to close on failure."""

    def _advance_to_check(self, repo: Path, verify_cmd: str = "true"):
        """Create a small phase with a verify command and advance to check in_progress."""
        (repo / "pew.yaml").write_text(yaml.dump({
            "project": {"name": "GateTest"},
            "commands": {"verify": verify_cmd},
            "approval_gates": {"before_build": False, "before_close": False},
        }))
        _run(repo, "add-phase", "--number", "1", "--title", "Gate Test", "--size", "small")
        for step in ["brd", "spec", "plan", "build"]:
            _complete_step(repo, 1, step, "Gate Test")
        _run(repo, "set-step-status", "--phase", "1", "--step", "check", "--status", "in_progress")

    def test_close_blocked_when_verify_fails(self, repo: Path):
        self._advance_to_check(repo, verify_cmd="exit 1")
        code, out = _run(repo, "set-step-status", "--phase", "1", "--step", "check", "--status", "complete")
        assert code == 1
        assert "BLOCKED" in out

    def test_close_allowed_when_verify_passes(self, repo: Path):
        self._advance_to_check(repo, verify_cmd="true")
        code, out = _run(repo, "set-step-status", "--phase", "1", "--step", "check", "--status", "complete")
        assert code == 0
        assert "auto-closed" in out

    def test_close_shows_failing_output(self, repo: Path):
        self._advance_to_check(repo, verify_cmd="echo 'FAIL: 2 tests failed' && exit 1")
        code, out = _run(repo, "set-step-status", "--phase", "1", "--step", "check", "--status", "complete")
        assert code == 1
        assert "2 tests failed" in out

    def test_close_allowed_when_no_verify_command(self, repo: Path):
        """If no verify command is configured, close proceeds (user hasn't set it up)."""
        self._advance_to_check(repo, verify_cmd="")
        code, out = _run(repo, "set-step-status", "--phase", "1", "--step", "check", "--status", "complete")
        assert code == 0
        assert "auto-closed" in out

    def test_close_writes_log_file(self, repo: Path):
        self._advance_to_check(repo, verify_cmd="echo 'all good'")
        _run(repo, "set-step-status", "--phase", "1", "--step", "check", "--status", "complete")
        log = repo / "phases/phase-1-gate-test/verify-output.log"
        assert log.exists()
        assert "all good" in log.read_text()

    def test_close_log_path_in_failure_output(self, repo: Path):
        self._advance_to_check(repo, verify_cmd="exit 1")
        code, out = _run(repo, "set-step-status", "--phase", "1", "--step", "check", "--status", "complete")
        assert code == 1
        assert "verify-output.log" in out

    def test_close_failure_shows_tail_only(self, repo: Path):
        # Generate 200 lines, then fail — agent should only see last 30
        cmd = "for i in $(seq 1 200); do echo \"line-$i\"; done && exit 1"
        self._advance_to_check(repo, verify_cmd=cmd)
        code, out = _run(repo, "set-step-status", "--phase", "1", "--step", "check", "--status", "complete")
        assert code == 1
        assert "line-200" in out  # last line present
        assert "line-1\n" not in out  # early lines not in agent output
        # but full output is in the log
        log = repo / "phases/phase-1-gate-test/verify-output.log"
        log_text = log.read_text()
        assert "line-1\n" in log_text
        assert "line-200" in log_text

    def test_close_blocked_when_verify_stalls(self, repo: Path):
        # Use a very short idle timeout for testing
        import unittest.mock
        cmd = "echo start && sleep 999"
        self._advance_to_check(repo, verify_cmd=cmd)
        import pw_gates
        with unittest.mock.patch.object(pw_gates, "VERIFY_IDLE_TIMEOUT", 2):
            code, out = _run(repo, "set-step-status", "--phase", "1",
                             "--step", "check", "--status", "complete")
        assert code == 1
        assert "stalled" in out


# ---------------------------------------------------------------------------
# Hardened gates
# ---------------------------------------------------------------------------

class TestHardenedGates:
    """Tests for gates enforced by pw.py (Groups A-E)."""

    # --- Group A: Artifact existence ---

    def test_complete_step_blocked_without_artifact(self, repo: Path):
        _add_phase(repo)
        _run(repo, "set-step-status", "--phase", "24", "--step", "ideas", "--status", "in_progress")
        code, out = _run(repo, "set-step-status", "--phase", "24", "--step", "ideas", "--status", "complete")
        assert code == 1
        assert "BLOCKED" in out
        assert "IDEAS.md" in out
        assert "Action:" in out

    def test_complete_step_allowed_with_artifact(self, repo: Path):
        _add_phase(repo)
        code, _ = _complete_step(repo, 24, "ideas")
        assert code == 0

    def test_build_and_check_skip_artifact_check(self, repo: Path):
        """build and check have no single artifact — should not require one."""
        _add_phase(repo, size="small")
        for step in ["brd", "spec", "plan"]:
            _complete_step(repo, 24, step)
        # build has no artifact file requirement
        _run(repo, "set-step-status", "--phase", "24", "--step", "build", "--status", "in_progress")
        code, _ = _run(repo, "set-step-status", "--phase", "24", "--step", "build", "--status", "complete")
        assert code == 0

    # --- Group B: Traceability auto-check ---

    def test_traceability_auto_checked_on_spec_complete(self, repo: Path):
        """Completing spec checks BRD→SPEC traceability."""
        _add_phase(repo, size="small")
        _complete_step(repo, 24, "brd")
        # Create SPEC.md but without FC IDs from BRD
        pdir = repo / "phases/phase-24-search"
        brd = pdir / "BRD.md"
        brd.write_text("# BRD\n## FC-001\nSome feature\n## FC-002\nAnother\n")
        spec = pdir / "SPEC.md"
        spec.write_text("# SPEC\nNo FC references here.\n")
        _run(repo, "set-step-status", "--phase", "24", "--step", "spec", "--status", "in_progress")
        code, out = _run(repo, "set-step-status", "--phase", "24", "--step", "spec", "--status", "complete")
        assert code == 1
        assert "BLOCKED" in out
        assert "Traceability" in out
        assert "FC-001" in out

    def test_traceability_skipped_when_prior_step_skipped(self, repo: Path):
        """Small phase: ideas is skipped, so ideas→brd traceability is skipped."""
        _add_phase(repo, size="small")
        code, _ = _complete_step(repo, 24, "brd")
        assert code == 0  # no traceability check since ideas was skipped

    # --- Group C: Dependency check before BUILD ---

    def test_build_blocked_on_unmet_deps(self, repo: Path):
        _add_phase(repo, 1, "First")
        _run(repo, "add-phase", "--number", "2", "--title", "Second",
             "--depends-on", "1", "--size", "small")
        for step in ["brd", "spec", "plan"]:
            _complete_step(repo, 2, step, "Second")
        code, out = _run(repo, "set-step-status", "--phase", "2", "--step", "build", "--status", "in_progress")
        assert code == 1
        assert "BLOCKED" in out
        assert "Unmet dependencies" in out

    # --- Group D: Config validation ---

    def test_config_validation_blocks_default_name(self, repo: Path):
        (repo / "pew.yaml").write_text(yaml.dump({"project": {"name": "My Project"}}))
        _add_phase(repo)
        code, out = _run(repo, "set-step-status", "--phase", "24", "--step", "ideas", "--status", "in_progress")
        assert code == 1
        assert "BLOCKED" in out
        assert "pew-init" in out

    # --- Group E: Mode-aware approval gates ---

    def test_build_approval_gate_returns_2(self, repo: Path):
        (repo / "pew.yaml").write_text(yaml.dump({
            "project": {"name": "GateProject"},
            "approval_gates": {"before_build": True, "before_close": True},
        }))
        _add_phase(repo, size="small")
        for step in ["brd", "spec", "plan"]:
            _complete_step(repo, 24, step)
        code, out = _run(repo, "set-step-status", "--phase", "24", "--step", "build", "--status", "in_progress")
        assert code == 2
        assert "APPROVAL REQUIRED" in out
        assert "--force" in out

    def test_build_approval_gate_skipped_autopilot(self, repo: Path):
        (repo / "pew.yaml").write_text(yaml.dump({
            "project": {"name": "GateProject"},
            "approval_gates": {"before_build": True, "before_close": False},
        }))
        _run(repo, "add-phase", "--number", "24", "--title", "Search",
             "--tags", "frontend,backend", "--size", "small", "--mode", "autopilot")
        for step in ["brd", "spec", "plan"]:
            _complete_step(repo, 24, step)
        code, _ = _run(repo, "set-step-status", "--phase", "24", "--step", "build", "--status", "in_progress")
        assert code == 0

    def test_build_approval_gate_skipped_config_off(self, repo: Path):
        (repo / "pew.yaml").write_text(yaml.dump({
            "project": {"name": "GateProject"},
            "approval_gates": {"before_build": False, "before_close": True},
        }))
        _add_phase(repo, size="small")
        for step in ["brd", "spec", "plan"]:
            _complete_step(repo, 24, step)
        code, _ = _run(repo, "set-step-status", "--phase", "24", "--step", "build", "--status", "in_progress")
        assert code == 0

    def test_close_approval_gate_returns_2(self, repo: Path):
        (repo / "pew.yaml").write_text(yaml.dump({
            "project": {"name": "GateProject"},
            "approval_gates": {"before_build": False, "before_close": True},
        }))
        _add_phase(repo, size="small")
        for step in ["brd", "spec", "plan", "build"]:
            _complete_step(repo, 24, step)
        _run(repo, "set-step-status", "--phase", "24", "--step", "check", "--status", "in_progress")
        code, out = _run(repo, "set-step-status", "--phase", "24", "--step", "check", "--status", "complete")
        assert code == 2
        assert "APPROVAL REQUIRED" in out

    def test_close_forced_after_approval(self, repo: Path):
        (repo / "pew.yaml").write_text(yaml.dump({
            "project": {"name": "GateProject"},
            "approval_gates": {"before_build": False, "before_close": True},
        }))
        _add_phase(repo, size="small")
        for step in ["brd", "spec", "plan", "build"]:
            _complete_step(repo, 24, step)
        _run(repo, "set-step-status", "--phase", "24", "--step", "check", "--status", "in_progress")
        # First attempt returns 2
        code, _ = _run(repo, "set-step-status", "--phase", "24", "--step", "check", "--status", "complete")
        assert code == 2
        # With --force, proceeds
        code, out = _run(repo, "set-step-status", "--phase", "24", "--step", "check", "--status", "complete", "--force")
        assert code == 0
        assert "auto-closed" in out

    def test_set_mode(self, repo: Path):
        _add_phase(repo)
        code, out = _run(repo, "set-mode", "--phase", "24", "--mode", "autopilot")
        assert code == 0
        data = pw.load_tracker(repo)
        assert data["phases"][0]["mode"] == "autopilot"

    def test_add_phase_with_mode(self, repo: Path):
        _run(repo, "add-phase", "--number", "1", "--title", "Auto Phase", "--mode", "autopilot")
        data = pw.load_tracker(repo)
        assert data["phases"][0]["mode"] == "autopilot"

    def test_set_mode_range(self, repo: Path):
        """--from 2 --to 4 sets mode on phases 2, 3, 4 only."""
        for i in range(1, 6):
            _run(repo, "add-phase", "--number", str(i), "--title", f"Phase {i}")
        code, out = _run(repo, "set-mode", "--from", "2", "--to", "4", "--mode", "autopilot")
        assert code == 0
        data = pw.load_tracker(repo)
        modes = {p["number"]: p["mode"] for p in data["phases"]}
        assert modes[1] == "manual"
        assert modes[2] == "autopilot"
        assert modes[3] == "autopilot"
        assert modes[4] == "autopilot"
        assert modes[5] == "manual"

    def test_set_mode_from_only(self, repo: Path):
        """--from 3 without --to sets phases 3+ to the end."""
        for i in range(1, 5):
            _run(repo, "add-phase", "--number", str(i), "--title", f"Phase {i}")
        code, _ = _run(repo, "set-mode", "--from", "3", "--mode", "auto")
        assert code == 0
        data = pw.load_tracker(repo)
        modes = {p["number"]: p["mode"] for p in data["phases"]}
        assert modes[1] == "manual"
        assert modes[2] == "manual"
        assert modes[3] == "auto"
        assert modes[4] == "auto"

    def test_autopilot_mode_guidance_on_step_start(self, repo: Path):
        """Starting a step in autopilot prints mode guidance."""
        _run(repo, "add-phase", "--number", "1", "--title", "Auto", "--size", "small", "--mode", "autopilot")
        code, out = _run(repo, "set-step-status", "--phase", "1", "--step", "brd", "--status", "in_progress")
        assert code == 0
        assert "MODE: autopilot" in out
        assert "AskUserQuestion" in out

    def test_auto_mode_guidance_on_step_start(self, repo: Path):
        """Starting a step in auto mode prints mode guidance."""
        _run(repo, "add-phase", "--number", "1", "--title", "Auto", "--size", "small", "--mode", "auto")
        code, out = _run(repo, "set-step-status", "--phase", "1", "--step", "brd", "--status", "in_progress")
        assert code == 0
        assert "MODE: auto" in out

    def test_manual_mode_no_guidance(self, repo: Path):
        """Starting a step in manual mode prints no MODE line."""
        _add_phase(repo, size="small")
        code, out = _run(repo, "set-step-status", "--phase", "24", "--step", "brd", "--status", "in_progress")
        assert code == 0
        assert "MODE:" not in out

    def test_close_shows_next_autopilot_phase(self, repo: Path):
        """After closing a phase, if next phase is autopilot, print NEXT guidance."""
        _run(repo, "add-phase", "--number", "1", "--title", "First", "--size", "small", "--mode", "autopilot")
        _run(repo, "add-phase", "--number", "2", "--title", "Second", "--size", "small", "--mode", "autopilot")
        for step in ["brd", "spec", "plan", "build"]:
            _complete_step(repo, 1, step, "First")
        _run(repo, "set-step-status", "--phase", "1", "--step", "check", "--status", "in_progress")
        code, out = _run(repo, "set-step-status", "--phase", "1", "--step", "check", "--status", "complete")
        assert code == 0
        assert "NEXT: Phase 2" in out
        assert "autopilot" in out
        assert "start it immediately" in out

    def test_close_all_phases_complete(self, repo: Path):
        """After closing the last phase, print 'All phases complete'."""
        _run(repo, "add-phase", "--number", "1", "--title", "Only", "--size", "small", "--mode", "autopilot")
        for step in ["brd", "spec", "plan", "build"]:
            _complete_step(repo, 1, step, "Only")
        _run(repo, "set-step-status", "--phase", "1", "--step", "check", "--status", "in_progress")
        code, out = _run(repo, "set-step-status", "--phase", "1", "--step", "check", "--status", "complete")
        assert code == 0
        assert "All phases complete." in out

    def test_close_autopilot_no_more_eligible(self, repo: Path):
        """Autopilot phase closes but remaining phases are manual → autopilot complete."""
        _run(repo, "add-phase", "--number", "1", "--title", "Auto", "--size", "small", "--mode", "autopilot")
        _run(repo, "add-phase", "--number", "2", "--title", "Manual", "--size", "small", "--mode", "manual")
        for step in ["brd", "spec", "plan", "build"]:
            _complete_step(repo, 1, step, "Auto")
        _run(repo, "set-step-status", "--phase", "1", "--step", "check", "--status", "in_progress")
        code, out = _run(repo, "set-step-status", "--phase", "1", "--step", "check", "--status", "complete")
        assert code == 0
        assert "Autopilot complete" in out

    def test_close_skips_phase_with_unmet_deps(self, repo: Path):
        """Next autopilot phase has unmet deps → skip to one with met deps."""
        _run(repo, "add-phase", "--number", "1", "--title", "First", "--size", "small", "--mode", "autopilot")
        # Phase 2 depends on phase 3 (unmet), phase 3 has no deps
        _run(repo, "add-phase", "--number", "2", "--title", "Blocked",
             "--size", "small", "--mode", "autopilot", "--depends-on", "3")
        _run(repo, "add-phase", "--number", "3", "--title", "Free",
             "--size", "small", "--mode", "autopilot")
        for step in ["brd", "spec", "plan", "build"]:
            _complete_step(repo, 1, step, "First")
        _run(repo, "set-step-status", "--phase", "1", "--step", "check", "--status", "in_progress")
        code, out = _run(repo, "set-step-status", "--phase", "1", "--step", "check", "--status", "complete")
        assert code == 0
        assert "NEXT: Phase 3" in out  # skipped phase 2 (deps unmet)

    def test_close_manual_mode_no_next(self, repo: Path):
        """Manual mode close prints no NEXT or Autopilot line."""
        _run(repo, "add-phase", "--number", "1", "--title", "Manual", "--size", "small", "--mode", "manual")
        _run(repo, "add-phase", "--number", "2", "--title", "Second", "--size", "small", "--mode", "autopilot")
        for step in ["brd", "spec", "plan", "build"]:
            _complete_step(repo, 1, step, "Manual")
        _run(repo, "set-step-status", "--phase", "1", "--step", "check", "--status", "in_progress")
        code, out = _run(repo, "set-step-status", "--phase", "1", "--step", "check", "--status", "complete")
        assert code == 0
        assert "NEXT:" not in out
        assert "Autopilot complete" not in out

    def test_set_mode_range_skips_complete(self, repo: Path):
        """Completed phases in range are not changed."""
        _run(repo, "add-phase", "--number", "1", "--title", "Done")
        _run(repo, "add-phase", "--number", "2", "--title", "Pending")
        # Manually mark phase 1 as complete in tracker
        data = pw.load_tracker(repo)
        data["phases"][0]["status"] = "complete"
        pw.save_tracker(repo, data)
        code, _ = _run(repo, "set-mode", "--from", "1", "--to", "2", "--mode", "autopilot")
        assert code == 0
        data = pw.load_tracker(repo)
        assert data["phases"][0]["mode"] == "manual"  # complete, not changed
        assert data["phases"][1]["mode"] == "autopilot"

    def test_force_close_skips_reverify(self, repo: Path):
        """After approval gate (exit 2), --force should not re-run verification."""
        (repo / "pew.yaml").write_text(yaml.dump({
            "project": {"name": "GateProject"},
            "commands": {"verify": "echo VERIFY_RAN"},
            "approval_gates": {"before_build": False, "before_close": True},
        }))
        _add_phase(repo, size="small")
        for step in ["brd", "spec", "plan", "build"]:
            _complete_step(repo, 24, step)
        _run(repo, "set-step-status", "--phase", "24", "--step", "check", "--status", "in_progress")
        # First attempt: verify runs, then approval gate fires
        code, out = _run(repo, "set-step-status", "--phase", "24", "--step", "check", "--status", "complete")
        assert code == 2
        assert "VERIFY_RAN" not in out or "APPROVAL REQUIRED" in out
        # Force: should skip re-verification
        code, out = _run(repo, "set-step-status", "--phase", "24", "--step", "check", "--status", "complete", "--force")
        assert code == 0
        assert "skipping re-run" in out

    def test_mode_in_analyze_phase_json(self, repo: Path):
        _run(repo, "add-phase", "--number", "1", "--title", "Test", "--mode", "autopilot")
        code, out = _run(repo, "analyze-phase", "--phase", "1", "--json")
        assert code == 0
        result = json.loads(out)
        assert result["mode"] == "autopilot"

    def test_mode_defaults_in_load_tracker(self, tmp_path: Path):
        """Phases without mode field in YAML get 'manual' default."""
        (tmp_path / "phases").mkdir(parents=True)
        tracker = tmp_path / "phases/phase-tracker.yaml"
        tracker.write_text(yaml.dump({"phases": [{"number": 1, "title": "Old", "status": "not_started"}]}))
        data = pw.load_tracker(tmp_path)
        assert data["phases"][0]["mode"] == "manual"


# ---------------------------------------------------------------------------
# Scoped config output
# ---------------------------------------------------------------------------

class TestScopedConfig:
    def test_scope_agent(self, repo: Path):
        (repo / "pew.yaml").write_text(yaml.dump({
            "project": {"name": "Test"},
            "conventions_file": "docs/conventions.md",
            "competitors": ["Rival"],
            "council": {"enabled": False},
        }))
        code, out = _run(repo, "dump-config", "--scope", "agent")
        assert code == 0
        config = json.loads(out)
        assert "project" in config
        assert "paths" in config
        assert "stack" in config
        assert "conventions_file" in config
        assert "competitors" not in config
        assert "council" not in config

    def test_scope_council(self, repo: Path):
        # Add conventions_file so it appears in output (empty values are stripped)
        (repo / "pew.yaml").write_text(yaml.dump({
            "conventions_file": "docs/conventions.md",
            "council": {"enabled": False},
        }))
        code, out = _run(repo, "dump-config", "--scope", "council")
        assert code == 0
        config = json.loads(out)
        assert "project" in config
        assert "paths" in config
        assert "council" in config
        assert "conventions_file" in config
        assert "stack" not in config
        assert "competitors" not in config

    def test_scope_research(self, repo: Path):
        (repo / "pew.yaml").write_text(yaml.dump({
            "competitors": ["Rival"],
        }))
        code, out = _run(repo, "dump-config", "--scope", "research")
        assert code == 0
        config = json.loads(out)
        assert "project" in config
        assert "paths" in config
        assert "stack" in config
        assert "competitors" in config
        assert "council" not in config
        assert "conventions_file" not in config

    def test_no_scope_returns_full(self, repo: Path):
        (repo / "pew.yaml").write_text(yaml.dump({
            "competitors": ["Rival"],
        }))
        code, out = _run(repo, "dump-config")
        assert code == 0
        config = json.loads(out)
        assert "project" in config
        assert "council" in config
        assert "competitors" in config
        assert "stack" in config


# ---------------------------------------------------------------------------
# TestResolveProfiles
# ---------------------------------------------------------------------------

class TestResolveProfiles:
    @pytest.fixture
    def profiles_dir(self, tmp_path: Path) -> Path:
        d = tmp_path / "profiles"
        d.mkdir()
        (d / "typescript.md").write_text(
            "---\nname: typescript\nkeywords: [typescript, ts]\npriority: 3\n---\n\n"
            "# TypeScript Best Practices\n\n"
            "## Rules\n\n"
            "### **Rule: Enable strict mode**\n\n"
            "**Always** enable `strict: true` in tsconfig.\n\n"
            "```json\n{\"strict\": true}\n```\n\n"
            "- **Why:** Catches bugs.\n",
            encoding="utf-8",
        )
        (d / "react.md").write_text(
            "---\nname: react\nkeywords: [react, jsx, tsx, component]\npriority: 10\n"
            "extends:\n  - typescript.md\n---\n\n"
            "# React Best Practices\n\n"
            "### **Rule: Use functional components**\n\n"
            "**Prefer** function components over class components.\n",
            encoding="utf-8",
        )
        (d / "_base.md").write_text(
            "---\nname: base\nkeywords: [javascript]\npriority: 1\n---\n\n"
            "# Base\n",
            encoding="utf-8",
        )
        return d

    def test_matches_by_extension(self, profiles_dir: Path):
        parser = pw.build_parser()
        args = parser.parse_args([
            "resolve-profiles", "--profiles-dir", str(profiles_dir),
            "--files", "src/app.ts", "--json",
        ])
        import io, contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = args.func(args)
        assert code == 0
        result = json.loads(buf.getvalue())
        names = [p["name"] for p in result["profiles"]]
        assert "typescript" in names

    def test_extends_resolved(self, profiles_dir: Path):
        parser = pw.build_parser()
        args = parser.parse_args([
            "resolve-profiles", "--profiles-dir", str(profiles_dir),
            "--files", "src/App.tsx", "--json",
        ])
        import io, contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = args.func(args)
        assert code == 0
        result = json.loads(buf.getvalue())
        names = [p["name"] for p in result["profiles"]]
        # typescript should be resolved via react's extends
        assert "typescript" in names
        assert "react" in names
        # Priority order: typescript (3) before react (10)
        assert names.index("typescript") < names.index("react")

    def test_underscore_files_skipped(self, profiles_dir: Path):
        parser = pw.build_parser()
        args = parser.parse_args([
            "resolve-profiles", "--profiles-dir", str(profiles_dir),
            "--files", "src/app.js", "--json",
        ])
        import io, contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = args.func(args)
        assert code == 0
        result = json.loads(buf.getvalue())
        names = [p["name"] for p in result["profiles"]]
        assert "base" not in names

    def test_summary_strips_code_blocks(self, profiles_dir: Path):
        parser = pw.build_parser()
        args = parser.parse_args([
            "resolve-profiles", "--profiles-dir", str(profiles_dir),
            "--files", "src/app.ts", "--summary",
        ])
        import io, contextlib
        buf = io.StringIO()
        err = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(err):
            code = args.func(args)
        assert code == 0
        output = buf.getvalue()
        assert "```" not in output
        assert "strict" in output.lower()

    def test_no_match_returns_empty(self, profiles_dir: Path):
        parser = pw.build_parser()
        args = parser.parse_args([
            "resolve-profiles", "--profiles-dir", str(profiles_dir),
            "--files", "data.csv", "--json",
        ])
        import io, contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = args.func(args)
        assert code == 0
        result = json.loads(buf.getvalue())
        assert result["profiles"] == []


# ---------------------------------------------------------------------------
# TestExtractIds
# ---------------------------------------------------------------------------

class TestExtractIds:
    def test_extracts_fc_and_t_ids(self, repo: Path):
        _run(repo, "add-phase", "--number", "1", "--title", "Login")
        pdir = repo / "phases/phase-1-login"
        pdir.mkdir(parents=True, exist_ok=True)

        (pdir / "BRD.md").write_text(
            "# BRD\n\n"
            "| ID | Capability |\n"
            "| --- | --- |\n"
            "| FC-001 | User can log in with email |\n"
            "| FC-002 | User can reset password |\n",
            encoding="utf-8",
        )
        (pdir / "SPEC.md").write_text(
            "# SPEC\n\n"
            "| ID | FC | Test |\n"
            "| --- | --- | --- |\n"
            "| T-001 | FC-001 | Validate email format |\n"
            "| T-002 | FC-002 | Reset flow e2e |\n",
            encoding="utf-8",
        )

        code, out = _run(repo, "extract-ids", "--phase", "1")
        assert code == 0
        result = json.loads(out)
        assert len(result["capabilities"]) == 2
        assert result["capabilities"][0]["id"] == "FC-001"
        assert result["capabilities"][0]["line"] > 0
        assert len(result["tests"]) == 2
        assert result["tests"][0]["linked_fc"] == "FC-001"

    def test_deduplicates_ids(self, repo: Path):
        _run(repo, "add-phase", "--number", "1", "--title", "Login")
        pdir = repo / "phases/phase-1-login"
        pdir.mkdir(parents=True, exist_ok=True)

        (pdir / "BRD.md").write_text(
            "FC-001 first mention\nFC-001 second mention\n",
            encoding="utf-8",
        )
        (pdir / "SPEC.md").write_text("", encoding="utf-8")

        code, out = _run(repo, "extract-ids", "--phase", "1")
        assert code == 0
        result = json.loads(out)
        assert len(result["capabilities"]) == 1

    def test_extracts_ac_ids_with_linked_fcs(self, repo: Path):
        _run(repo, "add-phase", "--number", "1", "--title", "Login")
        pdir = repo / "phases/phase-1-login"
        pdir.mkdir(parents=True, exist_ok=True)

        (pdir / "BRD.md").write_text(
            "# BRD\n\n"
            "## Acceptance Criteria\n\n"
            "| AC ID | Covers FC | Criterion | Validation Signal |\n"
            "| ----- | --------- | --------- | ----------------- |\n"
            "| AC-001 | FC-001, FC-002 | No hard-coded font sizes | grep returns 0 |\n"
            "| AC-002 | FC-003 | All tests pass | CI green |\n",
            encoding="utf-8",
        )
        (pdir / "SPEC.md").write_text("", encoding="utf-8")

        code, out = _run(repo, "extract-ids", "--phase", "1")
        assert code == 0
        result = json.loads(out)
        assert len(result["acceptance_criteria"]) == 2
        assert result["acceptance_criteria"][0]["id"] == "AC-001"
        assert result["acceptance_criteria"][0]["linked_fcs"] == ["FC-001", "FC-002"]
        assert result["acceptance_criteria"][1]["id"] == "AC-002"
        assert result["acceptance_criteria"][1]["linked_fcs"] == ["FC-003"]

    def test_ac_without_linked_fcs(self, repo: Path):
        _run(repo, "add-phase", "--number", "1", "--title", "Login")
        pdir = repo / "phases/phase-1-login"
        pdir.mkdir(parents=True, exist_ok=True)

        (pdir / "BRD.md").write_text(
            "| AC-001 | — | All tests pass | CI green |\n",
            encoding="utf-8",
        )
        (pdir / "SPEC.md").write_text("", encoding="utf-8")

        code, out = _run(repo, "extract-ids", "--phase", "1")
        assert code == 0
        result = json.loads(out)
        assert len(result["acceptance_criteria"]) == 1
        assert result["acceptance_criteria"][0]["linked_fcs"] == []

    def test_ac_deduplicates(self, repo: Path):
        _run(repo, "add-phase", "--number", "1", "--title", "Login")
        pdir = repo / "phases/phase-1-login"
        pdir.mkdir(parents=True, exist_ok=True)

        (pdir / "BRD.md").write_text(
            "AC-001 first mention\nAC-001 second mention\n",
            encoding="utf-8",
        )
        (pdir / "SPEC.md").write_text("", encoding="utf-8")

        code, out = _run(repo, "extract-ids", "--phase", "1")
        assert code == 0
        result = json.loads(out)
        assert len(result["acceptance_criteria"]) == 1

    def test_missing_files_returns_empty(self, repo: Path):
        _run(repo, "add-phase", "--number", "1", "--title", "Login")
        code, out = _run(repo, "extract-ids", "--phase", "1")
        assert code == 0
        result = json.loads(out)
        assert result["capabilities"] == []
        assert result["acceptance_criteria"] == []
        assert result["tests"] == []


# ---------------------------------------------------------------------------
# TestCompactConfig
# ---------------------------------------------------------------------------

class TestCompactConfig:
    def test_empty_fields_stripped(self, repo: Path):
        code, out = _run(repo, "dump-config")
        assert code == 0
        config = json.loads(out)
        # Default empty fields should be stripped
        assert "conventions_file" not in config
        assert "competitors" not in config
        # Empty nested dicts with all-empty values should be stripped
        for key in ("guidelines",):
            if "paths" in config:
                assert key not in config["paths"]

    def test_compact_json_format(self, repo: Path):
        code, out = _run(repo, "dump-config")
        assert code == 0
        # Compact JSON has no spaces after : or ,
        assert ": " not in out
        assert ", " not in out


# ---------------------------------------------------------------------------
# TestValidateConfig
# ---------------------------------------------------------------------------

class TestValidateConfig:
    def test_no_pew_yaml(self, repo: Path):
        # Remove the pew.yaml that the repo fixture creates
        pew = repo / "pew.yaml"
        if pew.exists():
            pew.unlink()
        code, out = _run(repo, "validate-config")
        assert code == 1
        result = json.loads(out)
        assert result["configured"] is False
        assert result["valid"] is False
        assert "pew.yaml not found" in result["errors"]

    def test_default_name_is_error(self, repo: Path):
        (repo / "pew.yaml").write_text(yaml.dump({
            "project": {"name": "My Project"},
        }))
        code, out = _run(repo, "validate-config")
        assert code == 1
        result = json.loads(out)
        assert result["configured"] is True
        assert result["valid"] is False
        assert any("project.name" in e for e in result["errors"])

    def test_valid_config(self, repo: Path):
        (repo / "pew.yaml").write_text(yaml.dump({
            "project": {"name": "Real App", "description": "A real app"},
            "stack": {"description": "React, TypeScript"},
            "commands": {"verify": "npm test"},
        }))
        code, out = _run(repo, "validate-config")
        assert code == 0
        result = json.loads(out)
        assert result["configured"] is True
        assert result["valid"] is True
        assert result["errors"] == []

    def test_missing_verify_warns(self, repo: Path):
        (repo / "pew.yaml").write_text(yaml.dump({
            "project": {"name": "Real App"},
        }))
        code, out = _run(repo, "validate-config")
        result = json.loads(out)
        assert any("commands.verify" in w for w in result["warnings"])

    def test_missing_stack_warns(self, repo: Path):
        (repo / "pew.yaml").write_text(yaml.dump({
            "project": {"name": "Real App"},
            "commands": {"verify": "npm test"},
        }))
        code, out = _run(repo, "validate-config")
        result = json.loads(out)
        assert any("stack.description" in w for w in result["warnings"])


# ---------------------------------------------------------------------------
# TestVibeMode
# ---------------------------------------------------------------------------

class TestVibeMode:
    def test_vibe_size_skips_planning_steps(self, repo: Path):
        _add_phase(repo, size="vibe")
        data = pw.load_tracker(repo)
        steps = data["phases"][0]["steps"]
        assert steps["ideas"] == "skipped"
        assert steps["brd"] == "skipped"
        assert steps["research"] == "skipped"
        assert steps["spec"] == "skipped"
        assert steps["plan"] == "skipped"
        assert steps["build"] == "not_started"
        assert steps["check"] == "not_started"

    def test_vibe_build_can_start(self, repo: Path):
        _add_phase(repo, size="vibe")
        code, _ = _run(repo, "set-step-status", "--phase", "24",
                        "--step", "build", "--status", "in_progress")
        assert code == 0

    def test_skipped_to_complete_allowed(self, repo: Path):
        _add_phase(repo, size="vibe")
        # Start build first (so phase is initialized)
        _run(repo, "set-step-status", "--phase", "24",
             "--step", "build", "--status", "in_progress")
        # Synthesizer creates BRD.md, then orchestrator marks complete
        pdir = repo / "phases/phase-24-search"
        pdir.mkdir(parents=True, exist_ok=True)
        (pdir / "BRD.md").write_text("# BRD\nSynthesized.\n")
        code, _ = _run(repo, "set-step-status", "--phase", "24",
                        "--step", "brd", "--status", "complete")
        assert code == 0
        data = pw.load_tracker(repo)
        assert data["phases"][0]["steps"]["brd"] == "complete"

    def test_vibe_analyze_first_step_is_build(self, repo: Path):
        _add_phase(repo, size="vibe")
        code, out = _run(repo, "analyze-phase", "--phase", "24", "--json")
        result = json.loads(out)
        assert result["first_incomplete_step"] == "build"


# ---------------------------------------------------------------------------
# TestFloatPhaseNumbers
# ---------------------------------------------------------------------------

class TestFloatPhaseNumbers:
    def test_decimal_phase_number(self, repo: Path):
        code, _ = _run(repo, "add-phase", "--number", "7.5", "--title", "Hotfix")
        assert code == 0
        data = pw.load_tracker(repo)
        assert data["phases"][0]["number"] == 7.5

    def test_whole_number_stays_int(self, repo: Path):
        code, _ = _run(repo, "add-phase", "--number", "8", "--title", "Feature")
        assert code == 0
        data = pw.load_tracker(repo)
        assert data["phases"][0]["number"] == 8
        assert isinstance(data["phases"][0]["number"], int)

    def test_decimal_phase_dir_name(self, repo: Path):
        _run(repo, "add-phase", "--number", "7.5", "--title", "Hotfix")
        _run(repo, "set-step-status", "--phase", "7.5",
             "--step", "ideas", "--status", "in_progress")
        assert (repo / "phases" / "phase-7-5-hotfix").is_dir()

    def test_decimal_depends_on(self, repo: Path):
        _run(repo, "add-phase", "--number", "7", "--title", "Base")
        _run(repo, "add-phase", "--number", "7.5", "--title", "Hotfix",
             "--depends-on", "7")
        data = pw.load_tracker(repo)
        hotfix = [p for p in data["phases"] if p["number"] == 7.5][0]
        assert hotfix["depends_on"] == [7]

    def test_phases_sorted_by_number(self, repo: Path):
        _run(repo, "add-phase", "--number", "8", "--title", "Later")
        _run(repo, "add-phase", "--number", "7.5", "--title", "Middle")
        _run(repo, "add-phase", "--number", "7", "--title", "First")
        data = pw.load_tracker(repo)
        numbers = [p["number"] for p in data["phases"]]
        assert numbers == [7, 7.5, 8]

    def test_display_no_trailing_zero(self, repo: Path):
        _run(repo, "add-phase", "--number", "8", "--title", "Feature")
        code, out = _run(repo, "list-phases")
        assert "Phase 8:" in out
        assert "8.0" not in out
