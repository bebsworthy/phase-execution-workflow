# Phase Workflow Sub-Agents

Claude Code sub-agent contracts for use during phase execution. Each file uses YAML frontmatter (`name`, `description`, `tools`, `model`) followed by a system prompt — the standard Claude Code sub-agent format.

All agents receive project context automatically via the `SubagentStart` hook defined in `plugin.json`. The hook runs `pw.sh dump-config --scope <role>` and injects the result as `additionalContext` into the agent's context window. Agents reference `config.*` fields for project-specific values (paths, stack, competitors, conventions).

Scope mapping: `build-*` → `agent`, `council-*` → `council`, research agents (`build-feature-benchmarker`, `build-ux-researcher`, `build-ux-designer`) → `research`.

The main agent MAY spawn these as needed, and MAY define additional phase-specific agents.

### Step Agents (orchestrator spawns these for each workflow step)

| Agent                                           | Model   | Step                          | Input                                                 | Output                                                      |
| ----------------------------------------------- | ------- | ----------------------------- | ----------------------------------------------------- | ----------------------------------------------------------- |
| [build-ideas-writer](build-ideas-writer.md)               | inherit | IDEAS: ideation + synthesis   | Brief, refs, retro, benchmark docs, conventions       | `{phase-dir}/IDEAS.md`                                      |
| [build-brd-writer](build-brd-writer.md)                   | inherit | BRD: requirements definition  | IDEAS.md, refs, conventions                           | `{phase-dir}/BRD.md`                                        |
| [build-research-writer](build-research-writer.md)         | inherit | RESEARCH: technical synthesis | BRD.md, refs, UX docs, arch-ref, conventions          | `{phase-dir}/RESEARCH.md`                                   |
| [build-spec-writer](build-spec-writer.md)                 | inherit | SPEC: technical specification | BRD.md, RESEARCH.md, DESIGN.md?, conventions          | `{phase-dir}/SPEC.md`                                       |
| [build-plan-writer](build-plan-writer.md)                 | inherit | PLAN: task decomposition      | SPEC.md, conventions                                  | `{phase-dir}/PLAN.md`                                       |

### Research Agents (spawned by orchestrator during IDEAS and RESEARCH steps)

| Agent                                           | Model   | When to Use                                                              | Input                                                 | Output                                                      |
| ----------------------------------------------- | ------- | ------------------------------------------------------------------------ | ----------------------------------------------------- | ----------------------------------------------------------- |
| [build-feature-benchmarker](build-feature-benchmarker.md) | inherit | IDEAS step: industry research (always, unless purely internal phase)     | Brief, tags, research log                             | Research file in `{config.paths.research}/` + 20-30 items   |
| [build-ux-researcher](build-ux-researcher.md)             | inherit | RESEARCH step: UX patterns and principles (frontend phases)              | BRD.md, phase context                                 | Topical report in `{config.paths.research}/ux-*.md`         |
| [build-ux-designer](build-ux-designer.md)                 | inherit | RESEARCH step: concrete UX design (frontend phases, after ux-researcher) | BRD.md, UX research output                            | `DESIGN.md` in phase directory                              |

### Build Agents (spawned by orchestrator during BUILD step)

| Agent                                           | Model   | When to Use                                                              | Input                                                 | Output                                                      |
| ----------------------------------------------- | ------- | ------------------------------------------------------------------------ | ----------------------------------------------------- | ----------------------------------------------------------- |
| [build-frontend-developer](build-frontend-developer.md)   | inherit | BUILD step: frontend task execution (if task Agent = build-frontend-developer) | Task, acceptance criteria, tests, profiles, playbooks | Files created/modified + verification results               |
| [build-backend-developer](build-backend-developer.md)     | inherit | BUILD step: backend task execution (if task Agent = build-backend-developer)   | Task, acceptance criteria, tests, profiles, playbooks | Files created/modified + verification results               |

### Council Agents (spawned by orchestrator during CHECK step 7a)

| Agent                                           | Model   | When to Use                                                              | Input                                                 | Output                                                      |
| ----------------------------------------------- | ------- | ------------------------------------------------------------------------ | ----------------------------------------------------- | ----------------------------------------------------------- |
| [council-security](council-security.md)         | inherit | CHECK step 7a: security review (always active)                           | Phase diff files, BRD.md, SPEC.md                     | JSON findings with SEC-nnn IDs                              |
| [council-architecture](council-architecture.md) | inherit | CHECK step 7a: architecture review (always active)                       | Phase diff files, BRD.md, SPEC.md                     | JSON findings with ARCH-nnn IDs                             |
| [council-testing](council-testing.md)           | inherit | CHECK step 7a: test strategy review (always active)                      | Test + source files, BRD.md, SPEC.md                  | JSON findings with TEST-nnn IDs                             |
| [council-test-quality](council-test-quality.md) | inherit | CHECK step 7a: test implementation quality (always active)               | Test files, BRD.md, SPEC.md                           | JSON findings with TQ-nnn IDs                               |
| [council-frontend](council-frontend.md)         | inherit | CHECK step 7a: frontend review (if `frontend` tag or frontend_src)       | Frontend files, BRD.md, SPEC.md                       | JSON findings with FE-nnn IDs                               |
| [council-backend](council-backend.md)           | inherit | CHECK step 7a: backend review (if `backend` tag or server files)         | Backend files, BRD.md, SPEC.md                        | JSON findings with BE-nnn IDs                               |

### Verification Agents (spawned by orchestrator during CHECK step 7b)

| Agent                                           | Model   | When to Use                                                              | Input                                                 | Output                                                      |
| ----------------------------------------------- | ------- | ------------------------------------------------------------------------ | ----------------------------------------------------- | ----------------------------------------------------------- |
| [build-alignment-checker](build-alignment-checker.md)     | inherit | CHECK step 7b: verify code matches spec                                  | SPEC.md, BRD.md, phase-diff output                    | Alignment report (aligned/misaligned/missing) + conventions |
| [build-product-reviewer](build-product-reviewer.md)       | inherit | CHECK step 7b: browser-based product validation (if frontend + enabled)  | BRD.md, app URL, start command                        | JSON findings with PR-nnn IDs                               |

### UX Audit Agents (spawned by ux-audit command orchestrator)

| Agent                                           | Model   | When to Use                                                              | Input                                                 | Output                                                      |
| ----------------------------------------------- | ------- | ------------------------------------------------------------------------ | ----------------------------------------------------- | ----------------------------------------------------------- |
| [ux-audit-goals](ux-audit-goals.md)             | inherit | UX audit Phase 1: user goal extraction (JTBD, ODI, demand-side)          | Project docs, web research                            | `ux-review/01-user-goals.md`                                |
| [ux-audit-impl](ux-audit-impl.md)               | inherit | UX audit Phase 2: implementation review (HTA, cognitive walkthroughs)    | Phase 1 output                                        | `ux-review/02-implementation.md`                            |
| [ux-audit-research](ux-audit-research.md)       | inherit | UX audit Phase 3: pattern research & competitive benchmarking            | Phase 2 output                                        | `ux-review/03-patterns.md`                                  |
| [ux-audit-eval](ux-audit-eval.md)               | inherit | UX audit Phase 4: full 12-layer UX/UI audit                             | Phases 1–3 output                                     | `ux-review/04-audit.md`                                     |
| [ux-audit-proposals](ux-audit-proposals.md)     | inherit | UX audit Phase 5: improvement proposals & roadmap                        | Phases 1–4 output                                     | `ux-review/05-proposals.md`                                 |
