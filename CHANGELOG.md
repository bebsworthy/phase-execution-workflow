# Changelog

All notable changes to PEW (Phase Execution Workflow) are documented here.

## [4.0.3] — 2026-03-14

### Added
- **Vibe mode** (`/pew-vibe`): Build-first phases with continuous decision recording and post-hoc BRD/SPEC synthesis. Full CHECK/CLOSE quality gate at the end.
- **Test audit skill** (`/pew-test-audit`): 10-agent, 5-phase test suite quality audit targeting LLM-generated anti-patterns (tautological tests, over-mocking, framework testing, happy-path bias, flaky tests). Phase 2 runs 6 auditors in parallel.
- **Audit-to-phases command** (`/pew-audit-to-phases`): Convert audit findings into PEW phases with smart scheduling (start now vs. queue after current work).
- **SubagentStart hook**: Auto-injects resolved `pew.yaml` config into every PEW agent via `additionalContext`. Agents no longer need config passed manually in spawn prompts.
- **Decimal phase numbers**: Phase numbers support floats (7.5) for inserting between existing phases using the half-technique. Whole numbers display without trailing zero.
- **5 step-writer agents**: `build-ideas-writer`, `build-brd-writer`, `build-research-writer`, `build-spec-writer`, `build-plan-writer` — each owns one planning step's document authoring.
- **Vibe synthesizer agent** (`build-vibe-synthesizer`): Generates post-hoc BRD/SPEC from decision log and code diff.
- **DECISIONS.md template**: Running decision log format with D-nnn IDs, auto-classification (change vs fix), and per-instruction commit tracking.
- **PATTERNS.md**: Orchestrator patterns documentation covering sequential chains, fan-out/fan-in, research-then-synthesize, and task loops. Includes hard constraints (no agent nesting, context isolation), anti-patterns, and key references.
- **Configurable audit paths**: `paths.audit_test` and `paths.audit_ux` in pew.yaml (defaults: `phases/audit/test`, `phases/audit/ux`).
- **Completion signals**: All 34 agents now signal completion with `[agent-name] COMPLETE ✓`.
- **Commit guidance**: All agents with Write/Edit tools include "do NOT commit" instruction.

### Changed
- **Thin orchestrator**: `pew-build` SKILL.md rewritten as a dispatch loop. Orchestrator spawns step agents instead of reading code and writing documents itself. Orchestrator never reads source code or writes artifact documents.
- **Step files deleted**: `skills/pew-build/steps/` directory removed. Step instructions moved into dedicated agent definitions.
- **Command naming**: All commands renamed with `pew-` prefix for namespace consistency (`/pew-vibe`, `/pew-ux-audit`, `/pew-test-audit`, `/pew-audit-to-phases`).
- **Audit output paths**: Hardcoded `ux-review/` and `test-review/` replaced with config-driven `{config.paths.audit_ux}` and `{config.paths.audit_test}`.
- **Audit final output**: Renamed from `playbook.md` to `report.md`.
- **pew-init overhaul**: Now covers all config fields (audit paths, council, approval gates, install_commands, product review). Defines update-mode merge algorithm for non-destructive config updates.
- **Agent spawning protocol**: Config passed via SubagentStart hook instead of manual embedding in spawn prompts.

### Fixed
- Skill name mismatch: test-audit and ux-audit agents now reference correct skill names (`pew-test-audit`, `pew-ux-audit`) in frontmatter.
- Missing config field documentation in SKILL.md (`audit_test`, `audit_ux`, `frontend_src`, `component_paths`, `install_commands`).
- Stale `skills/build/` reference in pew.yaml.example.
- SKILL.md spawn instructions: added missing inputs for `build-feature-benchmarker`, `build-ux-designer`, `build-research-writer`, `build-alignment-checker`.

## [4.0.0] — 2026-03-13

### Added
- **Phase refs**: Phases can include a `refs` list pointing to external docs (UX audits, research). Agents read these during IDEAS, BRD, RESEARCH, and BUILD to resolve finding IDs.
- **Concurrent phase support**: `--through` option for `check-dependencies` enables planning phase N while building N-1. `plan phase <N>` command runs IDEAS through PLAN, stops before BUILD.
- **Auto version bump**: Pre-push hook auto-bumps patch version in both `plugin.json` and `marketplace.json`. `pw.sh bump-version` command for manual bumps.

### Changed
- Skills renamed with `pew-` prefix (`/pew-build`, `/pew-init`, `/pew-ux-audit`).
- Agents renamed to `build-*` namespace for consistency.
- Version synced across `plugin.json` and `marketplace.json`.

## [3.0.0] — 2026-03-12

### Added
- **UX audit skill** (`/pew-ux-audit`): 5-phase UX/UI audit with sequential specialist agents (goals, implementation, research, evaluation, proposals). Every finding traces to a user goal.
- Agents: `build-feature-benchmarker`, `build-ux-researcher`, `build-ux-designer`, `build-alignment-checker`, `build-frontend-developer`, `build-backend-developer`, `build-product-reviewer`.
- Council agents: `council-security`, `council-architecture`, `council-testing`, `council-test-quality`, `council-frontend`, `council-backend`.
- Review profiles: composable tech best practices (TypeScript, React, NestJS, Tailwind, etc.).

## [2.0.0] — 2026-03-11

### Added
- Phase sizing (`small`, `medium`, `large`) controlling which steps run.
- Scoped config output (`--scope agent|council|research`).
- `/pew-init` skill for project setup.

## [1.0.0] — 2026-03-10

### Added
- Initial release: 7-step phase execution loop (IDEAS → BRD → RESEARCH → SPEC → PLAN → BUILD → CHECK/CLOSE).
- YAML-based phase tracker with lifecycle commands.
- Traceability verification between steps.
- Council review with parallel expert dispatch.
- Quality gates and approval gates.
