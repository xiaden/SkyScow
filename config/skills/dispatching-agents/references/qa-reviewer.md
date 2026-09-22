# QA-Reviewer

Dispatch QA-Reviewer as the quality gate after implementation completes.

## When to Dispatch

**Dispatch when:**
- Exec-Manager accepts required graph nodes and needs a quality gate before terminal acceptance
- You need a full, one-pass review of changed code
- After Exec-Fixer completes repairs on QA-flagged issues

**Do NOT dispatch when:**
- Implementation is still in progress — QA runs before acceptance of the selected implementation/support graph, not as an implementation substitute
- You need targeted fixes — use `exec-fixer` instead
- You need test coverage analysis only — use `qa-test-analyzer` instead
- You need documentation analysis only — use `qa-docs-analyzer` instead

## Dispatch Template

```
Review graph [GRAPH_ID] at revision [GRAPH_REVISION] for subject nodes [NODE_IDS].

Context files to read:
- [GRAPH_PATH] — authoritative GRAPH.json
- [DESIGN_DOC_PATH] — accepted design document, if applicable
- [AUTHORITATIVE_REQUEST] — verbatim original user request and requirement ledger
- The validated graph dependency/ownership context and subject node evidence

task:
  graphId: "[graph identifier]"
  graphRevision: [graph revision]
  subjectNodeIds: ["I001"]
  graphPath: "[GRAPH.json path]"
  designDoc: "[design doc path or N/A]"
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

- [ ] `checks.completeness` — all subject node obligations and current-node responsibilities delivered; classify remaining work by graph ownership
- [ ] Applicable analyzer reports are present and structurally complete, including generator outcome and changed files when a repair is claimed

QA must not report a graph node incomplete solely because it omitted an inapplicable test or documentation obligation. Those
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
