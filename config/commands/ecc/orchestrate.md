---
description: Orchestrate multiple agents for complex tasks
argument-hint: "<task description>"
---

# Orchestrate Command

Orchestrate multiple specialized agents for this complex task: $ARGUMENTS

## Your Task

1. **Analyze task complexity** and break into subtasks
2. **Identify optimal agents** for each subtask
3. **Create execution plan** with dependencies
4. **Coordinate execution** — parallel where possible
5. **Synthesize results** into unified output

## Available Agents

Load the `dispatching-agents` skill for canonical dispatch templates and the authoritative agent selection decision tree. The table below is the complete catalog — use it to route subtasks.

### R&D Department (Design & Analysis)

| Agent | Specialty | Use For |
|-------|-----------|---------|
| rnd-manager | R&D department head | Feature design dispatch, owns the "thinking" phase |
| rnd-dd-author | Design lead | Creates/refines design documents from requirements |
| rnd-refiner | Adversarial design orchestrator | 8-turn adversarial refinement across 4 persistent sessions |
| rnd-ideator | Creative solution generator | Explores design space, ranked ideas with feasibility |
| rnd-counter-ideator | Adversarial approach critic | Critiques proposed approaches, searches for failures/postmortems |
| rnd-improver | Enhancement suggester | Proposes implementation patterns with web-cited evidence |
| rnd-counter-improver | Adversarial pattern critic | Critiques implementation patterns, finds edge cases/risks |
| rnd-architect | Implementation options analyst | 2-4 concrete approaches with tradeoffs matrix |
| rnd-estimator | Effort estimator | TRIVIAL/SMALL/MEDIUM/LARGE/EPIC sizing |
| rnd-complexity-advisor | Semantic complexity analyst | Determines if code is simpler than it could be |

### Execution Department

| Agent | Specialty | Use For |
|-------|-----------|---------|
| exec-manager | Plan execution lifecycle owner | Runs implementation plans, spawns workers, handles fix cycles |
| exec-plan-gate | Large plan-group preflight | Validates groups of more than five plans during planning; spawned by Exec-Planner |
| exec-planner | Implementation plan author and gate owner | Creates/amends plan files and spawns Exec-PlanGate for groups of more than five |
| exec-worker | Scoped phase implementer | Implements a phase or range of steps from a plan |
| exec-fixer | Targeted build repair | Fixes MINOR severity review issues, runs lint, reports completion |

### QA Department

| Agent | Specialty | Use For |
|-------|-----------|---------|
| qa-reviewer | Quality gate | Full review in one pass — all checks, all issues in one round |
| qa-test-analyzer | Test coverage analysis | Identifies missing tests, stale tests, coverage gaps |
| qa-test-generator | Test author | Generates tests to fill coverage gaps identified by analyzer |
| qa-docs-analyzer | Documentation analysis | Identifies missing docstrings, stale docs, doc/code drift |
| qa-docs-generator | Documentation author | Generates/updates docs to fill gaps identified by analyzer |

### Support Department

| Agent | Specialty | Use For |
|-------|-----------|---------|
| support-researcher | Deep research | Codebase exploration, external docs, structured findings |
| support-debugger | Root cause analysis | Traces execution, forms hypotheses, returns diagnosis with fix |
| support-librarian | Artifact corpus navigator | Searches ADRs, logs, design docs; returns curated context summaries |
| support-pattern-enforcer | Consistency propagation | Finds all files that should adopt a pattern but haven't |

## Orchestration Patterns

### Sequential Execution
```
rnd-dd-author → exec-planner → exec-manager → qa-reviewer
```
Use when: Later tasks depend on earlier results

### Parallel Execution
```
            ┌→ qa-reviewer
exec-manager →├→ qa-test-analyzer
            └→ support-researcher
```
Use when: Tasks are independent

### Fan-Out/Fan-In
```
            ┌→ agent-1 ─┐
exec-planner →├→ agent-2 ─┼→ synthesizer
            └→ agent-3 ─┘
```
Use when: Multiple perspectives needed

## Execution Plan Format

### Phase 1: [Name]
- Agent: [agent-name]
- Task: [specific task]
- Depends on: [none or previous phase]

### Phase 2: [Name] (parallel)
- Agent A: [agent-name]
  - Task: [specific task]
- Agent B: [agent-name]
  - Task: [specific task]
- Depends on: Phase 1

### Phase 3: Synthesis
- Combine results from Phase 2
- Generate unified output

## Coordination Rules

1. **Plan before execute** — Create full execution plan first
2. **Minimize handoffs** — Reduce context switching
3. **Parallelize when possible** — Independent tasks in parallel
4. **Clear boundaries** — Each agent has specific scope
5. **Single source of truth** — One agent owns each artifact

---

## References

- **`dispatching-agents` skill** — Canonical dispatch templates, agent selection decision tree, native `task` fan-out guidance, and per-agent reference files. Load this before dispatching any agent.
- **`making-and-using-task-plans` skill** — Formal plan Markdown schema and writing guidance; see `references/syntax.md` and `references/writing-guide.md`.

**NOTE**: Complex tasks benefit from multi-agent orchestration. Simple tasks should use single agents directly. When in doubt, consult the `dispatching-agents` skill's decision tree.
