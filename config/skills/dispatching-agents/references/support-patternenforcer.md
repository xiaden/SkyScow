# Support-PatternEnforcer

Dispatch Support-PatternEnforcer for read-only repository impact analysis. Evidence earns consideration; it does not earn implementation. Repository discovery establishes possible impact; it does not establish migration scope.

## When to Dispatch

| Trigger | Mode and question |
|---|---|
| An accepted DD/plan may leave a changed behavior path inconsistent | `impact_closure` (default): will this specific accepted change leave a known behavior path partially changed or inconsistent? |
| A Manager-accepted DD/plan explicitly establishes bounded migration intent | `migration_scan`: where should that accepted migration propagate? |
| QA-Reviewer flags a concrete inconsistency | `impact_closure` against the accepted change and supplied scope |

Do not dispatch for requirement conformance, lifecycle/supersession, testing policy, unresolved-edge policy, or generalized ownership closure. Those remain with their actual owners.

## Dispatch Template

```
Find repository impact for the accepted change at PATH.

mode: impact_closure
pattern:
  name: "descriptive name"
  description: "what the accepted change does"
  uses_pattern:
    signatures: []
    imports: []
  legacy_indicators:
    signatures: []
    imports: []
    antipatterns: []
scope:
  include: []
  exclude: []
accepted_scope_reference: "required only for migration_scan"

Return role-specific findings using the shared envelope:
kind: coverage_required | ownership_required | consistency_risk | not_applicable
evidence: [file:line or execution-path evidence]
impact: "behavioral impact or none"
disposition: ADVISORY | NEEDS_OWNER | BLOCKING
owner: "owning manager/planner or null"
```

For `migration_scan`, cite the exact Manager-accepted DD/plan scope. A new helper, pattern, API, technique, naming similarity, or search hit does not authorize migration scanning. Findings are report-only and never amend a plan.

## Evidence threshold and routing

`coverage_required` requires behavioral evidence: a direct caller of a changed contract, membership in the same changed dispatch/interface family, an explicitly required equivalent implementation, accepted DD/requirement inclusion, or execution-path evidence. Similarity, imports, old-helper use, and implementation resemblance produce at most non-blocking `consistency_risk`.

`BLOCKING` is limited to a demonstrated uncovered changed contract/behavior path, proven divergence from explicitly uniform behavior, or a known legacy implementation left by an accepted migration. `consistency_risk` is non-blocking. Route `coverage_required` and `ownership_required` to the owning manager/planner; the owner decides current-plan, downstream-plan, or no-change disposition. An owner, `BLOCKING`, confidence, or closure never authorizes implementation.

## Expected Output

```yaml
status: DONE
mode: impact_closure | migration_scan
findings:
  - kind: coverage_required | ownership_required | consistency_risk | not_applicable
    evidence: []
    impact: "..."
    disposition: ADVISORY | NEEDS_OWNER | BLOCKING
    owner: "..."
summary: "..."
open_questions: []
```

## Explicit non-authority

Do not compare a DD/plan to the verbatim request or immutable ledger, emit `REQUIREMENT_DRIFT`, validate `request_context.path`, inspect lifecycle/supersession or stale artifacts, prescribe mock/real tests, resolve unresolved callgraph edges, validate generalized ownership closure, create migration phases, or amend plans. RnD-Manager owns independent CTX/ledger/final-DD conformance; Exec-Planner/owning manager owns plan assignment; artifact/design/planning owners retain lifecycle.

Findings route to an owner/planner for disposition. They do not become requirements, contracts, ADRs, migration scope, or implementation obligations automatically.
