# Server-Side Application Security — Deep Research

> Research compiled for building a security audit plugin for software projects.
> Focus: code-level security patterns, detection strategies, and actionable audit checks.
> Primary sources: OWASP, NIST, CWE, PortSwigger, Snyk.
> Date: 2026-04-04

---

## Table of Contents

1. [OWASP Top 10 (2021) Deep Dive](#1-owasp-top-10-2021-deep-dive)
2. [OWASP ASVS (Application Security Verification Standard)](#2-owasp-asvs)
3. [API Security](#3-api-security)
4. [Authentication & Authorization Patterns](#4-authentication--authorization-patterns)
5. [Data Protection in Code](#5-data-protection-in-code)
6. [Server-Side Request Handling](#6-server-side-request-handling)
7. [Database Security from Code Perspective](#7-database-security-from-code-perspective)
8. [Error Handling and Information Disclosure](#8-error-handling-and-information-disclosure)
9. [Logging and Monitoring for Security](#9-logging-and-monitoring-for-security)
10. [Master Reference Links](#10-master-reference-links)

---

## 1. OWASP Top 10 (2021) Deep Dive

Reference: https://owasp.org/Top10/

The OWASP Top 10 2021 represents the most critical web application security risks. Each category below includes CWE mappings, code-level detection patterns, and audit checks.

---

### A01: Broken Access Control

**Severity**: #1 — affects 94% of tested applications, 318,487 occurrences in dataset.

**Description**: Access control enforces policies so users cannot act outside intended permissions. Failures lead to unauthorized information disclosure, modification, or destruction of data, or performing business functions outside the user's limits.

**Common Vulnerability Patterns**:
- Violating least privilege or deny-by-default (resources accessible unless explicitly restricted)
- Bypassing access control checks via URL/parameter tampering, internal application state, or API request manipulation
- Insecure Direct Object References (IDOR) — viewing/editing another user's account by supplying their identifier
- Missing access control on POST, PUT, DELETE API endpoints
- Elevation of privilege — acting as a user without being logged in, or acting as admin when logged in as regular user
- Metadata manipulation — tampering with JWT, cookies, or hidden fields to elevate privileges
- CORS misconfiguration allowing API access from unauthorized/untrusted origins
- Force browsing to authenticated/privileged pages as unauthenticated user

**Code-Level Detection Patterns**:
```
# AUDIT CHECK: Look for these patterns

# 1. Direct object references without authorization check
GET /api/users/{userId}/profile   # Does handler verify requesting user == userId or has admin role?
GET /api/orders/{orderId}          # Is order ownership validated?

# 2. Missing authorization middleware/decorators
@app.route('/admin/users')         # No @require_role('admin') decorator
def list_users():                  # No authorization check in handler body

# 3. Client-side-only access control
if (user.role === 'admin') {       # JS-only check, no server enforcement
  showAdminPanel();
}

# 4. Horizontal privilege escalation via parameter manipulation
UPDATE accounts SET ... WHERE account_id = ?  # Is account_id from user input validated against session user?

# 5. Missing function-level access control
router.delete('/api/users/:id', deleteUser)  # No authz middleware before deleteUser
```

**Prevention Strategies**:
- Implement server-side access control that attackers cannot modify
- Deny by default — all resources require explicit authorization
- Centralize access control mechanisms; implement once, use everywhere
- Enforce record ownership rather than accepting that users can CRUD any record
- Disable web server directory listing; remove sensitive file metadata from webroot
- Log access control failures; alert administrators on repeated failures
- Rate-limit API and controller access to minimize automated attack impact
- Invalidate server-side session identifiers after logout; short-lived JWT tokens
- Use CORS restrictively; never use `Access-Control-Allow-Origin: *` for authenticated endpoints

**Key CWEs**: CWE-200 (Exposure of Sensitive Info), CWE-284 (Improper Access Control), CWE-285 (Improper Authorization), CWE-352 (CSRF), CWE-639 (Authorization Bypass Through User-Controlled Key), CWE-862 (Missing Authorization), CWE-863 (Incorrect Authorization), CWE-913 (Improper Control of Dynamically-Managed Code Resources)

**Audit Checklist**:
- [ ] Every endpoint has server-side authorization check
- [ ] Object references are validated against current user's permissions
- [ ] Admin functions are protected by role checks at server level
- [ ] CORS configuration uses explicit allowlists, not wildcards
- [ ] JWT tokens are validated server-side on every request
- [ ] Directory listing is disabled
- [ ] Access control failures are logged with user context
- [ ] Deny-by-default policy is implemented (not allow-by-default)

**References**:
- https://owasp.org/Top10/A01_2021-Broken_Access_Control/
- https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html
- https://cheatsheetseries.owasp.org/cheatsheets/Insecure_Direct_Object_Reference_Prevention_Cheat_Sheet.html
- https://cwe.mitre.org/data/definitions/862.html
- https://cwe.mitre.org/data/definitions/863.html

---

### A02: Cryptographic Failures

**Severity**: #2 — max incidence rate 46.44%, 29 mapped CWEs.

**Description**: Previously "Sensitive Data Exposure." Focuses on failures related to cryptography that lead to exposure of sensitive data. Root causes rather than symptoms.

**Common Vulnerability Patterns**:
- Data transmitted in cleartext (HTTP, SMTP, FTP)
- Old or weak cryptographic algorithms (MD5, SHA1 for passwords, DES, RC4)
- Default or reused cryptographic keys; no key rotation
- Missing encryption enforcement; missing HTTP Strict Transport Security (HSTS) header
- Server certificate not properly validated by clients
- Initialization vectors ignored, reused, or generated insecurely; use of ECB mode
- Passwords used directly as encryption keys (without key derivation function)
- Non-cryptographic PRNG used where cryptographic randomness is required
- Deprecated hash functions for password storage
- Deprecated padding schemes (PKCS#1 v1.5)

**Code-Level Detection Patterns**:
```
# AUDIT CHECK: Grep for these anti-patterns

# 1. Weak hashing
import hashlib
hashlib.md5(password)              # FAIL: MD5 for passwords
hashlib.sha1(password)             # FAIL: SHA1 for passwords
hashlib.sha256(password)           # FAIL: unsalted, fast hash for passwords

# 2. Hardcoded keys/secrets
SECRET_KEY = "my-secret-key-123"   # FAIL: hardcoded
AES_KEY = b'\x00' * 16            # FAIL: predictable key
DB_PASSWORD = "admin123"           # FAIL: hardcoded credential

# 3. Weak encryption
from Crypto.Cipher import DES      # FAIL: DES is broken
cipher = AES.new(key, AES.MODE_ECB)  # FAIL: ECB mode
cipher = AES.new(key, AES.MODE_CBC, iv=b'\x00'*16)  # FAIL: static IV

# 4. Insecure random
import random
token = random.randint(0, 999999)  # FAIL: predictable PRNG
session_id = str(random.random())  # FAIL: not cryptographically secure

# 5. Missing TLS enforcement
app.run(ssl_context=None)          # No TLS
SECURE_SSL_REDIRECT = False        # Django: TLS not enforced

# 6. Sensitive data in logs/responses
logger.info(f"User {user} password: {password}")  # FAIL
return {"ssn": user.ssn, ...}      # FAIL: PII in API response without need
```

**Prevention Strategies**:
- Classify data processed, stored, and transmitted; identify sensitive data per privacy laws and business needs
- Do not store sensitive data unnecessarily; discard as soon as possible; use tokenization or truncation
- Encrypt all sensitive data at rest using strong algorithms (AES-256-GCM)
- Enforce TLS with strong ciphers and forward secrecy (TLS 1.2+); enforce via HSTS
- Disable caching for responses containing sensitive data
- Use password-specific hashing: Argon2id, scrypt, bcrypt, or PBKDF2 (see Section 4)
- Use authenticated encryption (AES-GCM, ChaCha20-Poly1305); never ECB mode
- Generate keys with cryptographically secure random sources
- Use established libraries; never implement custom crypto

**Key CWEs**: CWE-259 (Hardcoded Password), CWE-319 (Cleartext Transmission), CWE-326 (Inadequate Encryption Strength), CWE-327 (Broken Crypto Algorithm), CWE-328 (Weak Hash), CWE-330 (Insufficient Randomness), CWE-331 (Insufficient Entropy)

**Audit Checklist**:
- [ ] All data in transit uses TLS 1.2+ with HSTS header
- [ ] Passwords use Argon2id, bcrypt, scrypt, or PBKDF2 (not MD5/SHA)
- [ ] No hardcoded secrets, keys, or passwords in source code
- [ ] Encryption at rest uses AES-256-GCM or equivalent authenticated encryption
- [ ] Cryptographic keys are generated from CSPRNG; never hardcoded
- [ ] ECB mode is never used; IVs are unique and randomly generated
- [ ] Sensitive data is not logged or cached unnecessarily
- [ ] Certificate validation is enforced on all outbound TLS connections

**References**:
- https://owasp.org/Top10/A02_2021-Cryptographic_Failures/
- https://cheatsheetseries.owasp.org/cheatsheets/Cryptographic_Storage_Cheat_Sheet.html
- https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html
- https://cheatsheetseries.owasp.org/cheatsheets/Transport_Layer_Security_Cheat_Sheet.html
- https://cwe.mitre.org/data/definitions/327.html

---

### A03: Injection

**Severity**: #3 — 94% of applications tested for injection, max incidence rate 19%, 274,228 occurrences, 33 mapped CWEs.

**Description**: An application is vulnerable when user-supplied data is not validated, filtered, or sanitized; dynamic queries or non-parameterized calls are used; hostile data is used within ORM search parameters; hostile data is directly concatenated into dynamic queries, commands, or stored procedures.

**Injection Types**:
- **SQL Injection**: Direct concatenation of user input into SQL queries
- **NoSQL Injection**: Operator injection in MongoDB queries (`$gt`, `$ne`, `$regex`)
- **OS Command Injection**: User input passed to system calls (`exec`, `system`, `popen`)
- **LDAP Injection**: User input in LDAP filters without escaping
- **ORM Injection**: Unsafe use of ORM query builders with raw input
- **Expression Language / Template Injection**: SSTI via Jinja2, Thymeleaf, Freemarker, etc.
- **XPath/XQuery Injection**: User input in XML query expressions

**Code-Level Detection Patterns**:
```
# AUDIT CHECK: SQL Injection
# DANGEROUS — string concatenation in queries
query = "SELECT * FROM users WHERE name = '" + username + "'"
query = f"SELECT * FROM users WHERE id = {user_id}"
cursor.execute("SELECT * FROM users WHERE name = '%s'" % name)
db.query("DELETE FROM orders WHERE id = " + req.params.id)

# SAFE — parameterized queries
cursor.execute("SELECT * FROM users WHERE name = ?", (username,))
cursor.execute("SELECT * FROM users WHERE name = %s", [username])
PreparedStatement ps = conn.prepareStatement("SELECT * FROM users WHERE name = ?");

# AUDIT CHECK: NoSQL Injection (MongoDB)
# DANGEROUS
db.users.find({username: req.body.username, password: req.body.password})
# Attacker sends: {"username": "admin", "password": {"$ne": ""}}

# SAFE
db.users.find({username: String(req.body.username), password: String(req.body.password)})

# AUDIT CHECK: OS Command Injection
# DANGEROUS
os.system("ping " + user_input)
subprocess.call("ls " + directory, shell=True)
exec("rm -rf " + path)
child_process.exec("git clone " + url)

# SAFE
subprocess.run(["ping", "-c", "4", validated_ip], shell=False)

# AUDIT CHECK: LDAP Injection
# DANGEROUS
filter = "(uid=" + username + ")"
# Attacker sends: *)(uid=*))(|(uid=*

# AUDIT CHECK: ORM Injection
# DANGEROUS (SQLAlchemy)
User.query.filter("name = '" + name + "'")
# SAFE
User.query.filter(User.name == name)
User.query.filter_by(name=name)

# AUDIT CHECK: Template Injection (SSTI)
# DANGEROUS
template = Template(user_input)  # Jinja2 SSTI
render_template_string(user_input)
```

**Prevention Strategies**:
1. **Use parameterized queries / prepared statements** — the database always distinguishes between code and data
2. **Use safe APIs** that provide parameterized interfaces; or use ORMs (but beware raw query methods)
3. **Server-side input validation** using positive allowlisting (syntactic and semantic)
4. **Escape special characters** using the specific escape syntax for the target interpreter (last resort — fragile)
5. **Use LIMIT and other SQL controls** to prevent mass disclosure on injection

**Key CWEs**: CWE-20 (Improper Input Validation), CWE-77 (Command Injection), CWE-78 (OS Command Injection), CWE-79 (XSS), CWE-89 (SQL Injection), CWE-90 (LDAP Injection), CWE-94 (Code Injection), CWE-643 (XPath Injection)

**Audit Checklist**:
- [ ] All SQL queries use parameterized statements or prepared statements
- [ ] No string concatenation/interpolation in any query construction
- [ ] ORM raw query methods are not used with user input
- [ ] OS command execution uses array-based APIs (not shell=True)
- [ ] User input is never passed to `eval()`, `exec()`, template constructors
- [ ] LDAP queries use proper escaping libraries
- [ ] NoSQL queries cast user input to expected types
- [ ] Input validation uses allowlists, not denylists

**References**:
- https://owasp.org/Top10/A03_2021-Injection/
- https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html
- https://cheatsheetseries.owasp.org/cheatsheets/OS_Command_Injection_Defense_Cheat_Sheet.html
- https://cheatsheetseries.owasp.org/cheatsheets/LDAP_Injection_Prevention_Cheat_Sheet.html
- https://cheatsheetseries.owasp.org/cheatsheets/Injection_Prevention_Cheat_Sheet.html
- https://portswigger.net/web-security/sql-injection
- https://portswigger.net/web-security/server-side-template-injection
- https://cwe.mitre.org/data/definitions/89.html

---

### A04: Insecure Design

**Severity**: #4 — new category in 2021, 40 mapped CWEs.

**Description**: Insecure design is a broad category representing missing or ineffective security controls at the design level. An insecure design cannot be fixed by a perfect implementation — the necessary security controls were never created to defend against specific attacks. This is distinct from implementation bugs.

**Common Vulnerability Patterns**:
- Missing threat modeling for critical authentication, access control, and business logic flows
- No abuse case / misuse case testing
- Trust boundary violations — not treating data from other components as untrusted
- Credential recovery using knowledge-based questions (violates NIST 800-63b)
- Missing rate limiting on business-critical flows (e.g., bulk purchases, account creation)
- No anti-automation controls where needed (CAPTCHAs, bot detection)
- Missing tenant isolation in multi-tenant applications

**Code-Level Detection Patterns**:
```
# AUDIT CHECK: Insecure Design Indicators

# 1. No rate limiting on sensitive endpoints
@app.route('/api/login', methods=['POST'])
def login():  # No rate limiter applied
    ...

# 2. Security questions for account recovery
if answer == user.security_answer:  # Knowledge-based recovery is insecure
    reset_password(user)

# 3. Missing business logic validation
def purchase(user, quantity):
    # No check for maximum quantity, negative values, or excessive bulk
    total = price * quantity
    charge(user, total)

# 4. No tenant isolation
def get_data(tenant_id):
    # tenant_id comes from user input, not from authenticated session
    return db.query("SELECT * FROM data WHERE tenant = ?", tenant_id)

# 5. Missing resource consumption limits
def process_upload(file):
    # No size limit, no file count limit, no rate limit
    save(file)
```

**Prevention Strategies**:
- Establish and use a secure development lifecycle with AppSec professionals
- Build and use a library of secure design patterns and paved road components
- Integrate threat modeling into refinement sessions or similar activities
- Write unit and integration tests to validate that all critical flows are resistant to the threat model
- Segregate tenants by design at all tiers
- Limit resource consumption by user or service

**Key CWEs**: CWE-209 (Generation of Error Message Containing Sensitive Info), CWE-256 (Unprotected Storage of Credentials), CWE-501 (Trust Boundary Violation), CWE-522 (Insufficiently Protected Credentials)

**Audit Checklist**:
- [ ] Threat model exists for authentication, access control, and business logic flows
- [ ] Rate limiting is applied to sensitive operations (login, registration, password reset, purchases)
- [ ] Business logic enforces constraints server-side (quantity limits, price validation)
- [ ] Multi-tenant data is isolated; tenant ID derived from session, not user input
- [ ] Account recovery does not use knowledge-based questions
- [ ] Anti-automation controls protect business-critical flows
- [ ] Resource consumption limits are enforced per user/session

**References**:
- https://owasp.org/Top10/A04_2021-Insecure_Design/
- https://cheatsheetseries.owasp.org/cheatsheets/Threat_Modeling_Cheat_Sheet.html
- https://cheatsheetseries.owasp.org/cheatsheets/Abuse_Case_Cheat_Sheet.html

---

### A05: Security Misconfiguration

**Severity**: #5 — 90% of applications tested had some misconfiguration, 208,000+ CWE occurrences.

**Description**: The application is vulnerable if it has improper security hardening across any part of the application stack, or improperly configured permissions on cloud services.

**Common Vulnerability Patterns**:
- Unnecessary features enabled (ports, services, pages, accounts, privileges)
- Default accounts with unchanged passwords
- Error handling reveals stack traces or overly informative error messages to users
- Security features disabled or not configured in upgraded systems
- Security settings in application servers, frameworks, libraries, databases not set to secure values
- Missing or misconfigured security headers (CSP, X-Frame-Options, HSTS, etc.)
- Software is out of date or vulnerable
- XXE enabled in XML parsers

**Code-Level Detection Patterns**:
```
# AUDIT CHECK: Security Misconfiguration

# 1. Debug mode in production
DEBUG = True                        # Django
app.run(debug=True)                 # Flask
NODE_ENV=development                # Node.js

# 2. Default/weak credentials
ADMIN_PASSWORD = "admin"
DEFAULT_USER = "sa"
connectionString = "...;Password=;"

# 3. Missing security headers
# Check HTTP response for absence of:
# Strict-Transport-Security, Content-Security-Policy,
# X-Content-Type-Options, X-Frame-Options, Referrer-Policy

# 4. Overly permissive CORS
Access-Control-Allow-Origin: *
Access-Control-Allow-Credentials: true

# 5. XML External Entity (XXE) — parser not hardened
DocumentBuilderFactory dbf = DocumentBuilderFactory.newInstance();
# Missing: dbf.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);

# 6. Directory listing enabled
# Apache: Options +Indexes
# Nginx: autoindex on;

# 7. Verbose error responses
app.use((err, req, res, next) => {
  res.status(500).json({ error: err.stack });  # FAIL: stack trace to client
});
```

**Prevention Strategies**:
- Repeatable hardening process across dev/QA/prod, automated where possible
- Minimal platform — remove unused features, components, documentation, samples
- Review and update configurations as part of patch management process
- Segmented application architecture with containerization or cloud security groups
- Send security directives to clients (security headers)
- Automated process to verify configuration effectiveness across all environments

**Key CWEs**: CWE-2 (Environmental), CWE-16 (Configuration), CWE-260 (Password in Configuration File), CWE-611 (XXE), CWE-614 (Sensitive Cookie Without Secure Flag), CWE-756 (Missing Custom Error Page)

**Audit Checklist**:
- [ ] Debug mode is disabled in production
- [ ] No default credentials exist in deployment
- [ ] Security headers are present and correctly configured
- [ ] CORS is restrictively configured (no wildcards with credentials)
- [ ] XML parsers have DTD/XXE disabled
- [ ] Directory listing is disabled
- [ ] Error responses do not leak stack traces or system information
- [ ] Unnecessary ports, services, and features are disabled
- [ ] TLS is properly configured with strong ciphers

**References**:
- https://owasp.org/Top10/A05_2021-Security_Misconfiguration/
- https://cheatsheetseries.owasp.org/cheatsheets/XML_External_Entity_Prevention_Cheat_Sheet.html
- https://cheatsheetseries.owasp.org/cheatsheets/Infrastructure_as_Code_Security_Cheat_Sheet.html

---

### A06: Vulnerable and Outdated Components

**Severity**: #6 — ranked #2 in community survey. The only Top 10 category without mapped CVEs (uses default 5.0 exploit/impact weight).

**Description**: Applications using components with known vulnerabilities. This includes the OS, web/application server, DBMS, APIs, libraries, frameworks, and all runtime environments.

**Common Vulnerability Patterns**:
- Unknown versions of all components used (client-side and server-side), including nested dependencies
- Vulnerable, unsupported, or out-of-date software (OS, web server, DBMS, applications, APIs, libraries, runtimes)
- No regular scanning for vulnerabilities; no monitoring of security advisories
- Delayed patching due to change control cycles (monthly/quarterly)
- Developers do not test compatibility of updated/patched libraries
- Component security settings are not properly configured

**Code-Level Detection Patterns**:
```
# AUDIT CHECK: Dependency vulnerability indicators

# 1. Check lockfiles for known vulnerable versions
# package-lock.json, yarn.lock, Pipfile.lock, Gemfile.lock, go.sum, pom.xml

# 2. Look for outdated dependency management
# No lockfile present
# Loose version ranges: "express": ">=4.0.0" or "*"

# 3. Check for presence of SCA tooling in CI/CD
# Presence of: npm audit, snyk test, safety check, bundler-audit,
# OWASP Dependency-Check, Dependabot config, Renovate config

# 4. Look for deprecated/known-vulnerable libraries
# e.g., lodash < 4.17.21, log4j < 2.17.0, Spring < 5.3.18
# Jackson-databind < 2.13.4, moment.js (deprecated)

# 5. Check for SRI (Subresource Integrity) on CDN scripts
<script src="https://cdn.example.com/lib.js">  # FAIL: no integrity attribute
<script src="https://cdn.example.com/lib.js"
  integrity="sha384-..." crossorigin="anonymous">  # SAFE
```

**Prevention Strategies**:
- Remove unused dependencies, unnecessary features, components, files, and documentation
- Continuously inventory component versions using tools like OWASP Dependency-Check, retire.js
- Monitor sources like CVE, NVD for component vulnerabilities; automate with software composition analysis (SCA)
- Obtain components from official sources over secure links; prefer signed packages
- Monitor for unmaintained libraries without security patches; consider virtual patches if needed
- Establish organizational patch management policy with timelines based on risk

**Key CWEs**: CWE-937 (Using Components with Known Vulnerabilities), CWE-1035 (same, 2017), CWE-1104 (Use of Unmaintained Third-Party Components)

**Audit Checklist**:
- [ ] Software Bill of Materials (SBOM) exists and is current
- [ ] SCA tool runs in CI/CD pipeline (Dependabot, Snyk, OWASP Dependency-Check)
- [ ] No components with known critical/high CVEs
- [ ] Lockfiles are present and used for reproducible builds
- [ ] CDN-loaded scripts use Subresource Integrity (SRI)
- [ ] Patch management policy defines remediation timelines
- [ ] Transitive/nested dependencies are tracked

**References**:
- https://owasp.org/Top10/A06_2021-Vulnerable_and_Outdated_Components/
- https://cheatsheetseries.owasp.org/cheatsheets/Vulnerable_Dependency_Management_Cheat_Sheet.html
- https://owasp.org/www-project-dependency-check/
- https://cwe.mitre.org/data/definitions/1104.html

---

### A07: Identification and Authentication Failures

**Severity**: #7 — previously #2 (Broken Authentication), 22 mapped CWEs.

**Description**: Confirmation of the user's identity, authentication, and session management is critical. Failures in these areas lead to account compromise.

**Common Vulnerability Patterns**:
- Permits brute force or automated credential stuffing attacks
- Permits default, weak, or well-known passwords (e.g., "Password1", "admin/admin")
- Uses weak credential recovery (knowledge-based questions)
- Uses plain text, encrypted (reversible), or weakly hashed passwords
- Missing or ineffective multi-factor authentication (MFA)
- Exposes session identifier in the URL
- Reuses session identifier after successful login (session fixation)
- Does not correctly invalidate session IDs on logout or after idle timeout

**Code-Level Detection Patterns**:
```
# AUDIT CHECK: Authentication Failures

# 1. Weak password hashing
user.password = hashlib.sha256(password.encode()).hexdigest()  # FAIL
user.password = md5(password)                                   # FAIL
user.password = encrypt(password, key)                          # FAIL: reversible

# SAFE: use adaptive hashing
user.password = bcrypt.hashpw(password, bcrypt.gensalt(rounds=12))
user.password = argon2.hash(password)

# 2. No brute force protection
@app.route('/login', methods=['POST'])
def login():
    user = User.query.filter_by(email=email).first()
    if user and check_password(password, user.password):
        return success  # No rate limiting, no account lockout, no CAPTCHA

# 3. Session fixation
# Session ID not regenerated after login
session['user'] = user.id  # Without calling session.regenerate() first

# 4. User enumeration
if not user:
    return "User not found"      # FAIL: different message reveals user existence
if not check_password():
    return "Invalid password"    # FAIL: reveals the user does exist

# SAFE: generic message
return "Invalid username or password"

# 5. Missing session timeout
SESSION_COOKIE_AGE = 31536000    # 1 year — too long
# No idle timeout configured

# 6. Session in URL
redirect(f"/dashboard?session_id={sid}")  # FAIL: session ID in URL
```

**Prevention Strategies**:
- Implement multi-factor authentication (prevents automated credential stuffing, brute force, stolen credential reuse)
- Do not ship/deploy with default credentials
- Check passwords against breached password lists (Have I Been Pwned)
- Align password policies with NIST 800-63b: min 8 chars with MFA, min 15 without; allow all characters; no composition rules
- Use server-side, secure session manager generating random high-entropy session IDs; IDs not in URL; invalidated after logout; idle and absolute timeouts
- Limit and increasingly delay failed login attempts; log all failures; alert on credential stuffing/brute force

**Key CWEs**: CWE-287 (Improper Authentication), CWE-384 (Session Fixation), CWE-521 (Weak Password Requirements), CWE-613 (Insufficient Session Expiration), CWE-798 (Hard-coded Credentials)

**Audit Checklist**:
- [ ] Passwords stored with Argon2id, bcrypt, scrypt, or PBKDF2
- [ ] MFA is available (ideally enforced for sensitive operations)
- [ ] Brute force protection exists (rate limiting, account lockout, CAPTCHA)
- [ ] Login responses do not enable user enumeration
- [ ] Session IDs regenerated after authentication
- [ ] Session timeouts enforced server-side (idle + absolute)
- [ ] Sessions invalidated on logout
- [ ] Default credentials are not present
- [ ] Password policy follows NIST 800-63b guidelines

**References**:
- https://owasp.org/Top10/A07_2021-Identification_and_Authentication_Failures/
- https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html
- https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html
- https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html
- https://pages.nist.gov/800-63-3/sp800-63b.html
- https://cwe.mitre.org/data/definitions/287.html

---

### A08: Software and Data Integrity Failures

**Severity**: #8 — 10 mapped CWEs, includes deserialization and supply chain attacks.

**Description**: Failures related to code and infrastructure that does not protect against integrity violations. Includes insecure CI/CD pipelines, auto-update without verification, and insecure deserialization.

**Common Vulnerability Patterns**:
- Applications relying on plugins, libraries, or modules from untrusted sources/CDNs without integrity verification
- Insecure CI/CD pipeline allowing unauthorized access, malicious code injection, or insufficient segregation
- Auto-update functionality without integrity verification (unsigned updates)
- Insecure deserialization — objects serialized and transmitted where attackers can see/modify structure

**Code-Level Detection Patterns**:
```
# AUDIT CHECK: Integrity Failures

# 1. Insecure Deserialization
# DANGEROUS patterns by language:

# Python
pickle.loads(user_data)                    # CRITICAL: arbitrary code execution
yaml.load(user_data)                       # CRITICAL: use yaml.safe_load()
yaml.load(user_data, Loader=yaml.Loader)   # CRITICAL: unsafe loader

# Java
ObjectInputStream ois = new ObjectInputStream(untrustedStream);
ois.readObject();                          # CRITICAL: gadget chain RCE
XMLDecoder decoder = new XMLDecoder(untrustedStream);  # CRITICAL

# PHP
unserialize($user_input);                  # CRITICAL
# SAFE: json_decode($user_input)

# .NET
BinaryFormatter bf = new BinaryFormatter();
bf.Deserialize(untrustedStream);           # CRITICAL: never use BinaryFormatter

# Node.js
node-serialize: require('node-serialize').unserialize(data)  # CRITICAL
js-yaml: yaml.load(data)                   # Use yaml.safeLoad() / yaml.load(data, { schema: yaml.SAFE_SCHEMA })

# 2. Missing integrity checks on dependencies
<script src="https://cdn.example.com/lib.js">           # No SRI
pip install package-from-unknown-source
npm install --registry http://untrusted-registry.com

# 3. CI/CD integrity issues
# Look for: no branch protection, no required reviews,
# secrets in plaintext in CI config, no signed commits,
# no artifact signing, writable pipeline configs by non-admin
```

**Safe Deserialization Alternatives**:
- Use JSON, XML, or Protocol Buffers for data interchange instead of native serialization
- If native serialization is required, implement allowlist-based type restrictions
- Implement integrity checks (digital signatures, HMAC) on serialized data before deserialization
- Isolate deserialization in low-privilege environments

**Key CWEs**: CWE-345 (Insufficient Verification of Data Authenticity), CWE-494 (Download of Code Without Integrity Check), CWE-502 (Deserialization of Untrusted Data), CWE-829 (Inclusion of Functionality from Untrusted Control Sphere)

**Audit Checklist**:
- [ ] No native deserialization of untrusted data (pickle, ObjectInputStream, BinaryFormatter, unserialize)
- [ ] YAML parsing uses safe loaders only
- [ ] CDN resources use Subresource Integrity (SRI)
- [ ] Dependencies sourced from trusted registries only
- [ ] CI/CD pipeline has branch protection, required reviews, and access controls
- [ ] Software updates are signed and verified
- [ ] Artifact signing is used for build outputs

**References**:
- https://owasp.org/Top10/A08_2021-Software_and_Data_Integrity_Failures/
- https://cheatsheetseries.owasp.org/cheatsheets/Deserialization_Cheat_Sheet.html
- https://cwe.mitre.org/data/definitions/502.html

---

### A09: Security Logging and Monitoring Failures

**Severity**: #9 — community survey ranked this #3.

**Description**: Without logging and monitoring, breaches cannot be detected. Insufficient logging, detection, monitoring, and active response occurs at any time. Average time to detect a breach is over 200 days, typically detected by external parties.

**Common Vulnerability Patterns**:
- Auditable events (logins, failed logins, high-value transactions) are not logged
- Warnings and errors generate no, inadequate, or unclear log messages
- Logs of applications and APIs are not monitored for suspicious activity
- Logs are only stored locally (no centralized log management)
- Alerting thresholds and response escalation processes are not in place
- Penetration testing and DAST scans do not trigger alerts
- Application cannot detect, escalate, or alert for active attacks in real-time or near real-time
- Log data is vulnerable to injection attacks (log forging)

**Code-Level Detection Patterns**:
```
# AUDIT CHECK: Logging Failures

# 1. Missing security event logging
def login(username, password):
    user = authenticate(username, password)
    if not user:
        return error  # FAIL: no log of failed login attempt
    # FAIL: no log of successful login

# 2. Sensitive data in logs
logger.info(f"Login attempt: user={username}, password={password}")  # FAIL
logger.info(f"Payment: card={card_number}")                          # FAIL
logger.info(f"Session: token={session_token}")                       # FAIL
logger.info(f"API call with key: {api_key}")                         # FAIL

# 3. Log injection vulnerability
logger.info(f"User action: {user_input}")  # FAIL if user_input contains \n
# Attacker injects: "action\n[INFO] Admin logged in from 127.0.0.1"
# Creates fake log entry

# SAFE: structured logging
logger.info("login_failed", extra={"username": username, "ip": request.remote_addr})

# 4. Missing audit trail for high-value operations
def transfer_funds(from_acct, to_acct, amount):
    # No audit log before or after the transfer
    execute_transfer(from_acct, to_acct, amount)

# 5. No alerting configuration
# Check for: no alert rules, no threshold configs, no SIEM integration
```

**Prevention Strategies**:
- Log all login, access control, and server-side input validation failures with sufficient user context to identify suspicious accounts; hold logs long enough for delayed forensic analysis
- Use log format compatible with centralized log management solutions (ELK, Splunk, etc.)
- Encode log data correctly to prevent log injection (sanitize CR, LF, delimiters)
- Establish audit trails with integrity controls for high-value transactions (append-only storage)
- Establish effective monitoring and alerting so suspicious activities are detected and responded to quickly
- Adopt incident response and recovery plan (NIST 800-61r2 or later)

**Key CWEs**: CWE-117 (Improper Output Neutralization for Logs), CWE-223 (Omission of Security-relevant Information), CWE-532 (Insertion of Sensitive Information into Log File), CWE-778 (Insufficient Logging)

**Audit Checklist**:
- [ ] Authentication events (success and failure) are logged
- [ ] Access control failures are logged
- [ ] High-value transactions have audit trails
- [ ] Logs do not contain passwords, tokens, keys, PII, or card data
- [ ] Log injection is prevented via structured logging or output encoding
- [ ] Logs are sent to centralized management (not local-only)
- [ ] Alerting thresholds are configured for security events
- [ ] Log integrity is protected (append-only, tamper detection)

**References**:
- https://owasp.org/Top10/A09_2021-Security_Logging_and_Monitoring_Failures/
- https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html
- https://cheatsheetseries.owasp.org/cheatsheets/Logging_Vocabulary_Cheat_Sheet.html
- https://csrc.nist.gov/pubs/sp/800/61/r2/final (NIST Incident Handling Guide)
- https://cwe.mitre.org/data/definitions/778.html

---

### A10: Server-Side Request Forgery (SSRF)

**Severity**: #10 — CWE-918, incidence rate relatively low but high severity impact. Added after community survey ranking.

**Description**: SSRF flaws occur whenever a web application fetches a remote resource without validating the user-supplied URL. This allows an attacker to coerce the application to send a crafted request to an unexpected destination, even when protected by a firewall, VPN, or other network access controls.

**Attack Vectors**:
- **Internal port scanning**: Enumerate open ports on internal servers via connection timing
- **Local file access**: `file:///etc/passwd`, `file:///C:/Windows/win.ini`
- **Cloud metadata access**: `http://169.254.169.254/latest/meta-data/` (AWS), `http://metadata.google.internal/` (GCP)
- **Internal service exploitation**: Access internal APIs, databases, admin panels via `http://localhost:PORT`
- **DNS rebinding**: Bypass allowlists by having DNS resolve to internal IPs after validation

**Code-Level Detection Patterns**:
```
# AUDIT CHECK: SSRF Vulnerabilities

# 1. Unvalidated URL from user input
response = requests.get(user_provided_url)                    # CRITICAL
fetch(req.query.url)                                          # CRITICAL
HttpClient.GetAsync(userUrl)                                  # CRITICAL
URL url = new URL(request.getParameter("target")); url.openConnection();  # CRITICAL

# 2. URL used for image/file fetching
def fetch_avatar(url):
    return requests.get(url).content  # SSRF if URL is user-controlled

# 3. Webhook/callback URLs from user input
def register_webhook(callback_url):
    # Later: requests.post(callback_url, data=event_data)
    # Attacker registers: http://169.254.169.254/latest/meta-data/

# 4. PDF/image rendering with URL input
def generate_pdf(html_url):
    wkhtmltopdf(html_url)  # SSRF via HTML containing <img src="http://internal/">

# 5. Redirect following
response = requests.get(url, allow_redirects=True)  # May redirect to internal IP
```

**Prevention — Application Layer**:
- Validate and sanitize ALL client-supplied URL/input data
- Enforce URL schema (https only), port, and destination with positive allowlists
- Do not accept complete URLs from users when possible — accept identifiers and construct URLs server-side
- Do not send raw responses to clients (avoid becoming an open proxy)
- Disable HTTP redirections in HTTP clients
- Be aware of URL consistency to prevent DNS rebinding and TOCTOU attacks
- Do NOT rely on denylists or regex — attackers have extensive bypass techniques

**Prevention — Network Layer**:
- Segment remote resource access into separate networks
- Enforce "deny by default" firewall policies blocking all but essential intranet traffic
- Use AWS IMDSv2 (requires PUT with token) instead of IMDSv1

**Key CWE**: CWE-918 (Server-Side Request Forgery)

**Audit Checklist**:
- [ ] No user-supplied URLs passed directly to server-side HTTP clients
- [ ] URL validation uses allowlists (not denylists)
- [ ] HTTP redirect following is disabled in server-side HTTP clients
- [ ] Cloud metadata endpoints are blocked at network and/or application layer
- [ ] IMDSv2 is enforced on AWS instances
- [ ] Network segmentation limits internal access from application servers
- [ ] Webhook/callback URLs are validated against allowlists
- [ ] DNS resolution results are validated against internal IP ranges

**References**:
- https://owasp.org/Top10/A10_2021-Server-Side_Request_Forgery_(SSRF)/
- https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html
- https://portswigger.net/web-security/ssrf
- https://cwe.mitre.org/data/definitions/918.html

---

## 2. OWASP ASVS

Reference: https://owasp.org/www-project-application-security-verification-standard/
GitHub: https://github.com/OWASP/ASVS

The OWASP Application Security Verification Standard (ASVS) provides a framework of security requirements for designing, developing, and testing web applications and web services.

### Verification Levels

| Level | Name | Target | Description |
|-------|------|--------|-------------|
| **L1** | First Steps | All applications | Minimum security for any application. Automated testing and whole-portfolio baseline. ASVS 5.0 has 70 L1 requirements (20% of total). |
| **L2** | Standard | Most applications | Recommended standard for apps handling sensitive data (business transactions, healthcare, sensitive functions). |
| **L3** | Advanced | High-value / high-assurance | Maximum trust — critical systems, military, health, safety, critical infrastructure. High-value transactions, protected health information. |

### ASVS 5.0 Chapter Structure (Released May 2025)

ASVS 5.0 restructured significantly from 4.x. The chapters are:

| Chapter | Domain |
|---------|--------|
| V1 | Encoding and Sanitization |
| V2 | Validation and Business Logic |
| V3 | Web Frontend Security (new) |
| V4 | API and Web Service |
| V5 | File Handling |
| V6 | Authentication |
| V7 | Session Management |
| V8 | Authorization |
| V9 | Self-contained Tokens (new) |
| V10 | OAuth and OIDC (new) |
| V11 | Cryptography |
| V12 | Secure Communication |
| V13 | Configuration |
| V14 | Data Protection |
| V15 | Secure Coding and Architecture (new) |
| V16 | Security Logging and Error Handling |
| V17 | WebRTC (new) |

> Note: ASVS 4.x had V1 (Architecture) which has been removed in 5.0; its requirements were redistributed to relevant chapters.

### Using ASVS for Code Review

**As an audit checklist**, each ASVS requirement becomes a verifiable check during code review:

1. **Select the appropriate level** (L1/L2/L3) based on application risk profile
2. **Extract requirements** for each chapter relevant to the code under review
3. **Map to code patterns** — each requirement translates to specific code-level checks
4. **Track compliance** using the requirement identifier format: `<chapter>.<section>.<requirement>`

**Most Critical Sections for Code Review**:
- **V1 (Encoding/Sanitization)**: Injection prevention, output encoding, XSS prevention
- **V6 (Authentication)**: Password storage, credential security, MFA
- **V7 (Session Management)**: Session IDs, timeouts, fixation
- **V8 (Authorization)**: Access control enforcement, IDOR prevention
- **V11 (Cryptography)**: Algorithm selection, key management, random generation
- **V14 (Data Protection)**: Sensitive data handling, PII protection

**ASVS-to-Cheat-Sheet Index**: https://cheatsheetseries.owasp.org/IndexASVS.html

**References**:
- https://owasp.org/www-project-application-security-verification-standard/
- https://github.com/OWASP/ASVS/tree/v5.0.0
- https://devguide.owasp.org/en/03-requirements/05-asvs/

---

## 3. API Security

### OWASP API Security Top 10 (2023)

Reference: https://owasp.org/API-Security/editions/2023/en/0x11-t10/

| # | Risk | Description | Code-Level Detection |
|---|------|-------------|---------------------|
| **API1** | Broken Object Level Authorization | APIs expose endpoints handling object identifiers without verifying the requesting user owns or can access that object. | Check every endpoint that takes an ID parameter — does it verify the authenticated user has access to that specific object? |
| **API2** | Broken Authentication | Authentication mechanisms implemented incorrectly — missing token validation, weak token generation, no rate limiting on auth endpoints. | Look for endpoints without auth middleware, weak token validation, missing rate limits on login/token endpoints. |
| **API3** | Broken Object Property Level Authorization | Excessive data exposure combined with mass assignment. API returns more properties than needed; accepts properties that shouldn't be user-modifiable. | Check API responses for over-exposure. Check request handlers for mass assignment (accepting all fields into model updates). |
| **API4** | Unrestricted Resource Consumption | No rate limiting, no payload size limits, no pagination limits, no limits on expensive operations. | Look for missing rate limiters, unbounded query results, no pagination, unlimited file upload sizes. |
| **API5** | Broken Function Level Authorization | Complex permission hierarchies with unclear separation between admin/user functions. | Check if admin endpoints are accessible by regular users. Look for role checks only on some endpoints. |
| **API6** | Unrestricted Access to Sensitive Business Flows | Business flows exposed without compensating controls for automated abuse. | Ticket purchasing, comment posting, reservation flows without bot detection, CAPTCHA, or rate limiting. |
| **API7** | Server Side Request Forgery | API fetches remote resources without validating user-supplied URI. | Same as A10 OWASP Top 10. See SSRF section above. |
| **API8** | Security Misconfiguration | Missing security hardening, misconfigured headers, verbose error messages, unnecessary HTTP methods enabled. | Same as A05 OWASP Top 10. See Security Misconfiguration section above. |
| **API9** | Improper Inventory Management | Exposed deprecated API versions, unpatched debug endpoints, outdated documentation, missing API versioning strategy. | Look for: `/api/v1/` still accessible alongside `/api/v2/`, debug/test endpoints in production, no API inventory. |
| **API10** | Unsafe Consumption of APIs | Third-party API data trusted without validation. Data from external APIs not sanitized before use. | Check if data from third-party APIs is validated/sanitized before use, especially before database storage or rendering. |

### REST API Security Checklist

**Authentication**:
- Use standard protocols (OAuth2, OIDC) — do not invent custom auth
- Validate JWT signatures server-side on every request
- Use short-lived access tokens (15-60 minutes) with refresh token rotation
- Never accept tokens in URL query parameters

**Authorization**:
- Implement object-level authorization (check ownership/access on every object access)
- Implement function-level authorization (role checks on every endpoint)
- Use attribute-based or role-based access control consistently
- Prevent mass assignment — explicitly allowlist writable fields

**Rate Limiting**:
- Apply per-user and per-IP rate limits
- Stricter limits on authentication endpoints
- Implement exponential backoff for repeated failures
- Return 429 Too Many Requests with Retry-After header

**Input Validation**:
- Validate Content-Type header matches expected type
- Validate and sanitize all input parameters (path, query, body, headers)
- Use schema validation (JSON Schema, OpenAPI validation)
- Enforce maximum request body size
- Enforce maximum pagination limits (do not allow `?limit=1000000`)

**Response Security**:
- Return only necessary fields (no over-exposure)
- Use envelope format with consistent error structure
- Include security headers (see A05)
- Disable TRACE/TRACK HTTP methods

### GraphQL Security

Reference: https://cheatsheetseries.owasp.org/cheatsheets/GraphQL_Cheat_Sheet.html

**Introspection Control**:
- Disable introspection in production environments
- Java: `NoIntrospectionGraphqlFieldVisibility`
- JavaScript: `NoIntrospection` validation rule
- Even with introspection disabled, attackers may enumerate fields via brute force

**Query Depth Limiting**:
- Restrict nested query levels to prevent resource exhaustion
- Tools: `graphql-depth-limit` (JS), `MaxQueryDepthInstrumentation` (Java)
- Typical safe depth: 5-10 levels depending on schema complexity

**Query Complexity Analysis**:
- Assign costs to field resolution; reject queries exceeding a cost threshold
- Tools: `graphql-cost-analysis`, `graphql-validation-complexity` (JS)
- Account for list fields multiplying child field costs

**Batching Attack Prevention**:
- GraphQL batching allows sending multiple operations in a single request
- Batched queries appear as single requests to WAFs, bypassing traditional rate limits
- Mitigation: implement per-operation rate limiting, disable batching for sensitive operations, limit concurrent operations per request

**Authorization**:
- Enforce access control on both edges and nodes within the schema
- Validate permissions in Query and Mutation resolvers
- Never rely on client-side filtering of response data

**Input Validation**:
- Use specific GraphQL scalar types and enums for strict typing
- Use parameterized queries when passing input to backend interpreters
- Validate custom scalar inputs server-side

### gRPC Security

Reference: https://cheatsheetseries.owasp.org/cheatsheets/gRPC_Security_Cheat_Sheet.html

**Transport Security**:
- Always use TLS in production (TLS 1.2+, strong cipher suites)
- Implement mutual TLS (mTLS) for service-to-service communication
- Use short-lived certificates (90 days or less) with automated rotation
- Disable weak protocols and ciphers

**Authentication & Authorization**:
- Validate JWT tokens via server-side interceptors
- Extract credentials from metadata headers (not request parameters)
- Token expiration: 15-60 minutes
- API key validation via metadata ("x-api-key" header)
- Enforce method-level access control with role-based permissions
- Log all authorization failures

**Input Validation**:
- Validate protobuf messages server-side using tools like `protoc-gen-validate`
- Implement allowlist validation for string inputs
- Use parameterized database queries — never concatenate protobuf field values into queries

**Resource Protection**:
- Configure `MaxRecvMsgSize` and `MaxSendMsgSize` (e.g., 4MB) to prevent memory exhaustion
- Implement per-client rate limiting
- Configure client and server timeouts

**Error Handling**:
- Return generic error messages to clients; log details server-side
- Use proper gRPC status codes: `UNAUTHENTICATED`, `PERMISSION_DENIED`, `INVALID_ARGUMENT`

**Service Discovery**:
- Disable gRPC reflection in production
- Secure service discovery with mTLS or Kubernetes RBAC

**gRPC Audit Checklist**:
- [ ] TLS 1.2+ enforced on all gRPC channels
- [ ] mTLS enabled for service-to-service calls
- [ ] JWT validation implemented in server interceptors
- [ ] Message size limits configured
- [ ] gRPC reflection disabled in production
- [ ] Per-method authorization enforced
- [ ] Rate limiting applied per client

**References**:
- https://owasp.org/API-Security/editions/2023/en/0x11-t10/
- https://cheatsheetseries.owasp.org/cheatsheets/REST_Security_Cheat_Sheet.html
- https://cheatsheetseries.owasp.org/cheatsheets/GraphQL_Cheat_Sheet.html
- https://cheatsheetseries.owasp.org/cheatsheets/gRPC_Security_Cheat_Sheet.html
- https://grpc.io/docs/guides/auth/

---

## 4. Authentication & Authorization Patterns

### JWT Security

Reference: https://cheatsheetseries.owasp.org/cheatsheets/JSON_Web_Token_for_Java_Cheat_Sheet.html

**Algorithm Confusion Attacks**:
- The `none` algorithm vulnerability: some libraries treat tokens signed with `none` as valid with verified signatures
- Algorithm switching: attacker changes `alg` from RS256 to HS256, then signs with the public key (which the server uses as HMAC secret)
- **Prevention**: Always specify the expected algorithm explicitly during verification; never let the token dictate the algorithm

```java
// SAFE: explicit algorithm
JWTVerifier verifier = JWT.require(Algorithm.HMAC256(keyHMAC)).build();

// DANGEROUS: library auto-detects algorithm from token header
JWT.decode(token);  // Attacker controls alg field
```

**Token Storage**:
- Recommended: `sessionStorage` + Bearer header (not cookies)
- Alternative: JavaScript closure with private variable
- If `localStorage`: enforce short expiration (15-30 minutes) and implement rotation
- Never store in URL parameters

**Token Sidejacking Prevention**:
- Generate random fingerprint string
- Send fingerprint as hardened cookie: `HttpOnly; Secure; SameSite=Strict`
- Store SHA-256 hash of fingerprint inside the JWT (not the raw value)
- Validate fingerprint match on every request
- This makes stolen tokens unusable without the cookie

**Expiry and Revocation**:
- Use short-lived access tokens (15-30 minutes)
- Implement token denylist (revocation table) storing SHA-256 digests of revoked tokens
- Denylist entries can be purged after the token's natural expiration time

**Signing Key Management**:
- HMAC secrets: minimum 64 characters from cryptographically secure random source
- Prefer RSA/EC signing over HMAC to eliminate shared-secret vulnerability
- Never store keys as JVM string objects (immutable, hard to clear from memory)
- Read keys from protected configuration files, not source code

**Information Disclosure**:
- Encrypt JWT payloads using JWE with AES-GCM (authenticated encryption)
- Libraries: Google Tink, Nimbus JOSE+JWT
- This hides internal claims from client inspection

### OAuth2 / OIDC Implementation Pitfalls

Reference: https://cheatsheetseries.owasp.org/cheatsheets/OAuth2_Cheat_Sheet.html

**Critical Implementation Requirements**:

1. **Always use PKCE** (Proof Key for Code Exchange)
   - Prevents authorization code injection/replay attacks
   - Authorization Servers must enforce `code_verifier` validation
   - Reject downgrade attacks (require `code_challenge` when `code_verifier` present)

2. **Redirect URI Validation**
   - Exact match validation only — never pattern match or prefix match
   - No HTTP schemes except for native loopback (`127.0.0.1`)
   - No open redirectors anywhere in the client application

3. **Token Security**
   - Bearer tokens confined to single Resource Server audience
   - For multi-audience: use sender-constrained tokens (DPoP or mTLS)
   - Refresh token rotation: invalidate old tokens immediately to detect replay
   - Restrict access token privileges to minimum required scope

4. **Mix-Up Attack Prevention**
   - When clients use multiple authorization servers: implement issuer identification via `iss` parameter
   - Or use distinct redirect URIs per authorization server

5. **OIDC Specific**
   - `nonce` parameter provides CSRF protection in OIDC flows
   - Without OIDC `nonce`, `state` parameter must carry one-time CSRF token

**OAuth2 Audit Checklist**:
- [ ] PKCE is implemented and enforced
- [ ] Redirect URIs use exact match validation
- [ ] No HTTP redirect URIs (except localhost for native apps)
- [ ] Access tokens are audience-restricted
- [ ] Refresh tokens use rotation with replay detection
- [ ] Token scopes follow least privilege
- [ ] State/nonce parameters prevent CSRF

### Session Management

Reference: https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html

**Session ID Requirements**:
- Minimum 64 bits of entropy from CSPRNG
- Generic session ID name (e.g., `id`) — not framework-revealing (e.g., `JSESSIONID`, `PHPSESSID`)
- Never in URL parameters

**Cookie Security Attributes**:
| Attribute | Purpose | Required Setting |
|-----------|---------|------------------|
| `Secure` | Only sent over HTTPS | Always set |
| `HttpOnly` | Not accessible via JavaScript | Always set (prevents XSS session theft) |
| `SameSite` | Cross-site transmission control | `Strict` or `Lax` (prevents CSRF) |
| `Domain` | Cookie scope | Most restrictive possible |
| `Path` | Cookie path scope | Most restrictive possible |

**Session Fixation Prevention**:
- Regenerate session ID after every privilege level change (especially login)
- Destroy the old session completely
- Never accept session IDs the application did not generate

**Timeouts**:
- **Idle timeout**: 2-30 minutes depending on risk (enforced server-side)
- **Absolute timeout**: 4-8 hours for typical business applications
- Server-side enforcement only — client-side values are unreliable

### RBAC / ABAC Implementation

**RBAC (Role-Based Access Control)**:
```
# Pattern: role check on every protected operation
@require_role('admin')
def delete_user(user_id):
    ...

# Anti-pattern: checking role name strings scattered through code
if user.role == 'admin':  # Fragile, error-prone, inconsistent
```

**ABAC (Attribute-Based Access Control)**:
```
# Pattern: policy-based decision
def can_access(subject, resource, action):
    # Check subject attributes (role, department, clearance)
    # Check resource attributes (classification, owner)
    # Check environment attributes (time, location, network)
    return policy_engine.evaluate(subject, resource, action)
```

**Implementation Best Practices**:
- Centralize authorization logic — never scatter checks
- Default deny — explicit grants only
- Log all authorization decisions (especially denials)
- Test authorization with automated integration tests covering privilege escalation scenarios

### Password Storage

Reference: https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html

**Algorithm Recommendations** (in order of preference):

| Algorithm | Parameters | Notes |
|-----------|-----------|-------|
| **Argon2id** | m=19MiB, t=2, p=1 (or equivalent alternatives) | Best choice. Memory-hard, GPU-resistant. |
| **scrypt** | N=2^17, r=8, p=1 | Use if Argon2id unavailable. |
| **bcrypt** | work factor >= 10 | Legacy systems. 72-byte input limit. |
| **PBKDF2-HMAC-SHA256** | 600,000 iterations | FIPS-140 compliance only. |

**Pre-hashing with bcrypt is dangerous**: null bytes in hash output cause collisions. If required: `bcrypt(base64(hmac-sha384(password, pepper)), salt, cost)`

**Upgrade Strategy for Legacy Hashes**:
1. **Layering**: Apply new algorithm over old: `bcrypt(md5($password))` — replace with direct hash on next login
2. **Expiration**: Force password reset after inactivity period
3. Use PHC modular string format to store algorithm and parameters with hashes

**Peppers**: Shared secret stored separately from database, added pre- or post-hashing. Provides defense-in-depth if database is compromised but pepper is not.

**Password Storage Audit Checklist**:
- [ ] Passwords use Argon2id, scrypt, bcrypt, or PBKDF2 (never MD5/SHA/plaintext/reversible encryption)
- [ ] Hash parameters meet minimum recommendations
- [ ] Upgrade path exists for legacy hashes
- [ ] Pepper is stored separately from password hashes (if used)
- [ ] Password comparison uses constant-time function

---

## 5. Data Protection in Code

### Encryption at Rest

Reference: https://cheatsheetseries.owasp.org/cheatsheets/Cryptographic_Storage_Cheat_Sheet.html

**Symmetric Encryption**:
- **Algorithm**: AES with 128-bit key minimum (256-bit preferred)
- **Mode**: GCM or CCM (authenticated encryption) as first choice; CTR or CBC with Encrypt-then-MAC as alternative
- **Never use**: ECB mode, DES, 3DES, RC4, Blowfish
- **IVs**: Unique per encryption operation; generated from CSPRNG; never reused with same key

**Asymmetric Encryption**:
- Prefer Elliptic Curve (Curve25519)
- If RSA: minimum 2048-bit key (3072+ recommended for long-term)

**Code Patterns**:
```python
# SAFE: AES-256-GCM
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
key = AESGCM.generate_key(bit_length=256)
aesgcm = AESGCM(key)
nonce = os.urandom(12)
ciphertext = aesgcm.encrypt(nonce, plaintext, associated_data)

# DANGEROUS
cipher = AES.new(key, AES.MODE_ECB)  # ECB mode
cipher = DES.new(key)                 # DES
```

### Encryption in Transit

- TLS 1.2+ required for all communications
- Enforce via HSTS header: `Strict-Transport-Security: max-age=31536000; includeSubDomains`
- Certificate validation must be enforced (never `verify=False`)
- Forward secrecy cipher suites preferred (ECDHE)

### Key Management in Application Code

Reference: https://cheatsheetseries.owasp.org/cheatsheets/Key_Management_Cheat_Sheet.html

**Generation**: Keys generated from cryptographically secure random within FIPS-compliant modules. Never derived from passwords without a proper KDF. Never from keyboard mashing or predictable sources.

**Storage**:
- Never in source code, environment variables, or unencrypted config files
- Use dedicated secrets management: HashiCorp Vault, AWS Secrets Manager, Azure Key Vault, GCP Secret Manager
- Separate Data Encryption Keys (DEK) from Key Encryption Keys (KEK)
- Store KEK in different location/system than DEK

**Rotation**:
- Automated rotation recommended
- Rotate on: compromise, cryptoperiod expiry, algorithm vulnerability discovery
- Applications must handle multiple active key versions during rotation

**Destruction**:
- Overwrite key material before deallocation
- Clear from memory immediately after use
- Destroy all copies including backups

### PII Handling

**Classification**: Identify all PII fields: names, emails, phone numbers, SSN, DOB, addresses, IP addresses, biometrics, health data, financial data.

**Code-Level Controls**:
```
# 1. Minimize collection
# Only collect PII that is necessary for the business function

# 2. Minimize storage duration
# Auto-delete PII after retention period
# Implement data retention policies in code

# 3. Minimize access
# PII fields should require explicit access grants
# Different authorization for reading vs. writing PII

# 4. Encrypt PII at rest
# Application-level encryption for PII columns
# Or use database-level transparent data encryption (TDE)
```

### Data Masking and Redaction

```python
# Pattern: mask PII in API responses and logs
def mask_email(email):
    local, domain = email.split('@')
    return local[0] + '***@' + domain

def mask_card(number):
    return '****-****-****-' + number[-4:]

def mask_ssn(ssn):
    return '***-**-' + ssn[-4:]

# Pattern: redact from logs
REDACT_FIELDS = {'password', 'token', 'secret', 'ssn', 'card_number', 'api_key'}
def sanitize_log_data(data):
    return {k: '[REDACTED]' if k in REDACT_FIELDS else v for k, v in data.items()}
```

### Secure Deletion

- Overwrite data before deletion (not just marking as deleted)
- Clear sensitive variables from memory after use
- Database: DELETE followed by VACUUM (for SQLite) or equivalent
- File systems: consider crypto-shredding (delete the encryption key rather than the data)

---

## 6. Server-Side Request Handling

### SSRF Prevention (Detailed)

Reference: https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html

**Application Layer Defenses**:

1. **Input Validation Strategy** — use allowlists, not denylists
2. **For IP addresses**: validate format with language-specific libraries; cross-check against allowlist
3. **For domain names**: validate format without DNS resolution; maintain allowlist; monitor for DNS resolution to non-public IPs
4. **For URLs**: Avoid accepting complete URLs from users — they are difficult to validate and parsers can be abused
5. **Disable HTTP redirect following** in server-side HTTP clients
6. **Validate resolved IP** before making the connection (prevent DNS rebinding)

**Network Layer Defenses**:
- Firewalls limiting application to legitimate outbound routes only
- Network segmentation blocking illegitimate internal calls
- Internal DNS resolvers configured for internal domains only
- AWS: enforce IMDSv2 (token-based) for metadata service

**Blocked Ranges** (for denylist layer — not sufficient alone):
- `169.254.169.254` (cloud metadata)
- `127.0.0.0/8`, `::1/128` (localhost)
- `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16` (RFC1918 private)
- `224.0.0.0/4`, `ff00::/8` (multicast)
- `0.0.0.0/8` (unspecified)
- `metadata.google.internal`, `metadata.amazonaws.com`

### Path Traversal

**Detection Patterns**:
```
# AUDIT CHECK: Path Traversal

# DANGEROUS
file_path = os.path.join(BASE_DIR, user_input)  # ../../../etc/passwd
open(request.args['file'])                        # Direct user input as file path
send_file(f"uploads/{filename}")                  # Filename from user

# SAFE
import os
safe_path = os.path.realpath(os.path.join(BASE_DIR, user_input))
if not safe_path.startswith(os.path.realpath(BASE_DIR)):
    raise SecurityError("Path traversal detected")
```

**Prevention**:
- Canonicalize the path, then verify it starts with the expected base directory
- Use allowlists for file identifiers — map user input to predefined paths
- Strip or reject `..`, `/`, `\` from user-supplied filenames
- Use `os.path.realpath()` (Python), `Path.GetFullPath()` (.NET), `Paths.get().normalize()` (Java)

### File Upload Security

Reference: https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html

**Validation Checks** (in order):
1. **Authentication/Authorization**: Verify user is allowed to upload before processing
2. **File size**: Enforce maximum size limit before reading entire file
3. **Extension**: Allowlist of safe extensions only (e.g., `.jpg`, `.png`, `.pdf`); block double extensions (`.jpg.php`), null bytes (`.php%00.jpg`)
4. **Content-Type**: Validate but do not trust (trivially spoofed)
5. **File signature (magic bytes)**: Validate against expected type (limited but adds a layer)
6. **Filename**: Generate random filename (UUID/GUID); if user names are kept, sanitize to alphanumeric + hyphens + periods only; enforce max length

**Storage**:
1. Best: Separate hosting service (S3, dedicated storage server)
2. Good: Outside webroot with restricted access
3. Minimum: Inside webroot with write-only permissions and strict access control

**Additional Protections**:
- Antivirus scanning before making file accessible
- Content Disarm and Reconstruct (CDR) for document types
- Re-encode images to strip embedded payloads
- Never serve uploaded files with their original Content-Type without validation
- Set `Content-Disposition: attachment` to prevent browser execution
- For compressed files: check decompressed size to prevent zip bombs

**File Upload Audit Checklist**:
- [ ] File size limits enforced before processing
- [ ] Extension allowlist (not denylist) enforced
- [ ] Filenames randomized or strictly sanitized
- [ ] Files stored outside webroot (or on separate service)
- [ ] Content-Disposition: attachment set on downloads
- [ ] No path traversal possible via filename
- [ ] Compressed file decompression size checked

### XML/JSON Parsing Security

**XXE (XML External Entity)**:

Reference: https://cheatsheetseries.owasp.org/cheatsheets/XML_External_Entity_Prevention_Cheat_Sheet.html

The safest defense: disable DTDs (External Entities) completely.

**Language-Specific Hardening**:

| Language | Parser | Configuration |
|----------|--------|---------------|
| Java | DocumentBuilderFactory | `setFeature("http://apache.org/xml/features/disallow-doctype-decl", true)` |
| Java | SAXParserFactory | Same feature flag as above |
| Java | XMLInputFactory | `setProperty(XMLInputFactory.SUPPORT_DTD, false)` |
| .NET 4.5.2+ | XmlReader, XmlNodeReader | Safe by default |
| .NET pre-4.5.2 | XmlDocument, XmlTextReader | Set `XmlResolver = null`, `DtdProcessing = Prohibit` |
| PHP 8.0+ | All parsers | XXE disabled by default |
| PHP pre-8.0 | All parsers | `libxml_set_external_entity_loader(null)` |
| Python | All parsers | Use `defusedxml` package |
| C/C++ | libxml2 (2.9+) | XXE disabled by default; avoid `XML_PARSE_NOENT` and `XML_PARSE_DTDLOAD` |

**Billion Laughs / XML Bomb**:
- Exponential entity expansion causing DoS
- Prevention: disable DTDs; or limit entity expansion count; use `defusedxml` (Python)

**JSON Parsing Security**:
- Use strict JSON parsers (not `eval()` in JavaScript)
- Set maximum nesting depth limits
- Set maximum string length limits
- Be aware of large number handling differences across parsers

### Request Smuggling Awareness

**What it is**: Exploiting discrepancies between how front-end (proxy/load balancer) and back-end servers parse HTTP requests, particularly around `Content-Length` and `Transfer-Encoding` headers.

**Code-Level Awareness**:
- Use HTTP/2 end-to-end where possible (eliminates classic smuggling)
- Ensure front-end and back-end agree on request boundaries
- Reject ambiguous requests (both `Content-Length` and `Transfer-Encoding: chunked`)
- Use well-maintained reverse proxy configurations
- This is primarily an infrastructure concern, but application code should use standard HTTP libraries that handle framing correctly

**Reference**: https://portswigger.net/web-security/request-smuggling

---

## 7. Database Security from Code Perspective

### Parameterized Queries

The primary defense against SQL injection. Every language has support:

```java
// Java — PreparedStatement
String query = "SELECT * FROM users WHERE name = ?";
PreparedStatement ps = connection.prepareStatement(query);
ps.setString(1, username);
ResultSet results = ps.executeQuery();
```

```python
# Python — DB-API 2.0
cursor.execute("SELECT * FROM users WHERE name = %s", [username])
# Or with named parameters:
cursor.execute("SELECT * FROM users WHERE name = :name", {"name": username})
```

```csharp
// C# — SqlCommand
string query = "SELECT * FROM users WHERE name = @Name";
SqlCommand cmd = new SqlCommand(query, connection);
cmd.Parameters.AddWithValue("@Name", username);
```

```javascript
// Node.js — pg (PostgreSQL)
const result = await pool.query('SELECT * FROM users WHERE name = $1', [username]);
```

**Where parameterization does NOT work**: table names, column names, ORDER BY direction, LIMIT values. These must use allowlist validation (map user input to known-safe values).

### ORM Security

**Safe ORM Usage**:
```python
# SQLAlchemy — SAFE
User.query.filter(User.name == name)
User.query.filter_by(name=name)
session.query(User).filter(User.id == user_id)

# SQLAlchemy — DANGEROUS
User.query.filter("name = '" + name + "'")  # Raw string injection
session.execute(text("SELECT * FROM users WHERE name = '" + name + "'"))
session.execute(text("SELECT * FROM users WHERE name = :name"), {"name": name})  # SAFE with text()
```

**ORM Security Rules**:
- Never pass user input to raw query methods
- Use ORM query builders and let them handle parameterization
- If raw SQL is necessary, always use parameterized form
- Beware of `.extra()`, `.raw()`, `Sequelize.literal()`, `.whereRaw()` methods

### Connection String Security

- Never hardcode connection strings in source code
- Store in: secrets manager, encrypted config files outside webroot, or environment-injected secrets
- Use TLS for all database connections (TLS 1.2+ with certificate verification)
- Use dedicated database accounts per application/service with least privilege
- Never use administrative or shared accounts for application connections

### Migration Security

- Review migration files for: raw SQL with user data, privilege escalation, data exposure
- Run migrations under a privileged account separate from the application runtime account
- Migrations should be idempotent and reversible where possible
- Store migration history; detect and prevent unauthorized changes
- Never include sensitive seed data in migration files committed to source control

### Stored Procedure Injection

Stored procedures are NOT automatically safe from injection if they use dynamic SQL internally:

```sql
-- DANGEROUS stored procedure
CREATE PROCEDURE GetUser(@name VARCHAR(100))
AS
  EXEC('SELECT * FROM users WHERE name = ''' + @name + '''')
GO

-- SAFE stored procedure
CREATE PROCEDURE GetUser(@name VARCHAR(100))
AS
  SELECT * FROM users WHERE name = @name
GO
```

**Database Security Audit Checklist**:
- [ ] All queries use parameterized statements
- [ ] ORM raw query methods are not used with user input
- [ ] Connection strings are not in source code
- [ ] Database connections use TLS with certificate verification
- [ ] Application uses dedicated least-privilege database account
- [ ] Stored procedures do not use dynamic SQL with concatenation
- [ ] Migration files do not contain sensitive data
- [ ] Database accounts do not have unnecessary admin privileges

**References**:
- https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html
- https://cheatsheetseries.owasp.org/cheatsheets/Query_Parameterization_Cheat_Sheet.html
- https://cheatsheetseries.owasp.org/cheatsheets/Database_Security_Cheat_Sheet.html

---

## 8. Error Handling and Information Disclosure

Reference: https://cheatsheetseries.owasp.org/cheatsheets/Error_Handling_Cheat_Sheet.html

### Stack Trace Leakage

**Risk**: Stack traces reveal technology versions (Tomcat, Struts2, Spring), file paths, query structures, and internal architecture — all valuable for attacker reconnaissance.

**Detection Patterns**:
```
# AUDIT CHECK: Information Disclosure

# 1. Stack traces in error responses
app.use((err, req, res, next) => {
  res.status(500).json({ error: err.stack });       # FAIL
  res.status(500).json({ error: err.message });      # FAIL: may still leak
  res.status(500).json({ error: 'Internal error' }); # SAFE
});

# 2. Debug mode in production
DEBUG = True                    # Django: full stack traces in browser
app.run(debug=True)             # Flask: interactive debugger
NODE_ENV=development            # Express: verbose errors

# 3. Database errors exposed
try:
    cursor.execute(query)
except Exception as e:
    return str(e)               # FAIL: reveals DB type, query structure, table names

# 4. Verbose error messages enabling enumeration
"User admin@example.com not found"        # FAIL: reveals user existence
"Password incorrect for user admin"       # FAIL: confirms user exists
"Invalid username or password"            # SAFE: generic

# 5. Version information in headers/responses
Server: Apache/2.4.41 (Ubuntu)           # FAIL: reveals version
X-Powered-By: Express                    # FAIL: reveals framework
```

### Centralized Error Handling

**Pattern**: Framework-level handlers that separate internal logging from external responses.

```java
// Spring — @RestControllerAdvice
@RestControllerAdvice
public class GlobalExceptionHandler {
    @ExceptionHandler(Exception.class)
    public ResponseEntity<ErrorResponse> handleAll(Exception ex) {
        log.error("Unhandled exception", ex);  // Full details logged internally
        return ResponseEntity.status(500)
            .body(new ErrorResponse("Internal server error", correlationId));  // Generic to client
    }
}
```

```javascript
// Express — centralized error handler
app.use((err, req, res, next) => {
    const correlationId = generateCorrelationId();
    logger.error({ err, correlationId, path: req.path });  // Internal
    res.status(500).json({
        error: 'Internal server error',
        correlationId  // Allows support lookup without leaking details
    });
});
```

**Use RFC 7807 Problem Details** for API error responses:
```json
{
    "type": "https://api.example.com/errors/internal",
    "title": "Internal Server Error",
    "status": 500,
    "instance": "/api/users/123",
    "correlationId": "abc-123-def"
}
```

### Debug Endpoints in Production

**Detection Patterns**:
```
# AUDIT CHECK: Debug/Development endpoints
/debug/
/actuator/ (Spring Boot — exposes env, beans, health, metrics)
/elmah.axd (.NET error logging)
/__debug__/ (Django Debug Toolbar)
/graphiql (GraphQL IDE)
/swagger-ui/ or /api-docs (API documentation — may be intentional but review)
/phpinfo.php
/server-status, /server-info (Apache)
/_profiler (Symfony)
/console (H2 database console)
```

### Timing Attacks

**Risk**: Differential response times reveal information (e.g., whether a username exists based on password hash comparison time).

**Prevention**:
```python
# SAFE: constant-time comparison
import hmac
hmac.compare_digest(provided_hash, stored_hash)

# SAFE: always perform the hash even if user not found
def authenticate(username, password):
    user = find_user(username)
    if user is None:
        # Still hash to prevent timing-based user enumeration
        bcrypt.hashpw(password, bcrypt.gensalt())
        return None
    if bcrypt.checkpw(password, user.password_hash):
        return user
    return None
```

**Error Handling Audit Checklist**:
- [ ] No stack traces returned to clients in any environment
- [ ] Debug mode disabled in production (all frameworks)
- [ ] Database errors not exposed in API responses
- [ ] Error messages are generic (no user enumeration possible)
- [ ] Server/framework version headers removed or suppressed
- [ ] Debug/development endpoints not accessible in production
- [ ] Correlation IDs link client errors to internal logs for support
- [ ] Constant-time comparison used for sensitive value checks
- [ ] Custom error pages/handlers configured for all HTTP error codes

**References**:
- https://cheatsheetseries.owasp.org/cheatsheets/Error_Handling_Cheat_Sheet.html
- https://cwe.mitre.org/data/definitions/209.html (Error Message Information Leak)
- https://cwe.mitre.org/data/definitions/203.html (Observable Discrepancy / Timing)
- https://portswigger.net/web-security/information-disclosure

---

## 9. Logging and Monitoring for Security

Reference: https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html

### What to Log (Security Events)

**Always Log**:
- Input validation failures (protocol violations, unacceptable encodings, invalid parameter names/values)
- Authentication successes AND failures
- Authorization failures (access control denials)
- Session management events (creation, destruction, timeout, fixation attempts)
- Application errors and system events
- Administrative actions (user creation/deletion, privilege changes, configuration changes)
- Access to sensitive data and encryption key usage/management
- File upload and download events
- Deserialization failures
- Network connection events and failures
- Certificate validation events
- Third-party service interactions

**Event Attributes** (include with every security log entry):
- **When**: Timestamp (UTC, ISO 8601)
- **Where**: Application identifier, server/host, endpoint/URL, HTTP method
- **Who**: User ID (not PII), source IP address, session ID hash (not raw value)
- **What**: Event type, event description, severity level, action taken (allow/deny), affected resource/object, success/failure, HTTP status code

### What NOT to Log

**Never Log**:
- Passwords (plaintext or hashed)
- Session identifiers (use hash if tracking needed)
- Access tokens, API keys, cryptographic keys
- Bank account numbers, payment card holder data (PCI DSS)
- Database connection strings
- Social Security Numbers, government IDs
- Health information (HIPAA)
- Biometric data
- Source code or internal network topology details

**Handle with Care** (may require de-identification):
- Names, email addresses, phone numbers — use pseudonymization when identity is not required for the log purpose
- IP addresses (may be PII under GDPR)

### Log Injection Prevention

**Risk**: Attackers inject newlines/delimiters into log entries to forge entries or break log parsers.

```
# Attack: user_input = "action\n[INFO] 2024-01-01 Admin logged in from 127.0.0.1"
logger.info(f"User action: {user_input}")
# Creates fake log entry that looks legitimate

# Prevention strategies:
# 1. Structured logging (JSON format) — automatically escapes
import structlog
logger.info("user_action", action=user_input, user_id=user.id)

# 2. Sanitize input before logging
sanitized = user_input.replace('\n', '').replace('\r', '')

# 3. Use parameterized logging
logger.info("User action: %s", user_input)  # Framework handles encoding
```

### Structured Logging for Security Events

```json
{
    "timestamp": "2024-01-15T14:30:00.000Z",
    "level": "WARN",
    "event": "authentication_failure",
    "logger": "security.auth",
    "user_id": "user-12345",
    "source_ip": "192.168.1.100",
    "endpoint": "/api/login",
    "method": "POST",
    "status_code": 401,
    "reason": "invalid_credentials",
    "attempt_count": 3,
    "correlation_id": "req-abc-123"
}
```

**Standard Formats**: CEF (Common Event Format), syslog (RFC 5424), JSON structured logging.

### Audit Trails

**Requirements for High-Value Operations**:
- Record WHO did WHAT to WHICH resource at WHAT time
- Include before/after values for data modifications
- Link related events with interaction/correlation identifiers
- Audit trail entries must be immutable (append-only)

**Implementation**:
```python
# Pattern: audit trail for data modifications
def update_user(current_user, target_user_id, changes):
    old_values = get_user(target_user_id)
    apply_changes(target_user_id, changes)
    audit_log.info("user_modified", extra={
        "actor": current_user.id,
        "target": target_user_id,
        "changes": {k: {"old": old_values[k], "new": v} for k, v in changes.items()},
        "timestamp": utc_now(),
        "correlation_id": request.correlation_id
    })
```

### Tamper-Evident Logging

**At Rest**:
- Store logs on read-only media as soon as possible
- Use append-only storage (write-once, read-many)
- Implement hash chaining: each log entry includes hash of previous entry
- Restrict and periodically audit log access privileges
- Record all access attempts to log storage

**In Transit**:
- Use secure transmission protocols (TLS) for log shipping
- Verify log data origin where possible (signed log entries)
- Use dedicated log collection infrastructure (separate from application)

**Monitoring Integration**:
- Ship logs to centralized SIEM (Splunk, ELK, Datadog, etc.)
- Configure real-time alerting for: repeated auth failures, privilege escalation attempts, unusual data access patterns, new admin accounts
- Monitor for logging cessation (gap detection)
- Ensure logging failures do not cause application failure (non-blocking, graceful degradation)

**Logging Audit Checklist**:
- [ ] Authentication events (success and failure) are logged with user context
- [ ] Authorization denials are logged
- [ ] High-value transactions have immutable audit trails
- [ ] No passwords, tokens, keys, PII in logs
- [ ] Structured logging format used (JSON preferred)
- [ ] Log injection prevented via structured logging or sanitization
- [ ] Logs shipped to centralized management system
- [ ] Alerting configured for security-critical events
- [ ] Log integrity protected (append-only, hash chaining, or tamper-evident storage)
- [ ] Log retention meets regulatory requirements
- [ ] Logging failures are handled gracefully (no DoS via log failure)

**References**:
- https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html
- https://cheatsheetseries.owasp.org/cheatsheets/Logging_Vocabulary_Cheat_Sheet.html
- https://csrc.nist.gov/pubs/sp/800/61/r2/final
- https://cwe.mitre.org/data/definitions/117.html (Log Injection)
- https://cwe.mitre.org/data/definitions/532.html (Sensitive Info in Log)
- https://cwe.mitre.org/data/definitions/778.html (Insufficient Logging)

---

## 10. Master Reference Links

### Primary Standards

| Source | URL | Description |
|--------|-----|-------------|
| OWASP Top 10 (2021) | https://owasp.org/Top10/ | Top 10 web application security risks |
| OWASP ASVS 5.0 | https://github.com/OWASP/ASVS/tree/v5.0.0 | Application Security Verification Standard |
| OWASP API Security Top 10 (2023) | https://owasp.org/API-Security/editions/2023/en/0x11-t10/ | Top 10 API security risks |
| OWASP Cheat Sheet Series | https://cheatsheetseries.owasp.org/ | Practical security guidance for developers |
| NIST SP 800-63b | https://pages.nist.gov/800-63-3/sp800-63b.html | Digital Identity: Authentication & Lifecycle |
| NIST SP 800-61r2 | https://csrc.nist.gov/pubs/sp/800/61/r2/final | Computer Security Incident Handling |
| CWE (Common Weakness Enumeration) | https://cwe.mitre.org/ | Categorized software/hardware weaknesses |
| NVD (National Vulnerability Database) | https://nvd.nist.gov/ | U.S. government vulnerability database |

### OWASP Cheat Sheets (Most Critical for Code Review)

| Cheat Sheet | URL |
|-------------|-----|
| SQL Injection Prevention | https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html |
| Authentication | https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html |
| Password Storage | https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html |
| Session Management | https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html |
| Authorization | https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html |
| Input Validation | https://cheatsheetseries.owasp.org/cheatsheets/Input_Validation_Cheat_Sheet.html |
| SSRF Prevention | https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html |
| Cryptographic Storage | https://cheatsheetseries.owasp.org/cheatsheets/Cryptographic_Storage_Cheat_Sheet.html |
| Deserialization | https://cheatsheetseries.owasp.org/cheatsheets/Deserialization_Cheat_Sheet.html |
| Logging | https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html |
| Error Handling | https://cheatsheetseries.owasp.org/cheatsheets/Error_Handling_Cheat_Sheet.html |
| File Upload | https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html |
| XXE Prevention | https://cheatsheetseries.owasp.org/cheatsheets/XML_External_Entity_Prevention_Cheat_Sheet.html |
| GraphQL | https://cheatsheetseries.owasp.org/cheatsheets/GraphQL_Cheat_Sheet.html |
| gRPC Security | https://cheatsheetseries.owasp.org/cheatsheets/gRPC_Security_Cheat_Sheet.html |
| Key Management | https://cheatsheetseries.owasp.org/cheatsheets/Key_Management_Cheat_Sheet.html |
| Secrets Management | https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html |
| OAuth2 | https://cheatsheetseries.owasp.org/cheatsheets/OAuth2_Cheat_Sheet.html |
| JWT for Java | https://cheatsheetseries.owasp.org/cheatsheets/JSON_Web_Token_for_Java_Cheat_Sheet.html |
| Database Security | https://cheatsheetseries.owasp.org/cheatsheets/Database_Security_Cheat_Sheet.html |
| Vulnerable Dependency Management | https://cheatsheetseries.owasp.org/cheatsheets/Vulnerable_Dependency_Management_Cheat_Sheet.html |
| IDOR Prevention | https://cheatsheetseries.owasp.org/cheatsheets/Insecure_Direct_Object_Reference_Prevention_Cheat_Sheet.html |
| CSRF Prevention | https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html |
| Content Security Policy | https://cheatsheetseries.owasp.org/cheatsheets/Content_Security_Policy_Cheat_Sheet.html |
| Transport Layer Security | https://cheatsheetseries.owasp.org/cheatsheets/Transport_Layer_Security_Cheat_Sheet.html |
| Threat Modeling | https://cheatsheetseries.owasp.org/cheatsheets/Threat_Modeling_Cheat_Sheet.html |

### CWE References (Most Critical)

| CWE | Name | URL |
|-----|------|-----|
| CWE-20 | Improper Input Validation | https://cwe.mitre.org/data/definitions/20.html |
| CWE-78 | OS Command Injection | https://cwe.mitre.org/data/definitions/78.html |
| CWE-79 | Cross-site Scripting (XSS) | https://cwe.mitre.org/data/definitions/79.html |
| CWE-89 | SQL Injection | https://cwe.mitre.org/data/definitions/89.html |
| CWE-117 | Log Injection | https://cwe.mitre.org/data/definitions/117.html |
| CWE-200 | Exposure of Sensitive Information | https://cwe.mitre.org/data/definitions/200.html |
| CWE-209 | Error Message Info Leak | https://cwe.mitre.org/data/definitions/209.html |
| CWE-259 | Hardcoded Password | https://cwe.mitre.org/data/definitions/259.html |
| CWE-284 | Improper Access Control | https://cwe.mitre.org/data/definitions/284.html |
| CWE-287 | Improper Authentication | https://cwe.mitre.org/data/definitions/287.html |
| CWE-327 | Broken Crypto Algorithm | https://cwe.mitre.org/data/definitions/327.html |
| CWE-352 | Cross-Site Request Forgery | https://cwe.mitre.org/data/definitions/352.html |
| CWE-384 | Session Fixation | https://cwe.mitre.org/data/definitions/384.html |
| CWE-502 | Deserialization of Untrusted Data | https://cwe.mitre.org/data/definitions/502.html |
| CWE-532 | Sensitive Info in Log File | https://cwe.mitre.org/data/definitions/532.html |
| CWE-611 | XXE | https://cwe.mitre.org/data/definitions/611.html |
| CWE-778 | Insufficient Logging | https://cwe.mitre.org/data/definitions/778.html |
| CWE-798 | Hardcoded Credentials | https://cwe.mitre.org/data/definitions/798.html |
| CWE-862 | Missing Authorization | https://cwe.mitre.org/data/definitions/862.html |
| CWE-918 | SSRF | https://cwe.mitre.org/data/definitions/918.html |

### Additional Security Resources

| Source | URL |
|--------|-----|
| PortSwigger Web Security Academy | https://portswigger.net/web-security |
| Snyk Vulnerability Database | https://security.snyk.io/ |
| HackerOne Hacktivity | https://hackerone.com/hacktivity |
| OWASP Dependency Check | https://owasp.org/www-project-dependency-check/ |
| OWASP ZAP | https://www.zaproxy.org/ |
| gRPC Auth Guide | https://grpc.io/docs/guides/auth/ |
| NIST SP 800-57 (Key Management) | https://csrc.nist.gov/pubs/sp/800/57/pt1/r5/final |
| NIST SP 800-131A (Crypto Transitions) | https://csrc.nist.gov/pubs/sp/800/131/a/r2/final |

---

## Consolidated Audit Quick-Reference

### Severity Tiers for Findings

| Tier | Severity | Description | Example |
|------|----------|-------------|---------|
| **P0** | Critical | Direct RCE, auth bypass, mass data exposure | Unsanitized deserialization, SQL injection in auth, hardcoded admin credentials |
| **P1** | High | Significant security control bypass or data exposure | Missing authorization on API endpoints, SSRF to internal services, weak password hashing |
| **P2** | Medium | Defense-in-depth failures, partial exposure | Missing rate limiting, overly verbose errors, missing security headers |
| **P3** | Low | Best-practice violations, minor information disclosure | Missing SRI on CDN scripts, framework version in headers, overly broad CORS |

### Top 20 Code Patterns to Grep For

1. String concatenation in SQL queries
2. `eval()`, `exec()`, `system()`, `popen()` with user input
3. `pickle.loads()`, `yaml.load()`, `ObjectInputStream.readObject()`, `unserialize()`, `BinaryFormatter`
4. `requests.get(user_url)` or equivalent (SSRF)
5. `hashlib.md5()`, `hashlib.sha1()`, `hashlib.sha256()` for passwords
6. Hardcoded secrets: `SECRET_KEY =`, `API_KEY =`, `PASSWORD =`
7. `DEBUG = True`, `debug=True`, `NODE_ENV=development`
8. `Access-Control-Allow-Origin: *`
9. `verify=False`, `rejectUnauthorized: false` (TLS bypass)
10. `shell=True` in subprocess calls
11. Missing auth middleware on route definitions
12. `os.path.join()` with user input without canonicalization check
13. `AES.MODE_ECB`, `DES`, `RC4`
14. `random.random()`, `Math.random()` for security purposes
15. Password/token/key in `logger.info()`, `console.log()`, `print()`
16. Missing `HttpOnly`, `Secure`, `SameSite` on session cookies
17. `.extra()`, `.raw()`, `.whereRaw()`, `Sequelize.literal()` with user input
18. XML parser without DTD/XXE disabled
19. File operations with user-controlled paths (path traversal)
20. `allow_redirects=True` on server-side HTTP requests fetching user-supplied URLs
