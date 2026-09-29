---
name: dispatching-agents
description: Construct a correct handoff for an already-selected agent using its per-agent dispatch reference and output contract. Use after work-routing has selected the owner; do not use to choose which specialist owns the work.
---

# Dispatching Agents

Given an agent whose owner has already been selected, this skill constructs the
dispatch prompt that gives it everything it needs in a single pass.

## Skill Precondition — Owner First

The caller must already have selected the owner using the **`work-routing`** skill
or another explicit authoritative workflow. This skill owns **dispatch mechanics**:
given a selected agent X, **how** do I dispatch X correctly? It does **not** answer
**who** owns the next step.

- Do not use this skill to decide direct-versus-delegated work, which specialist
  should own a task, R&D / Change DAG / QA ownership, or Support-Librarian /
  Support-Researcher selection. That policy lives in `work-routing`.
- This skill must not silently reroute the task. If the requested agent conflicts
  with a hard capability or permission constraint, report the mismatch and the
  constraint — do not substitute a different owner on your own.
- Selecting the owner and constructing the dispatch are separate steps. Follow the
  selection you were given.

## Non-Negotiable Context Boundary

Every dispatched or tasked agent starts with **NO context** from the calling
agent. It does not inherit the conversation, reasoning, files read, tool
results, decisions, assumptions, or working memory. Native `task` children have
this same context boundary, so prompts must carry all required context.

Before **any** dispatch, open the exact per-agent reference linked below and
follow its template and output contract. Put every required fact in the prompt
itself, or link to a specific file, artifact, Change DAG, symbol, or line range the
agent must read. Never write "as discussed," "the above," "use the context,"
or "you know the codebase": those references do not exist for the new agent.

The per-agent reference is the authority for that dispatch's required fields and
output contract. This skill selects and extends that reference; it does not
replace it.

## Universal Dispatch Skeleton

Every agent dispatch follows this structure. Agent-specific templates in references/ extend it with their own required fields and output contracts.

**Route directly to the per-agent file:** every dispatch prompt must name and
follow the matching reference under
`/home/opencode/.config/opencode/skills/dispatching-agents/references/` (for
example, `references/change-dag-author.md`). Do not invent an alternate template
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
| **Fill every bracketed field.** | Placeholder text like `[DAG_PATH]` or `{slug}` gives the agent no information. If you leave a bracket, you haven't dispatched. |
| **List every context file.** | The agent starts with NO inherited context. It cannot see files you don't name. Every file it should read before acting must be listed, with relevant symbols or line ranges where useful. |
| **Restate all non-file context.** | User requirements, constraints, prior decisions, hypotheses, failure output, and expected behavior must be directly stated or linked to a durable artifact. Never rely on conversation history. |
| **Include negative constraints.** | Tell the agent what NOT to do. Research agents should not implement. Change-DAG authors should not edit source. Without this, scope bleeds. |
| **Be specific about output.** | "Tell me what you find" is a briefing, not a dispatch. "Read ADR-003 by identity with `adr_read(name=\"ADR-003\")`" is a dispatch. |
| **One task per dispatch.** | "Execute the DAG AND fix the tests AND update the docs" is three dispatches. Scope-creeping dispatches produce scope-creeping output. |

For design, decomposition, implementation, and QA handoffs, include the original
user request verbatim and an immutable requirement ledger. The request may have
arrived only as a user message; do not assume a `task.md` file exists. The
ledger must identify mandatory capabilities, behaviors, CLI semantics, defaults,
safety rules, and definition-of-done items. Downstream agents must compare their
output against it. Summaries and derived artifacts never replace the original
request. Link governing decisions and requirements through the workspace-local
`architecture-decisions` and `system-requirements` skills (read a specific record
by identity) instead of restating or paraphrasing them.

For DD creation/amendment and Change DAG create/amend, the handoff must also
include a readable `request_context.path` to an `artifacts/requests/CTX_*.md`
conversation snapshot created by Nyx with `capture_request_context`. The capture
is primary-source conversation evidence; `handoff_goal` and constraints are
operational direction and do not replace it. Missing or unreadable context is a
blocking dispatch failure. Nyx must capture the relevant conversation before
routing these authoring operations; downstream agents must read and preserve the
reference.

### Dispatch Lifecycle

1. **Before dispatch:** Open the exact per-agent reference linked in the department indexes below, and produce a complete handoff: every agent-specific field, every context file, and all already-known requirements, constraints, decisions, and evidence. A complete handoff means nothing the agent needs is missing — it does **not** mean duplicating the selected specialist's core investigation. When the specialist owns discovery of the evidence it needs (for example RnD-Manager owns the design-evidence graph), pass what you already know and let it select the rest; never force the caller to redo that discovery first.
2. **During dispatch:** Fill every field in that per-agent reference. List every file and artifact. Directly state every requirement, decision, constraint, hypothesis, and expected output. State what the agent must NOT do.
3. **After dispatch:** Verify the output against the expected contract. If malformed or incomplete, re-dispatch with clarification. Log significant findings. Route results to the next step.

### Common Dispatch Failures

| Failure | Symptom | Fix |
|---------|---------|-----|
| Placeholder text | Agent reports back confused or asks "what DAG?" | Fill every `[bracket]` with actual data before sending |
| Missing context files | Agent wastes turns asking for files or reads the wrong ones | List every file the agent needs. Check: would YOU know what to read from this prompt? |
| Implicit parent context | Agent assumes facts, decisions, or prior tool output that were only present in the caller's session | Restate it in the prompt or link a durable artifact; assume the agent knows nothing |
| No negative constraints | Agent over-steps — researcher writes code, author implements | Always add "Do NOT" — the bolded worker-spawn blocks in manager references exist for this reason |
| Too broad scope | Agent returns shallow, surface-level results | Narrow to one change, one module, one decision. Multi-part work → multiple dispatches. |
| Rerouting a selected owner | Caller silently substitutes a different agent than the one routing selected | Owner selection is `work-routing`'s policy. Dispatch the selected agent; if a hard capability/permission constraint conflicts, report the mismatch instead of substituting |

## Dispatch Mechanics by Department

The indexes below map each dispatched agent to its reference file and its dispatch
role or boundary. They are a reference index, not an owner-selection matrix — the
choice of which agent to dispatch comes from `work-routing`.

### Change DAG Dispatch

Change-DAG-Author owns construction end-to-end: bounded discovery, semantic
structure, exact work, the service-derived decomposition-frontier loop
(`dag_decomposition_frontier`), convergence/reconciliation, preview, validation,
and mutable correction without mutating source. It dispatches one bounded
`change-dag-worker` per returned semantic node via native `task`; the Worker
retrieves its own scope with `dag_decomposition_scope`. Change-DAG-Worker is a
bounded single-semantic-node construction capability that may selectively dispatch
its two read-only researchers (`change-dag-semantic-researcher`,
`change-dag-file-researcher`) for disposable exploration — **Nyx never dispatches Change-DAG-Worker directly**
for normal DAG construction. Only the
orchestrator/controller (Nyx) selects
Change-DAG-Reviewer, and only for observable coordination or authority triggers;
reviewer evidence is never persisted DAG state and does not authorize execution.
Nyx owns Change DAG lifecycle control through `dag_start`, `dag_status`,
`dag_stop`, and `dag_archive`; `dag_executor` performs deterministic execution and
does not dispatch or record QA.

| Agent | Dispatch reference | Dispatch role / boundary |
|-------|--------------------|--------------------------|
| `change-dag-author` | [`change-dag-author`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/change-dag-author.md) | Construction manager; owns the decomposition-frontier loop and internal worker dispatch |
| `change-dag-worker` | [`change-dag-worker`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/change-dag-worker.md) | Bounded single-semantic-node construction; dispatches its two read-only researchers; dispatched only by Change-DAG-Author |
| `change-dag-reviewer` | [`change-dag-reviewer`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/change-dag-reviewer.md) | Dynamically selected read-only review; selected by Nyx only for observable triggers |
| `change-dag-semantic-researcher` | [`change-dag-semantic-researcher`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/change-dag-semantic-researcher.md) | Read-only semantic-graph context compression; dispatched only by Change-DAG-Worker |
| `change-dag-file-researcher` | [`change-dag-file-researcher`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/change-dag-file-researcher.md) | Read-only repository-discovery context compression; dispatched only by Change-DAG-Worker; projected source authoritative |

### R&D Dispatch

RnD-Manager is the sole orchestrator for a formal DD. It owns the evidence-based
route (`DAG_ONLY` / `DD_REQUIRED` / `RESEARCH_ONLY`) and the **selection of the
design-evidence graph**, and returns the structured result to Nyx; it never
dispatches the downstream `change-dag-author` — Nyx does, only after
`status: DONE` and `phase: READY_FOR_AUTHORING`. It composes the smallest
sufficient graph from Librarian, Researcher, Refiner, Architect,
ComplexityAdvisor, Estimator, DDAuthor, and PatternEnforcer capabilities. It may
fan out independent work and must preserve dependency order and static authority.
The caller passes any governing constraint it already holds; neither side is
required to independently read the same governance corpus. RnD-Refiner executes
only one Manager-selected bounded external or repository pair per invocation.
DDAuthor never orchestrates other agents. Direct leaf dispatch is valid only for
focused analysis outside a formal DD workflow.

The adversarial critique agents ([`rnd-counter-ideator`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/rnd-counter-ideator.md) and [`rnd-counter-improver`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/rnd-counter-improver.md)) are spawned by RnD-Refiner only in a selected external or repository pair. Counter-Ideator tests external/architectural assumptions and real-world evidence; Counter-Improver tests actual repository paths, ownership, lifecycle, runtime boundaries, and unnecessary mechanisms. Neither is required to discover a defect. Both may validate a proposal when credible examination finds no material applicable concern. Direct dispatch is rare.

| Agent | Dispatch reference | Dispatch role / boundary |
|-------|--------------------|--------------------------|
| `rnd-manager` | [`rnd-manager`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/rnd-manager.md) | Sole formal-DD orchestrator; owns the route and the design-evidence graph |
| `rnd-refiner` | [`rnd-refiner`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/rnd-refiner.md) | Executes one Manager-selected adversarial pair per invocation |
| `rnd-dd-author` | [`rnd-dd-author`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/rnd-dd-author.md) | Records the accepted handoff in the DD; never orchestrates other agents |
| `rnd-architect` | [`rnd-architect`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/rnd-architect.md) | Implementation options + tradeoffs |
| `rnd-ideator` | [`rnd-ideator`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/rnd-ideator.md) | Creative solution generation |
| `rnd-estimator` | [`rnd-estimator`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/rnd-estimator.md) | Effort sizing (TRIVIAL→EPIC) |
| `rnd-complexity-advisor` | [`rnd-complexity-advisor`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/rnd-complexity-advisor.md) | Complexity / over-engineering audit |
| `rnd-improver` | [`rnd-improver`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/rnd-improver.md) | Code improvement suggestions; repository-native realization |
| `rnd-counter-ideator` | [`rnd-counter-ideator`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/rnd-counter-ideator.md) | Adversarial approach critique; spawned by RnD-Refiner only |
| `rnd-counter-improver` | [`rnd-counter-improver`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/rnd-counter-improver.md) | Adversarial repository-fit critique; spawned by RnD-Refiner only |

### QA Dispatch

QA is independent of Change DAG execution and archival: it is not stored in
`EXECUTION_STATE`, is not a DAG phase, and does not gate `dag_archive`.
`qa-push-manager` is the final publication gate for a candidate commit: it
validates an isolated disposable snapshot of the candidate at the candidate SHA
and, only after deterministic validation is green, spawns the read-only reviewers
selected per `/home/opencode/.config/opencode/instructions/qa-applicability.md` —
correctness always, plus boundary, journey, and every matched domain-risk lens,
dispatched in the canonical lens order and 0 / 1–3 / >3 batching rule owned there
— with each DomainRisk invocation confined to its `assigned_lens`. The adversarial
reviewers are read-only, work from the same immutable candidate context, never
consume each other's findings, and must not be dispatched before deterministic
validation is green. Reviewer infrastructure failure fails closed (REVIEW
INFRASTRUCTURE FAILURE). QA-PushManager pushes only the exact validated commit
object and only when explicitly authorized; otherwise it reports the validated
candidate without pushing.

QA-Reviewer composes the normal post-change QA pass. It spawns QA-TestAnalyzer and
QA-DocsAnalyzer when their canonical applicability triggers fire; each first
inspects current state and produces its own candidate findings, then spawns
QA-TestGenerator or QA-DocsGenerator for every surviving generator-owned candidate
(`MINOR_DISPATCH` or `MAJOR_DISPATCH`), exactly once. A `PASS` run (no candidate at
all) and a `MINOR_PASS` run (every candidate closed by validated current
reconciliation, never a discretionary too-minor bypass) dispatch no generator, and
an implementation/systemic escalation runs no generator. Tier-to-generator routing
is owned by the "Analyzer and generator contract" section of
`/home/opencode/.config/opencode/instructions/qa-applicability.md`.

QA-RepoReviewManager is the separate whole-tree GitHub review entry point, distinct
from the standalone code-review gate (`qa-reviewer`) and the push/publication
`qa-push-manager`. It accepts exactly one explicit full HTTPS GitHub tree URL
(`https://github.com/<owner>/<repository>/tree/<exact-ref>`), resolves the named
ref to its run-start head, materializes the complete current-head tree as an
immutable detached snapshot, and reviews that complete tree — never a diff and
never a candidate commit; the resolved SHA is provenance only. It never pushes,
never operates a push gate, and shares no mutable state with the push suite. Its
read-only reviewers (`qa-repo-reviewer-correctness`, `qa-repo-reviewer-boundary`,
`qa-repo-reviewer-journey`, plus `qa-repo-reviewer-domainrisk` once per matched
lens, dispatched in the canonical order and concurrency/batching rule owned by the
canonical applicability reference) are dispatched in canonical batched parallel
groups with one immutable review context and never consume one another's output;
collection fails closed as `REVIEW_INFRASTRUCTURE_FAILURE`. Before any manager
GitHub operation, load and apply the applicable guidance selected through
`gg-router` (`gg-repos`, `gg-env`, `gg-core`, `ggt-conventions`); never improvise
GitHub or Git behavior from memory. Direct dispatch of the whole-tree reviewers
outside QA-RepoReviewManager is not valid.

| Agent | Dispatch reference | Dispatch role / boundary |
|-------|--------------------|--------------------------|
| `qa-push-manager` | [`qa-push-manager`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/qa-push-manager.md) | Final publication gate; spawns read-only reviewers after deterministic validation |
| `qa-reviewer` | [`qa-reviewer`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/qa-reviewer.md) | Composes the normal post-change QA pass; full quality gate in one round |
| `qa-reviewer-correctness` | [`qa-reviewer-correctness`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/qa-reviewer-correctness.md) | Independent correctness and contract review |
| `qa-reviewer-boundary` | [`qa-reviewer-boundary`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/qa-reviewer-boundary.md) | Independent boundary and failure review |
| `qa-reviewer-journey` | [`qa-reviewer-journey`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/qa-reviewer-journey.md) | Independent end-to-end journey review |
| `qa-reviewer-domainrisk` | [`qa-reviewer-domainrisk`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/qa-reviewer-domainrisk.md) | Assigned technical risk lens; one invocation per lens |
| `qa-repo-review-manager` | [`qa-repo-review-manager`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/qa-repo-review-manager.md) | One-shot whole-tree GitHub review manager; never a push gate |
| `qa-repo-reviewer-correctness` | [`qa-repo-reviewer-correctness`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/qa-repo-reviewer-correctness.md) | Whole-tree correctness reviewer (permanent lens) |
| `qa-repo-reviewer-boundary` | [`qa-repo-reviewer-boundary`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/qa-repo-reviewer-boundary.md) | Whole-tree boundary/failure reviewer |
| `qa-repo-reviewer-journey` | [`qa-repo-reviewer-journey`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/qa-repo-reviewer-journey.md) | Whole-tree end-to-end journey reviewer |
| `qa-repo-reviewer-domainrisk` | [`qa-repo-reviewer-domainrisk`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/qa-repo-reviewer-domainrisk.md) | Whole-tree single assigned-lens specialist reviewer |
| `qa-repo-review-authorized-pilot` | [`qa-repo-review-authorized-pilot`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/qa-repo-review-authorized-pilot.md) | Optional disposable-repository pilot checklist; no live success is implied |
| `qa-test-analyzer` | [`qa-test-analyzer`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/qa-test-analyzer.md) | Test coverage and quality analysis |
| `qa-test-generator` | [`qa-test-generator`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/qa-test-generator.md) | Generates tests from coverage gaps |
| `qa-docs-analyzer` | [`qa-docs-analyzer`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/qa-docs-analyzer.md) | Documentation coverage analysis |
| `qa-docs-generator` | [`qa-docs-generator`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/qa-docs-generator.md) | Generates documentation from gaps |
| `qa-reassertion` | [`qa-reassertion`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/qa-reassertion.md) | Reasserts the QA gate when skipped |

### Support Dispatch

All support agents are dispatched directly — they have no internal orchestrator.
Independent Librarian and Researcher work may run concurrently.

| Agent | Dispatch reference | Dispatch role / boundary |
|-------|--------------------|--------------------------|
| `support-debugger` | [`support-debugger`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/support-debugger.md) | Root cause analysis for failures |
| `support-librarian` | [`support-librarian`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/support-librarian.md) | Process-artifact context (logs, dead ends, prior design docs) |
| `support-patternenforcer` | [`support-patternenforcer`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/support-patternenforcer.md) | Pattern coverage and consistency checks |
| `support-researcher` | [`support-researcher`](file:///home/opencode/.config/opencode/skills/dispatching-agents/references/support-researcher.md) | Deep codebase and external research |

## Cross-Cutting Concerns

### QA and Publication Independence

QA is independent of Change DAG execution and archival. The Change DAG lifecycle **must not** dispatch or record QA, and `dag_archive` does not depend on QA. A candidate is published only through the separate publication gate (`qa-push-manager`), which enforces QA before publication. If a publication candidate reaches the gate without QA, use the `qa-reassertion` reference.

### Spec-First Testing

Spec-first / RED-first testing is surface-dependent, selected from observable repository/task facts per `/home/opencode/.config/opencode/instructions/validation-mandate.md`. Apply it only when the changed surface has a meaningful executable oracle — a regression test can reproduce the defect, the repository already follows a test-first style, or a spec-first test resolves genuine spec ambiguity. Do not force RED for non-test-first surfaces (for example documentation-only or configuration-only changes with no executable oracle). Where it applies, tests written against design documents are expected to fail during implementation — do NOT dispatch Support-Debugger for those expected spec-first failures. QA review must classify failures: expected (not yet implemented) vs. actual regressions.

### Pattern Impact Analysis

After an accepted change, Support-PatternEnforcer may run read-only `impact_closure` (default) to report evidence-backed impact. It may run `migration_scan` only when an accepted DD explicitly establishes bounded migration scope. Findings use role-specific kinds and the shared `ADVISORY | NEEDS_OWNER | BLOCKING` envelope, route to the owning Change-DAG-Author or to Nyx's Change DAG lifecycle control, and never amend a Change DAG automatically.

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

Spawning a manager (RnD-Manager)?
└─ task (managers spawn workers and retain the session tree)
```

## Lifecycle Validation Before Dispatch

Every design, decomposition, or execution dispatch must validate DD status and requirement conformance before handing work downstream. Accept a DD only with a recognized accepted status (`Complete (accepted)`, `Approved`, or `Completed`), normalizing repository wording `Complete (accepted)` as accepted; an accepted DD intentionally held in `pending/` must name the prerequisite disposition, responsible owner, and transition condition. Reject `Draft`, `Rejected`, stale/invalid pending DDs, and any execution or archival of an unaccepted DD.

For Change DAG work, the owning layer remains responsible for requirement conformance and DAG artifact lifecycle. Change-DAG-Author owns construction end-to-end, including the service-derived decomposition-frontier loop, and dispatches one fresh bounded Change-DAG-Worker per returned frontier node; only the orchestrator/controller (Nyx) selects Change-DAG-Reviewer, and only for observable coordination or authority triggers. Support-PatternEnforcer does not validate requirement conformance, emit `REQUIREMENT_DRIFT`, prescribe tests, resolve unresolved nodes, or validate supersession. Its impact findings and reviewer verdicts are evidence for owner/controller disposition only; `BLOCKING`, confidence, closure, PASS, and routing ownership do not authorize implementation.

## Related Skills

- `work-routing` — canonical owner-selection policy (who owns the next step). Load it before choosing an owner; this skill begins after that choice.
- `change-dag-lifecycle` — Nyx's Change DAG lifecycle operation contract for starting, monitoring, stopping, recovering, retrying, and archiving Change DAGs.
- `change-dag-semantic-researcher` — Read-only semantic-graph context compression for Change-DAG-Worker dispatches.
- `change-dag-file-researcher` — Read-only repository-discovery context compression for Change-DAG-Worker dispatches; projected source authoritative.
- `capture-subsystem` — codebase research skills.
