# OWASP Top 10 Categories

Detailed per-category check tables, common vulnerabilities, and remediation examples. Consult this when working through the OWASP Top 10 checklist in the main SKILL.md.

## Table of Contents

- [1. Injection](#1-injection)
- [2. Broken Authentication](#2-broken-authentication)
- [3. Sensitive Data Exposure](#3-sensitive-data-exposure)
- [4. XML External Entities (XXE)](#4-xml-external-entities-xxe)
- [5. Broken Access Control](#5-broken-access-control)
- [6. Security Misconfiguration](#6-security-misconfiguration)
- [7. Cross-Site Scripting (XSS)](#7-cross-site-scripting-xss)
- [8. Insecure Deserialization](#8-insecure-deserialization)
- [9. Known Vulnerable Components](#9-known-vulnerable-components)
- [10. Insufficient Logging & Monitoring](#10-insufficient-logging--monitoring)

---

## 1. Injection

SQL, NoSQL, command, and LDAP injection occur when untrusted data is sent to an interpreter as part of a command or query.

| What to check | Pass criteria |
|---------------|---------------|
| Query parameterization | All queries use parameterized statements or ORM query builders — no string concatenation |
| Input sanitization | User input is validated against an allowlist before use |
| ORM safety | Raw query escape hatches are not used with user input |
| Command execution | No `exec()`, `system()`, or shell invocations with user-controlled data |

**Common vulnerabilities:**

- String concatenation in SQL queries: `` `SELECT * FROM users WHERE id = ${userId}` ``
- Dynamic query building without escaping
- `eval()` or `Function()` on user input
- Template literals passed to database drivers

**Remediation:**

```javascript
// BAD: SQL injection vulnerability
const query = `SELECT * FROM users WHERE id = ${userId}`

// GOOD: Parameterized queries
const { data } = await supabase
  .from('users')
  .select('*')
  .eq('id', userId)
```

## 2. Broken Authentication

Weaknesses in authentication and session management that allow attackers to compromise identities.

| What to check | Pass criteria |
|---------------|---------------|
| Password hashing | bcrypt, argon2, or scrypt — never MD5/SHA alone |
| JWT validation | Signature verified, expiry checked, issuer validated |
| Session security | Secure, HttpOnly, SameSite cookies; session rotation on login |
| MFA | Available for sensitive operations |
| Brute force | Rate limiting or account lockout on auth endpoints |

**Common vulnerabilities:**

- Permittable login flows without rate limiting
- Session IDs exposed in URLs
- Passwords stored in plaintext or with weak hashing
- JWTs with `alg: none` or weak signing keys

## 3. Sensitive Data Exposure

Failure to protect sensitive data (PII, credentials, financial data) at rest and in transit.

| What to check | Pass criteria |
|---------------|---------------|
| HTTPS enforced | All traffic encrypted in transit; HSTS header set |
| Secrets management | Secrets in environment variables or vault — never in source |
| Encryption at rest | PII and credentials encrypted in database |
| Log sanitization | No passwords, tokens, or PII in log output |

**Common vulnerabilities:**

- Hardcoded API keys or passwords in source code
- Logging request bodies that contain credentials
- Transmitting PII over unencrypted connections
- Storing credit card data in plaintext

## 4. XML External Entities (XXE)

Improper processing of XML input that allows entity resolution, leading to file disclosure or SSRF.

| What to check | Pass criteria |
|---------------|---------------|
| XML parser config | External entities and DTDs disabled |
| Input format | JSON preferred over XML where possible |

**Remediation:**

```javascript
// Node.js — disable external entities
const parser = new DOMParser({
  noent: false,
  dtd: { external: false }
})
```

## 5. Broken Access Control

Restrictions on what authenticated users are allowed to do are not properly enforced.

| What to check | Pass criteria |
|---------------|---------------|
| Route-level auth | Every route has explicit authorization checks |
| Object references | Direct object references validated against ownership |
| CORS | Origin allowlist is explicit, not `*` with credentials |
| Directory traversal | File paths validated, no `../` passthrough |

**Common vulnerabilities:**

- Missing middleware on sensitive routes
- IDOR: accessing resources by guessing sequential IDs
- Privilege escalation via parameter tampering
- CORS misconfiguration allowing credential theft

## 6. Security Misconfiguration

Insecure default configurations, incomplete or ad hoc configurations, open cloud storage, misconfigured HTTP headers, and verbose error messages.

| What to check | Pass criteria |
|---------------|---------------|
| Default credentials | All defaults changed in production |
| Error handling | Stack traces not exposed to users |
| Security headers | CSP, X-Frame-Options, X-Content-Type-Options set |
| Debug mode | Disabled in production environments |
| Unused features | Unnecessary endpoints, frameworks, and ports removed |

## 7. Cross-Site Scripting (XSS)

Injection of malicious scripts into trusted websites.

| What to check | Pass criteria |
|---------------|---------------|
| Output escaping | All dynamic content escaped for context (HTML, JS, URL, CSS) |
| Content-Security-Policy | CSP header restricts inline scripts and external sources |
| Framework defaults | Auto-escaping enabled; raw HTML insertion avoided |
| DOM manipulation | `textContent` for plain text; DOMPurify for HTML content |

**Common vulnerabilities:**

- `innerHTML` with unsanitized user input
- `dangerouslySetInnerHTML` in React without sanitization
- `v-html` in Vue with user-controlled data
- URL parameters rendered without encoding

**Remediation:**

```javascript
// BAD: XSS vulnerability
element.innerHTML = userInput

// GOOD: Safe alternatives
element.textContent = userInput           // For plain text
element.innerHTML = DOMPurify.sanitize(userInput)  // For HTML content
```

## 8. Insecure Deserialization

Attacker-controlled data deserialized into objects, leading to remote code execution.

| What to check | Pass criteria |
|---------------|---------------|
| Safe deserialization | No `eval()`, `unpickle`, or `unmarshal` on user input |
| Type validation | Deserialized objects validated against expected schema |
| Library currency | Deserialization libraries up to date |

**Common vulnerabilities:**

- `JSON.parse()` on untrusted input without validation (prototype pollution)
- `pickle.loads()` on user-controlled data in Python
- Java `ObjectInputStream.readObject()` on untrusted data

## 9. Known Vulnerable Components

Using libraries, frameworks, or dependencies with known security weaknesses.

| What to check | Pass criteria |
|---------------|---------------|
| Dependency audit | `npm audit`, `pip audit`, `cargo audit` clean |
| CVE monitoring | Known CVEs tracked and patched |
| Version pinning | Dependencies pinned to specific versions |
| Update cadence | Critical patches applied within 72 hours |

## 10. Insufficient Logging & Monitoring

Failure to log security events and monitor for active attacks.

| What to check | Pass criteria |
|---------------|---------------|
| Security event logging | Auth failures, access control failures, input validation failures logged |
| Log integrity | Logs protected from tampering |
| Alerting | Automated alerts for suspicious patterns |
| Incident response | Runbook exists for common attack patterns |
