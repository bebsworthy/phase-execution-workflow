# Step 3: RESEARCH (RESEARCH.md)

- Run `pw.sh set-step-status --phase N --step research --status in_progress`
- **Input**: BRD.md, project docs/code, phase `refs` docs (if any — read each referenced file for prior research, UX audit findings, etc.)
- Read template reference: `templates/RESEARCH.template.md`
- **Architecture baseline**: Before starting research, check if `{config.paths.research}/architecture-reference.md` exists. If it exists, read it as baseline context — research should focus on novel, phase-specific findings only. If it does not exist, create it as part of this step: perform a one-time codebase architecture analysis covering project structure, module boundaries, data flow patterns, key abstractions, and tech stack details. Save to `{config.paths.research}/architecture-reference.md`. Future phases reference this doc instead of re-analyzing. When architecture changes significantly during a phase's BUILD step, update the shared doc.
- **Conciseness target**: RESEARCH.md should contain fewer than 2000 tokens of novel, phase-specific content. Reference shared docs (architecture-reference.md, prior UX research) for baseline context rather than restating it.
- **Step 3a — Parallel research** (run concurrently where possible):
  - For frontend-tagged phases: Spawn `build-ux-researcher` agent with BRD.md and phase context. Produces `{config.paths.research}/ux-<theme-slug>.md` (principles, patterns, component mappings, anti-patterns).
  - Simultaneously begin technical research: investigate technical feasibility, architectural options, risks, and ambiguities. Evidence-backed findings with concrete resolution propositions.
- **Step 3b — UX design** (frontend-tagged phases only, requires 3a UX research output): Spawn `build-ux-designer` agent with BRD.md and UX research output. Produces `DESIGN.md` in the phase directory. Wait for completion before 3c.
- **Step 3c — Consolidate**: Merge UX research, UX design (if applicable), and technical research into RESEARCH.md.
- Each open question: concrete resolution propositions + recommendation
- Review previous phase artifacts when relevant
- Post chat summary of open questions and proposed resolutions
- Open questions: present in structured format
- Atomic commit on completion
- Run `pw.sh set-step-status --phase N --step research --status complete`

**DO NOT:**

- Skip UX research for frontend-tagged phases.
- Propose architecture without evidence (benchmarks, docs, prior art).
- Copy UX research verbatim into RESEARCH.md. Synthesize and reference.
- Repeat general architecture information available in the shared reference doc.
