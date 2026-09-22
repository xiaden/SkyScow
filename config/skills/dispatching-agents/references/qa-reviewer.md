# QA-Reviewer

Dispatch QA-Reviewer as the normal graph-QA composer after required graph nodes are implemented and before terminal acceptance.

## Dispatch boundary

Dispatch with:

- `graph_id`, graph revision/state digest, and `GRAPH.json` path;
- subject node IDs and any related node IDs;
- changed files and provenance;
- request or accepted DD;
- graph requirements, contracts, acceptance, and ownership context;
- mode: `GRAPH_WORKSPACE` or `IMMUTABLE_CANDIDATE`.

Publication QA remains owned by `qa-push-manager` and `qa-repo-review-manager`; do not route publication candidates through this normal graph-QA contract.

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

Every finding retains all related node IDs and uses one classification:

- `NODE_DEFECT` — subject-node implementation/evidence defect;
- `GRAPH_GAP` — missing requirement, owner, dependency, contract, or graph obligation;
- `ARCHITECTURE_CONTRADICTION` — conflict with accepted request/DD authority.

Downstream ownership is valid only for an explicit present, non-superseded graph node. Historical plans, likely future work, annotations, and README text are not ownership evidence.

## Immutable candidate mode

`IMMUTABLE_CANDIDATE` reviews a supplied candidate snapshot without mutating it. `GRAPH_WORKSPACE` reviews the current graph workspace after generation and stabilization. Both modes are read-only for QA-Reviewer and specialist reviewers; repairs route separately to Exec-Fixer or Exec-Planner.

## Required output

```yaml
qaReview:
  status: PASS | MINOR | MAJOR | FAIL
  graph_id: "..."
  graph_revision: 0
  subjectNodeIds: []
  mode: GRAPH_WORKSPACE | IMMUTABLE_CANDIDATE
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
    - classification: NODE_DEFECT | GRAPH_GAP | ARCHITECTURE_CONTRADICTION
      relatedNodeIds: []
      files: []
      description: "..."
      blocksTerminalPass: true
```

Normal graph QA is mandatory before Exec-Manager reports terminal acceptance. QA-PushManager and QA-RepoReviewManager retain their existing publication behavior.
