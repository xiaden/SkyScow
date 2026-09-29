# Change-DAG-Reviewer
Dispatch Change-DAG-Reviewer as Nyx's dynamically selected, independent, read-only final reviewer for a completed Change DAG when observable coordination or authority conditions justify an execution-safety judgment.

## When to Dispatch

- A completed, resolved, executable DAG has an observable trigger such as cross-node shared writes/schemas/migrations/registries, nontrivial behavior-changing ordering, migration scope, shared semantic convergence, incompatible proposals, request/DD ambiguity, recovery risk, or explicit user request.
- A materially changed completed DAG or accepted DD/source context creates a new observable reason for independent final review; Nyx may reselect review before execution or during recovery.

**Do NOT dispatch when:**
- The DAG has no observable coordination risk; record the review outcome with rationale without a gate dispatch.
- Required DAG/source context for the requested bounded scope is missing.
- Execution or implementation is needed; Nyx controls Change DAG lifecycle directly.
- Completed work needs quality review; use QA-Reviewer.

## Dispatch Template

```text
Review the completed Change DAG [SLUG] for safe-to-run execution consequences. The supplied scope and trigger define the question; do not turn the review into a perfection gate or post-execution QA.

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
2. The supplied `DAG.json` exists at the revision and passes `dag_validate` with `resolved=true` and `executable=true`; incomplete or unresolved authoring state is not a final-review success context.
3. Review the complete supplied DAG, `bounded_scope`, and `review_question`; assess semantic sufficiency, exact-work compatibility, DD consistency, or the combined complete DAG according to `review_kind`.
4. For `COMBINED`, inspect the complete DAG's semantic sufficiency, exact work, nesting/order, run-barrier legality, and DD consistency without imposing perfection.
5. Surface only material execution consequences: invalid lower assumptions/dependencies, mechanical incoherence, dangerous destructive/irreversible behavior, material request/DD contradiction, materially worse safety/repairability, or bounded defects safely repairable after execution.
6. Every finding includes an execution disposition, category, evidence, and route guidance. Do not persist a verdict or lifecycle decision.

## Routing

| Verdict | Next action |
|---|---|
| `PASS` / `ALLOW` | Return external evidence; the controller may consider execution, but this is not persisted lifecycle authorization |
| `FINDINGS` / `ALLOW_WITH_FOLLOWUP` | Return the bounded repairable finding and route it to the named post-execution owner |
| `FINDINGS` / `BLOCK_RUN` | Do not start execution; route exact-work defects to Change-DAG-Fixer, semantic/graph defects to Change-DAG-Author, authority issues to DD/R&D owner or user, and safety/repairability issues to the controller/owner |
| `DD_CONTRADICTION` | Normally `BLOCK_RUN`; escalate to DD/R&D owner or user |
| `MISSING_ARTIFACT` | `BLOCK_RUN` until source/DAG/completion context is restored |
| `NEEDS_DECISION` | `BLOCK_RUN` and ask for an explicit decision |
| `BLOCKED` | `BLOCK_RUN`; halt and report the input/tooling or completion-verification failure |

The reviewer is read-only (`dag_show`, `dag_preview`, `dag_validate`). It remains independent and Nyx-selected, never spawns another agent, mutates, executes, or controls lifecycle. A review verdict is external evidence consumed by the controller; it is never stored in Change DAG or execution state, does not gate archival, and does not create a mandatory checkpoint.
