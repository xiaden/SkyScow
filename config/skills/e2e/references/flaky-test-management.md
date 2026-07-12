# Flaky Test Management

## Table of Contents
- [Identifying Flaky Tests](#identifying-flaky-tests)
- [Quarantine Strategies](#quarantine-strategies)
- [Root Cause Analysis](#root-cause-analysis)
- [Common Causes and Fixes](#common-causes-and-fixes)
- [Prevention Strategies](#prevention-strategies)

---

## Identifying Flaky Tests

### Repeat Tests Locally

```bash
# Run tests 10 times to catch intermittent failures
npx playwright test --repeat-each=10

# Run specific test file multiple times
npx playwright test tests/auth.spec.ts --repeat-each=20
```

### Analyze CI History

Look for tests with inconsistent pass rates:
- Pass rate < 95% over last 50 runs
- Intermittent failures without code changes
- Failures that resolve on retry

### Use Playwright's Flaky Test Detection

```typescript
// playwright.config.ts
export default defineConfig({
  retries: process.env.CI ? 2 : 0,
  reporter: [
    ['html'],
    ['json', { outputFile: 'test-results.json' }]
  ]
})
```

---

## Quarantine Strategies

### Using test.fixme()

Mark tests as known failures (won't run):

```typescript
test.fixme('should handle concurrent edits', async ({ page }) => {
  // Test is flaky - Issue #123
  // Will be fixed in PR #456
})
```

### Conditional Skip in CI

Skip flaky tests only in CI environment:

```typescript
test('should animate smoothly', async ({ page }) => {
  test.skip(process.env.CI === 'true', 'Flaky in CI - Issue #789')
  // Test code
})
```

### Tag-Based Quarantine

Use tags to group and filter flaky tests:

```typescript
test('should handle network timeout', async ({ page }) => {
  test.skip(process.env.QUARANTINE === 'true', 'Quarantined - Issue #101')
  // Test code
})

// Run only stable tests
QUARANTINE=true npx playwright test --grep-invert="@flaky"
```

---

## Root Cause Analysis

### Checklist for Flaky Tests

1. **Timing issues**: Are you waiting for the right conditions?
2. **Race conditions**: Are multiple async operations competing?
3. **Test data collisions**: Are tests sharing state?
4. **Environment dependencies**: Does the test rely on external services?
5. **Animation/transition timing**: Are you interacting before animations complete?
6. **Network variability**: Are you handling slow/unreliable networks?

---

## Common Causes and Fixes

### Race Conditions

**Problem**: Interacting with elements before they're ready

```typescript
// ❌ Bad
await page.click('[data-testid="button"]')

// ✅ Good - auto-waits for element to be actionable
await page.locator('[data-testid="button"]').click()
```

### Network Timing

**Problem**: Assertions run before API responses arrive

```typescript
// ❌ Bad - arbitrary wait
await page.waitForTimeout(2000)
await expect(page.locator('[data-testid="result"]')).toBeVisible()

// ✅ Good - wait for specific network response
await page.waitForResponse(resp => 
  resp.url().includes('/api/search') && resp.status() === 200
)
await expect(page.locator('[data-testid="result"]')).toBeVisible()
```

### Animation Timing

**Problem**: Clicking elements during transitions

```typescript
// ❌ Bad - element might be animating
await page.click('[data-testid="modal-close"]')

// ✅ Good - wait for element to be stable
await page.locator('[data-testid="modal-close"]').waitFor({ state: 'visible' })
await page.locator('[data-testid="modal-close"]').click()
```

### Test Data Collisions

**Problem**: Tests interfere with each other's data

```typescript
// ❌ Bad - shared test data
test('should update user', async ({ page }) => {
  await loginUser(page, 'testuser@example.com')
  // Another test might be using the same user
})

// ✅ Good - unique test data per test
test('should update user', async ({ page }) => {
  const uniqueEmail = `test-${Date.now()}@example.com`
  await createUser(page, uniqueEmail)
  await loginUser(page, uniqueEmail)
})
```

---

## Prevention Strategies

### Use Auto-Waiting Assertions

```typescript
// ✅ Playwright auto-waits for these assertions
await expect(page.locator('[data-testid="result"]')).toBeVisible()
await expect(page.locator('[data-testid="count"]')).toHaveText('5')
await expect(page.locator('[data-testid="input"]')).toHaveValue('test')
```

### Isolate Test State

```typescript
test.beforeEach(async ({ page }) => {
  // Fresh state for each test
  await page.context().clearCookies()
  await page.evaluate(() => localStorage.clear())
})

test.afterEach(async ({ page }) => {
  // Cleanup
  await page.close()
})
```

### Use Deterministic Selectors

```typescript
// ❌ Brittle - CSS classes change
await page.click('.btn-primary.submit-btn')

// ✅ Stable - data-testid is controlled
await page.click('[data-testid="submit-button"]')

// ✅ Semantic - role-based
await page.getByRole('button', { name: 'Submit' }).click()
```

### Control Time

```typescript
// Mock timers for deterministic behavior
await page.evaluate(() => {
  jest.useFakeTimers()
})

// Or use Playwright's clock API
await page.clock.install()
await page.clock.fastForward(1000)
```
