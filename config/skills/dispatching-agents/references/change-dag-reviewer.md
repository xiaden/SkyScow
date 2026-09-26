# Change-DAG-Reviewer
Dispatch Change-DAG-Reviewer as a dynamically selected, read-only reviewer for a bounded Change DAG scope when observable coordination or authority conditions justify independent judgment.

## When to Dispatch

- Change-DAG-Author is constructing or has amended a DAG with an observable trigger such as cross-node shared writes/schemas/migrations/registries, nontrivial behavior-changing ordering, migration scope, shared semantic convergence, incompatible proposals, request/DD ambiguity, recovery risk, or explicit user request.
- A materially changed DAG or accepted DD/source context creates a new observable reason for independent review; the controller may reselect review before execution or during recovery.

**Do NOT dispatch when:**
- The DAG has no observable coordination risk; record the review outcome with rationale without a gate dispatch.
- Required DAG/source context for the requested bounded scope is missing.
- Execution or implementation is needed; use Change-DAG-Runner.
- Completed work needs quality review; use QA-Reviewer.

## Dispatch Template

```text
Review the requested Change DAG scope [SLUG]. Do not assume a complete-DAG review or a pre-execution gate unless the supplied scope and trigger explicitly require it.

Context:
- [DAG_PATH]
- [REQUEST_OR_DD_PATH]
- [DAG_CONTRACT_CONTEXT]

task:
  slug: "[SLUG]"
  dag_revision: [DAG_REVISION]
  node_ids: ["[BOUNDED_NODE_ID]"]
  bounded_scope: "[PATHS, FRONTIER, OR COMPLETE-DAG SCOPE]"
  review_question: "[CONCRETE INDEPENDENT QUESTION]"
  trigger: "[OBSERVABLE REASON INDEPENDENT JUDGMENT IS JUSTIFIED]"
  review_kind: SEMANTIC | EXACT_WORK | DD_CONSISTENCY | COMBINED
```

## Required Checks

1. Supplied source request or accepted/amended DD is readable and retained in DAG provenance.
2. The supplied `DAG.json` exists at the revision and passes `dag_validate` as mechanical context; a bounded review may occur during mutable authoring or after a complete DAG is assembled.
3. Review only the supplied `node_ids`, `bounded_scope`, and `review_question`; assess semantic sufficiency, exact-work compatibility, DD consistency, or the combined complete DAG according to `review_kind`.
4. For `COMBINED`, inspect the complete DAG's semantic sufficiency, exact work, nesting/order, run-barrier legality, and DD consistency.
5. Surface missing prerequisites, duplicate ownership, contradictions, incompatible overlap, and unowned gaps within the requested scope.
6. Downstream-owned intermediate incompleteness is allowed when a present, non-superseded node owns the later integration.

## Routing

| Verdict | Next action |
|---|---|
| `PASS` | Return external evidence to the controller; it may route to Change-DAG-Runner, but PASS is not execution authorization or a lifecycle transition |
| `AMEND_REQUIRED` | Return the bounded finding to Change-DAG-Author while the DAG is stopped/not active; revalidate and optionally reselect review from current triggers |
| `DD_CONTRADICTION` | Escalate to DD/R&D owner or user |
| `MISSING_ARTIFACT` | Halt until source/DAG context is restored |
| `NEEDS_DECISION` | Halt and ask for an explicit decision |
| `BLOCKED` | Halt and report the input/tooling failure |

The reviewer is read-only (`dag_show`, `dag_preview`, `dag_validate`). A review verdict is external evidence consumed by the controller; it is never stored in Change DAG or execution state, does not gate archival, and does not create a mandatory checkpoint.
