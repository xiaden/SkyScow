---
name: dispatching-agents
description: Use when delegating work to any subagent. Covers dispatch templates for exec, R&D, support, QA, and RW agent types, plus task-vs-delegate selection guidance. Use whenever you need to spawn an agent via the task or delegate tools — this skill provides the correct dispatch template, required fields, expected output, and agent selection guidance. Do NOT use for single-file reads, trivial fixes, or work you can do yourself faster than dispatching.
---

# Dispatching Agents

Produce dispatch prompts that give subagents everything they need in a single pass.

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
| **List every context file.** | The agent starts in a fresh context. It cannot see files you don't name. Every file it should read before acting must be listed. |
| **Include negative constraints.** | Tell the agent what NOT to do. Research agents should not implement. Exec agents should not design. Without this, scope bleeds. |
| **Be specific about output.** | "Tell me what you find" is a briefing, not a dispatch. "Return an ADR in artifacts/decisions/" is a dispatch. |
| **One task per dispatch.** | "Execute the plan AND fix the tests AND update the docs" is three dispatches. Scope-creeping dispatches produce scope-creeping output. |

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
├─ Requires designing a feature? → Dispatch RnD-Manager
│  └─ Needs adversarial validation? → Dispatch RnD-Refiner instead
├─ Requires focused R&D analysis (not full design)?
│  ├─ Implementation options + tradeoffs → RnD-Architect
│  ├─ Creative brainstorming → RnD-Ideator
│  ├─ Effort sizing → RnD-Estimator
│  ├─ Complexity/over-engineering audit → RnD-ComplexityAdvisor
│  └─ Code improvement suggestions → RnD-Improver
├─ Requires parallel isolated workers (no phase dependencies)? → Dispatch RW-Director
├─ Requires checking pattern consistency? → Dispatch Support-PatternEnforcer
├─ Requires reasserting QA gate? → Re-dispatch Exec-Manager (qa-reassertion reference)
└─ Requires targeted post-review fixes (issue list with file:line)? → Dispatch Exec-Fixer
```

### Dispatch Lifecycle

1. **Before dispatch:** Do your own investigation. Read the affected files and check logs/ADRs so you can give the agent concrete context — not "figure out what's wrong."
2. **During dispatch:** Fill every field. List every file. State what the agent must NOT do.
3. **After dispatch:** Verify the output against the expected contract. If malformed or incomplete, re-dispatch with clarification. Log significant findings. Route results to the next step.

### Common Dispatch Failures

| Failure | Symptom | Fix |
|---------|---------|-----|
| Placeholder text | Agent reports back confused or asks "what plan?" | Fill every `[bracket]` with actual data before sending |
| Missing context files | Agent wastes turns asking for files or reads the wrong ones | List every file the agent needs. Check: would YOU know what to read from this prompt? |
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
| Adversarial design refinement (8-turn pipeline) | [`rnd-refiner`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/rnd-refiner.md) |
| Create or refine a design document | [`rnd-dd-author`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/rnd-dd-author.md) |
| Implementation options + tradeoffs | [`rnd-architect`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/rnd-architect.md) |
| Creative solution generation | [`rnd-ideator`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/rnd-ideator.md) |
| Effort sizing (TRIVIAL→EPIC) | [`rnd-estimator`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/rnd-estimator.md) |
| Complexity/over-engineering audit | [`rnd-complexity-advisor`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/rnd-complexity-advisor.md) |
| Code improvement suggestions | [`rnd-improver`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/rnd-improver.md) |

RnD-Manager and RnD-Refiner are orchestrators — they spawn the leaf R&D agents internally. Direct dispatch of leaf R&D agents is valid for focused analysis without a full design workflow.

The adversarial critique agents ([`rnd-counter-ideator`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/rnd-counter-ideator.md) and [`rnd-counter-improver`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/rnd-counter-improver.md)) are spawned by RnD-Refiner in the adversarial pipeline. Direct dispatch is rare.

### QA Department

| Task | Reference |
|------|-----------|
| Full quality gate review (all checks) | [`qa-reviewer`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/qa-reviewer.md) |
| Test coverage and quality analysis | [`qa-test-analyzer`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/qa-test-analyzer.md) |
| Generate tests from coverage gaps | [`qa-test-generator`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/qa-test-generator.md) |
| Documentation coverage analysis | [`qa-docs-analyzer`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/qa-docs-analyzer.md) |
| Generate documentation from gaps | [`qa-docs-generator`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/qa-docs-generator.md) |
| Reassert QA gate when skipped | [`qa-reassertion`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/qa-reassertion.md) |

QA-Reviewer is the primary QA entry point — spawned by Exec-Manager after all implementation phases. QA-TestAnalyzer and QA-DocsAnalyzer are spawned by QA-Reviewer. QA-TestGenerator and QA-DocsGenerator are spawned by their respective analyzers. Direct dispatch of leaf QA agents is valid for standalone coverage assessment.

### Support Department

| Task | Reference |
|------|-----------|
| Diagnose test, runtime, lint, or behavior failures | [`support-debugger`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/support-debugger.md) |
| Gather artifact context (ADRs, logs, design docs) | [`support-librarian`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/support-librarian.md) |
| Check pattern coverage and consistency | [`support-patternenforcer`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/support-patternenforcer.md) |
| Deep codebase or external documentation research | [`support-researcher`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/support-researcher.md) |

All support agents are dispatched directly — they have no internal orchestrator. Support-Librarian should run before any design or planning work in brownfield codebases.

### RW (Rapid Worker) Department

| Task | Reference |
|------|-----------|
| Parallel worker loop (implement → review → continue/stop) | [`rw-director`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/rw-director.md) |
| Decompose goal and fan-out to parallel workers | [`rw-manager`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/rw-manager.md) |
| Isolated sub-task implementation | [`rw-worker`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/rw-worker.md) |
| Validate diff for meaningful progress | [`rw-reviewer`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/rw-reviewer.md) |
| Post-worker mechanical cleanup | [`rw-fixer`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/rw-fixer.md) |

RW-Director is a dumb loop spawner — it delegates to RW-Manager (decomposition + fan-out) and RW-Reviewer (validation), routing on CONTINUE/STOP. Use for straightforward parallel work with no multi-phase dependencies.

## Cross-Cutting Concerns

### QA Gate Enforcement

Exec-Manager **must not** return `DONE` without `qaReview.status: PASS`. If Exec-Manager reports DONE without QA, use the `qa-reassertion` reference to push back.

### Spec-First Testing

Tests written against design documents are expected to fail during implementation. Do NOT dispatch Support-Debugger for spec-first test failures. QA review must classify failures: expected (not yet implemented) vs. actual regressions.

### Pattern Adoption

After a plan introduces a new pattern, verify it propagated everywhere via Support-PatternEnforcer. If `high_confidence` gaps exist, spawn Exec-Planner (AMEND) for a migration phase.

## Dispatch Tools: `task` vs `delegate`

Two tools for spawning agents. Both accept any agent type — there are no permission gates. They differ in **visibility/steering** (can you observe and redirect mid-flight) and **timing** (blocking vs async). The choice is purely about what you need from the execution model.

### `delegate` — Async, Steerable, Survives Compaction

```
delegate(prompt, agent) → returns readable ID immediately
```

- **Returns immediately** — you continue working while the agent runs. No blocking.
- **You can steer mid-flight.** The agent is not a black box. Read its output via `delegation_read(id)` while it runs, course-correct, and ensure the task happened as intended. Empirical test: a `delegate` agent's full output (including intermediate progress) is preserved and retrievable — unlike `task` which suppresses everything but the terminal message.
- **Output persists to disk.** Retrievable via `delegation_read(id)` at any time — survives context compaction. The output is durable where `task` output is ephemeral.
- Sends `<task-notification>` when complete — never poll `delegation_list`.

**Primary use case: Fan-out with steering.** Fire multiple `delegate` calls with the same prompt to different files. All agents run concurrently. You keep working while watching each one — reading their output mid-flight via `delegation_read`, steering them as needed to keep the work consistent across all files. This is the tool for "make the same edit to 12 files and make sure each one gets it right."

**Secondary use cases:** Research that should persist across sessions, fire-and-forget investigation whose output you don't need for the immediate next step, anything where you want the output durable and auditable.

| Use `delegate` when... | Don't use `delegate` when... |
|-------------------------|------------------------------|
| You want to steer the agent mid-flight | The next step depends on the agent's output RIGHT NOW |
| You're fanning out the same task across many files/agents | You need session tree tracking (manager → worker chains) |
| The output should survive context compaction | You need the raw agent message INLINE immediately |
| You want to watch progress and course-correct | — |

### `task` — Synchronous, Opaque Mid-Flight, Inline Return

```
task(prompt, agent) → blocks until agent finishes, returns final message only
```

- **Blocks until the agent finishes.** You get the result inline but you wait for it. The call does not return until the agent exits. Parallel `task` calls (up to 8 in one message) all block together — you get nothing until the slowest finishes.
- **Opaque mid-flight.** The agent's internal work is completely invisible — you cannot audit, steer, or course-correct while it runs. Empirical test: a task agent instructed to announce progress at multiple phases returned only the terminal message; all intermediate output was suppressed. There is no mechanism to read partial progress.
- **Auditable only after completion.** Once the agent returns, you have the final message. But during execution, it's a black box. All steering must happen before dispatch.
- **Result is ephemeral** — lost on compaction unless you explicitly log it.

**Primary use case: Managers that orchestrate workers.** Exec-Manager and RnD-Manager spawn their own workers via `task` — they need the session tree for tracking and the inline result to make routing decisions.

**Secondary use cases:** When the very next step in YOUR workflow depends on the agent's output and you can't proceed without it. Simple delegations where you don't need to steer.

| Use `task` when... | Don't use `task` when... |
|----------------------|--------------------------|
| The NEXT step requires the agent's output | You want to steer/course-correct mid-flight |
| You're spawning a manager (it needs session tree tracking) | The work is fan-out across many files |
| You need the raw agent message inline | Output should survive context compaction |
| Simple, one-shot delegation | You want persistent, auditable output |

### Output Fidelity: `delegate` vs `task`

A critical difference that becomes apparent in testing:

```
delegate output:  "PHASE 1: Researching..." → "PHASE 2: Analyzing..." → "DONE: Complete"
                  └─ All agent output preserved and retrievable

task output:      "DONE: Complete"
                  └─ Intermediate output suppressed; only terminal message survives
```

`delegate` preserves the full transcript — every announcement the agent makes. `task` collapses to the final message. If you need to see what the agent DID (not just what it concluded), use `delegate`.

### Conceptual Difference

```
delegate:  Fire → [agent runs] → you keep working + can steer mid-flight → notification → audit
           └─ Returns ID instantly ─┘   └─ Agent is observable ─┘          └─ Output persists to disk

task:      Fire → [agent runs ... opaque ... ] → result lands inline → you audit now
           └─ You're blocked (or waiting on parallel batch) ─┘  └─ Ephemeral ─┘
```

`delegate` is a remote monitor — you dispatch, watch, and steer. `task` is a courier — you hand off the package and don't hear back until delivery.

### Quick Decision

```
Need to steer the agent mid-flight or fan out across many files?
├─ Yes → delegate (async, steerable; you keep working while watching)
└─ No → consider task

Need agent output for the very next step — can't proceed without it?
├─ Yes → task (blocks until done, result inline)
└─ No → delegate (keep working, retrieve via delegation_read)

Fanning out the same prompt to 5+ files?
├─ Need to ensure consistency across all of them? → delegate (steer each one)
└─ Consistency doesn't matter, just need results fast? → task (up to 8 parallel in one message)

Spawning a manager (Exec-Manager, RnD-Manager)?
└─ task (managers spawn workers — they need the session tree)

Research or investigation where output should persist across sessions?
└─ delegate (persisted to disk, retrievable any time)
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

  **QA:** [`qa-reviewer.md`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/qa-reviewer.md) — Full quality gate review.
  [`qa-test-analyzer.md`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/qa-test-analyzer.md) — Test coverage analysis.
  [`qa-test-generator.md`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/qa-test-generator.md) — Test generation from gaps.
  [`qa-docs-analyzer.md`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/qa-docs-analyzer.md) — Documentation coverage analysis.
  [`qa-docs-generator.md`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/qa-docs-generator.md) — Documentation generation from gaps.
  [`qa-reassertion.md`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/qa-reassertion.md) — Reassert QA gate when Exec-Manager skips review.

  **Support:** [`support-debugger.md`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/support-debugger.md) — Root cause analysis for failures.
  [`support-librarian.md`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/support-librarian.md) — Artifact context (ADRs, logs, design docs).
  [`support-patternenforcer.md`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/support-patternenforcer.md) — Pattern coverage and consistency checks.
  [`support-researcher.md`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/support-researcher.md) — Deep codebase and external research.

  **RW:** [`rw-director.md`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/rw-director.md) — Parallel worker loop (implement → review → continue/stop).
  [`rw-manager.md`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/rw-manager.md) — Decompose goal and fan-out.
  [`rw-worker.md`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/rw-worker.md) — Isolated sub-task implementation.
  [`rw-reviewer.md`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/rw-reviewer.md) — Validate diff for meaningful progress.
  [`rw-fixer.md`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/rw-fixer.md) — Post-worker mechanical cleanup.

- **Related skills:** `capture-subsystem` (codebase research skills), `creating-auto-injected-instructions` (instruction files for layer conventions)
