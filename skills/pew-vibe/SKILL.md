---
name: pew-vibe
description: >
  Build-first phase mode. Implement changes following user instructions while continuously
  recording decisions. Synthesizes BRD/SPEC post-hoc before running the full CHECK/CLOSE
  quality gate. Use when adapting to user testing feedback or iterating on a live feature.
user-invocable: true
---

# Vibe Mode — Build First, Document Post-Hoc

## Purpose

Vibe mode inverts the standard pew-build flow. Instead of IDEAS → BUILD (plan everything, then build), you build first following user instructions, record decisions as they happen, then run the full CHECK/CLOSE quality gate at the end.

Use vibe mode when:
- User testing reveals adjustments needed ("move this button", "add a date column")
- Quick iterations on a live feature that doesn't need market research or formal planning
- The plan met the enemy and didn't survive — adapt while keeping traceability

## How It Differs from pew-build

| Aspect | pew-build | pew-vibe |
| --- | --- | --- |
| Flow | IDEAS → BRD → RESEARCH → SPEC → PLAN → BUILD → CHECK | BUILD (with decision log) → Synthesize BRD/SPEC → CHECK |
| Planning | Upfront, before code | Post-hoc, from code + decisions |
| Artifacts | Written before implementation | Generated retroactively by synthesizer |
| Quality gate | Same CHECK/CLOSE | Same CHECK/CLOSE |
| Phase size | large/medium/small | vibe (skips ideas, brd, research, spec, plan) |

## How It Differs from Pure Vibe Coding

A vibe phase still benefits from:
- **Decision recording** — every change is logged with rationale
- **Post-hoc BRD/SPEC** — synthesized before CHECK so alignment can be verified
- **Full council review** — same experts, same standards
- **Alignment checking** — code verified against the synthesized requirements
- **Phase closing** — verification evidence, test closure, optional retro

---

## Decision Recording Protocol

Every time the user gives an instruction during a vibe phase, the orchestrator:

### 1. Implement the Change

Delegate to `build-frontend-developer` or `build-backend-developer` (same as pew-build BUILD step), or implement directly for small changes.

### 2. Record the Decision

Append to `{phase-dir}/DECISIONS.md`:

```markdown
### D-003 — Add publication date to story list

- **Type**: change
- **Instruction**: "we need to see the date here"
- **What changed**: Added `publishedAt` column to StoryList component
- **Files**: src/components/StoryList.tsx
- **Commit**: abc1234
```

### 3. Auto-Classify

Classify each decision as:
- **change** — new or altered requirement (user wants something different from what exists)
- **fix** — correcting broken behavior (something doesn't work as expected)

**Heuristics for auto-classification:**
- User says "doesn't work", "broken", "bug", "wrong" → **fix**
- User says "add", "move", "change", "show", "hide", "new" → **change**
- Modifying existing test assertions to match new behavior → **change** (the behavior changed)
- Modifying code to match existing test expectations → **fix** (the code was wrong)

The user can override the classification. When unsure, default to **change**.

### 4. Commit

Atomic commit per instruction (same discipline as pew-build BUILD step). The commit message should reference the decision ID:

```
D-003: Add publication date to story list
```

---

## Decision Log Format

The decision log uses D-nnn IDs (sequential). Template at `templates/DECISIONS.template.md`.

The summary table at the top tracks totals:

```markdown
| Total | Changes | Fixes |
| ----- | ------- | ----- |
| 7     | 5       | 2     |
```

Update the summary after each decision.

---

## Synthesis Protocol

When the user says "close vibe phase N":

1. **Mark build complete**: `pw.sh set-step-status --phase N --step build --status complete`
2. **Spawn build-vibe-synthesizer** with:
   - DECISIONS.md path
   - `pw.sh phase-diff --phase N` output
   - Phase context (number, title, tags)
   - Conventions file path
   - Template paths (BRD.template.md, SPEC.template.md)
3. **Validate**: BRD.md and SPEC.md exist and are non-empty
4. **Un-skip steps**: `pw.sh set-step-status --phase N --step brd --status complete` and `--step spec --status complete`
5. **Commit** the synthesized artifacts
6. **Run CHECK/CLOSE** — same as pew-build Step 7 (council, verify, alignment, fix cycles, close)

---

## CHECK/CLOSE

Reuses the exact same CHECK step from pew-build. The council reviews code against the post-hoc BRD/SPEC. The alignment checker verifies that every FC-nnn has implementation and every T-nnn has a test.

Any gaps found by the alignment checker indicate:
- A decision that wasn't recorded (the synthesizer missed it)
- Code that exists without a corresponding requirement (over-implementation)
- Tests that are missing for documented changes

These are handled through the normal fix cycle (fix/descope/defer).
