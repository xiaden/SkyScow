# Execution Subagent Dispatch Protocol

How to construct subagent prompts that produce correct, focused implementations one phase at a time.

---

## Prompt Structure

Every execution subagent call includes these sections:

```
1. TASK          — Which plan, which phase, what to implement
2. PLAN          — Full plan content (for orientation across all phases)
3. CONTRACTS     — Relevant CONTRACTS.md entries (methods to call or create)
4. PRIOR WORK    — Annotations from completed phases (if resuming mid-plan)
5. CONSTRAINTS   — Architecture rules, what NOT to touch
6. COMPLETION    — How to signal done (plan_complete_step per step)
```

---

## Prompt Template

```
Execute implementation for:

## Task
Plan: {plan file path}
Phase: {phase number} — {phase title}
Implement all steps in this phase. Mark each step complete using plan_complete_step as you finish it.

## Full Plan
{Paste full plan file content — the subagent needs all phases for orientation,
but ONLY implements the target phase.}

## Contracts from Prior Plans
{Paste relevant CONTRACTS.md sections. Include:
- Methods this phase CALLS (from upstream plans)
- Methods this phase CREATES (so downstream is aware)
- DTOs referenced in this phase
- Relevant architectural decisions

If the ledger is small, paste the whole thing. If large, extract relevant sections.}

## Prior Phase Work
{If this is Phase 2+ of the same plan, paste annotations from prior phases.
These come from plan_complete_step annotations.
If Phase 1, write: "This is the first phase. No prior work."}

## Constraints
- Implement ONLY Phase {N} steps. Do not work on other phases.
- Follow project architecture: layers, DI patterns, layer-appropriate data structures.
- **Quality standards (ECC):** files 200–400 lines typical (800 max), functions <50 lines, nesting <4 levels.
- **Immutability:** never mutate — return new objects/arrays. No `obj.prop = x`, no `list.append()`.
- **No console.log/print()** — use the project's logging facility. Remove any debugging output before completing.
- Lint after completing each step that modifies files.
- Write tests for new code — target ≥80% coverage on changed code.
- If a step cannot be completed as written, annotate it with what blocked you and move on.
  Do NOT silently skip or half-implement steps.
- Use existing patterns from the codebase. Before creating a new module, check if a similar
  one exists using available code-reading tools.

## Completion
- Mark each step complete using plan_complete_step(plan_name="{plan_name}", step_id="{step_id}")
- Add annotations for anything noteworthy: deviations from plan, decisions made, issues found
- After completing all steps in the phase, lint affected paths
- Report: which steps completed, which (if any) were blocked, and any deviations from plan
```

---

## Context Injection Rules

### What to always include

 | Context | Source | Purpose |
 | --- | --- | --- |
 | Target plan | `artifacts/plans/pending/TASK-{feature}-{letter}-*.md` | Phase boundaries, step descriptions, what NOT to implement yet |
 | Contracts ledger | `artifacts/designs/parts/{feature}/CONTRACTS.md` | Method signatures to call or create — prevents guessing |
 | Feature parts README | `artifacts/designs/parts/{feature}/README.md` | Execution rounds, dependency order, scope boundaries |
 | This prompt template | `{execution_protocol_file}` | Reference for constructing the subagent prompt |
 | **Layer instructions — include ALL that apply to this phase:** | | |
 | Interfaces layer | `{interfaces_instructions_file}` | Route handlers, auth, data-validation-only rule |
 | Services layer | `{services_instructions_file}` | DI wiring, thinness, no business logic |
 | Workflows layer | `{workflows_instructions_file}` | Use-case orchestration, one public function per file |
 | Components layer | `{components_instructions_file}` | Domain logic, stateless functions, ML isolation |
 | Persistence layer | `{persistence_instructions_file}` | Query patterns, db.module.method() access pattern |
 | Helpers layer | `{helpers_instructions_file}` | Pure utilities, DTOs, no business logic imports |
 | Frontend | `{frontend_instructions_file}` | UI conventions, framework patterns |

Only include the layer docs for layers the phase actually touches. A frontend-only phase does not need persistence.instructions.md.

### What to include conditionally

 | Context | When |
 | --- | --- |
 | Prior phase annotations | Phase 2+ of same plan |
 | Specific codebase patterns | When the plan references "follow pattern in X" |
 | Design doc sections | When plan steps reference design decisions |

### What to never include

 | Context | Why |
 | --- | --- |
 | Other plans' full content | Bloats context, causes cross-plan confusion |
 | Entire CONTRACTS.md for early plans | If only 2 entries exist, paste them; don't paste the boilerplate |
 | General coding instructions | The subagent inherits project context already |

---

## Granularity: Phase, Not Plan

**One phase per dispatch.** Reasons:

1. **Context focus** — A phase has 3-6 steps in one domain. The subagent stays in one area of the codebase.
2. **Checkpoint safety** — If context runs out, you lose at most one phase, not the whole plan.
3. **Annotation feedback** — Between phases, you can read annotations and adjust the next dispatch.
4. **Review accuracy** — Smaller increments mean review catches issues closer to where they were introduced.

**Exception:** If a phase has only 1-2 trivial steps (e.g., "verify lint passes"), you may combine it with the adjacent phase. Use judgment.

---

## Handling Subagent Failures

 | Situation | Action |
 | --- | --- |
 | Subagent completes all steps | Proceed to next phase |
 | Subagent completes some steps, blocks on others | Read annotations. Fix blockers yourself or adjust plan, then re-dispatch for remaining steps |
 | Subagent reports a plan error (wrong method signature, missing dependency) | Update the plan. Do NOT ask the subagent to improvise around plan errors |
 | Subagent runs out of context mid-phase | Check which steps completed via plan_read. Re-dispatch for remaining steps in the phase |
 | Subagent produces code that doesn't lint | This should be caught by the subagent's own lint step. If it wasn't, note it for review |

---

## Step Tracking

The subagent uses `plan_complete_step` to mark each step as it finishes. The orchestrator (you) verifies after the subagent returns:

1. Run `plan_read` on the plan
2. Check that all steps in the target phase are complete
3. Read annotations for deviations or concerns
4. If steps are missing completion marks, investigate — don't assume they were done

**Annotations are first-class output.** They feed into the review phase and the next execution dispatch. Encourage subagents to annotate liberally.
