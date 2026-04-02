---
name: pew-style
description: Analyze a web application's design language against a target reference and produce a tiered migration plan with component hierarchy proposals
allowed-tools: Agent, Read, Write, Bash, Glob, Grep, AskUserQuestion
---

# Design Language Migration — Orchestrator

You are the **Orchestrator Agent**. Your job is NOT to analyze the design yourself — it is to **spawn, coordinate, and synthesize** a team of 7 specialized sub-agents across 5 phases. Each phase's output feeds the next.

This skill operates in the application's workspace directory. It compares the app's current design language against a target reference (screenshots, exported source code, or both) and produces a comprehensive migration plan.

## Invocation

The user invokes this skill with optional arguments:

```
/pew-style
/pew-style --reference ./mockups/
/pew-style --screenshots ./designs/ --source ./stitch-export/
```

Arguments are passed to agents via `$ARGUMENTS`.

## Step 0 — Initialize Workspace

### 0a. Locate or Create Config

Check if `style.yaml` exists in the current working directory.

**If it exists**: read it to get app root, reference paths, and settings.

**If it doesn't exist**: ask the user via `AskUserQuestion`:
```json
{
  "question": "No style.yaml found. I need to know where your target reference design is located. Do you have screenshots, exported source code (from Figma AI, Google Stitch, v0, etc.), or both?",
  "header": "Reference type",
  "options": [
    {"label": "Screenshots only", "description": "I have PNG/JPG images of the target design"},
    {"label": "Source code only", "description": "I have exported React/HTML code from a design tool"},
    {"label": "Both", "description": "I have screenshots AND exported source code"},
    {"label": "I'll create style.yaml", "description": "Let me write the config file myself"}
  ]
}
```

If the user provides reference type, ask a follow-up for the path(s), then create `style.yaml` with:
- `app.root`: current working directory
- `reference.screenshots` and/or `reference.source`: user-provided paths
- `settings.project_name`: derived from directory name or ask user

### 0b. Validate Reference Inputs

Check that the configured reference paths exist and contain files:
- If `reference.screenshots` is set: verify the directory exists and contains image files (PNG, JPG, JPEG, WEBP)
- If `reference.source` is set: verify the directory exists and contains code files (HTML, JSX, TSX, CSS, SCSS)
- If neither is configured or both are empty: ask user to provide reference materials before proceeding

### 0c. Create Output Directory

Read `settings.project_name` from `style.yaml`. Create directory: `style/{project_name}/`

### 0d. Detect Re-run

Check if `style/{project_name}/.meta.json` exists.

**If it exists**: present via `AskUserQuestion`:
```json
{
  "question": "Previous analysis found for this project (ran {date}). What would you like to do?",
  "header": "Re-run",
  "options": [
    {"label": "Full re-run", "description": "Run complete analysis from scratch (overwrites previous)"},
    {"label": "View results", "description": "Open existing report.md"},
    {"label": "New reference", "description": "Keep app analysis, re-run with a new reference design"}
  ]
}
```

- **"Full re-run"**: Continue with Step 1.
- **"View results"**: Point user to `style/{project_name}/report.md` and end.
- **"New reference"**: Ask for new reference path, update `style.yaml`, then skip to Phase 2 (reuse `01-intake.json` and `02-app-profile.md` if they exist, re-run `style-reference-profiler` only, then continue from Phase 3).

**If it does not exist**: continue with Step 1.

---

## Step 1 — Phase 1: Intake (Sequential)

Output: `Phase 1/5 — Classifying inputs and detecting scope...`

### Spawn `style-intake`

> Classify the inputs for a design migration analysis. Read `style.yaml` from the current directory. Detect the app's framework and styling approach by scanning the codebase. Classify the reference input type (screenshots, source, or mixed). Inventory component directories, style directories, theme files, and any existing design system artifacts. If reference is source code, detect its framework too. If reference is screenshots, list all image files with brief descriptions. Save to `style/{project_name}/01-intake.json`. $ARGUMENTS

**Wait for completion.** Validate `01-intake.json` exists and contains valid JSON with `app`, `reference`, and `analysis_scope` fields.

### Input Validation Gate

Read `01-intake.json`. If `analysis_scope.reference_files_count` is 0:
```json
{
  "question": "No reference files were found at the configured path(s). Please provide the location of your reference design.",
  "header": "No reference",
  "options": [
    {"label": "Update path", "description": "I'll provide the correct path to my reference files"},
    {"label": "Cancel", "description": "Stop the analysis"}
  ]
}
```

If the user provides a new path, update `style.yaml` and re-spawn `style-intake`.

Report scope: `Found {N} components, {M} style files in the app. Reference: {K} files ({type}).`

---

## Step 2 — Phase 2: Dual Profiling (Parallel)

Output: `Phase 2/5 — Profiling app and reference design languages...`

### Spawn BOTH agents in a single message (parallel):

**Agent 1 — `style-app-profiler`:**
> Create a comprehensive design profile of the application. Read intake at `style/{project_name}/01-intake.json` for detected paths and framework. Extract all design tokens (colors, typography, spacing, borders, shadows, animations, breakpoints). Build a complete component inventory with semantic roles. Assess the component hierarchy quality. Analyze the visual language. Identify ad-hoc styling patterns. Use the Design Profile Template from the pew-style skill. Save to `style/{project_name}/02-app-profile.md`.

**Agent 2 — `style-reference-profiler`:**
> Create a design profile of the target reference. Read intake at `style/{project_name}/01-intake.json` for input type and paths. If the reference is screenshots: visually analyze each image, infer color palette, typography, spacing, component types, and visual language — mark all values `[inferred]`. If the reference is source code: parse and extract exact tokens, components, and structure — mark values `[extracted]`. Use the same Design Profile Template from the pew-style skill so outputs are directly comparable to the app profile. Save to `style/{project_name}/03-reference-profile.md`.

**Wait for BOTH to complete.** Validate `02-app-profile.md` and `03-reference-profile.md` exist and are non-empty.

---

## Step 3 — Phase 3: Correspondence & Delta (Sequential)

Output: `Phase 3/5 — Mapping components and computing token deltas...`

### Spawn `style-matcher`

> Map app components to their reference counterparts by semantic role (not content — the apps may be in different domains). Read `style/{project_name}/01-intake.json`, `style/{project_name}/02-app-profile.md`, and `style/{project_name}/03-reference-profile.md`. Build a correspondence table mapping each app component to its reference equivalent with confidence levels. Compute a design token delta for every token category (current → target → change type). Flag unmapped components (app-only and reference-only). Detect and flag structural conflicts as `[CONFLICT: type]`. Save to `style/{project_name}/04-correspondence.md`.

**Wait for completion.** Validate `04-correspondence.md` exists and contains: correspondence table, token delta tables, unmapped components section, and conflicts section.

### Conflict Resolution Gate

Read `04-correspondence.md`. Search for `[CONFLICT:` markers.

**If conflicts exist**, present them via `AskUserQuestion`:
```json
{
  "question": "The reference design conflicts with your app's structure in {N} places:\n\n{list each conflict: type + description}\n\nHow should these be handled?",
  "header": "Conflicts",
  "options": [
    {"label": "Keep app patterns", "description": "Preserve the app's current structural patterns, adopt reference styling only"},
    {"label": "Adopt reference patterns", "description": "Migrate to the reference's structural patterns"},
    {"label": "Let me decide each", "description": "I'll resolve each conflict individually"}
  ]
}
```

- **"Keep app patterns"**: Append `## Resolved Conflicts\nAll conflicts resolved: KEEP APP PATTERN` to `04-correspondence.md`.
- **"Adopt reference patterns"**: Append `## Resolved Conflicts\nAll conflicts resolved: ADOPT REFERENCE PATTERN` to `04-correspondence.md`.
- **"Let me decide each"**: For each conflict, ask via `AskUserQuestion` with "Keep app" / "Adopt reference" options. Append each resolution to the file.

**If no conflicts**: continue.

---

## Step 4 — Phase 4: Hierarchy & Migration Planning (Parallel)

Output: `Phase 4/5 — Designing component hierarchy and migration roadmap...`

### Spawn BOTH agents in a single message (parallel):

**Agent 1 — `style-hierarchy`:**
> Propose a restructured semantic component hierarchy for the application. Read `style/{project_name}/01-intake.json`, `style/{project_name}/02-app-profile.md`, `style/{project_name}/03-reference-profile.md`, and `style/{project_name}/04-correspondence.md`. Grade the current hierarchy quality (A-F). Identify anti-patterns (div soup, inline overrides, duplicated style logic). Propose semantic names for all components using the standard role categories from the pew-style skill. Map each current component to its proposed semantic name and target visual style. Propose a design system definition (token file structure, component API contracts, naming conventions). Save to `style/{project_name}/05-hierarchy.md`.

**Agent 2 — `style-migration-planner`:**
> Produce a phased migration roadmap for transforming the app's design toward the reference. Read `style/{project_name}/01-intake.json`, `style/{project_name}/02-app-profile.md`, `style/{project_name}/03-reference-profile.md`, and `style/{project_name}/04-correspondence.md`. Organize the migration into 5 tiers: (1) Tokens, (2) Atomic Components, (3) Composite Components, (4) Page Layouts, (5) Polish. For each tier: list affected files, effort level (L1-L5), risk assessment, and rollback strategy. Identify find-and-replace-safe changes vs manual refactoring. Flag high-risk items (components used in 10+ places). Save to `style/{project_name}/06-migration-plan.md`.

**Wait for BOTH to complete.** Validate `05-hierarchy.md` and `06-migration-plan.md` exist and are non-empty.

---

## Step 5 — Phase 5: Synthesis (Sequential)

Output: `Phase 5/5 — Synthesizing final report...`

### Spawn `style-synthesizer`

> Merge all design analysis into a final report. Read all files in `style/{project_name}/`: `01-intake.json`, `02-app-profile.md`, `03-reference-profile.md`, `04-correspondence.md`, `05-hierarchy.md`, and `06-migration-plan.md`. Produce a report with 7 sections: (1) Executive Summary, (2) App Design Profile (condensed), (3) Reference Design Profile (condensed), (4) Component Correspondence Map, (5) Design Token Delta, (6) Component Hierarchy Proposal, (7) Migration Roadmap. Cross-reference hierarchy proposals with migration tiers. Ensure every token change maps to a specific migration tier. Save to `style/{project_name}/report.md`.

**Wait for completion.** Validate `report.md` exists and contains all 7 required sections.

---

## Step 6 — Present Results

### Write Run Metadata

Write `style/{project_name}/.meta.json`:
```json
{
  "last_run": "{ISO timestamp}",
  "project_name": "{project_name}",
  "app_framework": "{from 01-intake.json}",
  "reference_type": "{screenshots/source/mixed}",
  "components_analyzed": "{count}",
  "conflicts_found": "{count}",
  "conflicts_resolved": true
}
```

### Present Completion Summary

Output a file tree of all generated files:
```
Analysis complete!

style/{project_name}/
  01-intake.json
  02-app-profile.md
  03-reference-profile.md
  04-correspondence.md
  05-hierarchy.md
  06-migration-plan.md
  report.md
```

### Offer Next Steps

```json
{
  "question": "Design migration analysis complete. What would you like to do next?",
  "header": "Next steps",
  "options": [
    {"label": "Create pew-build phase", "description": "Create a single PEW delivery phase for the migration (tiers become ordered tasks)"},
    {"label": "Export design tokens", "description": "Extract proposed tokens as CSS custom properties / Tailwind config / JSON"},
    {"label": "Analyze another reference", "description": "Run again with a different target design"},
    {"label": "Done", "description": "End the analysis"}
  ]
}
```

- **"Create pew-build phase"**: Read `06-migration-plan.md`. Create a **single** PEW phase (size: `large`, tags: `frontend, style-migration`) with `style/{project_name}/report.md` as `brief_file` and the analysis files as `refs`. The 5 migration tiers become ordered task groups within the phase's PLAN — not separate phases. If the user explicitly asks to split into multiple phases, create one phase per tier instead.
- **"Export design tokens"**: Read `04-correspondence.md` token delta and `05-hierarchy.md` token definitions. Write token files in the format matching the app's styling approach (CSS custom properties for CSS vars, `tailwind.config` additions for Tailwind, theme object for styled-components).
- **"Analyze another reference"**: Ask for new reference path, update `style.yaml`, loop back to Step 0.
- **"Done"**: End.

---

## Error Handling

- If an agent fails to produce its output file: inform the user and offer to retry the agent or skip the phase.
- If an agent produces an incomplete file (missing required sections): re-prompt that specific agent with the gaps identified.
- Never skip Phase 3 (correspondence) — it is the critical bridging step that all downstream phases depend on.
- If the user cancels at any gate, save `.meta.json` with partial run status so the next run can resume.
