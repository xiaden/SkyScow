# QA Reassertion

Push back when a publication candidate reaches the publication gate without running QA review.

## When to Use

- A candidate is presented for publication without a `qaReview` report
- A publication path attempts to skip QA review entirely
- A candidate is accepted without a complete QA-Reviewer report or final `PASS` verdict

## Do NOT Use

- For general QA issues or review feedback — that's QA-Reviewer's domain
- For fixing bugs found by QA — use the normal fix cycle
- When QA ran but you disagree with the results — that's a different workflow

## Evidence Enforcement Rejections

Reassert until QA is complete before publication. Reject a report that:

- is missing the QA-Reviewer report or final verdict;
- omits required core QA checks or contains malformed QA output;
- claims publication readiness while QA-Reviewer reports unresolved `WORK_DEFECT`, `COVERAGE_GAP`, or `ARCHITECTURE_CONTRADICTION` blocking findings;
- accepts repair claims beyond the repairs actually performed.

QA-Reviewer results are consumed as a whole and are not reconstructed or reinterpreted internally. QA is independent of Change DAG execution and archival; `dag_archive` does not depend on QA. QA is enforced separately at the publication gate.

## Reassertion Template

Send this back to the publication path (`qa-push-manager`) before publishing:

QA review is mandatory before publication. Run QA-Reviewer before publishing.

Your report MUST include:
- QA-Reviewer verdict and all applicable checks (deterministic checks, contracts, completeness, and applicable test/documentation evidence)
- the complete QA-Reviewer findings and classification
- no unresolved work defects or unowned coverage gaps

## Required Checks

The publication report must include all of these before publishing:

- [ ] `checks.deterministic: PASS` (applicable changed-surface evidence)
- [ ] `checks.contracts: PASS`
- [ ] `checks.completeness: PASS` (executed Change DAG obligations)
- [ ] `checks.testCoverage: PASS` or evidence-based `NOT_APPLICABLE`
- [ ] `checks.documentation: PASS` or evidence-based `NOT_APPLICABLE`

If any mandatory check is missing, malformed, or not `PASS`, re-dispatch QA-Reviewer and wait for a complete report before publishing again.

A reassertion in this context should verify that:
1. QA-Reviewer **ran** (not skipped)
2. QA-Reviewer **classified failures correctly** — distinguishing intentional "not yet implemented" failures from actual regressions

**What NOT to do:**
- Do not demand that every spec test passes prematurely
- Do not accept a publication report that skipped QA entirely because "spec tests are expected to fail"

### Correct reassertion message (spec-first variant)

```
QA review is mandatory even with spec-first tests. Run QA-Reviewer before publishing.

QA-Reviewer must classify test failures:
- Spec-first failures (expected — not yet implemented) → note in report
- Actual failures (regressions, bugs) → must be fixed before publication

Your report MUST include:
- QA-Reviewer verdict with failure classification
- the complete QA-Reviewer checks and findings
- no unresolved work defects or unowned coverage gaps
```
