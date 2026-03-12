---
name: init
description: Initialize or update PEW configuration for a project. Explores the repo, detects tech stack, verification commands, and project structure, then writes pew.yaml.
user-invocable: true
---

# PEW Project Initialization

Initialize or update this project's PEW configuration by creating/updating `pew.yaml`.

## Pre-check

Run `bash ${CLAUDE_PLUGIN_ROOT}/scripts/pw.sh validate-config`.

- If `configured` is `false` → **fresh init**: create `pew.yaml` from scratch.
- If `configured` is `true` → **update mode**: read the existing `pew.yaml` first, then re-explore the repo to detect changes (new dependencies, renamed scripts, added test runners, structural changes). Present differences to the user and update `pew.yaml` with confirmed changes. Do not overwrite fields the user previously customized unless they confirm.

## Step 1: Explore the project

Read the config reference at `${CLAUDE_PLUGIN_ROOT}/pew.yaml.example` to understand all available fields.

Then explore the repo to detect project settings. Check these sources (read whichever exist):

**Project identity:**
- `package.json` → name, description
- `go.mod` → module name
- `pyproject.toml` / `setup.py` → name, description
- `Cargo.toml` → package name, description
- `README.md` → project description (first paragraph)
- Fall back to directory name if nothing found

**Tech stack:**
- `package.json` dependencies → React, Vue, Angular, NestJS, Express, Tailwind, Prisma, etc.
- `go.mod` → Go
- `pyproject.toml` dependencies → Django, Flask, FastAPI, etc.
- `Cargo.toml` → Rust
- Config files: `tsconfig.json` (TypeScript), `tailwind.config.*` (Tailwind), `vite.config.*` (Vite)
- `docker-compose.*` → scan for database services (postgres, mysql, redis)
- Summarize as comma-separated string for `stack.description`

**Verification commands:**
- `package.json` scripts → look for `lint`, `typecheck`/`type-check`, `test`, combine with `&&` for `commands.verify`
- `package.json` scripts → look for `test:e2e`, `e2e`, `cypress`, `playwright` for `commands.e2e`
- `Makefile` targets → `lint`, `test`, `check`, `verify`, `e2e`
- CI configs (`.github/workflows/*.yml`, `.gitlab-ci.yml`) → extract test/lint commands
- If no single verify command exists, propose building one from individual commands found
- If no test runner is configured at all, note this as a gap for the user

**Frontend structure** (if frontend stack detected):
- Find source directory containing `.tsx`/`.jsx`/`.vue` files → `stack.frontend_src`
- Find `components/` directories → `stack.component_paths`
- Find dev server command → `product_review.start_command`
- Detect dev server port from `vite.config.*` or package.json scripts → `product_review.app_url`

**Documentation & conventions:**
- Look for `docs/`, `guidelines/`, `playbooks/` directories → `paths.guidelines`
- Look for conventions, ADR, or decisions files → `conventions_file`

## Step 2: Present findings to user

Use `AskUserQuestion` to present the detected configuration. Show:
- Project name and description
- Detected tech stack
- Verification commands (or gaps found)
- Frontend structure (if applicable)
- Any fields that need manual input

Always ask about:
- **Competitors** — cannot be auto-detected, ask the user to list 2-3 competitors (or skip)
- **Verify command** — confirm the assembled command is correct

In **update mode**, only present fields where the detected value differs from the current config. Show what changed and why.

## Step 3: Write pew.yaml

Write the confirmed config to `pew.yaml` at the repo root. Use the path defaults from `pew.yaml.example` unless the project has a non-standard structure:
- `paths.tracker`: `phases/phase-tracker.yaml`
- `paths.plan`: `phases/implementation-plan.md`
- `paths.phases`: `phases`
- `paths.research`: `phases/research`

Only include fields with non-default values — keep the file minimal. Add YAML comments for sections the user might want to customize later.

## Step 4: Validate

Run `bash ${CLAUDE_PLUGIN_ROOT}/scripts/pw.sh validate-config` to verify the written config. If there are errors, fix them. If there are warnings, inform the user.

## Step 5: Commit

Commit `pew.yaml` with an appropriate message:
- Fresh init: `chore: initialize PEW configuration`
- Update: `chore: update PEW configuration`
