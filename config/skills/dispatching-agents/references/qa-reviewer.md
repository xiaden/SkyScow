# QA-Reviewer

Dispatch QA-Reviewer as the quality gate after implementation completes.

## When to Dispatch

**Dispatch when:**
- Exec-Manager completes all implementation phases and needs a quality gate before reporting DONE
- You need a full, one-pass review of changed code
- After Exec-Fixer completes repairs on QA-flagged issues

**Do NOT dispatch when:**
- Implementation is still in progress — QA runs after ALL phases, not partial
- You need targeted fixes — use `exec-fixer` instead
- You need test coverage analysis only — use `qa-test-analyzer` instead
- You need documentation analysis only — use `qa-docs-analyzer` instead

## Dispatch Template

```
Review the implementation for plan [PLAN_PATH].

Context files to read:
- [PLAN_PATH] — the plan
- [DESIGN_DOC_PATH] — design document, if applicable
- [CONTRACTS_PATH] — contracts ledger, if applicable
- [AUTHORITATIVE_REQUEST] — verbatim original user request and requirement ledger
- The validated ordered plan set and dependency/ownership context for the current plan

task:
  plan: "[plan identifier]"
  currentPlan: "[plan identifier]"
  orderedPlanSet: "[present, schema-valid, dependency-ordered, non-superseded plan set]"
  designDoc: "[design doc path or N/A]"
  contractsPath: "[contracts path or N/A]"
  changedFiles: ["..."]
```

## Analyzer boundary

QA-Reviewer reviews the actual subject changed by the plan. It dispatches QA-TestAnalyzer and/or
QA-DocsAnalyzer only when the canonical applicability classification requires them. Those analyzers
inspect only their own domains, may dispatch their permitted generators, and return exactly
`PASS`, `GENERATED`, or `FAIL`.

QA-Reviewer waits for applicable analyzer results before running affected tests/checks, so generated
changes are included. It does not independently re-verify generator work. A missing analyzer, unrecognized
status, `GENERATED` without changed files, or `FAIL` without a reason is incomplete.

## Output

The review report includes the direct correctness review plus, when applicable, each analyzer's status,
summary, generator changed files, and failure reason. Analyzer gaps use only `description`, `files`, and
`reason`; no severity, plan ownership, durable record, or reconciliation fields are required.

- [ ] `checks.completeness` — all current-plan implementation steps and current-plan-owned responsibilities delivered; classify remaining implementation work by validated plan-set ownership
- [ ] Applicable analyzer reports are present and structurally complete, including generator outcome and changed files when a repair is claimed

QA must not report a plan incomplete solely because the plan omitted a test or documentation step. Those
outputs are derived from the implemented surface and are owned by the applicable analyzer/generator unless
explicitly required by the user request or accepted architecture.

`checks.testCoverage` and `checks.documentation` are applicability-conditional; all other checks must run.

### Output Structure

```
qaReview:
  status: PASS | MINOR | MAJOR | FAIL
  checks:
    lint: PASS | FAIL
    layerCompliance: PASS | FAIL
    contracts: PASS | FAIL
    codeQuality: PASS | FAIL
    completeness: PASS | FAIL
  testCoverage: PASS | FAIL | NOT_APPLICABLE
  documentation: PASS | FAIL | NOT_APPLICABLE
  requirementConformance: PASS | FAIL
    issues: [list of issues with file, line, severity, description, ownership, downstreamPlan when applicable, blocksCurrentPlan; ownership is CURRENT_PLAN | DOWNSTREAM_PLAN | PLANNING_GAP]
  testAnalyzerReport: { ... }
  docsAnalyzerReport: { ... }
```

## QA Gate Enforcement

The QA gate is **mandatory**. Exec-Manager must not report DONE without `qaReview.status: PASS`. The `qa-reassertion` reference covers pushback when this gate is skipped.

## Incomplete Work Handling

Test or documentation status does not create an exception to ownership classification. A spec-first or otherwise incomplete finding is `CURRENT_PLAN` when owned here, `DOWNSTREAM_PLAN` only with a validated later owner in the supplied plan set, and `PLANNING_GAP` otherwise. The latter two classifications retain their defined carry-forward or blocking behavior; no annotation-only or likely-future ownership is accepted.
