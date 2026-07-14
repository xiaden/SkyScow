# RW-Health-Restorer

Dispatch RW-Health-Restorer after the RW loop completes to restore repository health. The health restorer is a manager that builds a causal repair allowlist, categorizes failures from the RW transformation, and dispatches goal-aware fixer agents sequentially to repair them — without reverting intentional RW changes.

## When to Dispatch

**Dispatch when:**
- The RW loop has completed (STOP verdict or budget exhausted)
- The repository has lint, type, or test errors plausibly associated with RW changes
- You need a systematic health restoration pass that respects RW intent
- The pre-RW git SHA and goal file are available

**Do NOT dispatch when:**
- The RW loop is still running — health restoration is post-loop only
- The repository has zero errors — health restoration is unnecessary
- You need to revert RW changes — health restoration fixes collateral damage, not the transformation itself
- The task is a single error — fix it directly instead

## Dispatch Template

```
Restore repository health after the completed RW transformation.

**Your job is to dispatch fixers, not fix directly:**
- Assess all lint, type, and test failures
- Build a causal repair allowlist (seed with RW-changed files; add untouched files with documented causal links)
- Categorize each failure by layer (implementation/test/configuration/assumption)
- Cross-reference implementation fixes against the goal — fixes that complete the goal are valid; fixes that contradict it must be escalated
- Dispatch rw-health-fixer sequentially for each category (one at a time)
- Verify results after each fixer; loop up to 3 iterations if errors remain
- Escalate ambiguous or goal-contradicting cases via question
Do NOT implement fixes yourself unless a fixer has failed twice on the same error.

PRE_RW_SHA: <sha before RW loop started>
POST_RW_SHA: <current HEAD after all RW rounds>
GOAL_PATH: <path to RW goal file, e.g., .rw/<run-id>/goal.md>

Context files to read:
- .rw/<run-id>/health/pre-rw-sha
- .rw/<run-id>/health/post-rw-sha
- .rw/<run-id>/goal.md
```

## Required Fields

| Field | Description | Example |
|-------|-------------|---------|
| `PRE_RW_SHA` | Git commit hash before the RW loop started | `abc123def456` |
| `POST_RW_SHA` | Git commit hash after all RW rounds completed | `789ghi012jkl` |
| `GOAL_PATH` | Path to the RW goal file | `.rw/1720000000/goal.md` |

## Expected Output

RW-Health-Restorer runs iteratively:

1. **Assess:** Full lint + typecheck + test sweep
2. **Build allowlist:** Seed with RW-changed files; add untouched files with documented causal links
3. **Categorize:** Each error classified by stale layer (implementation/test/configuration/assumption) and goal-consistency
4. **Dispatch:** Spawns `rw-health-fixer` sequentially per category with scoped error lists and goal context
5. **Verify:** Re-runs full sweep after each fixer, compares error counts
6. **Loop:** Up to 3 iterations of categorize → dispatch → verify
7. **Complete:** Reports error delta, repair allowlist, files modified, escalated/skipped items

Returns final status with:
- Error summary table (before/after per category)
- Files modified during health restoration
- Escalated items with user decisions
- Unfixable items with reasons

## Contract

The health restorer's contract is bounded by two git SHAs and the goal:

- **Scope:** Causal repair allowlist — seeded from RW-changed files, expanded with documented causal links for cross-layer fallout. Errors not plausibly associated with RW changes are documented but not repaired.
- **Attribution:** The contract repairs current failures plausibly associated with RW-touched code. It does not claim precise introduced-versus-pre-existing attribution.
- **Intent:** RW changes are presumed correct. The goal file is the authority — fixes that complete the goal are valid; fixes that contradict it are escalated.
- **Completion:** Zero errors in the repair allowlist, OR all remaining errors escalated with user approval, OR 3 iterations exhausted.

## Key Constraints

- **RW changes are intentional.** Do not revert, bypass, or weaken goal-directed changes to satisfy tests, typing, linting, or builds.
- **Goal-aware fixing.** Fixes that complete the goal's described behavior are valid. Fixes that contradict the goal must be escalated.
- **Causal allowlist, not diff-only.** RW-changed files are the seed. Add untouched files only with documented causal links.
- **Narrowest layer repair.** Fix the narrowest responsible layer: implementation → test → configuration → assumption.
- **Sequential dispatch.** Fixers run one at a time. Verify after each. No parallel fixers.
- **Escalate, don't revert.** Any change that materially reverses RW intent or contradicts the goal requires explicit user approval via `question`.
- **Three iterations max.** If errors remain after 3 loops, report and exit.
- **No git operations.** The director handles all commits.
