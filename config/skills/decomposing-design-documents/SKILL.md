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
change-dag-author (manager: semantic graph, dag_decomposition_frontier loop, reconciliation, validation)
        ↓
one bounded change-dag-worker per frontier branch (lower to exact work, or decompose further)
        ↓
observable independent-review trigger?
   ├─ no → Nyx: dag_start / dag_status
   └─ yes → change-dag-reviewer (bounded external evidence)
                      ↓
                  PASS → Nyx lifecycle control
                 AMEND_REQUIRED → author correction → revalidate
        ↓
independent post-change QA (separate lifecycle, not a DAG phase)
```

`DAG.json` is declarative structure only: the semantic requirements and the exact terminal work that must satisfy them. It contains no runtime status and no execution history. `EXECUTION_STATE.json` records terminal-node execution state for resumability, and `WORK_LOG.jsonl` is append-only evidence.

## Graph model

- `requires` is the only edge; it is ALL-of and expresses what must become true for a semantic requirement to be fulfilled — a semantic node is satisfied only when every node it directly requires is satisfied.
- A semantic node with no `requires` is an unresolved semantic node and is not satisfied; unresolved semantic nodes are legal graph state. A semantic node is locally resolved when it directly requires at least one terminal work node, or declares `decomposition_only=true` over semantic children only. Unresolved DAGs are valid authoring artifacts but are not executable.
- Shared descendants are legal: multiple parents may reference one child identity, and that child is executed or satisfied once.
- Semantic siblings imply no authoring dependency through each other. Nodes on the same semantic frontier assert authoring independence; the frontier service derives the frontier from `requires` edges only and never infers a missing causal relationship. If correct authoring of B requires accepted work from A, B must have a `requires` path to A rather than being represented as an independent sibling.
- Node IDs are opaque, service-assigned, and monotonic (`^N[0-9]+$`); agents never allocate IDs.
- Depth is derived from the longest path from root and is never persisted.
- Direct-terminal composition is structural: semantic children are always allowed; `edit` is composable (any number may coexist with each other and with semantic children); `create`, `remove`, `move`, and `run` are exclusive direct terminals — when a semantic node has any of them it must be that node's only terminal child. A `run` child is additionally the run-barrier node, and a semantic node has at most one direct `run` child.
- `schema_valid`, `executable`, and `resolved` are distinct derived properties. `executable` is the aggregate execution-admission/lint result: it requires structural validity, `resolved`, and no deterministic compiler/context admission conflict. Recoverable live-applicability failures stay reported as `runtime_failures`, not admission blockers.
- A running/in-progress DAG is immutable; repair requires execution to stop/fail or `dag_stop`, then the stopped mutable region may be edited before `dag_start(retry=true)`.

## Authoring a Change DAG

1. Read the authoritative request, the accepted DD when present, repository facts, and relevant live surfaces. Discovery always reads the live repository; there is no projected planning worktree.
2. Generate the smallest complete semantic graph as an initial **semantic skeleton** grounded in known correctness/causal structure: distinct obligations stated as postconditions, with causal edges derived as a separate judgment. Do not pre-size nodes for one Worker context; Worker-discovered breadth may be refined later through lossless SCALE decomposition. Follow the canonical derivation procedure in `references/semantic-generation.md` — obligation extraction, postcondition normalization, deduplication, compound splitting, the sibling-independence test, and the representation-assumption guard. State a condition/postcondition per semantic node — never an implementation action, and never an assumed file/symbol/mechanism unless authoritative. Pure paraphrase or recursive restatement is invalid decomposition.
3. Submit the whole semantic graph atomically through `dag_create(slug, semantic_graph)`. Initial semantic construction is not a loop of `dag_add_requirement` calls; incremental insertion is reserved for later review, reconciliation, and recovery.
4. The author runs the decomposition-frontier loop by querying the DAG service: `dag_decomposition_frontier(slug)` returns the deepest unresolved semantic nodes, and for each returned node the author dispatches one fresh bounded `change-dag-worker` that lowers the node's requirement into exact terminal work (`create`, `edit`, `remove`, `move`, `run`, attached with `dag_add_create` / `dag_add_edit` / `dag_add_remove` / `dag_add_move` / `dag_add_run`) or refines it into further semantic decomposition. The author never computes depths itself, never keeps a processed-frontier registry, and reconciles a frontier only when worker results or conflicts require it. Edit work is authored as exact `{old, new}` replacements (`dag_add_edit(slug, parent_ids, path, replacements)`); the service generates the internal unified diff, so agents never author diff syntax. A worker that reports `edit_base_unavailable` for a peer-produced file signals a missing causal edge or decomposition defect, which the author repairs by adding a `requires` edge or decomposing the producing obligation — never by exposing peer work.
5. For affected paths, combine live source with applicable accepted lower DAG work through `dag_read` / `dag_grep` / `dag_search` at `node_id=<boundary semantic node>`. These return that boundary's SELF view — live source, strictly-deeper accepted work, and the boundary node's own persisted terminal work — while same-frontier peers and shallower/future work stay excluded. The narrower BASE lens (accepted lower work only, without the boundary's own work) is what a new mutation is validated against, so an operation never becomes its own base. `dag_preview(path=..., node_id=...)` remains available for compiled operation/conflict metadata. New files, renamed paths, and planned-only symbols are read from DAG work, not rediscovered by repository search.
6. Correct proposed mutable nodes with the typed `dag_update_*` tools or `dag_remove`. `dag_add_requirement` may insert a requirement between existing parents and selected children (convergence) and is also the recovery tool.
7. Validate with `dag_validate` and inspect with `dag_show` and `dag_preview`. Authoring stops at a validated DAG; it never edits repository source.

## Discovery and generation boundaries

- Discovery remains bounded by the semantic requirement being handled. Broad implementation discovery is evidence to evaluate SCALE decomposition, not automatic evidence of a new semantic concern. The file-count rule and the MEANING/SCALE model are defined once in `change-dag-semantics`; real repository breadth or context cost may justify narrowing the SAME predicate recursively.
- Decomposition has two reasons: **MEANING** (distinct required states or causal obligations) and **SCALE** (the same semantic postcondition is too broad for one bounded context); SCALE refinement is lossless and exhaustive. The Worker owns scale refinement beneath its assigned scope; the Author owns the initial semantic skeleton. The canonical model — including the parent/child completeness invariant — is `change-dag-semantics`.
- Each semantic node is lowered by one bounded `change-dag-worker` invocation reasoning from its SELF view — BASE plus the boundary node's own persisted terminal work, where BASE is live repository plus strictly-deeper accepted work. A new or changing mutation is validated against BASE alone, so an operation never becomes its own base. Same-frontier peer proposals are excluded from both lenses and are not a design basis, and the frontier service infers no missing causal dependency. There is no persisted frontier, worker registry, or construction-state artifact — the DAG is the only construction artifact.
- Exact work is authored against live repository source plus applicable accepted lower DAG patches; there is no generated write scope and no file-ownership claim system.
- GPU/consumer contracts are not a second dependency system. Interface coherence is re-homed to semantic requirements, bounded caller/implementation discovery, and patch-aware work review.
- A `run` node verifies or satisfies the change (tests, builds, type checks, schema checks). Publication/lifecycle commands — commit, push, PR, release, deploy — never belong in a `run` node and are excluded by the canonical argv policy.
- Edit work is authored as ordered exact `{old, new}` replacements applied sequentially with zero fuzz (`old` non-empty and occurring exactly once); the service derives and validates the internal unified diff. Agents never author unified diff syntax, hunk numbers, or `*** Begin Patch` / `*** End Patch`.
- `anchor_commit` is a creation-time drift/provenance marker only; a dirty tree and `HEAD != anchor_commit` do not invalidate the DAG.

## Optional independent review

Dispatch `change-dag-author` to create or amend the Change DAG. The author is the construction manager: it owns bounded discovery, semantic decomposition, the service-derived decomposition-frontier loop (`dag_decomposition_frontier`), per-branch `change-dag-worker` dispatch, exact-work lowering, convergence/reconciliation, `dag_preview`, `dag_validate`, and mutable correction/recovery. It uses authoring tools only, never mutates source, and never dispatches `change-dag-reviewer` (it surfaces review triggers for Nyx).

The orchestrator/controller selects `change-dag-reviewer` only when observable conditions justify independent judgment: shared semantic convergence, incompatible cross-branch proposals, nontrivial behavior-changing ordering, producer/consumer or interface migration, shared schema/registry/persistence/migration work, request/DD decomposition ambiguity, DD authority ambiguity, materially useful recovery amendment, or an explicit user request. Do not invoke it for node count, node types, ordinary run barriers, mechanically independent branches, or ordinary author-correctable mechanical errors.

Reviewer input includes the DAG slug, relevant node IDs/bounded scope, source context, a concrete review question, the observable trigger, and `review_kind` (`SEMANTIC`, `EXACT_WORK`, `DD_CONSISTENCY`, or `COMBINED`). The reviewer is read-only (`dag_show`, `dag_preview`, `dag_validate`). `PASS` means only that the requested scope found no material issue; it is not persisted DAG state, execution authorization, or a mandatory lifecycle transition. `AMEND_REQUIRED` returns a bounded finding to the mutable author; `DD_CONTRADICTION` and `NEEDS_DECISION` route upstream.

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
- [ ] `dag_decomposition_frontier` reports `resolved=true` before construction is declared complete.

## References

- `file://config/skills/decomposing-design-documents/references/subagent-protocol.md` — Change DAG authoring and handoff protocol.
- `file://config/skills/decomposing-design-documents/references/semantic-generation.md` — canonical initial semantic-graph derivation procedure.
- `file://config/skills/dispatching-agents/references/change-dag-author.md` — author dispatch contract.
- `file://config/skills/dispatching-agents/references/change-dag-worker.md` — bounded single-node worker dispatch contract (internal to the author manager).
- `file://config/skills/dispatching-agents/references/change-dag-reviewer.md` — read-only review dispatch contract.
- `file://artifacts/SkyScow_Change_DAG_Agents.md` — Change DAG agent construction protocol.
- `file://artifacts/SkyScow_Change_DAG_Toolset.md` — Change DAG tool contract.
- `file://artifacts/SkyScow_Change_Execution_Artifacts.md` — Change DAG / Execution State / Work Log artifacts.
