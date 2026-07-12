---
name: security-review
description: OWASP Top 10 security review methodology, vulnerability pattern detection, and ECC AgentShield integration for agent/hook/MCP/permission surfaces. Use when reviewing code for security issues — injection attacks, broken authentication, sensitive data exposure, XSS, insecure deserialization, and other common vulnerabilities. Also use when auditing agent prompts, MCP server configs, plugin hooks, or permission surfaces for security weaknesses. Trigger when security-sensitive code changes are detected, before merging PRs touching auth, data access, payment flows, or agent configurations.
---

# Security Review

Conduct thorough OWASP Top 10 security analysis on code, configurations, and dependencies. This skill provides a structured methodology for identifying, categorizing, and remediating security vulnerabilities before they reach production.

## When to Use

**Trigger conditions:**

- Reviewing a PR that touches authentication, authorization, payments, or data access
- Writing code that handles user input, credentials, or sensitive data
- Auditing an existing module for vulnerabilities
- Configuring deployment, environment settings, or security headers
- Before merging any code that processes external input
- Reviewing agent prompts, MCP server configurations, plugin hooks, or permission rules
- After running `npx ecc-agentshield scan` — reviewing and prioritizing findings

**Do NOT use this skill when:**

- Making cosmetic or documentation-only changes (no code behavior changes)
- Working on pure UI/styling changes with no data flow implications
- Reviewing internal tooling that never processes user input or sensitive data
- The code is already covered by automated security scanning with recent clean results

## Security Review Workflow

### Step 1: Scope the Review

Identify the attack surface:

- What user inputs does the code accept?
- What external systems does it interact with?
- What data does it persist or transmit?
- What authentication and authorization boundaries exist?

### Step 2: Run the OWASP Top 10 Checklist

Work through each of the 10 categories systematically. For detailed per-category check tables, common vulnerabilities, and remediation examples, consult:

[`references/owasp-categories.md`](file:///home/opencode/.config/opencode/skills/security-review/references/owasp-categories.md)

### Step 3: Detect Vulnerability Patterns

Scan for these high-priority patterns. For detailed code examples of each pattern with before/after fixes, see:

[`references/vulnerability-patterns.md`](file:///home/opencode/.config/opencode/skills/security-review/references/vulnerability-patterns.md)

| Pattern | Severity | What to Look For |
|---------|----------|------------------|
| Hardcoded Secrets | CRITICAL | API keys, passwords, tokens in source |
| SQL Injection | CRITICAL | String concatenation in queries, unparameterized calls |
| XSS | HIGH | `innerHTML`, unsanitized user content in DOM |
| Race Conditions | CRITICAL | Non-atomic read-then-write in financial/state ops |
| Insecure Deserialization | HIGH | `eval()`, unsafe JSON parsing of user input |
| Missing Auth Checks | HIGH | Unprotected routes, missing middleware |
| CSRF Protection | HIGH | State-changing operations without CSRF tokens or SameSite cookies |
| Insecure Cookies | MEDIUM | Missing Secure, HttpOnly, or SameSite flags on auth cookies |

### Step 4: Produce a Security Review Report

Use the report format template:

[`references/report-format.md`](file:///home/opencode/.config/opencode/skills/security-review/references/report-format.md)

### Step 5: Verify Remediation

After fixes are applied, re-run the checklist. Critical and High issues must be resolved before merging. Medium issues should have a tracking ticket. Low issues may be noted for future cleanup.

### Step 6: Run Automated Scanners

In addition to manual review, run automated scanning tools:

- **AgentShield (agent/hook/MCP surfaces):** `npx ecc-agentshield scan --path .` — detects hardcoded secrets, broad permissions, executable hooks, MCP servers with shell/filesystem/remote transport access, and agent prompts handling untrusted content without defenses. Returns a security grade and prioritized remediation plan.
- **ECC security-audit tool:** Three audit types — `dependencies` (npm audit), `secrets` (regex-based detection of API keys, passwords, JWT tokens, GitHub tokens, AWS secrets), `code` (eval, innerHTML, dangerouslySetInnerHTML, document.write, SQL injection patterns).

These scanners complement manual review — they catch patterns at scale, but cannot replace contextual judgment.

## Security Response Protocol

When a security vulnerability is found:

1. **STOP** the current implementation work immediately
2. **Triage the severity** using the Priority Rules below
3. **Fix CRITICAL issues** before continuing with any other work
4. **Rotate any exposed secrets** — if credentials were committed, revoke and regenerate them
5. **Review the entire codebase** for similar patterns — one found instance often means more
6. **Document the finding** in the security review report

## Priority Rules

- **CRITICAL** (hardcoded secrets, SQL injection, auth bypass, race conditions in financial code) — block merge, fix immediately
- **HIGH** (XSS, missing auth on sensitive routes, exposed PII) — must fix before next release
- **MEDIUM** (security header gaps, missing rate limiting, stale dependencies) — ticket required
- **LOW** (informational headers, minor config improvements) — note and track

## Anti-Patterns

- **Don't skip the checklist** — even "obvious" code can hide subtle vulnerabilities. Systematic review catches what intuition misses.
- **Don't trust framework defaults** — frameworks provide tools, not guarantees. Verify that escaping, CSRF protection, and auth middleware are actually applied to every route.
- **Don't review in isolation** — a function may be safe alone but vulnerable when composed with others. Trace data flow from input to sink.
- **Don't assume dependencies are clean** — `npm audit` / `pip audit` on every review. A vulnerable transitive dependency is still your vulnerability.

## Agent & Infrastructure Surfaces

Security review is not limited to application code. ECC's AgentShield scanner also covers:

- **Agent prompts** — prompts that process untrusted content without input validation or output sanitization
- **MCP servers** — servers configured with shell access, filesystem access, remote transport, or unpinned `npx` that could execute attacker-controlled code
- **Plugin hooks** — executable hooks (file.edited, tool.execute.before/after) that could run malicious code when triggered
- **Permission surfaces** — overly broad tool permissions that bypass user approval gates

These surfaces are distinct from OWASP Top 10 and require their own review methodology. Run `npx ecc-agentshield scan` to audit them.

## Additional Scanning Tools

Complement manual review with these tools:

| Tool | Purpose | Command |
|------|---------|---------|
| `ecc-agentshield` | Agent/hook/MCP/permission surface scanning | `npx ecc-agentshield scan --path .` |
| `eslint-plugin-security` | Static analysis for JS/TS security patterns | Configure in ESLint config |
| `git-secrets` | Prevent committing secrets to git | `git secrets --scan` |
| `trufflehog` | Find secrets in git history and files | `trufflehog filesystem .` |
| `semgrep` | Pattern-based security scanning with rule packs | `semgrep --config=auto .` |

## CI Integration

For enforced security gates in CI:

```yaml
# GitHub Actions — AgentShield security gate
- uses: affaan-m/agentshield@v1
  with:
    path: "."
    min-severity: "medium"
    fail-on-findings: true
```

Block merges on CRITICAL and HIGH findings. Run `npm audit --audit-level=high` as a separate CI step for dependency vulnerabilities.

## References

- [`references/owasp-categories.md`](file:///home/opencode/.config/opencode/skills/security-review/references/owasp-categories.md) — Detailed per-category check tables, common vulnerabilities, and remediation examples for all 10 OWASP categories
- [`references/vulnerability-patterns.md`](file:///home/opencode/.config/opencode/skills/security-review/references/vulnerability-patterns.md) — Code-level vulnerability patterns with before/after fixes (secrets, SQL injection, XSS, race conditions)
- [`references/report-format.md`](file:///home/opencode/.config/opencode/skills/security-review/references/report-format.md) — Security review report template with checklist
