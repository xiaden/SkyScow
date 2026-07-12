---
name: e2e
description: End-to-end testing methodology using Playwright — test structure, Page Object Model, flaky test management, artifact capture, and CI integration. Use when writing, reviewing, or debugging E2E tests, or when working with Playwright test suites.
---

# E2E Testing

**Purpose:** End-to-end testing methodology for Playwright. Covers the full lifecycle: planning, authoring, debugging flaky tests, and CI integration.

---

## When to Use

**Trigger conditions:**

- Writing or reviewing E2E tests
- Debugging flaky or failing Playwright tests
- Setting up Playwright or CI pipelines for E2E

**Do NOT use when:**

- Writing unit or integration tests
- Working with non-Playwright tools (Cypress, Selenium)
- Testing business logic without UI

---

## Navigation

Use this table to find the right reference for your task:

| Task | Reference |
|------|-----------|
| Writing a test, choosing selectors, setting up isolation | [`references/core-patterns.md`](file:///home/opencode/.config/opencode/skills/e2e/references/core-patterns.md) |
| Designing page objects, fixtures, composition | [`references/pom-patterns.md`](file:///home/opencode/.config/opencode/skills/e2e/references/pom-patterns.md) |
| Debugging flaky tests, quarantining, prevention | [`references/flaky-test-management.md`](file:///home/opencode/.config/opencode/skills/e2e/references/flaky-test-management.md) |
| Configuring CI pipelines, sharding, artifacts | [`references/ci-integration.md`](file:///home/opencode/.config/opencode/skills/e2e/references/ci-integration.md) |
| Running tests, debugging, code generation, reports | [`references/cli-commands.md`](file:///home/opencode/.config/opencode/skills/e2e/references/cli-commands.md) |

---

## E2E Testing Workflow

### 1. Plan Phase
- Identify critical user journeys (auth, core features, payments, data integrity)
- Define test scenarios (happy path, edge cases, error cases)
- Prioritize by risk:
  - **HIGH**: Financial transactions, authentication flows
  - **MEDIUM**: Search/filter, form submissions
  - **LOW**: UI polish, cosmetic changes

### 2. Create Phase
- Write tests following Page Object Model (POM) pattern
- Use meaningful test descriptions: `test('should [expected behavior] when [condition]')`
- Include assertions at key steps
- Capture screenshots at critical interaction points, on failure, and for full-page verification

### 3. Run Phase
- Run across browsers (Chromium, Firefox, WebKit) and mobile viewports
- Capture artifacts — screenshots, videos, and traces (see [`references/core-patterns.md`](file:///home/opencode/.config/opencode/skills/e2e/references/core-patterns.md) for wait strategies)
- Handle flaky tests through quarantine (see [`references/flaky-test-management.md`](file:///home/opencode/.config/opencode/skills/e2e/references/flaky-test-management.md))
- Use CLI commands for headed debugging, retries, and repeat runs (see [`references/cli-commands.md`](file:///home/opencode/.config/opencode/skills/e2e/references/cli-commands.md))

### 4. Report Phase
- Generate HTML reports, JUnit XML, and JSON output
- Summarize pass rates, flaky rates, failures with screenshots and error details
- See [`references/ci-integration.md`](file:///home/opencode/.config/opencode/skills/e2e/references/ci-integration.md) for CI reporting and artifact upload

---

## Core Patterns

For detailed code examples, see [`references/core-patterns.md`](file:///home/opencode/.config/opencode/skills/e2e/references/core-patterns.md).

### Test Structure
Follow AAA (Arrange, Act, Assert) within `test.describe` blocks. Set up state in `beforeEach`, capture screenshots on failure in `afterEach`.

### Selector Strategy
Priority order: `data-testid` → semantic selectors (`getByRole`, `getByLabel`, `getByText`) → avoid CSS classes. `data-testid` is most stable because your team controls it.

### Wait Strategy
Use Playwright's auto-waiting: `expect().toBeVisible()` and locator actions retry until the element is ready. Prefer `page.waitForResponse()` for network-dependent checks. Avoid `page.waitForTimeout()` — it masks real timing issues.

### Test Isolation
Each test must be independently runnable. Use unique test data per test, clear state in `beforeEach`, and close the page in `afterEach`. No shared state, no ordering dependencies.

---

## Validation Checklist

Before declaring E2E work complete:

### Test Quality
- [ ] Test descriptions follow `'should [expected behavior] when [condition]'` format
- [ ] All critical user journeys have test coverage
- [ ] Selectors use `data-testid` or semantic APIs, not CSS classes
- [ ] No `page.waitForTimeout()` calls — use auto-waiting or `waitForResponse`

### Stability
- [ ] Each test is independently runnable (no shared state)
- [ ] Unique test data per test (no hardcoded values that collide)
- [ ] Tests pass consistently when run 3+ times locally

### CI Readiness
- [ ] `playwright.config.ts` configured with CI retries and artifact capture
- [ ] CI pipeline runs tests on relevant branches
- [ ] Test duration is under the CI timeout limit

---

## Success Metrics

- All critical journeys passing (100%)
- Pass rate > 95%
- Flaky rate < 5%
- No failed tests blocking deployment
- Test duration < 10 minutes
