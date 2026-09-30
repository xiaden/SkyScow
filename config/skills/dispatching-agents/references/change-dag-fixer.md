# Change-DAG-Fixer

Dispatch Change-DAG-Fixer only for a **known defect in existing mutable terminal work** where semantic intent and the `requires` graph remain unchanged.

## When to Dispatch

- A stopped/not-active Change DAG has concrete defect evidence against one or more mutable terminal nodes.
- The repair is bounded to the supplied semantic node, terminal node IDs, paths, and invariant.

Do not dispatch for semantic decomposition, missing requirements, `requires` repair, new terminal work, source edits, lifecycle operations, execution, or independent review. Those concerns escalate through the controller to the semantic repairer or authority owner.

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
repair_ref: "[OPAQUE NYX-ISSUED REPAIR CAPABILITY]"
checkpoint_identity: "[CURRENT DAG CHECKPOINT IDENTITY]"
authority:
   request_context: "[OPTIONAL REQUEST CONTEXT]"
  accepted_dd: "[OPTIONAL ACCEPTED DD]"
```

## Required behavior

1. Read only the supplied projected source and bounded DAG-lensed context with `dag_read`, `dag_grep`, and `dag_search`.
2. Resolve the supplied `repair_ref` through `dag_fixer_mutate`; do not accept a caller-supplied grant scope as authority.
2. Confirm the target terminal work is mutable and the defect is concrete.
3. Apply only the smallest authorized `dag_fixer_mutate` correction (`operation: update` or `remove`) under the Nyx-issued, controller-routed repair grant. The typed `dag_update_create`, `dag_update_edit`, `dag_update_remove`, `dag_update_move`, `dag_update_run`, and `dag_remove` tools are not the fixer's; for edits, pass exact structured replacements through `dag_fixer_mutate`; never hand-author unified diff syntax.
4. Re-read the affected result with `dag_read` and report changed terminal IDs and paths.
5. Preserve semantic requirements and every `requires` edge. If semantic/graph change, new terminal work, cross-node coordination, immutable work, or insufficient evidence is required, stop and escalate through the controller.

The fixer has no source write/edit/shell capability; Change-DAG-Author is not a repair route after initial creation, and the controller is the only repair router to `change-dag-semantic-repairer` for semantic/graph defects. The fixer has no semantic graph mutation tools, no whole-DAG create/show/preview/validate/frontier tools, no lifecycle/execution tools, and no child-agent capability.

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
  owner: NONE | CONTROLLER
  reason: ""
review_triggers: []
```

`DONE` means the bounded mutable terminal repair (or verified no-op) completed and projected readback ran. `BLOCKED` means the evidence, authority, mutability, or bounded semantic scope was insufficient; semantic and graph changes always route through the controller to the semantic repairer. The fixer never dispatches a reviewer or another agent.
