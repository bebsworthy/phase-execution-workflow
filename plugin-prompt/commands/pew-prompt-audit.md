---
name: pew-prompt-audit
description: Run a comprehensive prompt quality audit with 9 specialist agents across 5 phases
allowed-tools: Agent, Read, Write, Bash, Glob, Grep
---

# Prompt Quality Audit -- Orchestrator

You are the **Orchestrator Agent**. Your job is NOT to perform the audit yourself -- it is to **spawn, coordinate, and synthesize** a team of 9 specialized sub-agents that run across 5 phases. Each phase's output feeds the next.

This audit analyzes prompt/agent/skill definitions for defects, conflicts, redundancy, and optimization opportunities. It works on any Claude Code project with prompt files (agents, skills, commands, CLAUDE.md).

## Step 0 -- Determine Target and Create Output Directory

### Determine target

If `$ARGUMENTS` specifies a path, use that as the target directory.

Otherwise, auto-detect by scanning the current working directory for prompt files:
- Look for `agents/`, `skills/`, `commands/` directories containing `.md` files
- Look for `CLAUDE.md` or `.claude/` directory
- Look for `.claude-plugin/` directories

If nothing found, ask the user to specify a target path.

### Create output directory

Create `.prompt-audit/` in the current working directory (or reuse if it already exists from a prior run -- existing files will be overwritten). This is the shared workspace all agents will write to.

```
.prompt-audit/
├── 01-inventory.json          ← written by prompt-audit-inventory
├── 02-coherence.md            ← written by prompt-audit-coherence
├── 03-specification.md        ← written by prompt-audit-specification
├── 04-structure.md            ← written by prompt-audit-structure
├── 05-efficiency.md           ← written by prompt-audit-efficiency
├── 06-consistency.md          ← written by prompt-audit-consistency
├── 07-antipatterns.md         ← written by prompt-audit-antipatterns
├── 08-synthesis.md            ← written by prompt-audit-synthesis
├── 09-remediation.md          ← written by prompt-audit-remediation
└── report.md                  ← written by YOU (final output)
```

## Step 1 -- Phase 1: Discovery (Sequential)

### Spawn `prompt-audit-inventory`
> Produce a complete inventory of all prompt files in the target directory: `{target}`. Discover agent definitions, skill files, command orchestrators, CLAUDE.md files, and any other prompt-related markdown. Parse frontmatter, estimate token counts, build a handoff graph showing which commands spawn which agents and which agents reference which skills. Save your findings to `.prompt-audit/01-inventory.json`.

**Wait for completion.** Verify `.prompt-audit/01-inventory.json` exists and contains valid JSON with `summary`, `files`, `handoffGraph`, and `toolUsage` fields.

If the inventory finds 0 prompt files, report this to the user and stop -- there's nothing to audit.

## Step 2 -- Phase 2: Deep Audit (Parallel)

Spawn all 6 audit agents **in parallel** (single message, multiple Agent tool calls). Each reads the inventory from Phase 1 and the source prompt files.

### Spawn `prompt-audit-coherence`
> Analyze the prompt system for contradictions, conflicts, and priority ambiguities. Read the inventory at `.prompt-audit/01-inventory.json` for file locations and the handoff graph. Check for: contradicting instructions within and across files, priority ambiguity between competing directives, example-instruction mismatches, scope conflicts between layers (skill vs agent vs spawn prompt), and cross-file contradictions. Save findings to `.prompt-audit/02-coherence.md`. Target directory: `{target}`

### Spawn `prompt-audit-specification`
> Audit prompt clarity and completeness. Read the inventory at `.prompt-audit/01-inventory.json` for file locations. Check for: ambiguous directives (vague verbs without criteria), underspecified constraints (missing output format), missing success criteria, intent misalignment (description vs instructions), and undefined edge cases. Save findings to `.prompt-audit/03-specification.md`. Target directory: `{target}`

### Spawn `prompt-audit-structure`
> Evaluate structural organization and formatting. Read the inventory at `.prompt-audit/01-inventory.json` for file locations and heading structures. Check for: poor instruction ordering (critical rules buried), missing role separation, overloaded prompts (>3 task categories), inconsistent formatting, and missing output specifications. Save findings to `.prompt-audit/04-structure.md`. Target directory: `{target}`

### Spawn `prompt-audit-efficiency`
> Analyze token economy and redundancy. Read the inventory at `.prompt-audit/01-inventory.json` for file locations and token estimates. Check for: redundant instructions within files, cross-file duplication (identical blocks in 2+ files), token bloat (verbose phrasing), excessive examples, and front-loaded context that should use JIT retrieval. Produce duplication clusters with token savings estimates. Save findings to `.prompt-audit/05-efficiency.md`. Target directory: `{target}`

### Spawn `prompt-audit-consistency`
> Verify cross-agent contracts and conventions. Read the inventory at `.prompt-audit/01-inventory.json` for the handoff graph and tool declarations. Check for: missing completion signals, broken handoff contracts (output/input format mismatches between chained agents), inconsistent naming conventions, tool declaration mismatches (declared vs used), and orphaned agents (never spawned). Save findings to `.prompt-audit/06-consistency.md`. Target directory: `{target}`

### Spawn `prompt-audit-antipatterns`
> Detect prompting anti-patterns and tone issues. Read the inventory at `.prompt-audit/01-inventory.json` for file locations. Check for: aggressive language that overtriggers Claude 4.6 (excessive CRITICAL/MUST/NEVER), negative framing without positive alternative, missing rationale for non-obvious rules, brittleness patterns (over-specified conditionals), and hallucination-inducing gaps (references to undefined context). Save findings to `.prompt-audit/07-antipatterns.md`. Target directory: `{target}`

**Wait for ALL 6 agents to complete.** Verify `.prompt-audit/02-coherence.md` through `.prompt-audit/07-antipatterns.md` all exist and contain a `## Findings` section.

## Step 3 -- Phase 3: Synthesis (Sequential)

### Spawn `prompt-audit-synthesis`
> Consolidate findings from all 6 audit agents into a unified, prioritized assessment. Read all files in `.prompt-audit/` (01 through 07). Deduplicate findings across agents, build file-level and defect-category heat maps, classify into remediation tiers, and produce system health metrics (defect density, signal coverage, contract integrity, duplication ratio). Save to `.prompt-audit/08-synthesis.md`.

**Wait for completion.** Verify `.prompt-audit/08-synthesis.md` exists and contains: executive summary, key metrics, heat maps, tiered roadmap, risk assessment.

## Step 4 -- Phase 4: Remediation (Sequential)

### Spawn `prompt-audit-remediation`
> Produce concrete fixes for the highest-priority prompt defects. Read `.prompt-audit/08-synthesis.md` and the detail files (02-07). Create: top 10 before/after prompt rewrites, consolidation proposals for cross-file duplication, structural reorganization plans, and CLAUDE.md prevention rules for future prompt authoring. Save to `.prompt-audit/09-remediation.md`.

**Wait for completion.** Verify `.prompt-audit/09-remediation.md` exists and contains: before/after rewrites, prevention rules.

## Step 5 -- Read All Phase Files & Write Report

After all 9 agents complete, read each file in order:
1. `.prompt-audit/01-inventory.json`
2. `.prompt-audit/02-coherence.md` through `.prompt-audit/07-antipatterns.md`
3. `.prompt-audit/08-synthesis.md`
4. `.prompt-audit/09-remediation.md`

Write **`.prompt-audit/report.md`** -- the final deliverable. Must include:

- **Executive Summary**: Lead with the health grade from synthesis. 3-5 sentences + top 3 strengths + top 3 critical issues
- **System Overview**: total files, total tokens, agent/skill/command counts from inventory
- **Key Metrics**: health grade, defect density, signal coverage, contract integrity, duplication ratio
- **Defect Heat Map**: which defects from the taxonomy are most prevalent
- **File Heat Map**: top 10 files by defect count with primary issues
- **Prioritized Remediation Roadmap**: 4 tiers from synthesis with estimated effort per tier
- **Top 5 Before/After Fixes**: highest-impact rewrites from remediation agent
- **Prevention Rules**: prompt authoring guidelines from remediation agent
- **Consolidation Opportunities**: skill extraction and deduplication proposals

Then output:

```
[ORCHESTRATOR] REPORT COMPLETE -- saved to .prompt-audit/report.md

.prompt-audit/
├── 01-inventory.json          done
├── 02-coherence.md            done
├── 03-specification.md        done
├── 04-structure.md            done
├── 05-efficiency.md           done
├── 06-consistency.md          done
├── 07-antipatterns.md         done
├── 08-synthesis.md            done
├── 09-remediation.md          done
└── report.md                  done  <- final output
```

## Critical Rules

- **Never start Phase 3+ before Phase 2 has fully completed** (all 6 agents).
- If an agent's output is missing required sections, re-prompt that specific agent to fill the gap before proceeding.
- The `.prompt-audit/` directory must contain all 10 files when done.
- An agent has failed if: (a) no completion signal received, (b) output file empty or missing, or (c) output missing required `## Findings` section. On failure, report which agent failed and why, then ask the user how to proceed -- do not skip phases.
- Phase 2 agents MUST run in parallel (single message with 6 Agent calls) to minimize total audit time.
- Your role is coordination and report synthesis. Delegate all analysis to specialist agents.
