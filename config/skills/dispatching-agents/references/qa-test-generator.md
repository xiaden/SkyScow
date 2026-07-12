# QA-TestGenerator

Dispatch QA-TestGenerator to generate tests for coverage gaps identified by QA-TestAnalyzer.

## When to Dispatch

**Dispatch when:**
- QA-TestAnalyzer reports MINOR_DISPATCH or MAJOR_DISPATCH with specific gaps
- You have a concrete list of missing tests to generate

**Do NOT dispatch when:**
- You need test coverage analysis — use `qa-test-analyzer` instead
- No gaps have been identified — generation needs specific targets
- The tests are trivial (simple assertions on pure functions) — write them yourself

## Dispatch Template

```
Generate tests for the following coverage gaps:

Context files to read:
- [files that need tests]
- [reference tests for pattern/style guidance]

gaps:
  - file: "[path to source file]"
    missing:
      - "[function/class/path that needs tests]"
    reason: "[why it needs tests — e.g., 'core auth logic, no tests exist']"
  # ... repeat per gap

Follow project test conventions. Write tests, run them, report results. Leaf agent — no children.
```

## Required Fields

| Field | Description | Example |
|-------|-------------|---------|
| `gaps` | List of gaps from QA-TestAnalyzer | See template |
| `file` | Path to source file needing tests | `src/auth/service.ts` |
| `missing` | Functions/classes/paths needing tests | `validateToken()`, `refreshSession()` |
| `reason` | Why tests are needed | "Core auth logic — validateToken has no test coverage" |

## Expected Output

- Generated test files following project conventions
- Test results (passing/failing)
- Coverage improvement summary
- Any tests that couldn't be generated with reason

This agent is **leaf** — it does not spawn children. It generates tests, runs them to verify they pass, and reports completion.

## After Generation

- Verify generated tests pass (`[test runner]`)
- Report coverage improvement
- If tests fail, fix the tests (not the source code) unless the failure reveals a real bug
