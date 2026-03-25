---
name: pew-test-audit
description: >
  Shared anti-pattern taxonomy, severity scales, and output format for test audit agents.
  This skill is preloaded by all test-audit-* agents to ensure consistent evaluation criteria.
user-invocable: true
---

# LLM-Generated Test Suite Audit Framework

## Purpose

This framework powers a multi-phase audit of test suites, with a focus on systemic quality issues introduced by LLM coding agents (Claude Code, Codex, Gemini, Cursor, etc.). It goes beyond coverage metrics to evaluate whether tests actually protect against regressions.

Every finding must answer: "What production bug could ship because this test exists (or doesn't)?"

## Tone & Approach

- Direct and precise. Do not soften findings.
- Every finding must cite the specific anti-pattern and include a concrete fix.
- **Call out strengths**: Note well-written tests, not just problems.
- Prioritize by business risk — payment, auth, and data integrity code first.

---

## Anti-Pattern Taxonomy

| # | Anti-Pattern | Description | Detection Signal | Fix |
|---|-------------|-------------|-----------------|-----|
| 1 | Tautological Test | Mirrors implementation logic | Same computation in test and source | Assert against specification |
| 2 | Mock Echo | Asserts mock returns what it was told to return | `mock.returns(X)` → `expect(result).toBe(X)` | Remove mock, test real logic |
| 3 | Framework Test | Tests the framework, not the app | "renders without crashing", "should create" | Delete |
| 4 | Secret Catcher | No explicit assertions | No `expect()` in test body | Add meaningful assertions or delete |
| 5 | Line Hitter | Executes code without verifying output | High coverage, low mutation score | Add assertions that catch mutations |
| 6 | Over-Mocking | Everything mocked, nothing real tested | Mock count > assertion count | Replace mocks with fakes |
| 7 | Implementation Coupling | Tests break on refactoring | Tests reference private methods/state | Test at behavioral boundaries |
| 8 | Happy-Path Only | No error/edge case tests | All tests use valid, simple inputs | Add negative and boundary tests |
| 9 | Copy-Paste Tests | Duplicate tests with different literals | Near-identical test bodies | Parameterize |
| 10 | Snapshot Abuse | Huge snapshots that break on cosmetic changes | Snapshot files > 100 lines | Replace with targeted assertions |
| 11 | Dodger | Tests side effects, ignores core behavior | Core function untested | Rewrite to test primary behavior |
| 12 | Wrong Framework | Uses wrong test runner/library | Mixed imports (jest + mocha) | Standardize |
| 13 | Flaky Test | Non-deterministic results | Different results across runs | Fix timing, state, dependencies |
| 14 | Excessive Setup | 100 lines of setup for 1 assertion | Setup:assertion ratio > 5:1 | Extract factories, reduce scope |

---

## Severity Scale

| Severity | Meaning | Action |
|----------|---------|--------|
| **Critical** | Test actively hides bugs or creates false confidence | Fix immediately |
| **High** | Test provides no regression protection | Fix this sprint |
| **Medium** | Test is fragile, expensive to maintain, or poorly scoped | Fix next sprint |
| **Low** | Test is suboptimal but provides some value | Fix when convenient |

---

## Test Verdict Classification

For each test in the suite, agents assign one verdict:

| Verdict | Meaning |
|---------|---------|
| ✅ KEEP | Valuable, well-written test |
| 🔧 REFACTOR | Has value but needs improvement |
| 🗑️ DELETE | Zero value, pure noise, or actively harmful |
| 📝 REWRITE | The scenario is valuable but the implementation is wrong |
| ➕ MISSING | A test that should exist but doesn't |

---

## Remediation Tiers

| Tier | Timeframe | Focus |
|------|-----------|-------|
| **Tier 1 — Immediate** | This sprint | Delete zero-value tests, fix flaky tests, add missing tests for critical paths |
| **Tier 2 — Short Term** | Next 2 sprints | Refactor tautological tests, reduce mocking, add negative/error-path tests |
| **Tier 3 — Medium Term** | Next quarter | Address implementation coupling, parameterize duplicates, improve naming |
| **Tier 4 — Ongoing** | Continuous | Snapshot reduction, contract tests, mutation testing in CI |

---

## LLM Test Generation Rules

These rules should be included in project CLAUDE.md / .cursorrules to prevent future anti-patterns:

1. NEVER generate a test that merely checks the code "works as written." Every test must verify behavior against a SPECIFICATION or REQUIREMENT.
2. NEVER mock internal modules. Only mock: HTTP clients, databases, file system, clock, third-party SDKs.
3. For every happy-path test, generate at least one error-path test and one boundary-condition test for the same function.
4. Test names MUST describe business behavior: GOOD: "expired session token returns 401 and clears cookie" BAD: "should call authService.validate"
5. Maximum 3 mocks per test. If you need more, you're testing at the wrong level.
6. NEVER generate tests that verify: a component renders without crashing (framework test), a mock was called (mock test), a constructor initializes properties (trivial test).
7. Every test must have at least one explicit assertion on observable output or side effect. No assertion-free tests.
8. Before generating tests, read the existing test patterns in the project. Match the existing style, runner, assertion library, and naming convention.
9. After generating tests, mentally mutate the source code (change an operator, swap a condition) and verify your tests would catch it.
10. Maximum 10 tests per source file unless the source file contains complex branching logic. Quality over quantity.

---

## AI-Generated Test Review Checklist

When reviewing tests produced by any LLM agent:

- [ ] Is this test tautological? (Does it just mirror the implementation?)
- [ ] Could this test fail? (Try mentally mutating the code under test)
- [ ] Does every mock serve a purpose? (Could any mock be removed?)
- [ ] Is the test testing YOUR code or the FRAMEWORK's code?
- [ ] Does the test name describe a behavior a product manager would understand?
- [ ] Is there at least one negative/error test per feature?
- [ ] Are assertion values derived from requirements, not from the code?

---

## Finding Report Format

Each agent outputs findings in this structure:

```markdown
## Findings

### [SEVERITY] Finding title

- **File**: path/to/test-file
- **Test**: test name or describe block
- **Anti-pattern**: #N from taxonomy
- **Lines**: L42-L58
- **Issue**: What's wrong
- **Evidence**: The specific code showing the problem
- **Fix**: How to fix it
- **Business risk**: What bug could ship because of this
```

---

## File-Saving Instructions

1. Write your complete output to your designated file under `{output_dir}/`.
2. Do not write to any other agent's file.
3. Signal completion with: `[test-audit-<name>] COMPLETE ✓ — saved to {output_dir}/<filename>`
