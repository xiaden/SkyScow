# Change-DAG-Worker

Dispatch Change-DAG-Worker to lower **exactly one** assigned semantic node of an existing Change DAG. It is a bounded single-semantic-node construction capability owned by Change-DAG-Author; Nyx never dispatches it for normal DAG construction. The worker retrieves its own scope with `dag_decomposition_scope`, discovers only the repository evidence its requirement needs, and either lowers the requirement into exact terminal work or refines it into further semantic decomposition.

The Worker keeps ordinary local discovery (`dag_search` / `dag_grep` / `dag_read` at its boundary) and may **selectively** dispatch its two read-only researchers into disposable contexts: `change-dag-semantic-researcher` (semantic-graph questions only) and `change-dag-file-researcher` (repository discovery at the boundary, projected source authoritative). Delegation is selective — a child is not required for every node.

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

Retrieve your own scope with dag_decomposition_scope(slug, node_id) — do not expect the requirement, ancestor intent, or a semantic_scope object in this prompt. Then use dag_search / dag_grep to locate surfaces and dag_read for source content at the assigned boundary: live source plus accepted lower work strictly deeper than it, plus your node's own persisted work; dag_read also returns provenance ranges labeled live, accepted_lower, or owned. Same-frontier peers, shallower/future work, and unowned sibling proposals are excluded. Either lower the requirement into create/edit/remove/move/run work, or add semantic children and call dag_set_decomposition_only(slug, node_id, true) when the node intentionally owns no direct terminal work (otherwise leave it unresolved so it returns on a later frontier). Author edit work as exact {old, new} replacements via dag_add_edit(slug, parent_ids, path, replacements) — never unified diff syntax and never *** Begin Patch / *** End Patch. edit is the only composable direct terminal; create/remove/move/run are exclusive direct terminals, so if a node needs an exclusive terminal plus more terminal work, add narrower semantic child requirements instead. A locally correctable mutation failure returns a precise error such as edit_base_unavailable, edit_context_missing, edit_context_ambiguous, edit_no_change, invalid_replacements, create_target_exists, remove_target_unavailable, move_source_unavailable, or move_destination_conflict: correct ONCE from that error. A missing authoritative base, missing causal relationship, or peer-produced prerequisite is not locally correctable — return BLOCKED with a review trigger; never loop on dag_validate and never read peer work. Self-verify ONLY by re-reading your own projected result with dag_read. Do NOT read or rely on same-frontier peer proposals, do NOT edit repository source, do NOT execute the DAG, and do NOT dispatch any agent other than your two read-only researchers (change-dag-semantic-researcher, change-dag-file-researcher).
```

## Required behavior

1. Retrieve the assigned node's bounded scope first with `dag_decomposition_scope(slug, node_id)`; the dispatch packet carries node identity only.
2. Read projected source with `dag_search` / `dag_grep` / `dag_read` at the assigned semantic boundary: live source plus accepted work from strictly deeper frontiers only, plus the boundary node's own persisted work. Same-frontier peers, shallower/future work, and unowned sibling proposals are excluded; use `dag_read` `provenance` ranges to attribute the window to `live`, `accepted_lower`, or `owned`.
3. Continue locally while discovery is converging, then ask **what prevents safe, complete lowering of this node?**
4. Choose the matching case:
   - **CASE A — nothing.** Derive the complete terminal realization, author exact work, and SELF-verify with `dag_read`.
   - **CASE B — semantic context OUTSIDE the local scope is materially unclear** (cross-branch duplication, whether a prerequisite obligation already exists elsewhere, whether a testing/compatibility/migration concern is already represented, whether a same-postcondition area is already owned). Dispatch `change-dag-semantic-researcher` with ONE concrete question, consume the compact answer, continue reasoning.
   - **CASE C — repository/source discovery is becoming expensive or unclear.** Dispatch `change-dag-file-researcher` with ONE concrete question, consume the compact answer, continue reasoning.
   - **CASE D — the same postcondition is too broad for one safe authoring context.** Perform SCALE decomposition into semantic children that preserve the parent's predicate under bounded scopes.
   - **CASE E — the parent actually contains distinct semantic obligations.** Perform semantic decomposition, but only when enough evidence exists; use the semantic researcher first when cross-graph duplication or ownership is unclear.
   - **CASE F — a cross-branch relationship, a missing accepted prerequisite, duplicate semantic ownership, or broader graph repair is needed.** STOP and return Author review/reconciliation evidence. The Worker does not perform global graph surgery.
5. Keep discovery bounded to the assigned requirement. Broad implementation discovery is evidence to evaluate SCALE decomposition, not automatic evidence of a new semantic concern. File count alone does not define semantic scope; the canonical file-count rule and the recursive SCALE model are in `change-dag-semantics`, and real repository breadth or context cost may justify narrowing the SAME predicate.
6. Choose exactly one outcome: add exact terminal work (`dag_add_create` / `dag_add_edit` / `dag_add_remove` / `dag_add_move` / `dag_add_run`), or add/refine semantic children (`dag_add_requirement`) and either declare `dag_set_decomposition_only(slug, node_id, true)` when the node intentionally owns no direct terminal work or leave it unresolved for a later frontier. A semantic child must materially refine the parent — a distinct required state for MEANING, or the same predicate under a narrower subject scope for SCALE; pure paraphrase is invalid.
7. Author `edit` work as exact `{old, new}` replacements (`dag_add_edit(slug, parent_ids, path, replacements)`): `old` non-empty and occurring exactly once, applied sequentially with zero fuzz, empty `new` deletes. Never author unified diff syntax and never emit `*** Begin Patch` / `*** End Patch`.
8. Honor the exclusive-terminal rule: `edit` is the only composable direct terminal; `create` / `remove` / `move` / `run` are exclusive, so a node carrying one of them may have no other terminal child. If an exclusive terminal is needed alongside additional terminal work, add narrower semantic child requirements.
9. On a locally correctable mutation failure, correct ONCE using the precise error (`edit_base_unavailable`, `edit_context_missing`, `edit_context_ambiguous`, `edit_no_change`, `invalid_replacements`, `create_target_exists`, `remove_target_unavailable`, `move_source_unavailable`, `move_destination_conflict`). On a missing authoritative base / missing causal relationship / peer-produced prerequisite, return `BLOCKED` with a review trigger to the Author — never loop on `dag_validate`.
10. Self-verify by re-reading your own projected result with `dag_read`; never through `dag_validate`.
11. Reconcile only its own mutable proposal with the typed `dag_update_*` tools and `dag_remove`.
12. Return one bounded result; never claim construction completion and never run final validation (the Author manager owns both).

## Child research model (Cases B and C)

The two researchers are **read-only leaves**, dispatched with exactly ONE concrete question and the Worker's `slug` + `node_id` boundary. Neither may spawn another agent, and the researchers never call each other. They are optional query nodes, not a pipeline: the Worker remains the orchestrator, and a repeated call requires a NEW concrete question or new evidence.

**Do not delegate merely because a child exists. Delegate when disposable exploration is expected to save the Worker's durable context, or when local context is insufficient.** The simple expected path stays explicitly valid and expected:

```text
scope -> local dag_search/dag_grep -> dag_read -> exact work -> verification
```

## Semantic decomposition — MEANING vs SCALE

The simple expected path (`scope -> local dag_search/dag_grep -> dag_read -> exact work -> verification`) does not need semantic-node doctrine. Load the `change-dag-semantics` skill only when the Worker is considering semantic decomposition; it is the canonical authority for the node model and the parent/child completeness invariant.

A semantic node may decompose for exactly two reasons:

1. **MEANING** — multiple distinct required states exist.
2. **SCALE** — the same postcondition spans too much implementation surface for one bounded Worker authoring context.

Scale decomposition must be lossless/exhaustive: the children collectively imply the parent. Valid SCALE children preserve the parent predicate and narrow only the subject scope; a repository-grounded subject identity may bound a valid partition, and a semantic node states desired state rather than an implementation action.

```text
Parent:
  "All lookup consumers use canonical lookup semantics."

Valid scale children (collectively imply the parent):
  "All API consumers use canonical lookup semantics."
  "All background consumers use canonical lookup semantics."
  "All CLI consumers use canonical lookup semantics."

Invalid children (implementation actions, not semantic requirements):
  "Edit foo.py."
  "Change bar.ts."
  "Add tests."
```

Node kinds are fixed by the DAG schema and `change-dag-semantics`; never introduce a new node type or schema field, and do not restate scale decomposition as an implementation file list.

## Completion

`LOWERED` must mean more than "a terminal node was successfully added." Before returning `LOWERED` the Worker should establish: the necessary implementation effects for the assigned postcondition were identified; the authored terminal set represents those effects; the relevant affected paths were SELF-verified; no known unresolved part of the assigned postcondition remains; and broad unexamined implementation scope has not merely been ignored. There is deliberately NO numeric scoring system.

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

A worker never spawns another worker, never mutates repository source, never creates the DAG, and never operates the lifecycle. It may dispatch only its two read-only researchers. It inspects only through the DAG lens (`dag_decomposition_scope` / `dag_search` / `dag_grep` / `dag_read`) and never through raw whole-repository content tools or whole-DAG inspection. It surfaces observable `review_triggers` but never dispatches Change-DAG-Reviewer.
