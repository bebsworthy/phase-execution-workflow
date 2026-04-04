---
name: pew-security-audit
description: Run a comprehensive application security audit with up to 10 specialist agents across 5 phases
allowed-tools: Agent, Read, Write, Bash, Glob, AskUserQuestion
---

# Application Security Audit — Orchestrator

You are the **Orchestrator Agent**. Your job is NOT to perform the audit yourself — it is to **spawn, coordinate, and synthesize** a team of up to 10 specialized sub-agents across 5 phases. Each phase's output feeds the next.

This audit covers code security, secrets hygiene, supply chain, server-side, frontend, and infrastructure security. Not all domains apply to every project — the inventory agent determines which domains are relevant.

## Step 0 — Initialize

### 0a. Load Config

Read `pew.yaml` from the project root. If it doesn't exist, tell the user to run `/pew-init` first.

Extract `paths.audit_security` — this is the `{output_dir}` for all agents. If the key doesn't exist, default to `phases/audit/security`.

### 0b. Create Output Directory

Create the `{output_dir}/` directory.

```
{output_dir}/
├── 01-inventory.json          ← security-audit-inventory
├── 02-code.md                 ← security-audit-code (always)
├── 03-secrets.md              ← security-audit-secrets (always)
├── 04-supply-chain.md         ← security-audit-supply-chain (conditional)
├── 05-server.md               ← security-audit-server (conditional)
├── 06-frontend.md             ← security-audit-frontend (conditional)
├── 07-infrastructure.md       ← security-audit-infrastructure (conditional)
├── 08-synthesis.md            ← security-audit-synthesis
├── 09-remediation.md          ← security-audit-remediation
├── 10-playbook.md             ← security-audit-playbook
└── report.md                  ← YOU (final output)
```

## Step 1 — Phase 1: Discovery (Sequential)

### Spawn `security-audit-inventory`
> Map the project structure, tech stack, security-relevant files, and determine which security domains need auditing. Detect mono-repo structure and sub-projects. Identify existing security tooling. Save findings to `{output_dir}/01-inventory.json`. $ARGUMENTS

**Wait for completion.** Verify `{output_dir}/01-inventory.json` exists and contains valid JSON with `repoType`, `subProjects`, `activeDomains`, and `summary` fields.

## Step 2 — Phase 2: Deep Audit (Parallel, Conditional)

### 2a. Read Activation Plan

Read ONLY the `activeDomains` and `summary` fields from `{output_dir}/01-inventory.json`. Do NOT read the full file into your context — just the activation data.

Check `pew.yaml` for `security_audit.domains` overrides. If present, merge: config overrides win.

### 2b. Present Activation Plan

Use `AskUserQuestion` to confirm which domains to audit:

> Based on project inventory, I'll run these security domains:
>
> [x] Code Security (N sub-projects) — always runs
> [x] Secrets Hygiene (N sub-projects) — always runs
> [x/skip] Supply Chain (N sub-projects) — reason
> [x/skip] Server Security (N sub-projects) — reason
> [x/skip] Frontend Security (N sub-projects) — reason
> [x/skip] Infrastructure (N sub-projects) — reason
>
> Total: N agents in parallel. Override? (add/remove domains, or 'go')

If the user wants to override, adjust the activation. Then proceed.

### 2c. Spawn Active Agents

Spawn all active agents **in parallel** (single message, multiple Agent tool calls). Pass each agent its assigned sub-projects from `activeDomains`.

**Always spawn:**

#### Spawn `security-audit-code`
> Audit code-level security: injection patterns, input validation, cryptographic failures, error handling, insecure coding patterns. Read inventory at `{output_dir}/01-inventory.json`. Your assigned sub-projects: {activeDomains.code.subProjects}. Save findings to `{output_dir}/02-code.md`. $ARGUMENTS

#### Spawn `security-audit-secrets`
> Audit secrets hygiene: hardcoded credentials, API keys, tokens, .env exposure, secrets in Docker/CI, git history. Read inventory at `{output_dir}/01-inventory.json`. Your assigned sub-projects: {activeDomains.secrets.subProjects}. Save findings to `{output_dir}/03-secrets.md`. $ARGUMENTS

**Conditionally spawn (if activeDomains.X.active is true):**

#### Spawn `security-audit-supply-chain` (if supplyChain active)
> Audit supply chain security: dependency vulnerabilities, lockfile integrity, CI/CD pipeline security, dependency confusion, build system. Read inventory at `{output_dir}/01-inventory.json`. Your assigned sub-projects: {activeDomains.supplyChain.subProjects}. Save findings to `{output_dir}/04-supply-chain.md`. $ARGUMENTS

#### Spawn `security-audit-server` (if server active)
> Audit server-side security: OWASP Top 10, authentication/authorization, API security, database security, SSRF, error handling. Read inventory at `{output_dir}/01-inventory.json`. Your assigned sub-projects: {activeDomains.server.subProjects}. Save findings to `{output_dir}/05-server.md`. $ARGUMENTS

#### Spawn `security-audit-frontend` (if frontend active)
> Audit frontend security: XSS, CSP, CSRF, browser security headers, client-side storage, third-party scripts, framework-specific vulnerabilities. Read inventory at `{output_dir}/01-inventory.json`. Your assigned sub-projects: {activeDomains.frontend.subProjects}. Save findings to `{output_dir}/06-frontend.md`. $ARGUMENTS

#### Spawn `security-audit-infrastructure` (if infrastructure active)
> Audit infrastructure security: Docker hardening, reverse proxy config, TLS, database configuration, CI/CD deployment, runtime security. Read inventory at `{output_dir}/01-inventory.json`. Your assigned sub-projects: {activeDomains.infrastructure.subProjects}. Save findings to `{output_dir}/07-infrastructure.md`. $ARGUMENTS

**Wait for ALL spawned agents to complete.** Verify each expected output file exists and is non-empty.

## Step 3 — Phase 3: Synthesis (Sequential)

### Spawn `security-audit-synthesis`
> Consolidate findings from all Phase 2 agents into a unified security assessment. Read all files in `{output_dir}/` (01 through 07, only those that exist). Deduplicate findings, identify attack chains, compute security posture score, create tiered remediation roadmap. Save to `{output_dir}/08-synthesis.md`. $ARGUMENTS

**Wait for completion.** Verify `{output_dir}/08-synthesis.md` exists and contains: executive summary, security posture score, vulnerability heat map, tiered roadmap, per-file action list.

## Step 4 — Phase 4: Remediation (Sequential)

### Spawn `security-audit-remediation`
> Produce concrete fixes for all security findings. Read `{output_dir}/08-synthesis.md` for the prioritized roadmap. For Tier 1/2 findings, produce before/after code fixes. For Tier 3, produce implementation guides. For Tier 4, produce CI/CD and process configurations. Save to `{output_dir}/09-remediation.md`. $ARGUMENTS

**Wait for completion.** Verify `{output_dir}/09-remediation.md` exists and contains: quick wins checklist, Tier 1-4 fixes/guides, verification steps.

## Step 5 — Phase 5: Security Playbook (Sequential)

### Spawn `security-audit-playbook`
> Produce a comprehensive security playbook for the project. Read all files in `{output_dir}/`. Create SSDLC recommendations, CI/CD security pipeline config, pre-commit hooks, CLAUDE.md security rules, PR review checklist, logging/monitoring recommendations, and architecture improvements. Save to `{output_dir}/10-playbook.md`. $ARGUMENTS

**Wait for completion.** Verify `{output_dir}/10-playbook.md` exists and contains: SSDLC recommendations, CI/CD config, CLAUDE.md rules, PR checklist.

## Step 6 — Read All Phase Files & Synthesize Report

After all agents complete, read each file in order:
1. `{output_dir}/01-inventory.json`
2. `{output_dir}/02-code.md` through `{output_dir}/07-infrastructure.md` (only those that exist)
3. `{output_dir}/08-synthesis.md`
4. `{output_dir}/09-remediation.md`
5. `{output_dir}/10-playbook.md`

Write **`{output_dir}/report.md`** — the final deliverable. Must include:

- **Executive Summary**: 3-5 sentences + security posture score + top 3 risks + top 3 strengths
- **Audit Scope**: Which domains were audited, which were skipped, sub-project breakdown
- **Key Metrics**: Total findings by severity, by category, by sub-project (for mono-repos)
- **Vulnerability Heat Map**: From synthesis
- **Attack Chain Analysis**: Top 3 most dangerous exploit paths from synthesis
- **Prioritized Remediation Roadmap**: 4 tiers with estimated effort from synthesis
- **Quick Wins (Top 10)**: Highest-impact, lowest-effort fixes from remediation
- **Top 5 Before/After Fixes**: Most impactful code fixes from remediation
- **Security Playbook Summary**: Key recommendations from playbook
- **CLAUDE.md Security Rules**: Ready-to-paste rules from playbook
- **CI/CD Security Checklist**: Actionable pipeline additions from playbook
- **PR Security Review Checklist**: For reviewing future code changes

Then output:

```
[ORCHESTRATOR] REPORT COMPLETE ✓ — saved to {output_dir}/report.md

{output_dir}/
├── 01-inventory.json          ✓
├── 02-code.md                 ✓
├── 03-secrets.md              ✓
├── 04-supply-chain.md         ✓ (or skipped)
├── 05-server.md               ✓ (or skipped)
├── 06-frontend.md             ✓ (or skipped)
├── 07-infrastructure.md       ✓ (or skipped)
├── 08-synthesis.md            ✓
├── 09-remediation.md          ✓
├── 10-playbook.md             ✓
└── report.md                  ✓  ← final output
```

## Step 7 — Offer to Create Phases

After the report is complete, ask the user if they want to convert the findings into PEW phases:

> "The audit found N findings across M tiers. Want me to create phases to fix them?"

If yes, follow the `audit-to-phases` command logic (see `commands/pew-audit-to-phases.md`):
1. Read the synthesis (`08-synthesis.md`) to extract remediation tiers
2. Check current phase state (`pw.sh list-phases --json`)
3. Propose phases with smart scheduling (start now vs. queue after current work)
4. Ask for confirmation via `AskUserQuestion`
5. Create phases via `pw.sh add-phase` with `--tags security`

If the user declines, just output the report and finish. They can run `/pew-audit-to-phases` later.

If `pw.sh validate-config` shows no pew.yaml, skip this step — tell the user to run `/pew-init` first if they want to create phases.

## Critical Rules

- **Never start Phase 3+ before Phase 2 has fully completed** (all active agents).
- If an agent's output is missing required sections, re-prompt that specific agent to fill the gap before proceeding.
- The `{output_dir}/` directory must contain all expected files when done (inventory + active domain files + synthesis + remediation + playbook + report).
- If an agent fails, report the failure and ask the user how to proceed — do not skip phases.
- Phase 2 agents MUST run in parallel (single message with N Agent calls) to minimize total audit time.
- **Conditional activation is mandatory**: Read the inventory before spawning Phase 2 agents. Never spawn agents for inactive domains.
- When passing sub-project lists to agents, include the sub-project ID and path, not the full inventory JSON.
