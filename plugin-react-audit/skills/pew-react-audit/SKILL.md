---
name: pew-react-audit
description: >
  Shared code smell taxonomy, severity scales, and output format for code audit agents.
  This skill is preloaded by all react-audit-* agents to ensure consistent evaluation criteria.
user-invocable: true
---

# React/TypeScript Code Quality Audit Framework

## Purpose

This framework powers a multi-phase audit of React/TypeScript applications, covering code patterns, security, duplication, complexity, and technical debt. It goes beyond linting to evaluate architectural health, maintainability, and production risk.

Empirical research shows LLM-generated code contains **65% more code smells** than human-written code (arxiv:2510.03029), with **dead code comprising up to 42% of all issues** (arxiv:2508.14727), **code duplication growing 4x** since AI adoption (GitClear 2025), and **refactoring activity collapsing from 25% to under 10%** of changed lines. This taxonomy is calibrated to catch these systemic patterns.

Every finding must answer: "What concrete harm does this cause -- bugs, performance, security, or developer velocity?"

## Tone & Approach

- Direct and precise. Do not soften findings.
- Every finding must cite a specific code smell and include an actionable fix.
- **Call out strengths**: Note well-structured code, not just problems.
- Prioritize by business risk -- auth, payment, and data integrity code first.

---

## Code Smell Taxonomy

### A. Type Safety Erosion

LLMs bypass type systems with confident-looking escape hatches. Research shows AI code has significantly higher encapsulation violations (+138% vs human) and type-related defects.

| # | Smell | Detection Signal | Fix | Business Risk |
|---|-------|-----------------|-----|---------------|
| 1 | Any Escape | `any` on API boundaries, function params, return types, or generics. Includes `Record<string, any>`, `as any`, and untyped `catch(e)` | Use proper types, `unknown` with type guards, or generics. Type `catch` as `unknown` | Type errors propagate silently through the codebase and reach production |
| 2 | Type Assertion Abuse | `as` casts bypassing checks instead of narrowing. Chained assertions (`as unknown as T`). Assertions on API responses instead of runtime validation | Use type guards, discriminated unions, Zod schemas at boundaries | Runtime type mismatches cause crashes in production paths the assertion "promised" were safe |
| 3 | Non-null Assertion | `!` operator suppressing null/undefined where the value could genuinely be absent | Add proper null checks, optional chaining, or refactor to guarantee presence | Null reference errors in production -- the `!` is a lie the compiler believes |
| 4 | Missing Strict Mode | `strict: false`, `noImplicitAny: false`, `strictNullChecks: false` in tsconfig | Enable `strict: true` and fix resulting errors incrementally | Entire classes of bugs (implicit any, null derefs, wrong `this`) go undetected at compile time |

### B. React Anti-Patterns

LLMs frequently generate React code that "works on first render" but breaks under real-world conditions: re-renders, unmounts, error states, and concurrent updates.

| # | Smell | Detection Signal | Fix | Business Risk |
|---|-------|-----------------|-----|---------------|
| 5 | Effect-Derived State | `useEffect` + `useState` to compute values derivable during render. `useEffect` to "sync" state from props | Compute inline during render, or `useMemo` for genuinely expensive calculations. Use the `key` pattern to reset state on prop change | Unnecessary re-render cascades, one-frame stale state visible to users, subtle bugs in concurrent mode |
| 6 | Missing Cleanup | Effects with `addEventListener`, `setInterval`, `setTimeout`, `subscribe`, or WebSocket connections without a cleanup return | Return a cleanup function that unsubscribes/clears/closes | Memory leaks compound per mount cycle. Ghost handlers fire on unmounted components, causing "setState on unmounted" errors or corrupt state |
| 7 | Unstable References | Object/array literals or inline `() => {}` in dependency arrays. `useMemo`/`useCallback` with constantly-changing deps that defeat the purpose | Extract to module scope, `useMemo`, or `useCallback` with stable deps | Infinite re-render loops that freeze the UI, or wasted renders that degrade performance on every interaction |
| 8 | Component Bloat | Single component >200 lines mixing rendering, data fetching, state management, and event handling. >10 hooks or >8 props | Extract sub-components, custom hooks, and utility functions by concern | Impossible to test in isolation, merge conflicts on every PR, changes to one concern risk breaking another |
| 9 | Missing Error Boundary | Feature sections, route-level components, or async data-dependent areas without `<ErrorBoundary>` wrapping | Wrap feature sections with error boundary + fallback UI | A single render error in one component crashes the entire application -- users see a white screen |

### C. Security Vulnerabilities

Research shows 37.6% increase in critical vulnerabilities after just 5 iterations of AI refinement (IEEE-ISTAS 2025). Hard-coded credentials appear in 10-30% of AI-generated code (arxiv:2508.14727).

| # | Smell | Detection Signal | Fix | Business Risk |
|---|-------|-----------------|-----|---------------|
| 10 | XSS Vector | `dangerouslySetInnerHTML`, `innerHTML`, `outerHTML`, `document.write` with user-controlled data. `eval()`, `new Function()`, string args in `setTimeout` | Sanitize with DOMPurify, use safe rendering, avoid `eval` entirely | Attacker injects arbitrary scripts that steal sessions, exfiltrate data, or impersonate users |
| 11 | Insecure Storage | Tokens/secrets in `localStorage`/`sessionStorage` (XSS-accessible). API keys hardcoded in source. Secrets in `VITE_`/`NEXT_PUBLIC_` env vars (bundled into client). Sensitive data in URL params | Use `httpOnly`/`Secure`/`SameSite` cookies for tokens. Server-side env vars. Strip sensitive data from URLs | Token theft via any XSS vector. Credentials in git history forever. Secrets in browser history and server logs |
| 12 | Missing Auth Guard | Unprotected routes, API calls without auth headers, client-only authorization without server enforcement, missing RBAC/ownership checks | Route guards, auth middleware, server-side permission checks on every protected endpoint | Unauthorized access to data and operations. Privilege escalation via direct API calls bypassing UI restrictions |
| 13 | Input Validation Gap | User input flowing to APIs, queries, file operations, or rendering without schema validation. Missing rate limiting on auth-sensitive forms | Zod/yup schemas at every system boundary. Rate limiting on login/registration/password-reset | Injection attacks, data corruption, brute-force credential attacks |

### D. Duplication & Redundancy

GitClear (2025, 211M lines): code clones grew 4x during 2024. Copy-paste lines now exceed moved/refactored lines for the first time. LLMs generate fresh implementations instead of discovering and reusing existing abstractions.

| # | Smell | Detection Signal | Fix | Business Risk |
|---|-------|-----------------|-----|---------------|
| 14 | Copy-Paste Proliferation | Near-identical logic blocks in 3+ locations: same API call pattern, same form validation, same error handling, same conditional rendering. Parameterized only by literals | Extract shared hook, utility function, or component. Parameterize the variation | A bug fix applied to one copy is missed in the others. Behavior diverges silently across features |
| 15 | Redundant Implementation | Multiple functions/hooks/components solving the same problem in different modules: date formatters, HTTP wrappers, permission checkers, toast helpers | Consolidate into a single shared module with a clear interface. Delete the duplicates | Inconsistent behavior for the same operation across the app. Maintenance cost multiplied by copy count |
| 16 | Duplicate Type Definitions | Interfaces/types with >70% field overlap defined in separate files. Same API response shape typed independently per feature | Single source-of-truth type, derived/extended where variants are needed | Schema changes require hunting down every copy. Missed copies cause runtime type mismatches |

### E. Modularity & Complexity

AI-generated code shows significantly higher modularity violations: god classes, Law of Demeter breaches, and excessive public exposure (arxiv:2510.03029). SlopCodeBench confirms "overly verbose or defensive code" that erodes structure across iterations.

| # | Smell | Detection Signal | Fix | Business Risk |
|---|-------|-----------------|-----|---------------|
| 17 | God Module | File >300 lines mixing UI rendering, business logic, data fetching, state management, and event handling. High import count + high export count + many responsibilities | Split by concern: presentation component, data hook, business logic module, types file | Merge conflicts on every PR, impossible to reason about side effects, changes to one concern risk breaking another |
| 18 | Dead Code | Unused exports never imported anywhere. Unreachable branches behind impossible conditions. Commented-out code blocks left "just in case." Unused dependencies in `package.json`. Orphaned files not imported by any module | Delete it -- git has history. Run `knip` or similar to automate detection | Misleads readers into thinking code is active. Inflates bundle size. Triggers false positives in searches. Dead code is 14-42% of all AI code smells (arxiv:2508.14727) |
| 19 | Excessive Complexity | Deeply nested conditionals (>3 levels). Functions >50 lines mixing branching and sequential logic. >5 early returns. Long switch/case (>8 cases) without table-driven approach | Flatten with early returns, extract helper functions, use lookup tables or polymorphism | High cyclomatic complexity correlates directly with bug density. Hard to review, hard to test, hard to modify without introducing regressions |
| 20 | Over-Engineering | Abstraction layers with single implementations. Factory/strategy patterns with one variant. Wrapper functions that delegate without adding logic. Generic utilities parameterized for flexibility never exercised. Redux/Zustand for state that could be a simple `useState` | Inline the abstraction. Add indirection only when a second use case actually arrives. Replace global state with local state where appropriate | Slows navigation ("where does this actually happen?"). Obscures intent behind ceremony. Each layer is a place where bugs can hide |
| 21 | Encapsulation Breach | Internal module details exported and imported by other modules (bypassing public API). Components importing domain types or SDK clients directly. Leaky abstractions exposing implementation details through their interface | Define explicit public APIs via `index.ts`. Hide internals. Depend on abstractions, not concretions | Tight coupling means changing one module's internals breaks distant consumers. Refactoring becomes "all-or-nothing" |
| 22 | Hidden Mutation | Functions with pure-sounding names that modify external state. In-place array/object mutations (`.sort()`, `.splice()`, direct property assignment) disguised as transformations. Side effects in render functions, selectors, or reducers | Make mutation explicit: return new objects, use `structuredClone`, rename to signal intent (`updateX`, `mutateX`) | Bugs that only manifest in specific call orders. React state bugs when reference identity doesn't change after mutation |

### F. Incompleteness & Magic Values

LLMs generate code with "complete conviction -- including bugs or nonsense" (Addy Osmani). Stubs and placeholders get merged as if finished. Magic literals scatter meaning across the codebase.

| # | Smell | Detection Signal | Fix | Business Risk |
|---|-------|-----------------|-----|---------------|
| 23 | Incomplete Implementation | `TODO`/`FIXME`/`HACK` comments left in production code. Empty `catch` blocks that swallow errors silently. Missing `default` cases in switch/exhaustive checks. Placeholder return values (`return null`, `return []`, `return {}`) in non-trivial functions | Implement the missing logic or remove the dead path. Add error reporting in catch blocks. Use TypeScript `never` for exhaustive switches | Silent failures in production. Errors swallowed without logging mean bugs are invisible until a user reports data loss |
| 24 | Magic Values | Hardcoded numeric literals (`setTimeout(3000)`, `if (status === 2)`), string literals used as enum stand-ins (`role === "admin"`), repeated threshold values without named constants | Extract to named constants, enums, or config. Use string union types for known sets | Meaning is opaque -- "what does 3000 mean here?" Changes require finding every instance. Typos in string literals cause silent bugs |

### G. Technical Debt & Staleness

AI agents cargo-cult patterns from training data that may be years out of date. Research shows 5.2% of AI-suggested packages don't exist ("slopsquatting"), and deprecated APIs are confidently used.

| # | Smell | Detection Signal | Fix | Business Risk |
|---|-------|-----------------|-----|---------------|
| 25 | Outdated Pattern | Class components, legacy lifecycle methods (`componentDidMount`, `UNSAFE_*`), old Context API (`contextType`), `defaultProps`/`propTypes` on function components, `ReactDOM.render` instead of `createRoot`, Redux `connect()` HOC, hand-rolled data fetching (`useEffect` + `useState` + loading/error flags) | Migrate incrementally: function components + hooks, `createRoot`, TanStack Query/SWR, Redux Toolkit or Zustand | Blocks React upgrades. Confuses developers who learned modern React. Two mental models in one codebase increases cognitive load and bug surface |
| 26 | Config Debt | `strict: false` in tsconfig. Missing `noUncheckedIndexedAccess`. Outdated ESLint config (`.eslintrc` vs flat config). Missing `eslint-plugin-react-hooks`. No import sorting. No code splitting (`React.lazy`). Barrel re-exports defeating tree shaking | Update configs to current best practices. Enable strict flags incrementally. Add missing plugins | Slow builds, inconsistent rule enforcement, inflated bundles, classes of bugs that linting would have caught for free |
| 27 | Dependency Rot | Dependencies >2 majors behind. Deprecated packages still in use. Libraries with widely-adopted modern replacements (`moment` -> `date-fns`, `lodash` -> native/`lodash-es`, `classnames` -> `clsx`). Packages in `package.json` not imported anywhere | Update, replace, or remove. Prefer smaller, maintained alternatives. Audit with `knip` + `npm audit` | Known CVEs in outdated deps. Deprecated APIs removed in next major. Unused deps expand install time and attack surface |
| 28 | Cargo-Culted Infrastructure | Technology choices disproportionate to the problem: Redis for a todo list, Kubernetes for a single-service app, GraphQL for one consumer, WebSockets for data that changes hourly. Patterns copied from training data without evaluating fit | Right-size the solution: local state before global, REST before GraphQL, polling before WebSockets, SQLite before Postgres before distributed cache | Operational complexity without operational need. Every dependency is a maintenance burden, a failure mode, and a hiring requirement |

---

## Severity Scale

| Severity | Meaning | Action |
|----------|---------|--------|
| **Critical** | Security vulnerability, data loss risk, or production crash | Fix immediately |
| **High** | Bug risk, significant performance impact, or developer velocity blocker | Fix this sprint |
| **Medium** | Code smell, maintainability concern, or minor performance impact | Fix next sprint |
| **Low** | Style issue, minor debt, or optimization opportunity | Fix when convenient |

---

## Remediation Tiers

| Tier | Timeframe | Focus |
|------|-----------|-------|
| **Tier 1 -- Immediate** | This sprint | Security fixes, critical bugs, dead code removal |
| **Tier 2 -- Short Term** | Next 2 sprints | Pattern fixes, duplication consolidation, missing error handling |
| **Tier 3 -- Medium Term** | Next quarter | Architecture improvements, modernization, complexity reduction |
| **Tier 4 -- Ongoing** | Continuous | Dependency updates, config improvements, tooling adoption |

---

## Finding Report Format

Each agent outputs findings in this structure:

```markdown
## Findings

### [SEVERITY] Finding title

- **File**: path/to/file.ts
- **Lines**: L42-L58
- **Category**: #N from taxonomy
- **Issue**: What is wrong
- **Evidence**: The specific code pattern showing the problem
- **Impact**: Concrete harm (bug risk, performance, security, velocity)
- **Fix**: How to fix it -- specific, actionable guidance
- **Effort**: S (< 1 hour) / M (hours) / L (days)
```

---

## File-Saving Instructions

1. Write your complete output to your designated file under `{output_dir}/`.
2. Do not write to any other agent's file.
3. Signal completion with: `[react-audit-<name>] COMPLETE ✓ -- saved to {output_dir}/<filename>`
