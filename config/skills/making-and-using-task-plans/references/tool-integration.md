# Tool Integration Reference

Plans are read, updated, and archived via three tools. This reference covers their signatures and usage patterns.

## `plan_read`

Parse and validate a plan's structure. Returns structured JSON with phases, steps, and annotations.

```python
plan_read(plan_name="TASK-add-auth")
```

Use this:
- At the start of a session to understand what's been done
- After editing a plan manually to verify syntax
- Before archiving to confirm all steps are complete

## `plan_complete_step`

Mark a step as complete with an optional annotation.

```python
plan_complete_step(
    plan_name="TASK-add-auth",
    step_id="P1-S1",                    # Auto-generated from phase/step position
    annotation_marker="Notes",          # One of: Notes, Warning, Blocked, Deviation
    annotation_text="Used JWT with HS256, stored in httpOnly cookie"
)
```

Step IDs are auto-generated: `P{phase}-S{step}` where both are 1-indexed. Do not invent IDs — they come from the step's position in the plan.

## `plan_archive`

Move a completed plan from `artifacts/plans/pending/` to `artifacts/plans/completed/`.

```python
plan_archive(plan_name="TASK-add-auth")
```

Use `ignore_blocked=True` to archive despite `**Blocked:**` annotations — useful when blocked steps are intentionally deferred.
