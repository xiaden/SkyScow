# Change-DAG-Author

Dispatch Change-DAG-Author as the construction **manager** for one Change DAG. It owns construction from an accepted request/DD through semantic decomposition, the service-derived decomposition-frontier loop, bounded Change-DAG-Worker dispatch, frontier reconciliation, and final validation. The Change DAG is the single implementation-work authority; new work must not create task plans, `CONTRACTS.md`, or `GRAPH.json` implementation graphs.

## When to Dispatch

- An accepted request or accepted/amended DD requires semantic decomposition and exact work authored as a Change DAG.
- Execution exposes a semantic gap, hidden caller, missing prerequisite, impossible acceptance condition, or missing exact work — amend the DAG while it is stopped/not active.

Do not dispatch for execution, node status changes, source mutation, QA, or a single obvious edit that needs no DAG amendment. Do not dispatch Change-DAG-Worker directly: the Author manager owns worker dispatch internally.

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
  known_scope: [OPTIONAL_BOUNDED_FAILING_SCOPE_IF_ALREADY_KNOWN]

The author is the construction manager: it builds the semantic graph, queries the service-derived decomposition frontier with `dag_decomposition_frontier`, dispatches one bounded Change-DAG-Worker per returned frontier node, reconciles the frontier only when required, validates with dag_validate/dag_show/dag_preview, and returns a construction result. Do not supply a frontier or a semantic-node list; the author queries the DAG service for the frontier and manages internal semantic scopes. Independent Change-DAG-Reviewer review is Nyx-selected from observable triggers; the author surfaces review_triggers but never dispatches the reviewer. The author must not edit repository source and must not execute nodes.

Context partitioning: the author owns internal worker dispatch. Supply overall construction authority and source context; never require the author to receive the whole repository in one session, and never have Nyx calculate or query the frontier or dispatch node workers.
```

## Authoring protocol

1. Gather only materially relevant artifacts/research. Unknown repository facts may select Support-Researcher; accepted migration impact may select PatternEnforcer.
2. Generate the smallest complete **semantic** graph (conditions/postconditions, never implementation actions) and submit it atomically with `dag_create`. Initial semantic construction is not a loop of `dag_add_requirement`.
3. Query the service-derived deepest **decomposition frontier** with `dag_decomposition_frontier` and dispatch one fresh `change-dag-worker` per returned node — concurrently when the nodes are independent. The worker retrieves its own scope with `dag_decomposition_scope(slug, node_id)` and then lowers the requirement into exact terminal work (`dag_add_create` / `dag_add_edit` / `dag_add_remove` / `dag_add_move` / `dag_add_run`) or refines it into further semantic decomposition, reading live source plus applicable accepted lower DAG work through frontier-bounded `dag_preview(path=..., node_id=<this semantic node>)` (strictly deeper accepted work only; same-frontier peers and shallower/future work are excluded). Same-frontier nodes assert authoring independence; if authoring B requires accepted work under A, B must `requires` A rather than being a sibling, and the service infers no missing causal edge.
4. Collect worker results and reconcile the frontier only when results or conflicts require it: incompatible same-file proposals, shared paths, semantic convergence, worker-discovered deeper decomposition, ordering/nesting, and compiler conflicts. When workers introduced deeper semantic requirements, re-query `dag_decomposition_frontier` and descend before proceeding shallower — never track processed nodes in session memory.
5. Correct mutable nodes with the typed `dag_update_*` tools or `dag_remove`; the service owns references, cycle checks, reachability, and IDs. Do not persist a separate frontier/worker registry or proposal artifact — the DAG is the only construction artifact.
6. Run `dag_validate` and inspect with `dag_show` / `dag_preview`. Size context with `context_tokens`/`context_budget` and `config/agent-context-budgets.yaml`; never copy numeric ceilings into the DAG.
7. Surface observable `review_triggers`; never dispatch `change-dag-reviewer`. A reviewer `PASS` is external evidence only and never execution authorization.
8. Stop at a validated DAG. Never edit source, never execute nodes, and never claim execution.

A running/in-progress DAG is immutable; accepted work mutation requires the DAG to be stopped/not active. Any independent review after a correction is Nyx-selected again from observable conditions; no persisted review state or mandatory review checkpoint exists.

## Outcomes

- `DONE`: the construction loop completed, the DAG was reconciled, and final validation ran. It does not authorize execution.
- `BLOCKED`: missing source context, unresolved authority, invalid graph, or unresolved architecture.

## Expected output

```yaml
status: DONE | BLOCKED
summary: "..."
slug: "[SLUG]"
construction:
  complete: true | false
  dispatched_nodes: ["N3", "N7"]   # report only; the frontier service is the progress authority
  blockers: []
validation: {schema_valid: true, executable: true, resolved: true, issues: []}
review_triggers:
  - kind: "..."
    node_ids: ["N7"]
    reason: "..."
```
