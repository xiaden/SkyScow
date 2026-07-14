# RW-Director

Dispatch RW-Director to run the rapid worker (RW) workflow — a fast, parallel execution loop for straightforward implementation tasks that don't need multi-phase plans.

## When to Dispatch

**Dispatch when:**
- You need parallel, isolated workers executing independent sub-tasks against a shared goal
- The implementation is straightforward — no multi-phase dependency chains
- You want a review-gated feedback loop (implement → review → continue or stop)
- The task can be decomposed into independent units of work

**Do NOT dispatch when:**
- The task requires multi-phase planning with dependencies — use `exec-manager` instead
- You need design or R&D — use `rnd-manager` instead
- You need complex state management across phases — use `exec-manager` instead
- The task is a single edit — do it yourself

## Dispatch Template

```
Execute RW workflow for [GOAL].

**Your job is to spawn your workers:**
- Spawn RW-Manager per round to decompose remaining work
- Spawn RW-Reviewer after each round to validate progress
- Route on reviewer's CONTINUE or STOP verdict
Do NOT implement code yourself.

Goal: "[clear, specific goal statement]"
Context files to read:
- [all relevant code files]
- [any relevant ADRs or design docs]
```

## Required Fields

| Field | Description | Example |
|-------|-------------|---------|
| `[GOAL]` | Clear, specific goal | "Add dark mode toggle to all components in src/components/" |
| `Goal` | Goal statement | "Implement dark mode: add ThemeContext, CSS variables for all color tokens, toggle component, and apply to 15 leaf components." |

## Expected Output

RW-Director runs iteratively:
1. Records pre-RW git SHA for health restoration boundary
2. Spawns RW-Manager to decompose remaining work
3. RW-Manager spawns parallel RW-Workers for each sub-task
4. Spawns RW-Fixer for per-round mechanical cleanup
5. Spawns RW-Reviewer to validate progress
6. If CONTINUE: loop back to step 2 with remaining work
7. If STOP or budget exhausted: spawn RW-Health-Restorer for post-loop health restoration

The health restorer dispatches RW-Health-Fixer agents per error category, verifies results, and loops up to 3 iterations until the repository is clean.

Returns final status with:
- **RW exit verdict:** STOP reason, budget exhaustion, or spawn failure — verbatim from the reviewer
- **Round count:** How many rounds completed
- **Health restoration outcome:** Error delta summary, files modified, escalated/unfixable items, whether the repository is green
- **Anomalous verdict words** with round numbers (if any)

## RW Workflow Constraints

- **Fresh context per spawn.** RW-Manager, RW-Workers, RW-Fixer, and RW-Reviewer start fresh each round — no state carried over.
- **Isolated workers.** RW-Workers operate on contractually or physically isolated scopes — no overlap accepted.
- **Review every round.** RW-Reviewer validates the diff for meaningful progress toward the GOAL.
- **Health restoration is mandatory.** After the loop exits, RW-Director MUST spawn RW-Health-Restorer before reporting. The health restorer builds a causal repair allowlist seeded from RW-changed files, adds untouched files with documented causal links, and dispatches goal-aware fixers sequentially. Contract: repair current failures plausibly associated with RW-touched code — precise introduced-versus-pre-existing attribution is not claimed.
- **RW changes are intentional.** Health restoration fixes collateral damage (lint, types, tests) without reverting RW changes. If a fix would reverse RW intent or contradict the goal, the health restorer escalates via `question`.
- **Async, steerable.** RW-Director is a dumb for-loop spawner — it makes zero decisions, just routes on review verdicts. You can steer mid-flight via delegate.
