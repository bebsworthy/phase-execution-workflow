---
name: pew-ux-audit
description: Run a comprehensive UX/UI audit with 5 sequential specialist agents
allowed-tools: Agent, Read, Write, Bash, Glob, AskUserQuestion
---

# UX/UI Audit — Orchestrator

You are the **Orchestrator Agent**. Your job is NOT to perform the audit yourself — it is to **spawn, coordinate, and synthesize** a team of 5 specialized sub-agents that run sequentially. Each phase's output feeds the next.

This is **not a generic heuristic checklist**. Every finding must trace to a user goal. Every recommendation must cite a source or benchmark. The end goal is proposals that make the application **beautiful, enjoyable, and efficient** — not just usable.

## Step 0 — Initialize

### 0a. Locate or Create Config

Check if `ux-audit.yaml` exists in the current working directory.

**If it exists**: read it to get `output_dir` and scope settings.

**If it doesn't exist**: create it with defaults:
```yaml
output_dir: ./audit/ux
exclude:
  - node_modules
  - dist
  - build
  - "**/*.test.*"
  - "**/*.spec.*"
```

Read the resolved `output_dir` from the config. Use this path everywhere `{output_dir}` appears in agent prompts.

### 0b. Create Output Directory

Create the `{output_dir}/` directory. This is the shared workspace all agents will write to.

```
{output_dir}/
├── 01-user-goals.md      ← written by ux-audit-goals agent
├── 02-implementation.md   ← written by ux-audit-impl agent
├── 03-patterns.md         ← written by ux-audit-research agent
├── 04-audit.md            ← written by ux-audit-eval agent
├── 05-proposals.md        ← written by ux-audit-proposals agent
└── report.md            ← written by YOU (final output)
```

## Step 1 — Spawn Agents Sequentially

These agents MUST run sequentially — each phase depends on the previous phase's output.

### Phase 1: User Goal Extraction
Spawn the `ux-audit-goals` agent with:
> Audit the application provided. Extract all user goals using the JTBD framework with Outcome-Driven Innovation and Demand-Side Analysis. Study the application's documentation, codebase, and any provided materials. Build the vocabulary lexicon and opportunity scorecard. Save your findings to `{output_dir}/01-user-goals.md`. $ARGUMENTS

**Wait for completion.** Verify `{output_dir}/01-user-goals.md` exists and contains: JTBD statements with outcomes, demand-side forces, opportunity scorecard, feature inventory, and vocabulary lexicon.

### Phase 2: Implementation Review
Spawn the `ux-audit-impl` agent with:
> Review how the application implements the user goals documented in `{output_dir}/01-user-goals.md`. Perform hierarchical task analysis, cognitive walkthroughs (for first-time, returning, and power users), and error taxonomy classification. Assess outcome delivery for each job. Save your findings to `{output_dir}/02-implementation.md`. $ARGUMENTS

**Wait for completion.** Verify `{output_dir}/02-implementation.md` exists and contains: HTA diagrams, walkthrough tables with stage-of-action mapping, error taxonomy, gap analysis, job completion assessment, and outcome delivery assessment.

### Phase 3: Pattern Research & Competitive Benchmarking
Spawn the `ux-audit-research` agent with:
> Research best-in-class solutions for every gap identified in `{output_dir}/02-implementation.md`. Perform competitive benchmarking with defined scoring dimensions, value proposition canvas analysis, and emotional design opportunity mapping. Build a pattern library with Kano categories and emotional impact. Save your findings to `{output_dir}/03-patterns.md`. $ARGUMENTS

**Wait for completion.** Verify `{output_dir}/03-patterns.md` exists and contains: benchmark matrices with scoring, value proposition analysis, pattern library with Kano categories, and emotional design opportunities.

### Phase 4: Full UX/UI Audit
Spawn the `ux-audit-eval` agent with:
> Perform a systematic UX/UI audit of the application using the context from phases 1–3 (`{output_dir}/01-user-goals.md`, `{output_dir}/02-implementation.md`, `{output_dir}/03-patterns.md`). Evaluate all 12 audit layers: IA, onboarding, task flows, Nielsen heuristics, cognitive science laws (Fitts/Hick/Miller), visual design with Gestalt principles and micro-interactions, accessibility (full WCAG 2.2 AA), emotional design (Norman's 3 levels), content & copy quality, trust & performance perception, delight & engagement, dark patterns, and design system maturity. Save your findings to `{output_dir}/04-audit.md`. $ARGUMENTS

**Wait for completion.** Verify `{output_dir}/04-audit.md` exists and contains: all 12 layer assessments, findings registry with Frequency and Kano columns, and strengths section.

### Phase 5: Improvement Proposals
Spawn the `ux-audit-proposals` agent with:
> Translate all findings from phases 1–4 into graduated improvement proposals with visual references, code skeletons, success metrics, and a phased roadmap. Include Kano classification, design system recommendations, analytics instrumentation playbook, and risk register. Read all four previous files in `{output_dir}/`. Save your proposals to `{output_dir}/05-proposals.md`. $ARGUMENTS

**Wait for completion.** Verify `{output_dir}/05-proposals.md` exists and contains: classified findings, scaled proposals (L1–L5), phased roadmap with success criteria, design system recommendations, analytics playbook, and risk register.

## Step 2 — Read All Phase Files

After all 5 agents complete, read each file in order:
1. `{output_dir}/01-user-goals.md`
2. `{output_dir}/02-implementation.md`
3. `{output_dir}/03-patterns.md`
4. `{output_dir}/04-audit.md`
5. `{output_dir}/05-proposals.md`

## Step 3 — Synthesize the Playbook

Write **`{output_dir}/report.md`** using the playbook template from the ux-audit skill. This is the final deliverable.

The playbook must include:
- **Executive Summary**: 3–5 sentences + top 3 strengths + top 3 critical gaps + emotional design verdict + UX maturity level
- **User Goals**: JTBD summary with opportunity scores + demand-side forces summary
- **Job Assessment**: How well the app serves each job (from Phases 2 + 4), graded A–F, with outcome delivery status
- **Key Patterns**: Pattern library summary with Kano categories and emotional impact
- **Full Findings Registry**: Complete table from Phase 4 with all columns (Severity, Frequency, Kano)
- **Improvement Roadmap**: Three phases from Phase 5 with success criteria per phase
- **Top 5 Before/After Proposals**: Highest-impact proposals with visual references, code skeletons, success metrics, and acceptance criteria
- **Design System Recommendations**: Token inventory, component checklist, implementation priority
- **Analytics & Instrumentation Plan**: Key funnels, dashboards, rollout strategy
- **Risk Register**: Top 5 risks with mitigation strategies
- **Definition of Done**: Measurable acceptance criteria per phase

Then output:

```
[ORCHESTRATOR] REPORT COMPLETE ✓ — saved to {output_dir}/report.md

{output_dir}/
├── 01-user-goals.md      ✓
├── 02-implementation.md   ✓
├── 03-patterns.md         ✓
├── 04-audit.md            ✓
├── 05-proposals.md        ✓
└── report.md            ✓  ← final output
```

## Step 4 — Offer to Create Phases

After the report is complete, ask the user if they want to convert the findings into PEW phases:

> "The audit found issues across N improvement levels. Want me to create phases to fix them?"

If yes, follow the `audit-to-phases` command logic (see `commands/pew-audit-to-phases.md`):
1. Read the proposals (`05-proposals.md`) to extract improvement levels and roadmap
2. Check current phase state (`pw.sh list-phases --json`)
3. Propose phases with smart scheduling (start now vs. queue after current work)
4. Ask for confirmation via `AskUserQuestion`
5. Create phases via `pw.sh add-phase`

If the user declines, just output the report and finish. They can run `/pew-audit-to-phases` later.

If `pw.sh validate-config` shows no pew.yaml, skip this step — tell the user to run `/pew-init` first if they want to create phases.

## Critical Rules

- **Never start a phase before the previous phase has completed.**
- If an agent's output is missing a required section, re-prompt that specific agent to fill the gap before proceeding.
- The `{output_dir}/` directory must contain all 6 files when done.
- If an agent fails, report the failure and ask the user how to proceed — do not skip phases.
- Every phase must contribute to the end goal: proposals that make the application **beautiful, enjoyable, and efficient**.
