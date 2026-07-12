# Playwright CLI Commands

## Contents
- [Running Tests](#running-tests)
- [Debugging](#debugging)
- [Generating Tests](#generating-tests)
- [Reporting](#reporting)
- [Browser Selection](#browser-selection)
- [Update Snapshots](#update-snapshots)

---

## Running Tests

```bash
# Run all E2E tests
npx playwright test

# Run a specific test file
npx playwright test tests/auth.spec.ts

# Run tests matching a grep pattern
npx playwright test --grep "login"

# Run tests excluding a pattern
npx playwright test --grep-invert "@flaky"

# Run a specific project from config
npx playwright test --project=chromium
npx playwright test --project=auth

# Run tests in headed mode (see browser)
npx playwright test --headed

# Run with specific number of retries
npx playwright test --retries=3

# Repeat tests to catch intermittent failures
npx playwright test --repeat-each=10
```

---

## Debugging

```bash
# Debug test with Playwright Inspector
npx playwright test --debug

# Run with trace (for post-mortem debugging)
npx playwright test --trace on

# Run a single test with full debug output
npx playwright test tests/auth.spec.ts --debug

# Step through test one action at a time
npx playwright test --debug --workers=1
```

---

## Generating Tests

```bash
# Open Playwright codegen (record browser actions as test code)
npx playwright codegen http://localhost:3000

# Codegen targeting a specific device
npx playwright codegen --device="iPhone 13" http://localhost:3000

# Codegen and save to a file
npx playwright codegen --output tests/new-feature.spec.ts http://localhost:3000
```

---

## Reporting

```bash
# Open the HTML report
npx playwright show-report

# Specify a custom report directory
npx playwright show-report playwright-report

# Generate reports in multiple formats (configured in playwright.config.ts):
# HTML, JUnit XML, JSON
```

---

## Browser Selection

```bash
# Run in specific browser
npx playwright test --project=chromium
npx playwright test --project=firefox
npx playwright test --project=webkit

# Install browsers (run after npm install)
npx playwright install
npx playwright install --with-deps  # includes system dependencies
```

---

## Update Snapshots

```bash
# Update all visual snapshots
npx playwright test --update-snapshots

# Update snapshots for a specific project
npx playwright test --update-snapshots --project=chromium
```
