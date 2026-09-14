# Security Checklist

## When This Applies

Applicability is determined by the canonical classification in
`/home/opencode/.config/opencode/instructions/qa-applicability.md`, using the security surfaces and
triggers owned by `/home/opencode/.config/opencode/skills/security-review/SKILL.md`. This checklist
does not define or repeat those triggers. When the security lens is matched, load the security-review
skill and use this document for review HOW, including the C01-C08 checks and the guidance below.

For changes not classified for the security lens, preserve existing security invariants under ordinary
correctness review; the full C01-C08 checklist is not required.

## C01-C08 Checks

| ID | Check | Violation Example | Correct Approach |
|----|-------|-------------------|------------------|
| C01 | No hardcoded secrets | `const key = "sk-proj-abc123"` | `const key = process.env.OPENAI_API_KEY` |
| C02 | All user inputs validated | `app.get('/u', (req) => db.find(req.query.id))` | Validate with schema (zod, joi, pydantic) before use |
| C03 | SQL injection prevention | `` db.query(`SELECT * FROM users WHERE id = ${id}`) `` | Use parameterized queries: `db.query('SELECT ... WHERE id = $1', [id])` |
| C04 | XSS prevention | `element.innerHTML = userInput` | Use text content, sanitization libraries, or framework auto-escaping |
| C05 | CSRF protection enabled | State-changing GET requests without tokens | Use CSRF tokens on all state-changing operations |
| C06 | Auth/authz verified | Endpoint accessible without authentication check | Verify identity (authn) AND permissions (authz) on every request |
| C07 | Rate limiting on endpoints | Unlimited requests to `/api/login` | Apply rate limits (e.g., 100 req/min per IP) |
| C08 | Error messages don't leak data | `throw new Error(\`DB error: ${sqlError.message}\`)` | Return generic messages; log details server-side only |

## Secret Management

Secrets must never appear in source code, config files committed to git, or log output.

**Correct pattern:**
```typescript
const apiKey = process.env.OPENAI_API_KEY
if (!apiKey) {
  throw new Error('OPENAI_API_KEY not configured — see .env.example')
}
```

**Violations:**
- Hardcoded string literals containing keys, tokens, or passwords
- Secrets in `.env` files that are not in `.gitignore`
- Secrets printed to console or included in error messages
- Secrets passed as URL query parameters

## Security Response Protocol

If a security issue is discovered during development or review:

1. **STOP** — do not commit the change
2. **Assess severity** — is data exposed? Is auth bypassed?
3. **Fix before continuing** — CRITICAL and HIGH issues block all other work
4. **Rotate exposed secrets** — any secret that appeared in code, logs, or version history must be rotated
5. **Scan for similar issues** — search the codebase for the same pattern

## Enforcement

These enforcement rules apply to changes that touch a security-sensitive surface (canonical owner:
`/home/opencode/.config/opencode/skills/security-review/SKILL.md`):

- **Pre-commit:** For a security-sensitive change, run a secrets scanner (e.g., `gitleaks`, `trufflehog`) before commit
- **CI gate:** Fail the build when a C01-C08 check is violated on a security-sensitive surface
- **PR review:** For a security-sensitive change, the reviewer explicitly confirms C01-C08 compliance before approving
- **Periodic audit:** Run a full security scan on the repository-defined schedule; treat findings as blocking issues
