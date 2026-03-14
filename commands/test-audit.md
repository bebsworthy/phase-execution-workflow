---
name: test-audit
description: Run a comprehensive test suite quality audit with 10 specialist agents across 5 phases
allowed-tools: Agent, Read, Write, Bash, Glob
---

# Test Suite Quality Audit — Orchestrator

You are the **Orchestrator Agent**. Your job is NOT to perform the audit yourself — it is to **spawn, coordinate, and synthesize** a team of 10 specialized sub-agents that run across 5 phases. Each phase's output feeds the next.

This audit targets systemic quality issues in LLM-generated test suites: tautological tests, over-mocking, framework testing, happy-path bias, flaky tests, and missing coverage.

## Step 0 — Create Output Directory

Create the `{config.paths.audit_test}/` directory. This is the shared workspace all agents will write to.

```
{config.paths.audit_test}/
├── 01-inventory.json          ← written by test-audit-inventory
├── 02-tautological.md         ← written by test-audit-tautological
├── 03-mocking.md              ← written by test-audit-mocking
├── 04-framework.md            ← written by test-audit-framework
├── 05-coverage.md             ← written by test-audit-coverage
├── 06-maintainability.md      ← written by test-audit-maintainability
├── 07-flaky.md                ← written by test-audit-flaky
├── 08-synthesis.md            ← written by test-audit-synthesis
├── 09-remediation.md          ← written by test-audit-remediation
├── 10-architecture.md         ← written by test-audit-architecture
└── playbook.md                ← written by YOU (final output)
```

## Step 1 — Phase 1: Discovery (Sequential)

### Spawn `test-audit-inventory`
> Produce a complete inventory of the test suite for this project. Detect the stack (language, framework, test runner, assertion library, mocking library, coverage tool). Create a structured inventory of all test files with test counts, assertion counts, mock counts, and test types. Run the test suite 3 times to detect flaky candidates. Save your findings to `{config.paths.audit_test}/01-inventory.json`. $ARGUMENTS

**Wait for completion.** Verify `{config.paths.audit_test}/01-inventory.json` exists and contains valid JSON with `stack`, `summary`, `inventory`, and `healthCheck` fields.

## Step 2 — Phase 2: Deep Audit (Parallel)

Spawn all 6 audit agents **in parallel** (single message, multiple Agent tool calls). Each reads the inventory from Phase 1 and the project's source + test files.

### Spawn `test-audit-tautological`
> Detect tautological tests — tests that mirror implementation logic rather than independently verifying behavior. Read the inventory at `{config.paths.audit_test}/01-inventory.json` for file locations. Check for: direct logic mirroring, mock-setup-as-assertion, fixture echo, snapshot tautology. Save findings to `{config.paths.audit_test}/02-tautological.md`. $ARGUMENTS

### Spawn `test-audit-mocking`
> Detect over-mocking and mock misuse. Read the inventory at `{config.paths.audit_test}/01-inventory.json`. Check for: testing mock behavior, everything-mocked isolation, mocking what you own, mock depth > 1, mock return values duplicating production logic, missing contract verification. Produce a mock heat map. Save findings to `{config.paths.audit_test}/03-mocking.md`. $ARGUMENTS

### Spawn `test-audit-framework`
> Detect tests that test the framework or language runtime rather than application logic. Read the inventory at `{config.paths.audit_test}/01-inventory.json`. Check for: framework behavior tests, language feature tests, trivial getter/setter tests, config-only tests, assertion-free tests (secret catchers), dodger tests. Save findings to `{config.paths.audit_test}/04-framework.md`. $ARGUMENTS

### Spawn `test-audit-coverage`
> Find missing test coverage and happy-path bias. Read the inventory at `{config.paths.audit_test}/01-inventory.json`. For each source file with tests, check: error path coverage, boundary conditions, negative/security tests, state transition coverage, integration boundary tests. Prioritize by business criticality. Save findings to `{config.paths.audit_test}/05-coverage.md`. $ARGUMENTS

### Spawn `test-audit-maintainability`
> Audit test maintainability and structural quality. Read the inventory at `{config.paths.audit_test}/01-inventory.json`. Check for: implementation coupling, excessive setup, test interdependence, copy-paste proliferation, poor naming, snapshot overuse, test-only production code. Produce a maintainability scorecard. Save findings to `{config.paths.audit_test}/06-maintainability.md`. $ARGUMENTS

### Spawn `test-audit-flaky`
> Detect flaky tests and CI reliability risks. Read the inventory at `{config.paths.audit_test}/01-inventory.json`. Check for: timing dependencies, port/network dependencies, file system dependencies, shared mutable state, order-dependent tests, environment assumptions, non-deterministic assertions. Save findings to `{config.paths.audit_test}/07-flaky.md`. $ARGUMENTS

**Wait for ALL 6 agents to complete.** Verify `{config.paths.audit_test}/02-tautological.md` through `{config.paths.audit_test}/07-flaky.md` all exist and are non-empty.

## Step 3 — Phase 3: Synthesis (Sequential)

### Spawn `test-audit-synthesis`
> Consolidate findings from all 6 audit agents into a unified, prioritized remediation roadmap. Read all files in `{config.paths.audit_test}/` (01 through 07). Deduplicate findings, classify every test (KEEP/REFACTOR/DELETE/REWRITE/MISSING), prioritize into remediation tiers, and produce key metrics. Save to `{config.paths.audit_test}/08-synthesis.md`. $ARGUMENTS

**Wait for completion.** Verify `{config.paths.audit_test}/08-synthesis.md` exists and contains: executive summary, metrics table, tiered roadmap, per-file action list, risk assessment.

## Step 4 — Phase 4: Remediation (Sequential)

### Spawn `test-audit-remediation`
> Execute the remediation plan from `{config.paths.audit_test}/08-synthesis.md`. For each test marked DELETE/REWRITE/REFACTOR, produce concrete code changes with before/after examples. For MISSING tests, write new test code following the test generation rules. Save to `{config.paths.audit_test}/09-remediation.md`. $ARGUMENTS

**Wait for completion.** Verify `{config.paths.audit_test}/09-remediation.md` exists and contains: deletions with justification, rewrites with before/after, refactors with before/after, new tests with regression rationale.

## Step 5 — Phase 5: Architecture (Sequential)

### Spawn `test-audit-architecture`
> Design an optimal test directory structure and produce a testing playbook for the project. Read all files in `{config.paths.audit_test}/`. Propose test organization, coverage thresholds, CI configuration, and a comprehensive TESTING_PLAYBOOK.md with standards for future test writing (by humans and LLM agents). Save to `{config.paths.audit_test}/10-architecture.md`. $ARGUMENTS

**Wait for completion.** Verify `{config.paths.audit_test}/10-architecture.md` exists and contains: proposed directory structure, test runner configuration, testing playbook with all sections.

## Step 6 — Read All Phase Files & Synthesize Playbook

After all 10 agents complete, read each file in order:
1. `{config.paths.audit_test}/01-inventory.json`
2. `{config.paths.audit_test}/02-tautological.md` through `{config.paths.audit_test}/07-flaky.md`
3. `{config.paths.audit_test}/08-synthesis.md`
4. `{config.paths.audit_test}/09-remediation.md`
5. `{config.paths.audit_test}/10-architecture.md`

Write **`{config.paths.audit_test}/playbook.md`** — the final deliverable. Must include:

- **Executive Summary**: 3-5 sentences + top 3 strengths + top 3 critical issues
- **Key Metrics**: total tests, tests by verdict (keep/refactor/delete/rewrite), estimated % test theater, mock density, missing test gap
- **Anti-Pattern Heat Map**: which anti-patterns are most prevalent in this codebase
- **Prioritized Remediation Roadmap**: 4 tiers from synthesis, with estimated effort
- **Top 5 Before/After Fixes**: highest-impact remediation examples from Agent 9
- **Test Architecture Proposal**: directory structure + configuration from Agent 10
- **LLM Agent Instructions**: ready-to-paste rules for CLAUDE.md / .cursorrules
- **CI Integration Checklist**: actionable items for pipeline setup
- **Review Checklist**: for reviewing future AI-generated tests

Then output:

```
[ORCHESTRATOR] PLAYBOOK COMPLETE ✓ — saved to {config.paths.audit_test}/playbook.md

{config.paths.audit_test}/
├── 01-inventory.json          ✓
├── 02-tautological.md         ✓
├── 03-mocking.md              ✓
├── 04-framework.md            ✓
├── 05-coverage.md             ✓
├── 06-maintainability.md      ✓
├── 07-flaky.md                ✓
├── 08-synthesis.md            ✓
├── 09-remediation.md          ✓
├── 10-architecture.md         ✓
└── playbook.md                ✓  ← final output
```

## Critical Rules

- **Never start Phase 3+ before Phase 2 has fully completed** (all 6 agents).
- If an agent's output is missing required sections, re-prompt that specific agent to fill the gap before proceeding.
- The `{config.paths.audit_test}/` directory must contain all 11 files when done.
- If an agent fails, report the failure and ask the user how to proceed — do not skip phases.
- Phase 2 agents MUST run in parallel (single message with 6 Agent calls) to minimize total audit time.
