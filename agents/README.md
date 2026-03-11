# Phase Workflow Sub-Agents

Claude Code sub-agent contracts for use during phase execution. Each file uses YAML frontmatter (`name`, `description`, `tools`, `model`) followed by a system prompt — the standard Claude Code sub-agent format.

All agents receive project context automatically via the `SubagentStart` hook, which injects the resolved `pew.yaml` config. Agents reference `config.*` fields for project-specific values (paths, stack, competitors, conventions).

The main agent MAY spawn these as needed, and MAY define additional phase-specific agents.

| Agent                                           | Model   | When to Use                                                              | Input                                                 | Output                                                      |
| ----------------------------------------------- | ------- | ------------------------------------------------------------------------ | ----------------------------------------------------- | ----------------------------------------------------------- |
| [feature-benchmarker](feature-benchmarker.md)   | inherit | IDEAS step: industry research (always, unless purely internal phase)     | Brief, tags, current app state, research log          | Research file in `{config.paths.research}/` + 20-30 items   |
| [alignment-checker](alignment-checker.md)       | inherit | CHECK step: verify code matches spec                                     | SPEC.md, BRD.md, phase-diff output                    | Alignment report (aligned/misaligned/missing) + conventions |
| [ux-researcher](ux-researcher.md)               | inherit | RESEARCH step 3a: UX patterns and principles                             | BRD.md, phase context                                 | Topical report in `{config.paths.research}/ux-*.md`         |
| [ux-designer](ux-designer.md)                   | inherit | RESEARCH step 3b: concrete UX design for the phase                       | BRD.md, UX research output                            | `DESIGN.md` in phase directory                              |
| [council-security](council-security.md)         | inherit | CHECK step 7a: security review (always active)                           | Phase diff files, BRD.md, SPEC.md                     | JSON findings with SEC-nnn IDs                              |
| [council-architecture](council-architecture.md) | inherit | CHECK step 7a: architecture review (always active)                       | Phase diff files, BRD.md, SPEC.md                     | JSON findings with ARCH-nnn IDs                             |
| [council-testing](council-testing.md)           | inherit | CHECK step 7a: test strategy review (always active)                      | Test + source files, BRD.md, SPEC.md                  | JSON findings with TEST-nnn IDs                             |
| [council-test-quality](council-test-quality.md) | inherit | CHECK step 7a: test implementation quality (always active)               | Test files, BRD.md, SPEC.md                           | JSON findings with TQ-nnn IDs                               |
| [council-frontend](council-frontend.md)         | inherit | CHECK step 7a: frontend review (if `frontend` tag or frontend_src)       | Frontend files, BRD.md, SPEC.md                       | JSON findings with FE-nnn IDs                               |
| [council-backend](council-backend.md)           | inherit | CHECK step 7a: backend review (if `backend` tag or server files)         | Backend files, BRD.md, SPEC.md                        | JSON findings with BE-nnn IDs                               |
| [frontend-developer](frontend-developer.md)     | inherit | BUILD step: frontend task execution (if task Agent = frontend-developer) | Task, acceptance criteria, tests, profiles, playbooks | Files created/modified + verification results               |
| [backend-developer](backend-developer.md)       | inherit | BUILD step: backend task execution (if task Agent = backend-developer)   | Task, acceptance criteria, tests, profiles, playbooks | Files created/modified + verification results               |
| [product-reviewer](product-reviewer.md)         | inherit | CHECK step 7b: browser-based product validation (if frontend + enabled)  | BRD.md, app URL, start command                        | JSON findings with PR-nnn IDs                               |
