# Step 5: PLAN (PLAN.md)

- Run `pw.sh set-step-status --phase N --step plan --status in_progress`
- **Input**: SPEC.md
- Read template reference: `templates/PLAN.template.md`
- Ordered task list (PH-nnn) with dependencies and acceptance criteria
- Task statuses: `todo | in_progress | done | descoped`
- **Parallel tracks**: Group independent tasks into named tracks (A, B, C...). Track A = foundation tasks with no dependencies. Subsequent tracks may execute in parallel once their track-level dependencies are met.
- **Agent assignment**: For each task, suggest a tech agent based on task type: frontend component/hook/page work → `frontend-developer`, backend service/controller/migration → `backend-developer`. If no specific agent fits, leave blank (main agent handles it).
- **Gate**: run `pw.sh verify-traceability --phase N --from spec --to plan` before advancing
- Atomic commit on completion
- Run `pw.sh set-step-status --phase N --step plan --status complete`

**DO NOT:**

- Create tasks without acceptance criteria.
- Sequence tasks without considering dependency order.
- Include tasks that cannot be verified independently.
- Create tracks with circular cross-track dependencies.
