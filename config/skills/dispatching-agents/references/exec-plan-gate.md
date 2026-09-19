# Exec-PlanGate

Dispatch Exec-PlanGate from Exec-Planner as the mandatory read-only preflight for a coordinated group of more than five implementation plans.

## When to Dispatch

- Exec-Planner has created or updated a complete coordinated group containing six or more plans
- A previously gated group has a plan amended or reordered; Exec-Planner must rerun the gate before handoff
- The governing Design Document changes after the group was gated; Exec-Planner must rerun the gate before handoff

**Do NOT dispatch when:**

- The complete group contains five or fewer plans (not required; a smaller-group invocation is allowed but must record `NOT_REQUIRED` — see below)
- A single plan needs execution — use Exec-Manager
- Plans need to be created, amended, or reordered — use Exec-Planner
- Completed implementation needs review — use QA-Reviewer
- Exec-Manager needs to perform the gate — Exec-Planner owns the planning preflight

## Dispatch Template

```text
Validate the complete implementation plan group before execution.

You are a read-only blocking preflight. Validate every plan against the Design Document and validate all plans against one another. Do not edit plans, contracts, the Design Document, or source code. Do not dispatch workers.

Context files to read:
- [DESIGN_DOC_PATH] — governing Design Document
- [CONTRACTS_PATH] — contracts ledger
- [README_PATH] — feature dependency graph and execution rounds
- [PLAN_A_PATH] — complete plan group member
- [PLAN_B_PATH] — complete plan group member
- [ALL_OTHER_PLAN_PATHS] — every remaining group member

task:
  feature: "[FEATURE_SLUG]"
  designDoc: "[DESIGN_DOC_PATH]"
  contracts: "[CONTRACTS_PATH]"
  readme: "[README_PATH]"
  plans:
    - "[PLAN_A_PATH]"
    - "[PLAN_B_PATH]"
    - "[ALL_OTHER_PLAN_PATHS]"
  planCount: [PLAN_COUNT]
  trigger: "more-than-five-plans"
  rerunReason: "[initial-preflight|plan-amended|plan-reordered|design-doc-changed]"
```

## Request-context prerequisite

The gate input must include a readable `request_context.path` pointing to an
`artifacts/requests/CTX_*.md` conversation snapshot. Verify that the plan set
retains this source reference. Missing or unreadable context is a blocking input
failure; a summary or handoff goal cannot replace it.

## Required Checks

1. The request-context capture is present and readable, and the plan set preserves its reference.
2. All listed plans are present and schema-valid.
3. Every DD requirement maps to plan ownership, actionable steps, and verification.
4. Dependencies are explicit, acyclic, and executable in the README's order.
5. Cross-plan contracts, signatures, schemas, migrations, APIs, and assumptions agree.
6. Shared ownership and parallel write overlap are safe or explicitly serialized.
7. No contradictions, missing prerequisites, duplicate ownership, or unowned outputs exist.

## Routing

| Verdict | Next action |
|---------|-------------|
| `PASS` | Exec-Planner may hand the group to Exec-Manager; Exec-Manager verifies the current report |
| `AMEND_REQUIRED` | Exec-Planner amends/reorders; rerun Exec-PlanGate before handoff |
| `DD_CONTRADICTION` | Escalate to DD/R&D owner or user |
| `MISSING_ARTIFACT` | Halt until required input is restored |
| `NEEDS_DECISION` | Halt and ask for an explicit decision |
| `BLOCKED` | Halt and report the input/tooling failure |
| `NOT_REQUIRED` | Record and return when the group has five or fewer plans; invocation is optional for a smaller group but must log this verdict, never leave an absent or ambiguous result |

## Expected Output

Return the Exec-PlanGate agent's complete YAML output, including coverage, dependency graph, contract compatibility, ownership/overlap, findings, routes, and whether rerunning is required. `PASS` means all blocking checks passed; it does not mean the implementation is complete.


### Additional Blocking Checks
The gate is mandatory for six or more plans and logs a verdict on every invocation. A coordinated group of five or fewer plans is `NOT_REQUIRED`: the gate is not mandatory, but if invoked it must still log `NOT_REQUIRED` (or an equivalent explicitly-labeled result) so no invocation is silent and no `NOT_REQUIRED` is mistaken for a stale or missing `PASS`. A previously recorded `NOT_REQUIRED` is invalidated when the group grows to six or more plans and must be replaced by a fresh `PASS`. Add blocking checks only for authoritative requirement coverage, implementation ownership, dependency/contract closure, ordering, and architectural invariants. Request callgraph/import evidence only where it establishes one of those facts; unresolved edges block only when they prevent satisfying an authoritative requirement or invariant. Do not require mocked/real caller tests, documentation, or other QA artifacts as universal plan content. Exec-Manager only verifies the recorded result and never spawns this gate.
