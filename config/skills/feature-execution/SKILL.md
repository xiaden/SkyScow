---
name: feature-execution
description: Execute a complete set of dependency-ordered implementation plans for one feature. Use when the user asks to implement or work through plans and all lettered plans are present and valid; do not use for creating plans, decomposing designs, or executing a single plan.
---

# Feature Execution

Pipeline for implementing a set of feature plans produced by `decomposing-design-documents`. Uses a manager-owned capability graph: Nyx → Exec-Manager → selected Worker/support capabilities → independent QA → bounded revalidation.

```
Plans + Ledger → compose local execution graph → selected implementation/support nodes → mandatory QA → bounded revalidation → Update Ledger → Archive
                                      ↓                                      ↓                                      ↓
                         dependencies and safe concurrency             Manager routes findings          complete-set lifecycle
```

The graph is observability and routing guidance, not a new registry, phase DAG, or DSL. Static authority remains unchanged: plans own scope/dependencies, workers implement, support agents advise or diagnose, QA owns independent correctness, and Exec-Manager owns lifecycle without implementing.

### Execution Decision Flowchart

**1. Check prerequisites:**
   - All plans present and schema-valid → proceed to step 2
   - Any missing or invalid → stop; run `decomposing-design-documents` or fix the plan first

**2. For each plan in dependency order, dispatch one Exec-Manager and handle the response.**

   **When plans are independent** (both share the same dependency and neither depends on the other), dispatch them in **parallel**. Fan out when safe — let Exec-Managers run concurrently, then collect results.

   **When plans have sequential dependencies** (Plan B requires Plan A's outputs), dispatch one at a time in order.

   For each dispatch:
    - `DONE` → verify no unresolved `CURRENT_PLAN` or `PLANNING_GAP` findings, record any validated `DOWNSTREAM_PLAN` carry-forward, update the ledger (Phase 3), then return to step 2 for the next plan(s)
   - `BLOCKED` → investigate the blocker; if resolvable provide guidance and re-dispatch; if not, stop and notify the user
   - `ESCALATE` → stop immediately; present the blocker to the user; do not retry

**3. When all plans have returned `DONE`:**
   - Confirm every plan in the present, schema-valid, non-superseded ordered set passed its mandatory QA gate and all carry-forward findings were resolved by their owning later plans
   - Only then archive the feature (Phase 5); never claim feature completion or archival while a later plan remains incomplete

---

## Capability Graph and Static Gates

Nyx dispatches one Exec-Manager per plan. Each manager composes only the capabilities needed by observed execution results:

- Exec-Worker for assigned implementation scope, conservatively one sequential phase at a time.
- Exec-Fixer for known bounded defects with explicit issue lists.
- Support-Debugger only when the cause is unclear; it routes `SIMPLE` to Fixer, `NEEDS_PLAN` to Planner AMEND, and `INCONCLUSIVE` to escalation.
- Exec-Planner for `PLANNING_GAP`, architectural contradiction, or debugger-authorized amendment; affected work is re-executed.
- Support-PatternEnforcer only for accepted impact closure or migration scope.
- QA-Reviewer remains mandatory and independent before acceptance; it consumes canonical `qa-applicability.md`.

Independent plans may run concurrently only when README metadata proves no dependency or write overlap. Within a plan, phases remain sequential unless prerequisites, outputs/annotations, write scopes, and order irrelevance prove safe independence. Exec-Manager owns routing, ledger actuals, carry-forward, and archival; Nyx receives `DONE | BLOCKED | ESCALATE`.

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
2. Parts README exists: `artifacts/designs/pending/{feature}/README.md`
3. Contracts ledger exists: `artifacts/designs/pending/{feature}/CONTRACTS.md`
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

For each plan in dependency order, dispatch a Exec-Manager with the current plan and validated ordered plan set. Dispatch independent plans in parallel (see Rule 4).

### 2a. Quality Handoff (Enforced by Exec-Manager)

Each Exec-Manager runs the repository-defined checks relevant to the changed surface and its independent QA review before returning DONE. The implementation plan remains responsible for implementation steps, dependencies, contracts, and explicit requested/architectural deliverables; QA owns post-implementation test and documentation applicability, generation, and corrective work.

| Gate | Check | Standard |
|------|-------|----------|
| **Repository checks** | Checks selected from the observable changed surface and repository capabilities | Required when applicable; no invented commands |
| **Layer Compliance** | No upward imports, correct DI patterns | Mandatory — blocks DONE |
| **Contract Adherence** | Actual signatures match authoritative shared contracts | Mandatory — blocks DONE |
| **Code Quality** | Repository/project coding standards | Mandatory — blocks DONE |
| **QA correctness** | Independent review of the implemented current-plan slice | Mandatory — blocks DONE |
| **Test/Documentation QA** | Canonical analyzers/generators when their applicability triggers hold | Conditional QA ownership — never a universal plan deliverable |
| **Completeness** | All current-plan implementation steps and authoritative current-plan responsibilities delivered | Mandatory — current-plan omissions and unowned implementation gaps block DONE |
| **Drift Detection** | Implementation matches accepted requirements and architectural intent without scope creep | Mandatory |

Fix cycles resolve current-plan-owned implementation issues before DONE. Valid downstream-owned implementation work is reported as carry-forward; QA-owned test/documentation work is routed through QA and does not become a planning gap merely because it was absent from the plan.

### Coordinated-Plan QA Semantics

Each plan is a bounded implementation slice in the dependency-ordered plan set. Exec-Manager and QA-Reviewer evaluate the current plan against its own steps, contracts, and deliverables, while receiving the validated ordered plan set for incomplete-work classification. `CURRENT_PLAN` findings block normally. `DOWNSTREAM_PLAN` findings must name a present, schema-valid, non-superseded later plan in the same set; they are reported and carried forward without blocking the current plan. `PLANNING_GAP` findings have no valid owner and remain blocking/escalatory. This rule applies identically to correctness, boundary, journey, domain-risk, test, and documentation findings. Feature completion and archival still require every plan to return DONE.

### 2b. Dispatch Exec-Manager

```yaml
# Dispatch to Exec-Manager agent
contextFiles:
  - artifacts/plans/pending/TASK-{feature}-{letter}-{title}.md    # The plan
  - artifacts/designs/pending/{feature}/CONTRACTS.md      # Current contracts
  - artifacts/designs/pending/{feature}/README.md         # Feature structure
  - artifacts/designs/pending/{feature}/DD.md               # Design doc
  - {layer_instructions_file}  # Per layer in this plan

task:
  plan: "TASK-{feature}-{letter}-{title}"
  startPhase: 1         # Or resume from incomplete
  reviewRequired: true
  currentPlan: "TASK-{feature}-{letter}-{title}"
  orderedPlanSet: ["TASK-{feature}-A-{title}", "TASK-{feature}-B-{title}"]
  orderedPlanSetValidation: "present, schema-valid, non-superseded, dependency-ordered"
```

After all plans required for the coordinated group exist and are individually valid, Exec-Planner evaluates observable coordination-risk triggers—cross-plan contracts, shared writes/schemas/migrations/registries, nontrivial ordering/reorder, multi-plan migration, multi-plan DD amendments, generational supersession, or unresolved ownership closure. Triggered groups require the read-only Exec-PlanGate preflight and `PASS` before any Exec-Manager is dispatched. Untriggered groups receive a Planner-owned `plan_gate: status: NOT_REQUIRED` record with observable rationale. Exec-Manager verifies the current Planner record or gate result; it does not recompute applicability or spawn the gate.

**Exec-Manager handles internally:**

- Dispatching Exec-Worker per phase by default, with safe independent dispatch only when plan metadata proves independence
- Running mandatory independent QA before acceptance of the selected implementation/support graph
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

**Do NOT re-run Exec-Manager for DONE.** The current bounded slice passed its gate; retain any validated `DOWNSTREAM_PLAN` carry-forward and proceed to ledger update. The feature is not complete until every plan in the set passes.

---

## Internal DD Tool Usage

DD operations are performed by internal agents through the registered OpenCode plugin tools `dd_create`, `dd_read`, and `dd_archive`. `dd_create` writes `artifacts/designs/pending/{slug}/DD.md`; `dd_read` accepts a slug or conventional DD name and prefers the pending bundle before the completed bundle; `dd_archive` validates linked plans, sets the DD status to `Completed`, and moves the bundle when possible. Direct `python3 -m common.tools.<module>` invocation is only the focused test boundary. These tools do not introduce generic artifact writes, arbitrary artifact filesystem access, or a user-facing CLI.

## Phase 3: Update Ledger

After Exec-Manager returns DONE:

1. **Verify carry-forward:** every `DOWNSTREAM_PLAN` finding names a present, schema-valid, non-superseded later plan in the same ordered set; `CURRENT_PLAN` and `PLANNING_GAP` findings must not remain unresolved.
2. **Update CONTRACTS.md** with *actual* implementations, not planned signatures
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

After every plan in the validated ordered set has returned DONE, its mandatory QA gate has passed, all downstream carry-forward findings are resolved, the ledger is updated, and the user is informed of deviations — archive the feature. Never archive while a later plan remains incomplete. DD completion is represented by the DD's `**Status:** Completed` metadata; a completed bundle may remain under `artifacts/designs/pending/{feature}/` if its move is pending or unsuccessful. No `COMPLETION.md` is generated or required.

See [references/archival-protocol.md](file:///home/opencode/.config/opencode/skills/feature-execution/references/archival-protocol.md) for the DD bundle move protocol, verification steps, and standalone plan handling.

---

## Session Continuity

When starting a new session mid-feature:

1. Read `artifacts/designs/pending/{feature}/README.md` — execution rounds
2. Read `artifacts/designs/pending/{feature}/CONTRACTS.md` — implemented contracts
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

- [ ] All Exec-Managers returned DONE **→ Each plan's bounded responsibilities and all quality gates passed; downstream-owned work was carried into later plans**
- [ ] CONTRACTS.md reflects actual implementations **→ No plan-vs-code drift**
- [ ] Available linter passes on full workspace **→ Zero errors**
- [ ] Test coverage gate applies per `/home/opencode/.config/opencode/instructions/qa-applicability.md` (canonical WHEN/trigger owner); repository-defined coverage policy honored where one exists, otherwise coverage reported as diagnostic (no universal percentage, see `/home/opencode/.config/opencode/instructions/validation-mandate.md`) **→ No coverage regression**
- [ ] Security review applies per `/home/opencode/.config/opencode/instructions/qa-applicability.md` (canonical WHEN/trigger owner); surface list per `/home/opencode/.config/opencode/skills/security-review/SKILL.md` **→ Security-sensitive surfaces covered**
- [ ] No orphaned fix plans with incomplete steps **→ Clean state**
- [ ] User informed of any design deviations **→ Alignment**
- [ ] DD status is `Completed`; no completion manifest is generated or required **→ Authoritative DD completion state**
- [ ] All artifacts moved to `artifacts/plans/completed/` **→ Clean working directory**
- [ ] No feature plan files remain in `artifacts/plans/pending/`; standalone plan archival is complete **→ Verified plan cleanup**
- [ ] If the DD bundle move succeeded, no feature files remain in `artifacts/designs/pending/{feature}/`; if the move is pending or unsuccessful, the completed DD may remain there for retry **→ Bundle cleanup is optional after authoritative completion status**

---

## References

- [references/execution-protocol.md](file:///home/opencode/.config/opencode/skills/feature-execution/references/execution-protocol.md) — Subagent dispatch patterns, prompt templates, and context injection rules (used internally by Exec-Manager)
- [references/review-protocol.md](file:///home/opencode/.config/opencode/skills/feature-execution/references/review-protocol.md) — Review dispatch protocol, checklist, scope classification, and fix cycle limits (used internally by Exec-Manager)
- [references/archival-protocol.md](file:///home/opencode/.config/opencode/skills/feature-execution/references/archival-protocol.md) — DD completion-status, bundle-move protocol, and verification steps (used by Nyx in Phase 5)


## Lifecycle Enforcement Gates

### Coordinated Plan Preflight (Conditional Hard Gate)

When observable coordination-risk triggers apply—cross-plan producer/consumer contracts, shared writes/schemas/migrations/registries, nontrivial ordering or reorder, multi-plan migration, DD amendments affecting multiple plans, generational supersession, or unresolved ownership closure—`Exec-PlanGate` is mandatory and fail-closed. No Exec-Manager dispatch is permitted without a recorded current `PASS`. A large independent group may skip; a small coupled group may require the gate. Plan count alone never selects or skips it. The gate checks dependency completeness, contract consistency, DD coverage, downstream gaps, overlap/parallel-write safety, and ownership closure. Exec-Manager verifies the result and never spawns the gate.

If no observable trigger applies, record `NOT_REQUIRED` with the skip rationale. A missing or stale result is never equivalent to `NOT_REQUIRED`; a newly triggered risk requires a fresh gate `PASS`.

### Startup Lifecycle Sweep

Before starting a feature family, inspect every plan status. Fully checked plans must be archived or explicitly marked `complete, awaiting QA`; a plan with zero open steps is not in flight. Forbid duplicate basenames across `pending/` and `completed/`, and forbid stray backup files. A superseded plan or DD is removed from the executable set before dispatch.

### Strengthened Rule 7: Archive the Whole Feature

After all plans pass QA, archive every plan and update the DD status to `Completed`. Use the registered internal `dd_archive` tool to move the complete DD bundle to `artifacts/designs/completed/{feature}/` when possible. The status remains authoritative if the move is pending or unsuccessful; do not generate or require `COMPLETION.md`, and do not report standalone plan archival as DD completion.
### CI Evidence Location

CI-gating manifests and evidence must live in tracked repository paths, never under the gitignored `artifacts/` tree, and static YAML or manifest presence is never `CI_PASS`. The `LOCAL_PASS` / `LOCAL_UNAVAILABLE` / `CI_DEFERRED` / `CI_PASS` labels are owned by `/home/opencode/.config/opencode/skills/ci-lint-test-gates/SKILL.md`; this section references that canonical owner. Preserve the label recorded by the producing gate and never relabel local or deferred evidence as `CI_PASS`.
