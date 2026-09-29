# Change-DAG-Fixer

Dispatch Change-DAG-Fixer only for a **known defect in existing mutable terminal work** where semantic intent and the `requires` graph remain unchanged.

## When to Dispatch

- A stopped/not-active Change DAG has concrete defect evidence against one or more mutable terminal nodes.
- The repair is bounded to the supplied semantic node, terminal node IDs, paths, and invariant.

Do not dispatch for semantic decomposition, missing requirements, `requires` repair, new terminal work, source edits, lifecycle operations, execution, or independent review. Those concerns escalate to Change-DAG-Author or the controller.

## Dispatch Template

```text
Repair the known terminal-work defect in Change DAG [SLUG].

Context:
- [REQUEST_OR_DD_PATH if applicable]
- [BOUNDED DAG-LENSED SCOPE]
- [CONCRETE DEFECT EVIDENCE]

Task:
  type: REPAIR
  slug: "[SLUG]"
  semantic_node_id: "[SEMANTIC_NODE_ID]"
  terminal_node_ids: ["[TERMINAL_NODE_ID]"]
  bounded_scope:
    paths: ["[PATH]"]
    description: "[ONE BOUNDED TERMINAL REALIZATION]"
  defect:
    evidence: "[OBSERVED DEFECT AND EVIDENCE]"
    expected_invariant: "[SEMANTIC INTENT TO PRESERVE]"
authority:
  request_context: "[OPTIONAL REQUEST CONTEXT]"
  accepted_dd: "[OPTIONAL ACCEPTED DD]"
```

## Required behavior

1. Read only the supplied projected source and bounded DAG-lensed context with `dag_read`, `dag_grep`, and `dag_search`.
2. Confirm the target terminal work is mutable and the defect is concrete.
3. Apply only the smallest typed `dag_update_create`, `dag_update_edit`, `dag_update_remove`, `dag_update_move`, `dag_update_run`, or `dag_remove` correction. For edits, use structured replacements; never hand-author unified diff syntax.
4. Re-read the affected result with `dag_read` and report changed terminal IDs and paths.
5. Preserve semantic requirements and every `requires` edge. If semantic/graph change, new terminal work, cross-node coordination, immutable work, or insufficient evidence is required, stop and escalate to `Change-DAG-Author`.

The fixer has no source write/edit/shell capability, no semantic graph mutation tools, no whole-DAG create/show/preview/validate/frontier tools, no lifecycle/execution tools, and no child-agent capability.

## Expected output

```yaml
status: DONE | BLOCKED
slug: "[SLUG]"
semantic_node_id: "[SEMANTIC_NODE_ID]"
terminal_node_ids: ["[TERMINAL_NODE_ID]"]
result: REPAIRED | UNCHANGED | ESCALATED
summary: "..."
changed_paths: ["[PATH]"]
changed_terminal_node_ids: ["[TERMINAL_NODE_ID]"]
verification:
  projected_readback: PASS | FAIL | NOT_RUN
  semantic_intent_preserved: true | false | unknown
blockers: []
escalation:
  owner: NONE | AUTHOR
  reason: ""
review_triggers: []
```

`DONE` means the bounded mutable terminal repair (or verified no-op) completed and projected readback ran. `BLOCKED` means the evidence, authority, mutability, or bounded semantic scope was insufficient; semantic and graph changes always route to the Author. The fixer never dispatches a reviewer or another agent.
