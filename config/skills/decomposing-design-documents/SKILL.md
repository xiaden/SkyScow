---
name: decomposing-design-documents
description: Derive a persistent implementation graph from an accepted request or design document. Use when new work needs requirements, obligations, dependency, contract, and ownership decomposition; do not create plans or README part indexes for new work.
---

# Decomposing Design Documents

For new work, this skill derives graph facts and hands them to `exec-planner`. It does not create task plans, phase files, parts indexes, `CONTRACTS.md`, execution rounds, or plan-letter artifacts.

## New-work pipeline

```text
accepted request / accepted DD
        ↓
Exec-Planner
        ↓
artifacts/implementation/pending/{graph_id}/GRAPH.json
        ↓
deterministic graph validation
        ↓
conditional Exec-PlanGate when observable coordination risk exists
        ↓
ready-frontier execution
```

`GRAPH.json` is the active authority for requirements, implementation obligations, dependencies, contracts, producer/consumer ownership, acceptance, provenance, and context hints. Worker packets and Manager frontiers are runtime scheduling decisions; they are not pre-packed during decomposition.

## Derive graph facts

1. Read the authoritative request, accepted DD when present, repository facts, and relevant existing contracts.
2. Normalize each requirement without weakening, inventing, or dropping user intent. Every required requirement must map to one or more graph nodes.
3. Derive bounded implementation obligations. A node is meaningful repository work, not a file, phase, plan, commit, or arbitrary tiny edit.
4. Assign one owner to each obligation and record changed surfaces, acceptance, and relevant context hints.
5. Add only real edges: prerequisite ordering, producer/consumer contracts, migrations, registrations, generated artifacts, or required data/control flow. Never derive edges from layers, letters, alphabetical order, review order, commit order, or milestone aesthetics.
6. Define canonical root contracts with one declared producer and explicit consumers. Materialized actuals are added only by the producer through graph completion.
7. Validate ownership closure, references, acyclicity, producer ancestry, requirement coverage, contract compatibility, safe writes, and source provenance.
8. Invoke `exec-plan-gate` only after the complete graph exists and deterministic validation passes, and only when observable coordination risk exists. Otherwise `exec-planner` records its own `plan_gate: NOT_REQUIRED` rationale.

## Planner handoff

Dispatch `exec-planner` with the request or accepted DD, repository facts, normalized requirements, candidate obligations, contract relationships, ownership, acceptance, changed surfaces, and context hints. The Planner creates or amends `GRAPH.json`; it does not execute nodes or claim runtime state.

An amendment is bounded and provenance-aware. It may add/update/remove pending nodes, add/remove dependencies, add/update/remove unused contracts, and map/unmap requirements through explicit operations. It must not rewrite completed history, mutate while claims are active, or replace requirement/contract arrays wholesale.

## Graph gate boundary

`exec-plan-gate` is read-only. It validates the complete graph for requirement ownership, dependency closure, cycles, producer/consumer compatibility, materialized contract correctness, shared-write safety, migration ordering, and unowned gaps. It returns only actual gate outcomes; `NOT_REQUIRED` belongs to `exec-planner` and is not a gate verdict.

A graph may contain intermediate downstream-owned incompleteness during execution. It may not contain ownerless required work, impossible acceptance, or a missing producer/consumer owner.

## Runtime boundary

Decomposition ends at graph creation/amendment and validation. Runtime packet assembly belongs to `exec-manager`:

- derive the ready frontier from `PENDING` nodes whose dependencies are `COMPLETE`;
- claim compatible nodes atomically with one packet-level write scope;
- create ephemeral worker packets at execution time;
- accept per-node evidence through Manager-owned graph mutations;
- repeat until all required nodes reach terminal state, or surface a graph gap/blocker.

No packet or frontier artifact is persisted.

## DD lifecycle

A DD may be archived through `dd_archive` only after every linked graph has been archived/completed with terminal QA PASS. A DD with no graph linkage retains the historical legacy archive behavior. Pending legacy plan absence is never proof of completion for a graph-backed DD, and plans and graphs are not co-authorities for new work.

## Legacy compatibility

Historical plan decomposition remains available only for reading or explicit compatibility migration. It must be labeled `LEGACY` and must not be presented as the new-work path. Do not create:

- `artifacts/plans/pending/*`
- `TASK-*.md`
- parts README indexes
- `PART-*-scope.md`
- `CONTRACTS.md` as a second authority
- dependency-ready plan groups or execution rounds

## Validation checklist

- [ ] Every required requirement maps to an owned graph node.
- [ ] Every node has a bounded obligation, acceptance, changed surfaces, and provenance.
- [ ] Every edge is a real prerequisite or producer/consumer relationship.
- [ ] Contract producers and consumers agree and producer ancestry is valid.
- [ ] The graph is acyclic and has no ownerless gaps.
- [ ] Superseded predecessors are structurally rewritten rather than treated as satisfied.
- [ ] PlanGate is invoked only for a complete graph with observable coordination risk.
- [ ] Runtime packetization is deferred to execution.
- [ ] No new plan, parts README, `CONTRACTS.md`, or commit milestone is created.

## References

- `file://config/skills/decomposing-design-documents/references/subagent-protocol.md` — historical dispatch compatibility only.
- `file://config/tools/common/schemas/IMPLEMENTATION_GRAPH_SCHEMA.json` — graph shape.
- `file://config/agents/exec-planner.md` — graph author/amender contract.
- `file://config/agents/exec-plan-gate.md` — read-only graph gate.
