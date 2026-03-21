---
name: pew-groom
description: >
  Shared grooming methodology, complexity scales, effort estimation model, and output formats for groom agents.
  This skill is preloaded by all groom-* agents to ensure consistent evaluation criteria.
user-invocable: true
---

# Automated Technical Grooming Framework

## Purpose

This framework powers a multi-phase technical grooming of issue tracker tickets. It analyzes issues against actual code across multiple repositories, producing a grounded technical analysis with clarifying questions, test plans, effort estimates, and Definition of Done.

The skill acts as the interface between Product Owners and Tech Leads — translating vague or incomplete requirements into actionable, code-grounded technical assessments.

Every analysis must answer: "Can we build this, how long will it take, and what's missing from the spec?"

## Tone & Approach

- Professional and constructive. The audience is product owners and non-technical stakeholders.
- Every finding must be grounded in actual code references (file paths, function names, module boundaries).
- **Acknowledge what's well-specified**: Note clear requirements, not just gaps.
- Adjust depth to complexity — a typo fix doesn't need an architectural analysis.

---

## Issue Clarity Scale

| Grade | Label | Definition | Action |
|-------|-------|-----------|--------|
| A | Complete | Clear objective, acceptance criteria, edge cases defined | Proceed to planning |
| B | Adequate | Objective clear, some gaps in edge cases or acceptance criteria | Minor clarifications needed |
| C | Insufficient | Objective understood but significant specification gaps | Clarifying questions required before planning |
| D | Ambiguous | Multiple interpretations possible, key information missing | Block until PO responds |
| F | Invalid | Contradictory requirements, impossible constraints, or no actionable content | Return to PO with explanation |

---

## Complexity Scale

| Level | Label | Estimated Duration | Analysis Depth | Breakdown Required? |
|-------|-------|--------------------|----------------|---------------------|
| XS | Trivial | < 1 day | Shallow: single file, single repo | No |
| S | Small | 1-3 days | Standard: few files, single repo | No |
| M | Medium | 3-5 days | Standard: cross-module, possibly multi-repo | No |
| L | Large | 1-2 weeks | Deep: cross-repo, architectural impact | Optional |
| XL | Epic | > 2 weeks | Deep: requires mandatory breakdown into sub-issues | Required |

---

## Effort Estimation Methodology

Raw development estimates must be multiplied by human-velocity factors to produce realistic total estimates. AI agents underestimate because they don't account for context switching, meetings, code review cycles, deployment ceremonies, and UAT coordination.

| Component | Multiplier | Description |
|-----------|------------|-------------|
| Development | 1.0x | Raw implementation time (coding + unit tests) |
| Testing | 0.3-0.5x | Integration testing, manual QA, test environment setup |
| Code Review | 0.1-0.2x | PR review cycles, addressing feedback, re-review |
| Deployment | 0.1x | Staging deploy, smoke tests, production deploy, monitoring |
| UAT | 0.2-0.3x | User acceptance testing coordination, feedback cycles |
| Buffer | 0.2x | Unexpected complications, context switching, meetings |
| **Total Multiplier** | **1.9-2.3x** | Applied to raw dev estimate |

### Confidence Levels

| Level | Definition | Range Width |
|-------|-----------|-------------|
| High | Well-understood codebase, clear requirements, no blockers | +/- 20% |
| Medium | Some unknowns, minor blockers, standard complexity | +/- 40% |
| Low | Significant unknowns, hard blockers, novel architecture | +/- 60% |

### Estimate Format

Always provide three-point estimates:
- **Optimistic**: base * 0.7 (everything goes smoothly)
- **Likely**: base * 1.0 (normal conditions)
- **Pessimistic**: base * 1.5 (complications arise)

### Breakdown Trigger

If the **likely** total estimate exceeds 10 working days (2 weeks), the estimator MUST propose a breakdown into sub-issues, each independently estimated and deliverable within 2 weeks.

---

## Blocker Classification

| Type | Definition | Action |
|------|-----------|--------|
| Hard Blocker | Cannot proceed without resolution (missing API, unmerged dependency, architectural decision needed) | Must resolve before work begins |
| Soft Blocker | Can work around but increases risk/effort (tech debt, missing tests, unclear ownership) | Note risk, propose mitigation |
| Tech Debt | Existing code issues that complicate implementation (tight coupling, missing abstractions, outdated patterns) | Document, estimate added effort |
| Missing Dependency | External system, API, or service not ready | Track, identify workarounds or parallel work |

---

## Finding Format

Each agent uses this consistent structure for individual findings:

```markdown
### [SEVERITY] Finding title
- **Repository**: repo-name
- **Files**: path/to/file(s)
- **Impact**: How this affects the implementation
- **Evidence**: Specific code/config demonstrating the issue
- **Recommendation**: Actionable guidance
```

Severity levels: `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`, `INFO`.

---

## Workspace Structure

The groom skill operates in a standalone workspace directory (not necessarily a git repo). Repositories are cloned into a `repos/` subdirectory.

```
{workspace}/
├── groom.yaml                    # Config: repos, tracker type, settings (see template)
├── groom/
│   ├── knowledge/                # Persistent across /clear
│   │   └── {repo-name}/
│   │       └── architecture.json # Cached architecture snapshot
│   └── {issue-id}/              # Per-issue analysis
│       ├── 01-intake.json       # Shared (approach-independent)
│       ├── 02-repos.json
│       ├── 03-architecture.md
│       ├── 04-approaches.md
│       ├── {approach-slug}/     # Per-approach deep analysis
│       │   ├── 05-code-impact.md
│       │   ├── 06-blockers.md
│       │   ├── 07-spec-evaluation.md
│       │   ├── 08-test-plan.md
│       │   ├── 09-estimation.md
│       │   ├── 10-review-completeness.md
│       │   ├── 11-review-feasibility.md
│       │   └── analysis.md      # FINAL OUTPUT for this approach
│       ├── {other-approach}/    # Additional approaches (on demand)
│       │   └── ...
│       └── .meta.json           # Run history (per-approach)
└── repos/                        # Cloned repositories
    └── {repo-name}/
```

### groom.yaml Schema

```yaml
repos:
  - name: string       # Short name (used as directory name under repos/)
    url: string        # Git clone URL
    branch: string     # Branch to checkout (default: main)
tracker:
  type: string         # linear | jira | youtrack | github | gitlab
  project: string      # Project key or identifier
settings:
  max_repos: number    # Maximum repos to analyze (default: 10)
```

A template is available at `plugin/templates/groom.yaml.example`.

---

## Re-run Protocol

When the analysis directory `groom/{issue-id}/` already exists:

1. Read `.meta.json` to get previous run metadata
2. Compare current issue state (updated timestamp, comment count) against last run
3. Determine re-run type:

| Scenario | Behavior |
|----------|----------|
| No changes since last run | Skip analysis, point user to existing `analysis.md` |
| New comments only | Focused re-analysis: intake extracts new comments, Phase 3-6 agents instructed to address new information and update analysis |
| Description changed | Full re-analysis (description change = scope change) |
| Different approach requested | Reuse shared files (01-04), create new approach subdir, run Phase 3-6 only |
| Force re-run (user request) | Full re-analysis regardless of changes |

---

## Completion Signals

All groom agents must end their output with:

```
[groom-<name>] COMPLETE ✓
```

If the agent has unresolvable questions that block analysis:

```
[groom-<name>] COMPLETE WITH QUESTIONS ✓
OPEN QUESTIONS:
1. Question text?
2. Question text?
```

Agents MUST NOT commit any changes. The orchestrator handles all file validation and state management.
