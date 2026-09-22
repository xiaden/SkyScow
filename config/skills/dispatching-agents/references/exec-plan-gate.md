# Exec-PlanGate

Dispatch Exec-PlanGate from Exec-Planner as the conditional read-only preflight for a complete persistent implementation graph with observable coordination risk.

## When to Dispatch

- Exec-Planner has created or amended a complete `GRAPH.json` with cross-node contracts, shared writes/schemas/migrations/registries, nontrivial ordering, migration scope, generational supersession, or unresolved ownership closure.
- A gated graph is amended or its accepted DD/source changes; Exec-Planner reruns the gate before claims.

**Do NOT dispatch when:**
- The complete graph has no observable coordination trigger; Exec-Planner records `NOT_REQUIRED` with rationale.
- The graph is incomplete or source context is missing.
- Execution or implementation is needed; use Exec-Manager/Exec-Worker.
- Completed nodes need quality review; use QA-Reviewer.

## Dispatch Template

```text
Validate the complete persistent implementation graph before execution.

Context:
- [GRAPH_PATH]
- [REQUEST_OR_DD_PATH]
- [GRAPH_CONTRACT_CONTEXT]

task:
  graph_id: "[GRAPH_ID]"
  graph_revision: [GRAPH_REVISION]
  coordinationTriggers: [CROSS_NODE_CONTRACT | SHARED_WRITE_OR_SCHEMA | MIGRATION_OR_REGISTRY | NONTRIVIAL_ORDERING | UNRESOLVED_OWNERSHIP_CLOSURE]
  rerunReason: "initial | graph-amended | source-changed"
```

## Required Checks

1. Source request or accepted/amended DD is readable and retained in graph provenance.
2. Complete `GRAPH.json` exists at the supplied revision and passes schema validation.
3. Every requirement maps to actionable owned node(s) with acceptance conditions.
4. Dependencies are real, explicit, acyclic, and producer/consumer compatible.
5. Contracts have declared producers, consumers, and materialized actuals where required.
6. Shared ownership, writes, schemas, migrations, and registrations are safe or explicitly ordered.
7. Missing prerequisites, duplicate ownership, contradictions, and unowned gaps are surfaced.
8. Downstream-owned intermediate incompleteness is allowed when a present non-superseded node owns the later integration.

## Routing

| Verdict | Next action |
|---|---|
| `PASS` | Exec-Planner hands the graph to Exec-Manager; claims may begin |
| `AMEND_REQUIRED` | Exec-Planner amends the graph and reruns the gate |
| `DD_CONTRADICTION` | Escalate to DD/R&D owner or user |
| `MISSING_ARTIFACT` | Halt until source/graph context is restored |
| `NEEDS_DECISION` | Halt and ask for an explicit decision |
| `BLOCKED` | Halt and report the input/tooling failure |

`NOT_REQUIRED` is never a gate verdict. The planning owner records it before dispatch when no trigger applies. Exec-Manager only verifies the Planner-owned record or current gate result and never recomputes applicability.
