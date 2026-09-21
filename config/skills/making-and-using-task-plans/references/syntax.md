# Task Plan Syntax Reference

Plans are parsed by planning tools. Invalid structure causes parse errors.

## Canonical semantics

- A **step** is one actionable, bounded implementation obligation owned by one implementation package. It is verifiable against its own intent; it does not promise repository-wide integration.
- A **phase** is a worker context unit: a dependency-compatible package of steps one Exec-Worker can understand and execute safely within its context. A phase is not a commit, release, deployable checkpoint, independently buildable feature, or globally green milestone.
- A **plan** is a manager review context unit: a package of phases one Exec-Manager can validate against the request/DD, contracts, annotations, changed surfaces, QA findings, and downstream ownership. A plan is not a commit, release, deployable state, or fully integrated feature.
- The **plan set** owns eventual whole-change integration. Its README/dependency graph carries true producer-consumer and prerequisite edges.
- Git commits are orthogonal to steps, phases, plans, and plan sets. No lifecycle state implies a commit.

A plan or phase may finish while the repository is temporarily incomplete only when the missing work has a present, schema-valid, non-superseded downstream owner in the plan-set graph. Unowned breakage is a current defect or `PLANNING_GAP`.

## Template

```markdown
# Task: <Brief Title>

## Problem Statement
<What and why. Assume reader has zero context.>

## Dependencies
- `None`, or explicit producer/consumer prerequisites from the feature README.

## Phases

### Phase 1: <Worker-context package>
- [ ] Concrete, bounded, verifiable implementation obligation
- [ ] Another obligation owned by this phase

### Phase 2: <Worker-context package>
- [ ] Step whose prerequisites are satisfied by the explicit graph

## Completion Criteria
- Owned obligations are complete and annotated.
- Local checks useful for the changed surface have been run where possible.
- Any incomplete integration is named and owned by a later plan/phase.

## References
- Related issue, DD, ADR, or prior plan
```

## Format rules

| Element | Pattern | Note |
|---|---|---|
| Title | `# Task: <title>` | Required |
| Section | `## <name>` | Any `## Header` becomes a parsed key |
| Phase | `### Phase N: <title>` | N is a sequential display integer |
| Step | `- [ ] <text>` or `- [x] <text>` | Flat; no indented checkboxes |
| Annotation | `**Notes:**`, `**Warning:**`, `**Blocked:**`, `**Deviation:**` | Phase- or step-level |

Step IDs auto-generate as `P{phase}-S{step}`. Do not invent IDs.

## Writing good steps

Steps are:

- **Actionable** — state the concrete obligation and relevant path/symbol.
- **Bounded** — one owned outcome, not an entire feature or repository.
- **Verifiable** — completion can be checked against the step's intent.
- **Dependency-aware** — name a real prerequisite when one exists.

Do not require a step to leave the repository globally green when later owned work is intentionally incomplete. Do require explicit downstream ownership for any expected incomplete integration.

## DAG first, then packing

Decomposition derives work before assigning containers:

1. Enumerate implementation obligations from the request, accepted DD, and repository facts.
2. Identify real producer-consumer and prerequisite edges.
3. Build the implementation DAG and validate ownership closure.
4. Pack dependency-compatible nodes into phases using worker context, context locality, and return-envelope constraints.
5. Pack phases into plans using manager review context and cross-plan ownership/contract visibility.
6. Preserve the graph in the existing feature README/dependency metadata.

Plan letters and names are stable identifiers, not sequencing semantics. They may be assigned in display or topological order, but `A → B` exists only when explicit dependency metadata says so. Independent plans remain independent and may execute concurrently when safe.

## Context-based splitting

Use the canonical policy in `config/agent-context-budgets.yaml` and the `context_tokens` / `context_budget` tools. Do not copy numeric limits into planning prose. Include the context the role actually carries:

- Worker phase sizing: plan context, source/repository context, contracts, expected edits, and annotations/return output.
- Manager plan sizing: request/DD intent, plan and phase content, contracts, worker results, changed surfaces, QA report, and repair context.

Split when the worker or manager context would be unsafe or diffuse, not because a fixed step count, phase count, layer boundary, or milestone has been reached. A split must preserve real dependency edges and ownership; it must not manufacture dependencies.

## Parser rejection rules

### Nested steps

```markdown
- [ ] Create files
  - [ ] Create auth.py  <!-- rejected: indented checkbox -->
```

Flatten the steps or use annotations.

### Non-sequential display phases

```markdown
### Phase 1: First package
### Phase 3: Skipped display number  <!-- rejected -->
```

The display numbers remain sequential even though execution constraints come from the dependency graph.

### Invalid phase format

```markdown
### Phase One: Discovery  <!-- rejected -->
### Phase 1 - Discovery  <!-- rejected -->
```

## Validation

Always run `plan_read(plan_name)` after creating or editing a plan. Verify flat steps, sequential display numbers, a complete problem statement, measurable owned criteria, explicit real dependencies, and downstream ownership for expected incomplete integration.

## Cross-session continuity

1. Create in `artifacts/plans/pending/`.
2. Resume with `plan_read` and annotations.
3. Mark owned steps complete with `plan_complete_step`.
4. Archive with `plan_archive` when the plan's owned review package is complete and accepted.

Archiving is artifact lifecycle bookkeeping. It does not assert a commit, release, globally green repository, complete feature, or completed sibling plans.

## Common mistakes

| Don't | Do instead |
|---|---|
| Make plan letters imply order | Record real dependencies in the existing README graph |
| Split backend/frontend by convention | Keep them together when one worker can safely hold the context |
| Split at a fixed step/phase count | Measure role context with canonical budget tools |
| Require each phase to compile/deploy/test independently | Verify the owned obligation and classify explicit downstream state |
| Add a commit step at plan/phase completion | Leave Git policy to the caller or Git workflow |
| Create orchestrator/graph artifacts | Use the existing plan format and dependency metadata |
