# TypeScript / JavaScript Code Review

**Purpose:** Language-specific code review checklist for TypeScript and JavaScript — security, code quality, performance, and best practices.
**Scope:** All `.ts`, `.tsx`, `.js`, `.jsx` files including library modules, application code, and tests.

## Verification Commands
- `tsc --noEmit` — type safety check
- `eslint .` — linting
- `prettier --check .` — formatting check
- `npm test` / `bun test` — all tests pass

## [CRITICAL] Security
- **Hardcoded credentials**: API keys, passwords, tokens in source code
- **SQL injection risks**: String concatenation in queries
- **XSS vulnerabilities**: Unescaped user input rendered in DOM
- **Missing input validation**: No validation on external data
- **Insecure dependencies**: Outdated, vulnerable packages
- **Path traversal risks**: User-controlled file paths without sanitization
- **CSRF vulnerabilities**: Missing CSRF tokens on state-changing requests
- **Authentication bypasses**: Improper auth checks

## [HIGH] Code Quality
- **Large functions**: Over 50 lines
- **Large files**: Over 800 lines
- **Deep nesting**: More than 4 levels of indentation
- **Missing error handling**: No try/catch or unhandled promise rejections
- **console.log statements**: Debug logging left in production code
- **Mutation patterns**: Prefer immutability (spread operator, `Object.freeze`)
- **Missing tests**: New code without test coverage

## [MEDIUM] Performance
- **Inefficient algorithms**: O(n²) when O(n log n) possible
- **Unnecessary re-renders in React**: Missing `useMemo`, `useCallback`, `React.memo`
- **Missing memoization**: Expensive computations not cached. **Impact: 2-5x unnecessary recomputation per render cycle.**
- **Missing `key` in React lists**: Reconciliation bugs, performance issues. **Impact: full list re-render on every state change.**
- **Large bundle sizes**: Unoptimized imports, tree-shaking issues
- **Unoptimized images**: Missing lazy loading, wrong formats
- **Missing caching**: Repeated expensive operations
- **N+1 queries**: Database queries in loops. **Impact: 10-100x slower on large datasets.**

## [MEDIUM] Best Practices
- **Emoji usage in code/comments**: Keep codebase professional
- **TODO/FIXME without tickets**: Every TODO needs a tracking ticket
- **Missing JSDoc for public APIs**: Document exported functions and types
- **Accessibility issues**: Missing ARIA labels, poor contrast
- **Poor variable naming**: `x`, `tmp`, `data` — use descriptive names
- **Magic numbers without explanation**: Use named constants
- **Inconsistent formatting**: Run prettier

## Anti-Patterns

| Pattern | Severity | What to Look For |
|---------|----------|------------------|
| Hardcoded API keys | CRITICAL | Secrets in source code — use env vars |
| `any` type usage | HIGH | Bypasses type safety — use specific types |
| Missing error boundaries | HIGH | Unhandled React errors crash the app |
| `==` instead of `===` | MEDIUM | Type coercion bugs |
| `console.log` in production | MEDIUM | Debug noise — use logger |
| Mutable default parameters | HIGH | Shared state bugs — use immutable defaults |
| Missing `key` in React lists | MEDIUM | Reconciliation bugs, performance issues |

## Review Output Format

For each issue:
```
[CRITICAL] Hardcoded API key
File: src/api/client.ts:42
Issue: API key exposed in source code
Fix: Move to environment variable

const apiKey = "sk-abc123";  // Bad
const apiKey = process.env.API_KEY;  // Good
```

## Project-Specific Guidelines

Add project-specific checks here. Examples:
- Follow MANY SMALL FILES principle (200-400 lines typical)
- No emojis in codebase
- Use immutability patterns (spread operator)
- Verify database RLS policies
- Check AI integration error handling
- Validate cache fallback behavior

## Post-Review Actions
- Run `prettier --write` on modified files after reviewing
- Run `tsc --noEmit` to verify type safety
- Check for console.log statements and remove them
- Run tests to verify changes don't break functionality

## Approval Criteria
- **Approve**: No CRITICAL or HIGH issues
- **Warning**: MEDIUM issues only (can merge with caution)
- **Block**: CRITICAL or HIGH issues found

### Quick-Scan
```bash
grep -rn "console\.log" src/ --include="*.ts" --include="*.tsx"    # Debug logging
grep -rn "\.innerHTML" src/ --include="*.tsx"                       # Potential XSS
grep -rn "dangerouslySetInnerHTML" src/ --include="*.tsx"           # Potential XSS
grep -rn "as any" src/ --include="*.ts" --include="*.tsx"          # Type safety bypass
grep -rn "TODO\|FIXME" src/ --include="*.ts" --include="*.tsx"     # Unresolved tech debt
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

## ECC Tools

Prefer ECC tooling for automated checks before manual review:
- `lint-check` — detects Biome/ESLint and returns command
- `format-code` — detects Biome/Prettier and returns command
- `security-audit` — scans for secrets, XSS vectors, and dependency vulnerabilities
- `run-tests` — detects Jest/Vitest and runs test suite
- `check-coverage` — verifies coverage meets the 80% threshold
