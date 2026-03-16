---
name: pew-doc
description: Generate comprehensive application documentation from codebase analysis — product overview, architecture, internals, API contracts, and data models. Supports single repos, monorepos, and multi-repo folders.
user-invocable: true
---

# pew-doc — Comprehensive Application Documentation

Generate documentation deep enough for another LLM to use as its **sole planning and research reference** for feature work. The skill deploys specialist agents that systematically extract every layer of an application: product strategy, data models, API contracts, architecture, and code internals.

## When to Use

- Onboarding to an unfamiliar codebase
- Preparing context for LLM-driven feature planning
- Auditing what an application actually does vs. what docs claim
- Documenting a system that has no documentation

## Artifacts Generated

The pipeline produces a bootstrap manifest plus **5 main documentation artifacts** (validated by coverage and consistency checkers):

| File | Agent | Purpose |
|------|-------|---------|
| `00-discovery.json` | `doc-discovery` | Bootstrap: stack, layout, key files, graph summary |
| `01-PRODUCT.md` | `doc-product` | Product strategy: roles, flows, domain vocab, business rules |
| `02-DATA-MODELS.md` | `doc-data-models` | Schema, entities, DTOs, field-level lineage, ER diagrams |
| `03-API-CONTRACTS.md` | `doc-api-contracts` | Endpoints, payloads, events, auth per endpoint |
| `04-ARCHITECTURE.md` | `doc-architecture` | C4 diagrams, components, communication, infra, security |
| `05-INTERNALS.md` | `doc-internals` | Code structure, all operation flows, patterns, config |
| `SYSTEM-MAP.md` | `doc-system-map` | Cross-module/repo integration (multi-mode only) |
| `index.md` | orchestrator | Table of contents linking all artifacts |

## Modes of Operation

### Single Repo (default)
```
/pew-doc
```
Documents the current working directory. Output: `docs/`.

### Multi-Module (monorepo)
```
/pew-doc
```
When the discovery agent detects multiple modules (e.g., `apps/`, `packages/`, `services/`) and reports them in its `modules` array, the orchestrator switches to multi-module mode. Each module gets its own subdirectory under `docs/`, plus a `SYSTEM-MAP.md` for cross-module relationships.

### Multi-Repo (folder of repos)
```
/pew-doc --path /folder/of/repos
```
Scans the target folder, identifies each repo (by `.git` presence), documents each individually, then generates a `SYSTEM-MAP.md` for cross-repo integration.

### Subset / Incremental
```
/pew-doc product api-contracts
```
Regenerate only the specified artifacts. Discovery always re-runs. Valid names: `product`, `data-models`, `api-contracts`, `architecture`, `internals`.

### Custom Output Directory
```
/pew-doc --output my-docs/
```

## Agent Pipeline

### Per-Module Pipeline (Steps 1–4)
```
Step 1:  doc-discovery         (sequential — scans repo, outputs JSON manifest)
Step 2:  doc-product           (sequential — establishes domain vocab for all others)
Step 3:  doc-data-models  ‖  doc-api-contracts   (parallel)
Step 4:  doc-architecture  ‖  doc-internals       (parallel)
```

### Validation Pass (Step 5)
```
Step 5a: doc-coverage-checker × 5  (parallel — one per artifact vs graph)
Step 5b: doc-consistency-checker    (sequential — cross-references all artifacts)
```

If gaps or inconsistencies found, the orchestrator re-spawns the affected artifact agents with the report appended. Max 2 remediation rounds.

### Cross-Module Step (Step 6, multi-mode only)
```
Step 6:  doc-system-map  (reads all per-module docs, graph cross-service edges)
```

### Final Step (Step 7)
Orchestrator writes `index.md` linking all artifacts.

## Codebase-Memory MCP Integration

This skill leverages the `codebase-memory-mcp` server for graph-based code exploration:

- **Orchestrator** indexes repos via `index_repository` before spawning agents
- **Discovery agent** uses `get_graph_schema` + `search_graph` for structural overview
- **Artifact agents** use `search_graph`, `query_graph`, `trace_call_path`, `get_code_snippet` for precise symbol discovery and call chain tracing
- **Coverage checker** compares documented items against graph nodes to find gaps
- **System map** uses `query_graph` for `HTTP_CALLS` and `ASYNC_CALLS` edges, `search_graph` for cross-module symbols, and `trace_call_path` for end-to-end request traces across modules

If the MCP server is not available, agents fall back to Grep/Glob-based exploration (less precise but still functional).

## Agent Conventions

- Agents communicate via **file paths**, not inline content
- Each agent outputs a **completion signal**: `[agent-name] COMPLETE ✓`
- Agents **never commit** — the orchestrator handles git
- All diagrams use **Mermaid** syntax for portability
- Agents are **code-only** — no web research, everything extracted from the codebase
