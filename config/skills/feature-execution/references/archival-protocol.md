# Implementation Graph Archival Protocol

Graph-native work is archived through `impl_graph_archive` after all required non-superseded nodes are complete, no active claims or blocking gaps remain, and terminal QA PASS is current for the graph revision and workspace fingerprint. The tool moves `artifacts/implementation/pending/{graph_id}/GRAPH.json` to `artifacts/implementation/completed/{graph_id}/GRAPH.json` atomically at the artifact boundary.

## Graph Completion Record

`GRAPH.json` is the authoritative completion record for new work. It contains node evidence, changed files, actual contracts, provenance, graph revision, terminal QA evidence, graph digest, and workspace fingerprint. No worker or manager packet is persisted, and archival does not imply a commit, release, deployment, or global repository state beyond the recorded evidence.

## Graph Archive Gate

Before calling `impl_graph_archive`, Exec-Manager verifies:

1. Every required node is `COMPLETE` or explicitly `SUPERSEDED`.
2. No node retains an active claim.
3. No blocking gap remains.
4. `final_qa.status` is `PASS`.
5. The supplied graph revision and digest match the pending graph.
6. The supplied workspace fingerprint matches the workspace used for terminal QA.

The archive tool fails closed for stale revision, stale digest, stale workspace, incomplete nodes, active claims, missing QA, or a completed destination collision.

## Legacy Compatibility

Historical Markdown plans and DD bundles remain readable and may be archived by their existing `plan_archive` and `dd_archive` tools. They are not new-work authority and are not prerequisites for graph archival. Do not create a plan artifact merely to archive a graph.

## Auditability

Read a completed graph from `artifacts/implementation/completed/{graph_id}/GRAPH.json`. Use its `requirements`, `contracts`, `nodes`, per-node evidence, and `final_qa` fields to reconstruct ownership and outcome. Git commits and release operations remain orthogonal and are governed by their applicable Git/GitHub skills.
