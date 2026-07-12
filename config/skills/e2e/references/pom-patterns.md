# Page Object Model Patterns

## Table of Contents
- [Basic POM Structure](#basic-pom-structure)
- [Component Composition](#component-composition)
- [Fixture Integration](#fixture-integration)
- [Advanced Techniques](#advanced-techniques)

---

## Basic POM Structure

```typescript
import { Page, Locator } from '@playwright/test'

export class MarketsPage {
  readonly page: Page
  readonly searchInput: Locator
  readonly resultsList: Locator
  readonly loadingSpinner: Locator

  constructor(page: Page) {
    this.page = page
    this.searchInput = page.locator('[data-testid="search-input"]')
    this.resultsList = page.locator('[data-testid="results-list"]')
    this.loadingSpinner = page.locator('[data-testid="loading-spinner"]')
  }

  async goto() {
    await this.page.goto('/markets')
    await this.page.waitForLoadState('networkidle')
  }

  async searchMarkets(query: string) {
    await this.searchInput.fill(query)
    await this.page.waitForResponse(resp => 
      resp.url().includes('/api/markets/search') && resp.status() === 200
    )
    await this.loadingSpinner.waitFor({ state: 'hidden' })
  }

  async getResultCount(): Promise<number> {
    return await this.resultsList.locator('li').count()
  }

  async selectMarket(index: number) {
    await this.resultsList.locator('li').nth(index).click()
  }
}
```

---

## Component Composition

Break down complex pages into reusable components:

```typescript
// components/HeaderComponent.ts
export class HeaderComponent {
  readonly page: Page
  readonly logo: Locator
  readonly userMenu: Locator

  constructor(page: Page) {
    this.page = page
    this.logo = page.locator('[data-testid="logo"]')
    this.userMenu = page.locator('[data-testid="user-menu"]')
  }

  async clickLogo() {
    await this.logo.click()
  }

  async openUserMenu() {
    await this.userMenu.click()
  }
}

// pages/DashboardPage.ts
export class DashboardPage {
  readonly page: Page
  readonly header: HeaderComponent
  
  constructor(page: Page) {
    this.page = page
    this.header = new HeaderComponent(page)
  }

  async goto() {
    await this.page.goto('/dashboard')
  }
}
```

---

## Fixture Integration

Use Playwright fixtures for automatic page object instantiation:

```typescript
// fixtures.ts
import { test as base } from '@playwright/test'
import { DashboardPage } from './pages/DashboardPage'
import { MarketsPage } from './pages/MarketsPage'

type PageObjects = {
  dashboardPage: DashboardPage
  marketsPage: MarketsPage
}

export const test = base.extend<PageObjects>({
  dashboardPage: async ({ page }, use) => {
    await use(new DashboardPage(page))
  },
  marketsPage: async ({ page }, use) => {
    await use(new MarketsPage(page))
  },
})

export { expect } from '@playwright/test'

// tests/example.spec.ts
import { test, expect } from '../fixtures'

test('should navigate to markets', async ({ dashboardPage, marketsPage }) => {
  await dashboardPage.goto()
  await dashboardPage.header.clickLogo()
  await marketsPage.searchMarkets('tech')
  await expect(marketsPage.resultsList).toBeVisible()
})
```

---

## Advanced Techniques

### Lazy Locators

Define locators as getters for better performance:

```typescript
export class LoginPage {
  readonly page: Page

  constructor(page: Page) {
    this.page = page
  }

  get usernameInput(): Locator {
    return this.page.locator('[data-testid="username"]')
  }

  get passwordInput(): Locator {
    return this.page.locator('[data-testid="password"]')
  }

  get submitButton(): Locator {
    return this.page.locator('[data-testid="submit"]')
  }

  async login(username: string, password: string) {
    await this.usernameInput.fill(username)
    await this.passwordInput.fill(password)
    await this.submitButton.click()
  }
}
```

### Page Object Inheritance

Create base classes for common functionality:

```typescript
export abstract class BasePage {
  readonly page: Page

  constructor(page: Page) {
    this.page = page
  }

  async waitForPageLoad() {
    await this.page.waitForLoadState('networkidle')
  }

  async takeScreenshot(name: string) {
    await this.page.screenshot({ path: `screenshots/${name}.png` })
  }

  async getCurrentUrl(): Promise<string> {
    return this.page.url()
  }
}

export class HomePage extends BasePage {
  async goto() {
    await this.page.goto('/')
    await this.waitForPageLoad()
  }
}
```

### Method Chaining

Enable fluent API patterns:

```typescript
export class SearchPage {
  readonly page: Page

  constructor(page: Page) {
    this.page = page
  }

  async enterQuery(query: string): Promise<SearchPage> {
    await this.page.locator('[data-testid="search"]').fill(query)
    return this
  }

  async selectCategory(category: string): Promise<SearchPage> {
    await this.page.locator('[data-testid="category"]').selectOption(category)
    return this
  }

  async submit(): Promise<SearchPage> {
    await this.page.locator('[data-testid="submit"]').click()
    return this
  }
}

// Usage
await searchPage
  .enterQuery('laptop')
  .selectCategory('electronics')
  .submit()
```
