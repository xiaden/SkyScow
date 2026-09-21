# Exec-Planner

Dispatch Exec-Planner to create, amend, or reorder implementation plans. Choose the operation:

| Scenario | Operation |
|----------|-----------|
| Design document needs plan breakdown | **CREATE** |
| QA-Reviewer flags PLANNING_GAP | **AMEND** |
| Plans are out of sequence (A, B, E, C, D) | **REORDER** |

**Do NOT dispatch for:** executing plans (→ Exec-Manager), designing features (→ RnD-Manager), reviewing plans (→ QA-Reviewer), or single-step edits that don't need a plan.

## Expected Output

- **CREATE**: One or more plan files in `artifacts/plans/pending/`
- **AMEND**: Updated plan file with new/amended phases
- **REORDER**: Confirmation of new plan order

All outputs include `status: DONE` when complete.

## Post-Dispatch Checklist

- [ ] Exec-Planner reported `status: DONE`
- [ ] Plan files exist at the expected paths
- [ ] For AMEND: affected phases are re-executed before QA review
- [ ] For REORDER: no plans are executed before the reorder is confirmed

---

## CREATE: Initial Planning

Use when a design document needs to be broken into implementation plans.

### Dispatch Template

```
Create an implementation plan from design document: [DD_PATH]

Context files to read:
- [REQUEST_CONTEXT] — required `artifacts/requests/CTX_*.md` source conversation; read before planning
- [DD_PATH]  — design document
- [CONTRACTS_PATH]  — contracts ledger (if multi-part feature)
- [AUTHORITATIVE_REQUEST] — verbatim original user request and requirement ledger

Librarian briefing: [paste briefing or "see attached context"]
Key constraints: [key constraints from Librarian/PatternEnforcer]

PlanGate timing: create and validate every plan required for the coordinated group first. Only when the complete group exists may Exec-Planner evaluate coordination triggers, record Planner-owned `plan_gate: status: NOT_REQUIRED` with observable rationale, or dispatch Exec-PlanGate for a triggered group. Never gate a knowingly incomplete future group. Exec-Planner owns applicability; Exec-PlanGate is not dispatched for no-trigger groups.

The `request_context` path is required for CREATE, AMEND, and REORDER. A
summary or handoff goal cannot replace it; missing or unreadable context blocks
planning.

Precedence: authoritative user request > accepted DD requirements/architectural invariants > plan > code/tests. Research, review recommendations, estimates, and verification evidence are advisory unless explicitly adopted as a requirement, invariant, dependency, or contract. Compare the plan against every mandatory ledger item that requires implementation; report REQUIREMENT_DRIFT rather than omitting, weakening, deferring, inverting, or contradicting one. Do not predeclare QA-owned tests, documentation, or evidence artifacts.
```

### Required Fields

- `[DD_PATH]`: Path to the design document
- `[CONTRACTS_PATH]`: Path to contracts ledger (omit if not a multi-part feature)
- `[paste briefing or "see attached context"]`: Librarian's briefing
- `[key constraints]`: Critical constraints from Librarian/PatternEnforcer

### Spec-First Testing

### Implementation coordination

Describe contracts and behavior precisely enough for implementation and downstream coordination. A plan may include a spec-first test step only when the user explicitly requested that test deliverable or the accepted architecture makes the executable test artifact part of the implementation. Otherwise QA independently decides whether tests, docs, or corrective work are needed after implementation.

Do not add generic README, CONTRACTS, evidence, review, test, or documentation steps merely to satisfy a prior planning or validation artifact. Add them only when required to coordinate an authoritative implementation change. PatternEnforcer findings remain repository-impact evidence; they do not establish migration scope or automatically amend a plan. The owning planning layer records the explicit disposition after accepted migration intent exists.
## AMEND: Plan Amendment

Use when QA-Reviewer flags PLANNING_GAP issues, or when Support-Debugger identifies that a fix requires plan changes.

### Dispatch Template

```
Amend plan TASK-{feature}-{letter}-{title}.

Context files:
- artifacts/requests/CTX_<two-word-slug>.md  (required source conversation)
- artifacts/plans/pending/TASK-{feature}-{letter}-{title}.md  (existing plan)
- artifacts/designs/pending/{feature}/CONTRACTS.md
- artifacts/designs/pending/{feature}/README.md

task:
  type: AMEND
  plan: "TASK-{feature}-{letter}-{title}"
  reason: "{paste PLANNING_GAP detail from review report}"
```

### Required Fields

- `artifacts/requests/CTX_<two-word-slug>.md`: Readable source conversation for the plan set
- `TASK-{feature}-{letter}-{title}`: The plan to amend
- `reason`: The PLANNING_GAP detail from the review report or debugger's root cause

### After AMEND

Re-execute affected phases, then run full QA review.

---

## REORDER: Plan Reordering

Use when plans are out of sequence (e.g., A, B, E, C, D instead of A, B, C, D, E).

### Dispatch Template

```
Reorder plans for feature {feature}.

Context files:
- artifacts/requests/CTX_<two-word-slug>.md  (required source conversation)
- artifacts/plans/pending/  (all plan files for this feature)
- artifacts/designs/pending/{feature}/CONTRACTS.md
- artifacts/designs/pending/{feature}/README.md

task:
  type: REORDER
  feature: "{feature}"
  insertion:
    newPlan: "TASK-{feature}-{letter}-{title}"  (the out-of-sequence plan)
    insertAfter: "{letter}"                      (letter of the plan it should follow)
  reason: "{why this plan must precede the ones after it}"
```

### Required Fields

- `{feature}`: The feature slug
- `newPlan`: The out-of-sequence plan
- `insertAfter`: The letter of the plan it should follow
- `reason`: Why this plan must precede the ones after it

### After REORDER

**Do not execute any plan until Exec-Planner reports DONE.**

## GitHub Actions context (when relevant)

If the plan covers GitHub Actions workflow behavior, include in the dispatch:

- **GitHub Actions context:** the target workflow/repository and what behavior must be planned (inspect/create/modify/remove workflow files, branch/push, `gh workflow run`/dispatch, watch, view logs, download artifacts, cancel, cleanup, iterate from results).
- **Remote-Docker constraint:** local Docker is unavailable; Docker/attestation work targets GitHub-hosted runners (`gg-artifacts`).
- **PAT/`gh` assumption:** the plan assumes the existing PAT-authenticated `gh` CLI used directly through the terminal (`gg-env`); Exec-Planner plans this behavior but does not implement or execute it.
- **Skill-loading requirement:** direct the plan to require exec-workers to load the applicable `gg-*` skill (gg-actions for the workflow lifecycle, gg-core/gg-repos for branch/push, gg-env for credentials, gg-artifacts for hosted Docker, gg-docs for Pages, gg-router for routing, ggt-conventions for repo-local constraints) before the Git/GitHub operation.

Keep the exact-reference and authoritative-request conventions above intact when composing the dispatch.


### Lifecycle and Ownership Validation

Before dispatch, require accepted DD status (or an accepted DD explicitly marked as an intentional pending prerequisite with metadata naming the disposition, responsible owner, and next transition condition) and a recorded comparison against the verbatim user request. Reject stale/invalid pending DDs and any execution/archive of an unaccepted DD. Require each plan's `Ownership` to name every caller file for changed symbol signatures, return types, or behavior; handoffs do not count. Require ownership-closure evidence: a call-graph/import check listing resolved and unresolved edges, a manual disposition for every unresolved edge, and a mock-versus-real caller integration test for signature or return-type changes. Require a supersession sweep and permit generational families only with an explicit predecessor → successor graph, bounded scope, supersession metadata/back-pointers, and a recorded Exec-PlanGate `PASS`. On mismatch, dispatch must report `REQUIREMENT_DRIFT` and stop.
