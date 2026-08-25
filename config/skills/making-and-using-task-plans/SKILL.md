---
name: making-and-using-task-plans
description: Create, edit, validate, and execute task plan markdown files for the plan tooling system. Covers format rules, syntax requirements, step writing, annotations, cross-session continuity, and tool integration (plan_read, plan_complete_step, plan_archive). Load when creating or editing files in artifacts/plans/ or when you need to use plan tools.
---

# Making & Using Task Plans

**Purpose:** Produce valid, well-structured task plan markdown files and use the plan tooling system effectively.

This skill merges what were previously two separate skills (`task-plan-syntax` and `task-plans-guide`). The body is a dispatch index; format rules and writing guidance live in reference files loaded on demand.

---

## When to Use

**Load this skill when:**
- Creating a new task plan in `artifacts/plans/pending/`
- Editing or validating an existing plan
- Using plan tools (`plan_read`, `plan_complete_step`, `plan_archive`)
- Splitting a large task into lettered parts
- Reviewing a plan for completeness or cross-session continuity

**Do NOT use this skill when:**
- Decomposing a design document into multiple plans — use `decomposing-design-documents`
- Executing a multi-plan feature — use `feature-execution`
- The task is trivial and won't need cross-session continuity

---

## Reference Dispatch

This skill uses the **decision tree** pattern. The body is a dispatch index; load the reference matching your need:

| You need... | Load | Contains |
|-------------|------|----------|
| Format rules, phase structure, `plan_read` parser constraints, step ID conventions, splitting rules | [Syntax Reference](file:///home/opencode/.config/opencode/skills/making-and-using-task-plans/references/syntax.md) | Template, format rules, parser rejection rules, step writing, splitting large tasks, validation |
| Step annotations, best practices, cross-session continuity, common mistakes, tool integration details | [Writing Guide](file:///home/opencode/.config/opencode/skills/making-and-using-task-plans/references/writing-guide.md) | Step annotations, phase structure guidance, cross-session continuity, common mistakes |
| Full annotated example plan with commentary | [Example Plan](file:///home/opencode/.config/opencode/skills/making-and-using-task-plans/references/example-plan.md) | Annotated example showing all structural elements in practice |
| `plan_read`, `plan_complete_step`, `plan_archive` signatures and usage | [Tool Integration](file:///home/opencode/.config/opencode/skills/making-and-using-task-plans/references/tool-integration.md) | Tool signatures, parameter docs, usage patterns |

---

## Quick Reference

### Required Structure

```markdown
# Task: <Brief Title>

## Problem Statement
<What and why. Assume reader has zero context.>

## Phases

### Phase 1: <Outcome Name>
- [ ] Step description
- [ ] Step description

### Phase 2: <Outcome Name>
- [ ] Step description

## Completion Criteria
- Measurable success condition
```

### Format Rules

| Element | Pattern | Note |
|---------|---------|------|
| Title | `# Task: <title>` | Required |
| Phase | `### Phase N: <title>` | N must be sequential integer (1, 2, 3...) |
| Step | `- [ ] <text>` or `- [x] <text>` | **Must be flat — no indented checkboxes** |
| Annotation | `**Notes:**`, `**Warning:**`, `**Blocked:**` | Phase-level or step-level |

**Step IDs** auto-generate as `P{phase}-S{step}` (e.g., `P1-S1`, `P2-S3`).

**Parser rejection rules:** Nested steps, non-sequential phases, and invalid phase formats all cause parse errors. See [Syntax Reference](file:///home/opencode/.config/opencode/skills/making-and-using-task-plans/references/syntax.md) for details.

---

## Tool Integration

Three tools manage the plan lifecycle:

| Tool | Purpose |
|------|---------|
| `plan_read(plan_name)` | Parse and validate a plan, returns structured JSON |
| `plan_complete_step(plan_name, step_id, ...)` | Mark a step complete with optional annotation |
| `plan_archive(plan_name)` | Archive completed plan from pending to completed |

For detailed signatures and usage patterns, see [Tool Integration](file:///home/opencode/.config/opencode/skills/making-and-using-task-plans/references/tool-integration.md).

---

## Validation Checklist

Before declaring a plan complete:

- [ ] Structure matches template
- [ ] Phase numbers are sequential integers
- [ ] Steps are flat (no nesting)
- [ ] Problem Statement provides context for fresh sessions
- [ ] Completion Criteria are measurable
- [ ] Run `plan_read(plan_name)` — must parse without errors

---

## References

- [`references/syntax.md`](file:///home/opencode/.config/opencode/skills/making-and-using-task-plans/references/syntax.md) — Format rules, template, parser constraints, splitting, validation
- [`references/writing-guide.md`](file:///home/opencode/.config/opencode/skills/making-and-using-task-plans/references/writing-guide.md) — Annotations, best practices, common mistakes, cross-session continuity
- [`references/example-plan.md`](file:///home/opencode/.config/opencode/skills/making-and-using-task-plans/references/example-plan.md) — Full annotated example plan with commentary
- [`references/tool-integration.md`](file:///home/opencode/.config/opencode/skills/making-and-using-task-plans/references/tool-integration.md) — Tool API reference with signatures and usage patterns
- Related skills: `decomposing-design-documents` (multi-plan decomposition), `feature-execution` (execution pipeline)
