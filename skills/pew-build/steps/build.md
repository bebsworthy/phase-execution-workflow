# Step 6: BUILD

- Requires explicit user command: `start building phase <N>`
- **Approval gate**: If `config.approval_gates.before_build` is true, present a gate summary via `AskUserQuestion` before proceeding: phase title, completed artifacts, key SPEC decisions, and task count from PLAN. Options: "Approve BUILD" / "Request changes". This gate fires in both manual and auto mode.
- Run `pw.sh set-step-status --phase N --step build --status in_progress`
- **Pre-gate**: read relevant playbooks from `{config.paths.guidelines}/` based on phase tags. Also resolve review profiles for the phase's tech stack using the PLAN.md task file references (same resolution logic as Step 7a, but scanning task target files instead of phase-diff output). Pass matched profiles to tech agents alongside playbook context.
- Implement tasks from PLAN.md in dependency order. If tasks are organized into tracks, tracks with no cross-track dependencies may execute in parallel. Within a track, execute in dependency order.
- When a task has an Agent assignment, spawn that agent (see `agents/build-frontend-developer.md` or `agents/build-backend-developer.md`). Provide: task description, acceptance criteria, linked tests from SPEC, resolved review profiles, project playbooks matching the agent's domain (from `{config.paths.guidelines}/`, filtered by `applies_to` tags), and phase `refs` doc contents (so agents can resolve finding IDs referenced in tasks). Each agent has mandatory verification steps (build, typecheck, lint).
- Add tests matching SPEC.md test plan
- Update implementation log in PLAN.md
- Atomic commits per implementation slice
- **Architecture reference check**: If new modules, services, or major architectural patterns were created during BUILD, update `{config.paths.research}/architecture-reference.md` to reflect the changes.
- Run `pw.sh set-step-status --phase N --step build --status complete` when done

**DO NOT:**

- Implement without reading relevant playbooks.
- Skip tests for any task.
- Change files outside the phase scope without documenting why.
- Refactor unrelated code.
