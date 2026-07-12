# Exec-Fixer

Dispatch Exec-Fixer to perform targeted repairs for review issues.

## When to Dispatch

**Dispatch when:**
- QA-Reviewer has flagged MINOR severity issues with specific file paths and line numbers
- Exec-Manager delegates fix work after QA review
- You have a concrete, scoped issue list that needs mechanical fixes

**Do NOT dispatch when:**
- Issues require architectural changes — use `exec-planner` (AMEND) instead
- The issue list includes PLANNING_GAP issues — Exec-Fixer cannot handle these
- Fixes are trivial (typos, missing imports) — fix them yourself
- You're executing an implementation plan — use `exec-manager` instead

## Dispatch Template

```
Fix the following review issues:

Context files to read:
- [list every file mentioned in the issues]

issues:
  - file: "[path]"
    line: [line number]
    severity: MINOR
    description: "[what's wrong]"
    suggestion: "[suggested fix]"
  # ... repeat for each issue

Fix each issue, run lint, report completion. Do NOT handle PLANNING_GAP issues — escalate those.
```

## Required Fields

| Field | Description | Example |
|-------|-------------|---------|
| `issues` | List of MINOR issues with file, line, severity, description, suggestion | See template |
| `file` | Path to the affected file | `src/auth/service.ts` |
| `line` | Line number (or range) of the issue | `45` or `45-52` |
| `description` | What's wrong | "Missing null check on user object before accessing user.id" |
| `suggestion` | Suggested fix | "Add `if (!user) throw new AuthError(...)` before line 45" |

## Expected Output

- Fixed files with lint passing (zero new errors)
- Report of what was fixed (per-issue)
- Any issues that couldn't be fixed with reason

This agent is **leaf** — it does not spawn children. It handles MINOR issues only. PLANNING_GAP or MAJOR issues must be escalated, not fixed here.

## Routing After Fix

| Outcome | Action |
|---------|--------|
| All issues fixed, lint clean | Re-run QA-Reviewer |
| Some issues couldn't be fixed | Escalate with reason |
| Fix introduces new issues | Re-run QA-Reviewer (not another fix cycle) |
