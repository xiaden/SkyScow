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
Analyze test coverage and quality for changed files.

Context files to read:
- [PLAN_PATH]  — the plan that produced these changes
- [list changed files covered by the plan]

scope: "[files/modules to analyze]"
plan: "[plan identifier]"
task_family: "[existing task family — passed to qa_record_read]"

Inspect the current repository and produce candidate findings FIRST, before reading any prior QA round
record. Each candidate needs an explicit gap kind, stable subject, severity/priority, stale flag, and
generator-vs-implementation/systemic ownership. Then reconcile each candidate against the durable round
records via qa_record_read. Every surviving generator-owned candidate — minor or major — MUST reach
qa-test-generator exactly once, then be re-verified; no candidate is dismissed as too minor. Only
validated current reconciliation may close a candidate without generation. A dispatch-tier result is
incomplete until the generator has run.
```

## Required Fields

| Field | Description | Example |
|-------|-------------|---------|
| `scope` | Files/modules to analyze | `src/auth/, src/auth/__tests__/` |
| `plan` | Plan identifier for context | `TASK-auth-A-login` |
| `task_family` | Existing task family for durable-record reconciliation | `TASK-auth-A-login` |

## Expected Output

| Tier | Meaning | Action |
|------|---------|--------|
| `PASS` | No candidate gap at all | No action needed |
| `MINOR_PASS` | Every produced candidate was closed by validated current reconciliation | No new generation; report reconciliation basis |
| `MINOR_DISPATCH` | Surviving generator-owned candidates | Spawn QA-TestGenerator with candidate list |
| `MAJOR_DISPATCH` | Significant surviving generator-owned candidates | Spawn QA-TestGenerator with prioritized candidates |
| `MAJOR_RAISE` | Implementation/systemic defect | Escalate to the owning path |

Output includes:
- The full candidate set (gap kind, stable subject, severity/priority, stale flag, ownership)
- The reconciliation outcome per candidate (suppressed / reopened / new, with basis)
- Coverage assessment per file
- Identified gaps (missing tests for specific functions/paths)
- Stale tests (tests for removed functionality)

## Fresh-Before-History Ordering (hard invariant)

Fresh current-state inspection and candidate production MUST precede any read of prior QA round records.
Prior records are reconciliation evidence, never an analysis exclusion list. A dispatch prompt that asks
the analyzer to "check history first" contradicts this contract.

## Reconciliation Rules

Prior `UNNECESSARY` suppresses a repeat only after the current subject and its reason/evidence are
revalidated against current state; a material subject/behavior change invalidates it and reopens the
candidate. Prior `REPAIRED` is rechecked and can reopen. Prior `BLOCKED`/`ESCALATED` preserves ownership
unless material conditions changed. No matching record means the candidate is new. History that was
never produced by an analyzer is never persisted or used to suppress discovery. Missing history is
empty; malformed, cross-family, or writer-mismatched history fails closed.

## Routing by Tier

| Tier | Action |
|------|--------|
| `PASS` | Return to caller — no candidate gaps |
| `MINOR_PASS` | Return to caller — all candidates closed by validated current reconciliation; no new generation |
| `MINOR_DISPATCH` or `MAJOR_DISPATCH` | Spawn `qa-test-generator` exactly once with the surviving candidate list |
| `MAJOR_RAISE` | Escalate — implementation/systemic defect requires the owning path |
