---
name: pew-audit-to-phases
description: Convert audit report findings into actionable PEW phases. Works with react-audit, test-audit, and ux-audit reports.
allowed-tools: Agent, Read, Write, Bash, Glob
---

# Audit → Phases Converter

You convert audit report findings into PEW phases. This command works standalone (after an audit was run earlier) or is called automatically at the end of an audit.

**Note**: The audit plugins (pew-react-audit, pew-test-audit, pew-ux-audit) are separate plugins. They must be installed and run before this command can find their output. Audit output paths are configured in `pew.yaml` under `paths.audit_react`, `paths.audit_test`, and `paths.audit_ux`.

## Step 1 — Detect Audit Type and Report

Check for existing audit reports:

1. Run `bash ${CLAUDE_PLUGIN_ROOT}/scripts/pw.sh validate-config` — if no pew.yaml, tell the user to run `/pew-init` first.
2. Run `bash ${CLAUDE_PLUGIN_ROOT}/scripts/pw.sh dump-config` to get `config.paths.audit_test`, `config.paths.audit_ux`, and `config.paths.audit_react`.
3. Check which reports exist:
   - `{config.paths.audit_test}/08-synthesis.md` → test audit available
   - `{config.paths.audit_ux}/05-proposals.md` → UX audit available
   - `{config.paths.audit_react}/07-synthesis.md` → react audit available
4. If multiple exist, ask the user which audit to convert (or all).
5. If none exists, tell the user to run `/pew-test-audit`, `/pew-ux-audit`, or `/pew-react-audit` first.
6. If `$ARGUMENTS` specifies an audit type (`test`, `ux`, or `react`), use that directly.

## Step 2 — Read the Remediation Roadmap

### For test audits:
Read `{config.paths.audit_test}/08-synthesis.md` — extract the tiered remediation roadmap (Tiers 1-4) and per-file action list.

### For UX audits:
Read `{config.paths.audit_ux}/05-proposals.md` — extract the improvement proposals grouped by level (L1-L5) and phased roadmap.

## Step 3 — Determine Phase Numbering and Scheduling

Run `bash ${CLAUDE_PLUGIN_ROOT}/scripts/pw.sh next-phase-number` to get the starting phase number.

Then run `bash ${CLAUDE_PLUGIN_ROOT}/scripts/pw.sh list-phases --json` to understand scheduling context:

1. **No phases exist** (Scenario 2 / fresh project):
   - Default scheduling: "start now"

2. **Phases exist, none in progress**:
   - Default scheduling: "start now"

3. **Phases exist, one or more in progress**:
   - Default scheduling: "queue after current work"
   - NEVER insert a phase before an in-progress phase

## Step 4 — Propose Phases

Map remediation tiers to phases. Each phase gets:
- **Title**: descriptive, derived from the tier content
- **Brief**: summarizes what to fix, references finding IDs from the audit
- **Refs**: paths to the relevant audit detail files (not just the report — the specific agent outputs)
- **Size**: `medium` for Tier 1-2 (no market research needed), `small` for Tier 3+ (well-scoped)
- **Tags**: `test-quality` for test audit phases, `ux` for UX audit phases
- **depends_on**: audit fix phases depend on each other sequentially (Tier 1 before Tier 2), but do NOT depend on unrelated project phases

### Test audit → phases mapping:

| Tier | Suggested Phase | Size | Refs |
|------|----------------|------|------|
| Tier 1 (Immediate) | "Fix Critical Test Issues" — delete zero-value tests, fix flaky tests, add missing critical-path tests | medium | 08-synthesis.md, 02-tautological.md, 04-framework.md, 07-flaky.md |
| Tier 2 (Short Term) | "Improve Test Quality" — refactor tautological tests, reduce mocking, add negative/error-path tests | medium | 08-synthesis.md, 02-tautological.md, 03-mocking.md, 05-coverage.md |
| Tier 3 (Medium Term) | "Refactor Test Architecture" — address coupling, parameterize duplicates, improve naming, restructure directories | small | 08-synthesis.md, 06-maintainability.md, 10-architecture.md |

Tier 4 (Ongoing) is NOT a phase — it's conventions/CI config. Mention it as a recommendation but don't create a phase.

### UX audit → phases mapping:

Group by improvement level and impact:
| Priority | Suggested Phase | Size | Refs |
|----------|----------------|------|------|
| Quick Wins (L1-L2, high severity) | "Fix Critical UX Issues" — atomic changes and component fixes | small | 05-proposals.md, 04-audit.md |
| Strategic (L3-L4, high severity) | "Improve Core User Flows" — pattern introductions and flow redesigns | medium | 05-proposals.md, 04-audit.md, 01-user-goals.md |
| Structural (L5, any severity) | "UX Architecture Overhaul" — IA, navigation, mental model changes | large | 05-proposals.md, 04-audit.md, 01-user-goals.md, 03-patterns.md |

### Code audit → phases mapping:

| Tier | Suggested Phase | Size | Refs |
|------|----------------|------|------|
| Tier 1 (Immediate) | "Fix Critical Code Issues" -- security fixes, dead code removal, critical anti-patterns | medium | 07-synthesis.md, 03-security.md, 05-complexity.md |
| Tier 2 (Short Term) | "Consolidate & Clean Up" -- duplication consolidation, pattern fixes, missing error handling | medium | 07-synthesis.md, 02-patterns.md, 04-duplication.md |
| Tier 3 (Medium Term) | "Modernize & Simplify" -- architecture improvements, migrations, complexity reduction | medium | 07-synthesis.md, 06-debt.md, 08-roadmap.md |

Tier 4 (Ongoing) is NOT a phase -- it's conventions/CI config. Mention it as a recommendation but don't create a phase.

Skip phases with no findings. Combine small tiers if they have fewer than 3 items total.

## Step 5 — Present to User

Present proposed phases via `AskUserQuestion`:

**Question 1**: "Create these phases from the [test/UX] audit?"
- Options: list the proposed phases with titles and brief descriptions

**Question 2**: "When should these phases start?"
- Option A: **"Start now"** (Recommended if no phases in progress) — insert as next phases
- Option B: **"Queue after current work"** (Recommended if phases in progress) — append after last planned phase
- Option C: **"Just create, I'll prioritize"** — create with no specific ordering

## Step 6 — Create Phases

For each approved phase, run:

```
bash ${CLAUDE_PLUGIN_ROOT}/scripts/pw.sh add-phase \
  --number N \
  --title "Phase Title" \
  --brief "Phase brief with finding references" \
  --refs "path/to/audit-file1.md,path/to/audit-file2.md" \
  --tags "test-quality" \
  --size medium \
  --depends-on X
```

After creating all phases, run `pw.sh list-phases --json` to show the updated phase list.

Output:
```
[audit-to-phases] COMPLETE ✓ — created N phases from [test/UX] audit

Phase N:   Fix Critical Test Issues (medium, refs: 4 audit files)
Phase N+1: Improve Test Quality (medium, refs: 4 audit files)
Phase N+2: Refactor Test Architecture (small, refs: 3 audit files)

Run `/pew-build` and say `start phase N` to begin.
```

## Critical Rules

- NEVER insert phases before an in-progress phase.
- Audit fix phases depend on each other (Tier 1 → Tier 2 → Tier 3) but NOT on unrelated project phases.
- Skip tiers with no findings -- don't create empty phases.
- Tier 4 / L5+ ongoing items become conventions or CI config recommendations, not phases.
- For code audits, use tags `code-quality` on the generated phases.
- If pew.yaml doesn't exist, tell the user to run `/pew-init` first — don't create phases without a configured project.
- Refs must point to the detailed audit files, not just the report.
