# Change-DAG-Worker

Dispatch Change-DAG-Worker to lower **exactly one** assigned semantic node of an existing Change DAG. It is a bounded leaf construction capability owned by Change-DAG-Author; Nyx never dispatches it for normal DAG construction. The worker retrieves its own scope with `dag_decomposition_scope`, discovers only the repository evidence its requirement needs, and either lowers the requirement into exact terminal work or refines it into further semantic decomposition.

## When to Dispatch

- **From Change-DAG-Author only**, once per semantic node returned by `dag_decomposition_frontier`, when the node's requirement must be lowered into exact work or reconciled.
- A worker returns `DECOMPOSED` when it introduces deeper semantic requirements; the manager then re-queries `dag_decomposition_frontier`.

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
  node_id: "[NODE_ID]"
authority:
  request_context: "artifacts/requests/CTX_....md"
  accepted_dd: "[OPTIONAL ACCEPTED DD PATH]"

Retrieve your own scope with dag_decomposition_scope(slug, node_id) — do not expect the requirement, ancestor intent, or a semantic_scope object in this prompt. Then use dag_read, dag_grep, and dag_search for source content at the assigned boundary: live source plus accepted lower work strictly deeper than it. Use frontier-bounded dag_preview(path=..., node_id=[NODE_ID]) only for compiled operation/conflict metadata. Same-frontier peers, the assigned node's own proposal, and shallower/future work are excluded. Either lower the requirement into create/edit/remove/move/run work, or add semantic children and call dag_set_decomposition_only(slug, node_id, true) when the node intentionally owns no direct terminal work (otherwise leave it unresolved so it returns on a later frontier). Do NOT read or rely on same-frontier peer proposals, do NOT edit repository source, do NOT dispatch other agents, and do NOT execute the DAG.
```

## Required behavior

1. Retrieve the assigned node's bounded scope first with `dag_decomposition_scope(slug, node_id)`; the dispatch packet carries node identity only.
2. Read projected source with dag_read, dag_grep, and dag_search at the assigned semantic boundary: live source plus accepted work from strictly deeper frontiers only. Use dag_preview(path=..., node_id=[NODE_ID]) only for compiled operation/conflict metadata.
3. Keep discovery bounded to the assigned requirement; when discovery expands materially, decompose the requirement instead of loading a larger repository slice.
4. Choose exactly one outcome: add exact terminal work (`dag_add_create` / `dag_add_edit` / `dag_add_remove` / `dag_add_move` / `dag_add_run`), or add/refine semantic children (`dag_add_requirement`) and either declare `dag_set_decomposition_only(slug, node_id, true)` when the node intentionally owns no direct terminal work or leave it unresolved for a later frontier. A semantic child must materially narrow the parent; pure paraphrase is invalid.
5. Reconcile only its own mutable proposal with the typed `dag_update_*` tools and `dag_remove`.
6. Return one bounded result; never claim construction completion and never run final validation (the Author manager owns both).

## Outcomes

| Result | Meaning |
|---|---|
| `LOWERED` | Exact mechanical work now locally resolves the assigned node's authoring obligation. |
| `DECOMPOSED` | Deeper semantic requirements were added; the node is either marked `decomposition_only` or left unresolved for a later frontier, and the manager re-queries the frontier. |
| `RECONCILED` | Mutable work in the assigned scope was corrected. |
| `BLOCKED` | A missing authority/source/decision/tooling condition prevents completion. |

## Expected output

```yaml
status: DONE | BLOCKED
slug: "[SLUG]"
semantic_node_id: "[NODE_ID]"
result: LOWERED | DECOMPOSED | RECONCILED
affected_node_ids: ["[NODE_ID]"]
summary: "..."
blockers: []
review_triggers: []
```

A worker never spawns another worker, never mutates repository source, never creates the DAG, and never operates the lifecycle. It surfaces observable `review_triggers` but never dispatches Change-DAG-Reviewer.
