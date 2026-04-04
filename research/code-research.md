# Code-Level Security Best Practices, Checklists, and Review Methodology

> Research compiled for building a security audit plugin for software projects.
> Last updated: 2026-04-04

---

## Table of Contents

1. [Secure Coding Standards and Guidelines](#1-secure-coding-standards-and-guidelines)
2. [Code Review for Security](#2-code-review-for-security)
3. [Static Analysis and SAST](#3-static-analysis-and-sast)
4. [Language-Specific Security Pitfalls](#4-language-specific-security-pitfalls)
5. [Secrets Management in Code](#5-secrets-management-in-code)
6. [Dependency and Third-Party Code Security](#6-dependency-and-third-party-code-security)
7. [Security Code Review Checklists](#7-security-code-review-checklists)

---

## 1. Secure Coding Standards and Guidelines

### 1.1 OWASP Secure Coding Practices Quick Reference Guide

The OWASP Secure Coding Practices Quick Reference Guide is a technology-agnostic set of general software security coding practices organized as a comprehensive checklist. It covers 14 areas with specific actionable items.

**The 14 areas:**
1. Input Validation
2. Output Encoding
3. Authentication and Password Management
4. Session Management
5. Access Control
6. Cryptographic Practices
7. Error Handling and Logging
8. Data Protection
9. Communication Security
10. System Configuration
11. Database Security
12. File Management
13. Memory Management
14. General Coding Practices

**Key principles across all areas:**
- All security controls must be enforced on a trusted system (server-side)
- Use centralized, tested routines for security-critical functions
- Fail securely -- deny access by default on failure
- Apply defense in depth: never rely on a single control
- Validate all input from untrusted sources against allow-lists
- Encode all output contextually for the target interpreter

**Source:** [OWASP Secure Coding Practices Quick Reference Guide](https://owasp.org/www-project-secure-coding-practices-quick-reference-guide/) | [Full Checklist](https://owasp.org/www-project-secure-coding-practices-quick-reference-guide/stable-en/02-checklist/05-checklist)

### 1.2 CWE Top 25 Most Dangerous Software Weaknesses (2025)

The 2025 CWE Top 25, published by MITRE and CISA, is based on analysis of 39,080 CVE entries disclosed between June 2024 and June 2025. Each weakness is scored by prevalence and severity.

| Rank | CWE ID | Name |
|------|---------|------|
| 1 | CWE-79 | Cross-site Scripting (XSS) |
| 2 | CWE-89 | SQL Injection |
| 3 | CWE-352 | Cross-Site Request Forgery (CSRF) |
| 4 | CWE-862 | Missing Authorization |
| 5 | CWE-787 | Out-of-bounds Write |
| 6 | CWE-22 | Path Traversal |
| 7 | CWE-416 | Use After Free |
| 8 | CWE-125 | Out-of-bounds Read |
| 9 | CWE-78 | OS Command Injection |
| 10 | CWE-94 | Code Injection |
| 11 | CWE-120 | Classic Buffer Overflow |
| 12 | CWE-434 | Unrestricted File Upload |
| 13 | CWE-476 | NULL Pointer Dereference |
| 14 | CWE-121 | Stack-based Buffer Overflow |
| 15 | CWE-502 | Deserialization of Untrusted Data |
| 16 | CWE-122 | Heap-based Buffer Overflow |
| 17 | CWE-863 | Incorrect Authorization |
| 18 | CWE-20 | Improper Input Validation |
| 19 | CWE-284 | Improper Access Control |
| 20 | CWE-200 | Exposure of Sensitive Information |
| 21 | CWE-306 | Missing Authentication for Critical Function |
| 22 | CWE-918 | Server-Side Request Forgery (SSRF) |
| 23 | CWE-77 | Command Injection |
| 24 | CWE-639 | Authorization Bypass Through User-Controlled Key |
| 25 | CWE-770 | Allocation of Resources Without Limits |

**What to check during code review:**
- Every user input touching a SQL query, HTML output, OS command, or file path
- All authorization checks (present? correct? consistent?)
- Memory operations in C/C++ (bounds checking, lifetime management)
- Deserialization of any external data
- Resource allocation without limits (DoS vector)

**Source:** [CWE Top 25 (2025)](https://cwe.mitre.org/top25/archive/2025/2025_cwe_top25.html) | [CISA Alert](https://www.cisa.gov/news-events/alerts/2025/12/11/2025-cwe-top-25-most-dangerous-software-weaknesses) | [CWE-1435 View](https://cwe.mitre.org/data/definitions/1435.html)

### 1.3 SEI CERT Secure Coding Standards

The Software Engineering Institute (SEI) at Carnegie Mellon maintains CERT Coding Standards for C, C++, Java, Android, and Perl. Each standard consists of **rules** (normative requirements) and **recommendations** (best-practice guidance).

**CERT C Standard (2016 Edition):**
- 99 coding rules + 185 recommendations
- 11 chapters covering: preprocessor, declarations, expressions, integers, floating point, arrays, characters/strings, memory management, input/output, environment, signals, concurrency
- Each rule includes risk assessment: severity, likelihood, remediation cost
- Targets C11 and C99 compliance

**CERT C++ Standard:**
- 83+ rules across 11 chapters
- Builds on the C standard with C++-specific guidance
- Covers: object-oriented practices, templates, exception handling, concurrency

**CERT Java Standard:**
- Covers: input validation, numeric types, object construction, serialization, concurrency, JNI
- Specific rules for deserialization safety

**What to check:**
- Integer overflow/underflow (especially in C/C++)
- Format string vulnerabilities
- Null pointer dereference patterns
- Improper use of memory allocation/deallocation
- Signal handler safety
- Concurrent access without synchronization

**Sources:** [SEI CERT Coding Standards Wiki](https://wiki.sei.cmu.edu/confluence/display/seccode) | [CERT C Standard](https://wiki.sei.cmu.edu/confluence/display/c) | [CERT C++ Standard](https://wiki.sei.cmu.edu/confluence/pages/viewpage.action?pageId=88046682) | [SEI CERT C PDF](https://www.sei.cmu.edu/forms/secure-coding-form/)

### 1.4 MISRA Standards

MISRA C and MISRA C++ are coding standards primarily targeting safety-critical and embedded systems (automotive, aerospace, medical devices). They define a subset of C/C++ that avoids constructs with undefined, unspecified, or implementation-defined behavior.

**Key areas:**
- No dynamic memory allocation after initialization
- No recursion
- Restricted pointer arithmetic
- Mandatory use of static analysis tools for compliance verification
- Overlap with CERT rules but stricter for safety-critical contexts

**Source:** [MISRA Official](https://misra.org.uk/) | [LDRA CERT Coverage](https://ldra.com/sei-cert/)

### 1.5 NIST Secure Software Development Framework (SSDF) SP 800-218

NIST SP 800-218 v1.1 defines four practice groups for secure software development:

1. **Prepare the Organization (PO):** Define policies, roles, tooling, training
2. **Protect the Software (PS):** Secure development environments, protect code integrity
3. **Produce Well-Secured Software (PW):** Design, code review, testing, vulnerability remediation
4. **Respond to Vulnerabilities (RV):** Disclosure, analysis, remediation of discovered vulnerabilities

**Relevance to code review:** The PW group specifically mandates code review, static analysis, and testing as part of producing secure software. The SSDF provides a vocabulary that acquisition teams can use to require secure development from suppliers.

**Source:** [NIST SP 800-218](https://csrc.nist.gov/pubs/sp/800/218/final) | [CISA SSDF Resource](https://www.cisa.gov/resources-tools/resources/nist-sp-800-218-secure-software-development-framework-v11-recommendations-mitigating-risk-software) | [NIST SSDF Project](https://csrc.nist.gov/projects/ssdf)

---

## 2. Code Review for Security

### 2.1 Methodology

Security code review is the manual examination of source code to identify vulnerabilities that automated tools often miss. The OWASP Secure Code Review Cheat Sheet defines two review types:

**Baseline Reviews:** Examine entire codebases for new applications, major releases, legacy onboarding, and compliance needs.

**Diff-Based Reviews:** Focus on code changes in pull requests, daily workflows, and CI/CD pipelines.

**Preparation checklist before reviewing:**
- Understand the application architecture and trust boundaries
- Gather threat models and previous security findings
- Identify critical assets and high-risk functions
- Know the tech stack and its known vulnerability patterns
- Review security documentation and compliance requirements

**Review process (8 steps):**
1. Architecture security assessment
2. Entry point and input validation analysis
3. Authentication and authorization verification
4. Data flow tracing (source to sink)
5. Business logic analysis
6. Cryptographic implementation review
7. Error handling verification
8. Configuration and deployment review

**Source:** [OWASP Secure Code Review Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Secure_Code_Review_Cheat_Sheet.html) | [OWASP Code Review Guide v2 (PDF)](https://owasp.org/www-project-code-review-guide/assets/OWASP_Code_Review_Guide_v2.pdf) | [OWASP Code Review Project](https://owasp.org/www-project-code-review-guide/)

### 2.2 Common Vulnerability Patterns to Look For

#### Injection Flaws
- **SQL Injection:** String concatenation in SQL queries; missing parameterized queries
- **OS Command Injection:** User input passed to `exec()`, `system()`, `subprocess.run()`, `child_process.exec()`
- **LDAP/XML/XPath Injection:** Untrusted data in query construction
- **NoSQL Injection:** Unvalidated operators in MongoDB queries (`$gt`, `$ne`)
- **Template Injection (SSTI):** User input rendered in server-side templates without sandboxing

**What to check:** Trace every user-controlled input to where it's consumed. If it reaches a query, command, or interpreter without parameterization or encoding, flag it.

#### Cross-Site Scripting (XSS)
- **Reflected:** User input echoed in HTTP response without encoding
- **Stored:** Malicious input persisted and rendered to other users
- **DOM-based:** Client-side JavaScript manipulates DOM with unsanitized data

**What to check:** `innerHTML`, `document.write()`, `dangerouslySetInnerHTML`, `v-html`, unescaped template expressions, missing Content-Security-Policy headers.

#### Buffer Overflows (C/C++)
- Writing beyond allocated buffer bounds
- Off-by-one errors in loop bounds
- Unsafe functions: `strcpy`, `strcat`, `sprintf`, `gets`
- Missing bounds checks on array indices

**What to check:** Use of `strncpy`/`snprintf` instead of unsafe variants; bounds validation before memory writes; use of safe string libraries.

#### Race Conditions
- **TOCTOU (Time-of-Check-Time-of-Use):** Check a condition, then act on it, but the condition changes between check and use
- **File system races:** Checking file existence then opening; symlink attacks
- **Concurrent data access:** Shared mutable state without locks

**What to check:** File operations with separate check-and-use steps; shared variables without synchronization; database operations without transactions.

#### Insecure Deserialization
- Deserializing untrusted data can lead to Remote Code Execution (RCE)
- Gadget chains in Java (Apache Commons Collections, Spring)
- Python `pickle.loads()` on untrusted input
- PHP `unserialize()` with user data
- YAML `yaml.load()` without SafeLoader in Python

**What to check:** Any deserialization of data from external sources; class allowlists; use of safe alternatives (JSON instead of pickle/YAML).

#### Hardcoded Secrets
- API keys, passwords, tokens, connection strings in source code
- Default credentials left in production
- Private keys or certificates committed to repos

**What to check:** String literals matching key patterns (AWS, GitHub tokens, etc.); configuration files with credentials; `.env` files tracked in git.

#### Improper Error Handling
- Stack traces exposed to users
- Verbose error messages revealing system internals
- Catch-all exception handlers that swallow security exceptions
- Different error responses for valid vs. invalid usernames (user enumeration)

**What to check:** Generic error pages for production; no stack traces in API responses; consistent error messages for auth failures.

#### Cryptographic Misuse
- Using broken algorithms: MD5, SHA-1 for security, DES, RC4
- ECB mode for block ciphers
- Hardcoded or predictable IVs/nonces
- Rolling your own crypto
- Not using authenticated encryption (AES-GCM preferred over AES-CBC)
- Weak key sizes (RSA < 2048, ECDSA < P-256)

**What to check:** Algorithm and mode selection; key generation using CSPRNG; proper IV/nonce handling; key rotation mechanisms; no custom crypto implementations.

**Sources:** [OWASP Vulnerability Categories](https://owasp.org/www-community/vulnerabilities/) | [CWE Database](https://cwe.mitre.org/) | [Veracode CWE Reference](https://docs.veracode.com/r/c_review_cwe) | [Snyk Learn - Insecure Deserialization](https://learn.snyk.io/lesson/insecure-deserialization/)

### 2.3 Data Flow Analysis Technique

The most effective manual review technique for finding injection and data-exposure bugs:

1. **Identify sources:** User input (HTTP params, headers, cookies, file uploads, API payloads, WebSocket messages, environment variables from untrusted origins)
2. **Identify sinks:** SQL queries, OS commands, HTML output, file system operations, deserialization calls, logging with string interpolation, redirect URLs
3. **Trace the path:** Follow data from source through transformations to sink
4. **Verify controls:** At each trust boundary, verify validation, encoding, or parameterization exists
5. **Check completeness:** Ensure controls cover all code paths, including error paths

---

## 3. Static Analysis and SAST

### 3.1 Categories of Issues Detected by SAST

| Category | Examples |
|----------|----------|
| Injection | SQL, XSS, command, LDAP, template injection |
| Authentication | Hardcoded credentials, weak password storage, missing auth checks |
| Cryptography | Weak algorithms, insecure modes, hardcoded keys |
| Configuration | Debug mode in production, permissive CORS, missing security headers |
| Data exposure | Sensitive data in logs, error messages, comments |
| Memory safety | Buffer overflow, use-after-free, null dereference |
| Concurrency | Race conditions, deadlocks, improper synchronization |
| Resource management | Resource leaks, missing cleanup, unbounded allocation |
| Code quality/security | Dead code, unreachable branches, tainted data flow |

### 3.2 Key SAST Tools

#### Semgrep
- **Type:** Semantic pattern-matching SAST
- **Languages:** 30+ (Python, JS/TS, Java, Go, Ruby, C#, Rust, etc.)
- **Strengths:** Fast, developer-friendly, custom rules easy to write, taint tracking, large community rule registry (2,500+ rules), low false-positive rate
- **Catches:** Injection flaws, insecure API usage, hardcoded secrets, misconfigurations, framework-specific antipatterns
- **Integration:** CLI, CI/CD (GitHub Actions, GitLab CI), IDE, pre-commit
- **Also includes:** SCA (dependency scanning) and secrets detection
- **Source:** [semgrep.dev](https://semgrep.dev/) | [Semgrep Rules Registry](https://semgrep.dev/explore)

#### CodeQL
- **Type:** Query-based semantic analysis engine (GitHub)
- **Languages:** C/C++, C#, Go, Java/Kotlin, JavaScript/TypeScript, Python, Ruby, Swift
- **Strengths:** Deep dataflow and taint analysis, custom query language (QL), excellent for finding complex multi-step vulnerabilities, free for open-source on GitHub
- **Catches:** Injection variants (including complex multi-hop flows), access control issues, crypto misuse, resource leaks
- **Integration:** GitHub Code Scanning, VS Code extension, CLI
- **Source:** [CodeQL Documentation](https://codeql.github.com/) | [CodeQL Query Suites](https://github.com/github/codeql)

#### SonarQube / SonarCloud
- **Type:** Continuous code quality and security platform
- **Languages:** 30+ languages
- **Strengths:** Broad language support, quality gates in CI/CD, OWASP Top 10 and CWE coverage, technical debt tracking, enterprise governance
- **Catches:** OWASP Top 10 vulnerabilities, hardcoded secrets, IaC misconfigurations, code smells that can become security issues
- **Integration:** CI/CD pipelines, IDE (SonarLint), GitHub/GitLab/Azure DevOps
- **Source:** [sonarqube.org](https://www.sonarsource.com/products/sonarqube/)

#### Bandit (Python)
- **Type:** Python-specific security linter
- **Languages:** Python only
- **Strengths:** 47 built-in checks in 7 categories, fast, low friction, SARIF output for GitHub code scanning
- **Catches:** `eval()`, `exec()`, `pickle`, `subprocess` with `shell=True`, `yaml.load()`, hardcoded passwords, weak crypto, SQL injection, assert in production code
- **Integration:** Pre-commit hooks, GitHub Actions, CI/CD, any Python environment
- **Source:** [Bandit on GitHub](https://github.com/PyCQA/bandit) | [Bandit on PyPI](https://pypi.org/project/bandit/)

#### ESLint Security Plugins (JavaScript/TypeScript)
- **eslint-plugin-security:** 13 rules detecting `eval()`, `child_process`, non-literal regex, non-literal require, `Function()` constructor, prototype builtins
- **eslint-plugin-no-unsanitized (Mozilla):** Detects unsafe DOM manipulation: `innerHTML`, `outerHTML`, `document.write()`, `insertAdjacentHTML()`
- **Note:** eslint-plugin-security is effectively unmaintained since 2020. For comprehensive JS/TS security linting, Semgrep with its JavaScript rules is the stronger choice.
- **Source:** [eslint-plugin-security](https://www.npmjs.com/package/eslint-plugin-security) | [eslint-plugin-no-unsanitized](https://github.com/mozilla/eslint-plugin-no-unsanitized)

#### Brakeman (Ruby on Rails)
- **Type:** Rails-specific static analysis
- **Languages:** Ruby (Rails applications only)
- **Strengths:** Deep understanding of Rails routing, ActiveRecord, ERB templates; zero configuration needed
- **Catches:** SQL injection, XSS, command injection, mass assignment, file access, redirect vulnerabilities, session/cookie issues
- **Source:** [Brakeman Scanner](https://brakemanscanner.org/)

#### Other Notable Tools
| Tool | Language | Focus |
|------|----------|-------|
| **Gosec** | Go | Go-specific security: crypto, file perms, SQL, command injection |
| **cargo-audit** | Rust | Known vulnerabilities in Rust crate dependencies |
| **cargo-geiger** | Rust | Counts unsafe blocks in dependency tree |
| **SpotBugs + Find Security Bugs** | Java | OWASP Top 10, deserialization, JNDI, XXE |
| **PHPStan / Psalm** | PHP | Type safety, taint analysis (with security extensions) |
| **Clippy** | Rust | Code quality and some safety checks (not security-focused) |
| **Bearer** | Multi | Data flow analysis focused on sensitive data exposure |

### 3.3 Integrating SAST into Review

**Recommended integration points:**
1. **Pre-commit hooks:** Fast checks (secrets detection, basic security linting) -- blocks commits
2. **Pull request CI:** Full SAST scan (Semgrep, CodeQL) -- blocks merge on findings
3. **Nightly/weekly:** Deep analysis (CodeQL extended queries, SonarQube quality gates) -- feeds security backlog
4. **IDE plugins:** Real-time feedback during development (SonarLint, Semgrep VS Code extension)

**Best practices:**
- Start with a high-confidence rule set to avoid alert fatigue
- Use baseline files to suppress existing findings and only flag new ones
- Combine multiple tools: no single SAST tool catches everything
- Treat SAST findings as leads for manual review, not final verdicts
- Track false-positive rates and tune rules accordingly

**Source:** [StackHawk SAST Comparison](https://www.stackhawk.com/blog/best-sast-tools-comparison/) | [AppSec Santa SAST Review](https://appsecsanta.com/sast-tools)

---

## 4. Language-Specific Security Pitfalls

### 4.1 TypeScript / JavaScript

| Vulnerability | Description | What to Check |
|--------------|-------------|---------------|
| **Prototype Pollution** | Attacker modifies `Object.prototype` via `__proto__`, `constructor.prototype`, or property merge functions, affecting all objects | Deep merge/clone functions (lodash `_.merge`, `_.defaultsDeep`); any function that recursively assigns properties from untrusted input; use `Object.create(null)` for maps |
| **ReDoS** | Regular expressions with catastrophic backtracking cause event loop blocking. Caused Stack Overflow 34-min outage (2016), Cloudflare 27-min outage (2019) | Nested quantifiers `(a+)+`, overlapping alternation `(a|a)*`; user input used in `new RegExp()`; use RE2 or safe-regex libraries; set timeouts |
| **eval() / Function()** | Executes arbitrary code from string input | Any use of `eval()`, `new Function()`, `setTimeout(string)`, `setInterval(string)` with dynamic data |
| **innerHTML / DOM XSS** | Injects HTML/JS into the page via DOM manipulation | `innerHTML`, `outerHTML`, `document.write()`, `insertAdjacentHTML()`, `dangerouslySetInnerHTML` in React, `v-html` in Vue |
| **Insecure Randomness** | `Math.random()` is not cryptographically secure | Use `crypto.getRandomValues()` (browser) or `crypto.randomBytes()` (Node) for security-sensitive values |
| **Path Traversal (Node)** | `path.join(base, userInput)` does not prevent `../` traversal | Validate resolved path starts with intended base directory using `path.resolve()` then check prefix |
| **npm script injection** | Package.json scripts can run arbitrary commands during install | Review `preinstall`, `postinstall`, `prepare` scripts in dependencies |

**Sources:** [MDN - Prototype Pollution](https://developer.mozilla.org/en-US/docs/Web/Security/Attacks/Prototype_pollution) | [Snyk - Prototype Pollution Prevention](https://snyk.io/articles/prevent-prototype-pollution-vulnerabilities-javascript/) | [OWASP - ReDoS](https://owasp.org/www-community/attacks/Regular_expression_Denial_of_Service_-_ReDoS) | [Sonar - Vulnerable Regex in JS](https://www.sonarsource.com/blog/vulnerable-regular-expressions-javascript)

### 4.2 Python

| Vulnerability | Description | What to Check |
|--------------|-------------|---------------|
| **pickle deserialization** | `pickle.loads()` on untrusted data allows arbitrary code execution via `__reduce__` method | Any use of `pickle.load()`/`pickle.loads()` with external data; use JSON, MessagePack, or protobuf instead |
| **YAML deserialization** | `yaml.load()` without SafeLoader can execute arbitrary Python constructors via `!python/object` tags | Use `yaml.safe_load()` always; PyYAML 6.0+ defaults to SafeLoader for `yaml.load()` but verify |
| **subprocess injection** | `subprocess.run(cmd, shell=True)` with user input enables command injection | `shell=True` with string commands from user input; use `shell=False` with argument lists instead |
| **eval() / exec()** | Arbitrary code execution from string input | `eval()`, `exec()`, `compile()` with any external data |
| **Format string injection** | `str.format()` or f-strings with user-controlled format strings can leak object attributes | User input used as format string template; use explicit field access instead |
| **assert in production** | `assert` statements are removed when Python runs with `-O` flag | Security checks using `assert` instead of explicit `if/raise` |
| **Insecure temp files** | `tempfile.mktemp()` has a TOCTOU race condition | Use `tempfile.mkstemp()` or `tempfile.NamedTemporaryFile()` instead |
| **XML External Entities** | Default XML parsers (xml.etree, lxml) may process external entities | Use `defusedxml` library; disable external entity processing |

**Sources:** [Sourcery - YAML RCE](https://www.sourcery.ai/vulnerabilities/python-pyyaml-unsafe-load-rce) | [Bandit Checks](https://github.com/PyCQA/bandit) | [Datadog - YAML Load](https://docs.datadoghq.com/security/code_security/static_analysis/static_analysis_rules/python-security/yaml-load/)

### 4.3 Go

| Vulnerability | Description | What to Check |
|--------------|-------------|---------------|
| **Goroutine leaks** | Goroutines that block forever on channels or I/O, consuming ~2KB+ stack each plus scheduler overhead, file handles, and network connections | Unbuffered channels without receivers; missing `context.WithCancel`/`WithTimeout`; missing `defer cancel()`; use `uber-go/goleak` in tests |
| **unsafe package** | `unsafe.Pointer` bypasses Go's type system, enabling buffer overflows, use-after-free, and arbitrary memory access | Any import of `unsafe`; verify it's truly necessary; isolate in dedicated packages with safe public APIs |
| **SQL injection** | String concatenation in SQL queries | `fmt.Sprintf` building SQL; use `database/sql` parameterized queries (`?` or `$1` placeholders) |
| **Integer overflow** | Go integers wrap silently on overflow | Arithmetic on user-controlled integers without bounds checks, especially for slice indexing or allocation sizes |
| **Unvalidated redirects** | `http.Redirect()` with user-controlled URLs | Validate redirect URLs against allowlist; check for open redirect patterns |
| **Insecure TLS** | `crypto/tls` with `InsecureSkipVerify: true` | Grep for `InsecureSkipVerify`; should only appear in test code |
| **Race conditions** | Concurrent map access, shared state without mutex | Run `go test -race`; shared state without `sync.Mutex` or channels |

**Sources:** [Ardanlabs - Goroutine Leaks](https://www.ardanlabs.com/blog/2018/11/goroutine-leaks-the-forgotten-sender.html) | [uber-go/goleak](https://github.com/uber-go/goleak) | [Go Security Best Practices](https://go.dev/doc/security/best-practices) | [Go Vulnerability Management](https://go.dev/doc/security/vuln/)

### 4.4 Rust

| Vulnerability | Description | What to Check |
|--------------|-------------|---------------|
| **unsafe blocks** | `unsafe` bypasses borrow checker, enabling UB: buffer overflows, use-after-free, data races, null pointer dereference | Every `unsafe` block; verify `// SAFETY:` comments documenting invariants; minimize scope; wrap in safe abstractions |
| **FFI boundaries** | Calling C code via `extern "C"` inherits all C vulnerabilities | All FFI function calls; validate inputs before passing to C; handle null pointers; check error returns |
| **Supply chain (crates)** | Malicious or vulnerable crate dependencies | Run `cargo audit`; use `cargo-geiger` to count unsafe usage in dependency tree; review new dependencies |
| **Panics in unsafe code** | Panic unwinding through unsafe code can leave invariants violated | `catch_unwind` at FFI boundaries; avoid panics inside unsafe blocks |
| **Integer overflow** | In debug mode Rust panics on overflow; in release mode it wraps silently | Arithmetic on untrusted integers in release builds; use `checked_*`, `saturating_*`, or `wrapping_*` methods explicitly |
| **Timing side channels** | Non-constant-time comparisons of secrets | Use `subtle` crate for constant-time operations; avoid `==` for secret comparison |

**Sources:** [Rust Book - Unsafe](https://doc.rust-lang.org/book/ch20-01-unsafe-rust.html) | [Google Rust Crate Audit Standards](https://github.com/google/rust-crate-audits/blob/main/auditing_standards.md) | [Sherlock Rust Security Guide 2026](https://sherlock.xyz/post/rust-security-auditing-guide-2026) | [Trust-in-Soft - Rust Hidden Dangers](https://www.trust-in-soft.com/resources/blogs/rusts-hidden-dangers-unsafe-embedded-and-ffi-risks)

### 4.5 Java

| Vulnerability | Description | What to Check |
|--------------|-------------|---------------|
| **Deserialization / Gadget Chains** | `ObjectInputStream.readObject()` on untrusted data enables RCE via gadget chains (Commons Collections, Spring, etc.) | Any use of Java serialization with external input; use allowlist filtering (`ObjectInputFilter` in Java 9+); prefer JSON |
| **JNDI Injection (Log4Shell)** | Log4j's `${jndi:ldap://...}` lookup in log messages enabled RCE (CVE-2021-44228) | Log4j version (must be >= 2.17.1); any JNDI lookups with user-controlled strings; `InitialContext.lookup()` with untrusted input |
| **XML External Entities (XXE)** | Default XML parsers process external entities, enabling file read and SSRF | `DocumentBuilderFactory`, `SAXParserFactory` without `FEATURE_SECURE_PROCESSING`; disable external entities and DTDs explicitly |
| **SQL Injection** | `Statement.execute()` with string concatenation | Use `PreparedStatement` with parameterized queries always |
| **Spring-specific issues** | SpEL injection, mass assignment via `@ModelAttribute`, actuator endpoints exposed | User input in SpEL expressions; exposed actuator/health endpoints; `@RequestBody` binding without `@Valid` |
| **Weak cryptography** | `java.util.Random` for security, `DES`, `MD5` for password hashing | Use `SecureRandom`; AES-256-GCM; bcrypt/scrypt/Argon2 for passwords |
| **Path traversal** | `new File(base + userInput)` without canonicalization | Canonicalize paths and verify they start with expected base directory |

**Sources:** [Snyk - Log4Shell](https://snyk.io/blog/log4j-rce-log4shell-vulnerability-cve-2021-44228/) | [Semgrep - Log4Shell](https://semgrep.dev/blog/2021/understanding-log4j-and-log4shell/) | [Google Cloud - Deserialization Exploits](https://cloud.google.com/blog/topics/threat-intelligence/hunting-deserialization-exploits) | [OWASP - Deserialization](https://owasp.org/www-community/vulnerabilities/Deserialization_of_untrusted_data)

---

## 5. Secrets Management in Code

### 5.1 What Constitutes a Hardcoded Secret

- API keys (AWS, GCP, Azure, GitHub, Stripe, Twilio, etc.)
- Database connection strings with credentials
- OAuth client secrets and tokens
- JWT signing keys
- Private keys (SSH, TLS/SSL, PGP)
- Passwords and passphrases
- Encryption keys
- Webhook secrets
- Service account credentials
- Default/test credentials left in production code

### 5.2 Detection Tools

#### Gitleaks
- **Best for:** Pre-commit hooks (fast, low latency)
- **How it works:** Regex-based pattern matching against a configurable rule set
- **Integration:** Pre-commit hook, GitHub Action (`gitleaks-action`), CI/CD pipeline
- **Output:** JSON, SARIF, CSV
- **Strengths:** Speed, simplicity, low false-positive rate with good defaults
- **Source:** [gitleaks on GitHub](https://github.com/gitleaks/gitleaks)

#### TruffleHog
- **Best for:** CI/CD pipeline and deep scanning (credential verification)
- **How it works:** Entropy analysis + regex patterns + active credential verification (tests if detected secrets are live)
- **Scans:** Git repos, S3 buckets, Docker images, Slack, Confluence, file systems
- **Killer feature:** Verifies whether detected credentials are still active, dramatically reducing false-positive triage
- **Source:** [TruffleHog on GitHub](https://github.com/trufflesecurity/trufflehog) | [TruffleHog Docs](https://trufflesecurity.com/trufflehog)

#### detect-secrets (Yelp)
- **How it works:** Entropy-based + regex; maintains a baseline file of known secrets to track changes
- **Strengths:** Baseline diffing (only alert on new secrets); pluggable detection modules
- **Limitations:** Requires more manual configuration than newer tools
- **Source:** [detect-secrets on GitHub](https://github.com/Yelp/detect-secrets)

#### GitHub Secret Scanning
- **Built into GitHub** for public repos (free) and private repos (GHAS license)
- **Integrates with:** 200+ service providers for automatic revocation
- **Push protection:** Blocks pushes containing detected secrets before they enter history

#### Semgrep Secrets
- **Part of the Semgrep platform**
- **Combines:** Semantic code analysis with secrets detection for lower false-positive rates
- **Source:** [semgrep.dev](https://semgrep.dev/)

### 5.3 Prevention Strategy

**Layered defense:**
1. **Pre-commit hook:** Gitleaks or TruffleHog (blocks secret from ever entering git history)
2. **CI/CD gate:** TruffleHog with verification (catches anything that slipped through)
3. **GitHub/GitLab native:** Secret scanning + push protection (platform-level backstop)
4. **Regular audits:** Periodic full-history scan of repositories

**Complementary practices:**
- `.gitignore` patterns for common secret files: `.env`, `*.pem`, `*.key`, `credentials.json`, `serviceAccountKey.json`
- Use environment variables or secret managers (Vault, AWS Secrets Manager, GCP Secret Manager) instead of config files
- Rotate any secret that was ever committed, even if the commit was reverted
- Document secret management procedures in developer onboarding

**Source:** [OWASP DevSecOps - Secrets Management](https://owasp.org/www-project-devsecops-guideline/latest/01a-Secrets-Management) | [Jit - TruffleHog vs Gitleaks](https://www.jit.io/resources/appsec-tools/trufflehog-vs-gitleaks-a-detailed-comparison-of-secret-scanning-tools)

---

## 6. Dependency and Third-Party Code Security

### 6.1 Supply Chain Attack Vectors

| Vector | Description | Real-World Example |
|--------|-------------|-------------------|
| **Account compromise** | Attacker takes over maintainer account and publishes malicious version | Axios npm package compromise (2026) -- malicious dependency inserted into axios@1.14.1 |
| **Typosquatting** | Publish package with similar name to popular library | `reqeusts` instead of `requests`, `react-router-doms` instead of `react-router-dom` |
| **Dependency confusion** | Internal package name collision with public registry | Substituting private packages with malicious public ones |
| **Malicious install scripts** | `preinstall`/`postinstall` scripts execute arbitrary code | Packages that exfiltrate env vars or install backdoors during `npm install` |
| **Protestware** | Maintainer intentionally sabotages their own package | `node-ipc` (2022), `colors`/`faker` (2022) |

**Scale of the problem:** 454,648 malicious packages were published to npm in 2025. The average npm project pulls in 79 transitive dependencies.

### 6.2 Actionable Review Steps

**When reviewing imports and dependencies:**
1. **Verify package names carefully** -- check for typosquatting (character substitution, extra/missing characters)
2. **Review new dependencies before adding** -- check download counts, maintenance activity, known vulnerabilities, GitHub stars/issues
3. **Pin exact versions** -- use exact version in `package.json` (no `^` or `~` prefixes) or rely on lockfiles
4. **Enforce lockfile use** -- `npm ci` (not `npm install`) in CI/CD; commit `package-lock.json` / `yarn.lock` / `pnpm-lock.yaml`
5. **Audit regularly** -- `npm audit`, `pip audit`, `cargo audit`, `go vuln check`, `bundle audit`
6. **Review install scripts** -- check `preinstall`, `postinstall`, `prepare` scripts in new dependencies; use `--ignore-scripts` flag when appropriate
7. **Minimize dependencies** -- evaluate whether a dependency is truly needed; prefer built-in APIs
8. **Monitor for advisories** -- enable Dependabot / Renovate / Snyk automated PRs

**Reviewing transitive dependencies:**
- Use `npm ls --all` or `yarn why <package>` to understand the full dependency tree
- Tools like `socket.dev` analyze packages for supply chain indicators (install scripts, network access, filesystem access, obfuscated code)
- Consider using `npm-lockfile-lint` to enforce lockfile policies

### 6.3 Tools for Dependency Security

| Tool | Ecosystem | What It Does |
|------|-----------|-------------|
| **npm audit** | Node.js | Checks installed packages against known CVE database |
| **Socket.dev** | npm, Python | Analyzes packages for supply chain risk indicators (not just CVEs) |
| **Snyk** | Multi | SCA with fix PRs, license compliance, container scanning |
| **Dependabot** | GitHub | Automated dependency update PRs with vulnerability alerts |
| **Renovate** | Multi | Automated dependency updates with extensive customization |
| **pip-audit** | Python | Audits Python packages against the OSV database |
| **cargo audit** | Rust | Checks Cargo.lock against RustSec Advisory Database |
| **govulncheck** | Go | Official Go vulnerability scanner, checks actual usage paths |
| **OWASP Dependency-Check** | Java, .NET | Identifies known CVEs in project dependencies |
| **Trivy** | Multi + containers | Scans dependencies, containers, IaC, and Kubernetes |

**Source:** [npm Supply Chain Security Guide](https://apidog.com/blog/npm-supply-chain-security-guide/) | [Socket.dev Blog](https://socket.dev/blog/axios-npm-package-compromised) | [Snyk - Axios Compromise](https://snyk.io/blog/axios-npm-package-compromised-supply-chain-attack-delivers-cross-platform/) | [Armorcode - NPM Supply Chain Defense](https://www.armorcode.com/blog/defending-against-npm-supply-chain-attacks-a-practical-guide)

---

## 7. Security Code Review Checklists

### 7.1 OWASP Comprehensive Checklist

The full OWASP Secure Coding Practices checklist (14 categories, 100+ items). The highest-priority items for a code security audit:

**Input Validation (CRITICAL):**
- [ ] All input validated on server side (not just client side)
- [ ] Allow-list validation (not deny-list)
- [ ] Data type, range, and length validation enforced
- [ ] Centralized validation routine used across application
- [ ] UTF-8 character set specified and canonicalization applied before validation

**Output Encoding (CRITICAL):**
- [ ] Context-appropriate encoding for all untrusted data (HTML, JS, URL, CSS, SQL, LDAP, XML)
- [ ] Output encoding done on server side
- [ ] Tested, standard encoding routines used (not custom)

**Authentication (HIGH):**
- [ ] Cryptographically strong one-way salted hashes for password storage
- [ ] Authentication failure responses don't reveal which credential was wrong
- [ ] Account lockout after N failed attempts
- [ ] MFA for sensitive operations
- [ ] Credentials transmitted only over encrypted connections
- [ ] Re-authentication before critical operations

**Session Management (HIGH):**
- [ ] Server-generated session identifiers only
- [ ] New session ID on login and re-authentication
- [ ] Session timeout enforced
- [ ] Cookies have Secure, HttpOnly, SameSite attributes
- [ ] Session IDs never in URLs or logs

**Access Control (HIGH):**
- [ ] Centralized authorization check on every request
- [ ] Fail-secure: deny access if security config unavailable
- [ ] Direct object references restricted to authorized users (IDOR prevention)
- [ ] Server-side and UI access control rules match
- [ ] Least privilege enforced

**Cryptographic Practices (HIGH):**
- [ ] Only FIPS 140-2 compliant or equivalent cryptographic modules
- [ ] CSPRNG for all random values
- [ ] Key management policy defined and followed
- [ ] No custom cryptographic algorithms

**Error Handling and Logging (MEDIUM):**
- [ ] No sensitive data in error messages (no stack traces in production)
- [ ] Generic error messages shown to users
- [ ] All auth attempts (success + failure) logged
- [ ] All access control failures logged
- [ ] Log integrity protected (cryptographic hash)
- [ ] No sensitive data in logs (no session IDs, passwords, PII)

**Data Protection (MEDIUM):**
- [ ] Sensitive data encrypted at rest
- [ ] No sensitive data in URL parameters
- [ ] Autocomplete disabled on sensitive form fields
- [ ] Source code comments don't reveal sensitive information
- [ ] Cached sensitive data purged when no longer needed

**Database Security (MEDIUM):**
- [ ] Parameterized queries used exclusively (no string concatenation)
- [ ] Application uses least-privilege database accounts
- [ ] Default database admin credentials changed
- [ ] Connection strings not hardcoded

**File Management (MEDIUM):**
- [ ] File uploads validated by content (headers), not just extension
- [ ] Upload directory has no execute permissions
- [ ] File paths use index values, not user-supplied paths
- [ ] Uploaded files scanned for malware

**Source:** [OWASP Secure Coding Practices Checklist](https://owasp.org/www-project-secure-coding-practices-quick-reference-guide/stable-en/02-checklist/05-checklist)

### 7.2 Microsoft SDL Code Review Checklist

Microsoft's Security Development Lifecycle mandates these code review requirements:

- [ ] Code reviewed by a separate reviewer (not the author) before merging to release branch
- [ ] Reviewer verifies code meets SDL security requirements
- [ ] Reviewer verifies functional and security tests pass
- [ ] Associated documentation, configurations, and dependencies reviewed
- [ ] Automated security tooling (SAST) complements manual review
- [ ] Threat model updated if architecture changed
- [ ] All compiler/framework security flags enabled
- [ ] Deprecated or banned APIs replaced with safe alternatives

**Source:** [Microsoft SDL](https://www.microsoft.com/en-us/securityengineering/sdl) | [Microsoft SDL Practices](https://www.microsoft.com/en-us/securityengineering/sdl/practices)

### 7.3 Mozilla Security Review Focus Areas

Mozilla's approach emphasizes DOM security for web applications:

- [ ] No use of `innerHTML`, `outerHTML`, `document.write()` with untrusted data
- [ ] `insertAdjacentHTML()` reviewed for XSS
- [ ] Content Security Policy (CSP) headers enforced
- [ ] Third-party script inclusion minimized and integrity-verified (SRI)
- [ ] Use of `eslint-plugin-no-unsanitized` in CI

**Source:** [eslint-plugin-no-unsanitized](https://github.com/mozilla/eslint-plugin-no-unsanitized)

### 7.4 Universal Security Audit Checklist (Synthesized)

A consolidated checklist drawing from OWASP, CERT, CWE Top 25, Microsoft SDL, and industry best practices. Organized by review phase:

#### Phase 1: Pre-Review Preparation
- [ ] Identify the threat model and trust boundaries
- [ ] Know the tech stack and its known vulnerability patterns (see Section 4)
- [ ] Have access to SAST tool results (see Section 3)
- [ ] Understand the data classification (what's sensitive?)
- [ ] Review previous security findings and pen-test results

#### Phase 2: Input/Output Boundary Review
- [ ] All user inputs validated server-side with allow-list approach
- [ ] All outputs encoded for their context (HTML, SQL, OS command, URL, etc.)
- [ ] File uploads validated by content type, size-limited, stored outside web root
- [ ] API request/response schemas enforced (reject unknown fields)
- [ ] Redirect URLs validated against allowlist

#### Phase 3: Authentication and Authorization
- [ ] Authentication required for all non-public resources
- [ ] Passwords stored with strong adaptive hash (bcrypt/scrypt/Argon2)
- [ ] Session management uses framework defaults (no custom session IDs)
- [ ] Authorization checked on every request (including API endpoints)
- [ ] IDOR prevention: indirect references or ownership verification
- [ ] No privilege escalation paths (horizontal or vertical)
- [ ] Rate limiting on authentication endpoints

#### Phase 4: Data Security
- [ ] No hardcoded secrets (API keys, passwords, tokens) in source code
- [ ] Sensitive data encrypted at rest (AES-256-GCM or equivalent)
- [ ] TLS 1.2+ for all data in transit
- [ ] PII/sensitive data not logged
- [ ] Sensitive data not cached in browser (appropriate cache headers)
- [ ] Database credentials in environment variables or secret manager

#### Phase 5: Cryptography
- [ ] No weak algorithms (MD5, SHA-1 for security; DES; RC4)
- [ ] AES key size >= 256 bits; RSA >= 2048 bits; ECDSA >= P-256
- [ ] Authenticated encryption used (GCM mode, not ECB or raw CBC)
- [ ] IVs/nonces unique per operation, generated from CSPRNG
- [ ] No hardcoded keys or predictable seeds
- [ ] Key rotation mechanism exists

#### Phase 6: Error Handling and Logging
- [ ] No stack traces or system details in production error responses
- [ ] Security events logged: auth failures, access denials, input validation failures
- [ ] Logs don't contain secrets, session IDs, or full credit card numbers
- [ ] Log injection prevented (untrusted data sanitized before logging)

#### Phase 7: Dependency and Configuration
- [ ] Dependencies pinned to exact versions with lockfile committed
- [ ] No known vulnerabilities in dependencies (audit tools run in CI)
- [ ] Install scripts reviewed for new dependencies
- [ ] Debug mode disabled in production
- [ ] Security headers present (CSP, HSTS, X-Content-Type-Options, X-Frame-Options)
- [ ] CORS configuration restrictive (not `*`)

#### Phase 8: Language-Specific Checks
- [ ] **JS/TS:** No `eval()`, no `innerHTML` with user data, no prototype-pollutable deep merge, no ReDoS-vulnerable regex
- [ ] **Python:** No `pickle`/`yaml.load()` on untrusted data, no `subprocess(shell=True)` with user input, no `eval()`/`exec()`
- [ ] **Go:** No `unsafe` import without justification, no `InsecureSkipVerify`, goroutine leak patterns reviewed
- [ ] **Rust:** Every `unsafe` block has safety comments and minimal scope, FFI boundaries validated
- [ ] **Java:** No `ObjectInputStream` on untrusted data, Log4j >= 2.17.1, XXE protections on XML parsers, no JNDI with user input

---

## Appendix A: Primary Source Links

### Standards Organizations
- [OWASP Secure Coding Practices](https://owasp.org/www-project-secure-coding-practices-quick-reference-guide/)
- [OWASP Code Review Guide](https://owasp.org/www-project-code-review-guide/)
- [OWASP Cheat Sheet Series](https://cheatsheetseries.owasp.org/)
- [CWE/MITRE Top 25](https://cwe.mitre.org/top25/)
- [CWE Database](https://cwe.mitre.org/)
- [NIST SP 800-218 SSDF](https://csrc.nist.gov/pubs/sp/800/218/final)
- [SEI CERT Coding Standards](https://wiki.sei.cmu.edu/confluence/display/seccode)
- [SANS Top 25](https://www.sans.org/top25-software-errors)
- [Microsoft SDL](https://www.microsoft.com/en-us/securityengineering/sdl/practices)

### SAST Tools
- [Semgrep](https://semgrep.dev/)
- [CodeQL](https://codeql.github.com/)
- [SonarQube](https://www.sonarsource.com/products/sonarqube/)
- [Bandit](https://github.com/PyCQA/bandit)
- [Brakeman](https://brakemanscanner.org/)
- [eslint-plugin-security](https://www.npmjs.com/package/eslint-plugin-security)
- [eslint-plugin-no-unsanitized](https://github.com/mozilla/eslint-plugin-no-unsanitized)
- [Gosec](https://github.com/securego/gosec)
- [cargo-audit](https://github.com/rustsec/rustsec/tree/main/cargo-audit)
- [cargo-geiger](https://github.com/geiger-rs/cargo-geiger)
- [SpotBugs + Find Security Bugs](https://find-sec-bugs.github.io/)

### Secrets Detection
- [Gitleaks](https://github.com/gitleaks/gitleaks)
- [TruffleHog](https://github.com/trufflesecurity/trufflehog)
- [detect-secrets](https://github.com/Yelp/detect-secrets)

### Dependency Security
- [Socket.dev](https://socket.dev/)
- [Snyk](https://snyk.io/)
- [Trivy](https://github.com/aquasecurity/trivy)
- [OWASP Dependency-Check](https://owasp.org/www-project-dependency-check/)
- [govulncheck](https://go.dev/doc/security/vuln/)
- [pip-audit](https://github.com/pypa/pip-audit)
- [RustSec Advisory Database](https://rustsec.org/)

### Language-Specific Security References
- [Go Security Best Practices](https://go.dev/doc/security/best-practices)
- [Rust unsafe documentation](https://doc.rust-lang.org/book/ch20-01-unsafe-rust.html)
- [Google Rust Crate Audit Standards](https://github.com/google/rust-crate-audits/blob/main/auditing_standards.md)
- [MDN - Prototype Pollution](https://developer.mozilla.org/en-US/docs/Web/Security/Attacks/Prototype_pollution)
- [OWASP - ReDoS](https://owasp.org/www-community/attacks/Regular_expression_Denial_of_Service_-_ReDoS)
- [Snyk Learn](https://learn.snyk.io/)

### Vulnerability Databases
- [NVD (NIST)](https://nvd.nist.gov/)
- [GitHub Advisory Database](https://github.com/advisories)
- [OSV (Open Source Vulnerabilities)](https://osv.dev/)
- [Snyk Vulnerability Database](https://security.snyk.io/)
