# General Code Review

**Purpose:** Language-agnostic code review checklist for files without a language-specific reference. Covers security, code quality, performance, and best practices across any codebase.
**Scope:** Any source code file not covered by a language-specific reference — applies universal code review standards.

## Verification Commands

Discover the commands the repository actually defines before visual inspection; do not default to a
generic toolchain the repository does not have. Select the evidence from the surface-to-evidence
table in `/home/opencode/.config/opencode/instructions/validation-mandate.md`:
- `git diff` — see recent changes
- Run the repository's own lint command for the changed files, when one is defined
- Run the repository's own formatter command for the changed files, when one is defined
- Run the repository's own type-check, test, and build commands for the changed surface, when defined

Omit any check the repository does not define and report it as unavailable rather than inventing a command.

## [CRITICAL] Security

Apply these checks when the changed surface is observably security-sensitive — authentication or
authorization, payments, secrets or credentials, user/external input handling, persisted or
transmitted sensitive data, external systems, deployment or security configuration, or
agent/MCP/plugin/permission surfaces. Those surfaces are owned by
`/home/opencode/.config/opencode/skills/security-review/SKILL.md`, which carries the full OWASP/AgentShield methodology.

For non-security changes, preserve existing security invariants under ordinary correctness review
without running the full generic checklist. This does not weaken the severity or verdict rules: any
CRITICAL or HIGH issue found, by any path, still blocks merge.

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

## Repository Commands

Discover and run the repository's own commands before manual review — do not assume ECC or any
specific toolchain is present:
- Lint — run the repository's own lint command for the changed files, when defined
- Format — run the repository's own formatter command for the changed files, when defined
- Tests — run the repository's own test command for the changed surface, when defined
- Coverage — verify against the repository-defined coverage gate when one exists; impose no universal threshold (see `/home/opencode/.config/opencode/instructions/validation-mandate.md`)
- Security — for observably security-sensitive surfaces, run the security review (canonical owner: `/home/opencode/.config/opencode/skills/security-review/SKILL.md`); non-security changes preserve existing security invariants under ordinary correctness review

Omit and report any command the repository does not define.
