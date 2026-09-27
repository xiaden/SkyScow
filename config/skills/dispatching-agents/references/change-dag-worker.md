# Change-DAG-Worker

Dispatch Change-DAG-Worker to lower **exactly one** assigned semantic node of an existing Change DAG. It is a bounded leaf construction capability owned by Change-DAG-Author; Nyx never dispatches it for normal DAG construction. The worker discovers only the repository evidence its requirement needs and either lowers the requirement into exact terminal work or refines it into further semantic decomposition.

## When to Dispatch

- **From Change-DAG-Author only**, once per semantic node selected from the current construction frontier, when the node's requirement must be lowered into exact work or reconciled.
- A worker returns `DECOMPOSED` when it introduces deeper semantic requirements; the manager then recomputes the construction frontier.

**Do NOT dispatch when:**
- You are Nyx or any agent other than Change-DAG-Author: worker dispatch is internal to construction.
- Several unrelated semantic nodes are being bundled into one prompt: one worker invocation equals one semantic node.
- A whole frontier or whole DAG is being handed over as an unconstrained task.
- Execution, source mutation, or independent review is needed; the worker does none of these.

## Dispatch Template

```text
Lower one assigned semantic node of Change DAG [SLUG].

task:
  type: LOWER | RECONCILE
  slug: "[SLUG]"
semantic_scope:
  node_id: "[NODE_ID]"
  requirement: "[EXACT SEMANTIC POSTCONDITION]"
  ancestor_intent:
    - "[BOUNDED NECESSARY PARENT INTENT]"
authority:
  request_context: "artifacts/requests/CTX_....md"
  accepted_dd: "[OPTIONAL ACCEPTED DD PATH]"
reason: "[WHY THIS NODE IS BEING LOWERED OR RECONCILED]"

Read the assigned node and its accepted lower work with frontier-bounded dag_preview(path=..., node_id=[NODE_ID]); read only the live source and repository surfaces the requirement needs. Lower the requirement into create/edit/remove/move/run work or refine it into further semantic requirements. Do NOT read or rely on same-frontier peer proposals, do NOT edit repository source, do NOT dispatch other agents, and do NOT execute the DAG.
```

## Required behavior

1. Read the assigned semantic node and its frontier-bounded planned-change context (`dag_preview(path=..., node_id=[NODE_ID])`): live source plus accepted work from strictly deeper frontiers only.
2. Keep discovery bounded to the assigned requirement; when discovery expands materially, decompose the requirement instead of loading a larger repository slice.
3. Either add exact terminal work (`dag_add_create` / `dag_add_edit` / `dag_add_remove` / `dag_add_move` / `dag_add_run`) or add/refine semantic children (`dag_add_requirement`). A semantic child must materially narrow the parent; pure paraphrase is invalid.
4. Reconcile only its own mutable proposal with the typed `dag_update_*` tools and `dag_remove`.
5. Return one bounded result; never claim construction completion and never run final validation (the Author manager owns both).

## Outcomes

| Result | Meaning |
|---|---|
| `LOWERED` | Exact mechanical work now satisfies the assigned requirement. |
| `DECOMPOSED` | Deeper semantic requirements were added; the manager must recompute the frontier. |
| `RECONCILED` | Mutable work in the assigned scope was corrected. |
| `NO_DIRECT_WORK` | The requirement is fully owned by its decomposed children; no direct mechanical work is needed. |
| `BLOCKED` | A missing authority/source/decision/tooling condition prevents completion. |

## Expected output

```yaml
status: DONE | BLOCKED
slug: "[SLUG]"
semantic_node_id: "[NODE_ID]"
result: LOWERED | DECOMPOSED | RECONCILED | NO_DIRECT_WORK
affected_node_ids: ["[NODE_ID]"]
summary: "..."
blockers: []
review_triggers: []
```

A worker never spawns another worker, never mutates repository source, never creates the DAG, and never operates the lifecycle. It surfaces observable `review_triggers` but never dispatches Change-DAG-Reviewer.
