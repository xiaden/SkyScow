---
description: Orchestrate multiple agents for complex tasks
argument-hint: "<task description>"
---

# Orchestrate Command

Orchestrate multiple specialized agents for this complex task: $ARGUMENTS

## Your Task

1. **Analyze task complexity** and break into subtasks
2. **Identify the smallest sufficient capability graph** for each subtask
3. **Record dependencies and static authority boundaries**
4. **Coordinate execution** — parallel only for independent work
5. **Synthesize results** into unified output

## Available Agents

Load the `dispatching-agents` skill for canonical dispatch templates and the authoritative agent selection decision tree. The table below is the complete catalog — use it to route subtasks.

### R&D Department (Design & Analysis)

| Agent | Specialty | Use For |
|-------|-----------|---------|
| rnd-manager | R&D department head | Feature design dispatch, owns the "thinking" phase |
| rnd-dd-author | Design lead | Creates/refines design documents from requirements |
| rnd-refiner | Adversarial design executor | Runs one Manager-selected bounded external or repository pair |
| rnd-ideator | Creative solution generator | Explores design space, ranked ideas with feasibility |
| rnd-counter-ideator | Adversarial approach critic | Critiques proposed approaches, searches for failures/postmortems |
| rnd-improver | Evidence-backed architecture adapter | Collapses a surviving approach into the smallest repository-native realization; reuses local behavior and adds only demonstrated mechanisms |
| rnd-counter-improver | Adversarial repository-fit validator | Challenges actual local fit, ownership, lifecycle, runtime paths, and unnecessary mechanisms; may conclude GOOD_ENOUGH |
| rnd-architect | Implementation options analyst | 2-4 concrete approaches with tradeoffs matrix |
| rnd-estimator | Effort estimator | TRIVIAL/SMALL/MEDIUM/LARGE/EPIC sizing |
| rnd-complexity-advisor | Semantic complexity analyst | Determines if code is simpler than it could be |

### Execution Department

| Agent | Specialty | Use For |
|-------|-----------|---------|
| change-dag-author | Change DAG author | Creates/amends one Change DAG — semantic decomposition, exact work, patch visibility; never writes source |
| change-dag-reviewer | Dynamically selected read-only reviewer | Bounded semantic/work/conflict/run-barrier/DD-consistency judgment when an observable trigger exists; external evidence only, stored nowhere in DAG state |
| change-dag-runner | Change DAG execution control | Starts/stops/monitors execution, reconciles queue/marker/lock, checkpoints a successful completion, and archives a completed DAG |

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

### Dependency-ordered execution
```
rnd-manager → selected R&D capabilities → rnd-dd-author (DD_REQUIRED only) → change-dag-author → [optional change-dag-reviewer when an observable trigger exists] → change-dag-runner → independent QA (qa-reviewer)
```
Use when: Later tasks depend on earlier results. The Manager selects the smallest
sufficient graph; independent Librarian/Researcher work may run concurrently.

### Parallel Execution
```
             ┌→ support-librarian ─┐
rnd-manager →├→ support-researcher ─┼→ dependent R&D node
             └→ selected evaluator ┘
```
Use when: Tasks are independent and their evidence domains do not overlap.

### Bounded fan-out/fan-in
```
            ┌→ agent-1 ─┐
nyx →├→ agent-2 ─┼→ synthesizer
            └→ agent-3 ─┘
```
Use when: Multiple perspectives needed

## Capability Graph Format

### Node 1: [Capability]
- Agent: [agent-name]
- Task: [specific bounded task]
- Depends on: [none or named nodes]
- Selected because: [short evidence-based rationale]

### Node 2: [Capability] (parallel when independent)
- Agent: [agent-name]
- Task: [specific bounded task]
- Depends on: [none or named nodes]
- Selected because: [short evidence-based rationale]

### Terminal synthesis
- Combine selected results only
- Record material skips, evaluator result, dispositions, re-entry/resume, and terminal reason

## Required routing cases

The Manager records the observed condition, selected and skipped capabilities, dependency/concurrency shape, terminal reason, and DD eligibility in the routing trace. These cases are acceptance examples, not a new registry or state-machine DSL:

- **A — Trivial local change:** a single well-understood module and no open external or architectural question. Select only route/sizing evidence needed for authoring; skip Librarian, Researcher, Refiner, Architect, ComplexityAdvisor, and DDAuthor with evidence-based reasons. Terminal: `DAG_ONLY`; no DD artifacts.
- **B — Open Nomarr backend choice:** backend alternatives are consequential and repository integration facts are unknown. Select independent Librarian/Researcher work, then external and repository Refiner pairs; select Architect only if multiple survivors still require tradeoffs. Preserve Manager/user decision authority before authoring. Terminal: `DD_REQUIRED` only after dispositions and an accepted direction.
- **C — Accepted architecture, unclear integration:** architecture is accepted but local runtime or ownership paths are unknown. Skip external Ideator/Counter-Ideator and Architect; select Researcher and, when repository adaptation is material, Improver/Counter-Improver. Terminal: selected evidence or Manager disposition; no redundant external exploration.
- **D — Greenfield alternatives:** no accepted direction exists and multiple credible designs may survive. Select Architect for explicit tradeoffs and require Manager or user resolution at the decision boundary; an advisory agent never chooses.
- **E — Evaluator is good enough:** a selected Counter returns credible `GOOD_ENOUGH` or `NO_MATERIAL_CONCERNS` with evidence, assumptions, failure modes, and applicability. Terminate that pair immediately; do not add a historical pass.
- **F — Mitigation requires authority:** an evaluator returns a material finding. Pause and return it to RnD-Manager; only a Manager `MITIGATE` disposition authorizes a bounded correction and optional revalidation. Other dispositions do not authorize implementation.
- **G — Generalized complexity:** the design introduces meaningful lifecycle/state machinery, new abstractions, dependency or compatibility management, registries, or broad scope. Select ComplexityAdvisor; keep its result advisory and preserve smallest-realization discipline.
- **H — DD not required:** the request is research-only or dag-only, or an existing accepted DD is sufficient. Do not select DDAuthor or create partial DD artifacts; route only bounded research/authoring work and record the terminal reason.

## Coordination Rules

1. **Compose locally** — Select the smallest sufficient capability graph from the
   request, evidence, accepted architecture, and risk; do not run a mandatory
   assembly line.
2. **Preserve gates** — Static permissions, requirement provenance, authority,
   security, DD acceptance, implementation authorization, and QA authority do not
   change with topology.
3. **Respect dependencies** — Keep dependent nodes ordered; parallelize only
   independent evidence gathering.
4. **Bound evaluators** — Stop on credible `GOOD_ENOUGH`/`NO_MATERIAL_CONCERNS`;
   return findings to the owning Manager before any mitigation or resume.
5. **Trace decisions** — Record selected/skipped rationale, outcome, evaluator
   result, re-entry, dispositions, and terminal reason in existing Manager logs.
6. **Single source of truth** — One agent owns each artifact and authority.

---

## Change DAG execution routing cases

The orchestrator/controller records the observed condition, selected and skipped capabilities,
dependencies/concurrency, outcome, re-entry, and terminal reason in its existing
routing trace; the Runner records execution facts in its existing execution trace.
These examples preserve static authority; they are not a registry or state-machine DSL:

- **A — Straightforward DAG:** author/validate `DAG.json` and route directly to execution; skip reviewer and support capabilities without observable triggers. Mechanical `dag_start` admission and normal independent QA still apply.
- **B — Independent branches:** multiple independent DAG nodes do not trigger review by count; execution is serialized by the single-DAG lock and runs in dependency order.
- **C — Coupled producer/consumer:** select the change-dag-reviewer for a real cross-node contract, shared semantic convergence, incompatible proposals, shared write/schema/migration/registry, nontrivial ordering, DD ambiguity, recovery amendment, or explicit user request. The review receives a bounded scope/question and `review_kind`; PASS is evidence only, not execution authorization. The controller may route to the Runner after PASS or directly when no review is selected.
- **D — Obvious node defect:** apply a bounded raw edit directly, or author a remediation DAG when the defect is substantial; do not invoke Debugger.
- **E — Unclear node failure:** select Support-Debugger; route `SIMPLE` to a bounded raw edit, `NEEDS_DAG` to Change-DAG-Author for a DAG amendment and re-execution, and `INCONCLUSIVE` to escalation.
- **F — QA `DAG_GAP`:** route by lifecycle. If the original DAG is still executing/recovering and not completed, amend it via Change-DAG-Author and re-run, then run normal QA again. If it is already completed, never reopen it: route a small/local gap to a bounded raw repair, or a substantial/cross-cutting gap to a NEW remediation Change DAG, then run normal QA again. A completed DAG is never amended; a `DAG_GAP` is never blindly forced into a raw edit.
- **G — Accepted migration:** select PatternEnforcer only for accepted impact closure or migration scope; findings remain advisory and scope changes return to Change-DAG-Author.
- **H — Historical artifacts:** select Support-Librarian only when ADRs, DDs, logs, or dead ends materially constrain DAG creation/routing; record a skip otherwise.
- **I — No history:** with no relevant artifact infrastructure, skip Support-Librarian and do not manufacture a briefing.
- **J — Architectural contradiction:** stop execution and return upstream to the accepted DD/request owner; no DAG agent invents a resolution.
- **K — A/C with independent B:** if A produces a contract consumed by C while B has no real edge, preserve `A → C`, keep B independent, and execution remains dependency-ordered.

## References

- **`dispatching-agents` skill** — Canonical dispatch templates, agent selection decision tree, native `task` fan-out guidance, and per-agent reference files. Load this before dispatching any agent.
- **`Change DAG schema/tools`** — `artifacts/change-dags/{pending|completed}/{slug}/DAG.json` is authoritative for new work; use `change-dag-author` and the `dag_*` tools rather than creating plans or graphs.
- **Legacy task-plan and implementation-graph artifacts** — Historical compatibility only; do not create new plan or legacy implementation-graph artifacts for Change DAG work.

**NOTE**: Complex tasks benefit from multi-agent orchestration. Simple tasks should use single agents directly. When in doubt, consult the `dispatching-agents` skill's decision tree.
