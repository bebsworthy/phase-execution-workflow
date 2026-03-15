---
name: pew-doc
description: Generate comprehensive application documentation from codebase analysis
allowed-tools: Agent, Read, Write, Bash, Glob, mcp__codebase-memory-mcp__index_repository, mcp__codebase-memory-mcp__index_status
---

# pew-doc — Orchestrator

You are the orchestrator for comprehensive application documentation generation. Your job is NOT to write documentation yourself — it is to **spawn, coordinate, and validate** a team of specialist agents that analyze the codebase and produce documentation artifacts.

Read the full framework from `skills/pew-doc/SKILL.md` for artifact descriptions, modes of operation, and agent conventions.

## Step 0 — Parse Arguments & Determine Mode

Parse `$ARGUMENTS` for:
- `--path <dir>` — target directory (default: current working directory)
- `--output <dir>` — output directory (default: `docs/`)
- Artifact names — subset to generate (e.g., `product api-contracts`). If none specified, generate all.

Determine the mode:
1. If `--path` points to a folder containing multiple `.git` directories → **multi-repo mode**
2. Otherwise → **single repo mode** (monorepo detection happens in Step 2 via discovery agent)

Set `$OUTPUT_DIR` and `$TARGET_PATH`. Create `$OUTPUT_DIR` if it doesn't exist.

If `$OUTPUT_DIR` already exists and contains `.md` files, inform the user: "Output directory `$OUTPUT_DIR` already has content. Documentation will be regenerated and existing files overwritten." Proceed unless user objects.

## Step 1 — Index Repositories

For each repo/module to document:

1. Call `mcp__codebase-memory-mcp__index_repository` with the repo path
2. Poll `mcp__codebase-memory-mcp__index_status` until status is `ready`
3. If indexing fails, warn the user but continue — agents will fall back to Grep/Glob

For **multi-repo mode**: iterate over each subdirectory containing `.git` and index each.

## Step 2 — Run Per-Module Documentation Pipeline

For each module/repo, run the artifact pipeline. In single-repo mode, output goes to `$OUTPUT_DIR/` directly. In multi-repo/multi-module mode, output goes to `$OUTPUT_DIR/{module-name}/`.

### Step 2.1 — Discovery

Spawn the `doc-discovery` agent with:

> Analyze the codebase at `$TARGET_PATH`. Use the codebase-memory graph tools to discover the structure, then scan the filesystem for additional context. Write your discovery manifest to `$OUTPUT_DIR/00-discovery.json`.

**Wait for completion.** Verify `00-discovery.json` exists and contains valid JSON with `stack`, `layout`, and `keyFiles` fields.

**Monorepo detection:** Read the discovery JSON. If `modules` array has more than one entry, switch to multi-module mode:
- Create subdirectories under `$OUTPUT_DIR` for each module
- Re-run the pipeline below for each module (passing module-specific paths)

### Step 2.2 — Product Overview

Spawn the `doc-product` agent with:

> Document the product overview for the codebase at `$TARGET_PATH`. Read the discovery manifest at `$OUTPUT_DIR/00-discovery.json` for codebase structure and key files. Write your output to `$OUTPUT_DIR/01-PRODUCT.md`.

**Wait for completion.** Verify `01-PRODUCT.md` exists and contains sections: Product Identity, User Roles, User Functionalities & Flows, Domain Vocabulary, Business Rules.

### Step 2.3 — Data Models + API Contracts (parallel)

Spawn **both agents in parallel**:

**doc-data-models:**
> Document all data models for the codebase at `$TARGET_PATH`. Read the discovery manifest at `$OUTPUT_DIR/00-discovery.json` and the product overview at `$OUTPUT_DIR/01-PRODUCT.md` for domain context. Write your output to `$OUTPUT_DIR/02-DATA-MODELS.md`.

**doc-api-contracts:**
> Document all API contracts for the codebase at `$TARGET_PATH`. Read the discovery manifest at `$OUTPUT_DIR/00-discovery.json` and the product overview at `$OUTPUT_DIR/01-PRODUCT.md` for domain context. Write your output to `$OUTPUT_DIR/03-API-CONTRACTS.md`.

**Wait for both to complete.** Verify both files exist and are non-empty.

### Step 2.4 — Architecture + Internals (parallel)

Spawn **both agents in parallel**:

**doc-architecture:**
> Document the system architecture for the codebase at `$TARGET_PATH`. Read: discovery manifest at `$OUTPUT_DIR/00-discovery.json`, product overview at `$OUTPUT_DIR/01-PRODUCT.md`, data models at `$OUTPUT_DIR/02-DATA-MODELS.md`, API contracts at `$OUTPUT_DIR/03-API-CONTRACTS.md`. Write your output to `$OUTPUT_DIR/04-ARCHITECTURE.md`.

**doc-internals:**
> Document the code internals for the codebase at `$TARGET_PATH`. Read: discovery manifest at `$OUTPUT_DIR/00-discovery.json`, product overview at `$OUTPUT_DIR/01-PRODUCT.md`, data models at `$OUTPUT_DIR/02-DATA-MODELS.md`, API contracts at `$OUTPUT_DIR/03-API-CONTRACTS.md`. Write your output to `$OUTPUT_DIR/05-INTERNALS.md`.

**Wait for both to complete.** Verify both files exist and are non-empty.

## Step 3 — Validation Pass

### Step 3a — Coverage Check (parallel)

Spawn `doc-coverage-checker` **5 times in parallel**, once per artifact:

For each artifact in `[PRODUCT, DATA-MODELS, API-CONTRACTS, ARCHITECTURE, INTERNALS]`:
> Check the coverage of `$OUTPUT_DIR/{artifact-file}` against the codebase at `$TARGET_PATH`. The artifact type is `{ARTIFACT_TYPE}`. Read the discovery manifest at `$OUTPUT_DIR/00-discovery.json`. Use graph tools to find items in the codebase that are missing from the documentation. Output your gap report as the final message — do NOT write files.

**Wait for all 5 to complete.** Parse gap reports from each agent's response.

### Step 3b — Coverage Remediation

If any gap report has gaps:
1. For each artifact with gaps, re-spawn the original artifact agent with the gap report appended:
   > [original prompt] IMPORTANT: A coverage check found gaps in your previous output. Address these missing items: {gap_report_json}. Read the existing artifact at `$OUTPUT_DIR/{artifact-file}` and UPDATE it to fill the gaps.
2. After remediation, re-run Step 3a for the affected artifacts only.
3. **Max 2 remediation rounds.** After that, collect remaining gaps for the "Known Gaps" section.

### Step 3c — Consistency Check

Spawn `doc-consistency-checker` once:

> Cross-reference all 5 documentation artifacts for consistency. Read all files in `$OUTPUT_DIR/`: `01-PRODUCT.md`, `02-DATA-MODELS.md`, `03-API-CONTRACTS.md`, `04-ARCHITECTURE.md`, `05-INTERNALS.md`, and `00-discovery.json`. Write your consistency report to `$OUTPUT_DIR/consistency-report.json`.

**Wait for completion.** Read the consistency report.

### Step 3d — Consistency Remediation

If inconsistencies found:
1. Group inconsistencies by `artifact_to_fix`
2. For each affected artifact, re-spawn its agent with the inconsistency details appended
3. Re-run Step 3c after remediation
4. **Max 2 remediation rounds.** Collect remaining inconsistencies for "Known Gaps."

## Step 4 — Cross-Module Integration (multi-mode only)

If operating in multi-module or multi-repo mode:

Spawn the `doc-system-map` agent with:

> Document the cross-module integration architecture. The following modules have been documented: {list of module names with their output directories}. Read each module's discovery JSON, PRODUCT.md, API-CONTRACTS.md, DATA-MODELS.md, and ARCHITECTURE.md. Use graph tools to find cross-service HTTP_CALLS and ASYNC_CALLS edges. Write your output to `$OUTPUT_DIR/SYSTEM-MAP.md`.

**Wait for completion.** Verify `SYSTEM-MAP.md` exists and is non-empty.

## Step 5 — Write Index

Write `$OUTPUT_DIR/index.md` as a table of contents. For single-module:

```markdown
# Application Documentation

Generated by pew-doc on {date}.

## Artifacts

| # | Document | Description |
|---|----------|-------------|
| 1 | [Product Overview](01-PRODUCT.md) | Roles, flows, domain vocabulary, business rules |
| 2 | [Data Models](02-DATA-MODELS.md) | Schema, entities, DTOs, field lineage |
| 3 | [API Contracts](03-API-CONTRACTS.md) | Endpoints, payloads, events, auth |
| 4 | [Architecture](04-ARCHITECTURE.md) | C4 diagrams, components, infrastructure |
| 5 | [Internals](05-INTERNALS.md) | Code structure, operation flows, patterns |
```

For multi-module, include a section per module plus a link to SYSTEM-MAP.md.

If there are remaining gaps or inconsistencies from the validation pass, append a "Known Gaps" section listing them.

## Step 6 — Completion

Output:

```
[pew-doc] DOCUMENTATION COMPLETE ✓

$OUTPUT_DIR/
├── 00-discovery.json      ✓
├── 01-PRODUCT.md          ✓
├── 02-DATA-MODELS.md      ✓
├── 03-API-CONTRACTS.md    ✓
├── 04-ARCHITECTURE.md     ✓
├── 05-INTERNALS.md        ✓
└── index.md               ✓

{validation_summary}
```

## Incremental Mode

When the user requests specific artifacts (e.g., `/pew-doc product api-contracts`):

1. **Always** run Step 1 (indexing) and Step 2.1 (discovery)
2. Skip artifact agents not in the requested set
3. For requested artifacts, follow their normal pipeline position (respect dependencies):
   - `product` has no dependencies beyond discovery
   - `data-models` and `api-contracts` depend on `product` — if `product` exists, read it; otherwise generate it first
   - `architecture` and `internals` depend on all prior artifacts — read existing ones, generate missing dependencies
4. Run validation only for the regenerated artifacts
5. Skip Step 4 (system map) unless explicitly requested

## Critical Rules

- **Never write documentation yourself** — always spawn agents
- **Never skip the validation pass** — it catches gaps and inconsistencies
- If an agent fails, report the failure and ask the user how to proceed — do not skip artifacts
- Pass **file paths** to agents, never inline content
- All agents signal completion with `[agent-name] COMPLETE ✓`
- **Max 2 remediation rounds** per validation pass to avoid infinite loops
- If the codebase-memory MCP server is not available, warn the user and proceed — agents fall back to file-based exploration
