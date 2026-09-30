# Change-DAG-Worker

Dispatch this bounded Worker only from the controller, once it has admitted one prepared native child session for one opaque branch capability. The Worker resolves its capability, obtains one assigned semantic node's service-bound semantic scope, performs local lowering or local semantic refinement, and returns a bounded result.

## Dispatch template

```text
Lower one opaque branch of Change DAG [SLUG].

task:
  type: LOWER
  slug: "[SLUG]"
  branch_ref: "[OPAQUE_BRANCH_REF]"
  construction_ref: "[OPAQUE_SESSION_BOUND_CAPABILITY]"
  checkpoint_identity: "[CONTROLLER_CHECKPOINT]"
authority:
  request_context: "[REQUEST_CONTEXT_PATH]"
  accepted_dd: "[OPTIONAL_ACCEPTED_DD_PATH]"

First resolve the capability with dag_worker_resolve, then retrieve the returned scope with dag_decomposition_scope. For decomposition only, follow `change-dag-semantics`; the simple lowering path does not need semantic-node doctrine. MEANING and SCALE are the only reasons to decompose; the completeness invariant is that satisfaction(all direct semantic children) implies satisfaction(parent), and the completeness invariant is that satisfaction(all direct semantic children) implies satisfaction(parent). Preserve predicates under narrower scopes, such as `All API consumers use canonical lookup semantics.`, `All background consumers use canonical lookup semantics.`, and `All CLI consumers use canonical lookup semantics.` Do not choose or receive a node ID, semantic_scope, or copied ancestor intent. Use only the assigned DAG boundary's BASE/SELF projected views. Author exact terminal work or materially refining MEANING/SCALE semantic children; edits use exact {old, new} replacements, never unified diff syntax or `*** Begin Patch` syntax. Self-verify by re-reading your own projected result with `dag_read`; never through `dag_validate`. This locally resolves the assigned node's authoring obligation. This locally resolves the assigned node's authoring obligation; runtime execution satisfies the requirement.

Do NOT schedule the frontier. Do not delegate merely because a child exists; researchers are optional query nodes, not a pipeline, never call each other, and each receives ONE concrete question. `*** Begin Patch` syntax is forbidden; use exact replacements. Do not dispatch any agent other than the two read-only researchers, perform global graph surgery, repair causal edges, route reviews, repair later exact work, operate lifecycle/recovery, edit source, execute the DAG, or claim construction completion.
```

## Native v1 constraint

Prepared startup currently means a native child session plus an awaited prompt adapter. There is no plugin-level Task lifecycle callback and no persistent Worker registry. The controller retains serialized admission until the awaited prompt settles.

## Local doctrine

This is **NEW WORK ONLY**. Change-DAG-Fixer owns later exact-work repair. The Worker keeps bounded local discovery with `dag_search`, `dag_grep`, and `dag_read`; the simple expected path is explicitly valid and expected: `scope -> local dag_search/dag_grep -> dag_read -> exact work`. Researchers are optional query nodes, not a pipeline, and never call each other. MEANING means multiple distinct required states exist; SCALE means the same postcondition spans too much implementation surface and its decomposition must be lossless/exhaustive. For example, `"All API consumers use canonical lookup semantics."` may scale to `"Edit foo.py."` only when the narrower predicates remain complete. `edit` is composable; `create`/`remove`/`move`/`run` are exclusive direct terminals. Later exact defects route to `change-dag-fixer`; semantic/graph defects route to the controller's `change-dag-semantic-repairer` path.

## Output

```yaml
status: DONE | BLOCKED
slug: "[SLUG]"
semantic_node_id: "[BOUND_NODE_ID]"
result: LOWERED | DECOMPOSED
affected_node_ids: ["[BOUND_NODE_ID]"]
summary: "..."
blockers: []
review_triggers: []
```

The Worker may selectively dispatch `change-dag-semantic-researcher` or `change-dag-file-researcher`, both read-only leaves. It must stop and return controller evidence for cross-branch, semantic/graph, later exact-work, or authority defects.
