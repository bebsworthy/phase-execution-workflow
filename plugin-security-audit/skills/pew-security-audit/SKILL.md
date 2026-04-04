---
name: pew-security-audit
description: >
  Shared vulnerability taxonomy, severity scales, CWE mappings, and output format for security audit agents.
  This skill is preloaded by all security-audit-* agents to ensure consistent evaluation criteria.
user-invocable: true
---

# Application Security Audit Framework

## Purpose

This framework powers a multi-phase security audit of application codebases, with a focus on vulnerabilities detectable through static code review. It covers code-level security, authentication/authorization, supply chain, frontend, infrastructure, and secrets management.

Every finding must answer: "How could an attacker exploit this, and what would be the impact?"

## Tone & Approach

- Direct and precise. No FUD (fear, uncertainty, doubt).
- Every Critical/High finding MUST include a concrete **attack scenario**.
- **Call out security strengths**: Note existing security controls, good practices, and well-defended code paths — not just problems.
- Prioritize by **exploitability** — a directly exploitable vulnerability ranks higher than a theoretical risk.
- When in doubt about severity, consider: Can an unauthenticated attacker reach this? What's the blast radius?

---

## Vulnerability Taxonomy

### A. Injection & Input Handling

| # | Vulnerability | Detection Signal | CWE | Fix |
|---|--------------|-----------------|-----|-----|
| 1 | SQL Injection | String concatenation/interpolation in SQL queries | CWE-89 | Use parameterized queries / prepared statements |
| 2 | OS Command Injection | User input in exec/system/subprocess/spawn calls | CWE-78 | Use library APIs instead of shell commands; validate against allowlist |
| 3 | Cross-Site Scripting (XSS) | innerHTML, dangerouslySetInnerHTML, v-html, document.write with user data | CWE-79 | Use framework auto-escaping; sanitize with DOMPurify; set CSP |
| 4 | Path Traversal | User input in file paths without normalization/validation | CWE-22 | Normalize paths, validate against base directory, reject `..` sequences |
| 5 | Template Injection | User input rendered directly in server-side templates | CWE-94 | Never pass user input as template source; use sandboxed templates |
| 6 | NoSQL Injection | Unvalidated operators ($gt, $ne, $where) in MongoDB/similar queries | CWE-943 | Validate input types; reject object inputs where strings expected |
| 7 | Missing Input Validation | No schema validation at API boundaries (controllers, handlers) | CWE-20 | Add Zod/Joi/class-validator schemas at every entry point |

### B. Authentication & Access Control

| # | Vulnerability | Detection Signal | CWE | Fix |
|---|--------------|-----------------|-----|-----|
| 8 | Missing Authentication | Endpoints/routes without auth middleware or guards | CWE-306 | Add auth middleware; use deny-by-default pattern |
| 9 | Broken Authorization (IDOR) | Object lookups without ownership/permission checks | CWE-862/863 | Validate resource ownership against authenticated user |
| 10 | Privilege Escalation | Client-only role checks; no server enforcement of roles | CWE-269 | Enforce RBAC/ABAC server-side; never trust client role claims |
| 11 | Session Mismanagement | Missing HttpOnly/Secure/SameSite cookie flags; no expiry; no invalidation | CWE-613 | Set all cookie security flags; implement session expiry and logout invalidation |
| 12 | CSRF Gap | State-mutating endpoints without CSRF tokens or SameSite cookies | CWE-352 | Use SameSite=Lax/Strict cookies; add CSRF tokens for forms |

### C. Cryptographic Failures

| # | Vulnerability | Detection Signal | CWE | Fix |
|---|--------------|-----------------|-----|-----|
| 13 | Weak Hashing | MD5/SHA1 for passwords; unsalted hashes | CWE-328 | Use Argon2id/bcrypt/scrypt with proper parameters |
| 14 | Hardcoded Secrets | API keys, passwords, tokens, connection strings in source code | CWE-798 | Move to environment variables or secret manager; add pre-commit scanning |
| 15 | Insecure Randomness | Math.random/random module for security tokens, session IDs, OTPs | CWE-338 | Use crypto.randomBytes/secrets.token_urlsafe/crypto.getRandomValues |
| 16 | Weak Encryption | DES, RC4, ECB mode, static IVs, small key sizes, missing TLS | CWE-327 | Use AES-256-GCM with random IVs; enforce TLS 1.2+ |

### D. Data Exposure

| # | Vulnerability | Detection Signal | CWE | Fix |
|---|--------------|-----------------|-----|-----|
| 17 | Sensitive Data in Logs | PII, tokens, passwords, credit cards logged or in error messages | CWE-532 | Redact sensitive fields before logging; use structured logging |
| 18 | Insecure Client Storage | Tokens in localStorage; secrets in NEXT_PUBLIC_/VITE_ env vars | CWE-922 | Store tokens in HttpOnly cookies; never expose secrets to client bundle |
| 19 | Information Disclosure | Stack traces in production; verbose errors; server version headers | CWE-209 | Use generic error responses in production; remove server headers |

### E. Supply Chain & Configuration

| # | Vulnerability | Detection Signal | CWE | Fix |
|---|--------------|-----------------|-----|-----|
| 20 | Vulnerable Dependencies | Known CVEs in direct/transitive dependencies | CWE-1395 | Run npm audit/pip-audit; enable Dependabot/Renovate; pin versions |
| 21 | Lockfile Integrity Gap | Missing lockfile; `npm install` instead of `npm ci` in CI; unpinned deps | CWE-829 | Commit lockfiles; use `npm ci`/`pip install --require-hashes`; pin deps |
| 22 | Misconfigured Security Headers | Missing CSP, HSTS, X-Frame-Options, X-Content-Type-Options | CWE-693 | Add security headers via Helmet/middleware/proxy config |

### F. Infrastructure Security

| # | Vulnerability | Detection Signal | CWE | Fix |
|---|--------------|-----------------|-----|-----|
| 23 | Container Running as Root | Missing USER directive in Dockerfile; no security_opt in compose | CWE-250 | Add non-root USER; set read_only, no_new_privileges, cap_drop: ALL |
| 24 | Secrets in Build Layers | Secrets in Dockerfile ARG/ENV/COPY; secrets in docker-compose env | CWE-798 | Use Docker BuildKit secrets; use Docker/Compose secrets mounts |
| 25 | Database Misconfiguration | Default credentials; trust auth in pg_hba.conf; exposed ports; no SSL | CWE-1188 | Use scram-sha-256; restrict pg_hba.conf; bind to internal network; enforce SSL |

### G. Additional Vulnerability Classes

| # | Vulnerability | Detection Signal | CWE | Fix |
|---|--------------|-----------------|-----|-----|
| 26 | Server-Side Request Forgery (SSRF) | User input in outbound HTTP URLs without allowlist | CWE-918 | Validate URLs against domain allowlist; block private IP ranges |
| 27 | Unrestricted File Upload | File uploads without content-type validation, size limits, or filename sanitization | CWE-434 | Validate content by magic bytes; enforce size limits; randomize filenames |

---

## Severity Scale

| Severity | Meaning | Exploitability Qualifier | Action |
|----------|---------|-------------------------|--------|
| **Critical** | Directly exploitable vulnerability with high impact (data breach, RCE, auth bypass) | Attacker can exploit with no special access | Fix immediately |
| **High** | Exploitable vulnerability requiring some preconditions | Attacker needs authenticated access or specific conditions | Fix this sprint |
| **Medium** | Defense-in-depth gap that increases attack surface | Exploitable only in combination with another vulnerability | Fix next sprint |
| **Low** | Best-practice violation that does not directly enable an attack | No direct exploit path | Fix when convenient |
| **Informational** | Observation or recommendation that is not a vulnerability | No exploit path; defensive suggestion | Address at discretion |

**Tiebreaker**: When uncertain between two adjacent severities, apply the higher severity if an unauthenticated external attacker can reach the issue with publicly available information.

**Attack Scenario Requirement**: Every Critical and High finding MUST include an attack scenario in this format:

> "An attacker could **[action]** by **[method]**, resulting in **[impact]**."

Example: "An attacker could extract all user records by manipulating the `userId` parameter in `GET /api/users/:id`, resulting in mass PII exposure (IDOR, no ownership check)."

---

## Remediation Tiers

| Tier | Timeframe | Focus | Examples |
|------|-----------|-------|---------|
| **Tier 1 — Immediate** | This sprint | Active vulnerabilities with direct exploit paths | Remove hardcoded secrets, add parameterized queries, add missing auth guards, fix critical CVEs |
| **Tier 2 — Short Term** | Next 2 sprints | Defense gaps on critical paths | Add input validation schemas, migrate to bcrypt/argon2, add CSRF protection, move tokens to HttpOnly cookies |
| **Tier 3 — Medium Term** | Next quarter | Hardening and defense in depth | Implement CSP, add rate limiting, harden Docker configs, add structured security logging |
| **Tier 4 — Ongoing** | Continuous | Process and automation | Add SAST in CI, enable Dependabot, add pre-commit secret scanning, generate SBOM, security review checklist |

---

## Finding Report Format

Each agent outputs findings in this structure:

```markdown
## Findings

### [SEVERITY] Finding title

- **File**: path/to/file
- **Lines**: L42-L58
- **Vulnerability**: #N — Name (from taxonomy)
- **CWE**: CWE-XXX
- **Sub-project**: name (if mono-repo, omit for single projects)
- **Issue**: What is wrong
- **Attack scenario**: An attacker could X by Y, resulting in Z (required for Critical/High)
- **Evidence**: The specific code showing the problem
- **Fix**: How to fix it (with code example when possible)
- **Effort**: S / M / L
```

---

## Strengths Section

Every agent MUST include a `## Security Strengths` section noting existing security controls and good practices found. Examples:

- "Authentication middleware is consistently applied to all API routes"
- "All SQL queries use parameterized statements via the ORM"
- "CSP headers are properly configured with nonce-based script loading"

This ensures the audit is balanced and acknowledges existing defensive measures.

---

## Mono-Repo Handling

When auditing mono-repos with multiple sub-projects:

1. Read the inventory at `{output_dir}/01-inventory.json` to understand sub-project structure
2. Focus on your **assigned sub-projects** (passed in the spawn prompt)
3. Tag every finding with the `Sub-project` field
4. Check for cross-sub-project security issues (e.g., shared auth library vulnerabilities)
5. If a sub-project has 200+ source files, use sampling: audit all high-risk files (auth, payment, crypto, user input) exhaustively, then sample 20% of remaining. Document your sampling methodology.

---

## LLM Secure Code Generation Rules

These rules should be included in project CLAUDE.md / .cursorrules to prevent future vulnerabilities:

1. NEVER concatenate user input into SQL, OS commands, HTML, or file paths. Always use parameterized queries, library APIs, framework auto-escaping, and path validation.
2. Every API endpoint MUST have server-side authentication AND authorization. Never rely on client-side role checks.
3. NEVER store secrets (API keys, passwords, tokens) in source code, environment variable defaults, or Dockerfile instructions. Use a secret manager or runtime environment injection.
4. All cryptographic operations MUST use modern algorithms: AES-256-GCM for encryption, Argon2id/bcrypt for passwords, crypto.randomBytes for tokens. Never use MD5, SHA1, Math.random, or ECB mode.
5. NEVER log PII, tokens, passwords, or session identifiers. Use structured logging with explicit field redaction.
6. Validate all input at API boundaries using schema validation (Zod, Joi, class-validator). Reject unexpected types and fields.
7. Set all cookie security flags: HttpOnly, Secure, SameSite=Lax (minimum). Never store tokens in localStorage.
8. Configure security headers: Content-Security-Policy, Strict-Transport-Security, X-Content-Type-Options, X-Frame-Options. Use Helmet or equivalent.
9. Pin all dependency versions and commit lockfiles. Never use `npm install` in CI — use `npm ci`.
10. For Docker deployments: use non-root USER, drop all capabilities, set read_only where possible. Never expose the Docker socket.

---

## Security Review Checklist

When reviewing code (human or AI-generated) for security:

- [ ] Are all user inputs validated and sanitized before use?
- [ ] Do all endpoints have server-side auth checks?
- [ ] Are secrets kept out of source code and logs?
- [ ] Are parameterized queries used for all database operations?
- [ ] Are security headers configured (CSP, HSTS, etc.)?
- [ ] Is error handling safe (no stack traces or sensitive data leaked)?
- [ ] Are dependencies up to date and free of known CVEs?

---

## File-Saving Instructions

1. Write your complete output to your designated file under `{output_dir}/`. The `{output_dir}` path is provided in your spawn prompt. If it is not set, default to `phases/audit/security`.
2. Do not write to any other agent's file.
3. Do NOT commit any changes. Save files but leave git commits to the orchestrator.
4. If you find zero vulnerabilities, still write the full output structure with an empty Findings section noting "No vulnerabilities detected in this domain."
5. Signal completion with: `[security-audit-<name>] COMPLETE ✓ — saved to {output_dir}/<filename>`
