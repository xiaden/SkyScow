# Security Review Report Format

Use this template when producing a security review report.

```markdown
# Security Review Report

**File/Component:** [path/to/file.ts]
**Reviewed:** YYYY-MM-DD

## Summary

- **Critical Issues:** X
- **High Issues:** Y
- **Medium Issues:** Z
- **Low Issues:** W
- **Risk Level:** HIGH / MEDIUM / LOW

## Critical Issues (Fix Immediately)

### 1. [Issue Title]
**Severity:** CRITICAL
**Category:** SQL Injection / XSS / Authentication / etc.
**Location:** `file.ts:123`

**Issue:**
[Description of the vulnerability]

**Impact:**
[What could happen if exploited]

**Remediation:**
[Secure implementation example]

---

## Security Checklist

- [ ] No hardcoded secrets
- [ ] All inputs validated
- [ ] SQL injection prevention
- [ ] XSS prevention
- [ ] CSRF protection
- [ ] Authentication required
- [ ] Authorization verified
- [ ] Rate limiting enabled
- [ ] HTTPS enforced
- [ ] Security headers set
- [ ] Dependencies up to date
- [ ] No vulnerable packages
- [ ] Logging sanitized
- [ ] Error messages safe
```
