# Change-DAG-Author

Dispatch Change-DAG-Author to create or amend a Change DAG. The Change DAG is the single implementation-work authority; new work must not create task plans, `CONTRACTS.md`, or `GRAPH.json` implementation graphs.

## When to Dispatch

- An accepted request or accepted/amended DD requires semantic decomposition and exact work authored as a Change DAG.
- Execution exposes a semantic gap, hidden caller, missing prerequisite, impossible acceptance condition, or missing exact work — amend the DAG while it is stopped/not active.

Do not dispatch for execution, node status changes, source mutation, QA, or a single obvious edit that needs no DAG amendment.

## Dispatch Template

```text
Create or amend a Change DAG [SLUG].

Source context:
- [REQUEST_OR_DD_PATH]
- [REPOSITORY_FACTS]
- [EXISTING_DAG_PATH if AMEND]

Task:
  type: CREATE | AMEND
  slug: "[SLUG]"
  title: "[TITLE]"
  reason: "[REASON]"
  semantic_graph: [CONDITION_POSTCONDITION_NODES]
  semantic_scope: [ASSIGNED_FRONTIER_OR_SINGLE_SEMANTIC_NODE]
  lower_work: [EXACT_CREATE_EDIT_REMOVE_MOVE_RUN_WORK]
  remove_node_ids: []

The author owns construction end-to-end: build the semantic graph, lower exact work from the deepest construction frontier upward, reconcile convergence and conflicts, validate with dag_validate/dag_show/dag_preview, and return node IDs, work applicability, provenance, and blockers. Independent Change-DAG-Reviewer review is optional and controller-selected by observable coordination or authority conditions; it is not required before lowering or before execution. The author must not edit repository source and must not execute nodes.

Context partitioning: dispatch one bounded author invocation per construction
frontier (or single bounded semantic scope). Supply only the assigned semantic
requirement(s), necessary ancestor intent, bounded live-repository evidence, and
applicable accepted lower DAG work — never the whole repository or all prior
branch context. When discovery expands beyond the assigned scope, return a
semantic decomposition recommendation instead of loading more repository.
```

## Authoring protocol

1. Gather only materially relevant artifacts/research. Unknown repository facts may select Support-Researcher; accepted migration impact may select PatternEnforcer.
2. Generate the smallest complete **semantic** graph (conditions/postconditions, never implementation actions) and submit it atomically with `dag_create`. Initial semantic construction is not a loop of `dag_add_requirement`.
3. Lower exact work with `dag_add_create` / `dag_add_edit` / `dag_add_remove` / `dag_add_move` / `dag_add_run`, reading live source plus applicable accepted lower DAG patches via `dag_preview(path)`.
4. Correct mutable nodes with the typed `dag_update_*` tools or `dag_remove`; the service owns references, cycle checks, reachability, and IDs.
5. Run `dag_validate` and inspect with `dag_show` / `dag_preview`. Size context with `context_tokens`/`context_budget` and `config/agent-context-budgets.yaml`; never copy numeric ceilings into the DAG.
6. If the controller selects independent review, provide the bounded node IDs, source context, observable trigger, concrete review question, and `review_kind`; route `AMEND_REQUIRED` findings back into mutable authoring and revalidate. A reviewer `PASS` is external evidence only and never execution authorization.
7. Authoring stops at a validated DAG. It never edits source and never claims or executes nodes.

A running/in-progress DAG is immutable; accepted work mutation requires the DAG to be stopped/not active. Any independent review after a correction is controller-selected again from observable conditions; no persisted review state or mandatory review checkpoint exists.

## Outcomes

- `DONE`: DAG created/amended, schema-valid (and executable when execution is intended), source/work evidence recorded.
- `BLOCKED`: missing source context, unresolved authority, invalid graph, or unresolved architecture.

## Expected output

```yaml
status: DONE | BLOCKED
summary: "..."
slug: "[SLUG]"
revision: 3
artifact: "artifacts/change-dags/pending/[SLUG]/DAG.json"
validation: {schemaValid: true, executable: true, resolved: false}
semanticNodes: ["N1"]
workNodes: ["N7"]
blockers: []
```
