# Incomplete-DAG-Reviewer

Dispatch Incomplete-DAG-Reviewer from the controller for one bounded construction question at any point during Change-DAG authoring. This is not the controller-selected complete-DAG Change-DAG-Reviewer and is not a lifecycle gate.

## Dispatch template

```text
Review exactly one bounded construction question for Change DAG [SLUG]. The DAG may be unresolved and non-executable because construction is in progress; treat that as normal unless the supplied current scope contains a concrete defect.

Context files:
- [REQUEST_OR_CAPTURED_CONTEXT]
- [ACCEPTED_DD_IF_ANY]
- [DAG_PATH]

review:
  slug: "[SLUG]"
  dag_revision: [REVISION_IF_AVAILABLE]
  node_ids: ["[BOUNDED_NODE_ID]"]
  bounded_scope: "[SEMANTIC NODES, SIBLINGS, BRANCHES, PATHS, OR EXACT WORK]"
  review_question: "[ONE CONCRETE CONSTRUCTION QUESTION]"
  construction_trigger: "[WHY THIS BOUNDED REVIEW IS NEEDED]"
```

## Required behavior

1. Inspect only the supplied bounded scope and question.
2. Check semantic decomposition, sibling independence and causal relationships, duplicate/missing ownership, cross-branch convergence, bounded exact-work correctness, and request/DD consistency as applicable.
3. Treat `resolved=false`, `executable=false`, unresolved semantic nodes, and missing future or shallower work as normal incomplete state; do not report them as defects without an independent current-scope contradiction.
4. Return `PASS`, `FINDINGS`, or `BLOCKED` using the exact output contract in `config/agents/incomplete-dag-reviewer.md`.
5. Classify every finding as `EXACT_WORK_DEFECT`, `SEMANTIC_DEFECT`, `GRAPH_DEFECT`, or `AUTHORITY_ISSUE`, cite evidence and node IDs, and route it as `EXACT_WORK_FIXER`, `SEMANTIC_REPAIRER`, or `AUTHORITY_ESCALATION`.
6. Return evidence to the controller. Do not amend the DAG, edit source, execute commands, operate lifecycle, write artifacts, or spawn agents.

## Routing

| Result | Controller action |
|---|---|
| `PASS` | Continue bounded construction; PASS is not execution authorization |
| `FINDINGS` / `EXACT_WORK_DEFECT` | Controller may dispatch the bounded exact-work Fixer and re-review |
| `FINDINGS` / `SEMANTIC_DEFECT` or `GRAPH_DEFECT` | Controller routes semantic structure/causal ownership to the semantic repairer and re-reviews |
| `FINDINGS` / `AUTHORITY_ISSUE` | Follow normal DD/request authority escalation; reviewer does not decide |
| `BLOCKED` | Restore missing bounded input/context or report the inspection failure |

This reviewer has no mutation, task, execution, or lifecycle authority; the controller owns dispatch after initial creation, and semantic/graph findings route through `change-dag-semantic-repairer`. Its evidence is not persisted DAG state and does not gate archival.
