# Step 2: BRD (BRD.md)

- Run `pw.sh set-step-status --phase N --step brd --status in_progress`
- **Input**: IDEAS.md selected items, project docs, phase `refs` docs (if any — read each referenced file to resolve finding IDs and user goals cited in the brief)
- Read template reference: `templates/BRD.template.md`
- Define scope, goals, non-goals, deliverables, acceptance criteria
- Functional requirements as capability contract: FC-nnn with actor, preconditions, action, response, not-allowed, error mapping, evidence target
- **Mandatory negative acceptance criteria**: Every FC MUST have at least one "Not Allowed" entry in the Not-Allowed column. If the FC genuinely has no restrictions, state "No restrictions identified" with rationale.
- Explicit User Can / User Cannot boundaries
- If phase has `frontend` tag or BRD contains "User can" → must include `## E2E User Test Flows` section (preconditions, steps, expected outcomes, error paths)
- Open questions: present in structured format
- **Gate**: run `pw.sh verify-traceability --phase N --from ideas --to brd` before advancing
- Atomic commit on completion
- Run `pw.sh set-step-status --phase N --step brd --status complete`

**DO NOT:**

- Write FCs without "Not Allowed" entries. Every capability has boundaries.
- Skip E2E test flows for user-facing phases.
- Include implementation details. The BRD is WHAT, not HOW.
