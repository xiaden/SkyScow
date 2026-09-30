# Change DAG Authoring and Handoff Protocol

This reference defines how a Change DAG is authored, reviewed, and handed to execution. The Change DAG is the single implementation-work authority; there is no task plan, plan phase, or `GRAPH.json` implementation graph.

## Authoring input

The authoring entry point receives:

1. an accepted request or accepted design document (DD);
2. bounded live-repository discovery relevant to the requested change;
3. the Change DAG graph rules and tool contract;
4. existing accepted DD/decision context when applicable.

Discovery always reads the live repository. There is no projected planning worktree; accepted lower work is combined with live source through `dag_read` / `dag_grep` / `dag_search` at `node_id=<boundary semantic node>`, which return that boundary's SELF view: live source, strictly-deeper accepted work, and the boundary node's own persisted terminal work, while excluding same-frontier peers and shallower/future work. The narrower BASE lens (accepted lower work only) is what a new or changing mutation is validated against, so an operation never becomes its own base. `dag_preview(path=..., node_id=...)` remains available for compiled operation/conflict metadata.

## Authoring behavior

1. Generate the smallest semantically justified **semantic** graph as an initial skeleton grounded in known correctness/causal structure: obligations normalized into postconditions, with causal edges derived as a separate judgment. Do not pre-size nodes for one Worker context; implementation breadth may be refined later by lossless SCALE decomposition. The canonical derivation procedure — obligation extraction, postcondition normalization, deduplication, compound splitting, the sibling-independence test, the representation-assumption guard, and the node-quality gates — is `references/semantic-generation.md`; follow it. Each semantic node states a condition/postcondition, never an implementation action, and never assumes a file/symbol/mechanism unless that representation is authoritative input.
2. Submit the whole semantic graph atomically with `dag_create(slug, semantic_graph)` using creation-local handles. The service validates the graph, rejects cycles/unreachable nodes/illegal structure, records `anchor_commit` (current Git `HEAD` as a drift/provenance marker only), allocates canonical opaque node IDs, and rewrites the handles. It persists nothing if creation fails; the Author then exits and hands construction to the controller.
3. The controller reads the state decision/node/branch claim; construction start mints capability references and admits exactly one worker through the DAG service: query `dag_construction_state(slug)` for the next opaque `branch_ref` admission and admit at most one fresh bounded `change-dag-worker` per returned branch in that serialized round. The packet contains `slug`, `branch_ref`, the opaque capability `construction_ref`, and `checkpoint_identity`; the Worker first calls `dag_worker_resolve(slug, branch_ref, construction_ref)`, after which the service selects/binds the concrete node and the Worker retrieves its scope with `dag_decomposition_scope(slug, node_id)` and then either lowers the node's requirement into exact terminal work with `dag_add_create`, `dag_add_edit`, `dag_add_remove`, `dag_add_move`, and `dag_add_run`, or refines it into further semantic decomposition (calling `dag_set_decomposition_only(slug, node_id, true)` only when the node intentionally owns no direct terminal work, otherwise leaving it unresolved). Each worker reads relevant live source plus applicable accepted lower DAG work with `dag_read` / `dag_grep` / `dag_search` at `node_id=<this semantic node>` before authoring; the manager re-queries the frontier rather than tracking progress in session memory and reconciles only when results or conflicts require it. Edit work is authored as exact `{old, new}` replacements; the service generates the internal unified diff, so neither the author nor a worker authors diff syntax. Direct-terminal composition is structural: `edit` is composable, while `create`/`remove`/`move`/`run` are exclusive direct terminals, so a node needing an exclusive terminal plus additional terminal work is decomposed into narrower semantic child requirements.
4. Use `dag_add_requirement` only for incremental insertion, convergence, reconciliation, or recovery — not for initial semantic construction.
5. Correct mutable proposed nodes with the typed `dag_update_*` tools or `dag_remove`; the service owns references, cycle checks, reachability, and atomic rewrites.
6. Every semantic child must materially refine the requirement above it — a distinct required state for MEANING, or the same predicate under a narrower subject scope for SCALE. The parent/child completeness invariant (`satisfaction(all direct semantic children) implies satisfaction(parent)`) and the rest of the model are defined in `change-dag-semantics`. Pure paraphrase or recursive restatement is invalid decomposition. A requirement that cannot yet be lowered may remain an unresolved semantic node.

Decomposition is for **MEANING** or **SCALE**, per the canonical `change-dag-semantics` model: SCALE refinement is lossless and exhaustive, with children collectively implying the parent. The Worker may lower, decompose for meaning, or scale-decompose beneath its assigned scope. The Author owns the initial skeleton; worker `semantic gap`, `duplicate ownership`, `cross-branch relationship`, and `missing prerequisite` reports are controller-consumed evidence for reconciliation.

A construction admission is the service-derived scheduling/reconciliation unit returned by `dag_construction_state`, represented by opaque branch capabilities. The controller admits at most one `change-dag-worker` per returned branch per serialized round; the service selects the concrete semantic node through `dag_worker_resolve`, and the controller re-queries after each batch. Nyx never calculates or queries frontiers and never dispatches node workers, and a worker never spawns another worker. Opaque branch components are serialized authoring units; nodes grouped in one branch are not necessarily independently dispatchable. The service derives branches from the graph and infers no missing causal relationship, so if authoring B requires accepted work under A, B must `requires` A rather than being treated as an independent sibling. Same-frontier workers reason from their SELF view (BASE plus the boundary node's own persisted terminal work), where BASE is live repository plus strictly-deeper accepted work alone and is the lens a new mutation is validated against; peer proposals are excluded from both and are not a design basis. No persisted frontier, worker registry, or construction-state artifact exists — the DAG is the only construction artifact.

`anchor_commit` is not an execution base. A dirty working tree and `HEAD != anchor_commit` are allowed; exact work that no longer applies fails normally and is corrected through DAG recovery.

## Controller-owned post-create construction correctness

The controller is the single owner of post-create construction correctness: frontier motion and Worker admission, interpretation of blocked Workers, reconciliation and convergence, mandatory review, repair routing, and the final whole-DAG `dag_validate`. The Author owns only the initial semantic graph and causal `requires` edges. A worker's `BLOCKED` result — for example `edit_base_unavailable` for a file another branch produces — is evidence that the graph lacks a causal edge or a proper semantic decomposition; the controller routes a semantic/graph defect to `change-dag-semantic-repairer`; the repairer may add the missing `requires` edge or adjust the semantic graph, never by exposing peer work to the worker. Workers self-verify by re-reading their own projected result through `dag_read`; they never run `dag_validate`.

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

The orchestrator/controller (Nyx) may select a bounded `change-dag-reviewer` invocation only when observable coordination or authority conditions justify independent judgment; neither the author manager nor a worker dispatches it. Review is read-only (`dag_show`, `dag_preview`, `dag_validate`) and mandatory after each completed frontier:

```text
SUFFICIENCY  would satisfying every graph leaf requirement satisfy the root requirement?
MINIMALITY   can any semantic layer be removed without losing meaning?
ORDERING     are required order constraints expressed by nesting / run barriers?
GROUNDING    do requirements correspond to live repository reality?
COVERAGE     are caller, migration, verification, documentation, and cross-cutting concerns represented?
WORK         is exact work valid against live source plus applicable lower patches; is overlap compatible?
```

A reviewer verdict is external evidence consumed by the controller. Incomplete construction review returns `PASS`, `FINDINGS`, or `BLOCKED`; unresolved or non-executable state and missing future work are normal incomplete state, not automatic findings. Final review returns `BLOCK_RUN`, `ALLOW_WITH_FOLLOWUP`, or `ALLOW`; the controller routes exact-work findings to `change-dag-fixer`, semantic/graph findings to `change-dag-semantic-repairer`, and authority issues upstream. `ALLOW_WITH_FOLLOWUP` preserves evidence for post-run QA or follow-on repair, while ordinary repairable correctness defects do not automatically block execution. Because a running DAG is immutable, accepted work mutation happens while the DAG is stopped/not active; any later review is selected again from observable conditions.

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
