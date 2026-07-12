# QA-TestAnalyzer

Dispatch QA-TestAnalyzer to assess test coverage and quality for changed code.

## When to Dispatch

**Dispatch when:**
- QA-Reviewer delegates test analysis as part of the full review
- You need standalone test coverage assessment for a module or feature
- After implementation to verify test quality before code review

**Do NOT dispatch when:**
- You need a full review — use `qa-reviewer` instead (it spawns this agent)
- You need tests generated — use `qa-test-generator` instead (spawned by this agent)
- You need documentation analysis — use `qa-docs-analyzer` instead
- The changed code is trivial (one-line fix, config change)

## Dispatch Template

```
Analyze test coverage and quality for changed files.

Context files to read:
- [PLAN_PATH]  — the plan that produced these changes
- [list changed files covered by the plan]

scope: "[files/modules to analyze]"
plan: "[plan identifier]"

Identify missing tests, stale tests, and coverage gaps. Route by tier.
```

## Required Fields

| Field | Description | Example |
|-------|-------------|---------|
| `scope` | Files/modules to analyze | `src/auth/, src/auth/__tests__/` |
| `plan` | Plan identifier for context | `TASK-auth-A-login` |

## Expected Output

| Tier | Meaning | Action |
|------|---------|--------|
| `PASS` | Test coverage adequate, all tests meaningful | No action needed |
| `MINOR_PASS` | Minor gaps, logged but not blocking | Log findings, no dispatch |
| `MINOR_DISPATCH` | Gaps need test generation | Spawn QA-TestGenerator with gap list |
| `MAJOR_DISPATCH` | Significant gaps, multiple files missing tests | Spawn QA-TestGenerator with prioritized gaps |
| `MAJOR_RAISE` | Critical gaps — core paths untested | Escalate to caller |

Output includes:
- Coverage assessment per file
- Identified gaps (missing tests for specific functions/paths)
- Stale tests (tests for removed functionality)
- Quality assessment (are existing tests meaningful?)

## Routing by Tier

| Tier | Action |
|------|--------|
| `PASS` or `MINOR_PASS` | Return to caller — no test generation needed |
| `MINOR_DISPATCH` or `MAJOR_DISPATCH` | Spawn `qa-test-generator` with gap list |
| `MAJOR_RAISE` | Escalate — critical gaps require caller intervention |
