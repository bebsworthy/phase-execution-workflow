---
name: run
description: Execute delivery phase-by-phase with high technical precision: IDEAS → BRD → RESEARCH → SPEC → PLAN → BUILD → CHECK/CLOSE. Tracks phases in YAML, enforces quality gates, and supports auto mode.
---

# Phase Execution Workflow

## Configuration

Project-specific settings live in `pew.yaml` at the repo root. **Before executing any command**, check if `pew.yaml` exists by running `bash ${CLAUDE_PLUGIN_ROOT}/scripts/pw.sh validate-config`. If it returns `"configured": false`, **stop immediately** and tell the user: "PEW is not configured for this project. Run `/pew:init` to set up your project configuration." Do not proceed with any workflow commands until `pew.yaml` exists.

If `pew.yaml` exists, load the config by running `bash ${CLAUDE_PLUGIN_ROOT}/scripts/pw.sh dump-config`. When spawning sub-agents, pass the relevant config fields from the loaded config (do not re-run the command in the agent — pass the values directly).

Config fields used throughout this skill:

- `config.project.name` / `config.project.description` — project identity for agent context
- `config.paths.tracker` — phase tracker YAML (source of truth)
- `config.paths.plan` — human-readable implementation plan (auto-rendered from YAML)
- `config.paths.phases` — directory containing phase subdirectories
- `config.paths.research` — benchmark and UX research output
- `config.paths.guidelines` — development playbooks read during BUILD
- `config.commands.verify` — full CI verification command
- `config.commands.e2e` — frontend e2e test command
- `config.stack.description` — tech stack summary for UX agents
- `config.competitors` — competitor list for build-feature-benchmarker
- `config.conventions_file` — path to conventions doc (if set)
- `config.council.enabled` — whether council review runs during CHECK (default: true)
- `config.council.max_findings_per_expert` — cap per expert (default: 15)
- `config.council.skip_tags` — phase tags that skip council review (e.g., `docs-only`)
- `config.council.experts` — optional per-domain config (reference docs, custom agent files, file patterns)
- `config.approval_gates.before_build` — require explicit user approval before BUILD (default: true)
- `config.approval_gates.before_close` — require explicit user approval before CLOSE (default: true)
- `config.product_review.enabled` — whether build-product-reviewer runs during CHECK (default: true for frontend phases)
- `config.product_review.app_url` — URL of running app for browser testing (default: `http://localhost:5173`)
- `config.product_review.start_command` — command to start the app if not reachable (e.g., `make dev-up`)
- `config.review_profiles_dir` — directory of composable tech best-practice profiles (default: `${CLAUDE_PLUGIN_ROOT}/review-profiles/`)

**Config merge note:** `pew.yaml` values are deep-merged with defaults. Scalar and object values merge recursively. List/array values (e.g., `component_paths`) are **replaced entirely** — if you override a list in `pew.yaml`, include all desired entries, not just additions.

## Core Concepts

7-step loop per phase: **IDEAS → BRD → RESEARCH → SPEC → PLAN → BUILD → CHECK/CLOSE**

- **Artifacts**: stored under `{config.paths.phases}/<phase-name>/` (IDEAS.md, BRD.md, RESEARCH.md, SPEC.md, PLAN.md, COUNCIL-REVIEW.md)
- **Phase tracker**: `{config.paths.tracker}` — source of truth for phase/step status
- **Implementation plan**: `{config.paths.plan}` — human-readable view, auto-rendered from YAML
- **Templates**: `${CLAUDE_PLUGIN_ROOT}/templates/` — references only, never copied into phase directories
- **Helper script**: `${CLAUDE_PLUGIN_ROOT}/scripts/pw.sh` — shell wrapper that auto-creates a Python venv on first run; abbreviated as `pw.sh <command>` below
- **Sub-agent contracts**: `${CLAUDE_PLUGIN_ROOT}/agents/` (see `agents/README.md` for index)
- **Review profiles**: `${CLAUDE_PLUGIN_ROOT}/review-profiles/` — composable, generic tech best practices. Injected into council experts (CHECK) and tech agents (BUILD). Complement project-specific playbooks in `{config.paths.guidelines}/`.
- **Phase naming**: convert title to kebab-case (e.g., "Phase 24 Advanced Search" → `phase-24-advanced-search`)

### Phase Sizing

Phases have a `size` field (`small | medium | large`, default: `large`) that controls which steps are mandatory:

| Size | Steps Run | Steps Skipped | Use When |
| --- | --- | --- | --- |
| **large** | All 7 steps | None | Major features, new capabilities |
| **medium** | BRD → RESEARCH → SPEC → PLAN → BUILD → CHECK | IDEAS | Well-understood features that don't need market research |
| **small** | BRD → SPEC → PLAN → BUILD → CHECK | IDEAS, RESEARCH | Bug fixes, small changes, well-scoped tasks |

Skipped steps are pre-set to `skipped` status when the phase is created via `pw.sh add-phase --size <size>`. The `analyze-phase` command respects skipped steps and resumes from the first non-skipped incomplete step.

For **medium** phases, RESEARCH still runs but skips the build-feature-benchmarker (market research) and UX research/design sub-agents — focus on technical research only.

For **small** phases, the BRD should be minimal: just FCs + acceptance criteria, no E2E test flows unless the phase is frontend-tagged.

---

## Step Definitions

### Smart Step Resolution (before any command)

Run `pw.sh analyze-phase --phase <N> --json` and resume from the first incomplete step. Earlier incomplete steps always take priority. Missing files, template placeholders, and unchecked checklists count as incomplete.

### Conventions Check (before every step)

If `config.conventions_file` is set and the file exists, read it before starting any step. Conventions are settled decisions — never recommend against an accepted convention without explicit justification. When making design choices in IDEAS, BRD, SPEC, or PLAN, check conventions first.

**Before executing any step**, read its instructions from `${CLAUDE_PLUGIN_ROOT}/skills/run/steps/<step>.md`:

| Step | File | Artifact |
| --- | --- | --- |
| 1. IDEAS | `steps/ideas.md` | IDEAS.md |
| 2. BRD | `steps/brd.md` | BRD.md |
| 3. RESEARCH | `steps/research.md` | RESEARCH.md |
| 4. SPEC | `steps/spec.md` | SPEC.md |
| 5. PLAN | `steps/plan.md` | PLAN.md |
| 6. BUILD | `steps/build.md` | (implementation) |
| 7. CHECK/CLOSE | `steps/check.md` | COUNCIL-REVIEW.md |

Only read the step file you are about to execute. Do not pre-load other steps.

---

## Command Dispatch Table

| User Intent                               | Action                                                                    |
| ----------------------------------------- | ------------------------------------------------------------------------- |
| `start phase <N>`                         | analyze-phase → begin at first incomplete step (auto-inits on first step) |
| `start ideas for phase <N>`               | Execute Step 1 only                                                       |
| `start brd for phase <N>`                 | Execute Step 2 only                                                       |
| `start researching phase <N>`             | Execute Step 3 only                                                       |
| `start spec for phase <N>`                | Execute Step 4 only                                                       |
| `start task list for phase <N>`           | Execute Step 5 only                                                       |
| `start building phase <N>`                | Execute Step 6 (explicit approval to code)                                |
| `check phase <N>`                         | Execute Step 7 check portion                                              |
| `status phase <N>`                        | Run analyze-phase, summarize progress                                     |
| `close phase <N>`                         | Execute Step 7 close portion, set complete                                |
| `start phase <N> auto`                    | run all steps in order, enforce gates (auto-inits on first step)          |
| `continue phase <N> auto`                 | analyze → resume from first incomplete, run to completion                 |
| `continue phase <N>`                      | analyze → execute next incomplete step only                               |
| `check phase <N> skip council`            | Execute Step 7 without council review (skip 7a, start at 7b)              |
| `start ideas for phase <N> skip research` | Execute Step 1 without build-feature-benchmarker (internal/technical phases)    |

### Script Commands Reference

```
bash ${CLAUDE_PLUGIN_ROOT}/scripts/pw.sh <command>
  set-step-status --phase N --step S --status S   # auto-inits phase, auto-closes on check complete
  analyze-phase --phase N [--json]
  add-phase --number N --title T [--brief "..."] [--depends-on X,Y] [--tags a,b] [--size small|medium|large]
  list-phases [--status S] [--json]
  verify-traceability --phase N --from S --to S    # exit 1 if missing IDs found
  check-dependencies --phase N
  phase-diff --phase N                        # uses three-dot diff; assumes linear history from phase start
  validate-config                                    # check pew.yaml exists and is valid
  dump-config [--scope agent|council|research]       # compact JSON, empty defaults stripped
  resolve-profiles --profiles-dir DIR --files F [--summary] [--json]  # match + output review profiles
  extract-ids --phase N                              # compact FC/T index from BRD + SPEC as JSON
  generate-verify-commands                         # output verify/e2e commands from config
```

---

## Mode Rules, Gates, and Operating Rules

### Auto Mode Rules

1. **Step ordering is strict** — same 7-step sequence, no skipping
2. **Hard gate policy** — each step must be complete + committed before the next begins
3. **Sub-agent delegation** — try one sub-agent per step; fallback to main agent if unavailable
4. **Stop condition** — approval gates always fire even in auto mode. Unresolved open questions with no good default also stop. After gate approval, resume auto mode execution from the next step without requiring a separate "continue" command.
5. **Default-by-best-practice** — proceed + log as ADR in SPEC.md
6. **Anti-drift lock** — before build step, only edit phase artifacts
7. **Pre-build** — run `pw.sh check-dependencies --phase N` to verify prerequisites

### Quality Gates

- **Traceability gate**: run `pw.sh verify-traceability` before advancing between steps (IDEAS→BRD, BRD→SPEC, SPEC→PLAN)
- **Code quality gate**: `{config.commands.verify}` must pass before phase close; also check for fake tests (empty assertions, toBeDefined-only, mocked subjects)
- **Alignment gate**: at verification, spawn build-alignment-checker to verify FC→implementation and T→test coverage; reports aligned/misaligned/missing

### Severity Classification

All issues found during CHECK are classified by severity:

- **P1 (Critical)**: Broken functionality, test failures, type errors, security vulnerabilities. Blocks close.
- **P2 (Important)**: Code quality issues, missing test coverage, alignment gaps. Should fix; may defer with documented rationale.
- **P3 (Minor)**: Style issues, documentation drift, non-blocking warnings. Fix if time allows; defer freely.

Fix cycles prioritize P1 → P2 → P3. A phase can close with P2/P3 deferred but never with P1 open.

### Conventions File

If `config.conventions_file` is set and the file exists, it contains settled architectural and coding decisions. All agents and steps must respect conventions:

- **IDEAS/BRD/SPEC/PLAN**: Check conventions before making design choices. If a convention covers the topic, follow it.
- **BUILD**: Follow conventions when implementing. Do not contradict accepted patterns.
- **CHECK**: Flag implementation that contradicts a convention as a P1 alignment issue.
- **Never recommend against** an accepted convention without explicit justification and user approval.

### Resolution Step for Failed Gates

1. Record failure
2. Categorize: `fix | descope | defer`
3. `fix`: make change, re-run failed gate only
4. `descope`: update artifacts with rationale
5. `defer`: add carry-forward note
6. Max 3 resolution cycles per gate before escalating to user

### AskUserQuestion Integration

When completing IDEAS, BRD, or RESEARCH steps, use the built-in `AskUserQuestion` tool to present open questions before proceeding. Call it with up to 4 questions per invocation. For each question:

- `question`: the full question text ending with `?`
- `header`: short label (max 12 chars), e.g. `"Scope"`, `"Auth model"`
- `options`: 2-4 choices, each with `label` (1-5 words) and `description` (trade-offs/implications). Put the recommended option first with `"(Recommended)"` appended to its label.
- `multiSelect`: `true` when choices are not mutually exclusive

Record user responses in the artifact as resolved decisions. In auto mode: proceed with the recommended option only if high confidence + low impact; otherwise call `AskUserQuestion`.

### Agent Spawning Protocol

When spawning any sub-agent, pass the relevant config fields directly in the agent prompt. Use scoped config output where appropriate: `pw.sh dump-config --scope agent` for developer agents, `--scope council` for council experts, `--scope research` for research agents. Each agent's `.md` file documents what config fields it uses.

### Operating Rules

- Keep phase artifacts as per-phase source of truth
- Do not implement before explicit user command (except in auto mode after all gates pass)
- Do not advance to next phase with unresolved P1 issues
- If scope changes, update all impacted docs in order
- Commit discipline: atomic commits after completed steps
- Update `last_updated` in edited docs on every material change

### Definition of Done

A phase is `complete` when:

1. All 5 artifacts complete and committed
2. Traceability verified across steps
3. All tests implemented or explicitly descoped
4. Verification evidence recorded
5. Documentation drift reconciled
6. Quality gate passed (lint, typecheck, tests)
7. Alignment check passed
8. No P1 issues open
9. Tracker status set to `complete`
