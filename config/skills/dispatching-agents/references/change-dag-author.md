# Change-DAG-Author

Dispatch Change-DAG-Author for exactly one initial semantic Change DAG creation from an authoritative request or accepted DD. The Author creates the semantic skeleton, verifies the atomic creation, and hands construction authority to the controller. It exits after that handoff.

## Do not dispatch for

Execution, lifecycle control, frontier motion, Worker dispatch, review routing, reconciliation, exact-work repair, semantic/graph repair, recovery, source mutation, QA, or a single obvious edit that needs no DAG.

## Dispatch template

```text
Create the initial semantic Change DAG [SLUG].

Source context:
- [REQUEST_CONTEXT_PATH]
- [ACCEPTED_DD_PATH if applicable]
- [BOUNDED REPOSITORY FACTS]

Task:
  type: CREATE
  slug: "[SLUG]"
  title: "[TITLE]"

Create exactly one atomic semantic graph with dag_create. Follow `change-dag-semantics` and `file://config/skills/decomposing-design-documents/references/semantic-generation.md`: the graph is a semantic skeleton, not an implementation plan; use postconditions only, derive nodes and edges as separate judgments, and never infer a dependency or independence. Ask “Could B be correctly authored if A's implementation had not yet been proposed or accepted?” before adding `requires`. Do not pre-decompose for Worker context size. Verify the created DAG and return the slug plus a controller handoff.

The controller, not the Author, owns serialized construction motion, service-derived deepest-frontier queries, one prepared native Worker at a time, independent review after every completed frontier, exact-work routing to change-dag-fixer, semantic/graph routing to change-dag-semantic-repairer, authority escalation, and final dag_validate. The controller must not invent semantic requirements, edges, work, or semantic meaning. Native v1 prepared startup is a native child session plus an awaited prompt adapter; there is no plugin-level Task lifecycle callback.

Do NOT query or schedule the frontier, dispatch agents, reconcile or repair any result, recover or execute the DAG, edit repository source, or create another construction artifact.
```

## Required handoff

```yaml
status: DONE | BLOCKED
slug: "[SLUG]"
created: true | false
handoff: CONTROLLER | NONE
summary: "..."
blockers: []
validation:
  schema_valid: true | false
  issues: []
```

The original request/captured context and accepted DD remain authoritative. The Author must not claim construction completion merely because `dag_create` succeeded; it reports creation and authority handoff only.


Follow the canonical semantic model in `change-dag-semantics` and the initial-generation procedure in `file://config/skills/decomposing-design-documents/references/semantic-generation.md`; this doctrine governs the one-shot semantic skeleton only, not controller scheduling authority.