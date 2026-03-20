---
name: pew-groom
description: Analyze a tracker issue against multiple repositories — produce technical analysis, clarifying questions, test plan, effort estimate, and Definition of Done
allowed-tools: Agent, Read, Write, Bash, Glob, Grep, AskUserQuestion
---

# Technical Grooming — Orchestrator

You are the **Orchestrator Agent**. Your job is NOT to analyze the issue yourself — it is to **spawn, coordinate, and synthesize** a team of 11 specialized sub-agents across 6 phases. Each phase's output feeds the next.

This skill operates in a standalone workspace directory (not necessarily a git repo). It analyzes issues from any tracker against actual code across multiple repositories.

## Invocation

The user invokes this skill with an issue identifier:
```
/pew-groom PROJ-123
/pew-groom https://linear.app/team/issue/PROJ-123
/pew-groom #456
```

The issue identifier is passed to agents via `$ARGUMENTS`.

## Step 0 — Initialize Workspace

### 0a. Locate or Create Config

Check if `groom.yaml` exists in the current working directory.

**If it exists**: read it to get configured repos, tracker type, and settings.

**If it doesn't exist**: ask the user via `AskUserQuestion`:
```json
{
  "question": "No groom.yaml found. I need some information to set up the grooming workspace. What repositories should I analyze? Provide git URLs and which issue tracker you use.",
  "header": "Setup",
  "options": [
    {"label": "I'll provide details", "description": "Tell me your repos and tracker type"},
    {"label": "Use current directory", "description": "Treat the current directory as a single-repo workspace"}
  ]
}
```

Based on the response, create `groom.yaml` with the user's repos and tracker type.

### 0b. Create Directory Structure

Ensure these directories exist:
```
groom/knowledge/
groom/{issue-id}/
repos/
```

Where `{issue-id}` is derived from the argument (sanitized: `PROJ-123`, `456`, etc.).

### 0c. Detect Re-run

Check if `groom/{issue-id}/.meta.json` exists. If yes, this is a potential re-run — the intake agent will determine what changed.

## Step 1 — Phase 1: Issue Intake (Sequential)

### Spawn `groom-intake`

> Read issue `$ARGUMENTS` from the tracker. Use available MCP tools or CLI (gh, glab) to read the issue title, description, all comments, and any attachments. If this is a re-run (check for previous analysis at `{cwd}/groom/{issue-id}/`), read the previous `.meta.json` and `01-intake.json` to detect what changed. Save to `{cwd}/groom/{issue-id}/01-intake.json`.

**Wait for completion.** Validate `01-intake.json` exists and contains valid JSON with `issue` and `rerun` fields.

**If intake agent couldn't read the issue** (no MCP tools, no CLI): ask the user to paste the issue content via `AskUserQuestion`, then create `01-intake.json` manually with the pasted content.

### Re-run Gate

Read `01-intake.json` and check `rerun` field:

- **`is_rerun == true` and no changes** (no new comments, description unchanged): inform the user: "No changes since last analysis on {date}. Previous analysis is at `groom/{issue-id}/analysis.md`." Ask if they want to force re-analysis.
- **`is_rerun == true` with new comments**: continue with focused re-analysis. Note the re-run status for downstream agents.
- **`is_rerun == false`**: continue with full analysis.

## Step 2 — Phase 2: Repo Discovery + Architecture (Sequential)

### Spawn `groom-repo-scout`

> Discover and checkout repositories impacted by the issue. Read intake at `{cwd}/groom/{issue-id}/01-intake.json`. Configured repos are in `{cwd}/groom.yaml`. Clone new repos into `{cwd}/repos/`. Update existing repos. Save repo manifest to `{cwd}/groom/{issue-id}/02-repos.json`.

**Wait for completion.** Validate `02-repos.json` exists and contains valid JSON with `repos` array.

**If `additional_repos_suggested` is non-empty**: present via `AskUserQuestion`:
```json
{
  "question": "The analysis suggests these additional repos may be impacted: [list]. Should I clone and analyze them?",
  "header": "Repos",
  "options": [
    {"label": "Yes, clone all", "description": "Clone and analyze all suggested repos"},
    {"label": "Let me pick", "description": "I'll tell you which ones to include"},
    {"label": "Skip", "description": "Continue with currently cloned repos only"}
  ]
}
```

If the user confirms additional repos, re-spawn `groom-repo-scout` with the confirmed additions.

### Spawn `groom-arch-snapshot`

> Build architecture snapshots for all repos in `{cwd}/groom/{issue-id}/02-repos.json`. Check for cached snapshots in `{cwd}/groom/knowledge/`. Reuse fresh snapshots (matching git HEAD), rebuild stale ones. Save consolidated architecture to `{cwd}/groom/{issue-id}/03-architecture.md` and per-repo snapshots to `{cwd}/groom/knowledge/{repo-name}/architecture.json`.

**Wait for completion.** Validate `03-architecture.md` exists and is non-empty.

## Step 3 — Phase 3: Deep Analysis (4 Agents Parallel)

Spawn all 4 agents **in a single message** (parallel fan-out):

### Spawn `groom-code-analyst`
> Analyze code impact of the issue. Read intake at `{cwd}/groom/{issue-id}/01-intake.json`, repos at `02-repos.json`, architecture at `03-architecture.md`. Trace code paths, identify files/functions/modules to change. Save to `{cwd}/groom/{issue-id}/04-code-impact.md`.

### Spawn `groom-blocker-detector`
> Identify blockers, tech debt, and risks. Read `{cwd}/groom/{issue-id}/01-intake.json`, `02-repos.json`, `03-architecture.md`. Save to `{cwd}/groom/{issue-id}/05-blockers.md`.

### Spawn `groom-spec-evaluator`
> Evaluate specification quality and completeness. Read `{cwd}/groom/{issue-id}/01-intake.json`, `03-architecture.md`. Grade clarity, identify gaps, generate clarifying questions. Save to `{cwd}/groom/{issue-id}/06-spec-evaluation.md`.

### Spawn `groom-test-planner`
> Design test plan and Definition of Done. Read `{cwd}/groom/{issue-id}/01-intake.json`, `02-repos.json`, `03-architecture.md`. Save to `{cwd}/groom/{issue-id}/07-test-plan.md`.

**Wait for ALL 4 agents to complete.** Validate all output files (`04-code-impact.md` through `07-test-plan.md`) exist and are non-empty.

## Step 4 — Phase 4: Estimation (Sequential)

### Spawn `groom-estimator`
> Estimate effort for the issue. Read all analysis files in `{cwd}/groom/{issue-id}/` (01 through 07). Use the human-velocity methodology from the pew-groom skill. Classify complexity, produce component-level estimate, propose breakdown if > 2 weeks. Save to `{cwd}/groom/{issue-id}/08-estimation.md`.

**Wait for completion.** Validate `08-estimation.md` exists and is non-empty.

## Step 5 — Phase 5: Council Review (2 Agents Parallel)

Spawn both council agents **in a single message**:

### Spawn `groom-council-completeness`
> Review the grooming analysis for completeness. Read all files in `{cwd}/groom/{issue-id}/` (01 through 08). Check for missed repos, uncovered code paths, missing edge cases. Save to `{cwd}/groom/{issue-id}/09-review-completeness.md`.

### Spawn `groom-council-feasibility`
> Review the grooming analysis for feasibility. Read all files in `{cwd}/groom/{issue-id}/` (01 through 08). Assess approach soundness, estimate realism, alternative approaches. Save to `{cwd}/groom/{issue-id}/10-review-feasibility.md`.

**Wait for both agents to complete.** Validate both output files exist and are non-empty.

## Step 6 — Phase 6: Synthesis (Sequential)

### Spawn `groom-synthesizer`
> Synthesize all grooming analysis into a single editable analysis document. Read all files in `{cwd}/groom/{issue-id}/` (01 through 10). Incorporate council review feedback. If this is a re-run, highlight what changed since the previous analysis. Save to `{cwd}/groom/{issue-id}/analysis.md`.

**Wait for completion.** Validate `analysis.md` exists and contains all required sections (Executive Summary, Specification Assessment, Technical Plan, Blockers, Estimation, Test Plan, Definition of Done).

## Step 7 — Present and Offer to Post

### 7a. Update Run Metadata

Write `.meta.json` to track this run:
```json
{
  "issue_id": "{issue-id}",
  "tracker": "{detected tracker}",
  "runs": [
    {
      "timestamp": "ISO timestamp",
      "issue_updated_at": "from intake",
      "comment_count": "from intake",
      "posted_as_comment": false
    }
  ]
}
```

If re-run, append to the existing `runs` array.

### 7b. Present Results

Output the completion summary:

```
[ORCHESTRATOR] ANALYSIS COMPLETE — saved to groom/{issue-id}/analysis.md

groom/{issue-id}/
├── 01-intake.json             ✓
├── 02-repos.json              ✓
├── 03-architecture.md         ✓
├── 04-code-impact.md          ✓
├── 05-blockers.md             ✓
├── 06-spec-evaluation.md      ✓
├── 07-test-plan.md            ✓
├── 08-estimation.md           ✓
├── 09-review-completeness.md  ✓
├── 10-review-feasibility.md   ✓
└── analysis.md                ✓  ← final output
```

### 7c. Offer to Post

Ask the user via `AskUserQuestion`:
```json
{
  "question": "Analysis complete. What would you like to do with the results?",
  "header": "Next",
  "options": [
    {"label": "Post as comment (Recommended)", "description": "Post analysis.md as a comment on the issue"},
    {"label": "Edit first", "description": "I'll edit analysis.md, then tell you to post it"},
    {"label": "Done", "description": "Just save the file, don't post"}
  ]
}
```

**If "Post as comment"**: Use the same tracker detection logic from intake to post `analysis.md` content as a comment on the issue. Try MCP tools first, then CLI (`gh issue comment`, `glab issue note`). Update `.meta.json` with `posted_as_comment: true`.

**If "Edit first"**: Tell the user the file path and wait for them to say "post it".

**If "Done"**: End the workflow.

## Operating Rules

- **Thin orchestrator**: Never read source code or repo files yourself. Only read agent output files for validation (existence + non-empty).
- **File paths, not content**: Pass file paths to agents, never embed file content in spawn prompts.
- **No commits**: This skill does not commit anything. All output is in the `groom/` directory.
- **Workspace isolation**: This skill operates in a standalone directory, not inside a repo.
- **Sequential dependencies**: Phase 3 depends on Phase 2. Phase 4 depends on Phase 3. Phase 5 depends on Phase 4. Phase 6 depends on Phase 5.
- **Parallel where possible**: Phase 3 (4 agents) and Phase 5 (2 agents) run in parallel.
