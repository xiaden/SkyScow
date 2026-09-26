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
change-dag-author (constructs, lowers, reconciles, previews, validates)
        ↓
observable independent-review trigger?
   ├─ no → change-dag-runner: dag_start / dag_status
   └─ yes → change-dag-reviewer (bounded external evidence)
                    ↓
                 PASS → change-dag-runner
                 AMEND_REQUIRED → author correction → revalidate
        ↓
independent post-change QA (separate lifecycle, not a DAG phase)
```

`DAG.json` is declarative structure only: the semantic requirements and the exact terminal work that must satisfy them. It contains no runtime status and no execution history. `EXECUTION_STATE.json` records terminal-node execution state for resumability, and `WORK_LOG.jsonl` is append-only evidence.

## Graph model

- `satisfied_by` is the only edge and means ALL-of: a semantic node is satisfied only when every referenced child is satisfied.
- A semantic node with no `satisfied_by` is an unresolved semantic leaf and is not satisfied; unresolved leaves are legal graph state.
- Shared descendants are legal: multiple parents may reference one child identity, and that child is executed or satisfied once.
- Node IDs are opaque, service-assigned, and monotonic (`^N[0-9]+$`); agents never allocate IDs.
- Depth is derived from the longest path from root and is never persisted.
- A `run` child is the only non-semantic child of its semantic parent (run-barrier invariant); a semantic node has at most one direct `run` child.
- `schema_valid`, `executable`, and `resolved` are independent derived properties. `executable` is a pre-execution conflict/applicability check, not a progress measure.
- A running/in-progress DAG is immutable; repair requires execution to stop/fail or `dag_stop`, then the stopped mutable region may be edited before `dag_start(retry=true)`.

## Authoring a Change DAG

1. Read the authoritative request, the accepted DD when present, repository facts, and relevant live surfaces. Discovery always reads the live repository; there is no projected planning worktree.
2. Generate the smallest complete semantic graph. State a condition/postcondition per semantic node — never an implementation action. Pure paraphrase or recursive restatement is invalid decomposition.
3. Submit the whole semantic graph atomically through `dag_create(slug, semantic_graph)`. Initial semantic construction is not a loop of `dag_add_requirement` calls; incremental insertion is reserved for later review, reconciliation, and recovery.
4. Lower exact work from the deepest construction frontier upward. Terminal work node types are `create`, `edit`, `remove`, `move`, and `run`, attached with `dag_add_create` / `dag_add_edit` / `dag_add_remove` / `dag_add_move` / `dag_add_run`.
5. For affected paths, combine live source with applicable accepted lower DAG patches through `dag_preview(path)`. New files, renamed paths, and planned-only symbols are read from DAG work, not rediscovered by repository search.
6. Correct proposed mutable nodes with the typed `dag_update_*` tools or `dag_remove`. `dag_add_requirement` may insert a requirement between existing parents and selected children (convergence) and is also the recovery tool.
7. Validate with `dag_validate` and inspect with `dag_show` and `dag_preview`. Authoring stops at a validated DAG; it never edits repository source.

## Discovery and generation boundaries

- Discovery remains bounded by the semantic requirement being handled. If impact keeps expanding, decompose the requirement so the new concern becomes explicit graph structure rather than loading a larger repository slice.
- Exact work is authored against live repository source plus applicable accepted lower DAG patches; there is no generated write scope and no file-ownership claim system.
- GPU/consumer contracts are not a second dependency system. Interface coherence is re-homed to semantic requirements, bounded caller/implementation discovery, and patch-aware work review.
- A `run` node verifies or satisfies the change (tests, builds, type checks, schema checks). Publication/lifecycle commands — commit, push, PR, release, deploy — never belong in a `run` node and are excluded by the canonical argv policy.
- `anchor_commit` is a creation-time drift/provenance marker only; a dirty tree and `HEAD != anchor_commit` do not invalidate the DAG.

## Optional independent review

Dispatch `change-dag-author` to create or amend the Change DAG. The author owns bounded discovery, semantic decomposition, exact-work lowering, convergence/reconciliation, `dag_preview`, `dag_validate`, and mutable correction/recovery. The author uses authoring tools only and never mutates source.

The orchestrator/controller selects `change-dag-reviewer` only when observable conditions justify independent judgment: shared semantic convergence, incompatible cross-branch proposals, nontrivial behavior-changing ordering, producer/consumer or interface migration, shared schema/registry/persistence/migration work, request/DD decomposition ambiguity, DD authority ambiguity, materially useful recovery amendment, or an explicit user request. Do not invoke it for node count, node types, ordinary run barriers, mechanically independent branches, or ordinary author-correctable mechanical errors.

Reviewer input includes the DAG slug, relevant node IDs/bounded scope, source context, a concrete review question, the observable trigger, and `review_kind` (`SEMANTIC`, `EXACT_WORK`, `DD_CONSISTENCY`, or `COMBINED`). The reviewer is read-only (`dag_show`, `dag_preview`, `dag_validate`). `PASS` means only that the requested scope found no material issue; it is not persisted DAG state, execution authorization, or a mandatory lifecycle transition. `AMEND_REQUIRED` returns a bounded finding to the mutable author; `DD_CONTRADICTION` and `NEEDS_DECISION` route upstream.

## Runner and lifecycle boundary

Authoring ends at a validated DAG; optional independent review is a controller-selected evidence step. Execution belongs to `change-dag-runner`:

- `dag_start(slug, retry?)` launches or queues whole-DAG execution and returns `running` or `queued`.
- `dag_status(slug?)` is the canonical completion poll until the DAG is `root_satisfied` or idle/not active. There is no durable `quiescent` state; a stopped DAG with failed/unresolved blockers is reported descriptively.
- `dag_stop(slug)` stops a queued or running DAG; it is recovery, not rollback.
- On successful root satisfaction the executor records inherited starting-worktree state, runs `git add -A`, and creates a local checkpoint commit. That checkpoint is not publication and is not a DAG `run` node.
- `dag_archive(slug)` moves a pending bundle to completed when execution is complete (root satisfied; no failed or `in_progress` terminal nodes) and does not depend on QA.

## DD lifecycle

A DD may be archived through `dd_archive` only after every Change DAG bundle linked from its Related Documents (or referenced from its Change DAG section) is completed in `artifacts/change-dags/` (artifact lifecycle). `dd_archive` evaluates both linked Change DAG completion and any declared non-DAG prerequisite gate. A declared prerequisite must be satisfied or explicitly migrated before archival; ordinary DDs with no declared prerequisite are not subject to an invented prerequisite gate. Archival does not depend on independent Change-DAG QA or `final_qa` PASS. QA-before-publication remains enforced by the separate `qa-push-manager` publication gate.

## Validation checklist

- [ ] Every required requirement maps to an owned semantic node.
- [ ] Each semantic node states a postcondition, not an action.
- [ ] Every semantic leaf is either terminal work or an explicit unresolved leaf.
- [ ] The graph is acyclic, reachable, and free of illegal run-barrier structure.
- [ ] Exact work is authored against live source plus applicable accepted lower DAG patches.
- [ ] No `GRAPH.json`, task plan, phase letter, or `CONTRACTS.md` authority is created.
- [ ] `dag_validate` reports the DAG as schema-valid (and executable when execution is intended).

## References

- `file://config/skills/decomposing-design-documents/references/subagent-protocol.md` — Change DAG authoring and handoff protocol.
- `file://config/skills/dispatching-agents/references/change-dag-author.md` — author dispatch contract.
- `file://config/skills/dispatching-agents/references/change-dag-reviewer.md` — read-only review dispatch contract.
- `file://artifacts/SkyScow_Change_DAG_Agents.md` — Change DAG agent construction protocol.
- `file://artifacts/SkyScow_Change_DAG_Toolset.md` — Change DAG tool contract.
- `file://artifacts/SkyScow_Change_Execution_Artifacts.md` — Change DAG / Execution State / Work Log artifacts.
