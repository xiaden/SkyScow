# Change-DAG-Reviewer

Dispatch Change-DAG-Reviewer as the read-only semantic and exact-work review for a complete Change DAG before execution.

## When to Dispatch

- Change-DAG-Author has created or amended a complete Change DAG with cross-node shared writes/schemas/migrations/registries, nontrivial ordering, migration scope, or unresolved ownership.
- A reviewed DAG is amended or its accepted DD/source changes; rerun review before execution.

**Do NOT dispatch when:**
- The DAG has no observable coordination risk; record the review outcome with rationale without a gate dispatch.
- The DAG is incomplete or source context is missing.
- Execution or implementation is needed; use Change-DAG-Runner.
- Completed work needs quality review; use QA-Reviewer.

## Dispatch Template

```text
Review the complete Change DAG [SLUG] before execution.

Context:
- [DAG_PATH]
- [REQUEST_OR_DD_PATH]
- [DAG_CONTRACT_CONTEXT]

task:
  slug: "[SLUG]"
  dag_revision: [DAG_REVISION]
  coordinationTriggers: [CROSS_NODE_SHARED_WRITE | SHARED_SCHEMA | MIGRATION_OR_REGISTRY | NONTRIVIAL_ORDERING | UNRESOLVED_OWNERSHIP]
  rerunReason: "initial | dag-amended | source-changed"
```

## Required Checks

1. Source request or accepted/amended DD is readable and retained in DAG provenance.
2. Complete `DAG.json` exists at the supplied revision and passes `dag_validate`.
3. Semantic sufficiency and minimality: every requirement maps to an owned semantic node; no pure paraphrase/restatement layer.
4. Every semantic leaf is either terminal exact work or an explicit unresolved leaf.
5. Nesting/order constraints are expressed structurally, including run-barrier legality (a run child is the only non-semantic child of its parent).
6. Exact work is valid against live source plus applicable accepted lower DAG patches; overlapping work is compatible or explicitly ordered.
7. Missing prerequisites, duplicate ownership, contradictions, and unowned gaps are surfaced.
8. Downstream-owned intermediate incompleteness is allowed when a present, non-superseded node owns the later integration.

## Routing

| Verdict | Next action |
|---|---|
| `PASS` | Hand the DAG to Change-DAG-Runner; execution may begin |
| `AMEND_REQUIRED` | Change-DAG-Author amends the DAG (stopped/not active) and review reruns |
| `DD_CONTRADICTION` | Escalate to DD/R&D owner or user |
| `MISSING_ARTIFACT` | Halt until source/DAG context is restored |
| `NEEDS_DECISION` | Halt and ask for an explicit decision |
| `BLOCKED` | Halt and report the input/tooling failure |

The reviewer is read-only (`dag_show`, `dag_preview`, `dag_validate`). A review verdict is an external result consumed by the runner; it is not stored in Change DAG execution state.
