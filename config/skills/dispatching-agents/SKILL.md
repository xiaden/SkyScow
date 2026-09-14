---
name: dispatching-agents
description: Prepare and route subagent dispatches using canonical agent templates and handoff contracts. Use when spawning a subagent with native task; do not use for single-file lookups, trivial fixes, or work you can do directly.
---

# Dispatching Agents

Produce dispatch prompts that give subagents everything they need in a single pass.

## Non-Negotiable Context Boundary

Every dispatched or tasked agent starts with **NO context** from the calling
agent. It does not inherit the conversation, reasoning, files read, tool
results, decisions, assumptions, or working memory. Native `task` children have
this same context boundary, so prompts must carry all required context.

Before **any** dispatch, open the exact per-agent reference linked below and
follow its template and output contract. Put every required fact in the prompt
itself, or link to a specific file, artifact, plan, symbol, or line range the
agent must read. Never write "as discussed," "the above," "use the context,"
or "you know the codebase": those references do not exist for the new agent.

The per-agent reference is the authority for that dispatch. This skill routes
to it; it does not replace it.

## When NOT to Dispatch

Do NOT use this skill — do the work directly — when:

| Skip dispatch when... | Do this instead |
|-----------------------|-----------------|
| A single file read or lookup is enough | Use `read` or `aft_search` directly |
| The fix is trivial (typo, missing import, one-line change) | Fix it yourself — faster than the dispatch overhead |
| You can diagnose a failure from reading 2–3 files | Read the files and fix directly |
| You're just exploring code structure | Use `aft_outline` / `aft_zoom` yourself |

Dispatching for anything in the left column wastes context and turns. The decision tree below covers when to dispatch — these are the hard stops.

## Universal Dispatch Skeleton

Every agent dispatch follows this structure. Agent-specific templates in references/ extend it with their own required fields and output contracts.

**Route directly to the per-agent file:** every dispatch prompt must name and
follow the matching reference under
`/home/opencode/.config/opencode/skills/dispatching-agents/references/` (for
example, `references/exec-worker.md`). Do not invent an alternate template
from this overview. The selected per-agent file must be opened before calling
native `task`.

```
Dispatch [AGENT] to [TASK].

Context files to read:
- [every file the agent needs — never make it guess]

[Agent-specific fields — see the relevant reference file]

Do NOT: [negative constraints — what the agent must not do]
```

### Rules That Apply to Every Dispatch

| Rule | Why |
|------|-----|
| **Fill every bracketed field.** | Placeholder text like `[PLAN_PATH]` or `{feature}` gives the agent no information. If you leave a bracket, you haven't dispatched. |
| **List every context file.** | The agent starts with NO inherited context. It cannot see files you don't name. Every file it should read before acting must be listed, with relevant symbols or line ranges where useful. |
| **Restate all non-file context.** | User requirements, constraints, prior decisions, hypotheses, failure output, and expected behavior must be directly stated or linked to a durable artifact. Never rely on conversation history. |
| **Include negative constraints.** | Tell the agent what NOT to do. Research agents should not implement. Exec agents should not design. Without this, scope bleeds. |
| **Be specific about output.** | "Tell me what you find" is a briefing, not a dispatch. "Return an ADR in artifacts/decisions/" is a dispatch. |
| **One task per dispatch.** | "Execute the plan AND fix the tests AND update the docs" is three dispatches. Scope-creeping dispatches produce scope-creeping output. |

For design, planning, implementation, and QA handoffs, include the original
user request verbatim and an immutable requirement ledger. The request may have
arrived only as a user message; do not assume a `task.md` file exists. The
ledger must identify mandatory capabilities, behaviors, CLI semantics, defaults,
safety rules, and definition-of-done items. Downstream agents must compare their
output against it. Summaries and derived artifacts never replace the original
request.

### Dispatch Decision Tree

```
Task at hand
├─ A single file read or lookup? → Do it yourself (no dispatch)
├─ A trivial fix (typo, missing import)? → Fix it directly
├─ Requires deep multi-file investigation? → Dispatch Support-Researcher (standard depth)
├─ Requires understanding prior decisions/logs/design docs? → Dispatch Support-Librarian first
├─ Requires diagnosing a failure? → Read affected files yourself first
│  ├─ Cause is obvious after reading → Fix directly
│  └─ Cause is unclear → Dispatch Support-Debugger
├─ Requires implementing from a plan? → Dispatch Exec-Manager
├─ Requires creating/amending a plan? → Dispatch Exec-Planner
├─ Requires designing a feature or formal DD? → Dispatch RnD-Manager
│  └─ RnD-Manager owns the complete DD workflow and dispatches RnD-Refiner when DD_REQUIRED
├─ Requires focused R&D analysis (not full design)?
│  ├─ Implementation options + tradeoffs → RnD-Architect
│  ├─ Creative brainstorming → RnD-Ideator
│  ├─ Effort sizing → RnD-Estimator
│  ├─ Complexity/over-engineering audit → RnD-ComplexityAdvisor
│  └─ Code improvement suggestions → RnD-Improver
├─ Requires checking pattern consistency? → Dispatch Support-PatternEnforcer
├─ Requires reviewing a whole GitHub tree (not a push)? → Dispatch QA-RepoReviewManager
├─ Requires candidate push-gate validation/publication? → Dispatch QA-PushManager
├─ Requires reasserting QA gate? → Re-dispatch Exec-Manager (qa-reassertion reference)
└─ Requires targeted post-review fixes (issue list with file:line)? → Dispatch Exec-Fixer
```

### Dispatch Lifecycle

1. **Before dispatch:** Select and open the exact per-agent reference linked in the Agent Selection tables. Do your own investigation and check logs/ADRs so you can give the agent concrete context — not "figure out what's wrong."
2. **During dispatch:** Fill every field in that per-agent reference. List every file and artifact. Directly state every requirement, decision, constraint, hypothesis, and expected output. State what the agent must NOT do.
3. **After dispatch:** Verify the output against the expected contract. If malformed or incomplete, re-dispatch with clarification. Log significant findings. Route results to the next step.

### Common Dispatch Failures

| Failure | Symptom | Fix |
|---------|---------|-----|
| Placeholder text | Agent reports back confused or asks "what plan?" | Fill every `[bracket]` with actual data before sending |
| Missing context files | Agent wastes turns asking for files or reads the wrong ones | List every file the agent needs. Check: would YOU know what to read from this prompt? |
| Implicit parent context | Agent assumes facts, decisions, or prior tool output that were only present in the caller's session | Restate it in the prompt or link a durable artifact; assume the agent knows nothing |
| No negative constraints | Agent over-steps — researcher writes code, planner implements | Always add "Do NOT" — the bolded worker-spawn blocks in manager references exist for this reason |
| Wrong agent for the task | Output doesn't match expectations or is formatted wrong | Check the selection table. Exec agents don't design. R&D agents don't execute. |
| Too broad scope | Agent returns shallow, surface-level results | Narrow to one feature, one module, one decision. Multi-part work → multiple dispatches. |
| Skipping Librarian in brownfield work | Agent proposes patterns that contradict existing ADRs | Always dispatch Support-Librarian before design or planning work on existing codebases. |
| Dispatching for a single-file read | Wasted context, slower than doing it yourself | If a `read` or `aft_search` call answers it, don't dispatch. |

## Agent Selection

### Exec Department

| Task | Reference |
|------|-----------|
| Execute an implementation plan | [`exec-manager`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/exec-manager.md) |
| Create, amend, or reorder plans | [`exec-planner`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/exec-planner.md) |
| Targeted repairs for MINOR review issues | [`exec-fixer`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/exec-fixer.md) |
| Implement a scoped plan phase | [`exec-worker`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/exec-worker.md) |

Exec-Manager spawns Exec-Worker per phase and Exec-Fixer for MINOR issues. Direct dispatch of Exec-Worker or Exec-Fixer is rare — prefer routing through Exec-Manager.

### R&D Department

| Task | Reference |
|------|-----------|
| Full R&D workflow (design doc, tradeoffs, estimates) | [`rnd-manager`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/rnd-manager.md) |
| Adversarial design refinement (8-turn pipeline; only from RnD-Manager) | [`rnd-refiner`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/rnd-refiner.md) |
| Create or refine a design document (only from RnD-Manager) | [`rnd-dd-author`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/rnd-dd-author.md) |
| Implementation options + tradeoffs | [`rnd-architect`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/rnd-architect.md) |
| Creative solution generation | [`rnd-ideator`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/rnd-ideator.md) |
| Effort sizing (TRIVIAL→EPIC) | [`rnd-estimator`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/rnd-estimator.md) |
| Complexity/over-engineering audit | [`rnd-complexity-advisor`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/rnd-complexity-advisor.md) |
| Code improvement suggestions | [`rnd-improver`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/rnd-improver.md) |

RnD-Manager is the sole orchestrator for a formal DD. It dispatches Librarian,
Researcher, Refiner, Architect, ComplexityAdvisor, Estimator, DDAuthor, and
PatternEnforcer in its canonical order. RnD-Refiner is a nested orchestrator
only for its fixed eight-turn adversarial sequence. DDAuthor never orchestrates
other R&D agents. Direct dispatch of leaf R&D agents is valid only for focused
analysis outside a formal DD workflow.

The adversarial critique agents ([`rnd-counter-ideator`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/rnd-counter-ideator.md) and [`rnd-counter-improver`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/rnd-counter-improver.md)) are spawned by RnD-Refiner in the adversarial pipeline. Direct dispatch is rare.

### QA Department

| Task | Agent | Reference |
|------|-------|-----------|
| Final publication gate: validate an isolated candidate snapshot, adversarially review, and push only the exact validated SHA when authorized | `qa-push-manager` | [`qa-push-manager`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/qa-push-manager.md) |
| Full quality gate review (all checks) | `qa-reviewer` | [`qa-reviewer`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/qa-reviewer.md) |
| Independent correctness and contract review | `qa-reviewer-correctness` | [`qa-reviewer-correctness`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/qa-reviewer-correctness.md) |
| Independent boundary and failure review | `qa-reviewer-boundary` | [`qa-reviewer-boundary`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/qa-reviewer-boundary.md) |
| Independent end-to-end journey review | `qa-reviewer-journey` | [`qa-reviewer-journey`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/qa-reviewer-journey.md) |
| Independent review for one explicitly assigned technical risk lens (one invocation per lens) | `qa-reviewer-domainrisk` | [`qa-reviewer-domainrisk`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/qa-reviewer-domainrisk.md) |
| One-shot whole-tree GitHub review: resolve an explicit full tree URL to an exact ref, review the complete current-head tree from an immutable detached snapshot, dispatch read-only reviewers in canonical batched parallel groups, and fail closed on collection failure | `qa-repo-review-manager` | [`qa-repo-review-manager`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/qa-repo-review-manager.md) |
| Whole-tree correctness and contract review (permanent lens) | `qa-repo-reviewer-correctness` | [`qa-repo-reviewer-correctness`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/qa-repo-reviewer-correctness.md) |
| Whole-tree boundary and failure review (dispatched when the tree contains boundary surfaces per the canonical applicability reference) | `qa-repo-reviewer-boundary` | [`qa-repo-reviewer-boundary`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/qa-repo-reviewer-boundary.md) |
| Whole-tree end-to-end journey review (dispatched when the tree contains journey surfaces per the canonical applicability reference) | `qa-repo-reviewer-journey` | [`qa-repo-reviewer-journey`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/qa-repo-reviewer-journey.md) |
| Whole-tree review for one explicitly assigned technical risk lens (exactly one lens per invocation; batching and the concurrency cap are owned by the canonical applicability reference) | `qa-repo-reviewer-domainrisk` | [`qa-repo-reviewer-domainrisk`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/qa-repo-reviewer-domainrisk.md) |
| Test coverage and quality analysis | `qa-test-analyzer` | [`qa-test-analyzer`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/qa-test-analyzer.md) |
| Generate tests from coverage gaps | `qa-test-generator` | [`qa-test-generator`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/qa-test-generator.md) |
| Documentation coverage analysis | `qa-docs-analyzer` | [`qa-docs-analyzer`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/qa-docs-analyzer.md) |
| Generate documentation from gaps | `qa-docs-generator` | [`qa-docs-generator`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/qa-docs-generator.md) |
| Reassert QA gate when skipped | `qa-reassertion` | [`qa-reassertion`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/qa-reassertion.md) |

QA-Reviewer is the primary post-change QA entry point, invoked by Exec-Manager after changes are made. `qa-push-manager` is the final publication gate for a candidate commit: it validates an isolated disposable snapshot of the candidate at the candidate SHA and, only after deterministic validation is green, spawns the read-only reviewers selected per `/home/opencode/.config/opencode/instructions/qa-applicability.md` — correctness always, plus boundary, journey, and every matched domain-risk lens, dispatched in the canonical lens order and 0 / 1–3 / >3 batching rule owned there — with each DomainRisk invocation confined to its `assigned_lens`. The adversarial reviewers are read-only, work from the same immutable candidate context, never consume each other's findings, and must not be dispatched before deterministic validation is green. Reviewer infrastructure failure fails closed (REVIEW INFRASTRUCTURE FAILURE). QA-PushManager pushes only the exact validated commit object and only when explicitly authorized; otherwise it reports the validated candidate without pushing. QA-TestAnalyzer and QA-DocsAnalyzer are spawned by QA-Reviewer when their canonical applicability triggers fire; each spawns QA-TestGenerator or QA-DocsGenerator only for a dispatch-tier result (`MINOR_DISPATCH` or `MAJOR_DISPATCH`), while a `PASS`/`MINOR_PASS` run dispatches no generator and an implementation/systemic escalation runs no generator. Tier-to-generator routing is owned by the "Analyzer and generator contract" section of `/home/opencode/.config/opencode/instructions/qa-applicability.md`. Direct dispatch of leaf QA agents is valid for standalone assessment when the owning manager is not required.

QA-RepoReviewManager is the separate whole-tree GitHub review entry point, distinct from the standalone code-review gate (`qa-reviewer`) and the push/publication `qa-push-manager`. It accepts exactly one explicit full HTTPS GitHub tree URL (`https://github.com/<owner>/<repository>/tree/<exact-ref>`), resolves the named ref to its run-start head, materializes the complete current-head tree as an immutable detached snapshot, and reviews that complete tree — never a diff and never a candidate commit; the resolved SHA is provenance only. It never pushes, never operates a push gate, and shares no mutable state with the push suite. Its read-only reviewers (`qa-repo-reviewer-correctness`, `qa-repo-reviewer-boundary`, `qa-repo-reviewer-journey`, plus `qa-repo-reviewer-domainrisk` once per matched lens, dispatched in the canonical order and concurrency/batching rule owned by the canonical applicability reference) are dispatched in canonical batched parallel groups with one immutable review context and never consume one another's output; collection fails closed as `REVIEW_INFRASTRUCTURE_FAILURE`. Before any manager GitHub operation, load and apply the applicable guidance selected through `gg-router` (`gg-repos`, `gg-env`, `gg-core`, `ggt-conventions`); never improvise GitHub or Git behavior from memory. Direct dispatch of the whole-tree reviewers outside QA-RepoReviewManager is not valid.

### Support Department

| Task | Reference |
|------|-----------|
| Diagnose test, runtime, lint, or behavior failures | [`support-debugger`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/support-debugger.md) |
| Gather artifact context (ADRs, logs, design docs) | [`support-librarian`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/support-librarian.md) |
| Check pattern coverage and consistency | [`support-patternenforcer`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/support-patternenforcer.md) |
| Deep codebase or external documentation research | [`support-researcher`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/support-researcher.md) |

All support agents are dispatched directly — they have no internal orchestrator. Support-Librarian should run before any design or planning work in brownfield codebases.

## Cross-Cutting Concerns

### QA Gate Enforcement

Exec-Manager **must not** report completion without `qaReview.status: PASS`. If completion is reported without QA, use the `qa-reassertion` reference to push back.

### Spec-First Testing

Spec-first / RED-first testing is surface-dependent, selected from observable repository/task facts per `/home/opencode/.config/opencode/instructions/validation-mandate.md`. Apply it only when the changed surface has a meaningful executable oracle — a regression test can reproduce the defect, the repository already follows a test-first style, or a spec-first test resolves genuine spec ambiguity. Do not force RED for non-test-first surfaces (for example documentation-only or configuration-only changes with no executable oracle). Where it applies, tests written against design documents are expected to fail during implementation — do NOT dispatch Support-Debugger for those expected spec-first failures. QA review must classify failures: expected (not yet implemented) vs. actual regressions.

### Pattern Adoption

After a plan introduces a new pattern, verify it propagated everywhere via Support-PatternEnforcer. If `high_confidence` gaps exist, spawn Exec-Planner (AMEND) for a migration phase.

## Dispatch Tool: native `task`

Native OpenCode `task` is the standard mechanism for spawning agents. Every child
starts with no caller context, so the prompt is the complete handoff. Independent
child calls issued in one assistant message run concurrently and return their
results together; dependent work remains ordered.

```text
task(prompt, agent) → returns the child result when it finishes
```

- Foreground tasks return the result needed for the caller's next decision.
- Multiple independent tasks may be fanned out in one message (bounded by the
  runtime); collect all required results before dependent decisions.
- Managers use native `task` so the parent/child session tree is retained.
- Durable findings belong in the appropriate log or artifact, not in a custom
  delegation store.

### Quick Decision

```
Need independent child results before proceeding?
├─ Yes → parallel native `task` calls (concurrent, result-bearing)
└─ No → use native `task` as needed

Need agent output for the very next step?
├─ Yes → task (blocks until done, result inline)
└─ No → proceed without custom background lifecycle

Spawning a manager (Exec-Manager, RnD-Manager)?
└─ task (managers spawn workers and retain the session tree)
```

## References

- **This skill's references:** — self-contained dispatch guides, one per agent type, organized by department:

  **Exec:** [`exec-manager.md`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/exec-manager.md) — Plan execution lifecycle, QA gate enforcement, fix cycles.
  [`exec-planner.md`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/exec-planner.md) — Plan creation, amendment, reordering.
  [`exec-fixer.md`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/exec-fixer.md) — Targeted MINOR issue repairs.
  [`exec-worker.md`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/exec-worker.md) — Scoped plan phase implementation.

  **R&D:** [`rnd-manager.md`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/rnd-manager.md) — Feature design, R&D, tradeoff analysis (orchestrator).
  [`rnd-refiner.md`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/rnd-refiner.md) — Adversarial design refinement pipeline.
  [`rnd-dd-author.md`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/rnd-dd-author.md) — Design document creation.
  [`rnd-architect.md`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/rnd-architect.md) — Implementation options + tradeoffs.
  [`rnd-ideator.md`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/rnd-ideator.md) — Creative solution generation.
  [`rnd-estimator.md`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/rnd-estimator.md) — Effort sizing.
  [`rnd-complexity-advisor.md`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/rnd-complexity-advisor.md) — Complexity/over-engineering audit.
  [`rnd-improver.md`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/rnd-improver.md) — Code improvement suggestions.
  [`rnd-counter-ideator.md`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/rnd-counter-ideator.md) — Adversarial approach critique.
  [`rnd-counter-improver.md`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/rnd-counter-improver.md) — Adversarial pattern critique.

  **QA:** [`qa-push-manager`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/qa-push-manager.md) — Final validation and publication gate.
  [`qa-reviewer-correctness`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/qa-reviewer-correctness.md) — Correctness, contract, and regression review.
  [`qa-reviewer-boundary`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/qa-reviewer-boundary.md) — Boundary, degraded-state, and failure review.
  [`qa-reviewer-journey`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/qa-reviewer-journey.md) — End-to-end journey review.
  [`qa-reviewer-domainrisk`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/qa-reviewer-domainrisk.md) — Assigned technical risk review.
  [`qa-reviewer`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/qa-reviewer.md) — Full quality gate review.
  [`qa-test-analyzer`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/qa-test-analyzer.md) — Test coverage analysis.
  [`qa-test-generator`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/qa-test-generator.md) — Test generation from gaps.
  [`qa-docs-analyzer`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/qa-docs-analyzer.md) — Documentation coverage analysis.
  [`qa-docs-generator`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/qa-docs-generator.md) — Documentation generation from gaps.
  [`qa-reassertion`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/qa-reassertion.md) — Reassert QA gate when Exec-Manager skips review.
  [`qa-repo-review-manager`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/qa-repo-review-manager.md) — One-shot whole-tree GitHub review manager (explicit tree URL; never a push gate).
  [`qa-repo-reviewer-correctness`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/qa-repo-reviewer-correctness.md) — Whole-tree correctness reviewer (permanent lens).
  [`qa-repo-reviewer-boundary`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/qa-repo-reviewer-boundary.md) — Whole-tree boundary/failure reviewer (dispatched when boundary surfaces are present).
  [`qa-repo-reviewer-journey`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/qa-repo-reviewer-journey.md) — Whole-tree end-to-end journey reviewer (dispatched when journey surfaces are present).
  [`qa-repo-reviewer-domainrisk`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/qa-repo-reviewer-domainrisk.md) — Whole-tree single assigned-lens specialist reviewer.
   [`qa-repo-review-authorized-pilot`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/qa-repo-review-authorized-pilot.md) — Optional disposable-repository pilot checklist; no live success is implied.

  **Support:** [`support-debugger.md`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/support-debugger.md) — Root cause analysis for failures.
  [`support-librarian.md`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/support-librarian.md) — Artifact context (ADRs, logs, design docs).
  [`support-patternenforcer.md`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/support-patternenforcer.md) — Pattern coverage and consistency checks.
  [`support-researcher.md`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/support-researcher.md) — Deep codebase and external research.

- **Related skills:** `capture-subsystem` (codebase research skills)


## Lifecycle Validation Before Dispatch

Every design, planning, or execution dispatch must validate DD status and requirement conformance before handing work downstream. Accept a DD only with a recognized accepted status (`Accepted` or `Complete (accepted)`), including an accepted DD intentionally held in `pending/` only when its metadata names the prerequisite disposition, responsible owner, and next transition condition; reject `Proposed`, `Draft`, `Rejected`, stale/invalid pending DDs, and any execution or archival of an unaccepted DD.

For plan families, the dispatcher must require ownership closure: each changed symbol contract has every caller file named in `Ownership`; a handoff annotation is not coverage. Ownership-closure evidence is a call-graph/import check that lists resolved and unresolved edges, a manual disposition for every unresolved edge (with a reason it is safe or a follow-up that resolves it), and a mock-versus-real caller integration test for every signature or return-type change. Reject missing or stale status, missing caller ownership, unresolved supersession, and `REQUIREMENT_DRIFT` rather than dispatching an unaudited family. Generational families are permitted only with an explicit predecessor → successor graph, bounded scope, supersession metadata/back-pointers, and a recorded Exec-PlanGate `PASS`. Support-Librarian and Support-PatternEnforcer dispatches must use the same checks when validating DDs or plans.
