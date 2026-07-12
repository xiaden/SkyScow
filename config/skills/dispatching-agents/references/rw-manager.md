# RW-Manager

Dispatch RW-Manager to decompose a goal into independent sub-tasks and fan them out to parallel workers.

## When to Dispatch

**Dispatch when:**
- RW-Director delegates decomposition and worker spawning per round
- You need one-shot planning + fan-out for a set of independent implementation tasks
- The goal can be broken into isolated, non-overlapping sub-tasks

**Do NOT dispatch when:**
- You need multi-phase execution with dependencies — use `exec-manager` instead
- You need design work — use `rnd-manager` instead
- The goal is a single edit — do it yourself or dispatch directly
- Sub-tasks have ordering dependencies — RW workers are parallel and isolated

## Dispatch Template

```
Decompose and execute: [SUB-GOAL].

**Your job is to spawn your workers:**
- Study the codebase to understand the scope
- Decompose into dependency DAG of isolated sub-tasks
- Fan out to parallel RW-Workers (one per sub-task)
- Return when all workers complete
Do NOT implement code yourself. Do NOT spawn RW-Reviewer.

Goal: "[specific sub-goal for this round]"
Context files to read:
- [relevant code files for this round's scope]
```

## Required Fields

| Field | Description | Example |
|-------|-------------|---------|
| `[SUB-GOAL]` | Specific sub-goal for this round | "Add dark mode CSS variables to all component stylesheets" |
| `Goal` | Concrete goal statement | "Replace all hardcoded color values in src/components/**/*.css with CSS variable references from the theme tokens." |

## Expected Output

- Decomposed sub-tasks (dependency DAG)
- One RW-Worker spawned per isolated sub-task
- Aggregated results from all workers
- Files changed per sub-task

## Key Constraints

- **Fresh context.** Each spawn starts fresh — no prior state. Include all needed context in the dispatch.
- **No reviewer spawning.** RW-Reviewer is RW-Director's responsibility. RW-Manager decomposes and fans out only.
- **Isolated sub-tasks.** Workers must not overlap in scope. Physical isolation (different files) or contractual isolation (different functions in same file) enforced.
- **One-shot.** RW-Manager plans once and fans out. It does not iterate — RW-Director handles the loop.
