---
name: feature-execution
description: Execute a complete set of dependency-ordered implementation plans for one feature. Use when the user asks to implement or work through plans and all lettered plans are present and valid; do not use for creating plans, decomposing designs, or executing a single plan.
---

# Feature Execution

Pipeline for implementing a set of feature plans produced by `decomposing-design-documents`. Uses hierarchical agent dispatch: Nyx → Exec-Manager → Exec-Worker/Reviewer/Fixer.

```
Plans + Ledger → Dispatch Exec-Manager → [internal: phases/review/fix] → Update Ledger → Next Plan → Archive
                        ↓                              ↓                      ↓                         ↓
                 One per plan              Exec-Manager handles           Nyx updates         COMPLETION.md
                                           execution lifecycle            CONTRACTS.md          → artifacts/plans/completed/
```

### Execution Decision Flowchart

**1. Check prerequisites:**
   - All plans present and schema-valid → proceed to step 2
   - Any missing or invalid → stop; run `decomposing-design-documents` or fix the plan first

**2. For each plan in dependency order, dispatch one Exec-Manager and handle the response.**

   **When plans are independent** (both share the same dependency and neither depends on the other), dispatch them in **parallel**. Fan out when safe — let Exec-Managers run concurrently, then collect results.

   **When plans have sequential dependencies** (Plan B requires Plan A's outputs), dispatch one at a time in order.

   For each dispatch:
   - `DONE` → update the ledger (Phase 3), then return to step 2 for the next plan(s)
   - `BLOCKED` → investigate the blocker; if resolvable provide guidance and re-dispatch; if not, stop and notify the user
   - `ESCALATE` → stop immediately; present the blocker to the user; do not retry

**3. When all plans have returned `DONE`:**
   - Archive the feature (Phase 5)

---

## Agent Hierarchy

Nyx (the top-level orchestrator executing this skill) dispatches **Exec-Manager** agents. Each Exec-Manager owns its plan's full lifecycle:

```
Nyx (top-level orchestrator)
├── Exec-Manager A
│   ├── Exec-Worker (per phase)
│   ├── Reviewer (after all phases)
│   └── Fixer (if review finds issues)
├── Exec-Manager B
│   └── ... same structure
└── Handles: escalations, ledger updates, archival
```

**Key principle:** Exec-Managers own execution details. Nyx receives `DONE | BLOCKED | ESCALATE` — not phase-by-phase progress.

See [.opencode/agents/](.opencode/agents/) for agent specifications.

---

## Hard Rules

| Category | Rules | Purpose |
| --- | --- | --- |
| Dispatch Rules | 1–4 | Control how and when agents are invoked |
| Ledger & Session Rules | 5–6 | Ensure ledger accuracy and session continuity |
| Archival Rules | 7 | Keep working directories clean after completion |

### Dispatch Rules
_(Govern how agents are invoked and when to stop)_

1. **Never bypass Exec-Manager.** Dispatch one Exec-Manager per plan. Exec-Manager handles phases, review, and fix cycles internally. Don't dispatch Exec-Workers or Reviewers directly. *(Example: for Plan B, dispatch one Exec-Manager for Plan B — not separate Exec-Worker + Reviewer calls.)*
2. **Never ignore Exec-Manager escalations.** If Exec-Manager returns `ESCALATE`, stop and address the blocker. These are real problems, not optional. *(Example: 3+ failed fix rounds → stop, present to user, do not retry.)*
3. **Never execute out of dependency order.** Follow the execution rounds from the feature README. A plan that depends on Plan A's outputs cannot run before Plan A's Exec-Manager returns DONE. *(Example: if Plan B depends on Plan A, Plan B's Exec-Manager cannot be dispatched until Plan A is fully DONE.)*
4. **Dispatch independent plans in parallel.** When two or more plans share the same completed dependency and neither depends on the other, dispatch their Exec-Managers concurrently. This maximizes throughput without violating dependency order. *(Example: Plans B and C both depend only on Plan A. Once Plan A is DONE, dispatch B and C in parallel — one `task` call each in the same message.)*

### Ledger & Session Rules
_(Govern continuity and correctness of recorded contracts)_

5. **Update the ledger with actuals, not plans.** After Exec-Manager returns DONE, update CONTRACTS.md with *implemented* signatures from the codebase — which may differ from what was planned. *(Example: if the plan specified `create_item(id: int)` but the implementation used `create_item(item_id: str)`, record the latter.)*
6. **If context budget is exhausted, stop at a plan boundary.** The ledger and plan step checkboxes preserve all progress. A new session resumes cleanly. *(Example: finish Plan C's ledger update, then stop — do not start Plan D mid-session.)*

### Archival Rules
_(Govern clean-up after feature completion)_

7. **Never leave completed features unarchived.** After the last plan's Exec-Manager returns DONE plus ledger update, execute the archival protocol. *(Example: move all TASK-{feature}-*.md files and the DD to `completed/` as described in Phase 5.)*

---

## Prerequisites

Before starting execution:

1. Feature plans exist: `artifacts/plans/pending/TASK-{feature}-{A..Z}-*.md`
2. Parts README exists: `artifacts/designs/parts/{feature}/README.md`
3. Contracts ledger exists: `artifacts/designs/parts/{feature}/CONTRACTS.md`
4. All plans pass `plan_read` (schema-valid)

If any are missing, run `decomposing-design-documents` first.

**If a plan file is invalid or corrupted** (i.e., `plan_read` returns a parse error): log the error, notify the user, and ask them to regenerate the affected plan via `decomposing-design-documents` before proceeding. Do not attempt to execute a plan that cannot be parsed.

**If CONTRACTS.md is missing or corrupted:** notify the user and halt execution. Do not attempt to run any Exec-Manager until CONTRACTS.md is present and readable. Ask the user to regenerate it via `decomposing-design-documents` (Phase 2: Initialize Contracts Ledger) before proceeding.

---

## Phase 1: Prepare

1. Read the parts README — get execution rounds and dependency order
2. Read CONTRACTS.md — current state of implemented contracts
3. Check which plans have all steps completed (via `plan_read` or checkbox inspection)
4. Identify the next incomplete plan in dependency order

**Resuming a session:** Steps 1-4 are the full resume protocol. The ledger + plan checkboxes contain all state.

---

## Phase 2: Execute Plan

For each plan in dependency order, dispatch a Exec-Manager. Dispatch independent plans in parallel (see Rule 4).

### 2a. Quality Gate (Enforced by Exec-Manager)

Each Exec-Manager enforces a full quality gate before returning DONE. Nyx doesn't run these checks — the Exec-Manager's internal Reviewer does:

| Gate | Check | Standard |
|------|-------|----------|
| **Lint** | Zero errors on all affected paths | Mandatory — blocks DONE |
| **Type Check** | Build/type check passes (tsc, mypy, etc.) | Mandatory — blocks DONE |
| **Layer Compliance** | No upward imports, correct DI patterns | Mandatory — blocks DONE |
| **Contract Adherence** | Actual signatures match CONTRACTS.md | Mandatory — blocks DONE |
| **Code Quality** | No mutation, file <800 lines, functions <50 lines, nesting <4, no console.log/print(), no bare except, no TODO/FIXME | Mandatory — blocks DONE |
| **Test Coverage** | Repository-defined: honor the repository's own coverage threshold or verification policy when one exists; otherwise coverage is diagnostic only — no universal percentage (see `config/instructions/validation-mandate.md`) | Conditional — blocks DONE only when the repository defines a coverage policy |
| **Security Review** | Required only when the changed surface includes an observable security-sensitive surface per the canonical list in `config/skills/security-review/SKILL.md` | Conditional — blocks DONE only when such a surface changed |
| **Build** | Project builds successfully | Mandatory — blocks DONE |
| **Completeness** | All plan steps implemented, no stubs, no "will implement later" | Mandatory — blocks DONE |
| **Drift Detection** | Implementation matches design intent, no scope creep, no missing methods | Mandatory — blocks DONE |

Fix cycles (up to 2 rounds) resolve issues before DONE. 3+ rounds → ESCALATE.

### 2b. Dispatch Exec-Manager

```yaml
# Dispatch to Exec-Manager agent
contextFiles:
  - artifacts/plans/pending/TASK-{feature}-{letter}-{title}.md    # The plan
  - artifacts/designs/parts/{feature}/CONTRACTS.md      # Current contracts
  - artifacts/designs/parts/{feature}/README.md         # Feature structure
  - artifacts/designs/pending/DD-{feature}.md               # Design doc
  - {layer_instructions_file}  # Per layer in this plan

task:
  plan: "TASK-{feature}-{letter}-{title}"
  startPhase: 1         # Or resume from incomplete
  reviewRequired: true
```

For a coordinated group of six or more plans, Exec-Planner must complete the Exec-PlanGate preflight and return `PASS` with the plan group before any Exec-Manager is dispatched. Exec-Manager verifies that result; it does not spawn the gate.

**Exec-Manager handles internally:**

- Dispatching Exec-Worker per phase
- Running Reviewer after all phases complete
- Dispatching Fixer if review finds issues
- Fix cycles (up to 2 rounds, then escalates)

For details on how Exec-Manager constructs subagent prompts and handles review internally:
- [references/execution-protocol.md](file:///home/opencode/.config/opencode/skills/feature-execution/references/execution-protocol.md) — Subagent dispatch patterns, prompt templates, context injection rules
- [references/review-protocol.md](file:///home/opencode/.config/opencode/skills/feature-execution/references/review-protocol.md) — Review dispatch protocol, checklist, and fix cycle limits

### 2c. Handle Exec-Manager Response

 | Status | Action |
 | -------- | -------- |
 | `DONE` | Proceed to Phase 3 (Update Ledger) |
 | `BLOCKED` | Investigate blocker. If resolvable, provide guidance and re-dispatch. If not, stop execution. |
 | `ESCALATE` | Stop. Present to user. Common causes: 3+ fix rounds, fundamental design issue, missing requirements. |

**Do NOT re-run Exec-Manager for DONE.** The plan is complete. Proceed to ledger update.

---

## Phase 3: Update Ledger

After Exec-Manager returns DONE:

1. **Update CONTRACTS.md** with *actual* implementations, not planned signatures
2. Use available code-reading tools (e.g., `Read`, `Grep`) to get real signatures from the codebase
3. Note any deviations from the original plan in the Decisions table
4. Date-stamp the update with the plan letter

**This is critical for downstream plans.** The next plan's Exec-Manager receives the ledger. Stale planned signatures cause cascading errors.

---

## Phase 4: Next Plan

Proceed to the next plan in dependency order. Return to Phase 2.

**Round boundaries:** When finishing the last plan in an execution round, all plans in that round should have their ledger entries updated before starting the next round.

---

## Phase 5: Archive Feature

After all plans' Exec-Managers return DONE, the ledger is updated, and the user is informed of any deviations — archive the feature.

See [references/archival-protocol.md](file:///home/opencode/.config/opencode/skills/feature-execution/references/archival-protocol.md) for the full completion manifest template, move protocol, verification steps, and standalone plan handling.

---

## Session Continuity

When starting a new session mid-feature:

1. Read `artifacts/designs/parts/{feature}/README.md` — execution rounds
2. Read `artifacts/designs/parts/{feature}/CONTRACTS.md` — implemented contracts
3. For each plan, run `plan_read` to check completion status
4. Identify state:
   - **Plan fully complete + ledger updated** → skip it (CONTRACTS.md has entries)
   - **Plan partially complete** → dispatch Exec-Manager with `startPhase: {next incomplete}`
   - **Plan not started** → check if all dependencies complete, then dispatch Exec-Manager
5. Resume at the appropriate phase

**The ledger is the source of truth for what's done.** If CONTRACTS.md has entries for Plan C's methods, Plan C's Exec-Manager returned DONE.

---

## Validation Checklist

Before declaring feature execution complete:

- [ ] All Exec-Managers returned DONE **→ Full implementation + all quality gates passed**
- [ ] CONTRACTS.md reflects actual implementations **→ No plan-vs-code drift**
- [ ] Available linter passes on full workspace **→ Zero errors**
- [ ] Repository-defined coverage policy honored where one exists, otherwise coverage reported as diagnostic (no universal percentage) **→ No coverage regression**
- [ ] Security review run where an observable security-sensitive surface changed, per `config/skills/security-review/SKILL.md` **→ Security-sensitive surfaces covered**
- [ ] No orphaned fix plans with incomplete steps **→ Clean state**
- [ ] User informed of any design deviations **→ Alignment**
- [ ] COMPLETION.md generated in `{feature}/` **→ Audit trail**
- [ ] All artifacts moved to `artifacts/plans/completed/` **→ Clean working directory**
- [ ] No feature files remain in `artifacts/plans/pending/` or `artifacts/designs/parts/` **→ Verified clean state**

---

## References

- [references/execution-protocol.md](file:///home/opencode/.config/opencode/skills/feature-execution/references/execution-protocol.md) — Subagent dispatch patterns, prompt templates, and context injection rules (used internally by Exec-Manager)
- [references/review-protocol.md](file:///home/opencode/.config/opencode/skills/feature-execution/references/review-protocol.md) — Review dispatch protocol, checklist, scope classification, and fix cycle limits (used internally by Exec-Manager)
- [references/archival-protocol.md](file:///home/opencode/.config/opencode/skills/feature-execution/references/archival-protocol.md) — Completion manifest template, artifact move protocol, and verification steps (used by Nyx in Phase 5)


## Lifecycle Enforcement Gates

### Coordinated Plan Preflight (Hard Gate)

For six or more coordinated plans, `Exec-PlanGate` is mandatory and fail-closed. No `Exec-Manager` dispatch is permitted without a recorded current `PASS`. The gate checks dependency completeness, contract consistency, layer compliance, DD coverage, downstream gaps (symbols needed but never created upstream), overlap/parallel-write safety, and ownership closure. Ownership closure requires every caller file for each changed symbol signature, return type, or behavior; handoff annotations do not satisfy it. Exec-Manager verifies the gate result and never spawns the gate.

For a coordinated group of **five or fewer** plans, the gate is **not required**. Invoking the gate is still allowed for a smaller group, but every invocation must record a `NOT_REQUIRED` verdict (or an equivalent explicitly-labeled result) so no result is ambiguous. A recorded `NOT_REQUIRED` is not a stale or missing `PASS`: dispatch proceeds on `NOT_REQUIRED`, never on an absent result, and a later plan-count increase to six or more invalidates any prior `NOT_REQUIRED` and requires a fresh gate `PASS`.

### Startup Lifecycle Sweep

Before starting a feature family, inspect every plan status. Fully checked plans must be archived or explicitly marked `complete, awaiting QA`; a plan with zero open steps is not in flight. Forbid duplicate basenames across `pending/` and `completed/`, and forbid stray backup files. A superseded plan or DD is removed from the executable set before dispatch.

### Strengthened Rule 7: Archive the Whole Feature

After all plans pass QA, archive every plan and the DD to `completed/`, generate `COMPLETION.md`, and assert that no feature files remain in `pending/` or `designs/parts/`. Do not report completion while any process artifact or handoff remains executable.

### CI Evidence Location

CI-gating manifests and evidence must live in tracked repository paths, never under the gitignored `artifacts/` tree, and static YAML or manifest presence is never `CI_PASS`. The `LOCAL_PASS` / `LOCAL_UNAVAILABLE` / `CI_DEFERRED` / `CI_PASS` labels are owned by `config/skills/ci-lint-test-gates/SKILL.md`; this section references that canonical owner. Preserve the label recorded by the producing gate and never relabel local or deferred evidence as `CI_PASS`.
