# RW-Worker

Dispatch RW-Worker to implement a single, focused, isolated sub-task.

## When to Dispatch

**Dispatch when:**
- RW-Manager decomposes a goal and spawns workers for each isolated sub-task
- You need a scoped, self-verifying implementation of a single concern

**Do NOT dispatch when:**
- The sub-task touches files that overlap with another worker — isolation required
- You need planning — use `rw-manager` or `exec-planner` instead
- The task spans multiple concerns — decompose further or use a manager

## Dispatch Template

```
Implement: [SUB-TASK].

Context files to read:
- [files in this worker's isolated scope]
- [reference files for patterns/conventions]

task: "[specific sub-task description]"
scope: "[exact files this worker owns]"
isolation: "[physical | contractual] — what prevents overlap with other workers"

Study the codebase, implement within scoped boundaries, self-verify with observable evidence. Report completion. No placeholders. No scope creep.
```

## Required Fields

| Field | Description | Example |
|-------|-------------|---------|
| `[SUB-TASK]` | Short task label | "Add theme CSS variables to Button component" |
| `task` | Specific description | "Replace all hardcoded colors in Button.css with CSS variable references. Use theme tokens from src/styles/theme.css." |
| `scope` | Exact files this worker owns | `src/components/Button/Button.css`, `src/components/Button/Button.tsx` |
| `isolation` | How this worker is isolated from others | `physical` (different files) or `contractual` (different functions in shared file) |

## Expected Output

- Implemented sub-task with concrete changes
- Self-verification evidence (lint passing, tests passing if applicable)
- No placeholders, no TODOs, no scope creep
- Files changed list

## Key Constraints

- **Strict scope boundaries.** Do not touch files outside `scope`. If a change requires crossing boundaries, report it as blocked — do not expand scope.
- **Fresh context.** No prior state. All needed context must be in the dispatch prompt.
- **Self-verify.** Run lint, run relevant tests, confirm the implementation works before reporting completion.
- **No placeholders.** Every line of code is real implementation. No `// TODO`, no stub functions, no "implement later."
- **Report blocked.** If a sub-task cannot be completed within scope, report exactly what's missing and why.
