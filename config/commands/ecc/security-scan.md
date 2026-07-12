---
description: Run security scan against code, agents, hooks, MCP servers, and permission surfaces. Reports prioritized findings and remediation plan.
argument-hint: "[path] [--format json|markdown] [--min-severity low|medium|high|critical]"
---

# Security Scan

Run a comprehensive security scan against the current project or a target path: $ARGUMENTS

## Your Task

Load the security-review skill and conduct a structured security audit:

```
skill(name="security-review")
```

## Scan Surfaces

### 1. Application Code

Run the OWASP Top 10 checklist from the security-review skill against all source files. Scan for:

- **Hardcoded secrets** — API keys, passwords, tokens, credentials in source
- **Injection vulnerabilities** — SQL, command, template injection patterns
- **XSS** — `innerHTML`, `dangerouslySetInnerHTML`, unsanitized DOM writes
- **Insecure deserialization** — `eval()`, unsafe JSON parsing of user input
- **Missing auth checks** — Unprotected routes, missing middleware
- **Race conditions** — Non-atomic read-then-write in state/financial ops
- **CSRF gaps** — State-changing operations without CSRF tokens or SameSite cookies
- **Insecure cookies** — Missing Secure, HttpOnly, or SameSite flags

### 2. Agent & Infrastructure Surfaces

Audit without external tool dependencies:

- **Agent prompts** — Prompts that process untrusted content without input validation or output sanitization
- **MCP server configs** — Servers with shell access, filesystem access, remote transport, or unpinned `npx` that could execute attacker-controlled code
- **Plugin hooks** — Executable hooks (`file.edited`, `tool.execute.before/after`) that run code on trigger
- **Permission surfaces** — Overly broad tool permissions that bypass user approval gates

### 3. Dependency Surface

- Run `npm audit` (or language-equivalent: `pip audit`, `cargo audit`, `bundler-audit`)
- Check for known CVEs in direct and transitive dependencies
- Flag packages with known vulnerabilities at `--audit-level=high` or above

## Output Contract

### 1. Security Grade and Score

```
Security Grade: A / B / C / D / F
Score: X/100
```

### 2. Findings by Severity

| Severity | Count | Runtime Confidence |
|----------|-------|-------------------|
| CRITICAL | N | High / Medium / Low |
| HIGH | N | High / Medium / Low |
| MEDIUM | N | High / Medium / Low |
| LOW | N | High / Medium / Low |

### 3. Critical and High Findings

For each CRITICAL or HIGH finding:

```
Finding: [title]
Path: [file:line]
Severity: [critical|high]
Confidence: [high|medium|low]
Impact: [what's at risk]
Remediation: [concrete fix]
Auto-fix safe: [yes|no]
```

### 4. Remediation Order

Priority-ordered fix plan:

1. Rotate any exposed secrets immediately
2. Fix CRITICAL findings (block merge)
3. Fix HIGH findings (must fix before release)
4. Create tickets for MEDIUM findings
5. Note LOW findings for future cleanup

### 5. Scan Context

- Target path and scope
- Files scanned (count)
- Surfaces covered (application, agent/infra, dependencies)
- Methodology (OWASP Top 10 + agent surface audit + dependency audit)

---

**IMPORTANT**: If CRITICAL findings include hardcoded secrets in git history, those secrets must be rotated (revoked and regenerated) — removing them from code is not enough. Review the entire codebase for similar patterns; one found instance often means more.

**NOTE**: This command uses the `security-review` skill's OWASP methodology and vulnerability pattern detection. It does not require external scanners — all checks are performed through code inspection and analysis.
