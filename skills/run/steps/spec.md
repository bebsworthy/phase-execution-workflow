# Step 4: SPEC (SPEC.md)

- Run `pw.sh set-step-status --phase N --step spec --status in_progress`
- **Input**: BRD.md, RESEARCH.md
- Read template reference: `templates/SPEC.template.md`
- Deep implementation spec: architecture, data model, API contracts, auth, observability
- Explicit test plan: T-nnn with linked spec item, level, target file, scenario, assertions
- E2E test flows from BRD must map to `level: e2e` test entries
- Phase exit-criteria mapping
- **Gate**: run `pw.sh verify-traceability --phase N --from brd --to spec` before advancing
- Atomic commit on completion
- Run `pw.sh set-step-status --phase N --step spec --status complete`

**DO NOT:**

- Create test plan entries (T-nnn) without linking to a specific FC.
- Omit error handling specifications.
- Skip the traceability gate.
