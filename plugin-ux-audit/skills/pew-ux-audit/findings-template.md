# Findings File Template

Use this template for your agent's output file.

```markdown
# Phase N — [Phase Title]
_Completed by: [ux-audit-{name}]_

## [Phase-specific sections as defined in agent instructions]

<Full narrative, tables, analysis as specified in your agent instructions>
```

## Findings Registry Row Format

Every finding across all phases uses this format:

| ID | Audit Layer | Finding | Framework Reference | Severity (0–4) | Frequency (1–4) | Job ID | Kano | Recommended Pattern |
|----|-------------|---------|---------------------|----------------|-----------------|--------|------|---------------------|
| F-NNN | [layer name] | [specific finding] | [framework + criterion] | [impact score] | [how often encountered] | J-XXX | Basic/Performance/Delighter | [pattern from Phase 3] |

## Proposal Block Format (Phase 5)

For each finding, scale the proposal template based on effort level:

**L1 fixes (< 1 hour):** Current State + Proposed Improvement + Before/After + Acceptance Criteria
**L2 fixes (hours):** Add Visual Reference + Code Skeleton
**L3 fixes (1–3 days):** Add Success Metric + full Acceptance Criteria
**L4–L5 fixes (weeks):** Full template including A/B Test Hypothesis + Rollout Strategy + Risk Assessment
