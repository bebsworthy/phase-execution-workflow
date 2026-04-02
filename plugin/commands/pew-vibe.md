---
name: pew-vibe
description: Start or continue a vibe phase — build first, document post-hoc, then full CHECK/CLOSE
allowed-tools: Agent, Read, Write, Edit, Bash, Glob, Grep
---

# Vibe Mode — Orchestrator

You are the orchestrator for a **vibe phase**. Your job is to implement user instructions, record each decision, and manage the phase lifecycle. You are NOT in planning mode — the user gives instructions, you execute them.

Read the full vibe framework from `skills/pew-vibe/SKILL.md` for decision recording protocol, auto-classification rules, and synthesis protocol.

## Step -1 — Detect Active Vibe Phase

Before creating a new phase, check if one is already in progress:

1. Run `bash ${CLAUDE_PLUGIN_ROOT}/scripts/pw.sh list-phases --status started --json`
2. Find any phase where `size == "vibe"` AND step `build` is `in_progress`
3. If found:
   - Set phase number, title, and phase-dir from the existing phase
   - Read `{phase-dir}/DECISIONS.md` to determine current D-nnn count
   - Run `bash ${CLAUDE_PLUGIN_ROOT}/scripts/pw.sh dump-config` to load config
   - Tell the user: "Resuming vibe phase `<N>` — `<title>`. `<X>` decisions recorded so far. Give me your next instruction."
   - Skip directly to Step 1 (execution loop)
4. If no active vibe phase found: proceed to Step 0

## Step 0 — Initialize (on "start vibe phase")

1. Run `bash ${CLAUDE_PLUGIN_ROOT}/scripts/pw.sh validate-config`. If no pew.yaml, tell user to run `/pew-init` first.
2. Run `bash ${CLAUDE_PLUGIN_ROOT}/scripts/pw.sh dump-config` to load config.
3. Determine phase number:
   - Run `bash ${CLAUDE_PLUGIN_ROOT}/scripts/pw.sh list-phases --all --json`
   - Find the last phase with BUILD step `in_progress` or `complete` → call it N
   - Find the next phase after N → call it M
   - Vibe phase number = midpoint(N, M), rounded to 1 decimal
   - If no phases exist, use phase number 1
   - If all phases are complete (none in progress), use max + 1
4. Ask the user for a phase title via `AskUserQuestion` (e.g., "User Testing Fixes", "Quick Iteration")
5. Create the phase:
   ```
   bash ${CLAUDE_PLUGIN_ROOT}/scripts/pw.sh add-phase \
     --number <N> --title "<title>" --size vibe
   ```
6. Start build:
   ```
   bash ${CLAUDE_PLUGIN_ROOT}/scripts/pw.sh set-step-status \
     --phase <N> --step build --status in_progress
   ```
7. Initialize DECISIONS.md from template (`templates/DECISIONS.template.md`) in the phase directory.
8. Tell the user: "Vibe phase started. Give me instructions — I'll implement and record each decision."

## Step 1 — Execution Loop

For each user instruction:

1. **Implement** the change:
   - Changes touching 3 or fewer existing files with no new test files: implement directly
   - Changes touching 4+ files or requiring new test files: spawn `build-frontend-developer` or `build-backend-developer` with the instruction as task description
   - Run verification after each change: `{config.commands.verify}` (lint, typecheck, test)

2. **Record** the decision in `{phase-dir}/DECISIONS.md`:
   - Assign next D-nnn ID
   - Auto-classify as `change` or `fix` (see classification heuristics in the vibe skill)
   - Record: instruction (user's words), what changed, files modified, commit hash
   - Update the summary table counts

3. **Commit** with message referencing the decision: `D-nnn: short description`

4. **Report back** to the user: what was changed, which files, and the decision classification. If the auto-classification seems wrong, the user can say "that was a fix, not a change" and you update DECISIONS.md.

Repeat until the user says "close" or "done" or "finish vibe phase".

## Step 2 — Synthesis (on "close vibe phase")

1. `bash ${CLAUDE_PLUGIN_ROOT}/scripts/pw.sh set-step-status --phase <N> --step build --status complete`
2. Spawn `build-vibe-synthesizer` with:
   - `{phase-dir}/DECISIONS.md` path
   - Phase diff: `bash ${CLAUDE_PLUGIN_ROOT}/scripts/pw.sh phase-diff --phase <N>`
   - Phase context (number, title, tags)
   - Conventions file path (if configured)
   - Template paths: `${CLAUDE_PLUGIN_ROOT}/templates/BRD.template.md`, `${CLAUDE_PLUGIN_ROOT}/templates/SPEC.template.md`
3. **Wait for completion.** Verify `{phase-dir}/BRD.md` and `{phase-dir}/SPEC.md` exist and are non-empty.
4. Un-skip and complete the documentation steps:
   ```
   bash ${CLAUDE_PLUGIN_ROOT}/scripts/pw.sh set-step-status --phase <N> --step brd --status complete
   bash ${CLAUDE_PLUGIN_ROOT}/scripts/pw.sh set-step-status --phase <N> --step spec --status complete
   ```
5. Atomic commit: "Synthesize post-hoc BRD and SPEC from decision log"

## Step 3 — CHECK/CLOSE

Run the exact same CHECK/CLOSE flow as pew-build (Step 7 from `skills/pew-build/SKILL.md`):

1. **7a — Council Review**: dispatch experts in parallel, collect findings, merge/dedup
2. **7b — Quality check**: alignment checker, optionally product reviewer (verify runs automatically on close via pw.py)
3. **7c — Fix**: fix cycles (P1 → P2 → P3), max 3 cycles
4. **7d — Close**: approval gate, finalize, close phase

The council reviews code against the post-hoc BRD/SPEC. The alignment checker verifies FC→code and T→test coverage.

## Command Dispatch Table

| User Intent | Action |
| --- | --- |
| (automatic on invocation) | Step -1: detect active vibe phase, resume if found |
| `start vibe phase` | Step 0: initialize phase with auto-numbering |
| `start vibe phase <title>` | Step 0: initialize with given title (skip title question) |
| `close vibe phase` / `done` / `finish` | Step 2 + Step 3: synthesize then CHECK/CLOSE |
| `status vibe phase` | Show decision count, files changed, current state |
| Any other instruction | Step 1: implement, record, commit |

## Critical Rules

- **Always record decisions** — every user instruction gets a D-nnn entry, no exceptions
- **Always commit per instruction** — same atomic commit discipline as pew-build
- **Never skip synthesis** — BRD/SPEC must be generated before CHECK
- **Never skip CHECK** — vibe phases get the full quality gate, same as build phases
- **Auto-classify, don't ask** — classify as change/fix automatically, let user override if wrong
- If the user says "that was a fix" or "that's a change", update DECISIONS.md accordingly
