---
name: run
description: Execute delivery phase-by-phase with high technical precision: IDEAS → BRD → RESEARCH → SPEC → PLAN → BUILD → CHECK/CLOSE. Tracks phases in YAML, enforces quality gates, and supports auto mode.
---

# Phase Execution Workflow

## Configuration

Project-specific settings live in `pew.yaml` at the repo root. The config is auto-injected by the plugin's built-in hooks (`UserPromptSubmit` and `SubagentStart`). If the config is not present in context, run `bash ${CLAUDE_PLUGIN_ROOT}/scripts/pw.sh dump-config`.

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
- `config.competitors` — competitor list for feature-benchmarker
- `config.conventions_file` — path to conventions doc (if set)
- `config.council.enabled` — whether council review runs during CHECK (default: true)
- `config.council.max_findings_per_expert` — cap per expert (default: 15)
- `config.council.skip_tags` — phase tags that skip council review (e.g., `docs-only`)
- `config.council.experts` — optional per-domain config (reference docs, custom agent files, file patterns)
- `config.approval_gates.before_build` — require explicit user approval before BUILD (default: true)
- `config.approval_gates.before_close` — require explicit user approval before CLOSE (default: true)
- `config.product_review.enabled` — whether product-reviewer runs during CHECK (default: true for frontend phases)
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

---

## Step Definitions

### Smart Step Resolution (before any command)

Run `pw.sh analyze-phase --phase <N> --json` and resume from the first incomplete step. Earlier incomplete steps always take priority. Missing files, template placeholders, and unchecked checklists count as incomplete.

### Conventions Check (before every step)

If `config.conventions_file` is set and the file exists, read it before starting any step. Conventions are settled decisions — never recommend against an accepted convention without explicit justification. When making design choices in IDEAS, BRD, SPEC, or PLAN, check conventions first.

### Step 1: IDEAS (IDEAS.md)

- Run `pw.sh set-step-status --phase N --step ideas --status in_progress`
- **Input**: Phase brief (from `{config.paths.tracker}` `brief` field), phase title/tags, previous phase RETRO.md (if exists)
- Read template reference: `templates/IDEAS.template.md`
- **Step 1a — Current state review**: Before generating ideas, review what the app currently does in the relevant area. Read existing code, routes, components, and API endpoints related to the phase topic. Summarize current capabilities as context for ideation.
- **Step 1b — Market research**: Spawn the feature-benchmarker agent (see `agents/feature-benchmarker.md`). Provide: phase brief, title, tags, current app capabilities summary, list of existing files in `{config.paths.research}/`, and the research log. Research output saved to `{config.paths.research}/benchmark-<topic-slug>.md`.
- **Step 1c — Ideation**: Using the market research brief + current state review + phase brief, produce categorized feature suggestions. Each idea gets:
  - **Importance** (`high|medium|low`) — scored on: (1) user impact breadth (how many users benefit), (2) friction reduction (how much pain it removes), (3) competitive parity (do competitors all have this?). State which factors drive the rating.
  - **Source**: `Market Research`, `Documentation`, `Current Gap`, or `New`
  - **Triage**: `selected|rejected|postponed` with rationale
- Compact inline format per idea: Importance (with scoring rationale), Source, Decision, Description, Rationale
- Open questions: present via `AskUserQuestion` tool (see integration rules below)
- Atomic commit on completion
- Run `pw.sh set-step-status --phase N --step ideas --status complete`

**DO NOT:**

- Skip current-state review (Step 1a). You cannot ideate without knowing what exists.
- Include ideas without importance scoring. Every idea needs the 3-factor rating.
- Proceed with more than 3 unresolved open questions.

### Step 2: BRD (BRD.md)

- Run `pw.sh set-step-status --phase N --step brd --status in_progress`
- **Input**: IDEAS.md selected items, project docs
- Read template reference: `templates/BRD.template.md`
- Define scope, goals, non-goals, deliverables, acceptance criteria
- Functional requirements as capability contract: FC-nnn with actor, preconditions, action, response, not-allowed, error mapping, evidence target
- **Mandatory negative acceptance criteria**: Every FC MUST have at least one "Not Allowed" entry in the Not-Allowed column. If the FC genuinely has no restrictions, state "No restrictions identified" with rationale.
- Explicit User Can / User Cannot boundaries
- If phase has `frontend` tag or BRD contains "User can" → must include `## E2E User Test Flows` section (preconditions, steps, expected outcomes, error paths)
- Open questions: present in structured format
- **Gate**: run `pw.sh verify-traceability --phase N --from ideas --to brd` before advancing
- Atomic commit on completion
- Run `pw.sh set-step-status --phase N --step brd --status complete`

**DO NOT:**

- Write FCs without "Not Allowed" entries. Every capability has boundaries.
- Skip E2E test flows for user-facing phases.
- Include implementation details. The BRD is WHAT, not HOW.

### Step 3: RESEARCH (RESEARCH.md)

- Run `pw.sh set-step-status --phase N --step research --status in_progress`
- **Input**: BRD.md, project docs/code
- Read template reference: `templates/RESEARCH.template.md`
- **Architecture baseline**: Before starting research, check if `{config.paths.research}/architecture-reference.md` exists. If it exists, read it as baseline context — research should focus on novel, phase-specific findings only. If it does not exist, create it as part of this step: perform a one-time codebase architecture analysis covering project structure, module boundaries, data flow patterns, key abstractions, and tech stack details. Save to `{config.paths.research}/architecture-reference.md`. Future phases reference this doc instead of re-analyzing. When architecture changes significantly during a phase's BUILD step, update the shared doc.
- **Conciseness target**: RESEARCH.md should contain fewer than 2000 tokens of novel, phase-specific content. Reference shared docs (architecture-reference.md, prior UX research) for baseline context rather than restating it.
- **Step 3a — Parallel research** (run concurrently where possible):
  - For frontend-tagged phases: Spawn `ux-researcher` agent with BRD.md and phase context. Produces `{config.paths.research}/ux-<theme-slug>.md` (principles, patterns, component mappings, anti-patterns).
  - Simultaneously begin technical research: investigate technical feasibility, architectural options, risks, and ambiguities. Evidence-backed findings with concrete resolution propositions.
- **Step 3b — UX design** (frontend-tagged phases only, requires 3a UX research output): Spawn `ux-designer` agent with BRD.md and UX research output. Produces `DESIGN.md` in the phase directory. Wait for completion before 3c.
- **Step 3c — Consolidate**: Merge UX research, UX design (if applicable), and technical research into RESEARCH.md.
- Each open question: concrete resolution propositions + recommendation
- Review previous phase artifacts when relevant
- Post chat summary of open questions and proposed resolutions
- Open questions: present in structured format
- Atomic commit on completion
- Run `pw.sh set-step-status --phase N --step research --status complete`

**DO NOT:**

- Skip UX research for frontend-tagged phases.
- Propose architecture without evidence (benchmarks, docs, prior art).
- Copy UX research verbatim into RESEARCH.md. Synthesize and reference.
- Repeat general architecture information available in the shared reference doc.

### Step 4: SPEC (SPEC.md)

- Run `pw.sh set-step-status --phase N --step spec --status in_progress`
- **Input**: BRD.md, RESEARCH.md
- Read template reference: `templates/SPEC.template.md`
- Deep implementation spec: architecture, data model, API contracts, auth, observability
- Explicit test plan: T-nnn with linked spec item, level, target file, scenario, assertions
- E2E test flows from BRD must map to `level: e2e` test entries
- Phase exit-criteria mapping
- **Gate**: run `pw.sh verify-traceability --phase N --from brd --to spec` before advancing
- Atomic commit on completion
- Run `pw.sh set-step-status --phase N --step spec --status complete`

**DO NOT:**

- Create test plan entries (T-nnn) without linking to a specific FC.
- Omit error handling specifications.
- Skip the traceability gate.

### Step 5: PLAN (PLAN.md)

- Run `pw.sh set-step-status --phase N --step plan --status in_progress`
- **Input**: SPEC.md
- Read template reference: `templates/PLAN.template.md`
- Ordered task list (PH-nnn) with dependencies and acceptance criteria
- Task statuses: `todo | in_progress | done | descoped`
- **Parallel tracks**: Group independent tasks into named tracks (A, B, C...). Track A = foundation tasks with no dependencies. Subsequent tracks may execute in parallel once their track-level dependencies are met.
- **Agent assignment**: For each task, suggest a tech agent based on task type: frontend component/hook/page work → `frontend-developer`, backend service/controller/migration → `backend-developer`. If no specific agent fits, leave blank (main agent handles it).
- **Gate**: run `pw.sh verify-traceability --phase N --from spec --to plan` before advancing
- Atomic commit on completion
- Run `pw.sh set-step-status --phase N --step plan --status complete`

**DO NOT:**

- Create tasks without acceptance criteria.
- Sequence tasks without considering dependency order.
- Include tasks that cannot be verified independently.
- Create tracks with circular cross-track dependencies.

### Step 6: BUILD

- Requires explicit user command: `start building phase <N>`
- **Approval gate**: If `config.approval_gates.before_build` is true, present a gate summary via `AskUserQuestion` before proceeding: phase title, completed artifacts, key SPEC decisions, and task count from PLAN. Options: "Approve BUILD" / "Request changes". This gate fires in both manual and auto mode.
- Run `pw.sh set-step-status --phase N --step build --status in_progress`
- **Pre-gate**: read relevant playbooks from `{config.paths.guidelines}/` based on phase tags. Also resolve review profiles for the phase's tech stack using the PLAN.md task file references (same resolution logic as Step 7a, but scanning task target files instead of phase-diff output). Pass matched profiles to tech agents alongside playbook context.
- Implement tasks from PLAN.md in dependency order. If tasks are organized into tracks, tracks with no cross-track dependencies may execute in parallel. Within a track, execute in dependency order.
- When a task has an Agent assignment, spawn that agent (see `agents/frontend-developer.md` or `agents/backend-developer.md`). Provide: task description, acceptance criteria, linked tests from SPEC, resolved review profiles, and project playbooks matching the agent's domain (from `{config.paths.guidelines}/`, filtered by `applies_to` tags). Each agent has mandatory verification steps (build, typecheck, lint).
- Add tests matching SPEC.md test plan
- Update implementation log in PLAN.md
- Atomic commits per implementation slice
- **Architecture reference check**: If new modules, services, or major architectural patterns were created during BUILD, update `{config.paths.research}/architecture-reference.md` to reflect the changes.
- Run `pw.sh set-step-status --phase N --step build --status complete` when done

**DO NOT:**

- Implement without reading relevant playbooks.
- Skip tests for any task.
- Change files outside the phase scope without documenting why.
- Refactor unrelated code.

### Step 7: CHECK + CLOSE

- Run `pw.sh set-step-status --phase N --step check --status in_progress`
- **Step 7a — Council Review**:
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
     - Conditional: `product-reviewer` (if phase has `frontend` tag and `config.product_review.enabled` is true) — dispatched in Step 7b, not 7a
  5. **RESOLVE REVIEW PROFILES**: Scan the `phase-diff` output file list to detect technologies (file extensions, import patterns, directory locations). Match against profiles in `${CLAUDE_PLUGIN_ROOT}/review-profiles/` using `keywords` and `matches.file_patterns` in each profile's frontmatter. Stack matched profiles by priority (lowest first). If a profile has `extends`, load parent profiles first. Log which profiles were applied (e.g., "Applying: fundamental → typescript → react → tanstack-query — 4 profiles").
  6. **DISPATCH** all active experts **in parallel** using the Agent tool. Each expert receives:
     - Phase number, title, tags
     - Domain-specific file list (from step 3)
     - BRD.md and SPEC.md paths (for artifact cross-referencing)
     - Matched review profiles content (from step 5)
     - Conventions file path (if configured)
     - Reference doc path (if configured per expert in `config.council.experts`)
  7. **COLLECT** JSON findings from each expert.
  8. **MERGE and DEDUPLICATE** (dedup key: file + line range):
     - Same file + same line range + same issue → keep the domain-specific expert's finding (higher priority), drop the generalist's
     - Same file + same line range + different angle → keep both, add `related_to` cross-reference between finding IDs
     - Contradicting findings (e.g., one says "add validation" and another says "trust the boundary") → keep both, flag for user resolution in Dedup Notes
     - Convention-covered patterns → silently drop, note in Dedup Notes
  9. **PERSIST** merged findings to `{phase-dir}/COUNCIL-REVIEW.md`. Format: date, phase number/title, list of active experts, then findings grouped by domain. Each finding includes: ID, severity, file, issue description, fix guidance, artifact_refs (array of FC-nnn/T-nnn IDs). Add a "Dedup Notes" section for any merged or dropped findings.
  10. Add merged council findings to the CHECK issue list alongside 7b results.
- **Step 7b — Verify**:
  - Run `{config.commands.verify}` (lint + typecheck + test:all); for frontend phases also run `{config.commands.e2e}`
  - Code quality check: review test files for empty assertions, `.toBeDefined()`-only tests, mocking the subject under test
  - Spawn alignment checker (see `agents/alignment-checker.md`): verify each FC-nnn has implementation, each T-nnn has test
  - If phase has `frontend` tag and `config.product_review.enabled` is true: spawn `product-reviewer` agent (see `agents/product-reviewer.md`). Provide BRD.md path, `config.product_review.app_url`, and `config.product_review.start_command`. The product reviewer uses Chrome MCP or Playwright MCP to navigate the running app and validate each FC-nnn and E2E test flow. Merge PR-nnn findings into the issue list with the same severity classification. If browser tools are unavailable, the review is skipped with a warning — add a finding to the issue list: `PR-SKIP | P2 | "Browser testing unavailable — manual validation required before CLOSE"`. The approval gate (Step 7d) must surface this to the user.
  - Reconcile documentation drift (architecture, domain, API, developer docs)
  - Classify each issue by severity:
    - **P1 (Critical)**: Broken functionality, test failures, type errors, security issues. Must fix before close.
    - **P2 (Important)**: Code quality issues, missing test coverage, alignment gaps. Should fix; may defer with rationale.
    - **P3 (Minor)**: Style issues, documentation drift, non-blocking warnings. Fix if time allows; defer freely.
  - Collect all issues (council findings + verify results) into a single list with category and severity: `council | lint | type | test | quality | alignment | docs` × `P1 | P2 | P3`
- **Step 7c — Fix** (if any issues found):
  - Fix cycle priority: resolve all P1 first, then P2, then P3.
  - For each issue, classify as `fix | descope | defer`
  - `fix`: make the change, atomic commit
  - `descope`: update SPEC.md/PLAN.md with rationale
  - `defer`: add carry-forward note to RETRO.md
  - Update COUNCIL-REVIEW.md — mark each finding with its disposition (`fixed`/`deferred`/`descoped`) and the commit hash or rationale.
  - After all fixes applied, restart from Step 7b (council review does not re-run on fix cycles). Max 3 fix cycles before escalating to user.
- **Step 7d — Close** (all P1 checks green):
  - **Approval gate**: If `config.approval_gates.before_close` is true, present a close summary via `AskUserQuestion`: verification results, link to COUNCIL-REVIEW.md, deferred P2/P3 items. Options: "Approve CLOSE" / "Request changes". Fires in both manual and auto mode.
  - Finalize COUNCIL-REVIEW.md — add a summary header with counts: total findings, fixed, deferred, descoped.
  - Record verification evidence in PLAN.md
  - Close every test ID with `passed|failed|descoped` + evidence
  - If council review surfaced recurring patterns worth codifying, offer to add them to the conventions file
  - Optional: create RETRO.md (3-5 went well, 3-5 improve, carry-forwards, max 30 lines)
  - Run `pw.sh set-step-status --phase N --step check --status complete` (auto-closes phase)

**DO NOT:**

- Close with any P1 issues unresolved.
- Skip the alignment checker agent.
- Mark tests as passing without running them.
- Skip dispatching a council expert because its domain seems irrelevant — let the expert decide.
- Include code snippets in the merged council findings.
- Auto-fix council findings without user review.

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
| `start ideas for phase <N> skip research` | Execute Step 1 without feature-benchmarker (internal/technical phases)    |

### Script Commands Reference

```
bash ${CLAUDE_PLUGIN_ROOT}/scripts/pw.sh <command>
  set-step-status --phase N --step S --status S   # auto-inits phase, auto-closes on check complete
  analyze-phase --phase N [--json]
  add-phase --number N --title T [--brief "..."] [--depends-on X,Y] [--tags a,b]
  list-phases [--status S] [--json]
  verify-traceability --phase N --from S --to S    # exit 1 if missing IDs found
  check-dependencies --phase N
  phase-diff --phase N                        # uses three-dot diff; assumes linear history from phase start
  dump-config                                      # output resolved pew.yaml as JSON
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
- **Alignment gate**: at verification, spawn alignment-checker to verify FC→implementation and T→test coverage; reports aligned/misaligned/missing

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

When spawning any sub-agent, the `SubagentStart` hook auto-injects the resolved `pew.yaml` config. Agents receive project context (name, description, stack, competitors, paths, conventions) automatically. Each agent's `.md` file documents what config fields it uses.

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
