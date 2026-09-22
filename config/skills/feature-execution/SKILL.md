---
name: feature-execution
description: Execute a persistent implementation graph for one feature. Use when the user asks to implement graph obligations; do not create new plan artifacts for graph-native work.
---

# Feature Execution

Execute the persistent implementation graph created by Exec-Planner. `GRAPH.json` is the authoritative new-work state; worker and manager packets are ephemeral.

```
GRAPH.json → derive ready nodes → claim compatible packets → worker evidence → manager acceptance → terminal QA → graph archive
```

Static authority remains unchanged: Exec-Planner owns graph topology and amendments; Exec-Manager owns claims, releases, blocking, and node acceptance; workers edit production code only for claimed nodes; support agents advise or diagnose; QA remains independent and canonical.

## Execution flow

1. **Validate prerequisites.** Read the persistent graph, source request/DD context, requirements, contracts, and current revision. Reject missing or invalid graph state; do not create a new plan artifact.
2. **Derive readiness.** A node is ready only when it is `PENDING` and every dependency is `COMPLETE` or `SUPERSEDED`. Readiness is derived, never persisted.
3. **Pack and claim.** Exec-Manager selects compatible ready nodes, checks known write overlap and context fit with `context_budget`/`context_tokens`, and atomically claims them. The resulting worker packet is ephemeral.
4. **Execute and accept.** Exec-Worker returns per-node evidence, changed files, actual contracts, deviations, and ownership-classified gaps. Exec-Manager accepts nodes with `impl_graph_complete`, releases or blocks claims as appropriate, and recomputes readiness.
5. **Route only observed needs.** Known bounded defects use Exec-Fixer; unclear causes use Support-Debugger; graph gaps or contract changes return to Exec-Planner; PatternEnforcer remains advisory for concrete impact closure; architectural contradictions return upstream.
6. **Terminal QA.** After all required non-superseded nodes are complete, run the canonical independent QA flow against the current graph revision and workspace fingerprint. Early review is not acceptance.
7. **Archive.** `impl_graph_archive` requires complete required nodes, no active claims or blocking gaps, current terminal QA PASS, and matching revision/digest/workspace evidence. Archival is artifact bookkeeping, not a commit, release, or deployment.

## Safe concurrency

Independent ready nodes may be claimed together only when existing graph metadata proves no dependency, no required output/annotation dependency, no known write overlap, satisfied prerequisites, and order irrelevance. A lack of known overlap is not proof of safety. A blocked branch does not block independent branches; no-ready incomplete state must surface as a graph gap or deadlock.

## QA and findings

QA receives `graph_id`, graph revision/digest, subject node IDs, changed files and provenance, requirements/contracts, and the request/DD context. Findings retain every related node ID and are classified as `NODE_DEFECT`, `GRAPH_GAP`, or `ARCHITECTURE_CONTRADICTION`. Graph amendments, accepted implementation mutations, or repairs invalidate terminal QA and require a fresh run. QA-PushManager and QA-RepoReviewManager remain unchanged.

## Legacy compatibility

Historical Markdown plans, `CONTRACTS.md`, README plan indexes, and DD bundles remain readable and may be archived with legacy tools when explicitly operating on historical artifacts. They are not a second authority for new graph work, and graph-native execution must not create or execute new plans.
