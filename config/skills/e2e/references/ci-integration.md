# CI Integration

## Table of Contents
- [Pipeline Configuration](#pipeline-configuration)
- [Parallelization Strategies](#parallelization-strategies)
- [Artifact Management](#artifact-management)
- [Environment Setup](#environment-setup)
- [Reporting and Metrics](#reporting-and-metrics)

---

## Pipeline Configuration

### GitHub Actions

```yaml
# .github/workflows/e2e.yml
name: E2E Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  e2e:
    runs-on: ubuntu-latest
    timeout-minutes: 30
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      
      - name: Install dependencies
        run: npm ci
      
      - name: Install Playwright browsers
        run: npx playwright install --with-deps
      
      - name: Start application
        run: npm run dev &
        env:
          PORT: 3000
      
      - name: Wait for application
        run: npx wait-on http://localhost:3000
      
      - name: Run Playwright tests
        run: npx playwright test
      
      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: playwright-report
          path: playwright-report/
          retention-days: 30
```

### GitLab CI

```yaml
# .gitlab-ci.yml
e2e-tests:
  stage: test
  image: mcr.microsoft.com/playwright:v1.40.0-jammy
  timeout: 30m
  
  before_script:
    - npm ci
    - npm run build
    - npm run start &
    - sleep 10
  
  script:
    - npx playwright test
  
  artifacts:
    when: always
    paths:
      - playwright-report/
      - test-results/
    expire_in: 30 days
  
  retry:
    max: 2
    when: runner_system_failure
```

---

## Parallelization Strategies

### Shard Tests Across Machines

```yaml
# GitHub Actions - shard across 4 runners
e2e:
  strategy:
    matrix:
      shard: [1, 2, 3, 4]
  
  steps:
    - name: Run tests
      run: npx playwright test --shard=${{ matrix.shard }}/4
```

### Configure Parallel Execution

```typescript
// playwright.config.ts
export default defineConfig({
  // Run tests in parallel within each worker
  fullyParallel: true,
  
  // Number of parallel workers
  workers: process.env.CI ? 4 : undefined,
  
  // Retry failed tests
  retries: process.env.CI ? 2 : 0,
})
```

### Group Tests by Feature

```typescript
// playwright.config.ts
export default defineConfig({
  projects: [
    { name: 'auth', testMatch: /auth.*\.spec\.ts/ },
    { name: 'checkout', testMatch: /checkout.*\.spec\.ts/ },
    { name: 'search', testMatch: /search.*\.spec\.ts/ },
  ],
})

// Run specific project
// npx playwright test --project=auth
```

---

## Artifact Management

### Configure Artifact Collection

```typescript
// playwright.config.ts
export default defineConfig({
  use: {
    // Screenshot on failure
    screenshot: 'only-on-failure',
    
    // Record video on failure
    video: 'retain-on-failure',
    
    // Record trace on first retry
    trace: 'on-first-retry',
  },
})
```

### Upload Artifacts in CI

```yaml
# GitHub Actions
- name: Upload artifacts
  if: failure()
  uses: actions/upload-artifact@v4
  with:
    name: e2e-artifacts
    path: |
      test-results/
      playwright-report/
    retention-days: 7
```

### Network Recording (HAR)

```typescript
test('should capture network traffic', async ({ page }) => {
  await page.routeFromHAR('./har/network.har', {
    url: '*/api/**',
    update: true,
  })
  
  // Test code
})
```

---

## Environment Setup

### Use Docker for Consistency

```dockerfile
# Dockerfile.e2e
FROM mcr.microsoft.com/playwright:v1.40.0-jammy

WORKDIR /app
COPY package*.json ./
RUN npm ci

COPY . .
RUN npx playwright install --with-deps

CMD ["npx", "playwright", "test"]
```

### Environment Variables

```typescript
// playwright.config.ts
export default defineConfig({
  use: {
    baseURL: process.env.BASE_URL || 'http://localhost:3000',
    
    // Authentication
    storageState: process.env.AUTH_STATE || 'auth.json',
    
    // Timeouts
    actionTimeout: process.env.CI ? 15000 : 5000,
    navigationTimeout: process.env.CI ? 30000 : 10000,
  },
})
```

### Database Seeding

```typescript
// global-setup.ts
import { FullConfig } from '@playwright/test'
import { seedDatabase } from './test-utils/seed'

async function globalSetup(config: FullConfig) {
  if (process.env.CI) {
    await seedDatabase()
  }
}

export default globalSetup
```

---

## Reporting and Metrics

### Generate Multiple Report Formats

```typescript
// playwright.config.ts
export default defineConfig({
  reporter: [
    ['html', { open: 'never' }],
    ['junit', { outputFile: 'test-results/junit.xml' }],
    ['json', { outputFile: 'test-results/results.json' }],
  ],
})
```

### Custom Test Report

```typescript
// test-report.ts
import { readFileSync } from 'fs'

const results = JSON.parse(readFileSync('test-results/results.json', 'utf-8'))

const summary = {
  total: results.suites.reduce((acc, s) => acc + s.specs.length, 0),
  passed: results.stats.expected,
  failed: results.stats.unexpected,
  flaky: results.stats.flaky,
  duration: results.stats.duration,
}

console.log(`
# E2E Test Report
**Duration:** ${Math.round(summary.duration / 1000)}s
**Status:** ${summary.failed === 0 ? 'PASSING' : 'FAILING'}

## Summary
- Passed: ${summary.passed} (${Math.round(summary.passed / summary.total * 100)}%)
- Failed: ${summary.failed}
- Flaky: ${summary.flaky}
- Total: ${summary.total}
`)
```

### Track Test Metrics Over Time

```yaml
# GitHub Actions - upload metrics
- name: Upload test metrics
  if: always()
  run: |
    echo "test_duration=$(jq '.stats.duration' test-results/results.json)" >> $GITHUB_ENV
    echo "test_pass_rate=$(jq '.stats.expected / .stats.expected * 100' test-results/results.json)" >> $GITHUB_ENV
```
