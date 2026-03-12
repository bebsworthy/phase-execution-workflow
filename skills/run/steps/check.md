# Step 7: CHECK + CLOSE

- Run `pw.sh set-step-status --phase N --step check --status in_progress`
- **Step 7a — Council Review**:
  1. **SKIP CHECK**: If `config.council.enabled` is `false`, or phase tags match any entry in `config.council.skip_tags`, skip to 7b.
  2. **SCOPE**: Run `pw.sh phase-diff --phase N` to get changed files.
  3. **CATEGORIZE** files into domains:
     - `security`: auth, middleware, env, API routes, validation, webhooks
     - `architecture`: module boundaries, shared utilities, barrel exports, services
     - `testing`: `*.test.*`, `*.spec.*`, `*.e2e-spec.*` + their source files
     - `test-quality`: same files as testing (reviews test implementation quality)
     - `frontend`: components, hooks, pages, styles (if expert active)
     - `backend`: controllers, services, modules, migrations (if expert active)
  4. **DETERMINE ACTIVE EXPERTS**:
     - Always active: `council-security`, `council-architecture`, `council-testing`, `council-test-quality`
     - Conditional: `council-frontend` (if phase has `frontend` tag or `config.stack.frontend_src` is set)
     - Conditional: `council-backend` (if phase has `backend` tag or server-side files are in the diff)
     - Conditional: `product-reviewer` (if phase has `frontend` tag and `config.product_review.enabled` is true) — dispatched in Step 7b, not 7a
  5. **RESOLVE REVIEW PROFILES**: Run `pw.sh resolve-profiles --profiles-dir ${CLAUDE_PLUGIN_ROOT}/review-profiles/ --files <comma-separated-phase-diff-files> --summary`. This auto-matches profiles by file extensions/keywords, resolves extends chains, and outputs condensed summaries (headers + rule names, no code blocks). The full profile path is included in each summary header so experts can read full details when needed.
  6. **BUILD ARTIFACT INDEX**: Run `pw.sh extract-ids --phase N`. This outputs a compact JSON index of all FC-nnn (from BRD) and T-nnn (from SPEC) with line numbers and summaries. Pass this index to experts instead of full BRD/SPEC content — experts can `Read` specific line ranges when writing findings that need full context.
  7. **DISPATCH** all active experts **in parallel** using the Agent tool. Each expert receives:
     - Phase number, title, tags
     - Domain-specific file list (from step 3)
     - Artifact index JSON (from step 6) — NOT full BRD/SPEC content
     - BRD.md and SPEC.md file paths (for targeted reads when needed)
     - Condensed review profile summaries (from step 5)
     - Conventions file path (if configured)
     - Reference doc path (if configured per expert in `config.council.experts`)
  8. **COLLECT** JSON findings from each expert. After collecting each expert's response, verify it contains valid JSON with `expert` (string) and `findings` (array) fields. If an expert returns malformed output, log which expert failed and exclude their findings from the merge — do not retry or block the pipeline. Note the exclusion in COUNCIL-REVIEW.md's Dedup Notes section.
  9. **MERGE and DEDUPLICATE** (dedup key: file + line range):
     - Same file + same line range + same issue → keep the domain-specific expert's finding (higher priority), drop the generalist's
     - Same file + same line range + different angle → keep both, add `related_to` cross-reference between finding IDs
     - Contradicting findings (e.g., one says "add validation" and another says "trust the boundary") → keep both, flag for user resolution in Dedup Notes
     - Convention-covered patterns → silently drop, note in Dedup Notes
  10. **PERSIST** merged findings to `{phase-dir}/COUNCIL-REVIEW.md`. Format: date, phase number/title, list of active experts, then findings grouped by domain. Each finding includes: ID, severity, file, issue description, fix guidance, artifact_refs (array of FC-nnn/T-nnn IDs). Add a "Dedup Notes" section for any merged or dropped findings.
  11. Add merged council findings to the CHECK issue list alongside 7b results.
- **Step 7b — Verify**:
  - Run `{config.commands.verify}` (lint + typecheck + test:all); for frontend phases also run `{config.commands.e2e}`
  - Code quality check: review test files for empty assertions, `.toBeDefined()`-only tests, mocking the subject under test
  - Spawn alignment checker (see `agents/alignment-checker.md`): verify each FC-nnn has implementation, each T-nnn has test
  - If phase has `frontend` tag and `config.product_review.enabled` is true: spawn `product-reviewer` agent (see `agents/product-reviewer.md`). Provide BRD.md path, `config.product_review.app_url`, and `config.product_review.start_command`. The product reviewer uses Chrome MCP or Playwright MCP to navigate the running app and validate each FC-nnn and E2E test flow. Merge PR-nnn findings into the issue list with the same severity classification. If browser tools are unavailable, the review is skipped with a warning — add a finding to the issue list: `PR-SKIP | P2 | "Browser testing unavailable — manual validation required before CLOSE"`. The approval gate (Step 7d) must surface this to the user.
  - Reconcile documentation drift (architecture, domain, API, developer docs)
  - Classify each issue by severity:
    - **P1 (Critical)**: Broken functionality, test failures, type errors, security issues. Must fix before close.
    - **P2 (Important)**: Code quality issues, missing test coverage, alignment gaps. Should fix; may defer with rationale.
    - **P3 (Minor)**: Style issues, documentation drift, non-blocking warnings. Fix if time allows; defer freely.
  - Collect all issues (council findings + verify results) into a single list with category and severity: `council | lint | type | test | quality | alignment | docs` × `P1 | P2 | P3`
- **Step 7c — Fix** (if any issues found):
  - Fix cycle priority: resolve all P1 first, then P2, then P3.
  - For each issue, classify as `fix | descope | defer`
  - `fix`: make the change, atomic commit
  - `descope`: update SPEC.md/PLAN.md with rationale
  - `defer`: add carry-forward note to RETRO.md
  - Update COUNCIL-REVIEW.md — mark each finding with its disposition (`fixed`/`deferred`/`descoped`) and the commit hash or rationale.
  - After all fixes applied, restart from Step 7b (council review does not re-run on fix cycles). Max 3 fix cycles before escalating to user.
- **Step 7d — Close** (all P1 checks green):
  - **Approval gate**: If `config.approval_gates.before_close` is true, present a close summary via `AskUserQuestion`: verification results, link to COUNCIL-REVIEW.md, deferred P2/P3 items. Options: "Approve CLOSE" / "Request changes". Fires in both manual and auto mode.
  - Finalize COUNCIL-REVIEW.md — add a summary header with counts: total findings, fixed, deferred, descoped.
  - Record verification evidence in PLAN.md
  - Close every test ID with `passed|failed|descoped` + evidence
  - If council review surfaced recurring patterns worth codifying, offer to add them to the conventions file
  - Optional: create RETRO.md (3-5 went well, 3-5 improve, carry-forwards, max 30 lines)
  - Run `pw.sh set-step-status --phase N --step check --status complete` (auto-closes phase)

**DO NOT:**

- Close with any P1 issues unresolved.
- Skip the alignment checker agent.
- Mark tests as passing without running them.
- Skip dispatching a council expert because its domain seems irrelevant — let the expert decide.
- Include code snippets in the merged council findings.
- Auto-fix council findings without user review.
