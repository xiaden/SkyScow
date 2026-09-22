# Exec-Manager

Dispatch Exec-Manager to schedule a persistent implementation graph.

## When to Dispatch

- A validated `GRAPH.json` exists and ready implementation nodes need claims and worker packets.
- A graph node result needs manager acceptance, release, blocking, bounded repair, or terminal QA routing.

**Do NOT dispatch when:**
- Graph topology is missing or wrong — use Exec-Planner.
- Production implementation is the task — use Exec-Worker only through Exec-Manager.
- Diagnosis is the task — use Support-Debugger.

## Dispatch Template

```text
Execute graph [GRAPH_ID] at structure revision [STRUCTURE_REVISION] and structural digest [STRUCTURE_DIGEST].

Context:
- [REQUEST_OR_DD_PATH]
- [GRAPH_CONTEXT]
- [CONTRACT_CONTEXT]
- [SOURCE_CONTEXT]

The manager must:
- Read the graph summary and derived-ready nodes.
- Claim compatible nodes atomically before any worker dispatch.
- Pack only obligations/contracts/source context that fit the ephemeral worker packet.
- Dispatch Exec-Worker with graph ID, current structure/state revisions, structural digest, node IDs, and claim ID.
- Accept only evidence-backed node completion; release or block claims explicitly.
- Route observed defects, unclear failures, graph gaps, and architectural contradictions only to the appropriate bounded capability.
- Run mandatory independent terminal QA after all required nodes are complete.
- Archive only through `impl_graph_archive` with fresh graph/workspace evidence.

Do not edit production code, amend topology, create plans, persist packets, bypass QA, or claim global-green/release/commit completion.

task:
  graph_id: "[GRAPH_ID]"
  structure_revision: [STRUCTURE_REVISION]
  structure_digest: [STRUCTURE_DIGEST]
  state_revision: [STATE_REVISION]
  terminal_review_required: true
```

## Required Fields

| Field | Description |
| --- | --- |
| `[GRAPH_ID]` | Persistent implementation graph identity |
| `[STRUCTURE_REVISION]` | Structural revision read before claiming nodes |
| `[STRUCTURE_DIGEST]` | Structural digest read before claiming nodes |
| `[STATE_REVISION]` | Current runtime state revision used for packet provenance |
| request/DD context | Requirement provenance and accepted architecture |
| graph context | Requirements, contracts, nodes, statuses, blockers |
| source context | Bounded files and repository facts for packet assembly |

## Routing Rules

- Ready nodes are derived from `PENDING` status plus complete non-superseded dependencies.
- Known bounded node defects go directly to Exec-Fixer.
- Unclear causes go to Support-Debugger: `SIMPLE` → Fixer, `NEEDS_PLAN` → Exec-Planner amendment, `INCONCLUSIVE` → escalation.
- Missing callers, contracts, ownership, or impossible acceptance conditions go to Exec-Planner; do not silently amend topology.
- PatternEnforcer is advisory only for concrete impact closure; scope changes go to Exec-Planner.
- Independent ready branches may run concurrently only when graph metadata proves no dependency, required output dependency, known write overlap, unsatisfied prerequisite, or order sensitivity.
- A blocked branch does not block unrelated ready branches. No-ready incomplete state is a graph gap/deadlock and must surface.

## QA and Archive

QA receives graph identity/revision/digest, subject node IDs, changed files/provenance, requirements/contracts, and request/DD context. QA applicability remains canonical and is not duplicated here. Findings retain all related node IDs and use `NODE_DEFECT`, `GRAPH_GAP`, or `ARCHITECTURE_CONTRADICTION`.

A graph amendment, accepted implementation mutation, or repair invalidates terminal QA. Archive requires all required nodes complete or superseded, no active claims/blocking gaps, current terminal QA PASS, and matching revision/digest/workspace fingerprint.

## Expected Output

```yaml
status: DONE | BLOCKED | ESCALATE
summary: "..."
graph_id: "[GRAPH_ID]"
structure_revision: 3
state_revision: 5
selected_nodes: ["I001"]
completed_nodes: ["I001"]
blocked_nodes: []
execution_trace:
  selected: []
  skipped: []
  outcomes: []
  terminal_reason: "..."
qa: {status: PASS | FAIL | NOT_RUN, state_revision: 5, implementation_state_digest: "...", workspace_fingerprint: "..."}
archive: {status: ARCHIVED | PENDING}
blockers: []
```
