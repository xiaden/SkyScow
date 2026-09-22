# Implementation Graph Archival Protocol

Graph-native work is archived through `impl_graph_archive` after all required non-superseded nodes are complete, no active claims or blocking gaps remain, and terminal QA PASS is current for the graph's state revision, canonical implementation-state digest, and content-aware workspace fingerprint. The tool atomically renames the complete pending graph artifact directory to `artifacts/implementation/completed/{graph_id}/`, preserving GRAPH.json and any graph-owned evidence.

## Graph Completion Record

`GRAPH.json` is the authoritative completion record for new work. It contains node evidence, changed files, actual contracts, provenance, structure/state revisions, terminal QA evidence, canonical implementation-state digest, and workspace fingerprint. No worker or manager packet is persisted, and archival does not imply a commit, release, deployment, or global repository state beyond the recorded evidence.

## Graph Archive Gate

Before calling `impl_graph_archive`, Exec-Manager verifies:

1. Every required node is `COMPLETE` or explicitly `SUPERSEDED`.
2. No node retains an active claim.
3. No blocking gap remains.
4. `final_qa.status` is `PASS`.
5. The archive operation recomputes the pending graph's state revision and canonical implementation-state digest.
6. The archive operation recomputes the content-aware workspace fingerprint and compares it with terminal QA.

The archive tool fails closed for stale revision, stale digest, stale workspace, incomplete nodes, active claims, missing QA, or a completed destination collision.

## Legacy Compatibility

Historical Markdown plans and DD bundles remain readable and may be archived by their existing `plan_archive` and `dd_archive` tools under explicit legacy rules. They are not new-work authority and are not prerequisites for graph archival. Do not create a plan artifact merely to archive a graph; graph-linked DD completion is established by the graph's required nodes and terminal QA.

## Auditability

Read a completed graph from `artifacts/implementation/completed/{graph_id}/GRAPH.json`. Use its `requirements`, `contracts`, `nodes`, per-node evidence, and `final_qa` fields to reconstruct ownership and outcome. Git commits and release operations remain orthogonal and are governed by their applicable Git/GitHub skills.
