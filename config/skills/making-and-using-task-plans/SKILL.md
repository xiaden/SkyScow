---
name: making-and-using-task-plans
description: Create, edit, or validate task-plan Markdown and use plan lifecycle tools. Use when working on artifacts/plans or plan_read, plan_complete_step, or plan_archive; do not use for decomposing a design document or executing a multi-plan feature.
---

# Making & Using Task Plans

**Purpose:** Produce valid task plans whose steps, worker phases, manager plans, and plan-set dependencies have explicit ownership without confusing those boundaries with Git or release boundaries.

This is the canonical plan-format entry point. Format rules and detailed guidance live in the references below.

## When to Use

**Load this skill when:**
- Creating, editing, or validating a task plan in `artifacts/plans/`.
- Using `plan_read`, `plan_complete_step`, `plan_annotate_step`, or `plan_archive`.
- Reviewing plan ownership, dependency closure, phase packing, or cross-session continuity.

**Do NOT use this skill when:**
- Decomposing a design document into multiple plans — use `decomposing-design-documents`.
- Executing a multi-plan feature — use `feature-execution`.
- The task is trivial and needs no cross-session plan.

## Canonical boundaries

- **Step:** one concrete, actionable, bounded implementation obligation owned by one package and verifiable against its own intent.
- **Phase:** a worker context unit containing dependency-compatible steps that one Exec-Worker can safely understand and execute. It is not a commit, release, deployable checkpoint, independently buildable feature, or globally green milestone.
- **Plan:** a manager review context unit containing phases that one Exec-Manager can validate against request/DD intent, contracts, worker results, changed surfaces, QA findings, and downstream ownership. It is not a commit, release, deployable state, or fully integrated feature.
- **Plan set:** the decomposition that owns eventual whole-change integration. Its existing README/dependency metadata carries the actual graph.
- **Commit:** an orthogonal Git/workflow boundary. No plan or phase state implies a commit.

A phase or plan may finish while downstream integration is incomplete only when a present, schema-valid, non-superseded later owner is named in the plan-set graph. Unowned breakage is a current defect or `PLANNING_GAP`.

## Reference Dispatch

| Need | Reference |
|---|---|
| Format, dependencies, phase/plan packing, parser rules | [`references/syntax.md`](file:///home/opencode/.config/opencode/skills/making-and-using-task-plans/references/syntax.md) |
| Writing steps, annotations, ownership, downstream state, archival | [`references/writing-guide.md`](file:///home/opencode/.config/opencode/skills/making-and-using-task-plans/references/writing-guide.md) |
| Annotated replacement-API example with valid intermediate state | [`references/example-plan.md`](file:///home/opencode/.config/opencode/skills/making-and-using-task-plans/references/example-plan.md) |
| Lifecycle tool signatures | [`references/tool-integration.md`](file:///home/opencode/.config/opencode/skills/making-and-using-task-plans/references/tool-integration.md) |

## Quick Reference

```markdown
# Task: <Brief Title>

## Problem Statement
<What, why, scope, and constraints>

## Dependencies
- None, or explicit producer/consumer prerequisites from the feature README.

## Phases

### Phase 1: <worker-context package>
- [ ] Bounded, actionable, verifiable obligation

## Completion Criteria
- Owned obligations complete and annotated.
- Relevant local checks run where possible.
- Any incomplete integration has a named downstream owner.
```

Phase display numbers must be sequential for parser stability; actual execution order comes from explicit dependency metadata, not phase numbers or plan letters. Steps remain flat checkboxes. Run `plan_read(plan_name)` after creating or editing a plan.

## Context-based sizing

Use `config/agent-context-budgets.yaml` and the `context_tokens` / `context_budget` tools as the source of truth. Include the actual context carried by the worker or manager; do not copy numeric limits into plan prose or split on fixed step/phase counts. Split only when context overload, context switching, review diffusion, or a real dependency requires it.

## Lifecycle and ownership

Plans may be `pending`, `in-flight`, `complete-awaiting-QA`, or `archived`. A plan can be archived when its owned review package is complete and accepted. Archival is artifact bookkeeping: it does not assert a commit, release, deployment, globally green repository, complete feature, or sibling-plan completion. Whole plan-set archival remains a separate boundary after dependency closure.

## Validation checklist

- [ ] Every implementation obligation has one owner.
- [ ] Every dependency edge is a real prerequisite or producer-consumer relation.
- [ ] Independent work remains independent.
- [ ] Phases fit worker context and plans fit manager review context using canonical budget tools.
- [ ] Expected incomplete integration has a valid downstream owner.
- [ ] QA obligations are exposed as changed surfaces/explicit requirements, not manufactured as universal phase milestones.
- [ ] No generic commit step is added because a phase or plan ends.
- [ ] `plan_read` passes.

## References

- [`references/syntax.md`](file:///home/opencode/.config/opencode/skills/making-and-using-task-plans/references/syntax.md)
- [`references/writing-guide.md`](file:///home/opencode/.config/opencode/skills/making-and-using-task-plans/references/writing-guide.md)
- [`references/example-plan.md`](file:///home/opencode/.config/opencode/skills/making-and-using-task-plans/references/example-plan.md)
- [`references/tool-integration.md`](file:///home/opencode/.config/opencode/skills/making-and-using-task-plans/references/tool-integration.md)
- Related: `decomposing-design-documents`, `feature-execution`

## Request Context for Plan Authoring

Plan CREATE and AMEND operations must carry a readable `request_context.path` to an `artifacts/requests/CTX_*.md` snapshot. The planner reads it before authoring and preserves its reference. Missing or unreadable context blocks plan authoring.

## Plan Lifecycle and Ownership Validation

During validation, require an `Ownership` section naming callers and changed behavior where relevant. A handoff annotation alone does not establish caller coverage. A plan with zero open steps is not new work: archive it or record `complete-awaiting-QA` with its disposition.
