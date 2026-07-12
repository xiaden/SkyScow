# RW-Fixer

Dispatch RW-Fixer for post-worker cleanup — mechanical error fixes on the current round's diff.

## When to Dispatch

**Dispatch when:**
- After RW-Workers complete a round and the diff has mechanical errors (lint, formatting, type errors)
- You need a cleanup pass before RW-Reviewer validates progress

**Do NOT dispatch when:**
- You need architectural fixes — use `exec-fixer` or `exec-planner` (AMEND) instead
- You need implementation changes — use `rw-worker` or `exec-worker` instead
- The errors are from a previous round — RW-Fixer handles current round's diff only

## Dispatch Template

```
Clean up the current round's diff.

Context files to read:
- [files changed in the current round]

task:
  round: "[round identifier]"
  goal: "[original goal]"

Run lint and tests on the current round's diff. Fix mechanical errors only. Report what was fixed. No git operations. No implementation changes.
```

## Required Fields

| Field | Description | Example |
|-------|-------------|---------|
| `round` | Current round identifier | `round-3` |
| `goal` | Original goal for context | "Add dark mode toggle to all components" |

## Expected Output

- List of mechanical errors found and fixed
- Lint status (zero new errors)
- Test status
- Any errors that couldn't be fixed mechanically with reason

## Key Constraints

- **Mechanical fixes only.** Typos, missing imports, formatting, type errors. No logic changes, no refactoring, no implementation.
- **Current round only.** Only fixes errors introduced in the current round's diff.
- **No git operations.** Does not commit, rebase, or branch.
- **No implementation changes.** If a fix requires changing behavior, escalate — don't fix it here.
