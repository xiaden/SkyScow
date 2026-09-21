# Example Plan

This example demonstrates worker-context phases, manager-review plans, explicit dependencies, and valid downstream-owned intermediate state.

```markdown
# Task: Introduce the replacement persistence API

## Problem Statement
Replace the legacy persistence entry point with a new contract and migrate its callers. The plan set owns eventual integration; this plan owns only the replacement API package.

## Dependencies
- None for the replacement API contract.
- Plan B consumes the replacement contract and owns service-consumer migration.
- Plan C consumes the migrated callers and owns legacy removal/final wiring.
- Plan B is independent of any unrelated Plan D; labels do not imply an edge.

## Phases

### Phase 1: Replacement API contract
- [ ] Define the replacement persistence interface and implementation contract.
- [ ] Add the implementation package and local checks for its own behavior.
  **Warning:** Existing callers still use the legacy entry point; that migration is explicitly owned by Plan B.

### Phase 2: Persistence implementation package
- [ ] Implement the replacement persistence operations and annotate produced contracts for downstream consumers.
- [ ] Verify the changed persistence surface with repository-defined checks that are possible before caller migration.

## Completion Criteria
- Replacement API obligations are implemented and annotated.
- Produced contracts are recorded for Plan B.
- Known caller migration is explicitly represented by a present downstream plan.
- No commit is required at the phase or plan boundary.
```

## Why this is valid

- The phases are worker context packages, not release milestones.
- The plan is a manager review package, not a commit or deployable checkpoint.
- The repository may temporarily fail because old callers remain; that is valid only because Plan B owns the dependent migration and Plan C owns final wiring/removal.
- A missing owner would be a `PLANNING_GAP`, not an acceptable intermediate state.
- A commit may happen during either phase, between phases, after this plan, or elsewhere according to caller/Git policy; the plan does not decide.
