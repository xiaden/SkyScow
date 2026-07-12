# Support-PatternEnforcer

Dispatch Support-PatternEnforcer to check whether a pattern is consistently applied across the codebase.

## When to Dispatch

| Trigger | What to check |
|---------|---------------|
| Design document created | Validate DD coverage — does every affected module appear in the document? |
| Plan created | Validate plan coverage — are all required changes accounted for? |
| Plan executed (new pattern) | Verify pattern adoption — did the new pattern propagate to all relevant files? |
| QA-Reviewer flags inconsistency | Investigate gaps — which files were missed? |

## Dispatch Templates

Two templates depending on the trigger.

### Coverage Check

For DD/plan validation or QA-flagged inconsistencies:

```
Check coverage for [DD or plan at PATH].

Pattern to enforce: [describe what should be touched — e.g., "all persistence modules that own X entity"]
Scope: [list modules or directories to scan]

Return gaps where the pattern should apply but is not mentioned.
```

| Field | Description | Example |
|-------|-------------|---------|
| `[DD or plan at PATH]` | Path to the design document or plan file | `artifacts/designs/pending/acme-auth.md` |
| `[describe what should be touched]` | The pattern or concern to check | "all persistence modules that own X entity" |
| `[list modules or directories to scan]` | Scope of the check | `src/persistence/`, `src/services/` |

### Pattern Adoption Check

For post-execution verification that a new pattern propagated everywhere it should:

```
Find all files that should adopt the new pattern introduced by {plan name}.

pattern:
  name: "{descriptive name of the new pattern}"
  description: "{what it does and why it replaces the old approach}"
  uses_pattern:
    signatures:
      - "{new function/method signature}"
    imports:
      - "{new import path}"
  legacy_indicators:
    signatures:
      - "{old function/method signature}"
    imports:
      - "{old import path}"
scope:
  include:
    - "src/"
  exclude:
    - "src/migrations/"
    - "tests/"
```

## Expected Output

Support-PatternEnforcer returns confidence-tiered results:

| Tier | Meaning |
|------|---------|
| `high_confidence` | Files that definitely need the pattern |
| `medium_confidence` | Files that might need the pattern |
| `low_confidence` | Files that might not need the pattern |
| `gaps` | Specific gaps where the pattern is missing |

## Routing Gaps

| Context | Action on gaps |
|---------|---------------|
| DD or plan creation | Route back to the authoring agent (RnD-DDAuthor or Exec-Planner) for amendment before proceeding. |
| Plan execution (new pattern) | If `high_confidence` candidates exist, spawn **Exec-Planner** (AMEND) to add a migration phase. |
