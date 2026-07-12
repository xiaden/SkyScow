# QA Reassertion

Push back when Exec-Manager reports completion without running QA review.

## When to Use

- Exec-Manager reports `status: DONE` but the report is missing `qaReview` section
- Exec-Manager reports DONE but `testAnalyzerReport` or `docsAnalyzerReport` is missing
- Exec-Manager attempts to skip QA review entirely

## Do NOT Use

- For general QA issues or review feedback — that's QA-Reviewer's domain
- For fixing bugs found by QA — use the normal fix cycle
- When QA ran but you disagree with the results — that's a different workflow

## Reassertion Template

Send this back to Exec-Manager:

```
QA review is mandatory. Re-run with QA-Reviewer before reporting DONE.

Your report MUST include:
- QA-Reviewer verdict and all checks (lint, layers, contracts, quality, completeness)
- QA-TestAnalyzer status and report
- QA-DocsAnalyzer status and report
```

## Required Checks

Exec-Manager's report must include ALL of these before accepting DONE:

- [ ] `checks.lint: PASS`
- [ ] `checks.layerCompliance: PASS`
- [ ] `checks.contracts: PASS`
- [ ] `checks.codeQuality: PASS`
- [ ] `checks.completeness: PASS`
- [ ] `checks.testCoverage: PASS` — confirms QA-TestAnalyzer ran
- [ ] `checks.documentation: PASS` — confirms QA-DocsAnalyzer ran
- [ ] `testAnalyzerReport` present in output
- [ ] `docsAnalyzerReport` present in output

If ANY check is missing (not failed — **missing**), the review is incomplete. Re-dispatch Exec-Manager with the reassertion message. Exec-Manager must then spawn QA-Reviewer and wait for a complete review before reporting DONE again.

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
- QA-TestAnalyzer status and report
- QA-DocsAnalyzer status and report
```
