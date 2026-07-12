# TDD Workflow

## When This Applies

- Before writing any new feature, function, or bug fix
- When tests fail — follow the troubleshooting protocol before changing test assertions
- When adding regression tests for a reported bug
- When refactoring — tests must pass before and after; coverage must not decrease

## TDD Cycle (RED → GREEN → REFACTOR)

| Phase | Action | Success Criterion |
|-------|--------|-------------------|
| **RED** | Write a failing test that describes the desired behavior | Test runs and FAILS (not skipped, not errored — fails) |
| **GREEN** | Write the minimal implementation to make the test pass | Test PASSES; no extra behavior implemented |
| **REFACTOR** | Improve code structure while keeping tests green | Tests still pass; code is cleaner; no behavior change |

**Violation examples:**
- Writing implementation first, then adding tests to match → tests verify what was written, not what was intended
- Making a test pass by changing the assertion instead of fixing the code
- Skipping the RED phase — if the test doesn't fail first, it's not testing anything new

## Coverage Targets (Tiered)

All three test types (unit, integration, E2E) are required. Coverage targets scale by code criticality — higher risk demands higher coverage:

| Code Type | Minimum Coverage | Examples |
|-----------|-----------------|----------|
| **Critical** | **100%** | Authentication logic, authorization checks, financial calculations, security-critical code, payment processing |
| **Standard** | **80%** | Business logic, API handlers, data transformations, service layer, utilities |
| **UI / Presentation** | **70%** | UI components, layout code, style-only rendering |

**Violation examples:**
- Auth logic at 78% coverage — critical code is not "close enough"; it must be 100%
- Only unit tests, no integration or E2E → misses wiring bugs between layers
- Coverage at 60% with "the rest is hard to test" → untested code is untrusted code
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

- **CI gate:** Fail the build if coverage drops below tiered targets (100% critical, 80% standard, 70% UI)
- **PR review:** Verify new code has corresponding tests; reject PRs with test-only skips; flag critical code below 100%
- **Pre-commit:** Run the fast test suite (unit tests) before every commit
- **Pre-commit verification:** Coverage check is step 5 of the [verification loop](file:///home/opencode/.config/opencode/skills/ecc-coding-standards/references/verification.md)
- **Coverage reports:** Generate and review coverage reports weekly; track trends per code tier
