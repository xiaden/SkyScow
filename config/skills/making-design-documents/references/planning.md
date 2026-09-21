# Planning & Decomposition Methodology

**Purpose:** Derive the implementation dependency graph, then package it into worker phases and manager-review plans.

## Planning process

1. Read the authoritative request, accepted DD, repository facts, and relevant contracts.
2. Enumerate concrete, bounded implementation obligations.
3. Identify true producer-consumer and prerequisite edges.
4. Build and validate the implementation DAG and ownership closure.
5. Pack dependency-compatible nodes into worker-context phases.
6. Pack phases into manager-review-context plans.
7. Preserve cross-plan edges in the existing feature README/dependency graph.
8. Cross-validate requirements, contracts, ownership, ordering, and parallel-write safety.

Do not start by inventing Plan A/B/C containers and deriving dependencies from their existence. Containers package work; they do not manufacture its dependency graph.

## Step breakdown

Each step names:

- a clear, actionable obligation;
- its owner and relevant files/symbols;
- real prerequisites and produced/consumed contracts;
- a bounded verification against its own intent;
- risks and downstream ownership when integration is intentionally deferred.

A step does not promise a repository-wide green state.

## Phase packing: worker context

A phase is a worker context unit. Pack the largest coherent dependency-compatible set one worker can safely understand and execute. Optimize for the canonical worker budget in `config/agent-context-budgets.yaml` and the `context_tokens`/`context_budget` tools, including plan context, source context, contracts, expected edits, and return annotations.

Use context locality, related repository surface, satisfied prerequisites, and bounded worker output as primary criteria. Do not split merely because work crosses files, modules, layers, backend/frontend boundaries, or a semantic milestone. Split when context overload, context switching, or a true dependency requires it.

A phase is not inherently independently testable, compilable, deployable, buildable, releaseable, architectural, or user-visible. Local checks useful for the assigned work remain appropriate. A phase may finish while downstream-owned integration is incomplete.

## Plan packing: manager review context

A plan is a manager review context unit. Pack the largest coherent set of phases one manager can validate against the request/DD, contracts, worker results, annotations, changed surfaces, QA findings, and downstream ownership. Split only when manager context would overload or review would become diffuse. Do not split for commits, releases, layer boundaries, fixed counts, or milestone aesthetics.

A plan is not inherently a commit, PR, release, deployable state, complete feature, or repository-green checkpoint.

## Context policy

`config/agent-context-budgets.yaml` is the sole shipped policy source. Planning prose must not duplicate numeric ceilings. Use the budget tools and include the actual context carried by the relevant role. Step count, phase count, dependency depth, and character-count shortcuts are not partition rules.

## Plan format

Use the existing task-plan format and parser. A plan contains a problem statement, explicit dependencies, phases, flat actionable steps, owned completion criteria, and references. Plan letters/names are stable identifiers only. The feature README carries the actual dependency graph; `A → B` is valid only when an explicit prerequisite exists.

## Completion and downstream state

Review a package for its own obligations, not whole-feature integration:

- `CURRENT_PLAN`: current-owned defect or incomplete obligation; blocks.
- `DOWNSTREAM_PLAN`: incomplete work is named by a present, schema-valid, non-superseded dependent plan; report and carry forward without blocking.
- `PLANNING_GAP`: required work has no valid owner; blocks and requires replanning.

Every expected incomplete state must have an explicit downstream owner. Do not use context partitioning as an excuse for arbitrary brokenness.

## Quality handoff

Expose changed surfaces, dependencies, contracts, and explicit user/architecture quality obligations to QA. Do not manufacture universal tests, builds, security reviews, code reviews, verification milestones, or commits in every phase or plan. QA independently selects applicable review/analyzer work from canonical applicability rules; repository-defined checks remain the source of truth.

## Example decomposition

A replacement persistence API may be Plan A, consumer migration Plan B, and legacy removal/final wiring Plan C. Plan A can be accepted while callers still use the old API because Plans B/C explicitly own that integration. This is valid intermediate state, not a release checkpoint. If no later owner exists, the same failure is a planning gap.

## Validation checklist

- Every obligation has one owner.
- Every dependency edge is a real prerequisite or producer-consumer relation.
- Independent work remains independent.
- Phases fit worker context and plans fit manager review context using canonical tools.
- Plan letters do not imply execution order.
- Expected incomplete integration has a valid downstream owner.
- Cross-plan contracts, ownership, cycles, and write overlap are validated after the complete plan set exists.
- No generic commit step is introduced by decomposition.
