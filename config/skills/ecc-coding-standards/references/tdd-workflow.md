# TDD Workflow

## When This Applies

RED → GREEN → REFACTOR is available guidance for surfaces with an executable behavioral oracle — it is not a universal edit-order ceremony. Apply it when at least one of these observable facts holds:

- The change adds or fixes behavior and an executable oracle exists (a unit, contract, or regression test can express the expected behavior).
- A reported defect can be reproduced by a regression test.
- The repository already uses test-first style for the changed surface.
- A spec-first test reduces ambiguity in the requirement.

Do not force artificial RED for static configuration, packaging, Dockerfiles, deployment manifests, docs, mechanical migrations, build metadata, or infrastructure — for those surfaces the requirement is behavioral evidence from the build, smoke, or runtime check selected per `config/instructions/validation-mandate.md`.

When a test does fail, follow the troubleshooting protocol below before changing test assertions. Coverage is a diagnostic; honor a repository-defined coverage threshold when one exists and impose no universal percentage.

## TDD Cycle (RED → GREEN → REFACTOR)

| Phase | Action | Success Criterion |
|-------|--------|-------------------|
| **RED** | Write a failing test that describes the desired behavior — when an executable behavioral oracle exists; otherwise identify the build/smoke/runtime check that will prove the change | Test runs and FAILS (not skipped, not errored — fails) |
| **GREEN** | Write the minimal implementation to make the test pass | Test PASSES; no extra behavior implemented |
| **REFACTOR** | Improve code structure while keeping tests green | Tests still pass; code is cleaner; no behavior change |

**Violation examples:**
- Writing implementation first, then adding tests to match → tests verify what was written, not what was intended
- Making a test pass by changing the assertion instead of fixing the code
- Skipping the RED phase on a surface that has an executable behavioral oracle — if the test doesn't fail first on such a surface, it is not testing anything new (static config, packaging, docs, build metadata, and infrastructure are proven by a build/smoke/runtime check instead)

## Coverage

Coverage is a useful diagnostic when the repository supports it. Honor a repository-defined coverage
threshold when one exists; impose no universal percentage. Coverage is selected from the observable
changed surface per the surface-selection table in `config/instructions/validation-mandate.md`.

**Violation examples:**
- Selecting test types by doctrine instead of by the observable changed surface — unit, integration, and E2E are surface-selected per `config/instructions/validation-mandate.md`, not universally stacked
- Arguing "the rest is hard to test" to justify untested code → untested code is untrusted code
- Tests that pass but don't assert anything meaningful (no assertions, or assertions that always pass)

### Test Types by Scope

| Test Type | Scope | Example |
|-----------|-------|---------|
| **Unit** | Individual functions, utilities, components | `updateUser()` returns new object with updated name |
| **Integration** | API endpoints, database operations, service boundaries | `POST /users` creates user and returns 201 |
| **E2E** | Critical user flows through the full stack | User signs up, verifies email, logs in |

## Troubleshooting Test Failures

When a test fails, follow this order before changing anything:

1. **Read the failure message** — what exactly is expected vs actual?
2. **Check test isolation** — does this test depend on state from another test? Each test must be independent.
3. **Verify mocks match reality** — do the mocked interfaces match the actual function signatures and return types?
4. **Run the test in isolation** — `test.only` / `pytest -k` — to rule out ordering effects
5. **Fix the implementation, not the test** — unless the test itself is genuinely wrong (stale assertion, renamed function)

**Violation examples:**
- Immediately changing the test assertion to match the new output
- Disabling a failing test with `test.skip` instead of investigating
- "The test is flaky" without investigating the race condition or shared state

## Enforcement

- **CI gate:** Fail the build only when the repository defines a coverage gate and coverage drops below the repository's own threshold; impose no universal percentage.
- **PR review:** Verify new code has corresponding tests; reject PRs with test-only skips. Honor a repository-defined coverage threshold when one exists; do not apply a universal percentage.
- **Pre-commit:** Run the repository-defined test command for the changed surface before every commit; omit and report a repository that defines none (see `config/instructions/validation-mandate.md`)
- **Pre-commit verification:** Run the repository-defined verification for the changed surface; coverage is included only when the repository configures a coverage gate (see `config/instructions/validation-mandate.md`)
- **Coverage reports:** Generate and review coverage reports when the repository supports coverage, honoring its own gate; impose no universal percentage
