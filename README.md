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

1. Run `/pew-init` — it explores your repo, detects your tech stack and verification commands, and writes `pew.yaml` after your confirmation
2. Run `/pew-build` and say `start phase 1`

You can also run `/pew-init` again later to update the config if your project structure changes.

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

## Skills

### `/pew-build` — Phase Execution

The main workflow engine. Runs the 7-step loop (IDEAS → BRD → RESEARCH → SPEC → PLAN → BUILD → CHECK/CLOSE) with quality gates, council review, and auto mode. Orchestrates `build-*` and `council-*` agents during execution.

### `/pew-init` — Project Setup

Explores your repo, detects tech stack and verification commands, and writes `pew.yaml` after confirmation. Run again to update config when your project changes.

### `/pew-vibe` — Vibe Mode (Build First)

Inverts the pew-build flow: implement changes following user instructions, record each decision to a running log, then synthesize BRD/SPEC post-hoc before running the full CHECK/CLOSE quality gate. Supports decimal phase numbering (7.5) for inserting between existing phases.

Use when user testing reveals adjustments, quick iterations are needed, or the plan didn't survive contact with reality.

### `/pew-ux-audit` — UX/UI Audit

Standalone 5-phase UX/UI audit that runs independently of the build workflow. Spawns 5 sequential specialist agents (`ux-audit-*`) that trace every finding back to a user goal:

1. **Goals** — JTBD extraction, persona research, opportunity scoring
2. **Implementation** — Hierarchical task analysis, cognitive walkthroughs, error taxonomy
3. **Research** — Competitive benchmarking, pattern library, emotional design opportunities
4. **Audit** — 12-layer evaluation (IA, onboarding, task flows, Nielsen heuristics, cognitive science, visual design, accessibility WCAG 2.2 AA, emotional design, content quality, trust, delight, dark patterns, design system maturity)
5. **Proposals** — Graduated improvements (L1–L5) with Kano classification, phased roadmap, code skeletons, and success metrics

Output: ``{config.paths.audit_ux}/`` directory with per-phase reports and a synthesized playbook.

### `/pew-test-audit` — Test Suite Quality Audit

Standalone 5-phase audit targeting systemic quality issues in LLM-generated test suites. Spawns 10 specialist agents (`test-audit-*`) across 5 phases — Phase 2 runs 6 agents in parallel for speed:

1. **Discovery** — Stack detection, test inventory, coverage baseline, flaky candidate detection
2. **Deep Audit** (6 agents in parallel) — Tautological tests, over-mocking, framework testing, missing coverage, maintainability, flaky tests
3. **Synthesis** — Deduplicate findings, classify every test (KEEP/REFACTOR/DELETE/REWRITE/MISSING), prioritize remediation
4. **Remediation** — Concrete code fixes with before/after examples for highest-impact issues
5. **Architecture** — Test directory redesign, testing playbook, CI configuration, LLM agent instructions

Output: ``{config.paths.audit_test}/`` directory with per-phase reports and a synthesized playbook.

## What's included

| Component              | Description                                                                                                                                                                                                                     |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **5 skills + 4 commands** | Skills: `/pew-build`, `/pew-init`, `/pew-vibe`, `/pew-ux-audit`, `/pew-test-audit`. Commands: `/pew-vibe` (start vibe phase), `/pew-ux-audit` (run UX audit), `/pew-test-audit` (run test audit), `/pew-audit-to-phases` (convert findings to phases) |
| **34 agents**          | Step writers (5): ideas, BRD, research, spec, plan. Research (3): feature benchmarker, UX researcher, UX designer. Build (2): frontend/backend developers. Vibe (1): vibe synthesizer. Council (6): security, architecture, testing, test-quality, frontend, backend. Verification (2): alignment checker, product reviewer. UX audit (5): goals, impl, research, eval, proposals. Test audit (10): inventory, tautological, mocking, framework, coverage, maintainability, flaky, synthesis, remediation, architecture. See [agents/README.md](agents/README.md) |
| **Review profiles**    | Composable tech best practices (fundamental, TypeScript, React, NestJS, TanStack, Tailwind, SPA, REST API, PostgreSQL) — auto-detected and injected                                                                             |
| **Templates**          | Reference templates for IDEAS, BRD, RESEARCH, SPEC, PLAN, DECISIONS (vibe mode), RETRO artifacts                                                                                                                                                              |
| **Helper script**      | `pw.sh` — phase tracker management (YAML-based), traceability verification, config validation, profile resolution                                                                                                                |

## How it works

1. **pew.yaml** at your repo root defines project-specific settings (paths, stack, commands, competitors)
2. `/pew-build` activates the workflow — it reads config on-demand, manages phase state, and orchestrates agents
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
/pew-build
  start phase <N>              # begin at first incomplete step
  start phase <N> auto         # run all steps, pause at gates
  continue phase <N>           # resume next incomplete step
  plan phase <N>               # run IDEAS through PLAN, stop before BUILD
  plan phase <N> auto          # same in auto mode
  start building phase <N>     # explicit BUILD approval
  check phase <N>              # run CHECK/CLOSE
  status phase <N>             # show progress

/pew-vibe                       # start a vibe phase (build first, document post-hoc)
/pew-ux-audit                  # run full 5-phase UX/UI audit
/pew-test-audit                # run 10-agent test suite quality audit
/pew-audit-to-phases           # convert audit findings into PEW phases
```

## Requirements

- Claude Code with plugin support
- Python 3.8+ (auto-creates venv for PyYAML on first run)
- **Optional:** Chrome MCP or Playwright MCP server — required for browser-based product review (`config.product_review.enabled`). Without it, validation is skipped with a P2 advisory.
