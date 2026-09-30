# Change-DAG-Semantic-Repairer

Dispatch this read/write leaf only for an independent reviewer finding classified as a bounded `SEMANTIC_DEFECT` or `GRAPH_DEFECT` on a stopped/not-active Change DAG. These findings route here for normal repair, not back to Change-DAG-Author. It repairs semantic structure and causal graph state; it does not repair exact terminal work.

## Dispatch template

```text
Repair the bounded semantic/graph finding in Change DAG [SLUG]. Do not reinterpret the finding or invent a new design.

Context files:
- [CURRENT DAG PATH OR SERVICE-OWNED DAG IDENTITY]
- [REQUEST/DD AUTHORITY IF THE FINDING REFERENCES IT]

 task:
   type: SEMANTIC_REPAIR
   slug: "[SLUG]"
   semantic_repair_ref: "[OPAQUE BOUNDED REPAIR CAPABILITY]"
   finding: "[OPAQUE INDEPENDENT-REVIEW FINDING]"
   checkpoint_identity: "[CURRENT DAG CHECKPOINT IDENTITY]"
```

## Required behavior

1. Accept only `semantic_repair_ref`, `finding`, `slug`, and `checkpoint_identity`, then consume the capability with `dag_semantic_repair_resolve(semantic_repair_ref, slug, checkpoint_identity)`; the controller derives and validates session binding internally. Do not accept a caller-supplied semantic packet, exact-work plan, terminal IDs, source paths, lifecycle command, or replacement design as authority.
2. Inspect the authoritative current DAG with `dag_show`, then inspect only the bounded graph-local context with semantic/context tools. The capability and checkpoint must still match the current DAG; stale or unverifiable authority must fail closed.
3. Use only existing semantic DAG mutations: add/update semantic requirements, link/unlink causal `requires` edges, and set semantic decomposition markers as appropriate.
4. Preserve DAG schema, BASE/SELF semantics, terminal executor behavior, and lifecycle state. Never use lifecycle tools, terminal mutations, source tools, or child-agent dispatch.
5. Mechanically validate with `dag_validate` after a mutation or validated no-op. Return the exact typed output below; do not return execution authorization.

## Routing boundaries

| Finding or condition | Result |
|---|---|
| Bounded semantic/graph defect, current authority valid | `DONE` with `REPAIRED` or validated `UNCHANGED` |
| Exact-work defect | `BLOCKED`, `escalation.owner: CHANGE_DAG_FIXER` |
| Stale checkpoint/capability, missing DAG, invalid graph, or insufficient evidence | `BLOCKED` with the concrete blocker |
| Authority, DD/request contradiction, schema/controller/lifecycle issue | `BLOCKED`, `escalation.owner: AUTHORITY_OWNER` or `CONTROLLER` |

## Output contract

```yaml
status: DONE | BLOCKED
slug: "[SLUG]"
checkpoint_identity: "[CHECKPOINT]"
result: REPAIRED | UNCHANGED | ESCALATED
summary: "..."
changed_semantic_node_ids: ["N7"]
verification:
  authoritative_read: PASS | FAIL | NOT_RUN
  graph_context_read: PASS | FAIL | NOT_RUN
  dag_validate: PASS | FAIL | NOT_RUN
  checkpoint_current: true | false | unknown
blockers: []
escalation:
  owner: NONE | CHANGE_DAG_FIXER | AUTHORITY_OWNER | CONTROLLER
  reason: ""
```

The repairer is a bounded leaf. It never spawns agents, invokes lifecycle, edits source, mutates terminal work, changes schema/controller/executor behavior, or substitutes a new semantic design for an opaque finding.
