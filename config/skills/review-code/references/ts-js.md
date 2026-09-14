# TypeScript / JavaScript Code Review

**Purpose:** Language-specific code review checklist for TypeScript and JavaScript — security, code quality, performance, and best practices.
**Scope:** All `.ts`, `.tsx`, `.js`, `.jsx` files including library modules, application code, and tests.

## Verification Commands

Run the repository's own commands for the changed surface; do not default to a toolchain the repository does not have. Select the evidence from the surface-to-evidence table in `config/instructions/validation-mandate.md`:
- Run the repository's own type-check command, when defined
- Run the repository's own lint command, when defined
- Run the repository's own formatter check, when defined
- Run the repository's own test command for the changed surface, when defined

Omit any check the repository does not define and report it as unavailable rather than inventing a command.

## [CRITICAL] Security

Apply these checks when the changed surface is observably security-sensitive — authentication or
authorization, payments, secrets or credentials, user/external input handling, persisted or
transmitted sensitive data, external systems, deployment or security configuration, or
agent/MCP/plugin/permission surfaces. Those surfaces are owned by
`config/skills/security-review/SKILL.md`, which carries the full OWASP/AgentShield methodology.

For non-security changes, preserve existing security invariants under ordinary correctness review
without running the full generic checklist. This does not weaken the severity or verdict rules: any
CRITICAL or HIGH issue found, by any path, still blocks merge.

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
- **Inconsistent formatting**: Run the repository's own formatter when one is defined; omit and report a repository that defines none

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
- Run the repository's own formatter command on modified files after reviewing, when defined
- Run the repository's own type-check command to verify type safety, when defined
- Check for console.log statements and remove them
- Run the repository's own test command for the changed surface, when defined

Omit and report any command the repository does not define.

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

## Repository Commands

Discover and run the repository's own commands before manual review — do not assume ECC or any
specific toolchain is present:
- Lint — run the repository's own lint command for the changed files, when defined
- Format — run the repository's own formatter command for the changed files, when defined
- Tests — run the repository's own test command for the changed surface, when defined
- Coverage — verify against the repository-defined coverage gate when one exists; impose no universal threshold (see `config/instructions/validation-mandate.md`)
- Security — for observably security-sensitive surfaces, run the security review (canonical owner: `config/skills/security-review/SKILL.md`); non-security changes preserve existing security invariants under ordinary correctness review

Omit and report any command the repository does not define.
