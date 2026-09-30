---
name: decomposing-design-documents
description: Decompose an accepted request or design document into a Change DAG. Use when new work needs semantic decomposition and exact work nodes authored as a Change DAG; do not create task plans or implementation graphs.
---

# Decomposing Design Documents

For new work, this skill derives a Change DAG from an accepted request or design document and hands it to `change-dag-author`. The Change DAG is the single implementation-work authority. This skill does not create task plans, plan phases, plan letters, `CONTRACTS.md`, execution rounds, or `GRAPH.json` implementation graphs.

## New-work pipeline

```text
accepted request / accepted DD
        ↓
bounded live-repository discovery
        ↓
change-dag-author (one atomic semantic dag_create, then exits)
         ↓
 controller-owned serialized frontier motion and one bounded change-dag-worker per opaque branch_ref per round (lower to exact work, or decompose further)
        ↓
observable independent-review trigger?
   ├─ no → Nyx: dag_start / dag_status
   └─ yes → change-dag-reviewer (bounded external evidence)
                      ↓
                  PASS → Nyx lifecycle control
                 FINDINGS → route by category: Fixer for exact work, semantic-repairer for semantic/graph, upstream for authority
        ↓
independent post-change QA (separate lifecycle, not a DAG phase)
```

The Change DAG bundle keeps construction and execution records separate: `DAG.json` is current declarative construction state; `DAG_MUTATIONS.jsonl`, when present, is append-only construction provenance; `EXECUTION_STATE.json` records terminal-node execution lifecycle state for resumability; and `WORK_LOG.jsonl` is append-only execution evidence. Archival moves these bundle files as-is and does not merge mutation provenance into the Work Log.

## Graph model

- `requires` is the only edge; it is ALL-of and expresses what must become true for a semantic requirement to be fulfilled — a semantic node is satisfied only when every node it directly requires is satisfied.
- A semantic node with no `requires` is an unresolved semantic node and is not satisfied; unresolved semantic nodes are legal graph state. A semantic node is locally resolved when it directly requires at least one terminal work node, or declares `decomposition_only=true` over semantic children only. Unresolved DAGs are valid authoring artifacts but are not executable.
- Shared descendants are legal: multiple parents may reference one child identity, and that child is executed or satisfied once.
- Opaque branch components are serialized authoring units; nodes grouped in one branch are not necessarily independently dispatchable. The frontier service derives branches from the graph and never infers a missing causal relationship. If correct authoring of B requires accepted work from A, B must have a `requires` path to A rather than being treated as an independent sibling.
- Node IDs are opaque, service-assigned, and monotonic (`^N[0-9]+$`); agents never allocate IDs.
- Depth is derived from the longest path from root and is never persisted.
- Direct-terminal composition is structural: semantic children are always allowed; `edit` is composable (any number may coexist with each other and with semantic children); `create`, `remove`, `move`, and `run` are exclusive direct terminals — when a semantic node has any of them it must be that node's only terminal child. A `run` child is additionally the run-barrier node, and a semantic node has at most one direct `run` child.
- `schema_valid`, `executable`, and `resolved` are distinct derived properties. `executable` is the aggregate execution-admission/lint result: it requires structural validity, `resolved`, and no deterministic compiler/context admission conflict. Recoverable live-applicability failures stay reported as `runtime_failures`, not admission blockers.
- A running/in-progress DAG is immutable; repair requires execution to stop/fail or `dag_stop`, then the stopped mutable region may be edited before `dag_start(retry=true)`.

## Authoring a Change DAG

1. Read the authoritative request, the accepted DD when present, repository facts, and relevant live surfaces. Discovery always reads the live repository; there is no projected planning worktree.
2. Generate the smallest complete semantic graph as an initial **semantic skeleton** grounded in known correctness/causal structure: distinct obligations stated as postconditions, with causal edges derived as a separate judgment. Do not pre-size nodes for one Worker context; Worker-discovered breadth may be refined later through lossless SCALE decomposition. Follow the canonical derivation procedure in `references/semantic-generation.md` — obligation extraction, postcondition normalization, deduplication, compound splitting, the sibling-independence test, and the representation-assumption guard. State a condition/postcondition per semantic node — never an implementation action, and never an assumed file/symbol/mechanism unless authoritative. Pure paraphrase or recursive restatement is invalid decomposition.
3. Submit the whole semantic graph atomically through `dag_create(slug, semantic_graph)`. Initial semantic construction is not a loop of `dag_add_requirement` calls; incremental insertion is reserved for later review, reconciliation, and recovery.
4. After the atomic create, the controller queries the decomposition frontier and admits at most one fresh bounded `change-dag-worker` per opaque branch in each serialized round. The packet contains `slug`, `branch_ref`, the opaque capability `construction_ref`, and `checkpoint_identity`, not a selected node ID. The Worker first calls `dag_worker_resolve(slug, branch_ref, construction_ref)`, and the service selects/binds one currently authorable semantic node before the Worker uses `dag_decomposition_scope` and lowers the returned node's requirement into exact terminal work (`create`, `edit`, `remove`, `move`, `run`, attached with `dag_add_create` / `dag_add_edit` / `dag_add_remove` / `dag_add_move` / `dag_add_run`) or refines it into further semantic decomposition. The controller never computes depths itself, never keeps a processed-frontier registry, and reconciles a frontier only when worker results or conflicts require it. Edit work is authored as exact `{old, new}` replacements (`dag_add_edit(slug, parent_ids, path, replacements)`); the service generates the internal unified diff, so agents never author diff syntax. A worker that reports `edit_base_unavailable` for a peer-produced file signals a missing causal edge or decomposition defect, which the author repairs by adding a `requires` edge or decomposing the producing obligation — never by exposing peer work.
5. For affected paths, combine live source with applicable accepted lower DAG work through `dag_read` / `dag_grep` / `dag_search` at `node_id=<boundary semantic node>`. These return that boundary's SELF view — live source, strictly-deeper accepted work, and the boundary node's own persisted terminal work — while same-frontier peers and shallower/future work stay excluded. The narrower BASE lens (accepted lower work only, without the boundary's own work) is what a new mutation is validated against, so an operation never becomes its own base. `dag_preview(path=..., node_id=...)` remains available for compiled operation/conflict metadata. New files, renamed paths, and planned-only symbols are read from DAG work, not rediscovered by repository search.
6. Correct proposed mutable nodes with the typed `dag_update_*` tools or `dag_remove`. `dag_add_requirement` may insert a requirement between existing parents and selected children (convergence) and is also the recovery tool.
7. Validate with `dag_validate` and inspect with `dag_show` and `dag_preview`. Authoring stops at a validated DAG; it never edits repository source.

## Discovery and generation boundaries

- Discovery remains bounded by the semantic requirement being handled. Broad implementation discovery is evidence to evaluate SCALE decomposition, not automatic evidence of a new semantic concern. The file-count rule and the MEANING/SCALE model are defined once in `change-dag-semantics`; real repository breadth or context cost may justify narrowing the SAME predicate recursively.
- Decomposition has two reasons: **MEANING** (distinct required states or causal obligations) and **SCALE** (the same semantic postcondition is too broad for one bounded context); SCALE refinement is lossless and exhaustive. The Worker owns scale refinement beneath its assigned scope; the Author owns the initial semantic skeleton. The canonical model — including the parent/child completeness invariant — is `change-dag-semantics`.
- Each returned branch is processed by at most one bounded `change-dag-worker` invocation per round; the service selects the concrete semantic node inside the branch at resolution time reasoning from its SELF view — BASE plus the boundary node's own persisted terminal work, where BASE is live repository plus strictly-deeper accepted work. A new or changing mutation is validated against BASE alone, so an operation never becomes its own base. Branch components are serialized authoring units, so same-frontier nodes are not necessarily independently dispatchable; peer proposals are excluded from both lenses and are not a design basis, and the frontier service infers no missing causal dependency. There is no persisted frontier, worker registry, or construction-state artifact — the DAG is the only construction artifact.
- Exact work is authored against live repository source plus applicable accepted lower DAG patches; there is no generated write scope and no file-ownership claim system.
- GPU/consumer contracts are not a second dependency system. Interface coherence is re-homed to semantic requirements, bounded caller/implementation discovery, and patch-aware work review.
- A `run` node verifies or satisfies the change (tests, builds, type checks, schema checks). Publication/lifecycle commands — commit, push, PR, release, deploy — never belong in a `run` node and are excluded by the canonical argv policy.
- Edit work is authored as ordered exact `{old, new}` replacements applied sequentially with zero fuzz (`old` non-empty and occurring exactly once); the service derives and validates the internal unified diff. Agents never author unified diff syntax, hunk numbers, or `*** Begin Patch` / `*** End Patch`.
- `anchor_commit` is a creation-time drift/provenance marker only; a dirty tree and `HEAD != anchor_commit` do not invalidate the DAG.

## Optional independent review

Dispatch `change-dag-author` for one initial semantic `dag_create`; it verifies creation and exits. The controller owns frontier motion, serialized Worker admission, mandatory review, exact-work routing to `change-dag-fixer`, semantic/graph routing to `change-dag-semantic-repairer`, authority escalation, reconciliation, `dag_preview`, `dag_validate`, and mutable recovery. The Author uses semantic authoring tools only, never mutates source, and never dispatches agents.

The orchestrator/controller selects `change-dag-reviewer` only when observable conditions justify independent judgment: shared semantic convergence, incompatible cross-branch proposals, nontrivial behavior-changing ordering, producer/consumer or interface migration, shared schema/registry/persistence/migration work, request/DD decomposition ambiguity, DD authority ambiguity, materially useful recovery amendment, or an explicit user request. Do not invoke it for node count, node types, ordinary run barriers, mechanically independent branches, or ordinary author-correctable mechanical errors.

Reviewer input includes the DAG slug, relevant node IDs/bounded scope, source context, a concrete review question, the observable trigger, and `review_kind` (`SEMANTIC`, `EXACT_WORK`, `DD_CONSISTENCY`, or `COMBINED`). The reviewer is read-only (`dag_show`, `dag_preview`, `dag_validate`). `PASS` means only that the requested scope found no material issue; it is not persisted DAG state, execution authorization, or a mandatory lifecycle transition. Final review uses `BLOCK_RUN`, `ALLOW_WITH_FOLLOWUP`, or `ALLOW`: Nyx routes exact-work defects to `change-dag-fixer`, semantic/graph defects to `change-dag-semantic-repairer`, and authority issues upstream. `ALLOW_WITH_FOLLOWUP` preserves evidence for post-run QA or follow-on repair; ordinary repairable correctness defects do not automatically block execution.

## Lifecycle boundary

Authoring ends at a validated DAG; optional independent review is a controller-selected evidence step. Nyx owns lifecycle control through the four public tools; `dag_executor` performs deterministic execution:

- `dag_start(slug, retry?)` launches or queues whole-DAG execution and returns `running` or `queued`.
- `dag_status(slug?)` is the canonical completion poll until the DAG is `root_satisfied` or idle/not active. There is no durable `quiescent` state; a stopped DAG with failed/unresolved blockers is reported descriptively.
- `dag_stop(slug)` stops a queued or running DAG; it is recovery, not rollback.
- On successful root satisfaction the executor records inherited starting-worktree state, runs `git add -A`, and creates a local checkpoint commit. That checkpoint is not publication and is not a DAG `run` node.
- `dag_archive(slug, reason)` retires a pending bundle into `artifacts/change-dags/archived/` with a required reason and an `ARCHIVE.json` disposition record. It is lifecycle cleanup: it does not require resolution, executability, root satisfaction, absence of failures, or QA. A running DAG must be stopped first; a queued DAG must be cancelled with `dag_stop`. Load `change-dag-lifecycle` for the concise operating contract.

## DD lifecycle

A DD may be archived through `dd_archive` only after every Change DAG bundle linked from its Related Documents (or referenced from its Change DAG section) has been retired into `artifacts/change-dags/archived/` (artifact lifecycle). Retirement is not success: consult the Change DAG's `ARCHIVE.json` for the recorded outcome. `dd_archive` evaluates both linked Change DAG completion and any declared non-DAG prerequisite gate. A declared prerequisite must be satisfied or explicitly migrated before archival; ordinary DDs with no declared prerequisite are not subject to an invented prerequisite gate. Archival does not depend on independent Change-DAG QA or `final_qa` PASS. QA-before-publication remains enforced by the separate `qa-push-manager` publication gate.

## Validation checklist

- [ ] Every required requirement maps to an owned semantic node.
- [ ] Each semantic node states a postcondition, not an action.
- [ ] Every semantic node is either locally resolved or an explicit unresolved semantic node.
- [ ] The graph is acyclic, reachable, and free of illegal exclusive-terminal structure (`edit` composable; `create`/`remove`/`move`/`run` exclusive direct terminals).
- [ ] Exact work is authored against live source plus applicable accepted lower DAG patches.
- [ ] No `GRAPH.json`, task plan, phase letter, or `CONTRACTS.md` authority is created.
- [ ] `dag_validate` reports the DAG as schema-valid (and executable when execution is intended).
- [ ] `dag_construction_state` reports completion and `dag_validate` confirms resolved before construction is declared complete.

## References

- `file://config/skills/decomposing-design-documents/references/subagent-protocol.md` — Change DAG authoring and handoff protocol.
- `file://config/skills/decomposing-design-documents/references/semantic-generation.md` — canonical initial semantic-graph derivation procedure.
- `file://config/skills/dispatching-agents/references/change-dag-author.md` — author dispatch contract.
- `file://config/skills/dispatching-agents/references/change-dag-worker.md` — bounded opaque/session-bound Worker dispatch contract (internal to the controller).
- `file://config/skills/dispatching-agents/references/change-dag-reviewer.md` — read-only review dispatch contract.
- `file://artifacts/SkyScow_Change_DAG_Agents.md` — Change DAG agent construction protocol.
- `file://artifacts/SkyScow_Change_DAG_Toolset.md` — Change DAG tool contract.
- `file://artifacts/SkyScow_Change_Execution_Artifacts.md` — Change DAG / Execution State / Work Log artifacts.
