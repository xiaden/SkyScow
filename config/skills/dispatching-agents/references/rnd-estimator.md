# RnD-Estimator

Dispatch RnD-Estimator to size implementation effort.

## When to Dispatch

**Dispatch when:**
- You need effort sizing for a feature or plan before committing
- You're comparing implementation approaches and need relative effort
- You need to validate scope before planning
- You're evaluating a technology choice and need ballpark effort

**Do NOT dispatch when:**
- The scope is trivial (single-file change, typo fix)
- You need a full design document — use `rnd-manager` or `rnd-dd-author` instead
- You need implementation analysis — use `rnd-architect` instead
- You need creative ideation — use `rnd-ideator` instead

## Dispatch Template

```
Estimate effort for [WORK ITEM].

Context files to read:
- [design doc, plan, or requirements]
- [relevant code for context]

work item: "[description of what needs to be built]"
scope: "[files/modules/layers affected]"

Return effort estimate with file count breakdown. Read-only — estimation only.
```

## Required Fields

| Field | Description | Example |
|-------|-------------|---------|
| `[WORK ITEM]` | What needs to be sized | "Add OAuth2 authentication flow" |
| `work item` | Description of what needs to be built | "Add OAuth2 login, token refresh, and session management to the auth service." |
| `scope` | Files/modules/layers affected | "src/auth/service.ts, src/auth/middleware.ts, src/auth/types.ts, src/auth/__tests__/" |

## Expected Output

| Tier | Description |
|------|-------------|
| `TRIVIAL` | < 3 files, < 50 lines changed |
| `SMALL` | 3-5 files, < 200 lines changed |
| `MEDIUM` | 5-15 files, < 1000 lines changed |
| `LARGE` | 15-30 files, may span multiple layers |
| `EPIC` | 30+ files, multiple layers, likely multi-plan |

Output includes:
- Effort tier with rationale
- Estimated file count and line changes
- Key risk factors
- Confidence level

This agent is **read-only** — it returns estimates, does not execute or implement.
