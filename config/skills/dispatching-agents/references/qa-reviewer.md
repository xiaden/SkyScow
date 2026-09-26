# QA-Reviewer

Dispatch QA-Reviewer as the normal post-change QA composer after a Change DAG has been executed and before any publication.

## Dispatch boundary

Dispatch with:

- the Change DAG bundle under review (`artifacts/change-dags/{pending,completed}/{slug}/DAG.json`, `EXECUTION_STATE.json`, `WORK_LOG.jsonl`);
- changed files and provenance from the Work Log;
- the request or accepted DD;
- DAG semantic requirements, expected exact work, and ownership context;
- mode: `CHANGE_WORKSPACE` or `IMMUTABLE_CANDIDATE`.

QA is independent of DAG execution and archival: it is not stored in `EXECUTION_STATE`, is not a DAG phase, and is not a DAG archive gate. Publication QA remains owned by `qa-push-manager` and `qa-repo-review-manager`; do not route publication candidates through this normal post-change QA contract.

## Composition order

QA-Reviewer owns one normal composition pass:

1. evaluate applicability once using `config/instructions/qa-applicability.md`;
2. run deterministic changed-surface checks;
3. dispatch applicable `qa-test-analyzer` and/or `qa-docs-analyzer`;
4. wait for analyzer and permitted generator results;
5. stabilize the post-generation subject files and workspace fingerprint;
6. dispatch immutable-candidate, read-only specialist reviewers for every applicable lens:
   - `qa-reviewer-correctness`
   - `qa-reviewer-boundary`
   - `qa-reviewer-journey`
   - `qa-reviewer-domainrisk` (one assigned lens per invocation; canonical concurrency batching only);
7. synthesize findings and bind terminal PASS to the stabilized post-generation state.

The explicit task allow-list is limited to `qa-test-analyzer`, `qa-docs-analyzer`, `qa-reviewer-correctness`, `qa-reviewer-boundary`, `qa-reviewer-journey`, and `qa-reviewer-domainrisk`. No other QA or implementation agent is dispatched from this contract.

Analyzer results are exactly `PASS`, `GENERATED`, or `FAIL`. Missing applicable analyzers, failed analyzers, malformed generator results, or generated changes without changed files block terminal PASS. Generator mutation occurs before specialist fan-out and before final evidence/fingerprint capture.

## Applicability and findings

Applicability is never selected by tier, numeric risk, depth score, or subjective change size. Correctness is always required for meaningful implementation, runtime, configuration, or policy behavior. Boundary, journey, domain-risk, test, and documentation lenses run only when canonical observable triggers match. `NOT_APPLICABLE` requires evidence.

Every finding is classified as one of:

- `WORK_DEFECT` — executed work/evidence defect in the reviewed change;
- `COVERAGE_GAP` — missing requirement, dependency, or exact work not represented by the Change DAG;
- `ARCHITECTURE_CONTRADICTION` — conflict with accepted request/DD authority.

Downstream ownership is valid only for an explicit present, non-superseded Change DAG node or a named owner. Historical plans, likely future work, annotations, and README text are not ownership evidence.

## Immutable candidate mode

`IMMUTABLE_CANDIDATE` reviews a supplied candidate snapshot without mutating it. `CHANGE_WORKSPACE` reviews the current workspace after generation and stabilization. Both modes are read-only for QA-Reviewer and specialist reviewers. Small repairs are bounded raw edits; substantial defects start a new `{dd-slug}-fix-N` Change DAG. QA results are not written into `EXECUTION_STATE`.

## Required output

```yaml
qaReview:
  status: PASS | MINOR | MAJOR | FAIL
  slug: "..."
  subjectNodeIds: []
  mode: CHANGE_WORKSPACE | IMMUTABLE_CANDIDATE
  workspace_fingerprint: "..."
  checks:
    deterministic: PASS | FAIL
    contracts: PASS | FAIL
    completeness: PASS | FAIL
    testCoverage: PASS | FAIL | NOT_APPLICABLE
    documentation: PASS | FAIL | NOT_APPLICABLE
  analyzerEvidence: []
  specialistEvidence: []
  findings:
    - classification: WORK_DEFECT | COVERAGE_GAP | ARCHITECTURE_CONTRADICTION
      relatedNodeIds: []
      files: []
      description: "..."
      blocksTerminalPass: true
```

Normal post-change QA is independent of DAG execution and archival. Whether QA has run does not gate `dag_archive`; QA-before-publication is enforced separately by QA-PushManager. QA-PushManager and QA-RepoReviewManager retain their existing publication behavior.
