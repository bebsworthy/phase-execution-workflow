---
name: pew-audit-to-phases
description: Convert audit report findings into actionable PEW phases. Works with react-audit, test-audit, and ux-audit reports.
allowed-tools: Agent, Read, Write, Bash, Glob
---

# Audit → Phases Converter

You convert audit report findings into PEW phases. This command works standalone (after an audit was run earlier) or is called automatically at the end of an audit.

**Note**: The audit plugins (pew-react-audit, pew-test-audit, pew-ux-audit) are separate plugins. They must be installed and run before this command can find their output. Output paths come from `pew.yaml` (`paths.audit_test`, `paths.audit_ux`, `paths.audit_react`).

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

### For code audits:
Read `{config.paths.audit_react}/07-synthesis.md` — extract the tiered remediation roadmap (Tiers 1-4) and file-level heat map. Also read `{config.paths.audit_react}/08-roadmap.md` for concrete before/after fixes and refactoring strategies.

## Step 3 — Determine Phase Numbering and Scheduling

Run `bash ${CLAUDE_PLUGIN_ROOT}/scripts/pw.sh next-phase-number` to get the starting phase number.

Then run `bash ${CLAUDE_PLUGIN_ROOT}/scripts/pw.sh list-phases --status started --json` to understand scheduling context:

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
- **Brief file**: a structured `AUDIT-BRIEF.md` generated per phase (see Step 4b below)
- **Refs**: paths to the relevant audit detail files (not just the report — the specific agent outputs)
- **Size**: always `audit` — skips IDEAS and RESEARCH, tells BRD/SPEC agents to derive from audit findings
- **Tags**: `test-quality` for test audit phases, `ux` for UX audit phases, `code-quality` for code audit phases
- **depends_on**: audit fix phases depend on each other sequentially (Tier 1 before Tier 2), but do NOT depend on unrelated project phases

### Test audit → phases mapping:

| Tier | Suggested Phase | Refs |
|------|----------------|------|
| Tier 1 (Immediate) | "Fix Critical Test Issues" — delete zero-value tests, fix flaky tests, add missing critical-path tests | 08-synthesis.md, 09-remediation.md, 01-inventory.json, 02-tautological.md, 04-framework.md, 07-flaky.md |
| Tier 2 (Short Term) | "Improve Test Quality" — refactor tautological tests, reduce mocking, add negative/error-path tests | 08-synthesis.md, 09-remediation.md, 02-tautological.md, 03-mocking.md, 05-coverage.md |
| Tier 3 (Medium Term) | "Refactor Test Architecture" — address coupling, parameterize duplicates, improve naming, restructure directories | 08-synthesis.md, 09-remediation.md, 06-maintainability.md, 10-architecture.md |

Tier 4 (Ongoing) is NOT a phase — it's conventions/CI config. Mention it as a recommendation but don't create a phase.

### UX audit → phases mapping:

Group by improvement level and impact:
| Priority | Suggested Phase | Refs |
|----------|----------------|------|
| Quick Wins (L1-L2, high severity) | "Fix Critical UX Issues" — atomic changes and component fixes | 05-proposals.md, 04-audit.md |
| Strategic (L3-L4, high severity) | "Improve Core User Flows" — pattern introductions and flow redesigns | 05-proposals.md, 04-audit.md, 02-implementation.md, 01-user-goals.md |
| Structural (L5, any severity) | "UX Architecture Overhaul" — IA, navigation, mental model changes | 05-proposals.md, 04-audit.md, 02-implementation.md, 01-user-goals.md, 03-patterns.md |

### Code audit → phases mapping:

| Tier | Suggested Phase | Refs |
|------|----------------|------|
| Tier 1 (Immediate) | "Fix Critical Code Issues" -- security fixes, dead code removal, critical anti-patterns | 07-synthesis.md, 08-roadmap.md, 01-inventory.json, 03-security.md, 05-complexity.md |
| Tier 2 (Short Term) | "Consolidate & Clean Up" -- duplication consolidation, pattern fixes, missing error handling | 07-synthesis.md, 08-roadmap.md, 02-patterns.md, 04-duplication.md |
| Tier 3 (Medium Term) | "Modernize & Simplify" -- architecture improvements, migrations, complexity reduction | 07-synthesis.md, 08-roadmap.md, 06-debt.md |

Tier 4 (Ongoing) is NOT a phase -- it's conventions/CI config. Mention it as a recommendation but don't create a phase.

All audit-derived phases use `--size audit`. Skip phases with no findings. Combine small tiers if they have fewer than 3 items total.

### Step 4b — Generate AUDIT-BRIEF.md per phase

For each proposed phase, write a structured brief file at `{config.paths.phases}/<phase-kebab-name>/AUDIT-BRIEF.md`. This file gives BRD and SPEC agents pre-digested audit content so they can derive artifacts without re-researching.

Read the relevant audit detail files (from the phase's refs) and extract into this structure:

```markdown
# Audit Brief — <Phase Title>

## Source
- Audit type: [test|ux|code]
- Tier/Level: [Tier N | L1-L2 | etc.]
- Synthesis file: <path>

## Findings in Scope

Extract findings from the audit detail files for this tier.

### For test audits:
Group by anti-pattern category (from the 14-item taxonomy: #1 Tautological, #2 Mock Echo, etc.) and list affected files:

### #N <Anti-pattern Name>
- **Severity**: [critical|high|medium|low]
- **Files**: file paths + test names from the audit detail files
- **Verdict**: [DELETE|REWRITE|REFACTOR] (from 08-synthesis.md per-file action list)
- **Issue**: what's wrong (from audit)
- **Before/After**: code examples from 09-remediation.md

### For UX audits:
Use finding IDs (F-nnn) from the 04-audit.md findings registry:

### F-nnn — <Finding Title>
- **Severity**: [0-4] / **Frequency**: [1-4]
- **Audit Layer**: [IA|Onboarding|Task Flows|Nielsen|etc.]
- **Kano**: [Basic|Performance|Delighter]
- **Improvement Level**: [L1-L5]
- **Proposal**: summary from 05-proposals.md

### For code audits:
Group by category (security, patterns, duplication, complexity, debt) and list affected files:

### <Category> — <Finding Title>
- **Severity**: [critical|high|medium|low]
- **Files**: file paths + line ranges from the audit detail files
- **Issue**: what's wrong (from audit)
- **Before/After**: code examples from 08-roadmap.md

## Acceptance Criteria

Derive from the audit findings:
- [ ] <concrete, verifiable criterion per finding or finding group>

## Out of Scope
- Findings from other tiers (handled in separate phases)
- Tier 4 / ongoing items (conventions, not phase work)
```

Create the phase directory first: `mkdir -p {config.paths.phases}/<phase-kebab-name>/`

Then write the AUDIT-BRIEF.md file using the Write tool.

## Step 5 — Present to User

Present proposed phases via `AskUserQuestion`:

**Question 1**: "Create these phases from the [test/UX/code] audit?"
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
  --brief-file "{config.paths.phases}/<phase-kebab-name>/AUDIT-BRIEF.md" \
  --refs "path/to/audit-file1.md,path/to/audit-file2.md" \
  --tags "test-quality" \
  --size audit \
  --depends-on X
```

After creating all phases, run `pw.sh list-phases` to show the updated phase list.

Output:
```
[audit-to-phases] COMPLETE ✓ — created N phases from [test/UX/code] audit

Phase N:   Fix Critical Test Issues (audit, refs: 4 audit files, brief: AUDIT-BRIEF.md)
Phase N+1: Improve Test Quality (audit, refs: 4 audit files, brief: AUDIT-BRIEF.md)
Phase N+2: Refactor Test Architecture (audit, refs: 3 audit files, brief: AUDIT-BRIEF.md)

Run `/pew-build` and say `start phase N` to begin.
```

## Critical Rules

- NEVER insert phases before an in-progress phase.
- Audit fix phases depend on each other (Tier 1 → Tier 2 → Tier 3) but NOT on unrelated project phases.
- Skip tiers with no findings -- don't create empty phases.
- Tier 4 / ongoing items become conventions or CI config recommendations, not phases.
- For code audits, use tags `code-quality` on the generated phases.
- If pew.yaml doesn't exist, tell the user to run `/pew-init` first — don't create phases without a configured project.
- Refs must point to the detailed audit files, not just the report.
