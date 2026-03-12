# PEW — Phase Execution Workflow

A Claude Code plugin for precision phased delivery. Runs a 7-step loop per feature phase:

**IDEAS → BRD → RESEARCH → SPEC → PLAN → BUILD → CHECK/CLOSE**

Each step produces traceable artifacts with quality gates, council review, and optional browser-based product validation.

## Install

### From marketplace (recommended)

```bash
# Add the marketplace (one-time)
/plugin marketplace add bebsworthy/phase-execution-workflow

# Install the plugin
/plugin install pew@pew-marketplace
```

### Local development

Clone the repo and point Claude Code at it:

```bash
claude --plugin-dir /path/to/phase-execution-workflow
```

## Setup

1. Run `/pew:init` — it explores your repo, detects your tech stack and verification commands, and writes `pew.yaml` after your confirmation
2. Run `/pew:run` and say `start phase 1`

You can also run `/pew:init` again later to update the config if your project structure changes.

### Manual setup (alternative)

1. Copy `pew.yaml.example` to your repo root as `pew.yaml`
2. Edit the config with your project's paths, stack, commands, and competitors

### Minimal config

```yaml
project:
  name: 'My App'
  description: 'A web application'

paths:
  tracker: 'phases/phase-tracker.yaml'

commands:
  verify: 'npm run lint && npm run typecheck && npm test'
```

Everything else has sensible defaults. See `pew.yaml.example` for the full config reference.

## What's included

| Component              | Description                                                                                                                                                                                                                     |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Skill** (`/pew:init`) | Project setup — explores repo, detects stack/commands, writes `pew.yaml`                                                                                                                                                     |
| **Skill** (`/pew:run`) | Main workflow engine — phase lifecycle, auto mode, command dispatch                                                                                                                                                             |
| **14 agents**          | Feature benchmarker, UX researcher/designer, alignment checker, council experts (security, architecture, testing, test-quality, frontend, backend), tech developers (frontend, backend), product reviewer |
| **Review profiles**    | Composable tech best practices (fundamental, TypeScript, React, NestJS, TanStack, Tailwind, SPA, REST API, PostgreSQL) — auto-detected and injected                                                                             |
| **Templates**          | Reference templates for IDEAS, BRD, RESEARCH, SPEC, PLAN artifacts                                                                                                                                                              |
| **Helper script**      | `pw.sh` — phase tracker management (YAML-based), traceability verification, config validation, profile resolution                                                                                                                |

## How it works

1. **pew.yaml** at your repo root defines project-specific settings (paths, stack, commands, competitors)
2. `/pew:run` activates the workflow — it reads config on-demand, manages phase state, and orchestrates agents
3. Agents receive scoped project context + review profiles + playbooks automatically
4. Quality gates (traceability, approval, council review) enforce precision at every step

## Project-specific playbooks

pew supports two layers of quality knowledge:

- **Review profiles** (generic, bundled with pew) — tech best practices for React, TypeScript, NestJS, etc.
- **Project playbooks** (your repo, at `config.paths.guidelines`) — project-specific conventions. Set `applies_to` tags in frontmatter for automatic matching.

Both are injected into council experts (CHECK) and tech agents (BUILD).

## Phase sizing

Not every change needs the full 7-step loop. Use `--size` when adding phases:

| Size | Steps | Use for |
| --- | --- | --- |
| `large` (default) | All 7 steps | Major features |
| `medium` | Skips IDEAS | Known features, no market research needed |
| `small` | Skips IDEAS + RESEARCH | Bug fixes, small scoped changes |

## Commands

```
/pew:run
  start phase <N>              # begin at first incomplete step
  start phase <N> auto         # run all steps, pause at gates
  continue phase <N>           # resume next incomplete step
  start building phase <N>     # explicit BUILD approval
  check phase <N>              # run CHECK/CLOSE
  status phase <N>             # show progress
```

## Requirements

- Claude Code with plugin support
- Python 3.8+ (auto-creates venv for PyYAML on first run)
- **Optional:** Chrome MCP or Playwright MCP server — required for browser-based product review (`config.product_review.enabled`). Without it, validation is skipped with a P2 advisory.
