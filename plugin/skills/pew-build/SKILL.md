---
name: pew-build
description: Execute delivery phase-by-phase with high technical precision: IDEAS → BRD → RESEARCH → SPEC → PLAN → BUILD → CHECK/CLOSE. Tracks phases in YAML, enforces quality gates, and supports auto mode.
user-invocable: true
---

# Phase Execution Workflow

You are an **orchestrator**. Your job is to dispatch sub-agents, validate their output, enforce quality gates, and manage phase lifecycle. You do NOT read source code, write artifact documents, or do research — agents handle that.

## Configuration

Project-specific settings live in `pew.yaml` at the repo root. **Before executing any command**, check if `pew.yaml` exists by running `bash ${CLAUDE_PLUGIN_ROOT}/scripts/pw.sh validate-config`. If it returns `"configured": false`, **stop immediately** and tell the user: "PEW is not configured for this project. Run `/pew-init` to set up your project configuration." Do not proceed with any workflow commands until `pew.yaml` exists.

If `pew.yaml` exists, load the config by running `bash ${CLAUDE_PLUGIN_ROOT}/scripts/pw.sh dump-config`. Config is **auto-injected into every PEW agent** via the `SubagentStart` hook defined in `plugin.json`. The hook runs `pw.sh dump-config --scope <role>` and injects the result as `additionalContext` — agents see it in their context as `config.*` fields. You do NOT need to manually embed config in spawn prompts.

Config fields the orchestrator references directly (agents receive the full scoped config via hook injection — you don't need to know every field):

- `config.paths.*` — tracker, plan, phases, research, guidelines directories
- `config.commands.verify` — CI verification command (lint, typecheck, unit, e2e). Run by pw.py on phase close.
- `config.stack.frontend_src` — if set, activates `council-frontend` and UX research agents
- `config.conventions_file` — path to conventions doc; pass to every step agent if set
- `config.council.enabled` / `config.council.skip_tags` — controls whether council review runs in CHECK
- `config.approval_gates.before_build` / `config.approval_gates.before_close` — approval gate toggles (default: true; skipped when phase `mode` is `autopilot`)
- `config.product_review.enabled` — whether `build-product-reviewer` runs in CHECK (frontend phases)

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
- **Phase refs**: optional list of reference doc paths (relative to repo root) on each phase. Agents read these during IDEAS, BRD, RESEARCH, and BUILD to resolve finding IDs (e.g., `F-001`), user goals (e.g., `J-001`), and other external context cited in the brief.

### Phase References and Brief File

- **`refs`**: list of reference doc paths (relative to repo root). Pass to every step agent so they can resolve finding IDs (F-001, J-001, etc.).
- **`brief_file`**: path to an external document (plan, AUDIT-BRIEF.md) that agents read as primary context. Pass to every step agent (IDEAS, BRD, RESEARCH, BUILD). Never embed its content in spawn prompts.

Both are set via `pw.sh add-phase --refs "..." --brief-file "..."` or directly in the tracker YAML.

### Phase Sizing

Phases have a `size` field (`small | medium | large | audit | vibe`, default: `large`) that controls which steps are mandatory:

| Size | Steps Run | Steps Skipped | Use When |
| --- | --- | --- | --- |
| **large** | All 7 steps | None | Major features, new capabilities |
| **medium** | BRD → RESEARCH → SPEC → PLAN → BUILD → CHECK | IDEAS | Well-understood features that don't need market research |
| **small** | BRD → SPEC → PLAN → BUILD → CHECK | IDEAS, RESEARCH | Bug fixes, small changes, well-scoped tasks |
| **audit** | BRD → SPEC → PLAN → BUILD → CHECK | IDEAS, RESEARCH | Phases from audit findings — agents derive from AUDIT-BRIEF.md |
| **vibe** | BUILD → CHECK | IDEAS, BRD, RESEARCH, SPEC, PLAN | Managed by /pew-vibe — build first, synthesize docs post-hoc |

Skipped steps are pre-set to `skipped` status when the phase is created via `pw.sh add-phase --size <size>`. The `analyze-phase` command respects skipped steps and resumes from the first non-skipped incomplete step.

For **medium** phases, RESEARCH still runs but skips the build-feature-benchmarker (market research) and UX research/design sub-agents — focus on technical research only.

For **small** phases, the BRD should be focused but not shallow. The BRD writer still performs pattern analysis — scanning the codebase for all instances of patterns described in the brief — to ensure FCs cover the full scope, not just files mentioned in refs. Just FCs + acceptance criteria, no E2E test flows unless the phase is frontend-tagged.

For **audit** phases (created by `/pew-audit-to-phases`), the phase has a `brief_file` pointing to an `AUDIT-BRIEF.md` with pre-digested audit findings — per-file actions, severity, before/after code examples, and acceptance criteria. BRD and SPEC agents operate in "audit derivation mode": they derive FC-nnn and T-nnn entries from the audit findings rather than researching from scratch. The BRD writer still performs a targeted pattern scan to catch files the audit may have missed.

---

## Step Dispatch

### Smart Step Resolution (before any command)

Run `pw.sh analyze-phase --phase <N> --json` and resume from the first incomplete step. Earlier incomplete steps always take priority.

### Dispatch Loop

For each step, the orchestrator: sets status to `in_progress` (pw.py enforces dependency/approval gates), spawns the step agent(s), commits, then sets status to `complete` (pw.py enforces artifact existence + traceability). The orchestrator **never reads code or writes artifacts** — agents do that.

Each agent receives: phase context (number, title, tags, brief, brief_file if set), file paths to read, conventions file path, and relevant config fields. Pass template paths as `${CLAUDE_PLUGIN_ROOT}/templates/<STEP>.template.md`.

**Open question protocol** (applies to Steps 1-3): If an agent reports open questions, in autopilot mode proceed with the recommended option and record the question + chosen answer — pass all to the spec-writer (Step 4) for ADR entries in SPEC.md. Otherwise, present via `AskUserQuestion` (see format below) and re-spawn agent with answers.

**Mode initialization (REQUIRED before auto/autopilot execution):** When the user requests `auto` or `autopilot` mode, you MUST run `pw.sh set-mode` BEFORE executing any steps. For single phase: `set-mode --phase N --mode <mode>`. For autopilot range: `set-mode --from N [--to M] --mode autopilot`. Verify the mode was set by checking the command output. Never rely on phases already having the correct mode — always set it explicitly.

#### Step 1: IDEAS

| Agent | Input | Output |
| --- | --- | --- |
| `build-feature-benchmarker` | Phase brief, tags, research path, competitors | `{config.paths.research}/benchmark-<topic>.md` |
| `build-ideas-writer` | Phase brief, brief_file, refs, retro path, benchmark doc paths, conventions | `{phase-dir}/IDEAS.md` |

1. `pw.sh set-step-status --phase N --step ideas --status in_progress`
2. Unless `skip research` flag: spawn `build-feature-benchmarker` with phase brief, title, tags, list of existing files in `{config.paths.research}/`, research log path (`{config.paths.research}/research-log.md`). Config (competitors, research path) is auto-injected via hook. Wait for completion. Note output file path.
3. Spawn `build-ideas-writer` with: phase brief, brief_file path (if set), title, tags, refs paths, previous RETRO.md path (if exists), benchmark doc paths (from step 2), conventions file path, template path. Wait for completion.
4. Handle open questions per protocol above.
5. Atomic commit
6. `pw.sh set-step-status --phase N --step ideas --status complete` — **pw.py auto-checks**: IDEAS.md exists and is non-empty

#### Step 2: BRD

| Agent | Input | Output |
| --- | --- | --- |
| `build-brd-writer` | IDEAS.md path (if exists), brief_file, refs, conventions | `{phase-dir}/BRD.md` |

1. `pw.sh set-step-status --phase N --step brd --status in_progress`
2. Spawn `build-brd-writer` with: IDEAS.md path (only if IDEAS step was not skipped), brief_file path (if set), refs paths, conventions file path, phase context, template path. Wait for completion.
3. Handle open questions per protocol above.
4. Atomic commit
5. `pw.sh set-step-status --phase N --step brd --status complete` — **pw.py auto-checks**: BRD.md exists, ideas→brd traceability (skipped if IDEAS was skipped)

#### Step 3: RESEARCH

| Agent | Input | Output |
| --- | --- | --- |
| `build-ux-researcher` (if frontend) | BRD.md, phase context | `{config.paths.research}/ux-<theme>.md` |
| `build-ux-designer` (if frontend) | BRD.md, UX research output | `{phase-dir}/DESIGN.md` |
| `build-research-writer` | BRD.md, brief_file, refs, UX docs, arch-ref, conventions | `{phase-dir}/RESEARCH.md` |

1. `pw.sh set-step-status --phase N --step research --status in_progress`
2. If phase has `frontend` tag and size is `large`:
   a. Spawn `build-ux-researcher` with BRD.md path, phase context, config (stack, research path). Wait for completion. Note output file path.
   b. Spawn `build-ux-designer` with BRD.md path, UX research output path, phase context (number, title, tags). Config (stack, component paths) is auto-injected via hook. Wait for completion.
3. Spawn `build-research-writer` with: BRD.md path, refs paths, UX research doc paths (if any), DESIGN.md path (if exists), architecture-reference.md path, conventions file path, phase tags, template path. Wait for completion.
4. Handle open questions per protocol above.
5. Atomic commit
6. `pw.sh set-step-status --phase N --step research --status complete` — **pw.py auto-checks**: RESEARCH.md exists

#### Step 4: SPEC

| Agent | Input | Output |
| --- | --- | --- |
| `build-spec-writer` | BRD.md, RESEARCH.md, DESIGN.md?, conventions | `{phase-dir}/SPEC.md` |

1. `pw.sh set-step-status --phase N --step spec --status in_progress`
2. Spawn `build-spec-writer` with: BRD.md path, RESEARCH.md path, DESIGN.md path (if exists), conventions file path, phase context, template path. Wait for completion.
3. Atomic commit
4. `pw.sh set-step-status --phase N --step spec --status complete` — **pw.py auto-checks**: SPEC.md exists, brd→spec traceability

#### Step 5: PLAN

| Agent | Input | Output |
| --- | --- | --- |
| `build-plan-writer` | SPEC.md, conventions | `{phase-dir}/PLAN.md` |

1. `pw.sh set-step-status --phase N --step plan --status in_progress`
2. Spawn `build-plan-writer` with: SPEC.md path, conventions file path, phase context, template path. Wait for completion.
3. Atomic commit
4. `pw.sh set-step-status --phase N --step plan --status complete` — **pw.py auto-checks**: PLAN.md exists, spec→plan traceability
5. If `plan phase` mode: **STOP HERE**.

#### Step 6: BUILD

1. `pw.sh set-step-status --phase N --step build --status in_progress` — **pw.py auto-checks**: dependencies satisfied, approval gate (returns exit 2 if approval required). If exit 2: present approval gate via `AskUserQuestion` ("Approve BUILD" / "Request changes"), then re-run with `--force`.
2. Read PLAN.md **task list only** (task IDs, descriptions, agent assignments, dependencies, linked T-nnn). Do NOT read playbooks, profiles, or source code.
3. Resolve review profiles: `pw.sh resolve-profiles --profiles-dir ${CLAUDE_PLUGIN_ROOT}/review-profiles/ --files <task-target-files> --summary`
4. For each task in dependency order (tracks with no cross-track dependencies may execute in parallel):
   - Spawn the assigned agent (`build-frontend-developer` or `build-backend-developer`) with:
     - Task description and acceptance criteria
     - Linked T-nnn test entries from SPEC
     - Resolved review profile summaries (from step 3)
     - Playbook directory path: `{config.paths.guidelines}/`
     - Phase refs paths
     - Brief file path (if set — especially important for audit phases where AUDIT-BRIEF.md is primary context)
     - Verify commands: `{config.commands.verify}`
   - Wait for completion
   - Update PLAN.md task status (`done` / `descoped`)
5. **Architecture reference check**: If agent reports new modules/services/patterns created, update `{config.paths.research}/architecture-reference.md`
6. Atomic commits per implementation slice
7. `pw.sh set-step-status --phase N --step build --status complete`

#### Step 7: CHECK + CLOSE

This step stays with the orchestrator — it is coordination work (dispatching experts, merging JSON, running commands), not document authoring.

**Step 7a — Council Review**:

1. **SKIP CHECK**: If `config.council.enabled` is `false`, or phase tags match any entry in `config.council.skip_tags`, skip to 7b.
2. **SCOPE**: Run `pw.sh phase-diff --phase N` to get changed files.
3. **CATEGORIZE** files into domains:
   - `security`: auth, middleware, env, API routes, validation, webhooks
   - `architecture`: module boundaries, shared utilities, barrel exports, services
   - `testing`: `*.test.*`, `*.spec.*`, `*.e2e-spec.*` + their source files
   - `test-quality`: same files as testing (reviews test implementation quality)
   - `frontend`: components, hooks, pages, styles (if expert active)
   - `backend`: controllers, services, modules, migrations (if expert active)
4. **DETERMINE ACTIVE EXPERTS**:
   - Always active: `council-security`, `council-architecture`, `council-testing`, `council-test-quality`
   - Conditional: `council-frontend` (if phase has `frontend` tag or `config.stack.frontend_src` is set)
   - Conditional: `council-backend` (if phase has `backend` tag or server-side files are in the diff)
   - Conditional: `build-product-reviewer` (if phase has `frontend` tag and `config.product_review.enabled` is true) — dispatched in Step 7b, not 7a
5. **RESOLVE REVIEW PROFILES**: Run `pw.sh resolve-profiles --profiles-dir ${CLAUDE_PLUGIN_ROOT}/review-profiles/ --files <comma-separated-phase-diff-files> --summary`.
6. **BUILD ARTIFACT INDEX**: Run `pw.sh extract-ids --phase N`. Pass this compact JSON index to experts instead of full BRD/SPEC content.
7. **DISPATCH** all active experts **in parallel** using the Agent tool. Each expert receives:
   - Phase number, title, tags
   - Domain-specific file list (from step 3)
   - Artifact index JSON (from step 6) — NOT full BRD/SPEC content
   - BRD.md and SPEC.md file paths (for targeted reads when needed)
   - Condensed review profile summaries (from step 5)
   - Conventions file path (if configured)
   - Reference doc path (if configured per expert in `config.council.experts`)
8. **COLLECT** JSON findings from each expert. Verify valid JSON with `expert` (string) and `findings` (array) fields. If malformed, log and exclude — do not retry.
9. **MERGE and DEDUPLICATE** (dedup key: file + line range):
   - Same file + same line range + same issue → keep domain-specific expert's finding, drop generalist's
   - Same file + same line range + different angle → keep both, add `related_to` cross-reference
   - Contradicting findings → keep both, flag for user resolution in Dedup Notes
   - Convention-covered patterns → silently drop, note in Dedup Notes
10. **PERSIST** merged findings to `{phase-dir}/COUNCIL-REVIEW.md`: date, phase number/title, active experts, findings grouped by domain, Dedup Notes section.

**Step 7b — Verify**:

- **Note**: Do NOT run `{config.commands.verify}` here — `pw.sh set-step-status --step check --status complete` runs it automatically on close and blocks if tests fail. Step 7b focuses on alignment and code quality, not re-running the test suite.
- Code quality check: review test files for empty assertions, `.toBeDefined()`-only tests, mocking the subject under test
- Spawn `build-alignment-checker` with: SPEC.md path, BRD.md path, phase-diff file list, conventions file path (if configured). Verify each FC-nnn has implementation, each T-nnn has test.
- If phase has `frontend` tag and `config.product_review.enabled` is true: spawn `build-product-reviewer` with BRD.md path, `config.product_review.app_url`, `config.product_review.start_command`. If browser tools unavailable, skip with warning.
- Classify each issue by severity: P1 (Critical), P2 (Important), P3 (Minor)
- Collect all issues (council + verify) into single list: `council | lint | type | test | quality | alignment | docs` × `P1 | P2 | P3`

**Step 7c — Fix** (if issues found):

- Fix cycle priority: P1 → P2 → P3
- For each issue: classify as `fix | descope | defer`
  - `fix`: make the change, atomic commit
  - `descope`: update SPEC.md/PLAN.md with rationale
  - `defer`: add carry-forward note to RETRO.md
- **Autopilot fix policy**: P1 → auto-fix. P2 → auto-fix on first pass, defer on subsequent cycles. P3 → auto-defer immediately. If P1 unresolved after 3 cycles → **hard stop autopilot** and report.
- Update COUNCIL-REVIEW.md — mark each finding with disposition (`fixed`/`deferred`/`descoped`) + commit hash or rationale
- After all fixes, restart from 7b (council review does NOT re-run). Max 3 fix cycles before escalating.

**Step 7d — Close** (all P1 checks green):

- **Note**: The approval gate and verification are handled by pw.py (see below).
- Finalize COUNCIL-REVIEW.md — summary header with counts: total, fixed, deferred, descoped
- Record verification evidence in PLAN.md
- Close every test ID with `passed|failed|descoped` + evidence
- If recurring patterns, offer to add to conventions file
- Optional: create RETRO.md (3-5 went well, 3-5 improve, carry-forwards, max 30 lines)
- `pw.sh set-step-status --phase N --step check --status complete` — **pw.py auto-checks**: runs `config.commands.verify` (refuses to close if tests fail), then checks approval gate (returns exit 2 if approval required). If exit 2: present close approval gate via `AskUserQuestion` ("Approve CLOSE" / "Request changes"), then re-run with `--force`.

**CHECK constraints:**

- Do NOT close with any P1 issues unresolved
- Do NOT skip the alignment checker agent
- Do NOT mark tests as passing without running them
- Do NOT skip dispatching a council expert because its domain seems irrelevant — let the expert decide
- Do NOT include code snippets in merged council findings
- Do NOT auto-fix council findings without user review (exception: autopilot mode auto-fixes P1/P2 findings, defers P3)

### Autopilot Phase Loop

After step 7d completes successfully for the current phase (autopilot mode only):

0. **Verify mode is set**: Before entering the loop, confirm `set-mode` was already called for the target phases. If starting fresh, run `pw.sh set-mode --from N [--to M] --mode autopilot` first.
1. Run `pw.sh next-phase --mode auto,autopilot --json`. If result contains `"none": true`, no more eligible phases — skip to step 6.
2. Use the returned `number` and `first_incomplete_step`. Run `pw.sh analyze-phase --phase N --json` and begin at the first incomplete step. Continue the full step dispatch loop.
3. After closing the phase, repeat from step 1. If `--limit` was specified and reached, proceed to step 6.
6. **Produce autopilot summary report**:
   ```
   Autopilot complete — N phases processed

   Phase X: <title> — closed ✓ (deferred: N items)
   Phase Y: <title> — STOPPED (P1 unresolved after 3 fix cycles)
   Phase Z: <title> — skipped (unmet dependencies: [A, B])

   Total deferred items: N (see RETRO.md per phase)
   ```

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
| `start phase <N> auto`                    | `pw.sh set-mode --phase N --mode auto`, then run all steps               |
| `continue phase <N> auto`                 | `pw.sh set-mode --phase N --mode auto`, then resume from first incomplete |
| `continue phase <N>`                      | analyze → execute next incomplete step only                               |
| `plan phase <N>`                          | Run IDEAS through PLAN only (Steps 1-5), stop before BUILD               |
| `plan phase <N> auto`                     | `pw.sh set-mode --phase N --mode auto`, then run Steps 1-5               |
| `check phase <N> skip council`            | Execute Step 7 without council review (skip 7a, start at 7b)              |
| `start ideas for phase <N> skip research` | Execute Step 1 without build-feature-benchmarker (internal/technical phases)    |
| `start autopilot [from phase <N>]`        | `pw.sh set-mode --from N --mode autopilot`, then run loop from phase N         |
| `start autopilot phase <N> to <M>`        | `pw.sh set-mode --from N --to M --mode autopilot`, then run loop               |

### Script Commands Reference

```
bash ${CLAUDE_PLUGIN_ROOT}/scripts/pw.sh <command>
  set-step-status --phase N --step S --status S [--force]  # enforces all gates; exit 1 = hard fail, exit 2 = approval needed (re-run with --force)
  set-mode --phase N --mode manual|auto|autopilot  # single phase
  set-mode --from N [--to M] --mode autopilot      # range: all non-complete phases N through M (or to end)
  analyze-phase --phase N [--json]
  add-phase --number N --title T [--brief "..."] [--brief-file PATH] [--depends-on X,Y] [--tags a,b] [--size small|medium|large|audit|vibe]
  list-phases [--status S] [--json] [--all] [--upcoming N]  # default: active + next 3 upcoming
  next-phase [--mode M] [--json]                 # first eligible phase (deps satisfied); M = comma-separated mode filter
  next-phase-number                              # output next available integer phase number
  verify-traceability --phase N --from S --to S    # exit 1 if missing IDs found
  check-dependencies --phase N [--through S]   # --through: deps completed through step S (not fully complete)
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
3. **Sub-agent delegation** — every step is handled by a dedicated agent; the orchestrator only validates and gates
4. **Stop condition** — approval gates always fire even in auto mode. Unresolved open questions with no good default also stop. After gate approval, resume auto mode execution from the next step without requiring a separate "continue" command.
5. **Default-by-best-practice** — proceed + log as ADR in SPEC.md
6. **Anti-drift lock** — before build step, only edit phase artifacts
7. **Pre-build** — pw.py auto-checks dependencies when starting build (no manual call needed)

### Autopilot Mode Rules

Autopilot mode inherits all auto mode rules (strict step ordering, step-completion gates, sub-agent delegation, anti-drift lock, pre-build dependency check) with these overrides:

1. **Approval gates skipped** — both `before_build` and `before_close` gates are skipped entirely. Log: "Autopilot: skipping BUILD/CLOSE approval gate for phase N."
2. **Open questions auto-resolved** — do not call `AskUserQuestion`. Always proceed with the recommended (first) option. Record each auto-resolved question and chosen answer. Pass all to the spec-writer (Step 4) for inclusion as ADR entries in SPEC.md.
3. **Fix cycle auto-policy**:
   - P1: auto-fix (up to 3 cycles). If still unresolved after 3 cycles → **hard stop autopilot**, report to user.
   - P2: auto-fix on first pass, defer with rationale on subsequent cycles.
   - P3: auto-defer immediately with carry-forward note.
4. **Council findings** — auto-fix P1/P2 findings, defer P3. This overrides the "Do NOT auto-fix council findings without user review" constraint.
5. **Multi-phase loop** — see "Autopilot Phase Loop" section for full behavior (phase selection, hard stops, summary report).

### Concurrent Phase Work

You can plan ahead while building. Dependency checks are step-aware:

- **Planning steps** (IDEAS → PLAN): dependencies only need to have completed through PLAN. Run `pw.sh check-dependencies --phase N --through plan` before starting planning steps on a dependent phase.
- **BUILD step**: dependencies must be fully complete (`check-dependencies --phase N` without `--through`).
- **Independent phases** (no `depends_on`): can run concurrently at any step without restriction.

**`plan phase <N>`**: Runs Steps 1-5 (IDEAS through PLAN) then stops. Use this to prepare a phase while another is building. The BUILD approval gate is not reached — the phase stays in `started` status with `plan: complete, build: not_started`.

This means you can:
- Plan phase N+1 while building phase N (if N+1 depends on N and N has completed PLAN)
- Plan multiple independent phases concurrently
- Queue up planned phases and build them sequentially

### Quality Gates

pw.py enforces artifact, traceability, dependency, approval, verification, and config gates automatically via `set-step-status` (annotated at each step above). The orchestrator cannot bypass them.

The orchestrator is additionally responsible for (not enforced by pw.py):
- **Code quality check**: review test files for empty assertions, `.toBeDefined()`-only tests, mocking the subject under test (Step 7b)
- **Alignment check**: spawn `build-alignment-checker` to verify FC→implementation and T→test coverage (Step 7b)

### Severity Classification

All issues found during CHECK are classified by severity:

- **P1 (Critical)**: Broken functionality, test failures, type errors, security vulnerabilities. Blocks close.
- **P2 (Important)**: Code quality issues, missing test coverage, alignment gaps. Should fix; may defer with documented rationale.
- **P3 (Minor)**: Style issues, documentation drift, non-blocking warnings. Fix if time allows; defer freely.

Fix cycles prioritize P1 → P2 → P3. A phase can close with P2/P3 deferred but never with P1 open.

### Conventions File

If `config.conventions_file` is set and the file exists, it contains settled architectural and coding decisions. Pass the conventions file path to every step agent. Conventions rules:

- **All agents**: Check conventions before making design choices. Follow accepted patterns.
- **CHECK**: Flag implementation that contradicts a convention as a P1 alignment issue.
- **Never recommend against** an accepted convention without explicit justification and user approval.

### AskUserQuestion Integration

When a step agent reports open questions, the orchestrator presents them via the `AskUserQuestion` tool. Call it with up to 4 questions per invocation. For each question:

- `question`: the full question text ending with `?`
- `header`: short label (max 12 chars), e.g. `"Scope"`, `"Auth model"`
- `options`: 2-4 choices, each with `label` (1-5 words) and `description` (trade-offs/implications). Put the recommended option first with `"(Recommended)"` appended to its label.
- `multiSelect`: `true` when choices are not mutually exclusive

Record user responses and re-spawn the agent with answers if needed. In auto mode: proceed with recommended option only if high confidence + low impact; otherwise call `AskUserQuestion`.

### Agent Spawning Protocol

Config fields (`config.*`) are **auto-injected** via the `SubagentStart` hook — do not embed config in spawn prompts.

When spawning any sub-agent, pass only:

1. **Phase context**: number, title, tags, brief, brief_file (if set), phase directory path
2. **File paths**: input artifact paths (not content), output path, template path
3. **Refs paths**: if the phase has refs

Never pass file content inline — agents read files themselves. Never read source code or artifact content yourself — that's the agent's job.

### Operating Rules

- Commit discipline: atomic commits after completed steps (orchestrator commits, not agents)
- If scope changes mid-phase, update all impacted docs in order (BRD → SPEC → PLAN)

### Definition of Done

A phase is `complete` when:

1. All required artifacts complete and committed:
   - **large**: IDEAS.md, BRD.md, RESEARCH.md, SPEC.md, PLAN.md, COUNCIL-REVIEW.md
   - **medium**: BRD.md, RESEARCH.md, SPEC.md, PLAN.md, COUNCIL-REVIEW.md
   - **small / audit**: BRD.md, SPEC.md, PLAN.md, COUNCIL-REVIEW.md
   - **vibe**: BRD.md, SPEC.md, COUNCIL-REVIEW.md (synthesized post-hoc)
2. Traceability verified across non-skipped steps
3. All tests implemented or explicitly descoped
4. Verification passed (`pw.sh set-step-status --step check --status complete` enforces this)
5. Documentation drift reconciled
6. Alignment check passed
7. No P1 issues open
8. Tracker status set to `complete`
