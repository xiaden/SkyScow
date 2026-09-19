# QA-TestAnalyzer

Dispatch QA-TestAnalyzer to assess test coverage and quality for changed code.

WHEN test analysis applies and the observable trigger are owned by
`/home/opencode/.config/opencode/instructions/qa-applicability.md`; this reference
owns only HOW test analysis is performed.

## When to Dispatch

**Dispatch when:**
- QA-Reviewer delegates test analysis as part of the full review
- You need standalone test coverage assessment for a module or feature
- After implementation to verify test quality before code review

**Do NOT dispatch when:**
- You need a full review — use `qa-reviewer` instead (it spawns this agent)
- You need tests generated — use `qa-test-generator` instead (spawned by this agent)
- You need documentation analysis — use `qa-docs-analyzer` instead

## Dispatch Template

```
Analyze test coverage and quality for the changed files.

Context files to read:
- [PLAN_PATH]
- [list changed files covered by the plan]

scope: "[files/modules to analyze]"
plan: "[plan identifier]"
changedFiles: ["..."]

Inspect the current surface and report concrete test gaps. If a repairable gap exists, dispatch
`qa-test-generator` once with only its `description`, `files`, and `reason`. The Generator owns test edits
and verification. Return exactly `PASS`, `GENERATED`, or `FAIL`; `GENERATED` requires changed files, and
`FAIL` requires a concise reason. Do not re-run tests, inspect durable Generator records, or reconstruct
Generator history.

## Required Fields

| Field | Description | Example |
|-------|-------------|---------|
| `scope` | Files/modules to analyze | `src/auth/, src/auth/__tests__/` |
| `plan` | Plan identifier for context | `TASK-auth-A-login` |
| `changedFiles` | Changed surface | `["src/auth/service.py"]` |

## Expected Output

DD lifecycle inputs use only `Draft`, `Approved`, `Completed`, `Superseded`, or `Rejected`; an `Approved` pending prerequisite is valid only with disposition, responsible owner, and transition condition.

| Status | Meaning | Action |
|--------|---------|--------|
| `PASS` | No actionable test gap; no generator needed | Return to caller |
| `GENERATED` | Generator successfully repaired a concrete gap | Return changed files |
| `FAIL` | Analysis or generation could not complete successfully | Return reason/failure kind |

Each gap contains only `description`, `files`, and `reason`. `GENERATED` requires non-empty changed files;
`FAIL` requires a concise reason.
