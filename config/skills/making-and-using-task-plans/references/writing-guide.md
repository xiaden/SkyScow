# Task Plan Writing Guide

**Purpose:** Produce task plans that preserve ownership, dependencies, and review context across sessions.

## Core model

A step is one bounded implementation obligation. A phase packages dependency-compatible steps for one worker context. A plan packages phases for one manager review context. The plan set owns whole-change integration. Git commits are independent of all four boundaries.

## Step annotations

Annotations preserve decisions, risks, downstream ownership, and blockers:

```markdown
- [x] Implement the replacement contract
  **Notes:** Contract is consumed by Plan C; caller migration remains downstream-owned.
  **Warning:** Repository integration is intentionally incomplete until Plan C.
```

Use `**Notes:**`, `**Warning:**`, `**Blocked:**`, and `**Deviation:**`. Every completed step needs an annotation explaining what was done and any non-obvious state.

## Build the dependency graph before containers

Before naming phases or plans:

1. Read the authoritative request/accepted DD and repository facts.
2. Enumerate concrete obligations.
3. Identify actual producer-consumer and prerequisite edges.
4. Validate every obligation has an owner.
5. Build the implementation DAG.
6. Pack nodes into worker-efficient phases.
7. Pack phases into manager-review-efficient plans.

Plan letters are identifiers. They do not create dependencies. Do not serialize work because it is called B, follows another package in a table, or looks like a later milestone.

## Phase packing

A phase is the largest coherent dependency-compatible implementation package one worker can safely hold and execute. Optimize for:

- canonical worker context budget;
- context locality and related repository surface;
- minimal worker context switching;
- satisfied true prerequisites;
- tractable source/contracts/constraints;
- bounded worker annotations and return envelope.

Crossing files, modules, layers, or backend/frontend boundaries is not itself a split criterion. Split when context or dependency facts require it. A phase need not be independently buildable, deployable, testable, releaseable, or user-visible.

## Plan packing

A plan is the largest coherent package one manager can validate confidently against:

- request and accepted DD intent;
- phases and owned steps;
- contracts and annotations;
- changed files and QA findings;
- downstream ownership and graph coherence.

Split for manager context overload or review diffusion, not for commits, milestones, layer changes, fixed counts, or the hope of a green intermediate repository.

## Completion criteria

Criteria describe owned acceptance, not whole-feature completion. Include:

- owned obligations complete and annotated;
- relevant local verification performed where possible;
- contracts and changed surfaces identified;
- every expected incomplete integration named with a valid downstream owner.

Do not manufacture full tests, full builds, security review, code review, or commits at every phase. QA independently selects review/analyzer work from observable changed surfaces and canonical applicability rules.

## Downstream incomplete state

Use this distinction explicitly:

- `DOWNSTREAM_PLAN`: incomplete behavior is actually dependent/relevant, and the later plan is present, schema-valid, non-superseded, and owns the missing work. It is non-blocking for the current package and must be carried forward.
- `CURRENT_PLAN`: the current package failed its own obligation. It blocks.
- `PLANNING_GAP`: required work has no valid owner. It blocks and requires planning correction.

Never hide arbitrary breakage behind a context boundary.

## Lifecycle and archival

A plan may be `complete`/archived when its owned review package is complete and accepted. Archival moves the artifact; it does not imply a commit, release, deployment, globally green repository, or sibling-plan completion. Whole feature/plan-set archival is a separate boundary after dependency closure and all required plan acceptance.

## Cross-session continuity

1. Read the plan with `plan_read`.
2. Read annotations and the feature README dependency graph.
3. Resume only owned incomplete steps whose prerequisites are satisfied.
4. Preserve deviations and downstream carry-forward explicitly.
5. Archive only after the plan's own acceptance state is established.

## Common mistakes

| Mistake | Correction |
|---|---|
| “A before B before C” because of letters | Put only real edges in dependency metadata |
| Every phase must compile or deploy | Verify owned work; classify named downstream integration |
| Fixed step/phase count | Use canonical context-budget machinery |
| Commit at phase/plan completion | Follow caller/Git policy separately |
| Plan completion means feature completion | Require plan-set dependency closure |
| No owner for known broken integration | Add a valid downstream owner or report `PLANNING_GAP` |
