# Change DAG Authoring and Handoff Protocol

This reference defines how a Change DAG is authored, reviewed, and handed to execution. The Change DAG is the single implementation-work authority; there is no task plan, plan phase, or `GRAPH.json` implementation graph.

## Authoring input

The authoring entry point receives:

1. an accepted request or accepted design document (DD);
2. bounded live-repository discovery relevant to the requested change;
3. the Change DAG graph rules and tool contract;
4. existing accepted DD/decision context when applicable.

Discovery always reads the live repository. There is no projected planning worktree; accepted lower work is combined with live source through frontier-bounded `dag_read` / `dag_grep` / `dag_search` at `node_id=<boundary semantic node>`, which excludes same-frontier peers, the boundary node's own work, and shallower/future work. `dag_preview(path=..., node_id=...)` remains available for compiled operation/conflict metadata.

## Authoring behavior

1. Generate the smallest complete **semantic** graph. Each semantic node states a condition/postcondition, not an implementation action.
2. Submit the whole semantic graph atomically with `dag_create(slug, semantic_graph)` using creation-local handles. The service validates the graph, rejects cycles/unreachable nodes/illegal structure, records `anchor_commit` (current Git `HEAD` as a drift/provenance marker only), allocates canonical opaque node IDs, and rewrites the handles. It persists nothing if creation fails.
3. Run the decomposition-frontier loop through the DAG service: query `dag_decomposition_frontier(slug)` for the deepest unresolved semantic nodes and dispatch one fresh bounded `change-dag-worker` per returned node, which retrieves its own scope with `dag_decomposition_scope(slug, node_id)` and then either lowers the node's requirement into exact terminal work with `dag_add_create`, `dag_add_edit`, `dag_add_remove`, `dag_add_move`, and `dag_add_run`, or refines it into further semantic decomposition (calling `dag_set_decomposition_only(slug, node_id, true)` only when the node intentionally owns no direct terminal work, otherwise leaving it unresolved). Each worker reads relevant live source plus applicable accepted lower DAG work with `dag_read` / `dag_grep` / `dag_search` at `node_id=<this semantic node>` before authoring; the manager re-queries the frontier rather than tracking progress in session memory and reconciles only when results or conflicts require it.
4. Use `dag_add_requirement` only for incremental insertion, convergence, reconciliation, or recovery — not for initial semantic construction.
5. Correct mutable proposed nodes with the typed `dag_update_*` tools or `dag_remove`; the service owns references, cycle checks, reachability, and atomic rewrites.
6. Every semantic child must materially refine the requirement above it. Pure paraphrase or recursive restatement is invalid decomposition. A requirement that cannot yet be lowered may remain an unresolved semantic node.

A **decomposition frontier** is the service-derived scheduling/reconciliation unit returned by `dag_decomposition_frontier`, and a **semantic node** is the worker/context unit. The author manager dispatches one `change-dag-worker` per returned frontier node; Nyx never calculates or queries frontiers and never dispatches node workers, and a worker never spawns another worker. Nodes on the same semantic frontier assert authoring independence; the service derives the frontier from `requires` only and infers no missing causal relationship, so if authoring B requires accepted work under A, B must `requires` A rather than being an independent sibling. Same-frontier workers reason from live repository plus strictly-deeper accepted work only; peer proposals are not a design basis. No persisted frontier, worker registry, or construction-state artifact exists — the DAG is the only construction artifact.

`anchor_commit` is not an execution base. A dirty working tree and `HEAD != anchor_commit` are allowed; exact work that no longer applies fails normally and is corrected through DAG recovery.

## Mutation authority

A running/in-progress DAG is immutable. Repair requires execution to stop/fail or `dag_stop`; the stopped mutable region may then be edited before `dag_start(retry=true)`.

```text
satisfied terminal node      immutable
failed terminal node         mutable
semantic ancestors at/above a failed node   mutable
unresolved / not-yet-executed structure      mutable
```

Prior Work Log evidence is never rewritten.

## Optional independent review

The orchestrator/controller (Nyx) may select a bounded `change-dag-reviewer` invocation only when observable coordination or authority conditions justify independent judgment; neither the author manager nor a worker dispatches it. Review is read-only (`dag_show`, `dag_preview`, `dag_validate`) and is not a mandatory handoff:

```text
SUFFICIENCY  would satisfying every graph leaf requirement satisfy the root requirement?
MINIMALITY   can any semantic layer be removed without losing meaning?
ORDERING     are required order constraints expressed by nesting / run barriers?
GROUNDING    do requirements correspond to live repository reality?
COVERAGE     are caller, migration, verification, documentation, and cross-cutting concerns represented?
WORK         is exact work valid against live source plus applicable lower patches; is overlap compatible?
```

A reviewer verdict is external evidence consumed by the controller. `PASS` means only that the requested scope found no material issue; it is not persisted DAG state, execution authorization, or a mandatory lifecycle transition. `AMEND_REQUIRED` returns a bounded finding to Change-DAG-Author while the DAG is stopped/not active. Because a running DAG is immutable, accepted work mutation happens while the DAG is stopped/not active; any later review is selected again from observable conditions.

## Execution handoff

Nyx owns execution admission and artifact lifecycle through the public lifecycle tools; `dag_executor` performs deterministic application:

- `dag_start(slug, retry?)` returns `running` (executor launched) or `queued` with a queue position.
- `dag_status(slug?)` is the canonical completion poll until `root_satisfied` or idle/not active.
- `dag_stop(slug)` stops a queued or running DAG and reconciles interrupted work.
- `dag_archive(slug, reason)` retires a pending bundle into `artifacts/change-dags/archived/`, recording the reason and the state at archive; it does not require resolution, executability, root satisfaction, or a failure-free state.

On successful root satisfaction the executor records inherited starting-worktree state, runs `git add -A`, and creates a local checkpoint commit (preformatted Change-DAG message; SHA/evidence recorded in the Work Log). That checkpoint is executor lifecycle behavior, not a `run` node and not publication.

## Verification boundary

Expose repository-defined, changed-surface verification commands as `run` nodes when they are part of satisfying or verifying the change. Do not manufacture universal test, lint, build, security, documentation, review, or commit steps. Publication/lifecycle commands (commit, push, PR, release, deploy) are excluded from `run` nodes; publication happens only through the separate publication lifecycle after independent QA.

## Prohibited new-work behavior

- creating `artifacts/plans/pending/TASK-*.md` or any task-plan artifact;
- creating an old implementation-graph artifact (for example `artifacts/implementation/pending/{graph_id}/GRAPH.json`) or any `GRAPH.json` implementation graph; the Change DAG under `artifacts/change-dags/{pending|completed}/{slug}/` is the single implementation-work authority;
- creating a second `CONTRACTS.md` authority or a producer/consumer contract registry;
- deriving dependency edges from letters, layers, file order, or review order;
- generation-time write scopes or source-file ownership claims;
- persisting a projected planning worktree;
- treating a Change DAG as a requirements ledger: the DD remains requirements authority;
- storing QA in `EXECUTION_STATE` or gating DAG archival on QA.
