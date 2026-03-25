# Playbook Template

Use this template for `{output_dir}/report.md`.

```markdown
# UX/UI Playbook — [Application Name]
_Generated: <date> | Based on: 01-user-goals.md, 02-implementation.md, 03-patterns.md, 04-audit.md, 05-proposals.md_

---

## Executive Summary
[3–5 sentences: what is the application, who is it for, what is the primary job it serves,
overall health verdict, and the single most important thing to fix first.]

**Overall UX Maturity:** Level X/3 (No System / Emerging / Managed / Mature)

**Top 3 Strengths:** [what the app does genuinely well — be specific]
**Top 3 Critical Gaps:** [the highest-severity findings that most directly block user jobs]

**Emotional Design Verdict:**
- Visceral: X/4 — [one-line assessment]
- Behavioral: X/4 — [one-line assessment]
- Reflective: X/4 — [one-line assessment]

---

## User Goals (from Phase 1)

### JTBD Summary
| Job ID | Statement (short) | Importance | Satisfaction | Opportunity | Primary Segment |
|--------|-------------------|-----------|-------------|-------------|-----------------|

### Demand-Side Forces Summary
[Key push/pull/habit/anxiety patterns that shape the user's relationship with this product.]

---

## How Well the App Serves Each Job Today (from Phases 2 + 4)
[One paragraph per job: current state assessment, biggest friction point, outcome delivery status, overall grade A–F]

---

## Key Patterns to Apply (from Phase 3)
| Pattern Name | Gap It Fixes | Source | Evidence | Kano | Emotional Impact |
|-------------|-------------|--------|----------|------|-----------------|

---

## Full Findings Registry (from Phase 4)
| ID | Layer | Finding | Framework | Severity | Frequency | Job | Kano | Pattern |
|----|-------|---------|-----------|----------|-----------|-----|------|---------|

---

## Improvement Roadmap (from Phase 5)

### Phase 1 — Quick Wins (Week 1–2)
[List with F-IDs, one-line description, effort, and Kano category]
**Success criteria:** [measurable outcomes for this phase]

### Phase 2 — Core Improvements (Week 3–8)
[List with F-IDs, one-line description, effort, and Kano category]
**Success criteria:** [measurable outcomes for this phase]

### Phase 3 — Strategic Redesigns (Quarter+)
[List with F-IDs, one-line description, effort, and Kano category]
**Success criteria:** [measurable outcomes for this phase]

---

## Top 5 Before/After Proposals
[The five highest-impact proposals written in full, including:
- Current state and proposed change
- Pattern basis and emotional impact
- Visual reference (layout description, component hierarchy, design tokens)
- Code skeleton (before/after for component-level changes)
- Success metric and acceptance criteria
- A/B test hypothesis (if applicable)]

---

## Design System Recommendations
### Token Inventory
[Recommended color, spacing, typography, radius, shadow, and transition tokens]

### Component Checklist
[Components needing states defined or improved, with priority]

### Implementation Priority
[Foundation → Core → Patterns timeline]

---

## Analytics & Instrumentation Plan
### Key Funnels to Track
[Per-job funnels with events and expected conversion rates]

### Recommended Dashboards
[What to monitor post-implementation to verify improvement]

### Rollout Strategy
[Phased rollout approach with rollback criteria per phase]

---

## Risk Register
[Top 5 risks for the improvement roadmap with likelihood, impact, and mitigation]

---

## Definition of Done (Full Audit)
[Measurable acceptance criteria for each phase. E.g.:
- All Nielsen heuristic violations scoring 3+ resolved
- Zero WCAG Level A violations
- All form inputs pass axe audit
- Primary job completable in <= N steps (matching benchmark)
- All error messages name the problem and suggest a fix
- Skeleton screens on all async content loads
- Design system token adoption > 75%
- Emotional design: no visceral/behavioral contradictions
- No dark patterns detected
- Core Web Vitals in "Good" range for primary pages]
```
