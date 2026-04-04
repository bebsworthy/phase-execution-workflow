# Web Frontend Security: Deep Research for Security Audit Plugin

> Research compiled April 2026. All recommendations are actionable audit checks for a security review tool.

---

## Table of Contents

1. [Cross-Site Scripting (XSS)](#1-cross-site-scripting-xss)
2. [Content Security Policy (CSP)](#2-content-security-policy-csp)
3. [Cross-Site Request Forgery (CSRF)](#3-cross-site-request-forgery-csrf)
4. [Client-Side Data Security](#4-client-side-data-security)
5. [Authentication on the Frontend](#5-authentication-on-the-frontend)
6. [Third-Party Script Security](#6-third-party-script-security)
7. [Browser Security Headers](#7-browser-security-headers)
8. [Frontend-Specific Vulnerability Patterns](#8-frontend-specific-vulnerability-patterns)
9. [Secure Frontend Architecture Patterns](#9-secure-frontend-architecture-patterns)
10. [Frontend Security Testing](#10-frontend-security-testing)
11. [Modern Frontend Framework Security](#11-modern-frontend-framework-security)

---

## 1. Cross-Site Scripting (XSS)

### 1.1 XSS Types

| Type | Vector | Detection Approach |
|------|--------|--------------------|
| **Reflected** | User input reflected in server response without encoding | Check server responses for unencoded query params in HTML body |
| **Stored** | Malicious input persisted in database, rendered to other users | Audit all data rendered from DB; check for encoding at output |
| **DOM-based** | Client-side JS reads from attacker-controlled sources, writes to dangerous sinks | Trace data flow from `location.*`, `document.referrer`, `postMessage` to sinks |
| **Mutation XSS (mXSS)** | Sanitized HTML mutated by browser parsing into executable form | Test sanitizer output with innerHTML re-parsing; check DOMPurify version |

### 1.2 Context-Dependent Output Encoding Rules

Per OWASP XSS Prevention Cheat Sheet, encoding must match the output context:

| Context | Required Encoding | Example |
|---------|-------------------|---------|
| HTML body | HTML entity encoding: `&` -> `&amp;`, `<` -> `&lt;`, `>` -> `&gt;`, `"` -> `&quot;`, `'` -> `&#x27;` | `<div>ENCODE(data)</div>` |
| HTML attributes | Hex entity `&#xHH;` format, always quote attributes | `<input value="ENCODE(data)">` |
| JavaScript strings | Unicode `\uXXXX` format, only in quoted strings | `var x = "ENCODE(data)";` |
| CSS property values | CSS hex `\XX` or `\XXXXXX` | `{ background: ENCODE(data) }` |
| URL parameters | Percent encoding `%HH` | `<a href="/page?q=ENCODE(data)">` |

**Dangerous contexts to never insert untrusted data into:**
- Directly inside `<script>` blocks
- Inside HTML comments
- As HTML tag or attribute names
- Directly in CSS blocks (outside property values)

### 1.3 Safe DOM Sinks vs Dangerous Sinks

**Dangerous sinks (must audit all uses):**
- `element.innerHTML`, `element.outerHTML`
- `document.write()`, `document.writeln()`
- `eval()`, `new Function()`, `setTimeout(string)`, `setInterval(string)`
- `element.setAttribute()` with event handler names (`onclick`, `onerror`, etc.)
- `element.insertAdjacentHTML()`
- `location.href`, `location.assign()`, `location.replace()` with user input
- `script.src`, `iframe.src` with user input

**Safe alternatives:**
- `element.textContent` (no code execution)
- `element.innerText` (no code execution)
- `document.createTextNode()`
- `element.setAttribute()` with non-event attributes (e.g., `class`, `title`, `value`)
- `element.classList.add()`
- `JSON.parse()` instead of `eval()` for JSON

### 1.4 DOMPurify Sanitization

```javascript
// Basic usage
let clean = DOMPurify.sanitize(dirty);

// With config
let clean = DOMPurify.sanitize(dirty, {
  ALLOWED_TAGS: ['b', 'i', 'em', 'strong', 'a'],
  ALLOWED_ATTR: ['href'],
  SANITIZE_NAMED_PROPS: true  // Prevents DOM clobbering
});
```

**Audit checks for DOMPurify:**
- [ ] Version is current (check for mXSS bypasses in older versions)
- [ ] Sanitized output is NOT modified after sanitization (re-serialization can re-introduce mXSS)
- [ ] Config does not allow dangerous tags (`script`, `iframe`, `object`, `embed`, `svg` with event handlers)
- [ ] `RETURN_DOM` or `RETURN_DOM_FRAGMENT` used when possible (avoids re-parsing)

### 1.5 Framework-Specific XSS Prevention

**React:**
- JSX auto-escapes values in `{}` curly braces for text content
- `dangerouslySetInnerHTML` bypasses escaping -- must sanitize with DOMPurify first
- `href` attributes accept `javascript:` URLs -- validate with `new URL()` and check protocol
- `ref.current.innerHTML` bypasses React's escaping -- audit all ref usage
- SSR with `ReactDOMServer.renderToString()` auto-escapes, but concatenating unsanitized data after render is unsafe

**Vue:**
- `v-html` directive renders raw HTML -- equivalent to `dangerouslySetInnerHTML`
- Template expressions `{{ }}` are auto-escaped
- `v-bind:href` can accept `javascript:` URLs
- Vue template compiler has had XSS vulnerabilities (CVE-2024-6783)

**Angular:**
- Strict Contextual Escaping (SCE) enabled by default
- `bypassSecurityTrustHtml()`, `bypassSecurityTrustScript()`, `bypassSecurityTrustUrl()`, `bypassSecurityTrustResourceUrl()` all disable sanitization -- audit every use
- Built-in `DomSanitizer` service for explicit sanitization
- Template injection possible if user input is compiled as Angular template

**Svelte:**
- `{@html expression}` renders raw HTML -- must sanitize
- Normal `{expression}` is auto-escaped

### 1.6 Trusted Types API

Trusted Types provide a browser-native defense against DOM XSS by requiring data to pass through a policy before reaching dangerous sinks.

**CSP header to enable:**
```
Content-Security-Policy: require-trusted-types-for 'script'
```

**Report-only for migration:**
```
Content-Security-Policy-Report-Only: require-trusted-types-for 'script'; report-uri /csp-report
```

**Creating a policy:**
```javascript
const policy = trustedTypes.createPolicy('myPolicy', {
  createHTML: (input) => DOMPurify.sanitize(input),
  createScriptURL: (input) => {
    const url = new URL(input, document.baseURI);
    if (url.origin === location.origin) return url.href;
    throw new TypeError('Untrusted URL');
  }
});
// Usage: element.innerHTML = policy.createHTML(untrustedInput);
```

**Audit checks:**
- [ ] Is Trusted Types CSP directive present (even report-only)?
- [ ] Are policies named and limited (avoid `default` policy except for legacy migration)?
- [ ] Browser support: Chrome/Edge 83+, Safari 26+, Firefox TP

**Sources:**
- [OWASP XSS Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html)
- [OWASP DOM-based XSS Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/DOM_based_XSS_Prevention_Cheat_Sheet.html)
- [OWASP XSS Filter Evasion Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/XSS_Filter_Evasion_Cheat_Sheet.html)
- [OWASP XSS Types](https://owasp.org/www-community/Types_of_Cross-Site_Scripting)
- [web.dev: Trusted Types](https://web.dev/articles/trusted-types)
- [MDN: Trusted Types API](https://developer.mozilla.org/en-US/docs/Web/API/Trusted_Types_API)
- [MDN: Cross-site scripting (XSS)](https://developer.mozilla.org/en-US/docs/Web/Security/Attacks/XSS)

---

## 2. Content Security Policy (CSP)

### 2.1 Strict CSP Design

**Recommended nonce-based CSP (server-rendered apps):**
```
Content-Security-Policy:
  script-src 'nonce-{RANDOM}' 'strict-dynamic';
  object-src 'none';
  base-uri 'none';
```

**Recommended hash-based CSP (static/SPA apps):**
```
Content-Security-Policy:
  script-src 'sha256-{HASH}' 'strict-dynamic';
  object-src 'none';
  base-uri 'none';
```

**Key requirements for nonces:**
- Minimum 128 bits of entropy (32 hex chars / 24 base64 chars)
- Cryptographically random (`crypto.randomBytes()`, not `Math.random()`)
- Regenerated for every HTTP response
- Never leaked in URLs, logs, or error messages

### 2.2 Nonce vs Hash Strategy

| Factor | Nonce | Hash |
|--------|-------|------|
| Best for | Server-rendered HTML | Static sites, SPAs, cached content |
| Requires | Per-request header generation | Pre-computed hashes of all inline scripts |
| CDN compatibility | Needs edge compute (e.g., Cloudflare Workers) | Works with static CDN |
| Maintenance | Automatic -- nonce changes per request | Must update hashes when scripts change |

### 2.3 strict-dynamic

When present, `strict-dynamic`:
- Trust granted by nonce/hash extends to dynamically loaded scripts (e.g., `createElement('script')`)
- Ignores `https:` and `unsafe-inline` allowlist fallbacks in supporting browsers
- Does NOT trust inline event handlers or `javascript:` URIs
- Browser support: Chrome 52+, Edge 79+, Firefox 52+, Safari 15.4+

### 2.4 CSP for SPAs

SPAs typically use hash-based CSP because:
- The HTML shell is static and cacheable
- A single bootstrap script loads the application bundle
- Framework bundlers can output hashes at build time

**Pattern for SPA bootstrap:**
```html
<script>
  // This script's hash goes in CSP header
  var scripts = ['/app.js', '/vendor.js'];
  scripts.forEach(function(src) {
    var s = document.createElement('script');
    s.src = src;
    s.async = false;
    document.head.appendChild(s);
  });
</script>
```

### 2.5 Refactoring for CSP Compliance

Common patterns that break strict CSP and their fixes:

| Blocked Pattern | Fix |
|----------------|-----|
| `<div onclick="handler()">` | `element.addEventListener('click', handler)` |
| `<a href="javascript:void(0)">` | `element.addEventListener('click', ...)` |
| `eval(jsonString)` | `JSON.parse(jsonString)` |
| `setTimeout("code", ms)` | `setTimeout(function() { ... }, ms)` |
| Inline `<style>` blocks | External stylesheets or `style-src 'nonce-...'` |

### 2.6 CSP Reporting

```
Content-Security-Policy: ...; report-uri /csp-report
Content-Security-Policy: ...; report-to csp-endpoint

# Report-To header (newer):
Report-To: {"group":"csp-endpoint","max_age":10886400,"endpoints":[{"url":"/csp-report"}]}
```

**Deployment process:**
1. Start with `Content-Security-Policy-Report-Only` to collect violations
2. Analyze reports, fix violations
3. Validate with [CSP Evaluator](https://csp-evaluator.withgoogle.com)
4. Switch to enforcing `Content-Security-Policy`

### 2.7 Common CSP Bypasses to Avoid

| Bypass | Cause | Prevention |
|--------|-------|------------|
| Allowlisting CDN domains | JSONP endpoints or user-uploaded content on CDN | Use nonce/hash, not domain allowlists |
| `unsafe-inline` | Disables inline script protection entirely | Use nonces or hashes instead |
| `unsafe-eval` | Allows `eval()` and related | Refactor code to remove eval |
| Base tag injection | `<base>` tag redirects relative script URLs | Add `base-uri 'none'` |
| Object/embed plugins | Flash/Java applets bypass CSP | Add `object-src 'none'` |
| Missing `default-src` | Unspecified directives fall back to unrestricted | Set `default-src 'self'` as baseline |
| `data:` URI in script-src | Allows inline script via data URIs | Do not include `data:` in script-src |

### 2.8 Audit Checklist for CSP

- [ ] CSP header present on all pages (not just meta tag)
- [ ] Uses nonce or hash (not domain allowlist alone)
- [ ] `object-src 'none'` present
- [ ] `base-uri 'none'` or `base-uri 'self'` present
- [ ] No `unsafe-inline` in script-src (unless with strict-dynamic for fallback)
- [ ] No `unsafe-eval` in script-src
- [ ] No wildcard `*` in any directive
- [ ] No `data:` in script-src
- [ ] `default-src` is set
- [ ] Report-uri or report-to configured
- [ ] Nonces have sufficient entropy (128+ bits)
- [ ] Nonces regenerated per request (not cached)
- [ ] Validate with [CSP Evaluator](https://csp-evaluator.withgoogle.com)

**Sources:**
- [web.dev: Strict CSP](https://web.dev/articles/strict-csp)
- [MDN: Content-Security-Policy](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Content-Security-Policy)
- [MDN: CSP Implementation Guide](https://developer.mozilla.org/en-US/docs/Web/Security/Practical_implementation_guides/CSP)
- [OWASP Content Security Policy Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Content_Security_Policy_Cheat_Sheet.html)
- [content-security-policy.com: strict-dynamic](https://content-security-policy.com/strict-dynamic/)
- [content-security-policy.com: nonce](https://content-security-policy.com/nonce/)
- [CSP Evaluator Tool](https://csp-evaluator.withgoogle.com)

---

## 3. Cross-Site Request Forgery (CSRF)

### 3.1 Primary Defense Mechanisms

**1. Synchronizer Token Pattern (stateful apps):**
- Server generates unique, unpredictable token tied to user session
- Token included in hidden form field or custom header
- Server validates token on every state-changing request (POST, PUT, DELETE)
- Tokens must be: unique per session, cryptographically random, server-side validated

**2. Double-Submit Cookie Pattern (stateless apps):**
- Server sets CSRF token in a cookie (e.g., `XSRF-TOKEN`)
- Client reads token from cookie, sends it in a custom header (e.g., `X-XSRF-TOKEN`)
- Server compares cookie value to header value
- **Must use signed double-submit** (HMAC binding token to session) to prevent cookie injection attacks

**3. Custom Request Headers (API/SPA apps):**
- Require a custom header (e.g., `X-Requested-With: XMLHttpRequest`) on all state-changing requests
- Browsers do not allow cross-origin requests with custom headers without CORS preflight
- Simple and effective for AJAX-only APIs

**4. Fetch Metadata Headers (modern browsers):**
- Check `Sec-Fetch-Site` header: reject `cross-site` for state-changing methods
- Fallback to origin/referer validation for legacy browsers

### 3.2 SameSite Cookies

| Value | Behavior | Use Case |
|-------|----------|----------|
| `Strict` | Never sent on cross-site requests | High-security (banking, admin) |
| `Lax` | Sent on top-level navigations (GET only) | General use -- good balance |
| `None` | Always sent (requires `Secure` flag) | Cross-site integrations only |

**SameSite alone is NOT sufficient.** OWASP recommends SameSite as defense-in-depth alongside token-based CSRF protection because:
- Older browsers may not support SameSite
- Subdomain attacks can bypass SameSite=Lax
- Not all cross-site contexts are covered

### 3.3 CSRF in SPAs with Token-Based Auth

For SPAs using JWT or token-based auth stored in memory:
- If tokens are in `Authorization` header (not cookies), CSRF is mitigated by default
- If using cookies for auth, implement the cookie-to-header pattern:
  1. Server sets CSRF token in non-HttpOnly cookie
  2. SPA reads token from cookie via `document.cookie`
  3. SPA includes token as custom header on every state-changing request
  4. Server validates header matches cookie

**Framework built-in CSRF:**
- **Angular**: `HttpClient` auto-reads `XSRF-TOKEN` cookie, sends as `X-XSRF-TOKEN` header
- **Axios**: Auto-reads `XSRF-TOKEN` cookie with `xsrfCookieName` / `xsrfHeaderName` config
- **Django**: Sets `csrftoken` cookie, expects `X-CSRFToken` header
- **Rails**: Includes `csrf_meta_tags` in layout, `X-CSRF-Token` header

### 3.4 Audit Checklist for CSRF

- [ ] All state-changing endpoints require CSRF protection
- [ ] CSRF tokens are cryptographically random and tied to session
- [ ] GET requests do not perform state changes
- [ ] SameSite attribute set on session cookies (Lax minimum)
- [ ] For SPAs: custom header requirement on state-changing requests
- [ ] Origin/Referer header validated on server for state-changing requests
- [ ] Double-submit cookies use HMAC signing (not plain comparison)
- [ ] CORS is not overly permissive (`Access-Control-Allow-Origin: *` with credentials)

**Sources:**
- [OWASP CSRF Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html)
- [OWASP SameSite](https://owasp.org/www-community/SameSite)
- [OWASP Session Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html)
- [OWASP CSRF Attack Description](https://owasp.org/www-community/attacks/csrf)

---

## 4. Client-Side Data Security

### 4.1 localStorage and sessionStorage Risks

**Key vulnerabilities:**
- Any XSS vulnerability gives full access to all stored data
- All applications on the same origin share localStorage
- No access control -- any script on the page can read/write
- localStorage persists across sessions (data lives until explicitly deleted)
- sessionStorage persists until the tab closes (but accessible for the tab's lifetime)

**What NOT to store in Web Storage:**
- Session tokens or session IDs
- Authentication tokens (JWTs, access tokens)
- Personally identifiable information (PII)
- API keys or secrets
- Credit card data
- Any data that would be harmful if exposed via XSS

**Audit checks:**
- [ ] Search codebase for `localStorage.setItem` and `sessionStorage.setItem` -- check what is stored
- [ ] Verify no authentication tokens in Web Storage
- [ ] Verify no PII or secrets in Web Storage
- [ ] Check that data read from Web Storage is treated as untrusted (validated/encoded before use)

### 4.2 IndexedDB Security

- Same-origin policy applies (isolated per origin)
- Accessible from any script on the origin (including XSS payloads)
- Data persists until explicitly deleted
- Same rules apply: do not store sensitive tokens or PII
- **Additional risk:** Larger storage capacity means more data at risk in breach

### 4.3 Cookie Security Flags

| Attribute | Purpose | Recommended Setting |
|-----------|---------|---------------------|
| `Secure` | Only sent over HTTPS | Always set |
| `HttpOnly` | Inaccessible to JavaScript | Set on session cookies and auth tokens |
| `SameSite` | Controls cross-site sending | `Lax` or `Strict` |
| `Domain` | Scope of cookie | Omit (current host only) or most restrictive |
| `Path` | Path scope | `/` or most restrictive path |
| `Max-Age` / `Expires` | Lifetime | As short as possible for session cookies |
| `__Host-` prefix | Requires Secure, Path=/, no Domain | Use for single-domain session cookies |
| `__Secure-` prefix | Requires Secure flag | Use for cross-subdomain cookies |

**Optimal session cookie:**
```http
Set-Cookie: __Host-SESSIONID=abc123; Max-Age=3600; Path=/; Secure; HttpOnly; SameSite=Lax
```

**Audit checks for cookies:**
- [ ] Session cookies have `HttpOnly` flag
- [ ] All cookies have `Secure` flag
- [ ] Session cookies have `SameSite=Lax` or `Strict`
- [ ] Session cookies use `__Host-` prefix where possible
- [ ] Cookie lifetimes are appropriate (not indefinite)
- [ ] Cookie `Domain` is as restrictive as possible

### 4.4 Sensitive Data in URLs and Browser History

- Never put tokens, session IDs, or secrets in URL query parameters
- URL parameters are logged in server logs, browser history, referrer headers, and proxy logs
- Use `Referrer-Policy: strict-origin-when-cross-origin` to limit referrer leakage
- POST bodies for sensitive data, not GET parameters
- `window.history.replaceState()` to remove sensitive data from URL after processing

### 4.5 Client-Side Encryption Considerations

- Client-side encryption provides defense-in-depth, not primary security
- WebCrypto API (`window.crypto.subtle`) for cryptographic operations
- Key management is the hard problem: where to store encryption keys client-side?
- Use for: encrypting data before sending to untrusted storage (e.g., encrypted backups)
- Do NOT rely on client-side encryption for data the server needs to validate

**Sources:**
- [OWASP HTML5 Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/HTML5_Security_Cheat_Sheet.html)
- [OWASP Testing Browser Storage](https://owasp.org/www-project-web-security-testing-guide/v42/4-Web_Application_Security_Testing/11-Client-side_Testing/12-Testing_Browser_Storage)
- [MDN: Using HTTP Cookies](https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/Cookies)
- [MDN: Secure Cookie Configuration](https://developer.mozilla.org/en-US/docs/Web/Security/Practical_implementation_guides/Cookies)
- [MDN: Web Storage API](https://developer.mozilla.org/en-US/docs/Web/API/Web_Storage_API)
- [OWASP HttpOnly](https://owasp.org/www-community/HttpOnly)

---

## 5. Authentication on the Frontend

### 5.1 Secure Token Storage Hierarchy

From most secure to least secure:

| Storage | XSS Risk | CSRF Risk | Persistence | Recommendation |
|---------|----------|-----------|-------------|----------------|
| **In-memory variable** | Exposed if XSS | None | Lost on refresh | Best for access tokens |
| **Web Worker memory** | Isolated from main thread | None | Lost on refresh | Best overall if feasible |
| **HttpOnly Secure cookie** | Not accessible to JS | Yes (mitigate with SameSite + CSRF token) | Persistent | Best for session tokens |
| **sessionStorage** | Full XSS exposure | None | Tab lifetime | Acceptable for non-sensitive |
| **localStorage** | Full XSS exposure | None | Permanent | Avoid for tokens |

### 5.2 OAuth2/OIDC for SPAs (PKCE)

**Current best practice: Authorization Code Flow with PKCE**

The implicit grant flow is deprecated for SPAs. Use Authorization Code + PKCE:

1. SPA generates `code_verifier` (random string) and `code_challenge` (SHA256 hash)
2. Redirect to authorization server with `code_challenge`
3. User authenticates, authorization server returns `code` via redirect
4. SPA exchanges `code` + `code_verifier` for tokens
5. Authorization server validates `code_challenge` matches `code_verifier`

**Why PKCE over Implicit:**
- Authorization code is not exposed in URL fragment
- Code verifier proves the requesting client is the same one that started the flow
- Supports refresh tokens (implicit does not)

### 5.3 Backend-for-Frontend (BFF) Pattern

The most secure SPA auth pattern:
- Thin backend proxy handles OAuth flows and stores tokens server-side
- SPA communicates with BFF using HttpOnly session cookies
- Tokens never reach the browser
- BFF forwards access token to APIs on behalf of the SPA
- Recommended by OAuth 2.1 draft and Auth0

### 5.4 Silent Refresh and Refresh Token Rotation

**Refresh Token Rotation:**
- Every refresh token exchange returns a new refresh token
- Previous refresh token is immediately invalidated
- If a stolen refresh token is used, both the attacker and legitimate user are detected
- Automatic reuse detection triggers session revocation

**Silent refresh patterns:**
- Hidden iframe approach is deprecated (blocked by third-party cookie restrictions)
- Use refresh token rotation with short-lived access tokens (5-15 min)
- Store refresh tokens in HttpOnly cookies or secure server-side session

### 5.5 Logout and Session Invalidation

- Invalidate session server-side (do not rely on client-side token deletion alone)
- Clear all auth cookies with expired `Max-Age=0` and empty values
- Use `Clear-Site-Data: "cookies", "storage"` header on logout endpoint
- Revoke refresh tokens on logout
- For multi-tab: use `BroadcastChannel` API or `storage` event to notify other tabs of logout

### 5.6 Multi-Tab Session Management

- **Cookie-based auth**: Sessions automatically shared across tabs (same cookies)
- **Token in memory**: Each tab has independent state -- use `BroadcastChannel` to sync
- **Lock pattern**: Use `navigator.locks.request()` (Web Locks API) to prevent race conditions during token refresh across tabs
- **Storage event**: Listen to `window.addEventListener('storage', ...)` to detect cross-tab auth changes in localStorage

### 5.7 Audit Checklist for Frontend Auth

- [ ] Tokens not stored in localStorage
- [ ] Access tokens stored in memory or HttpOnly cookies
- [ ] OAuth2 uses PKCE (not implicit grant)
- [ ] Refresh tokens use rotation with reuse detection
- [ ] Logout invalidates server-side session
- [ ] Multi-tab logout properly handled
- [ ] Silent refresh does not use deprecated iframe approach
- [ ] Token lifetimes are appropriate (access: 5-15 min, refresh: hours-days)
- [ ] BFF pattern considered for high-security apps

**Sources:**
- [Auth0: Authorization Code Flow with PKCE](https://auth0.com/docs/get-started/authentication-and-authorization-flow/authorization-code-flow-with-pkce)
- [Auth0: Token Storage](https://auth0.com/docs/secure/security-guidance/data-security/token-storage)
- [Auth0: Securing SPAs with Refresh Token Rotation](https://auth0.com/blog/securing-single-page-applications-with-refresh-token-rotation/)
- [Auth0: The Backend-for-Frontend Pattern (BFF)](https://auth0.com/blog/the-backend-for-frontend-pattern-bff/)
- [OWASP OAuth2 Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/OAuth2_Cheat_Sheet.html)
- [OWASP Session Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html)
- [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
- [Auth0: Demystifying OAuth Security -- State vs Nonce vs PKCE](https://auth0.com/blog/demystifying-oauth-security-state-vs-nonce-vs-pkce/)

---

## 6. Third-Party Script Security

### 6.1 Subresource Integrity (SRI)

SRI ensures that fetched resources (scripts, stylesheets) have not been tampered with by verifying a cryptographic hash.

```html
<script
  src="https://cdn.example.com/lib.js"
  integrity="sha384-oqVuAfXRKap7fdgcCY5uykM6+R9GqQ8K/uxy9rx7HNQlGYl1kPzQho1wx4JwY8wC"
  crossorigin="anonymous">
</script>
```

**Requirements:**
- CDN must support CORS (`crossorigin="anonymous"` attribute required)
- Hash must be updated when the resource changes
- Generate hashes: `openssl dgst -sha384 -binary lib.js | openssl base64 -A`
- Multiple hashes allowed (browser accepts if any match)
- Supported algorithms: SHA-256, SHA-384, SHA-512

**Audit checks:**
- [ ] All CDN-hosted scripts have `integrity` attribute
- [ ] All CDN-hosted stylesheets have `integrity` attribute
- [ ] `crossorigin="anonymous"` present on SRI-protected resources
- [ ] Hashes use SHA-384 or SHA-512 (not SHA-256 alone)

### 6.2 Third-Party Script Sandboxing

**iframe sandboxing:**
```html
<iframe
  src="https://third-party.com/widget"
  sandbox="allow-scripts"
  csp="script-src 'self'"
  referrerpolicy="no-referrer">
</iframe>
```

Sandbox attribute restrictions (all on by default, selectively allow):
- `allow-scripts`: Allow JavaScript execution
- `allow-same-origin`: Allow same-origin access
- `allow-forms`: Allow form submission
- `allow-popups`: Allow popups
- Never use `allow-scripts allow-same-origin` together (allows sandbox escape)

**CSP for third-party isolation:**
```
Content-Security-Policy: script-src 'nonce-{RANDOM}' 'strict-dynamic'; connect-src 'self' https://api.analytics.com;
```

### 6.3 Tag Manager Security

- Tag managers (GTM, Tealium) can load arbitrary scripts -- treat as a critical attack surface
- Require two-factor authentication on tag manager accounts
- Implement approval workflows for tag changes
- Use CSP to limit what tag-managed scripts can do
- Audit tag manager configurations regularly
- Consider: tag manager compromise = full site compromise

### 6.4 Supply Chain Risks

| Vector | Risk | Mitigation |
|--------|------|------------|
| CDN compromise | Modified scripts served to all users | SRI hashes |
| npm package hijack | Malicious code in dependency | `npm audit`, lockfile review, SCA tools |
| Typosquatting | Wrong package installed | Verify package names, use scoped packages |
| Maintainer account takeover | Malicious update published | Pin versions, review changelogs |
| Build tool compromise | Malicious code injected during build | Reproducible builds, CI integrity checks |

### 6.5 Audit Checklist for Third-Party Scripts

- [ ] Inventory all third-party scripts loaded on the site
- [ ] SRI hashes on all CDN-hosted resources
- [ ] Third-party scripts sandboxed where possible (iframes)
- [ ] CSP limits script sources
- [ ] Tag manager access uses 2FA and approval workflows
- [ ] `npm audit` or equivalent runs in CI
- [ ] Package lockfile committed and reviewed
- [ ] No scripts loaded from untrusted or unnecessary origins

**Sources:**
- [MDN: Subresource Integrity](https://developer.mozilla.org/en-US/docs/Web/Security/Defenses/Subresource_Integrity)
- [MDN: SRI Implementation Guide](https://developer.mozilla.org/en-US/docs/Web/Security/Practical_implementation_guides/SRI)
- [MDN: Securing your CDN with SRI](https://developer.mozilla.org/en-US/blog/securing-cdn-using-sri-why-how/)
- [MDN: Supply Chain Attacks](https://developer.mozilla.org/en-US/docs/Web/Security/Attacks/Supply_chain_attacks)
- [OWASP: Subresource Integrity](https://owasp.org/www-community/controls/SubresourceIntegrity)
- [OWASP: Third Party JavaScript Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Third_Party_Javascript_Management_Cheat_Sheet.html)

---

## 7. Browser Security Headers

### 7.1 Complete Header Reference

#### Essential Headers (deploy on all sites)

**Content-Security-Policy**
```
Content-Security-Policy: script-src 'nonce-{RANDOM}' 'strict-dynamic'; object-src 'none'; base-uri 'none';
```
Protects against: XSS, data injection. See [Section 2](#2-content-security-policy-csp) for full details.

**Strict-Transport-Security (HSTS)**
```
Strict-Transport-Security: max-age=63072000; includeSubDomains; preload
```
Protects against: Protocol downgrade, MitM attacks.
- `max-age=63072000` = 2 years
- `includeSubDomains`: All subdomains forced to HTTPS
- `preload`: Submit to [HSTS Preload List](https://hstspreload.org/) for browser-shipped enforcement
- Must only be sent over HTTPS (browsers ignore over HTTP)
- Caution: Incorrect deployment can lock out users; start with short `max-age` and increase

**X-Content-Type-Options**
```
X-Content-Type-Options: nosniff
```
Protects against: MIME-sniffing attacks (e.g., treating uploaded text as executable script).

**X-Frame-Options**
```
X-Frame-Options: DENY
```
Protects against: Clickjacking.
- `DENY`: Block all framing
- `SAMEORIGIN`: Allow same-origin framing only
- **Superseded by** `frame-ancestors` CSP directive; use both for backward compatibility

#### Recommended Headers

**Referrer-Policy**
```
Referrer-Policy: strict-origin-when-cross-origin
```
Protects against: Referrer leakage of sensitive URLs/tokens.
- `no-referrer`: Never send referrer (most private)
- `strict-origin-when-cross-origin`: Full URL for same-origin, origin-only for cross-origin HTTPS, none for HTTP downgrade
- `same-origin`: Referrer only for same-origin requests

**Permissions-Policy**
```
Permissions-Policy: geolocation=(), camera=(), microphone=(), payment=(), usb=(), magnetometer=(), gyroscope=(), accelerometer=()
```
Protects against: Unauthorized access to browser features.
- `()` = disabled for all origins
- `(self)` = allowed for same origin only
- `("https://trusted.com")` = allowed for specific origin
- Disable all features your app does not use

**Cross-Origin-Opener-Policy (COOP)**
```
Cross-Origin-Opener-Policy: same-origin
```
Protects against: Spectre-type side-channel attacks, cross-origin window interactions.

**Cross-Origin-Resource-Policy (CORP)**
```
Cross-Origin-Resource-Policy: same-origin
```
Protects against: Cross-origin resource theft (Spectre), unauthorized embedding.

**Cross-Origin-Embedder-Policy (COEP)**
```
Cross-Origin-Embedder-Policy: require-corp
```
Protects against: Spectre exploitation. Required for `SharedArrayBuffer` and `performance.measureUserAgentSpecificMemory()`.

**Cache-Control** (for sensitive pages)
```
Cache-Control: no-store
```
Prevents caching of sensitive content (auth pages, account data, etc.).

#### Headers to Remove or Disable

| Header | Action | Reason |
|--------|--------|--------|
| `Server` | Remove or set generic value | Reveals server software version |
| `X-Powered-By` | Remove entirely | Reveals technology stack |
| `X-AspNet-Version` | Disable | Reveals framework version |
| `X-XSS-Protection` | Set to `0` or remove | Can create vulnerabilities; CSP supersedes |
| `Expect-CT` | Remove | Deprecated |
| `Public-Key-Pins` (HPKP) | Remove | Deprecated; can cause lockout |

### 7.2 Audit Checklist for Security Headers

- [ ] `Content-Security-Policy` present and strict (see Section 2)
- [ ] `Strict-Transport-Security` with `max-age >= 31536000` and `includeSubDomains`
- [ ] `X-Content-Type-Options: nosniff`
- [ ] `X-Frame-Options: DENY` (or SAMEORIGIN) and/or `frame-ancestors` in CSP
- [ ] `Referrer-Policy` set (not default browser behavior)
- [ ] `Permissions-Policy` disables unused features
- [ ] `Cross-Origin-Opener-Policy` set
- [ ] `Cross-Origin-Resource-Policy` set
- [ ] `Server` header does not reveal version info
- [ ] `X-Powered-By` removed
- [ ] `X-XSS-Protection` set to `0` or absent
- [ ] `Cache-Control: no-store` on sensitive pages

**Testing tools:**
- [Mozilla Observatory](https://observatory.mozilla.org/)
- [Security Headers](https://securityheaders.com/)
- [CSP Evaluator](https://csp-evaluator.withgoogle.com)

**Sources:**
- [OWASP HTTP Headers Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/HTTP_Headers_Cheat_Sheet.html)
- [OWASP Secure Headers Project](https://owasp.org/www-project-secure-headers/)
- [web.dev: Security Headers Quick Reference](https://web.dev/articles/security-headers)
- [MDN: Strict-Transport-Security](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Strict-Transport-Security)
- [MDN: Cross-Origin-Opener-Policy](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Cross-Origin-Opener-Policy)
- [MDN: Cross-Origin-Embedder-Policy](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Cross-Origin-Embedder-Policy)
- [OWASP HSTS Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/HTTP_Strict_Transport_Security_Cheat_Sheet.html)
- [OWASP Clickjacking Defense Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Clickjacking_Defense_Cheat_Sheet.html)

---

## 8. Frontend-Specific Vulnerability Patterns

### 8.1 Open Redirects

**Vulnerability:** Application redirects user to a URL from untrusted input without validation.

**Dangerous patterns:**
```javascript
// Vulnerable
window.location = getUrlParam('redirect');
window.location.href = userInput;
window.location.replace(userInput);
```

**Prevention:**
1. Avoid user-controlled redirects entirely when possible
2. Use server-side mapping (user provides ID, server maps to URL)
3. Allowlist validation of redirect targets
4. Parse URLs with `new URL()` -- never use string operations (startsWith, indexOf, regex)
5. Validate protocol is `https:` or `http:` (block `javascript:`, `data:`, `vbscript:`)
6. Confirmation page: "You are being redirected to X. Continue?"

**Audit checks:**
- [ ] Search for `window.location`, `location.href`, `location.assign`, `location.replace` with dynamic values
- [ ] Search for `<a href=` and `<form action=` with dynamic values
- [ ] Check for redirect URL in query parameters (`?redirect=`, `?next=`, `?return=`, `?url=`)
- [ ] Verify URL validation uses `new URL()` parser, not string matching

### 8.2 Clickjacking

**Defense layers (use all):**
1. CSP `frame-ancestors 'none'` (or `'self'` if self-framing needed)
2. `X-Frame-Options: DENY` (backward compatibility)
3. `SameSite` cookies to prevent session cookies in framed requests

**Audit checks:**
- [ ] `frame-ancestors` directive in CSP
- [ ] `X-Frame-Options` header present
- [ ] Sensitive actions (payments, password changes) have additional click confirmation

### 8.3 postMessage Security

**Sending messages:**
```javascript
// UNSAFE - any origin can receive
targetWindow.postMessage(data, '*');

// SAFE - specify expected origin
targetWindow.postMessage(data, 'https://trusted.example.com');
```

**Receiving messages:**
```javascript
window.addEventListener('message', (event) => {
  // REQUIRED: validate origin
  if (event.origin !== 'https://trusted.example.com') return;

  // REQUIRED: validate data type/structure
  if (typeof event.data !== 'object') return;

  // SAFE: use textContent, not innerHTML
  element.textContent = event.data.text;
});
```

**Audit checks:**
- [ ] All `postMessage()` calls specify a target origin (never `'*'` for sensitive data)
- [ ] All `message` event listeners validate `event.origin` against an allowlist
- [ ] Origin validation uses exact match (not `indexOf`, `includes`, or regex)
- [ ] Message data is not passed to `eval()`, `innerHTML`, or `document.write()`
- [ ] Message data structure is validated before use

### 8.4 WebSocket Security

**Key requirements:**
- Always use `wss://` (never `ws://` in production)
- Validate `Origin` header on handshake with explicit allowlist
- Authenticate connections (token in initial handshake, not in URL)
- Authorize each message action (not just connection establishment)
- Rate limit messages (baseline: 100/minute per connection)
- Set maximum message size (baseline: 64KB)
- Validate all message content (treat as untrusted input)
- Use `JSON.parse()` for message parsing (never `eval()`)
- Close connections on session expiry; re-validate periodically (every 30 min)
- Disable compression (`permessage-deflate`) unless needed (CRIME/BREACH risk)

**Audit checks:**
- [ ] WebSocket URLs use `wss://`
- [ ] Origin validation on server handshake
- [ ] Per-message authorization
- [ ] Message size and rate limits configured
- [ ] Input validation on all received messages

### 8.5 Web Worker Security

- Workers run in separate global scope (isolated from main thread)
- Never create Worker from user-supplied URL: `new Worker(userInput)` is dangerous
- Validate all messages sent to/from workers
- Workers can make network requests -- apply same CORS/CSP controls
- Workers can be abused for CPU-intensive attacks (crypto mining, DDoS)

### 8.6 Prototype Pollution

**What it is:** Attacker injects properties into `Object.prototype`, which are then inherited by all objects.

**Common sources:**
- URL query parameters: `?__proto__[isAdmin]=true`
- JSON input: `{"__proto__": {"isAdmin": true}}`
- `postMessage` data
- Deep merge/clone utilities (lodash `_.merge`, `_.defaultsDeep`)

**Prevention:**
```javascript
// Use null-prototype objects for user data
const config = Object.create(null);

// Freeze prototypes
Object.freeze(Object.prototype);

// Sanitize keys in merge operations
function safeMerge(target, source) {
  for (const key of Object.keys(source)) {
    if (key === '__proto__' || key === 'constructor' || key === 'prototype') continue;
    target[key] = source[key];
  }
}

// Use Map instead of plain objects for user-keyed data
const userData = new Map();
```

**Audit checks:**
- [ ] Search for deep merge/clone utilities -- check if they sanitize `__proto__`, `constructor`, `prototype`
- [ ] Check lodash version (older versions of `_.merge` are vulnerable)
- [ ] Search for `Object.assign` with user-controlled input
- [ ] Check URL parameter parsing for prototype pollution vectors
- [ ] Verify JSON schema validation rejects `__proto__` keys

### 8.7 DOM Clobbering

**What it is:** HTML injection of elements with `id` or `name` attributes that overwrite global variables or DOM APIs.

**Example attack:**
```html
<!-- Injected HTML (e.g., via user-generated content) -->
<img id="isAdmin">
<!-- Now window.isAdmin returns the img element instead of undefined -->
```

**Prevention:**
```javascript
// Always use explicit variable declarations
const isAdmin = false; // 'const' prevents clobbering

// Type-check DOM properties before use
if (typeof someVar === 'string') { ... }  // clobbered values are Element instances

// Use strict mode
'use strict';

// Sanitize id and name attributes with DOMPurify
DOMPurify.sanitize(html, { SANITIZE_NAMED_PROPS: true });
```

**Audit checks:**
- [ ] User-controlled HTML is sanitized with `SANITIZE_NAMED_PROPS: true`
- [ ] Global variables are explicitly declared (`const`, `let`, `var`)
- [ ] Code does not rely on `window.X` or `document.X` for security decisions without type checking
- [ ] Avoid `document.getElementById` for security-critical lookups without validation

**Sources:**
- [OWASP: Open Redirect](https://owasp.org/www-community/attacks/open_redirect)
- [OWASP: Unvalidated Redirects and Forwards Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Unvalidated_Redirects_and_Forwards_Cheat_Sheet.html)
- [OWASP: Clickjacking Defense Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Clickjacking_Defense_Cheat_Sheet.html)
- [OWASP: HTML5 Security Cheat Sheet (postMessage, Workers)](https://cheatsheetseries.owasp.org/cheatsheets/HTML5_Security_Cheat_Sheet.html)
- [OWASP: WebSocket Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/WebSocket_Security_Cheat_Sheet.html)
- [OWASP: DOM Clobbering Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/DOM_Clobbering_Prevention_Cheat_Sheet.html)
- [PortSwigger: Prototype Pollution](https://portswigger.net/web-security/prototype-pollution)
- [PortSwigger: Client-Side Prototype Pollution](https://portswigger.net/web-security/prototype-pollution/client-side)
- [PortSwigger: DOM Clobbering](https://portswigger.net/web-security/dom-based/dom-clobbering)
- [PortSwigger: Controlling Web Message Source](https://portswigger.net/web-security/dom-based/controlling-the-web-message-source)
- [MDN: Prototype Pollution](https://developer.mozilla.org/en-US/docs/Web/Security/Attacks/Prototype_pollution)
- [PortSwigger: Clickjacking](https://portswigger.net/web-security/clickjacking)

---

## 9. Secure Frontend Architecture Patterns

### 9.1 Input Validation (Defense in Depth)

Client-side validation is for UX, not security. Server-side validation is the authoritative control.

**Client-side validation patterns:**
- HTML5 validation attributes: `required`, `pattern`, `type="email"`, `minlength`, `maxlength`
- JavaScript validation before submission (immediate feedback)
- Sanitize display values (encode before rendering)

**What client-side validation should NOT do:**
- Be the sole check for security-critical input
- Enforce authorization rules
- Trust any client-side-only validation for server operations

**Audit checks:**
- [ ] Every form with client-side validation also has server-side validation
- [ ] Input type attributes used (`type="email"`, `type="url"`, `type="number"`)
- [ ] Pattern attributes use restrictive regex where appropriate

### 9.2 Secure Routing and Auth Guards

**SPA route protection pattern:**
```javascript
// React Router example
function ProtectedRoute({ children }) {
  const { isAuthenticated } = useAuth();
  if (!isAuthenticated) return <Navigate to="/login" />;
  return children;
}
```

**Critical:** Route guards are UX, not security. The server must enforce authorization on every API call regardless of client-side routing.

**Audit checks:**
- [ ] Auth guards present on protected routes
- [ ] Auth state checked on mount (not just initial load)
- [ ] Server APIs independently authorize requests (do not trust client route guards)
- [ ] Unauthorized API responses (401/403) trigger client-side redirect to login
- [ ] Deep links to protected routes properly redirect to login

### 9.3 Error Boundary Security

**What NOT to expose in error UIs:**
- Stack traces
- File paths
- Database queries or error messages
- Internal API URLs
- User tokens or session data
- Server configuration details

```javascript
// React error boundary
class SecureErrorBoundary extends React.Component {
  state = { hasError: false };
  static getDerivedStateFromError() { return { hasError: true }; }
  componentDidCatch(error, errorInfo) {
    // Log to monitoring service (Sentry, etc.) -- NOT to the DOM
    logErrorToService(error, errorInfo);
  }
  render() {
    if (this.state.hasError) {
      return <h1>Something went wrong. Please try again.</h1>;
    }
    return this.props.children;
  }
}
```

**Audit checks:**
- [ ] Error boundaries or global error handlers present
- [ ] Production error messages are generic (no stack traces, paths, or internal details)
- [ ] Errors logged to server-side monitoring, not rendered to DOM
- [ ] `console.error` calls removed or gated behind debug mode in production builds
- [ ] Source maps not publicly accessible in production

### 9.4 Secure Form Handling

- Set `autocomplete="off"` on sensitive fields (passwords, credit cards, SSNs)
- Set `spellcheck="false"` on sensitive fields (prevents data sent to spell-check services)
- Use `autocorrect="off"` and `autocapitalize="off"` on sensitive mobile fields
- Submit forms over HTTPS only
- Use `POST` method for state-changing forms (not GET)
- Include CSRF tokens in form submissions
- Validate file types client-side before upload (server must re-validate)

### 9.5 File Upload Client-Side Validation

```javascript
function validateFile(file) {
  const ALLOWED_TYPES = ['image/jpeg', 'image/png', 'image/webp'];
  const MAX_SIZE = 5 * 1024 * 1024; // 5MB

  if (!ALLOWED_TYPES.includes(file.type)) {
    throw new Error('Invalid file type');
  }
  if (file.size > MAX_SIZE) {
    throw new Error('File too large');
  }
  // Check magic bytes for additional validation
  return readFileHeader(file).then(header => {
    if (!isValidImageHeader(header)) {
      throw new Error('File content does not match type');
    }
  });
}
```

**Key principle:** Client-side file validation is defense-in-depth. The server MUST:
- Re-validate file type (by magic bytes, not extension or MIME)
- Re-validate file size
- Scan for malware
- Store files outside web root or in object storage
- Serve uploaded files with `Content-Disposition: attachment` and `X-Content-Type-Options: nosniff`

**Sources:**
- [OWASP: Input Validation Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Input_Validation_Cheat_Sheet.html)
- [OWASP: HTML5 Security Cheat Sheet (form fields)](https://cheatsheetseries.owasp.org/cheatsheets/HTML5_Security_Cheat_Sheet.html)
- [OWASP Top 10 Proactive Controls: Validate All Input](https://top10proactive.owasp.org/archive/2024/the-top-10/c3-validate-input-and-handle-exceptions/)

---

## 10. Frontend Security Testing

### 10.1 Browser DevTools Security Auditing

**Manual checks using DevTools:**

| Tab | What to Check |
|-----|---------------|
| **Network** | Missing security headers; mixed content (HTTP on HTTPS pages); cookies without Secure/HttpOnly flags; unnecessary data in responses |
| **Application > Cookies** | Cookie flags (Secure, HttpOnly, SameSite); cookie lifetimes; sensitive data in cookies |
| **Application > Storage** | Sensitive data in localStorage/sessionStorage/IndexedDB |
| **Console** | CSP violation warnings; mixed content warnings; deprecated API warnings |
| **Security** | Certificate validity; TLS version; mixed content overview |
| **Sources** | Source maps accessible in production; sensitive comments in code |

### 10.2 Lighthouse Security Audits

Lighthouse (built into Chrome DevTools) checks:
- HTTPS usage and mixed content
- Missing security headers (HSTS, CSP via Best Practices audit)
- Vulnerable JavaScript libraries (integrates with Snyk DB)
- Links to cross-origin destinations without `rel="noopener"`
- Insecure form actions

**Run:** DevTools > Lighthouse tab > Check "Best Practices" > Generate Report

**Limitations:** Lighthouse is not a security scanner. It catches common misconfigurations but does not test for XSS, CSRF, or logic vulnerabilities.

### 10.3 OWASP ZAP for Frontend

ZAP (Zed Attack Proxy) is the primary free DAST tool for web applications.

**Frontend-relevant capabilities:**
- Automated spider and active scan
- Passive scan of all proxied traffic (header checks, cookie flags, etc.)
- Ajax Spider for SPA crawling (uses a real browser)
- DOM XSS scanner (optional plugin -- limited effectiveness for complex DOM XSS)
- Fuzzer for input testing
- WebSocket testing

**CI/CD integration:**
```bash
# ZAP baseline scan (passive only, fast)
docker run -t zaproxy/zap-stable zap-baseline.py -t https://myapp.com

# ZAP full scan (active, slower)
docker run -t zaproxy/zap-stable zap-full-scan.py -t https://myapp.com

# ZAP API scan (for REST APIs)
docker run -t zaproxy/zap-stable zap-api-scan.py -t https://myapp.com/openapi.json -f openapi
```

**Limitation:** Automated DOM XSS detection is unreliable. Manual testing with DOM Invader (Burp Suite) is more effective for complex DOM XSS.

### 10.4 Automated CSP and Header Scanning Tools

| Tool | Type | URL |
|------|------|-----|
| **Mozilla Observatory** | Online scanner | https://observatory.mozilla.org/ |
| **Security Headers** | Online scanner | https://securityheaders.com/ |
| **CSP Evaluator** | CSP policy analyzer | https://csp-evaluator.withgoogle.com/ |
| **Report URI** | CSP/security header monitoring | https://report-uri.com/ |
| **helmet** (Node.js) | Middleware | Sets secure headers by default |
| **csp_evaluator** (npm) | CLI tool | Offline CSP analysis |

### 10.5 DOM XSS Testing Tools

| Tool | Description |
|------|-------------|
| **DOM Invader** (Burp Suite) | Browser extension for DOM XSS, prototype pollution, postMessage testing |
| **Semgrep** | Static analysis with DOM XSS rules for React, Vue, Angular |
| **ESLint security plugins** | `eslint-plugin-security`, `eslint-plugin-no-unsanitized` |
| **Trusted Types (report-only)** | Browser-native DOM XSS detection in production |
| **RetireJS** | Detects known-vulnerable JavaScript libraries |

### 10.6 Recommended Security Testing Pipeline

```
1. Development:
   - ESLint with security plugins (no-unsanitized, security)
   - Semgrep rules for framework-specific XSS patterns
   - npm audit / Snyk in pre-commit or CI

2. CI/CD:
   - ZAP baseline scan (passive, header checks)
   - Lighthouse CI (best practices score)
   - SRI hash verification
   - CSP Evaluator validation

3. Pre-release:
   - ZAP full scan (active scanning)
   - Manual DOM XSS testing with DOM Invader
   - Header review with Mozilla Observatory

4. Production:
   - Trusted Types in report-only mode
   - CSP reporting enabled (report-uri/report-to)
   - Continuous dependency monitoring (Snyk, Dependabot)
```

**Sources:**
- [OWASP: Testing Tools Resource](https://owasp.org/www-project-web-security-testing-guide/v41/6-Appendix/A-Testing_Tools_Resource)
- [OWASP: Testing for DOM-based XSS](https://owasp.org/www-project-web-security-testing-guide/v41/4-Web_Application_Security_Testing/11-Client_Side_Testing/01-Testing_for_DOM-based_Cross_Site_Scripting)
- [OWASP: Testing for Reflected XSS](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/07-Input_Validation_Testing/01-Testing_for_Reflected_Cross_Site_Scripting)
- [OWASP: Vulnerability Scanning Tools](https://owasp.org/www-community/Vulnerability_Scanning_Tools)
- [OWASP: DevSecOps Guideline - DAST](https://owasp.org/www-project-devsecops-guideline/latest/02b-Dynamic-Application-Security-Testing)
- [PortSwigger: DOM Invader](https://portswigger.net/burp/documentation/desktop/tools/dom-invader)

---

## 11. Modern Frontend Framework Security

### 11.1 React

**Auto-escaping and its limits:**
- JSX `{variable}` auto-escapes text content (HTML entities)
- Does NOT escape HTML attributes in all cases
- Does NOT prevent `javascript:` in `href`, `action`, `formAction`, or `src` attributes

**Specific vulnerabilities to audit:**

| Pattern | Risk | Fix |
|---------|------|-----|
| `dangerouslySetInnerHTML={{__html: userInput}}` | XSS | Sanitize with DOMPurify |
| `<a href={userInput}>` | javascript: URL XSS | Validate protocol with `new URL()` |
| `ref.current.innerHTML = userInput` | DOM XSS bypass | Use `textContent` |
| JSON in SSR: `<script>var data = ${JSON.stringify(data)}</script>` | Script injection via `</script>` | Escape `<` chars: replace `<` with `\u003c` |
| `eval()` or `new Function()` with user data | Code injection | Refactor to avoid eval |

**React-specific ESLint rules:**
- `react/no-danger` -- flags `dangerouslySetInnerHTML`
- `react/jsx-no-target-blank` -- requires `rel="noopener noreferrer"`
- `react/jsx-no-script-url` -- flags `javascript:` in JSX

### 11.2 Next.js

**Server Components security:**
- Server Components run on the server -- do NOT pass sensitive data as props to Client Components
- Client Components receive serialized props -- never include secrets, API keys, or DB credentials
- Server Actions validate input server-side (client can send arbitrary data)
- Critical CVE (Dec 2025): RSC "Flight" protocol had RCE via unsafe deserialization -- keep Next.js updated

**Middleware auth pattern:**
```typescript
// middleware.ts
import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function middleware(request: NextRequest) {
  const token = request.cookies.get('session');
  if (!token && request.nextUrl.pathname.startsWith('/dashboard')) {
    return NextResponse.redirect(new URL('/login', request.url));
  }
  return NextResponse.next();
}
```

**Caution:** Middleware runs at the edge. Full auth validation must happen in API routes or server components. Middleware is a first-pass filter, not the authorization boundary.

**API Routes:**
- Validate auth on every API route independently
- Apply rate limiting
- Validate request body schema
- Set appropriate security headers

**Audit checks for Next.js:**
- [ ] Next.js version is current (check for RSC deserialization CVEs)
- [ ] Server Components do not pass secrets to Client Components
- [ ] Server Actions validate all input
- [ ] Middleware does not serve as sole authorization
- [ ] API routes independently validate auth and input
- [ ] `next.config.js` security headers configured
- [ ] Image optimization uses allowlisted domains (`images.remotePatterns`)

### 11.3 Vue

**Auto-escaping and escape hatches:**
- Template expressions `{{ }}` auto-escape
- `v-html` renders raw HTML (XSS risk)
- `v-bind:href` can accept `javascript:` URLs

**Vue-specific risks:**
- Template compilation from user input = template injection (if using runtime compiler)
- `v-html` with unsanitized content
- CVE-2024-6783: vue-template-compiler XSS in certain configurations
- `vue-i18n` XSS when `escapeParameterHtml: true` with malicious translation payloads

**Audit checks for Vue:**
- [ ] No `v-html` with unsanitized user input
- [ ] No user input in `v-bind:href` without protocol validation
- [ ] Runtime template compiler not used with user input
- [ ] `vue-i18n` translation strings sanitized
- [ ] Vue version current

### 11.4 Svelte

**Auto-escaping and escape hatches:**
- Normal `{expression}` is auto-escaped
- `{@html expression}` renders raw HTML (XSS risk)

**Audit checks for Svelte:**
- [ ] No `{@html}` with unsanitized user input
- [ ] No `bind:this` to inject innerHTML
- [ ] Component props with HTML content are sanitized

### 11.5 Angular

**Strict Contextual Escaping (SCE):**
- Angular sanitizes all values by default based on security context (HTML, style, URL, resource URL)
- Built-in `DomSanitizer` service

**Dangerous bypasses to audit:**
```typescript
// All of these disable sanitization -- audit every use
this.sanitizer.bypassSecurityTrustHtml(value);
this.sanitizer.bypassSecurityTrustScript(value);
this.sanitizer.bypassSecurityTrustUrl(value);
this.sanitizer.bypassSecurityTrustResourceUrl(value);
this.sanitizer.bypassSecurityTrustStyle(value);
```

**Angular-specific risks:**
- Template injection if user input is compiled as an Angular template (AOT compilation prevents this)
- `[innerHTML]` binding sanitized by default, but `bypassSecurityTrust*` disables it
- Expression sandbox was removed in Angular 1.6 -- AngularJS (1.x) is inherently less secure

**Audit checks for Angular:**
- [ ] Search for all `bypassSecurityTrust*` calls -- verify each is justified and input is validated
- [ ] No user input compiled as Angular templates
- [ ] Not using AngularJS (1.x) -- if so, upgrade is a security finding
- [ ] `[innerHTML]` bindings reviewed (sanitized by default, but check for bypasses)
- [ ] Angular version current

### 11.6 Cross-Framework Audit Summary

| Check | React | Vue | Angular | Svelte | Next.js |
|-------|-------|-----|---------|--------|---------|
| Raw HTML rendering | `dangerouslySetInnerHTML` | `v-html` | `bypassSecurityTrustHtml` | `{@html}` | Same as React |
| javascript: URLs | `href={input}` | `v-bind:href` | `[href]="input"` | `href={input}` | Same as React |
| Template injection | N/A (no template compiler) | Runtime compiler | AOT prevents | N/A | N/A |
| SSR data injection | `JSON.stringify` in `<script>` | SSR serialization | Universal serialization | SvelteKit serialization | Server Component props |
| Auto-escaping | JSX `{}` | `{{ }}` | Interpolation `{{ }}` | `{}` | JSX `{}` |

**Sources:**
- [Snyk: 10 React Security Best Practices](https://snyk.io/blog/10-react-security-best-practices/)
- [Snyk: Comparing React and Angular Secure Coding Practices](https://snyk.io/blog/comparing-react-and-angular-secure-coding-practices/)
- [Snyk: React Server Components & Next.js Critical RCE Vulnerabilities](https://snyk.io/blog/security-advisory-critical-rce-vulnerabilities-react-server-components/)
- [PortSwigger: Client-Side Template Injection](https://portswigger.net/web-security/cross-site-scripting/contexts/client-side-template-injection)
- [Snyk: Vue XSS Vulnerabilities](https://security.snyk.io/vuln/npm:vue:20180802)
- [Snyk: vue-template-compiler XSS (CVE-2024-6783)](https://security.snyk.io/vuln/SNYK-JS-VUETEMPLATECOMPILER-7554675)
- [OWASP: XSS Prevention Cheat Sheet (Framework Security)](https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html)
- [OWASP: Testing for OAuth Weaknesses](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/05-Authorization_Testing/05-Testing_for_OAuth_Weaknesses)

---

## Appendix A: Master Audit Checklist

This is a consolidated checklist of all audit items from the sections above, organized by priority.

### Critical (must fix)

- [ ] No `innerHTML` / `dangerouslySetInnerHTML` / `v-html` / `{@html}` with unsanitized user input
- [ ] No `eval()`, `new Function()`, `setTimeout(string)` with user input
- [ ] CSP header present with nonce or hash (no `unsafe-inline` in script-src)
- [ ] Session cookies have `HttpOnly`, `Secure`, and `SameSite` flags
- [ ] Authentication tokens not stored in localStorage
- [ ] HTTPS enforced with HSTS header
- [ ] No sensitive data in URL query parameters
- [ ] Server-side validation on all inputs (client-side is defense-in-depth only)
- [ ] CSRF protection on all state-changing endpoints
- [ ] OAuth2 uses PKCE (not implicit grant)
- [ ] Framework and dependencies up to date (check for known CVEs)

### High (should fix)

- [ ] `X-Content-Type-Options: nosniff` header present
- [ ] `X-Frame-Options: DENY` or CSP `frame-ancestors` present
- [ ] `Referrer-Policy` header set
- [ ] SRI hashes on all CDN-hosted scripts and stylesheets
- [ ] `object-src 'none'` and `base-uri 'none'` in CSP
- [ ] `postMessage` calls specify target origin (never `*`)
- [ ] `postMessage` listeners validate `event.origin`
- [ ] WebSocket connections use `wss://` with origin validation
- [ ] No `javascript:` protocol in dynamic `href` attributes
- [ ] Error UIs do not expose stack traces, file paths, or internal details
- [ ] Source maps not publicly accessible in production
- [ ] `Permissions-Policy` header disables unused browser features
- [ ] Production builds strip `console.log` / debug output

### Medium (recommended)

- [ ] Trusted Types CSP directive (at least in report-only mode)
- [ ] `Cross-Origin-Opener-Policy` and `Cross-Origin-Resource-Policy` headers
- [ ] DOMPurify configured with `SANITIZE_NAMED_PROPS: true`
- [ ] Prototype pollution prevention in deep merge utilities
- [ ] CSP reporting configured (`report-uri` or `report-to`)
- [ ] Third-party script inventory maintained
- [ ] Tag manager access secured with 2FA
- [ ] Refresh token rotation with reuse detection
- [ ] Multi-tab logout handled (BroadcastChannel or storage event)
- [ ] `Cache-Control: no-store` on sensitive pages
- [ ] `Server` and `X-Powered-By` headers removed or anonymized
- [ ] `npm audit` or Snyk runs in CI pipeline
- [ ] Form fields with sensitive data use `autocomplete="off"`, `spellcheck="false"`
- [ ] File upload validation (client-side + server-side with magic byte checking)

---

## Appendix B: Primary Source Index

### OWASP Cheat Sheet Series
- [XSS Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html)
- [DOM-based XSS Prevention](https://cheatsheetseries.owasp.org/cheatsheets/DOM_based_XSS_Prevention_Cheat_Sheet.html)
- [XSS Filter Evasion](https://cheatsheetseries.owasp.org/cheatsheets/XSS_Filter_Evasion_Cheat_Sheet.html)
- [Content Security Policy](https://cheatsheetseries.owasp.org/cheatsheets/Content_Security_Policy_Cheat_Sheet.html)
- [CSRF Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html)
- [Session Management](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html)
- [Authentication](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
- [HTTP Headers](https://cheatsheetseries.owasp.org/cheatsheets/HTTP_Headers_Cheat_Sheet.html)
- [HTML5 Security](https://cheatsheetseries.owasp.org/cheatsheets/HTML5_Security_Cheat_Sheet.html)
- [Third Party JavaScript Management](https://cheatsheetseries.owasp.org/cheatsheets/Third_Party_Javascript_Management_Cheat_Sheet.html)
- [Clickjacking Defense](https://cheatsheetseries.owasp.org/cheatsheets/Clickjacking_Defense_Cheat_Sheet.html)
- [DOM Clobbering Prevention](https://cheatsheetseries.owasp.org/cheatsheets/DOM_Clobbering_Prevention_Cheat_Sheet.html)
- [WebSocket Security](https://cheatsheetseries.owasp.org/cheatsheets/WebSocket_Security_Cheat_Sheet.html)
- [Unvalidated Redirects and Forwards](https://cheatsheetseries.owasp.org/cheatsheets/Unvalidated_Redirects_and_Forwards_Cheat_Sheet.html)
- [Input Validation](https://cheatsheetseries.owasp.org/cheatsheets/Input_Validation_Cheat_Sheet.html)
- [OAuth2](https://cheatsheetseries.owasp.org/cheatsheets/OAuth2_Cheat_Sheet.html)
- [HSTS](https://cheatsheetseries.owasp.org/cheatsheets/HTTP_Strict_Transport_Security_Cheat_Sheet.html)

### MDN Web Docs
- [Content-Security-Policy](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Content-Security-Policy)
- [CSP Implementation Guide](https://developer.mozilla.org/en-US/docs/Web/Security/Practical_implementation_guides/CSP)
- [Subresource Integrity](https://developer.mozilla.org/en-US/docs/Web/Security/Defenses/Subresource_Integrity)
- [SRI Implementation Guide](https://developer.mozilla.org/en-US/docs/Web/Security/Practical_implementation_guides/SRI)
- [Secure Cookie Configuration](https://developer.mozilla.org/en-US/docs/Web/Security/Practical_implementation_guides/Cookies)
- [Using HTTP Cookies](https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/Cookies)
- [Strict-Transport-Security](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Strict-Transport-Security)
- [Cross-Origin-Opener-Policy](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Cross-Origin-Opener-Policy)
- [Cross-Origin-Embedder-Policy](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Cross-Origin-Embedder-Policy)
- [Trusted Types API](https://developer.mozilla.org/en-US/docs/Web/API/Trusted_Types_API)
- [Supply Chain Attacks](https://developer.mozilla.org/en-US/docs/Web/Security/Attacks/Supply_chain_attacks)
- [Prototype Pollution](https://developer.mozilla.org/en-US/docs/Web/Security/Attacks/Prototype_pollution)
- [Cross-site Scripting (XSS)](https://developer.mozilla.org/en-US/docs/Web/Security/Attacks/XSS)
- [Securing your CDN with SRI](https://developer.mozilla.org/en-US/blog/securing-cdn-using-sri-why-how/)

### web.dev
- [Strict CSP](https://web.dev/articles/strict-csp)
- [Trusted Types](https://web.dev/articles/trusted-types)
- [Security Headers Quick Reference](https://web.dev/articles/security-headers)

### PortSwigger Web Security Academy
- [Prototype Pollution](https://portswigger.net/web-security/prototype-pollution)
- [Client-Side Prototype Pollution](https://portswigger.net/web-security/prototype-pollution/client-side)
- [DOM Clobbering](https://portswigger.net/web-security/dom-based/dom-clobbering)
- [Controlling Web Message Source](https://portswigger.net/web-security/dom-based/controlling-the-web-message-source)
- [Client-Side Template Injection](https://portswigger.net/web-security/cross-site-scripting/contexts/client-side-template-injection)
- [Clickjacking](https://portswigger.net/web-security/clickjacking)
- [DOM Invader](https://portswigger.net/burp/documentation/desktop/tools/dom-invader)

### Snyk
- [10 React Security Best Practices](https://snyk.io/blog/10-react-security-best-practices/)
- [Comparing React and Angular Secure Coding Practices](https://snyk.io/blog/comparing-react-and-angular-secure-coding-practices/)
- [React Server Components Critical RCE](https://snyk.io/blog/security-advisory-critical-rce-vulnerabilities-react-server-components/)

### Auth0
- [Authorization Code Flow with PKCE](https://auth0.com/docs/get-started/authentication-and-authorization-flow/authorization-code-flow-with-pkce)
- [Token Storage](https://auth0.com/docs/secure/security-guidance/data-security/token-storage)
- [Refresh Token Rotation for SPAs](https://auth0.com/blog/securing-single-page-applications-with-refresh-token-rotation/)
- [Backend-for-Frontend Pattern](https://auth0.com/blog/the-backend-for-frontend-pattern-bff/)
- [OAuth Security: State vs Nonce vs PKCE](https://auth0.com/blog/demystifying-oauth-security-state-vs-nonce-vs-pkce/)

### Tools
- [CSP Evaluator](https://csp-evaluator.withgoogle.com)
- [Mozilla Observatory](https://observatory.mozilla.org/)
- [Security Headers Scanner](https://securityheaders.com/)
- [HSTS Preload List](https://hstspreload.org/)
- [OWASP ZAP](https://www.zaproxy.org/)
- [content-security-policy.com](https://content-security-policy.com/)
