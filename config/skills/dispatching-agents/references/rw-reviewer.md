# RW-Reviewer

Dispatch RW-Reviewer to validate the git diff for meaningful progress toward a goal.

## When to Dispatch

**Dispatch when:**
- RW-Director runs review after each implementation round
- You need a read-only validation of whether changes constitute meaningful progress

**Do NOT dispatch when:**
- You need a full QA review — use `qa-reviewer` instead
- You need code fixes — use `rw-fixer` or `exec-fixer` instead
- You need to plan next steps — use `rw-manager` or `exec-planner` instead

## Dispatch Template

```
Review the current diff for progress toward [GOAL].

Context files to read:
- [any files defining the goal or expected outcome]

goal: "[the original goal statement]"

Validate the git diff. Return CONTINUE or STOP with reason. Read-only — no implementation.
```

## Required Fields

| Field | Description | Example |
|-------|-------------|---------|
| `[GOAL]` | The original goal statement | "Add dark mode toggle to all components" |
| `goal` | The goal to validate against | "Implement dark mode: ThemeContext, CSS variables, toggle, apply to 15 components." |

## Expected Output

| Verdict | Meaning |
|---------|---------|
| `CONTINUE` | Meaningful progress made — more work remains. Continue to next round. |
| `STOP` | Goal achieved. No more work needed. |

Output includes:
- Verdict with clear rationale
- What was accomplished this round
- What remains (if CONTINUE)
- Any concerns about approach or quality

## Key Constraints

- **Read-only.** Does not modify code, does not spawn workers, does not plan next steps.
- **Goal-only validation.** Reviews progress against the stated GOAL, not against code quality standards (that's QA-Reviewer's domain).
- **Does not read .rw-plan.md.** RW-Reviewer validates the diff, not the plan.
