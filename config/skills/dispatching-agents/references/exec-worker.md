# Exec-Worker

Dispatch Exec-Worker to implement a scoped portion of an implementation plan — a single phase or range of steps.

## When to Dispatch

**Dispatch when:**
- Exec-Manager delegates per-phase implementation work
- You need a focused, scoped implementation of a plan phase

**Do NOT dispatch when:**
- You're executing a full plan — use `exec-manager` instead (it spawns this agent per phase)
- You need planning — use `exec-planner` instead
- You need research — use `support-researcher` instead
- The work is a single trivial edit — do it yourself

## Dispatch Template

```
Implement phase [PHASE_NUMBER] of plan [PLAN_IDENTIFIER].

Your scope: steps [STEP_RANGE] only.

Use plan_read("[PLAN_IDENTIFIER]") to discover the plan and your steps.

Context:
- [CONTRACTS_PATH]  — contracts ledger (if multi-part feature)
- [DESIGN_DOC_PATH]  — design document

task:
  plan: "[PLAN_IDENTIFIER]"
  phase: [PHASE_NUMBER]
  steps: "[STEP_RANGE]"

For each step: implement, lint, mark complete with plan_complete_step and an annotation.
Report DONE when all steps in scope are complete.
```

## Required Fields

| Field | Description | Example |
|-------|-------------|---------|
| `[PLAN_IDENTIFIER]` | Plan name for plan_read | `TASK-feature-A-scope` |
| `plan` | Plan identifier | `TASK-feature-A-scope` |
| `phase` | Phase number to implement | `1` |
| `steps` | Step range to implement | `P1-S1 through P1-S4` |

## Expected Output

| Status | Meaning |
|--------|---------|
| `DONE` | All steps in range completed with annotations |
| `BLOCKED` | A step cannot be completed — reason provided |
| `ESCALATE` | Issue requires manager intervention |

Output includes:
- Steps completed with annotations
- Files created/modified/deleted
- Any blockers with specific details

## Step Annotation Rules

After completing each step, annotate in the plan:
- What was done (concrete, not "implemented feature")
- Files changed
- Any observations or warnings

**Never** modify the plan structure. Annotations only. Steps must be marked complete in order — no skipping, no partial completion.

## Spec-First Testing

When spec tests exist for the phase:
- Read the spec tests first to understand expected behavior
- Implement toward making spec tests pass
- Do NOT modify spec tests — change implementation instead
- Report spec test status at phase completion (passing / expected failures / unexpected failures)
