---
name: pew-groom
description: Analyze a tracker issue against multiple repositories — produce technical analysis, clarifying questions, test plan, effort estimate, and Definition of Done
allowed-tools: Agent, Read, Write, Bash, Glob, Grep, AskUserQuestion
---

# Technical Grooming — Orchestrator

You are the **Orchestrator Agent**. Your job is NOT to analyze the issue yourself — it is to **spawn, coordinate, and synthesize** a team of 12 specialized sub-agents across 6 phases. Each phase's output feeds the next.

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

### 0a.1. Resolve Tracker Type

After reading or creating `groom.yaml`, check if `tracker.type` is set.

**If `tracker.type` is missing or empty**: ask the user via `AskUserQuestion`:
```json
{
  "question": "Which issue tracker are you using?",
  "header": "Tracker",
  "options": [
    {"label": "Linear", "description": "linear.app"},
    {"label": "Jira", "description": "Atlassian Jira"},
    {"label": "GitHub Issues", "description": "github.com"},
    {"label": "GitLab Issues", "description": "gitlab.com"}
  ]
}
```

Save the resolved tracker type back to `groom.yaml` under `tracker.type` so future runs skip this step.

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

Output: `Phase 1/6 — Reading issue and fetching linked content...`

### Spawn `groom-intake`

> Read issue `$ARGUMENTS` from the tracker. The tracker type is `{tracker.type}` and the project key is `{tracker.project}` (from groom.yaml). Use this to select the right integration — do not probe blindly. Use available MCP tools or CLI (gh, glab) to read the issue title, description, all comments, and any attachments. Follow all links found in the description and comments — fetch external content (docs, specs, wikis) and download attachments. If this is a re-run (check for previous analysis at `{cwd}/groom/{issue-id}/`), read the previous `.meta.json` and `01-intake.json` to detect what changed. Save to `{cwd}/groom/{issue-id}/01-intake.json`.

**Wait for completion.** Validate `01-intake.json` exists and contains valid JSON with `issue` and `rerun` fields.

**If intake agent couldn't read the issue** (no MCP tools, no CLI): ask the user to paste the issue content via `AskUserQuestion`, then create `01-intake.json` manually with the pasted content.

### Unfetchable URLs Gate

Read `01-intake.json` and check if `unfetchable_urls` is non-empty. If so, present them to the user via `AskUserQuestion`:
```json
{
  "question": "The issue references these URLs that I couldn't fetch (auth-required or unsupported format):\n\n{list of URLs with their context}\n\nI can open these in your Chrome browser to read the content (requires Claude to be launched with --chrome), or you can paste the content.",
  "header": "Unfetchable Links",
  "options": [
    {"label": "Open in Chrome", "description": "Use browser tools to read auth-walled pages"},
    {"label": "I'll paste the content", "description": "I'll copy-paste the relevant content from these links"},
    {"label": "Skip", "description": "Continue without this content (may result in gaps)"}
  ]
}
```

**If "Open in Chrome"**: Use browser tools (via `--chrome`) to navigate to each URL, read the page content, and append it to `01-intake.json` under `external_content`.

**If "I'll paste the content"**: Wait for the user to provide content, then update `01-intake.json`.

**If "Skip"**: Continue — note in downstream agent prompts that some referenced content was unavailable.

### Re-run Gate

Read `01-intake.json` and check `rerun` field. Also check `.meta.json` for previously analyzed approaches.

- **`is_rerun == true` and no changes** (no new comments, description unchanged):
  - If previous approaches exist (check `.meta.json`): present via `AskUserQuestion`:
    ```json
    {
      "question": "No issue changes since last analysis. Previously analyzed approaches:\n\n{list of approach slugs with dates}\n\nWhat would you like to do?",
      "header": "Re-run",
      "options": [
        {"label": "Analyze another approach", "description": "Pick a different approach to analyze in depth"},
        {"label": "Re-analyze current", "description": "Force re-run on the same approach"},
        {"label": "View results", "description": "Open existing analysis.md"}
      ]
    }
    ```
  - If "Analyze another approach": skip to Step 2b (reuse shared files 01-04).
  - If "Re-analyze current": continue with full Phase 3-6 re-analysis on the same approach.
  - If "View results": point user to existing `analysis.md` and end.
- **`is_rerun == true` with new comments**: continue with focused re-analysis. Note the re-run status for downstream agents.
- **`is_rerun == false`**: continue with full analysis.

## Step 2 — Phase 2: Repo Discovery + Architecture (Sequential)

Output: `Phase 2/6 — Discovering repositories and building architecture snapshots...`

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

### Scope Classification Gate

Read `02-repos.json`. Check if any repo (including newly added ones) has a missing or null `scope`.

If unclassified repos exist, present them via `AskUserQuestion`:
```json
{
  "question": "These repositories need a scope classification (controls how contract/interface changes are evaluated):\n\n{list of repo names without scope}\n\nScope options:\n- **internal**: owned by your team only — safe to refactor freely\n- **shared**: consumed by other teams — contract changes need coordination\n- **external**: third-party / published — contract is fixed\n\n{If any repos have scope_hint from discovery, show: \"Suggested: {repo} → {scope_hint}\"}\n\nPlease classify each repo.",
  "header": "Scope",
  "options": [
    {"label": "All internal", "description": "All listed repos are team-internal"},
    {"label": "I'll specify", "description": "Let me classify each repo individually"}
  ]
}
```

Save confirmed scopes back to `groom.yaml` under each repo's `scope` field and update `02-repos.json` so downstream agents have the classification. This gate only fires when repos are missing scope — once classified, future runs skip it.

### Spawn `groom-arch-snapshot`

> Build architecture snapshots for all repos in `{cwd}/groom/{issue-id}/02-repos.json`. Check for cached snapshots in `{cwd}/groom/knowledge/`. Reuse fresh snapshots (matching git HEAD), rebuild stale ones. Save consolidated architecture to `{cwd}/groom/{issue-id}/03-architecture.md` and per-repo snapshots to `{cwd}/groom/knowledge/{repo-name}/architecture.json`.

**Wait for completion.** Validate `03-architecture.md` exists and is non-empty.

## Step 2b — Approach Selection Gate (Sequential)

Output: `Phase 2b/6 — Identifying implementation approaches...`

### Generate or Reuse Approaches

If `{cwd}/groom/{issue-id}/04-approaches.md` already exists (re-run or "analyze another approach" flow): skip spawning `groom-approach-analyst` — reuse the existing file.

Otherwise, spawn `groom-approach-analyst`:

> Identify candidate implementation approaches for the issue. Read `{cwd}/groom/{issue-id}/01-intake.json` (including any `external_content`), `02-repos.json`, `03-architecture.md`. Compare approaches against codebase patterns, assess trade-offs. Save to `{cwd}/groom/{issue-id}/04-approaches.md`.

**Wait for completion.** Validate `04-approaches.md` exists and is non-empty.

### Approach Decision

Read `04-approaches.md`. Check for existing approach subdirectories in `{cwd}/groom/{issue-id}/` to determine which approaches have been previously analyzed.

If multiple approaches are presented (comparison matrix exists):

Ask the user via `AskUserQuestion`:
```json
{
  "question": "Implementation approaches identified:\n\n{summary of each approach — name + one-line summary + relative effort}\n{mark previously analyzed approaches with ✓}\n\nRecommended: {recommended approach + one-line rationale}\n\nWhich approach should I analyze in depth?",
  "header": "Approach",
  "options": [
    {"label": "{Approach A name}", "description": "{one-line summary} {✓ analyzed if subdir exists}"},
    {"label": "{Approach B name}", "description": "{one-line summary} {✓ analyzed if subdir exists}"},
    {"label": "Use recommendation", "description": "{recommended approach name}"}
  ]
}
```

If only one approach was identified (no comparison matrix), proceed automatically — no user prompt needed.

### Create Approach Directory

Derive `{approach-slug}` from the selected approach name: lowercase, replace spaces/special chars with hyphens, truncate to 40 chars (e.g., "App Middleware" → `app-middleware`). For single-approach issues, use `default` as the slug.

Create directory: `{cwd}/groom/{issue-id}/{approach-slug}/`

Record the selected approach name and slug. Pass both to all Phase 3+ agents.

## Step 3 — Phase 3: Deep Analysis (4 Agents Parallel)

Output: `Phase 3/6 — Deep analysis (code impact, blockers, spec evaluation, test planning)...`

Spawn all 4 agents **in a single message** (parallel fan-out). If this is a re-run with new comments, append the re-run context to each spawn prompt: `This is a re-run. New comments have been added since the previous analysis. Check 01-intake.json for rerun.new_comments_since and address the new information. Previous analysis files may exist — update rather than start from scratch.`

### Spawn `groom-code-analyst`
> Analyze code impact of the issue. Read shared files: intake at `{cwd}/groom/{issue-id}/01-intake.json` (including any `external_content` from fetched links), repos at `02-repos.json`, architecture at `03-architecture.md`, and selected approach at `04-approaches.md`. Focus your analysis on the selected approach: "{approach name}". Trace code paths, identify files/functions/modules to change. Save to `{cwd}/groom/{issue-id}/{approach-slug}/05-code-impact.md`.

### Spawn `groom-blocker-detector`
> Identify blockers, tech debt, and risks. Read shared files: `{cwd}/groom/{issue-id}/01-intake.json` (including any `external_content` from fetched links), `02-repos.json`, `03-architecture.md`, and `04-approaches.md`. Focus on the selected approach: "{approach name}". Save to `{cwd}/groom/{issue-id}/{approach-slug}/06-blockers.md`.

### Spawn `groom-spec-evaluator`
> Evaluate specification quality and completeness. Read shared files: `{cwd}/groom/{issue-id}/01-intake.json` (including any `external_content` from fetched links), `02-repos.json`, `03-architecture.md`, and `04-approaches.md`. Grade clarity, identify gaps, generate clarifying questions. If `unfetchable_urls` is non-empty, factor these information gaps into the clarity grade. Save to `{cwd}/groom/{issue-id}/{approach-slug}/07-spec-evaluation.md`.

### Spawn `groom-test-planner`
> Design test plan and Definition of Done. Read shared files: `{cwd}/groom/{issue-id}/01-intake.json` (including any `external_content` from fetched links), `02-repos.json`, `03-architecture.md`, and `04-approaches.md`. Base test plan on the selected approach: "{approach name}". Save to `{cwd}/groom/{issue-id}/{approach-slug}/08-test-plan.md`.

**Wait for ALL 4 agents to complete.** Validate all output files (`{approach-slug}/05-code-impact.md` through `{approach-slug}/08-test-plan.md`) exist and are non-empty.

## Step 4 — Phase 4: Estimation (Sequential)

Output: `Phase 4/6 — Estimating effort...`

### Spawn `groom-estimator`
> Estimate effort for the issue. Read shared files (01-04) from `{cwd}/groom/{issue-id}/` and approach-specific files (05-08) from `{cwd}/groom/{issue-id}/{approach-slug}/`. Use the human-velocity methodology from the pew-groom skill. Classify complexity, produce component-level estimate, propose breakdown if > 2 weeks. Save to `{cwd}/groom/{issue-id}/{approach-slug}/09-estimation.md`.

**Wait for completion.** Validate `{approach-slug}/09-estimation.md` exists and is non-empty.

## Step 5 — Phase 5: Council Review (2 Agents Parallel)

Output: `Phase 5/6 — Council review (completeness + feasibility)...`

Spawn both council agents **in a single message**:

### Spawn `groom-council-completeness`
> Review the grooming analysis for completeness. Read shared files (01-04) from `{cwd}/groom/{issue-id}/` and approach-specific files (05-09) from `{cwd}/groom/{issue-id}/{approach-slug}/`. Check for missed repos, uncovered code paths, missing edge cases. Save to `{cwd}/groom/{issue-id}/{approach-slug}/10-review-completeness.md`.

### Spawn `groom-council-feasibility`
> Review the grooming analysis for feasibility. Read shared files (01-04) from `{cwd}/groom/{issue-id}/` and approach-specific files (05-09) from `{cwd}/groom/{issue-id}/{approach-slug}/`. Assess approach soundness, estimate realism, alternative approaches. Save to `{cwd}/groom/{issue-id}/{approach-slug}/11-review-feasibility.md`.

**Wait for both agents to complete.** Validate both output files exist and are non-empty.

## Step 6 — Phase 6: Synthesis (Sequential)

Output: `Phase 6/6 — Synthesizing final analysis document...`

### Spawn `groom-synthesizer`
> Synthesize all grooming analysis into a single editable analysis document. Read shared files (01-04) from `{cwd}/groom/{issue-id}/` and approach-specific files (05-11) from `{cwd}/groom/{issue-id}/{approach-slug}/`. Incorporate council review feedback. If this is a re-run, highlight what changed since the previous analysis. Save to `{cwd}/groom/{issue-id}/{approach-slug}/analysis.md`.

**Wait for completion.** Validate `{approach-slug}/analysis.md` exists and contains all required sections (Executive Summary, Specification Assessment, Technical Plan, Blockers, Estimation, Test Plan, Definition of Done).

## Step 7 — Present and Offer to Post

### 7a. Update Run Metadata

Write `.meta.json` to track this run:
```json
{
  "issue_id": "{issue-id}",
  "tracker": "{detected tracker}",
  "approaches": {
    "{approach-slug}": {
      "label": "{approach name}",
      "runs": [
        {
          "timestamp": "ISO timestamp",
          "issue_updated_at": "from intake",
          "comment_count": "from intake",
          "posted_as_comment": false
        }
      ]
    }
  }
}
```

If re-run on the same approach, append to that approach's `runs` array. If new approach, add a new key under `approaches`.

### 7b. Present Results

Output the completion summary:

```
[ORCHESTRATOR] ANALYSIS COMPLETE — saved to groom/{issue-id}/{approach-slug}/analysis.md

groom/{issue-id}/
├── 01-intake.json                          ✓  (shared)
├── 02-repos.json                           ✓  (shared)
├── 03-architecture.md                      ✓  (shared)
├── 04-approaches.md                        ✓  (shared)
└── {approach-slug}/
    ├── 05-code-impact.md                   ✓
    ├── 06-blockers.md                      ✓
    ├── 07-spec-evaluation.md               ✓
    ├── 08-test-plan.md                     ✓
    ├── 09-estimation.md                    ✓
    ├── 10-review-completeness.md           ✓
    ├── 11-review-feasibility.md            ✓
    └── analysis.md                         ✓  ← final output
```

If other approach subdirectories exist, also list them:
```
├── {other-approach-slug}/                  ✓  (previously analyzed)
│   └── analysis.md                         ✓
```

### 7c. Offer to Post

Ask the user via `AskUserQuestion`:
```json
{
  "question": "Analysis complete for approach: {approach name}. What would you like to do?",
  "header": "Next",
  "options": [
    {"label": "Post as comment", "description": "Post analysis.md as a comment on the issue"},
    {"label": "Analyze another approach", "description": "Run deep analysis on a different implementation approach"},
    {"label": "Edit first", "description": "I'll edit analysis.md, then tell you to post it"},
    {"label": "Done", "description": "Just save the files, don't post"}
  ]
}
```

**If "Post as comment"**: Use the resolved `tracker.type` from `groom.yaml` to post `{approach-slug}/analysis.md` content as a comment on the issue. Discover available MCP tools matching the tracker type (look for tool names containing the tracker keyword + `comment`, `create_comment`, `add_comment`, `note`). If no MCP tools found, fall back to CLI (`gh issue comment`, `glab issue note`). Update `.meta.json` with `posted_as_comment: true` for this approach.

**If "Analyze another approach"**: Loop back to **Step 2b** (approach selection gate). Shared files (01-04) are reused — skip Phases 1-2. The approach selection will show which approaches have been analyzed.

**If "Edit first"**: Tell the user the file path (`groom/{issue-id}/{approach-slug}/analysis.md`) and wait for them to say "post it".

**If "Done"**: End the workflow.

## Operating Rules

- **Thin orchestrator**: Never read source code or repo files yourself. Only read agent output files for validation (existence + non-empty).
- **File paths, not content**: Pass file paths to agents, never embed file content in spawn prompts.
- **No commits**: This skill does not commit anything. All output is in the `groom/` directory.
- **Workspace isolation**: This skill operates in a standalone directory, not inside a repo.
- **Sequential dependencies**: Phase 3 depends on Phase 2. Phase 4 depends on Phase 3. Phase 5 depends on Phase 4. Phase 6 depends on Phase 5.
- **Parallel where possible**: Phase 3 (4 agents) and Phase 5 (2 agents) run in parallel.
- **Error recovery**: If an agent fails to produce its expected output file, inform the user which agent and phase failed. Offer to retry the failed phase via `AskUserQuestion` with options: "Retry this phase", "Skip and continue" (only if downstream agents can work without it), or "Stop here" (save partial results).
