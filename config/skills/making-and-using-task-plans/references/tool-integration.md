# Tool Integration Reference

Plans are read, updated, and archived via the registered lifecycle tools.

## `plan_read`

Parse and validate a plan. Use at session start, after manual edits, before execution, and before archival.

```python
plan_read(plan_name="TASK-replacement-api-A-contract")
```

The result describes phases, steps, annotations, and lifecycle state. It does not decide whether the plan set is complete or the repository is globally integrated.

## `plan_complete_step`

Mark an owned step complete with an annotation.

```python
plan_complete_step(
    plan_name="TASK-replacement-api-A-contract",
    step_id="P1-S1",
    annotation_marker="Notes",
    annotation_text="Implemented the replacement contract; caller migration remains owned by Plan B."
)
```

Step IDs are generated from position: `P{phase}-S{step}`. Do not invent them. Completion means the step's owned obligation is complete, not that later integration is complete.

## `plan_annotate_step`

Add or replace context without changing completion state.

```python
plan_annotate_step(
    plan_name="TASK-replacement-api-A-contract",
    step_id="P1-S1",
    op="add",
    annotation_marker="Warning",
    annotation_text="The legacy caller remains until downstream Plan B."
)
```

Use annotations for decisions, deviations, blockers, and explicit downstream ownership.

## `plan_archive`

Move a plan from `artifacts/plans/pending/` to `artifacts/plans/completed/` after its owned review package is complete and accepted.

```python
plan_archive(plan_name="TASK-replacement-api-A-contract")
```

Archiving is not a commit, release, deploy, repository-green assertion, or plan-set completion assertion. Use `ignore_blocked=True` only when a blocked step is intentionally deferred with an explicit owner and disposition.
