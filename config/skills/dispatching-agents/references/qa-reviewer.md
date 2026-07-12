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

task:
  plan: "[plan identifier]"
  designDoc: "[design doc path]"
  contractsPath: "[contracts path or N/A]"

Full review in one pass. All checks run. All issues reported in one round. Do NOT stop early.
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

### Required Checks (All Must Run)

- [ ] `checks.lint` — lint compliance
- [ ] `checks.layerCompliance` — layer boundary adherence
- [ ] `checks.contracts` — contract compliance
- [ ] `checks.codeQuality` — code quality and patterns
- [ ] `checks.completeness` — all plan steps delivered
- [ ] `checks.testCoverage` — test quality and coverage (via QA-TestAnalyzer)
- [ ] `checks.documentation` — doc coverage and accuracy (via QA-DocsAnalyzer)

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
    testCoverage: PASS | FAIL
    documentation: PASS | FAIL
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
