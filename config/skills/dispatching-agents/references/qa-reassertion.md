# QA Reassertion

Push back when Exec-Manager reports completion without running QA review.

## When to Use

- Exec-Manager reports `status: DONE` but the report is missing `qaReview` section
- Exec-Manager reports DONE but a required analyzer report is missing — the test/documentation analyzer report is required only when the canonical tests/docs triggers hold per `/home/opencode/.config/opencode/instructions/qa-applicability.md`; otherwise an explicitly recorded evidence-based `NOT_APPLICABLE` is required
- Exec-Manager attempts to skip QA review entirely
- Exec-Manager accepts DONE while a surviving generator-owned candidate has neither specialized Generator terminal evidence nor a validated current reconciliation (including a `MINOR_PASS` used as a no-generator bypass)
- Exec-Manager accepts a docs-only path that skipped required Generator adjudication, or a missing, stale, malformed, duplicate, cross-family, or writer-mismatched terminal record, or a fixer claim beyond the repairs actually performed

## Do NOT Use

- For general QA issues or review feedback — that's QA-Reviewer's domain
- For fixing bugs found by QA — use the normal fix cycle
- When QA ran but you disagree with the results — that's a different workflow

## Evidence Enforcement Rejections

Reassert until every one of these is satisfied. Reject a manager report that:

- is missing a required analyzer, or has an unresolved generator-owned candidate (a surviving minor or major candidate without specialized Generator terminal evidence or a validated current reconciliation);
- accepts a stale or mismatched reconciliation (history that does not revalidate the current subject and its reason/evidence, or that predates the current mutation);
- lacks a terminal record for a generator-owned candidate, or accepts a Generator `UNNECESSARY` without repository-derived reason/evidence;
- accepts a no-change outcome without repository-derived evidence;
- accepts a `REPAIRED` terminal decision without actual verification;
- accepts a malformed subject identity (no stable subject: kind plus at least one identifying descriptor);
- accepts pre-mutation evidence, or asserts a generator/fixer record that was not written before return;
- accepts fixer claims beyond the repairs the fixer actually performed.

A valid specialized Generator `UNNECESSARY` must be accepted without override, and `BLOCKED`/`ESCALATED` ownership must be preserved; a stale `REPAIRED` is reopened after fresh analysis. No current history suppresses fresh discovery.

## Reassertion Template

Send this back to Exec-Manager:

```
QA review is mandatory. Re-run with QA-Reviewer before reporting DONE.

Your report MUST include:
- QA-Reviewer verdict and all checks (lint, layers, contracts, quality, completeness)
- Every surviving generator-owned candidate resolved by specialized Generator terminal evidence or a validated current reconciliation; record-before-return terminal records with task family, positive round, writer/agent, stable subject identity, decision, reason/evidence, changed files/symbols, actual verification, `repair` for Exec-Fixer records, and provenance
- QA-TestAnalyzer status and report when the canonical tests triggers hold per `/home/opencode/.config/opencode/instructions/qa-applicability.md`; otherwise an explicitly recorded evidence-based `NOT_APPLICABLE`
- QA-DocsAnalyzer status and report when the canonical documentation triggers hold per that reference; otherwise an explicitly recorded evidence-based `NOT_APPLICABLE`
```

## Required Checks

Exec-Manager's report must include all of these before accepting DONE (the analyzer items are applicability-conditional; the QA-Reviewer verdict and the core checks are mandatory):

- [ ] `checks.lint: PASS`
- [ ] `checks.layerCompliance: PASS`
- [ ] `checks.contracts: PASS`
- [ ] `checks.codeQuality: PASS`
- [ ] `checks.completeness: PASS`
- [ ] `checks.testCoverage` resolves to `PASS`, `FAIL`, or an evidence-based `NOT_APPLICABLE` per `/home/opencode/.config/opencode/instructions/qa-applicability.md`, and `testAnalyzerReport` is present with generator-dispatch evidence only for a dispatch-tier result (`MINOR_DISPATCH` or `MAJOR_DISPATCH`) whenever the canonical tests triggers hold; a `PASS` or `MINOR_PASS` analyzer run with no generator, and a correct escalation with no generator, are not missing checks
- [ ] `checks.documentation` resolves to `PASS`, `FAIL`, or an evidence-based `NOT_APPLICABLE` per that reference, and `docsAnalyzerReport` is present with generator-dispatch evidence only for a dispatch-tier result whenever the canonical documentation triggers hold; a `PASS` or `MINOR_PASS` analyzer run with no generator, and a correct escalation with no generator, are not missing checks

If any mandatory check is missing (not failed — **missing**), or an applicability-conditional analyzer check is absent without an evidence-based `NOT_APPLICABLE`, the review is incomplete. A dispatch-tier analyzer result without generator evidence is incomplete. A `PASS`/`MINOR_PASS` analyzer run with no generator, and a correct analyzer escalation with no generator, are not missing checks. An unresolved generator-owned candidate, a stale or mismatched reconciliation, a missing or malformed terminal record, pre-mutation evidence, or a fixer claim beyond performed repairs also makes the review incomplete. Re-dispatch Exec-Manager with the reassertion message. Exec-Manager must then spawn QA-Reviewer and wait for a complete review before reporting DONE again.

## Spec-First Tests

When spec-first tests are involved, QA review must handle partial results carefully. Spec-first tests are expected to **fail** until the full design document is implemented.

A reassertion in this context should verify that:
1. QA-Reviewer **ran** (not skipped)
2. QA-Reviewer **classified failures correctly** — distinguishing intentional "not yet implemented" failures from actual regressions

**What NOT to do:**
- Do not demand that every spec test passes prematurely
- Do not accept a DONE report that skipped QA entirely because "spec tests are expected to fail"

### Correct reassertion message (spec-first variant)

```
QA review is mandatory even with spec-first tests. Re-run with QA-Reviewer before reporting DONE.

QA-Reviewer must classify test failures:
- Spec-first failures (expected — not yet implemented) → note in report
- Actual failures (regressions, bugs) → must be fixed before DONE

Your report MUST include:
- QA-Reviewer verdict with failure classification
- QA-TestAnalyzer status and report when the canonical tests triggers hold per `/home/opencode/.config/opencode/instructions/qa-applicability.md`; otherwise an explicitly recorded evidence-based `NOT_APPLICABLE`
- QA-DocsAnalyzer status and report when the canonical documentation triggers hold per that reference; otherwise an explicitly recorded evidence-based `NOT_APPLICABLE`
```
