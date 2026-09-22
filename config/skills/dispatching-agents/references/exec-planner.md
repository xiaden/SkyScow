# Exec-Planner

Dispatch Exec-Planner to create or amend a persistent implementation graph. New graph work must not create Markdown plans or a second `CONTRACTS.md` authority.

## When to Dispatch

- A captured request or accepted/amended DD requires implementation obligations, contracts, ownership, or real dependency edges.
- Execution exposes a graph gap, hidden caller, missing producer/consumer edge, impossible acceptance condition, or ownership change.

Do not dispatch for execution, node claims/completion, production edits, QA, or a single obvious edit that needs no graph amendment.

## Dispatch Template

```text
Create or amend implementation graph [GRAPH_ID].

Source context:
- [REQUEST_OR_DD_PATH]
- [REPOSITORY_FACTS]
- [EXISTING_GRAPH_PATH if AMEND]

Task:
  type: CREATE | AMEND
  graph_id: "[GRAPH_ID]"
  title: "[TITLE]"
  reason: "[REASON]"
  requirements: [NORMALIZED_REQUIREMENTS]
  contracts: [PRODUCER_CONSUMER_CONTRACTS]
  nodes: [STABLE_IMPLEMENTATION_OBLIGATIONS]
  remove_node_ids: []

The planner must derive obligations and real edges before writing GRAPH.json, validate the complete graph, preserve active/complete history, and return node ownership, contract materialization, provenance, and blockers. It must not claim or execute nodes.
```

## Graph construction and timing

1. Gather only materially relevant artifacts/research. Unknown repository facts may select Support-Researcher; accepted migration impact may select PatternEnforcer.
2. Derive requirements, obligations, owners, changed surfaces, acceptance, consumed/produced contracts, and actual materialization.
3. Build the implementation DAG using only prerequisites, producer/consumer contracts, migrations, registrations, interfaces, or generated artifacts. Labels, layers, alphabetic order, commits, and review order are not edges.
4. Validate each node, then validate the complete graph for ownership closure, acyclicity, contract compatibility, write overlap, and unowned gaps.
5. Size ephemeral worker-node and manager-review context with `context_tokens`/`context_budget` and `config/agent-context-budgets.yaml`; never copy numeric ceilings into the graph.
6. Applicability is evaluated only after the complete required graph exists and validates. No-trigger graphs receive a Planner-owned `plan_gate: NOT_REQUIRED` record and are not dispatched to Exec-PlanGate. Triggered complete graphs dispatch the read-only gate.

## Outcomes

- `DONE`: graph created/amended, valid, and source/ownership evidence recorded.
- `BLOCKED`: missing source context, unresolved authority, invalid graph, or unresolved architecture.

Exec-Planner never claims, releases, completes, blocks, or executes nodes and never edits production code.

## Expected output

```yaml
status: DONE | BLOCKED
summary: "..."
graph_id: "[GRAPH_ID]"
revision: 3
artifact: "artifacts/implementation/pending/[GRAPH_ID]/GRAPH.json"
validation: {graphValid: true, topology: ACYCLIC}
plan_gate:
  status: NOT_REQUIRED | PASS | AMEND_REQUIRED | DD_CONTRADICTION | MISSING_ARTIFACT | NEEDS_DECISION | BLOCKED
  rationale: "..."
  complete_graph: true
nodes: ["I001"]
blockers: []
```
