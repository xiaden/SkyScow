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

The author is the construction manager: it builds the semantic graph, queries the service-derived decomposition frontier with `dag_decomposition_frontier`, dispatches at most one bounded Change-DAG-Worker per returned opaque `branch_ref` in each round; the service assigns the concrete semantic node, optionally dispatches Incomplete-DAG-Reviewer during construction, routes known bounded exact-work defects to Change-DAG-Fixer, reconciles the frontier only when required, validates with dag_validate/dag_show/dag_preview, and returns a construction result. Do not supply a frontier or a semantic-node list; the author queries the DAG service for the frontier and manages internal semantic scopes. The final/controller-selected Change-DAG-Reviewer is Nyx-selected from observable triggers; the author never dispatches it. The author must not edit repository source and must not execute nodes.

Context partitioning: the author owns internal worker dispatch. Supply overall construction authority and source context; never require the author to receive the whole repository in one session, and never have Nyx calculate or query the frontier or dispatch node workers.
```

## Authoring protocol

1. Gather only materially relevant artifacts/research. Unknown repository facts may select Support-Researcher; accepted migration impact may select PatternEnforcer.
2. Generate the smallest semantically justified **semantic** graph as an initial skeleton grounded in known correctness/causal structure — obligations stated as postconditions with causal edges derived separately, never implementation actions and never assumed artifacts — following the canonical Author-specific procedure in the `decomposing-design-documents` reference `references/semantic-generation.md`. General semantic-node doctrine (what a semantic node is, MEANING versus SCALE, parent/child completeness, sibling/causal semantics) is the `change-dag-semantics` skill. Do not pre-size nodes for one Worker context or proactively research implementation breadth to predict Worker partitioning; Worker-discovered breadth is refined later by lossless SCALE decomposition, which the Author treats as expected recursive refinement. Submit it atomically with `dag_create`. Initial semantic construction is not a loop of `dag_add_requirement`.
3. Query `dag_decomposition_frontier(slug)` for opaque `branch_ref` entries and dispatch at most one fresh `change-dag-worker` per branch in that round. The packet contains only `slug` and `branch_ref`; the Author does not select a node. The Worker first calls `dag_worker_resolve(slug, branch_ref)`, then uses the returned bound node with `dag_decomposition_scope(slug, node_id)`. Re-query after the batch; another round may consume more work from the same branch.` and then lowers the requirement into exact terminal work (`dag_add_create` / `dag_add_edit` / `dag_add_remove` / `dag_add_move` / `dag_add_run`) or refines it into further semantic decomposition, reading live source plus applicable accepted lower DAG work through `dag_read` / `dag_grep` / `dag_search` at `node_id=<this semantic node>`, which return the boundary's SELF view (strictly deeper accepted work plus the node's own persisted terminal work; same-frontier peers and shallower/future work excluded; `dag_preview` is for compiled metadata; BASE — accepted lower work only — is the internal lens a new mutation is validated against). Branch components are serialized authoring units; same-frontier nodes are not necessarily independently dispatchable; if authoring B requires accepted work under A, B must `requires` A rather than being a sibling, and the service infers no missing causal edge. Direct-terminal composition is a structural obligation you own: `edit` is the only composable direct terminal, while `create` / `remove` / `move` / `run` are exclusive direct terminals, so a node needing an exclusive terminal plus additional terminal work must be decomposed into narrower semantic child requirements rather than given conflicting direct terminals. Edit work is authored as exact `{old, new}` replacements (the service generates the internal unified diff); never hand-author diff syntax.
4. Collect worker results and reconcile the frontier only when results or conflicts require it: incompatible same-file proposals, shared paths, semantic convergence, worker-discovered deeper decomposition, ordering/nesting, and compiler conflicts. A worker `BLOCKED` result is yours to interpret and repair — in particular, a worker reporting `edit_base_unavailable` for a file another branch produces is evidence the graph lacks a causal edge or proper semantic decomposition; do not expose peer work to the worker, add the missing `requires` edge or decompose the producing obligation. When workers introduced deeper semantic requirements, re-query `dag_decomposition_frontier` and descend before proceeding shallower — never track processed nodes in session memory.
5. Correct mutable nodes with the typed `dag_update_*` tools or `dag_remove`; the service owns references, cycle checks, reachability, and IDs. Do not persist a separate frontier/worker registry or proposal artifact — the DAG is the only construction artifact.
6. Run `dag_validate` and inspect with `dag_show` / `dag_preview`. This final whole-DAG validation is yours alone; workers never run it. Size context with `context_tokens`/`context_budget` and `config/agent-context-budgets.yaml`; never copy numeric ceilings into the DAG.
7. Optionally dispatch `incomplete-dag-reviewer` during construction for a bounded question. Route known `EXACT_WORK_DEFECT` findings to `change-dag-fixer`; retain semantic/graph corrections and final validation yourself. Surface observable `review_triggers` for the final/controller-selected `change-dag-reviewer`, which you never dispatch. A reviewer `PASS` is external evidence only and never execution authorization.
8. Stop at a validated DAG. Never edit source, never execute nodes, and never claim execution.

A running/in-progress DAG is immutable; accepted work mutation requires the DAG to be stopped/not active. Incomplete construction review is optional and may lead to either Fixer routing for exact-work defects or Author-owned semantic/graph correction. The final/controller-selected review remains Nyx-owned; no persisted review state or mandatory review checkpoint exists.

## Ownership split and reconciliation evidence

The Author owns the initial semantic skeleton, causal `requires` relationships, global semantic reconciliation, cross-branch convergence, repair when a Worker discovers existing semantic ownership elsewhere, repair of missing causal prerequisites, and final whole-DAG validation. The Worker owns local exact lowering, local semantic refinement, lossless scale decomposition beneath its assigned scope, and selective dispatch of its two read-only researchers. Worker `BLOCKED` results and signals such as `semantic gap`, `duplicate ownership`, `cross-branch relationship`, and `missing prerequisite` are graph-reconciliation evidence, not mechanical instructions.

Adding or removing one causal `requires` edge from an existing semantic parent to an existing semantic or terminal child is Author-only reconciliation, performed one edge at a time with `dag_link_requirement` / `dag_unlink_requirement`. There is intentionally no tool that rewrites an entire `requires` array, and these tools are not Worker tools.

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
