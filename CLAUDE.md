# PEW Plugin Development

## What this is

A Claude Code plugin with 6 skills, 5 commands, 46 agents. See [README.md](README.md) for user-facing docs.

## Dev workflow

1. Edit agent/skill/command `.md` files and `plugin/scripts/lib/pw.py`
2. Run tests: `cd plugin/scripts/lib && .venv/bin/python3 -m pytest test_pw.py`
3. Commit. The pre-push hook auto-bumps version in both `plugin.json` and `marketplace.json`
4. Push — if the hook bumps, re-push

## Project structure

```
plugin/              → The installable plugin (marketplace.json source points here)
  skills/            → Skill definitions (pew-build, pew-init, pew-vibe, pew-ux-audit, pew-test-audit, pew-groom)
  commands/          → Command orchestrators (pew-vibe, pew-ux-audit, pew-test-audit, pew-audit-to-phases, pew-groom)
  agents/            → 45 sub-agent definitions (build-*, council-*, ux-audit-*, test-audit-*, groom-*)
  scripts/lib/       → pw.py (phase tracker CLI) + test_pw.py + .venv/
  scripts/           → pw.sh (venv wrapper), inject-config.sh (SubagentStart hook), pre-push-bump
  templates/         → Reference templates for phase artifacts (IDEAS, BRD, SPEC, etc.)
  review-profiles/   → Composable tech best-practice profiles (TypeScript, React, NestJS, etc.)
  .claude-plugin/    → plugin.json (plugin manifest)
.claude-plugin/      → marketplace.json (source: "./plugin")
```

## Key conventions

- **Agent naming**: `build-*` (step writers, devs, research), `council-*` (reviewers), `test-audit-*`, `ux-audit-*`, `groom-*` (technical grooming)
- **All agents**: Must have completion signal `[agent-name] COMPLETE ✓`, must say "do NOT commit" if they have Write/Edit tools
- **Config injection**: SubagentStart hook (`inject-config.sh`) auto-injects `pew.yaml` config into agents. Don't pass config manually in spawn prompts.
- **Sub-agents can't spawn sub-agents** (Claude Code hard limit). All agent spawning from orchestrator only.
- **Phase numbers**: Floats allowed (7.5). Use `_norm_num()` to normalize (24.0 → 24, 7.5 stays 7.5).
- **Commit discipline**: Agents never commit. Orchestrators commit after validating output.

## Sub-agent patterns

See [PATTERNS.md](PATTERNS.md) for orchestration patterns, hard constraints, and anti-patterns.

## Tests

All in `plugin/scripts/lib/test_pw.py`. Run with `.venv/bin/python3 -m pytest test_pw.py` from that directory. The venv is auto-created by `pw.sh` on first run.

When adding features to `pw.py`, add corresponding tests. Current: 128 tests.
