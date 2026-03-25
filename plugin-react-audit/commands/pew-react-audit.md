---
name: pew-react-audit
description: Run a comprehensive code quality audit with 8 specialist agents across 4 phases
allowed-tools: Agent, Read, Write, Bash, Glob
---

# Code Quality Audit -- Orchestrator

You are the **Orchestrator Agent**. Your job is NOT to perform the audit yourself -- it is to **spawn, coordinate, and synthesize** a team of 8 specialized sub-agents that run across 4 phases. Each phase's output feeds the next.

This audit targets code quality issues in React/TypeScript applications: anti-patterns, security vulnerabilities, code duplication, complexity hotspots, dead code, and technical debt.

## Step 0 -- Initialize

### 0a. Locate or Create Config

Check if `react-audit.yaml` exists in the current working directory.

**If it exists**: read it to get `output_dir` and scope settings.

**If it doesn't exist**: create it with defaults:
```yaml
output_dir: ./audit/react
exclude:
  - node_modules
  - dist
  - build
  - coverage
  - "**/*.test.*"
  - "**/*.spec.*"
```

Read the resolved `output_dir` from the config. Use this path everywhere `{output_dir}` appears in agent prompts.

### 0b. Create Output Directory

Create the `{output_dir}/` directory. This is the shared workspace all agents will write to.

```
{output_dir}/
├── 01-inventory.json          ← written by react-audit-inventory
├── 02-patterns.md             ← written by react-audit-patterns
├── 03-security.md             ← written by react-audit-security
├── 04-duplication.md          ← written by react-audit-duplication
├── 05-complexity.md           ← written by react-audit-complexity
├── 06-debt.md                 ← written by react-audit-debt
├── 07-synthesis.md            ← written by react-audit-synthesis
├── 08-roadmap.md              ← written by react-audit-roadmap
└── report.md                  ← written by YOU (final output)
```

## Step 1 -- Phase 1: Discovery (Sequential)

### Spawn `react-audit-inventory`
> Produce a complete inventory of this React/TypeScript codebase. Detect the full stack (TypeScript config, React version/variant, state management, UI library, routing, build tool, linter). Create a structured inventory of all source files with line counts, export/import counts, and file types. Audit lint suppressions (eslint-disable, ts-ignore, as any). Run dependency security analysis. Save your findings to `{output_dir}/01-inventory.json`. $ARGUMENTS

**Wait for completion.** Verify `{output_dir}/01-inventory.json` exists and contains valid JSON with `stack`, `summary`, `inventory`, `complexityBaseline`, `suppressions`, and `dependencies` fields.

## Step 2 -- Phase 2: Deep Audit (Parallel)

Spawn all 5 audit agents **in parallel** (single message, multiple Agent tool calls). Each reads the inventory from Phase 1 and the project's source files.

### Spawn `react-audit-patterns`
> Detect TypeScript and React anti-patterns in this codebase. Read the inventory at `{output_dir}/01-inventory.json` for file locations and stack info. Check for: any-type proliferation, type assertion abuse, non-null assertions, missing strict mode, effect-derived state, missing effect cleanup, unstable references, component bloat, missing error boundaries, and library-specific misuse (TanStack Query, Tailwind). Save findings to `{output_dir}/02-patterns.md`. $ARGUMENTS

### Spawn `react-audit-security`
> Perform a full-codebase security sweep. Read the inventory at `{output_dir}/01-inventory.json`. Check for: XSS vectors (dangerouslySetInnerHTML, innerHTML), insecure token storage (localStorage), hardcoded secrets, missing auth guards, input validation gaps, CSRF/CORS issues, and dependency vulnerabilities. For each finding, describe the concrete attack scenario. Save findings to `{output_dir}/03-security.md`. $ARGUMENTS

### Spawn `react-audit-duplication`
> Find code duplication and consolidation opportunities. Read the inventory at `{output_dir}/01-inventory.json`. Check for: copy-paste code blocks in 3+ locations, redundant utility implementations, duplicate type definitions, repeated API/form/error patterns. Group findings into duplication clusters with consolidation proposals. Save findings to `{output_dir}/04-duplication.md`. $ARGUMENTS

### Spawn `react-audit-complexity`
> Find complexity hotspots, dead code, and simplification opportunities. Read the inventory at `{output_dir}/01-inventory.json`. Check for: god modules (>300 lines mixed concerns), dead code (unused exports, unreachable branches, commented code), over-engineering (single-implementation abstractions), cyclomatic complexity hotspots, hidden mutation, and mixed concerns. Produce a complexity heat map. Save findings to `{output_dir}/05-complexity.md`. $ARGUMENTS

### Spawn `react-audit-debt`
> Assess technical debt and modernization opportunities. Read the inventory at `{output_dir}/01-inventory.json`. Check for: outdated React patterns (class components, legacy lifecycle), outdated TypeScript patterns, state management debt, config/tooling debt, dependency health (outdated, deprecated, better alternatives), and migration opportunities. Produce a migration priority matrix. Save findings to `{output_dir}/06-debt.md`. $ARGUMENTS

**Wait for ALL 5 agents to complete.** Verify `{output_dir}/02-patterns.md` through `{output_dir}/06-debt.md` all exist and are non-empty.

## Step 3 -- Phase 3: Synthesis (Sequential)

### Spawn `react-audit-synthesis`
> Consolidate findings from all 5 audit agents into a unified, prioritized remediation roadmap. Read all files in `{output_dir}/` (01 through 06). Deduplicate findings across agents, build a file-level heat map, classify into remediation tiers, and produce key metrics (findings by severity, hotspot files, debt score). Save to `{output_dir}/07-synthesis.md`. $ARGUMENTS

**Wait for completion.** Verify `{output_dir}/07-synthesis.md` exists and contains: executive summary, metrics table, code smell heat map, file-level heat map, tiered roadmap, risk assessment.

## Step 4 -- Phase 4: Roadmap (Sequential)

### Spawn `react-audit-roadmap`
> Produce a concrete remediation plan from the audit synthesis. Read `{output_dir}/07-synthesis.md` and the detail files (02-06). Create: top 10 before/after fixes, refactoring strategies for major items, CLAUDE.md prevention rules, ESLint/tsconfig recommendations, and a phased execution plan. Save to `{output_dir}/08-roadmap.md`. $ARGUMENTS

**Wait for completion.** Verify `{output_dir}/08-roadmap.md` exists and contains: before/after fixes, refactoring strategies, prevention rules, config recommendations, phased plan.

## Step 5 -- Read All Phase Files & Write Report

After all 8 agents complete, read each file in order:
1. `{output_dir}/01-inventory.json`
2. `{output_dir}/02-patterns.md` through `{output_dir}/06-debt.md`
3. `{output_dir}/07-synthesis.md`
4. `{output_dir}/08-roadmap.md`

Write **`{output_dir}/report.md`** -- the final deliverable. Must include:

- **Executive Summary**: 3-5 sentences + top 3 strengths + top 3 critical issues
- **Key Metrics**: total findings by severity, findings by domain, top 10 hotspot files, debt score, duplication ratio, security risk score
- **Code Smell Heat Map**: which smells from the taxonomy are most prevalent
- **Security Summary**: all Critical/High security findings with attack scenarios
- **Prioritized Remediation Roadmap**: 4 tiers from synthesis, with estimated effort per tier
- **Top 5 Before/After Fixes**: highest-impact remediation examples from roadmap agent
- **Prevention Rules**: CLAUDE.md / .cursorrules rules from roadmap agent
- **Config Recommendations**: ESLint rules and tsconfig changes from roadmap agent
- **Modernization Roadmap**: migration priorities from debt agent

Then output:

```
[ORCHESTRATOR] REPORT COMPLETE ✓ -- saved to {output_dir}/report.md

{output_dir}/
├── 01-inventory.json          ✓
├── 02-patterns.md             ✓
├── 03-security.md             ✓
├── 04-duplication.md          ✓
├── 05-complexity.md           ✓
├── 06-debt.md                 ✓
├── 07-synthesis.md            ✓
├── 08-roadmap.md              ✓
└── report.md                  ✓  ← final output
```

## Step 6 -- Offer to Create Phases

After the report is complete, ask the user if they want to convert the findings into PEW phases:

> "The audit found issues across N tiers. Want me to create phases to fix them?"

If yes, follow the `audit-to-phases` command logic (see `commands/pew-audit-to-phases.md`):
1. Read the synthesis (`07-synthesis.md`) to extract remediation tiers
2. Check current phase state (`pw.sh list-phases --json`)
3. Propose phases with smart scheduling (start now vs. queue after current work)
4. Ask for confirmation via `AskUserQuestion`
5. Create phases via `pw.sh add-phase`

If the user declines, just output the report and finish. They can run `/pew-audit-to-phases` later.

If `pw.sh validate-config` shows no pew.yaml, skip this step -- tell the user to run `/pew-init` first if they want to create phases.

## Critical Rules

- **Never start Phase 3+ before Phase 2 has fully completed** (all 5 agents).
- If an agent's output is missing required sections, re-prompt that specific agent to fill the gap before proceeding.
- The `{output_dir}/` directory must contain all 9 files when done.
- If an agent fails, report the failure and ask the user how to proceed -- do not skip phases.
- Phase 2 agents MUST run in parallel (single message with 5 Agent calls) to minimize total audit time.
