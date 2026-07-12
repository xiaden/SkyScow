# Exec-Manager

Dispatch Exec-Manager to execute an implementation plan.

## When to Dispatch

- When a plan is ready for implementation
- After Exec-Planner has created the plan
- After RnD-Manager has produced a design document and Exec-Planner has planned it

**Do NOT dispatch when:**
- The plan hasn't been created yet — use `exec-planner` instead
- You're doing R&D or design work — use `rnd-manager` instead
- You're debugging a failure — use `support-debugger` instead
- Executing a single-step task with no formal plan

## Dispatch Template

```text
Execute plan [PLAN_PATH].

**Your job is to spawn your workers:**
- Spawn Exec-Worker for EACH phase in order (one spawn per phase, never bundle)
- Spawn QA-Reviewer after ALL phases complete
- Spawn Exec-Fixer for MINOR issues found by QA-Reviewer
Do NOT implement code yourself.

Context files to read:
- [PLAN_PATH]  — the plan
- [CONTRACTS_PATH]  — contracts ledger (omit if not a multi-part feature)
- [DESIGN_DOC_PATH]  — design document

task:
  plan: "TASK-{feature}-{letter}-{title}"
  startPhase: 1
  reviewRequired: true
```

## Required Fields

| Field | Description | Example |
|-------|-------------|---------|
| `[PLAN_PATH]` | Path to the plan file | `artifacts/plans/pending/TASK-feature-A-scope.md` |
| `[CONTRACTS_PATH]` | Path to contracts ledger | Omit if not a multi-part feature |
| `[DESIGN_DOC_PATH]` | Path to the design document | `artifacts/designs/pending/feature-design.md` |
| `plan` | Plan identifier | `TASK-feature-A-scope` |
| `startPhase` | Phase to start from (usually 1) | `1` |
| `reviewRequired` | Enforce QA gate — must be `true` | `true` |

The bolded worker-spawn instructions are **required** — they remind Exec-Manager that it dispatches workers, not implements code itself.

## Expected Output

| Status | Meaning |
|--------|---------|
| `DONE` | All phases complete, QA-Reviewer passed |
| `BLOCKED` | A blocker cannot be resolved internally |
| `ESCALATE` | Director input is needed |

The output includes artifacts created/modified/deleted, annotations from each phase, QA review status (mandatory for DONE), and test/docs analyzer status.

## QA Gate Enforcement

The QA gate is a hard enforcement point. Exec-Manager must spawn QA-Reviewer after all implementation phases complete and must not return `DONE` until QA-Reviewer reports `PASS`.

**Enforcement rules:**

1. **QA-Reviewer must run after ALL phases complete.** Partial reviews are not a substitute.
2. **Only `PASS` unlocks `DONE`.** Any other status (`MINOR`, `MAJOR`, `FAIL`) must trigger a fix cycle or escalation.
3. **Exec-Fixer handles MINOR issues.** After fixes, re-run QA-Reviewer.
4. **MAJOR issues require escalation.** Architectural problems, missing functionality, or systemic bugs cannot be handled by Exec-Fixer alone.

**Fix cycle flow:** QA-Reviewer reports MINOR → Spawn Exec-Fixer with issue list → Re-run QA-Reviewer → Repeat until PASS or escalation. Each fix cycle requires a full QA-Reviewer re-run.

**Edge cases:**

- **QA-Reviewer fails to spawn:** Retry once. If second attempt fails, escalate with spawn error.
- **QA-Reviewer returns ambiguous results:** Re-spawn with clarification request — do not interpret output yourself.
- **Fix cycle exceeds 3 iterations:** Escalate. Issues are likely systemic.
- **No changes to review:** QA-Reviewer still runs and will return `PASS` for an empty diff. Do not skip the gate.

## Spec-First Testing Strategy

This project follows **spec-first testing** (TDD-style): tests are authored against the design document specification and expected to fail until implementation completes.

**Exec-Worker behavior:**
- Spec-first tests exist as the target — implementation works toward making them pass
- Test failures during phased implementation are expected, not blockers
- Do NOT modify spec tests to make them pass — change the implementation instead

**QA-Reviewer must distinguish between:**
- **Spec-first test failures:** tests from the spec that haven't passed yet (legitimate findings)
- **Stale tests:** tests referencing removed functionality (bugs in the tests)
- **Buggy tests:** tests with incorrect assertions (bugs in the tests)

**What NOT to do:**
- Do NOT dispatch Support-Debugger for spec-first test failures during execution
- Do NOT modify spec tests to match incomplete implementation
- Do NOT skip QA-Reviewer because spec tests are failing

| Symptom | Likely cause | Action |
|---------|-------------|--------|
| Test references a function that doesn't exist yet | Spec-first — implementation incomplete | Continue implementation |
| Test references a function that was removed | Stale test — spec changed | Escalate for plan amendment |
| Test fails with wrong output for existing function | Implementation bug | Fix implementation |
| Test setup fails (import error, missing mock) | Test is buggy | Escalate — test needs fixing |
