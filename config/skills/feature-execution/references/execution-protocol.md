# Graph Execution Protocol

This protocol constructs ephemeral worker packets from the authoritative implementation graph. It does not create or execute Markdown plans.

## Packet structure

Every worker dispatch includes:

1. **TASK** — graph ID, current revision, claim ID, and claimed node IDs.
2. **GRAPH CONTEXT** — obligations, dependencies, requirements, contracts, acceptance, provenance, and blockers relevant to the claimed nodes.
3. **SOURCE CONTEXT** — bounded repository files and patterns required by those obligations.
4. **CONSTRAINTS** — assigned nodes only, no topology/status mutation, no persisted packet.
5. **RETURN** — per-node evidence, changed files, actual contracts, deviations, downstream-owned gaps, and ownerless blockers.

## Packet template

```text
Implement claimed graph nodes:

## Task
graph_id: {graph_id}
graph_revision: {graph_revision}
claim_id: {claim_id}
node_ids: [{node_ids}]

## Graph context
{obligations, requirements, contracts, acceptance, dependency state, and provenance}

## Source context
{bounded files and relevant repository patterns}

## Constraints
- Implement only claimed nodes.
- Do not claim, release, complete, block, or amend graph state.
- Do not write this packet to disk.
- Preserve real contracts and report deviations.

## Return
For each node: evidence, changed files, actual contracts, verification, downstream owner if incomplete, or ownerless blocker.
```

## Context assembly

Use `context_tokens` for generic file ranges and `context_budget` with `graph_packet.kind: worker_node` for packet sizing. Include only source, contracts, acceptance, and request/DD context needed by the claimed nodes. Do not split or combine nodes merely by layer; combine only when obligations and context fit, and split semantically unified work when canonical context policy overloads.

## Scheduling and safety

Exec-Manager derives readiness and atomically claims nodes before dispatch. Independent ready nodes may share a packet or run concurrently only when existing graph metadata proves no dependency, no required output dependency, no known write overlap, satisfied prerequisites, and order irrelevance. A lack of known overlap is not proof of safety. Do not introduce a phase DAG, workflow schema, queue, or persisted packet store.

## Failure handling

Classify each failure as:

- **Node-owned:** current obligation or implementation defect; fix or block it.
- **Downstream-owned:** incomplete integration is explicitly owned by a present, non-superseded graph node; report that owner.
- **Graph gap:** missing caller, contract, dependency, or impossible acceptance; return to Exec-Planner.
- **Ownerless:** block/escalate; never hide it as downstream work.

A blocked branch does not block independent branches. A no-ready incomplete graph must surface as a gap/deadlock.
