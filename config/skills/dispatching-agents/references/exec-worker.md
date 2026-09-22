# Exec-Worker

Dispatch Exec-Worker to implement a bounded packet of compatible claimed implementation-graph nodes.

## When to Dispatch

**Dispatch when:**
- Exec-Manager has atomically claimed compatible ready graph nodes.
- The manager has an ephemeral packet with obligations, contracts, acceptance, context hints, graph revision, and claim identity.

**Do NOT dispatch when:**
- The graph topology needs creation or amendment — use `exec-planner`.
- Nodes need claiming, completion, blocking, or release — use `exec-manager`.
- You need QA review — use `qa-reviewer`.

## Dispatch Template

```
Implement the claimed graph packet `[GRAPH_ID]` containing node IDs `[NODE_IDS]`.

Your scope: claimed nodes only. Read the ephemeral packet supplied by Exec-Manager; it is not a persisted plan.

Context:
- [REQUEST_OR_DD_PATH] — authoritative request or accepted design context
- [CONTRACT_CONTEXT] — consumed/produced contracts and acceptance
- [SOURCE_CONTEXT] — files and repository patterns required by the packet

task:
  graph_id: "[GRAPH_ID]"
  graph_revision: [GRAPH_REVISION]
  node_ids: ["I001", "I002"]
  claim_id: "[CLAIM_ID]"

For each node: implement, return evidence, changed files, deviations, and actual contracts. Do not mutate graph state.
Report DONE when all claimed nodes have evidence and dependency-permitted verification.
```

## Required Fields

| Field | Description | Example |
|-------|-------------|---------|
| `[GRAPH_ID]` | Persistent implementation graph identity | `feature-change` |
| `graph_revision` | Revision claimed by the manager | `3` |
| `node_ids` | Claimed node identifiers | `I001, I002` |
| `claim_id` | Atomic claim identity | `worker-claim-1` |

## Expected Output

| Status | Meaning |
|--------|---------|
| `DONE` | All claimed nodes have evidence and permitted verification |
| `BLOCKED` | A claimed node cannot be completed — reason provided |
| `ESCALATE` | Issue requires manager or planner intervention |

Output includes:
- Per-node evidence and acceptance result
- Files created/modified/deleted
- Actual contracts and deviations
- Downstream-owned gaps with named graph owners
- Ownerless blockers with specific details

## Node Evidence Rules

After completing each node, return:
- What was done and acceptance evidence
- Files changed and actual contracts
- Any deviations, downstream owner, or warning

**Never** modify graph structure or status, write worker/manager packets to disk, or silently choose a new obligation. The manager alone accepts completion and the planner alone amends topology.

## Spec-First Testing

When spec tests exist for a claimed node:
- Read the spec tests first to understand expected behavior.
- Implement toward the graph obligation and contract.
- Do not modify spec tests unless the manager/planner explicitly amends the graph.
- Report passing, expected, or unexpected failures with ownership classification.
