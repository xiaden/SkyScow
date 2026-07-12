---
description: Run the quality pipeline — format, lint, typecheck — and report results
argument-hint: "[path|.] [--fix] [--strict]"
---

# Quality Gate Command

Run the quality pipeline on demand for a file or project scope.

## Usage

`/quality-gate [path|.] [--fix] [--strict]`

- Default target: current directory (`.`)
- `--fix`: Allow auto-format/fix where configured
- `--strict`: Fail on warnings where supported

## Pipeline

Run each step and collect results. If a step fails, continue to the next step but mark the gate as failed.

### Step 1: Detect Tooling

Identify the language and available tooling for the target:

- **TypeScript/JavaScript**: `prettier`, `eslint`, `tsc`
- **Python**: `black`/`ruff format`, `ruff check`/`pylint`, `mypy`/`pyright`
- **Rust**: `cargo fmt`, `cargo clippy`, `cargo check`
- **Go**: `gofmt`/`goimports`, `golangci-lint`, `go vet`
- **Kotlin**: `ktlint`, `detekt`, Kotlin compiler
- **Java**: `google-java-format`, `checkstyle`, `javac`

### Step 2: Format Check

Run the project's formatter in check mode (or apply with `--fix`):

| Language | Check Command | Fix Command |
|----------|--------------|-------------|
| TS/JS | `npx prettier --check .` | `npx prettier --write .` |
| Python | `ruff format --check .` | `ruff format .` |
| Rust | `cargo fmt --check` | `cargo fmt` |
| Go | `gofmt -l .` | `gofmt -w .` |

### Step 3: Lint Check

Run the project's linter:

| Language | Command |
|----------|---------|
| TS/JS | `npx eslint .` |
| Python | `ruff check .` |
| Rust | `cargo clippy -- -D warnings` |
| Go | `golangci-lint run` |

### Step 4: Type Check (if applicable)

| Language | Command |
|----------|---------|
| TypeScript | `npx tsc --noEmit` |
| Python | `mypy .` or `pyright` |
| Rust | (covered by `cargo check`) |
| Go | (compiled — `go build ./...`) |

### Step 5: Build Check

| Language | Command |
|----------|---------|
| TS/JS | `npm run build` |
| Rust | `cargo check` |
| Go | `go build ./...` |

## Output Format

```
Quality Gate Report
==================
Target: <path>
Mode: <check|fix> <standard|strict>

Results:
  Format:  PASS/FAIL  [details]
  Lint:    PASS/FAIL  [details]
  Types:   PASS/FAIL  [details]
  Build:   PASS/FAIL  [details]

Overall: PASS/FAIL (X/4 passed)

Remediation:
[If any step failed, list specific files and issues to fix]
```

## Verification Checklist

When running the full gate, also check:

- [ ] No `console.log` statements (unless intentional logging)
- [ ] No hardcoded secrets or API keys
- [ ] Bundle/build output size is reasonable
- [ ] No leftover debug code or `TODO` comments without tickets

## Arguments

$ARGUMENTS:
- `[path|.]` optional target path
- `--fix` optional — apply fixes automatically
- `--strict` optional — fail on warnings
