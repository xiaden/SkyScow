# Core Patterns

## Contents
- [Test Structure](#test-structure)
- [Selector Strategy](#selector-strategy)
- [Wait Strategy](#wait-strategy)
- [Test Isolation](#test-isolation)

---

## Test Structure

Follow the AAA pattern (Arrange, Act, Assert) within `test.describe` blocks. Use meaningful names: `test('should [expected behavior] when [condition]')`.

```typescript
import { test, expect } from '@playwright/test'

test.describe('Feature: [Name]', () => {
  test.beforeEach(async ({ page }) => {
    // Setup: navigate, authenticate, prepare state
  })

  test('should [expected behavior]', async ({ page }) => {
    // Arrange: Set up test data
    // Act: Perform user actions
    await page.click('[data-testid="button"]')
    // Assert: Verify results
    await expect(page.locator('[data-testid="result"]')).toBeVisible()
  })

  test.afterEach(async ({ page }, testInfo) => {
    if (testInfo.status !== 'passed') {
      await page.screenshot({ path: `test-results/${testInfo.title}.png` })
    }
  })
})
```

---

## Selector Strategy

Use selectors in this priority order, from most stable to most brittle:

1. **`data-testid` attributes** — controlled by your team, stable across UI changes
2. **Semantic selectors** — `getByRole()`, `getByLabel()`, `getByText()`
3. **Avoid CSS classes** — they change with styling updates and refactors

```typescript
// ✅ Preferred — stable, intentional
await page.locator('[data-testid="submit-button"]').click()
await page.getByRole('button', { name: 'Submit' }).click()
await page.getByLabel('Email address').fill('user@example.com')

// ❌ Avoid — brittle, coupled to styling
await page.locator('.btn-primary.submit-btn').click()
await page.locator('#user-form > div:nth-child(3)').click()
```

---

## Wait Strategy

Prefer Playwright's built-in auto-waiting over manual timeouts or sleeps:

```typescript
// ✅ Auto-waiting assertions — Playwright retries until condition is met or timeout
await expect(page.locator('[data-testid="result"]')).toBeVisible()
await expect(page.locator('[data-testid="count"]')).toHaveText('5')
await expect(page.locator('[data-testid="input"]')).toHaveValue('test')

// ✅ Locator actions auto-wait for element to be actionable
await page.locator('[data-testid="button"]').click()

// ✅ Wait for a specific network response instead of guessing timing
await page.waitForResponse(resp =>
  resp.url().includes('/api/search') && resp.status() === 200
)

// ❌ Brittle — arbitrary waits that mask real timing issues
await page.waitForTimeout(2000)
```

---

## Test Isolation

Each test must be independently runnable. No shared state, no ordering dependencies.

```typescript
// ✅ Unique test data per test prevents collisions
test('should update user', async ({ page }) => {
  const uniqueEmail = `test-${Date.now()}@example.com`
  await createUser(page, uniqueEmail)
  await loginUser(page, uniqueEmail)
})

// ✅ Set up and tear down in beforeEach/afterEach
test.beforeEach(async ({ page }) => {
  await page.context().clearCookies()
  await page.evaluate(() => localStorage.clear())
})

test.afterEach(async ({ page }) => {
  await page.close()
})
```
