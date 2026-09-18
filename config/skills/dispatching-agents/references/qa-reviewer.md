# QA-Reviewer

Dispatch QA-Reviewer as the quality gate after implementation completes.

## When to Dispatch

**Dispatch when:**
- Exec-Manager completes all implementation phases and needs a quality gate before reporting DONE
- You need a full, one-pass review of changed code
- After Exec-Fixer completes repairs on QA-flagged issues

**Do NOT dispatch when:**
- Implementation is still in progress — QA runs after ALL phases, not partial
- You need targeted fixes — use `exec-fixer` instead
- You need test coverage analysis only — use `qa-test-analyzer` instead
- You need documentation analysis only — use `qa-docs-analyzer` instead

## Dispatch Template

```
Review the implementation for plan [PLAN_PATH].

Context files to read:
- [PLAN_PATH]  — the plan
- [DESIGN_DOC_PATH]  — design document (for example, `artifacts/designs/pending/auth/DD.md`)
- [CONTRACTS_PATH]  — contracts ledger (if multi-part feature)
- [AUTHORITATIVE_REQUEST] — verbatim original user request and requirement ledger
- The validated ordered plan set and dependency/ownership context for the current plan

task:
  plan: "[plan identifier]"
  currentPlan: "[plan identifier]"
  orderedPlanSet: "[present, schema-valid, dependency-ordered, non-superseded plan set]"
  designDoc: "[design doc path]"
  contractsPath: "[contracts path or N/A]"

Full review in one pass. Run every applicable check per `/home/opencode/.config/opencode/instructions/qa-applicability.md`. Evaluate completeness against the current plan's bounded responsibilities, while using the validated ordered plan set to classify every incomplete finding. Use exactly `CURRENT_PLAN`, `DOWNSTREAM_PLAN`, or `PLANNING_GAP`: current-plan work and planning gaps block; downstream work is non-blocking only when explicitly owned by a present, schema-valid, non-superseded later plan in this same dependency-ordered set. Report downstream findings with `downstreamPlan` and carry them forward. Never infer ownership from likely-future work, annotations, or unrelated plans.

QA-TestAnalyzer and QA-DocsAnalyzer each run when their canonical applicability trigger fires. A `PASS` result (no candidate) requires no generator, and a `MINOR_PASS` result is acceptable only when every produced candidate was closed by validated current reconciliation after fresh analysis — never as a discretionary no-generator bypass for a surviving candidate. A `MINOR_DISPATCH` or `MAJOR_DISPATCH` result requires the analyzer to spawn its generator and have that output independently re-verified; an implementation or systemic escalation does not automatically run the generator. Reject any unresolved generator-owned candidate, stale or mismatched reconciliation, missing terminal record, malformed subject identity, pre-mutation evidence, missing `UNNECESSARY` reason/evidence, a `REPAIRED` without actual verification, or a fixer claim beyond the repairs actually performed. Tier-to-generator routing is owned by the "Analyzer and generator contract" section of `/home/opencode/.config/opencode/instructions/qa-applicability.md`.
```

## Required Fields

| Field | Description | Example |
|-------|-------------|---------|
| `[PLAN_PATH]` | Path to the plan file | `artifacts/plans/pending/TASK-auth-A-login.md` |
| `plan` | Plan identifier | `TASK-auth-A-login` |
| `designDoc` | Path to design document | `artifacts/designs/pending/auth/DD.md` |
| `contractsPath` | Path to contracts ledger or "N/A" | `artifacts/designs/pending/auth/CONTRACTS.md` |

## Expected Output

QA-Reviewer returns a tiered verdict:

| Verdict | Meaning | Action |
|---------|---------|--------|
| `PASS` | The current plan's responsibilities pass; any valid downstream-owned incompleteness is reported as carry-forward | Accept DONE from Exec-Manager; feature archival still waits for all plans |
| `MINOR` | Small-scope issues (typos, missing null checks, style) | Spawn Exec-Fixer with issue list, then re-run QA |
| `MAJOR` | Architectural issues, missing functionality, systemic bugs | Escalate — cannot be fixed by Exec-Fixer alone |
| `FAIL` | Critical issues — security, data loss, broken contracts | Escalate immediately |

- [ ] `checks.completeness` — all current-plan implementation steps and current-plan-owned responsibilities delivered; classify remaining implementation work by validated plan-set ownership
- [ ] `checks.testCoverage` — test quality and coverage via QA-TestAnalyzer when canonical test triggers hold; otherwise evidence-based `NOT_APPLICABLE`
- [ ] `checks.documentation` — documentation coverage and accuracy via QA-DocsAnalyzer when canonical documentation triggers hold; otherwise evidence-based `NOT_APPLICABLE`
- [ ] Every surviving generator-owned candidate has specialized Generator terminal evidence or a validated current reconciliation
- [ ] Terminal records contain required provenance and actual verification

QA must not report a plan incomplete solely because the plan omitted a test, documentation, or evidence step. Those outputs are derived from the implemented surface and are owned by the applicable QA analyzer/generator unless explicitly required by the user request or accepted architecture.
- [ ] Every surviving generator-owned candidate has specialized Generator terminal evidence or a validated current reconciliation; a `MINOR_PASS` records its reconciliation basis and is never used to accept a surviving candidate
- [ ] Terminal Generator and Exec-Fixer records carry task family, positive round, writer/agent, stable subject identity, decision, reason/evidence, changed files/symbols, actual verification, `repair` for Exec-Fixer records, and provenance; a valid specialized `UNNECESSARY` is accepted without override and `BLOCKED`/`ESCALATED` ownership is preserved

`checks.testCoverage` and `checks.documentation` are applicability-conditional; all other checks must run.

### Output Structure

```
qaReview:
  status: PASS | MINOR | MAJOR | FAIL
  checks:
    lint: PASS | FAIL
    layerCompliance: PASS | FAIL
    contracts: PASS | FAIL
    codeQuality: PASS | FAIL
    completeness: PASS | FAIL
  testCoverage: PASS | FAIL | NOT_APPLICABLE
  documentation: PASS | FAIL | NOT_APPLICABLE
  requirementConformance: PASS | FAIL
    issues: [list of issues with file, line, severity, description, ownership, downstreamPlan when applicable, blocksCurrentPlan; ownership is CURRENT_PLAN | DOWNSTREAM_PLAN | PLANNING_GAP]
  testAnalyzerReport: { ... }
  docsAnalyzerReport: { ... }
```

## QA Gate Enforcement

The QA gate is **mandatory**. Exec-Manager must not report DONE without `qaReview.status: PASS`. The `qa-reassertion` reference covers pushback when this gate is skipped.

## Incomplete Work Handling

Test or documentation status does not create an exception to ownership classification. A spec-first or otherwise incomplete finding is `CURRENT_PLAN` when owned here, `DOWNSTREAM_PLAN` only with a validated later owner in the supplied plan set, and `PLANNING_GAP` otherwise. The latter two classifications retain their defined carry-forward or blocking behavior; no annotation-only or likely-future ownership is accepted.
