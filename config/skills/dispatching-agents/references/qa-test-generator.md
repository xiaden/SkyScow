# QA-TestGenerator

Dispatch QA-TestGenerator to generate tests for coverage gaps identified by QA-TestAnalyzer.

## When to Dispatch

**Dispatch when:**
- QA-TestAnalyzer reports MINOR_DISPATCH or MAJOR_DISPATCH with specific surviving candidates
- You have a concrete list of missing tests to generate

**Do NOT dispatch when:**
- You need test coverage analysis — use `qa-test-analyzer` instead
- No candidate gaps have been identified — generation needs specific targets

## Dispatch Template

```
Generate tests for the following coverage gaps.

Context files to read:
- [files that need tests]
- [reference tests for pattern/style guidance]

task_family: "[existing task family]"
round: [positive QA round number]

gaps:
  - file: "[path to source file]"
    subject: {kind: behavior, module: "[module]", symbol: "[function/class/path]"}
    missing:
      - "[function/class/path that needs tests]"
    reason: "[why it needs tests — e.g., 'core auth logic, no tests exist']"
  # ... repeat per gap

Follow project test conventions. Every invocation ends in exactly one verified terminal decision
(REPAIRED, UNNECESSARY, BLOCKED, or ESCALATED) written durably via qa_record_write BEFORE you return.
Keep a meaningful behavioral oracle, exercise real callers where possible, run every test, lint to zero
errors, and avoid excessive mocking. Leaf agent — no children.
```

## Required Fields

| Field | Description | Example |
|-------|-------------|---------|
| `gaps` | Surviving candidate list from QA-TestAnalyzer | See template |
| `subject` | Stable identity for the gap | `{kind: behavior, module: "src/auth/service", symbol: "validateToken"}` |
| `file` | Path to source file needing tests | `src/auth/service.ts` |
| `missing` | Functions/classes/paths needing tests | `validateToken()`, `refreshSession()` |
| `reason` | Why tests are needed | "Core auth logic — validateToken has no test coverage" |
| `task_family` | Existing task family for the durable record | `TASK-auth-A-login` |
| `round` | Positive QA round number | `1` |

## Terminal Contract

Every invocation ends in **exactly one** verified terminal decision, written via `qa_record_write`
**before return**:

- `REPAIRED` — tests were changed. Requires non-empty actual verification and at least one changed file
  or symbol.
- `UNNECESSARY` — repository-derived evidence shows the gap does not warrant a test. Requires non-empty
  repository-derived evidence.
- `BLOCKED` — the gap cannot be completed now.
- `ESCALATED` — an implementation defect or out-of-remit decision was found.

The record requires `writer`/`agent` = `qa-test-generator`, the task family and positive round, a stable
`subject` (kind plus at least one identifying key), `decision`, `evidence`, `verification`,
`changed_files`/`changed_symbols` (empty only for a no-change outcome; `REPAIRED` needs at least one),
and `source_kind: "analyzer-finding"` plus `source_ref`. A failed or missing write is a failed
invocation.

## Expected Output

- Generated test files following project conventions
- The terminal decision and the durable record path (`artifacts/logs/qa-rounds/{family}/round-{N}/qa-test-generator.jsonl`)
- Test results (passing/failing) and lint status
- Any tests that couldn't be generated with reason

This agent is **leaf** — it does not spawn children. It generates tests, runs them to verify they pass,
records its terminal decision, and reports completion.

## After Generation

- Verify generated tests pass (`[test runner]`)
- Confirm the durable record was written before the report
- If tests fail, fix the tests (not the source code) unless the failure reveals a real bug
