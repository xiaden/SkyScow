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

task_family: "[existing task family]"
round: [positive review round]

Context files to read:
- [list every file mentioned in the issues]

issues:
  - file: "[path]"
    line: [line number]
    severity: MINOR
    description: "[what's wrong]"
    suggestion: "[suggested fix]"
  # ... repeat for each issue

Fix each issue, run lint, write the durable Plan A terminal repair record, report completion. Do NOT handle PLANNING_GAP issues — escalate those.
```

## Required Fields

| Field | Description | Example |
|-------|-------------|---------|
| `issues` | List of MINOR issues with file, line, severity, description, suggestion | See template |
| `task_family` | Existing task family for the durable terminal repair record | `TASK-auth-A-login` |
| `round` | Positive review round for the durable terminal repair record | `1` |
| `file` | Path to the affected file | `src/auth/service.ts` |
| `line` | Line number (or range) of the issue | `45` or `45-52` |
| `description` | What's wrong | "Missing null check on user object before accessing user.id" |
| `suggestion` | Suggested fix | "Add `if (!user) throw new AuthError(...)` before line 45" |

## Expected Output

- Fixed files with lint passing (zero new errors)
- Report of what was fixed (per-issue)
- The durable Plan A terminal repair record path (`artifacts/logs/qa-rounds/{task_family}/round-{N}/exec-fixer.jsonl`), written via `qa_record_write` before return
- Any issues that couldn't be fixed with reason (only unfixable listed issues)

This agent is **leaf** — it does not spawn children. It handles MINOR issues only. PLANNING_GAP or MAJOR issues must be escalated, not fixed here.

## Terminal Repair Record

Every performed repair writes exactly one durable Plan A terminal repair record via `qa_record_write` **before return** — one record per stable finding subject. A failed or missing write is a failed invocation. The record uses `writer`/`agent` set to `exec-fixer`, the supplied `task_family` and positive `round`, a stable `subject` (kind plus at least one identifying key), `decision: REPAIRED`, repository-derived `evidence`, the actual `verification`, `changed_files`/`changed_symbols` with non-empty entries (a `REPAIRED` record needs at least one changed file or symbol), `repair`, and `source_kind: fixer-issue` with `source_ref` naming the listed issue. A `BLOCKED` return lists only the unfixable listed issues and reasons; no `REPAIRED` record is fabricated for an unperformed repair. The fixer does not discover gaps, decide `UNNECESSARY`, adjudicate severity, suppress history, fabricate records, or act as a Test/Docs adjudicator.

## Routing After Fix

| Outcome | Action |
|---------|--------|
| All issues fixed, lint clean | Re-run QA-Reviewer |
| Some issues couldn't be fixed | Escalate with reason |
| Fix introduces new issues | Re-run QA-Reviewer (not another fix cycle) |
