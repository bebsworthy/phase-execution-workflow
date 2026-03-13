# Step 1: IDEAS (IDEAS.md)

- Run `pw.sh set-step-status --phase N --step ideas --status in_progress`
- **Input**: Phase brief (from `{config.paths.tracker}` `brief` field), phase title/tags, previous phase RETRO.md (if exists), phase `refs` docs (if any — read each referenced file for context on finding IDs, user goals, etc.)
- Read template reference: `templates/IDEAS.template.md`
- **Step 1a — Current state review**: Before generating ideas, review what the app currently does in the relevant area. Read existing code, routes, components, and API endpoints related to the phase topic. Summarize current capabilities as context for ideation.
- **Step 1b — Market research**: Spawn the build-feature-benchmarker agent (see `agents/build-feature-benchmarker.md`). Provide: phase brief, title, tags, current app capabilities summary, list of existing files in `{config.paths.research}/`, and the research log. Research output saved to `{config.paths.research}/benchmark-<topic-slug>.md`.
- **Step 1c — Ideation**: Using the market research brief + current state review + phase brief, produce categorized feature suggestions. Each idea gets:
  - **Importance** (`high|medium|low`) — scored on: (1) user impact breadth (how many users benefit), (2) friction reduction (how much pain it removes), (3) competitive parity (do competitors all have this?). State which factors drive the rating.
  - **Source**: `Market Research`, `Documentation`, `Current Gap`, or `New`
  - **Triage**: `selected|rejected|postponed` with rationale
- Compact inline format per idea: Importance (with scoring rationale), Source, Decision, Description, Rationale
- Open questions: present via `AskUserQuestion` tool (see integration rules in main SKILL.md)
- Atomic commit on completion
- Run `pw.sh set-step-status --phase N --step ideas --status complete`

**DO NOT:**

- Skip current-state review (Step 1a). You cannot ideate without knowing what exists.
- Include ideas without importance scoring. Every idea needs the 3-factor rating.
- Proceed with more than 3 unresolved open questions.
