# RW-Health-Fixer

Dispatch RW-Health-Fixer for post-loop goal-aware cleanup — fixes lint, type, and test errors in the health restorer's repair allowlist. Can extend RW changes when they're incomplete against the goal. Escalates when a fix would contradict the goal. Dispatched by the health restorer manager, not directly.

## When to Dispatch

**Dispatch when:**
- The health restorer has categorized errors and needs fixes for a specific layer
- Errors are goal-consistent: mechanical fixes, or implementation changes that complete the goal's described behavior
- The fix scope is bounded by a specific error list with file:line:category and a repair allowlist

**Do NOT dispatch when:**
- You need per-round cleanup during the RW loop — use `rw-fixer` instead
- You need architectural fixes — use `exec-fixer` or `exec-planner` (AMEND) instead
- You need implementation changes — use `rw-worker` or `exec-worker` instead
- The errors are pre-existing (predate the RW transformation) — those are out of scope

## Dispatch Template

```
Fix the following errors in the RW transformation scope.

PRE_RW_SHA: <sha>
POST_RW_SHA: <sha>
GOAL_PATH: <path to RW goal file>
Error category: <implementation|test|configuration|assumption>
Repair scope: <path to repair-scope.txt allowlist>

Errors to fix (file:line: message):
- <error1>
- <error2>
- ...

Rules:
- Read the goal. Cross-reference every implementation fix against it.
- If a fix completes the goal's described behavior, apply it.
- If a fix would contradict the goal, escalate — do not apply.
- If a test asserts old behavior, update the test.
- If a type signature changed, propagate to callers.
- Only edit files in the repair-scope allowlist.
- Report what was fixed and what couldn't be fixed with reason.
```

## Required Fields

| Field | Description | Example |
|-------|-------------|---------|
| `PRE_RW_SHA` | Git commit hash before the RW loop started | `abc123def456` |
| `POST_RW_SHA` | Git commit hash after all RW rounds completed | `789ghi012jkl` |
| `GOAL_PATH` | Path to the RW goal file | `.rw/1720000000/goal.md` |
| `Error category` | Layer classification: implementation, test, configuration, or assumption | `test` |
| `Errors to fix` | Specific error list with file:line:message | `src/theme.test.ts:42: Expected dark but got light` |
| `Repair scope` | Path to the health restorer's allowlist file | `.rw/<run-id>/health/repair-scope.txt` |

## Expected Output

- List of errors fixed with file:line and what was changed
- Before/after error counts for the assigned category
- List of unfixable errors with reason
- Verification evidence: lint/typecheck/test output confirming fixes

## Key Constraints

- **Goal-consistent fixes.** Implementation fixes that complete the goal's described behavior are valid. Fixes that contradict the goal must be escalated. Cross-reference every implementation fix against the goal.
- **Never revert RW changes.** If RW changed behavior, update callers and tests — don't change the behavior back.
- **Stay in the allowlist.** Only edit files in the health restorer's repair-scope.txt allowlist. If a fix requires a file not on the list, report it — don't expand scope.
- **Report unfixable items.** If an error requires a design decision, new behavior beyond the goal, or changes outside the allowlist, document it.
- **No git operations.** The director handles all commits.
- **One-shot.** Fix the assigned errors and return. The health restorer handles iteration.
