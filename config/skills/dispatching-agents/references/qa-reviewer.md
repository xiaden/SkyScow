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
- [DESIGN_DOC_PATH]  — design document
- [CONTRACTS_PATH]  — contracts ledger (if multi-part feature)
- [AUTHORITATIVE_REQUEST] — verbatim original user request and requirement ledger

task:
  plan: "[plan identifier]"
  designDoc: "[design doc path]"
  contractsPath: "[contracts path or N/A]"

Full review in one pass. Run every applicable check per `/home/opencode/.config/opencode/instructions/qa-applicability.md`. Report all issues in one round.

QA-TestAnalyzer and QA-DocsAnalyzer each run when their canonical applicability trigger fires. A `PASS` result (no candidate) requires no generator, and a `MINOR_PASS` result is acceptable only when every produced candidate was closed by validated current reconciliation after fresh analysis — never as a discretionary no-generator bypass for a surviving candidate. A `MINOR_DISPATCH` or `MAJOR_DISPATCH` result requires the analyzer to spawn its generator and have that output independently re-verified; an implementation or systemic escalation does not automatically run the generator. Reject any unresolved generator-owned candidate, stale or mismatched reconciliation, missing terminal record, malformed subject identity, pre-mutation evidence, missing `UNNECESSARY` reason/evidence, a `REPAIRED` without actual verification, or a fixer claim beyond the repairs actually performed. Tier-to-generator routing is owned by the "Analyzer and generator contract" section of `/home/opencode/.config/opencode/instructions/qa-applicability.md`.
```

## Required Fields

| Field | Description | Example |
|-------|-------------|---------|
| `[PLAN_PATH]` | Path to the plan file | `artifacts/plans/pending/TASK-auth-A-login.md` |
| `plan` | Plan identifier | `TASK-auth-A-login` |
| `designDoc` | Path to design document | `artifacts/designs/pending/auth-design.md` |
| `contractsPath` | Path to contracts ledger or "N/A" | `artifacts/designs/parts/auth/CONTRACTS.md` |

## Expected Output

QA-Reviewer returns a tiered verdict:

| Verdict | Meaning | Action |
|---------|---------|--------|
| `PASS` | All checks pass, ready to ship | Accept DONE from Exec-Manager |
| `MINOR` | Small-scope issues (typos, missing null checks, style) | Spawn Exec-Fixer with issue list, then re-run QA |
| `MAJOR` | Architectural issues, missing functionality, systemic bugs | Escalate — cannot be fixed by Exec-Fixer alone |
| `FAIL` | Critical issues — security, data loss, broken contracts | Escalate immediately |

### Required Checks

- [ ] `checks.lint` — lint compliance
- [ ] `checks.layerCompliance` — layer boundary adherence
- [ ] `checks.contracts` — contract compliance
- [ ] `checks.codeQuality` — code quality and patterns
- [ ] `checks.completeness` — all plan steps delivered
- [ ] `checks.testCoverage` — test quality and coverage via QA-TestAnalyzer (which spawns QA-TestGenerator for dispatch tiers) when the canonical tests triggers hold per `/home/opencode/.config/opencode/instructions/qa-applicability.md`; otherwise an evidence-based `NOT_APPLICABLE` is recorded
- [ ] `checks.documentation` — doc coverage and accuracy via QA-DocsAnalyzer (which spawns QA-DocsGenerator for dispatch tiers) when the canonical documentation triggers hold per that reference; otherwise an evidence-based `NOT_APPLICABLE` is recorded
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
  issues: [list of issues with file, line, severity, description]
  testAnalyzerReport: { ... }
  docsAnalyzerReport: { ... }
```

## QA Gate Enforcement

The QA gate is **mandatory**. Exec-Manager must not report DONE without `qaReview.status: PASS`. The `qa-reassertion` reference covers pushback when this gate is skipped.

## Spec-First Test Handling

When spec-first tests exist:
- Distinguish spec-first failures (expected, not yet implemented) from actual regressions
- Spec-first failures should be noted in the report but not block PASS (unless they indicate missing functionality)
- Actual regressions (tests that passed before but fail now) must be classified as MINOR or MAJOR
