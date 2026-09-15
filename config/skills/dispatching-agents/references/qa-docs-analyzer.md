# QA-DocsAnalyzer

Dispatch QA-DocsAnalyzer to assess documentation coverage and accuracy for changed code.

WHEN documentation analysis applies and the observable trigger are owned by
`/home/opencode/.config/opencode/instructions/qa-applicability.md`; this reference
owns only HOW documentation analysis is performed.

## When to Dispatch

**Dispatch when:**
- QA-Reviewer delegates documentation analysis as part of the full review
- You need standalone documentation assessment for a module or feature
- After implementation to verify docs before review

**Do NOT dispatch when:**
- You need a full review — use `qa-reviewer` instead (it spawns this agent)
- You need docs generated — use `qa-docs-generator` instead (spawned by this agent)
- You need test analysis — use `qa-test-analyzer` instead

## Dispatch Template

```
Analyze documentation coverage and accuracy for changed files.

Context files to read:
- [PLAN_PATH]  — the plan that produced these changes
- [list changed files covered by the plan]
- [existing docs or READMEs for context]

scope: "[files/modules to analyze]"
plan: "[plan identifier]"
task_family: "[existing task family — passed to qa_record_read]"

Inspect the current repository and produce candidate findings FIRST, before reading any prior QA round
record. Each candidate needs an explicit gap kind, stable subject, severity/priority, stale flag, and
generator-vs-systemic ownership. Then reconcile each candidate against the durable round records via
qa_record_read. Every surviving generator-owned candidate — minor or major — MUST reach
qa-docs-generator exactly once, then be re-verified; no candidate is dismissed as too minor. Only
validated current reconciliation may close a candidate without generation. A required public/operator
documentation gap can never be waived. A dispatch-tier result is incomplete until the generator has run.
```

## Required Fields

| Field | Description | Example |
|-------|-------------|---------|
| `scope` | Files/modules to analyze | `src/api/routes/, docs/api/` |
| `plan` | Plan identifier for context | `TASK-api-A-endpoints` |
| `task_family` | Existing task family for durable-record reconciliation | `TASK-api-A-endpoints` |

## Expected Output

| Tier | Meaning | Action |
|------|---------|--------|
| `PASS` | No candidate gap at all | No action needed |
| `MINOR_PASS` | Every produced candidate was closed by validated current reconciliation | No new generation; report reconciliation basis |
| `MINOR_DISPATCH` | Surviving generator-owned candidates | Spawn QA-DocsGenerator with candidate list |
| `MAJOR_DISPATCH` | Significant surviving generator-owned candidates | Spawn QA-DocsGenerator with prioritized candidates |
| `MAJOR_RAISE` | Systemic documentation problem | Escalate to the owning path |

Output includes:
- The full candidate set (gap kind, stable subject, severity/priority, stale flag, ownership)
- The reconciliation outcome per candidate (suppressed / reopened / new, with basis)
- Coverage assessment per file/module
- Missing docstrings (specific functions/classes)
- Stale docs (docs for removed/renamed APIs)
- Doc/code drift (docs say one thing, code does another)

## Fresh-Before-History Ordering (hard invariant)

Fresh current-state inspection and candidate production MUST precede any read of prior QA round records.
Prior records are reconciliation evidence, never an analysis exclusion list. A dispatch prompt that asks
the analyzer to "check history first" contradicts this contract.

## Reconciliation Rules

Prior `UNNECESSARY` suppresses a repeat only after the current subject and its reason/evidence are
revalidated against current state; a material subject/behavior change invalidates it and reopens the
candidate, and a still-required public/operator documentation gap can never be suppressed. Prior
`REPAIRED` is rechecked and can reopen. Prior `BLOCKED`/`ESCALATED` preserves ownership unless material
conditions changed. No matching record means the candidate is new. History that was never produced by an
analyzer is never persisted or used to suppress discovery. Missing history is empty; malformed,
cross-family, or writer-mismatched history fails closed.

## Routing by Tier

| Tier | Action |
|------|--------|
| `PASS` | Return to caller — no candidate gaps |
| `MINOR_PASS` | Return to caller — all candidates closed by validated current reconciliation; no new generation |
| `MINOR_DISPATCH` or `MAJOR_DISPATCH` | Spawn `qa-docs-generator` exactly once with the surviving candidate list |
| `MAJOR_RAISE` | Escalate — systemic documentation problem requires the owning path |
