# General Code Review

**Purpose:** Language-agnostic code review checklist for files without a language-specific reference. Covers security, code quality, performance, and best practices across any codebase.
**Scope:** Any source code file not covered by a language-specific reference — applies universal code review standards.

## Verification Commands

Run these before visual inspection:
- `git diff` — see recent changes
- `lint-check` (ECC tool) — auto-detect and run the appropriate linter
- `format-code` (ECC tool) — auto-detect and run the appropriate formatter
- `security-audit` (ECC tool) — scan for secrets and vulnerabilities
- Run the project's test suite to verify changes don't break functionality

## [CRITICAL] Security

- Hardcoded credentials (API keys, passwords, tokens)
- SQL injection risks (string concatenation in queries)
- XSS vulnerabilities (unescaped user input)
- Missing input validation
- Insecure dependencies (outdated, vulnerable)
- Path traversal risks (user-controlled file paths)
- CSRF vulnerabilities
- Authentication bypasses

## [HIGH] Code Quality

- Large functions (>50 lines)
- Large files (>800 lines)
- Deep nesting (>4 levels)
- Missing error handling (try/catch equivalents)
- Debug/log statements left in production code
- Mutation patterns — prefer immutability
- Missing tests for new code

## [MEDIUM] Performance

- Inefficient algorithms (O(n²) when O(n log n) possible)
- Unnecessary allocations or copies in hot paths
- Missing caching for repeated expensive operations
- N+1 queries (database calls in loops)

## [MEDIUM] Best Practices

- Emoji usage in code/comments — keep professional
- TODO/FIXME without tracking tickets
- Missing documentation for public APIs
- Poor variable naming (x, tmp, data)
- Magic numbers without explanation
- Inconsistent formatting

## Anti-Patterns

| Pattern | Severity | What to Look For |
|---------|----------|------------------|
| Hardcoded secrets | CRITICAL | API keys, passwords, tokens in source code |
| SQL injection | CRITICAL | String concatenation in queries |
| Missing input validation | HIGH | Unvalidated external data |
| Swallowed errors | HIGH | Empty catch blocks, ignored error returns |
| Large monolithic functions | HIGH | Functions > 50 lines |
| Large files | MEDIUM | Files > 800 lines |
| Deep nesting | MEDIUM | > 4 levels of indentation |
| Magic numbers | MEDIUM | Unnamed constants in business logic |
| N+1 queries | HIGH | Database calls in loops |

## Review Output Format

For each issue:
```
[SEVERITY] Issue title
File: path/to/file:line
Issue: Description
Fix: What to change
```

## Review Summary

End every review with:
```
## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0     | pass   |
| HIGH     | 1     | block  |
| MEDIUM   | 2     | info   |
| LOW      | 0     | note   |

Verdict: BLOCK — HIGH issues must be fixed before merge.
```

## Approval Criteria

- **Approve**: No CRITICAL or HIGH issues
- **Warning**: MEDIUM issues only (can merge with caution)
- **Block**: Any CRITICAL or HIGH issues — must fix before merge

## ECC Tools

Prefer ECC tooling for automated checks before manual review:
- `lint-check` — auto-detects and runs the appropriate linter
- `security-audit` — scans for secrets, dependencies, and code security anti-patterns
- `format-code` — auto-detects and runs the appropriate formatter
- `run-tests` — detects package manager and runs test suite
- `check-coverage` — verifies coverage meets the 80% threshold
