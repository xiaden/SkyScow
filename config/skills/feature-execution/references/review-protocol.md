# Graph Review Protocol

QA reviews the implemented graph after all required nodes are accepted. Early review may provide feedback but is not terminal acceptance.

## Review input

```yaml
graph_id: "{graph-id}"
graph_revision: 3
graph_digest: "..."
subject_node_ids: ["I001", "I002"]
request_or_dd: "..."
requirements: []
contracts: []
changed_files: []
provenance: []
```

The review package is ephemeral. `GRAPH.json` remains the authority for obligations, ownership, dependencies, claims, evidence, and actual contracts. Do not create a plan, phase, packet artifact, or second contract authority.

## Review checks

- Verify the subject nodes’ accepted obligations, changed files, evidence, deviations, and actual contracts.
- Run repository-defined checks applicable to the changed surface when available; do not invent universal lint, test, build, security, or documentation gates.
- Classify findings as `NODE_DEFECT` (repairable implementation issue), `GRAPH_GAP` (missing obligation/edge/contract/owner), or `ARCHITECTURE_CONTRADICTION` (request/DD conflict), retaining every related node ID.
- A downstream-owned incomplete handoff is non-blocking only when the graph contains a present, non-superseded owner; otherwise report `GRAPH_GAP`.
- QA owns applicability and independent correctness. Exec-Manager consumes the verdict and does not reinterpret or replace it.

## Finding output

```yaml
status: PASS | MINOR | MAJOR | FAIL
findings:
  - classification: NODE_DEFECT | GRAPH_GAP | ARCHITECTURE_CONTRADICTION
    node_ids: ["I001"]
    severity: MINOR | MAJOR | BLOCKING
    detail: "..."
    route: EXEC_FIXER | EXEC_PLANNER | DD_OWNER | USER
verification:
  checks: []
  ownership: CURRENT_NODE | DOWNSTREAM_NODE | OWNERLESS
```

Any accepted repair or graph amendment invalidates terminal QA and requires a fresh review against the new revision.
