---
name: pew-init
description: Initialize or update PEW configuration for a project. Explores the repo, detects tech stack, verification commands, and project structure, then writes pew.yaml.
user-invocable: true
---

# PEW Project Initialization

Initialize or update this project's PEW configuration by creating/updating `pew.yaml`.

## Pre-check

Run `bash ${CLAUDE_PLUGIN_ROOT}/scripts/pw.sh validate-config`.

- If `configured` is `false` → **fresh init**: create `pew.yaml` from scratch.
- If `configured` is `true` → **update mode**: read the existing `pew.yaml` first, then re-explore the repo to detect changes. Present only fields where the detected value differs from the current config. Do not overwrite user-customized fields unless they confirm.

### Update Mode Merge Rules

When updating an existing config:

1. **Read existing pew.yaml** into memory as `existing`
2. **Re-run detection** (Steps 1-2 below) to produce `detected`
3. **Compare field by field**:
   - Field exists in `existing` and `detected` with same value → keep, don't show
   - Field exists in `existing` and `detected` with different value → show diff, ask user which to keep
   - Field exists in `detected` but not in `existing` → new field, suggest adding with detected value
   - Field exists in `existing` but not in `detected` → user-customized, keep without question
4. **New config fields** (added in recent PEW versions): always suggest adding with defaults. Currently: `paths.audit_test`, `paths.audit_ux`, `council.*`, `approval_gates.*`.
5. **Never silently remove fields** — if a field was in the old config, keep it even if detection can't find it anymore.

## Step 1: Explore the project

Read the config reference at `${CLAUDE_PLUGIN_ROOT}/pew.yaml.example` to understand all available fields.

Then explore the repo to detect project settings. Check these sources (read whichever exist):

### Project identity
- `package.json` → name, description
- `go.mod` → module name
- `pyproject.toml` / `setup.py` → name, description
- `Cargo.toml` → package name, description
- `README.md` → project description (first paragraph)
- Fall back to directory name if nothing found

### Tech stack
- `package.json` dependencies → React, Vue, Angular, NestJS, Express, Tailwind, Prisma, etc.
- `go.mod` → Go
- `pyproject.toml` dependencies → Django, Flask, FastAPI, etc.
- `Cargo.toml` → Rust
- Config files: `tsconfig.json` (TypeScript), `tailwind.config.*` (Tailwind), `vite.config.*` (Vite)
- `docker-compose.*` → scan for database services (postgres, mysql, redis)
- Summarize as comma-separated string for `stack.description`

### Verification commands
- `package.json` scripts → look for `lint`, `typecheck`/`type-check`, `test`, combine with `&&` for `commands.verify`
- `package.json` scripts → look for `test:e2e`, `e2e`, `cypress`, `playwright` for `commands.e2e`
- `Makefile` targets → `lint`, `test`, `check`, `verify`, `e2e`
- CI configs (`.github/workflows/*.yml`, `.gitlab-ci.yml`) → extract test/lint commands
- If no single verify command exists, propose building one from individual commands found
- If no test runner is configured at all, note this as a gap for the user

### Frontend structure (if frontend stack detected)
- Find source directory containing `.tsx`/`.jsx`/`.vue` files → `stack.frontend_src`
- Find `components/` directories → `stack.component_paths`
- Detect component library install commands (shadcn, radix, etc.) → `stack.install_commands`
- Find dev server command → `product_review.start_command`
- Detect dev server port from `vite.config.*`, `webpack.config.*`, or package.json scripts → `product_review.app_url` (default: `http://localhost:5173`)

### Documentation & conventions
- Look for `docs/`, `guidelines/`, `playbooks/` directories → `paths.guidelines`
- Look for `CONVENTIONS.md`, `ADR.md`, `DECISIONS.md`, `.cursor/rules`, `.cursorrules` → `conventions_file`

### Existing PEW structure (update mode)
- Check if `phases/` directory exists with phase subdirectories
- Check if `phases/audit/test/` or `phases/audit/ux/` exist (from prior audits)
- Check if any phase tracker YAML exists at a non-default path

## Step 2: Present findings to user

Use `AskUserQuestion` to present the detected configuration. Show:

### Always show
- Project name and description
- Detected tech stack (`stack.description`)
- Verification commands (or gaps found)
- Frontend structure (if applicable): `frontend_src`, `component_paths`, `install_commands`

### Always ask
- **Competitors** — cannot be auto-detected, ask the user to list 2-3 competitors (or skip)
- **Verify command** — confirm the assembled command is correct

### Show if non-default or detectable
- **Paths** — only show if the project uses non-standard paths (not `phases/`)
- **Audit paths** — mention `paths.audit_test` and `paths.audit_ux` exist with defaults `phases/audit/test` and `phases/audit/ux`. Only ask to change if the user has a different preference.
- **Product review** — if a dev server was detected, confirm `app_url` and `start_command`
- **Conventions file** — if found, confirm the path

### Mention as available (don't ask unless user wants to customize)
- **Council settings** — enabled by default, max 15 findings per expert. Mention: "Council review is enabled by default. You can customize expert behavior, finding limits, and skip tags in pew.yaml later."
- **Approval gates** — both enabled by default. Mention: "Approval gates are on for BUILD and CLOSE steps. Disable in pew.yaml if you prefer uninterrupted auto mode."
- **Product review** — enabled by default for frontend phases. Mention: "Browser-based product review is on for frontend phases. Requires Chrome MCP or Playwright MCP."
- **Phase sizing** — mention available sizes: "Phases support sizes: `large` (all steps), `medium` (skip IDEAS), `small` (skip IDEAS+RESEARCH), `vibe` (build first, document post-hoc)."

### In update mode
Only present fields where the detected value differs from the current config. Show what changed and why. Also suggest adding any new config fields that were added in recent PEW versions.

## Step 3: Write pew.yaml

Write the confirmed config to `pew.yaml` at the repo root.

### Field inclusion rules
- **Always include**: `project.name`, `project.description`, `paths.tracker`, `commands.verify`
- **Include if non-empty**: `stack.description`, `stack.frontend_src`, `stack.component_paths`, `stack.install_commands`, `commands.e2e`, `competitors`, `conventions_file`, `paths.guidelines`
- **Include if non-default**: `paths.plan`, `paths.phases`, `paths.research`, `paths.audit_test`, `paths.audit_ux`, `product_review.*`, `council.*`, `approval_gates.*`
- **Omit if default**: Fields that match DEFAULT_CONFIG defaults don't need to be in the file — the deep-merge handles them. This keeps pew.yaml minimal.

### Comments
Add YAML comments for sections the user might want to customize later:
```yaml
# --- Phase Sizing ---
# Sizes: large (all steps), medium (skip IDEAS), small (skip IDEAS+RESEARCH),
# vibe (build first, document post-hoc — use /pew-vibe command)

# --- Council Review ---
# council:
#   enabled: true            # set false to skip council review
#   max_findings_per_expert: 15
#   skip_tags: [docs-only]   # phases with these tags skip council

# --- Approval Gates ---
# approval_gates:
#   before_build: true       # require approval before BUILD step
#   before_close: true       # require approval before CLOSE step
```

## Step 4: Validate

Run `bash ${CLAUDE_PLUGIN_ROOT}/scripts/pw.sh validate-config` to verify the written config. If there are errors, fix them. If there are warnings, inform the user.

## Step 5: Create phases directory

If `phases/` directory doesn't exist, create it along with the tracker file:
```bash
mkdir -p phases
echo "phases: []" > phases/phase-tracker.yaml
```

## Step 6: Commit

Commit `pew.yaml` and the phases directory with an appropriate message:
- Fresh init: `chore: initialize PEW configuration`
- Update: `chore: update PEW configuration`

Tell the user: "PEW is configured. Run `/pew-build` and say `start phase 1` to begin, or `/pew-vibe` for build-first mode."
