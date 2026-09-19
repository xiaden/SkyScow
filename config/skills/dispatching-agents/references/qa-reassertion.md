# QA Reassertion

Push back when Exec-Manager reports completion without running QA review.

## When to Use

- Exec-Manager reports `status: DONE` but the report is missing `qaReview` section
- Exec-Manager attempts to skip QA review entirely
- Exec-Manager accepts DONE without a complete QA-Reviewer report or final `PASS` verdict
## Do NOT Use

- For general QA issues or review feedback — that's QA-Reviewer's domain
- For fixing bugs found by QA — use the normal fix cycle
- When QA ran but you disagree with the results — that's a different workflow

## Evidence Enforcement Rejections

Reassert until the QA gate is complete. Reject a manager report that:

- is missing the QA-Reviewer report or final verdict;
- omits required core QA checks or contains malformed QA output;
- claims completion while QA-Reviewer reports unresolved current-plan or unowned blocking findings;
- accepts fixer claims beyond the repairs the fixer actually performed.

Exec-Manager consumes the QA-Reviewer report as a whole and does not reconstruct or reinterpret internal QA details.
## Reassertion Template

Send this back to Exec-Manager:

QA review is mandatory. Re-run with QA-Reviewer before reporting DONE.

Your report MUST include:
- QA-Reviewer verdict and all required checks (lint, layers, contracts, quality, completeness)
- the complete QA-Reviewer findings and ownership classification
- no unresolved current-plan or unowned blocking findings

## Required Checks

Exec-Manager's report must include all of these before accepting DONE:

- [ ] `checks.lint: PASS`
- [ ] `checks.layerCompliance: PASS`
- [ ] `checks.contracts: PASS`
- [ ] `checks.codeQuality: PASS`
- [ ] `checks.completeness: PASS`

If any mandatory check is missing, malformed, or not `PASS`, re-dispatch QA-Reviewer. Exec-Manager must
wait for a complete QA-Reviewer report before reporting DONE again.
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
- the complete QA-Reviewer checks and findings
- no unresolved current-plan or unowned blocking findings
