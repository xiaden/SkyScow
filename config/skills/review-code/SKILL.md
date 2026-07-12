---
name: review-code
description: Language-specific code review with security, code quality, performance, and best-practice checks. Loads the appropriate review methodology based on file extension — supports TypeScript/JavaScript, Python, Rust, Go, Java, PHP, Kotlin, C++, and PostgreSQL. Use for any code review task; the skill dispatches to the right language reference automatically.
---

# Review Code

Produce thorough, language-specific code reviews by dispatching to the correct review methodology.

## Progressive Disclosure Design

This skill uses the **decision tree** pattern: SKILL.md is a dispatch index loaded on every trigger, while language-specific review checklists live in `references/` and load only for the file extensions being reviewed.

| Level | What loads | When | Contains |
|-------|-----------|------|----------|
| **1. Metadata** | `name` + `description` | Always — listed in `<available_skills>` | Scope and trigger keywords |
| **2. Body** | This dispatch index | When the agent decides to review code | Routing table, workflow, output format |
| **3. References** | One language file per file extension | Only for the extensions in the diff | Full review checklist for that language |

**Never load all references at once.** Load only the reference(s) matching the file extensions you're actually reviewing. The dispatch table below tells you which to open.

## When to Use This Skill

**Trigger conditions:**

- Reviewing code files for security, performance, or quality issues
- Conducting code reviews before merge or deployment
- Analyzing code for language-specific anti-patterns or best practices
- Running language-specific diagnostic commands (linters, type checkers, security scanners)

**Do NOT use this skill when:**

- Writing or editing code (use language-specific style guides instead)
- Debugging runtime errors (use debugging skills or diagnostic tools)
- Refactoring code structure (use refactoring patterns, not review checklists)
- Reviewing configuration files, documentation, or non-code assets (this skill is for source code only)

## Language Dispatch Table

| File Extensions | Reference File | Review Dimensions |
|-----------------|---------------|-------------------|
| `.ts`, `.tsx`, `.js`, `.jsx` | [TS/JS Review](file:///home/opencode/.config/opencode/skills/review-code/references/ts-js.md) | Security (XSS, injection, secrets), type safety, React patterns, bundle size, N+1 queries, console.log, emoji, accessibility |
| `.py` | [Python Review](file:///home/opencode/.config/opencode/skills/review-code/references/python.md) | Security, type hints, async patterns, Pythonic patterns, framework checks (Django, FastAPI, Flask) |
| `.rs` | [Rust Review](file:///home/opencode/.config/opencode/skills/review-code/references/rust.md) | Security, borrow checker, unsafe blocks, panic vs Result, ownership/lifetimes, concurrency |
| `.go` | [Go Review](file:///home/opencode/.config/opencode/skills/review-code/references/go.md) | Security (injection, race conditions), error wrapping, goroutine leaks, nil pointer checks, interface pollution, anti-patterns |
| `.java` | [Java Review](file:///home/opencode/.config/opencode/skills/review-code/references/java.md) | Security, Spring Boot architecture, JPA/database (N+1, transactions), concurrency, testing, Maven/Gradle checks |
| `.php` | [PHP Review](file:///home/opencode/.config/opencode/skills/review-code/references/php.md) | Security (mass assignment, XSS), Eloquent N+1, type juggling, session security, framework checks (Laravel, Livewire, Filament) |
| `.kt`, `.kts` | [Kotlin Review](file:///home/opencode/.config/opencode/skills/review-code/references/kotlin.md) | Security (exported components, crypto), clean architecture, coroutine scopes, Compose recomposition, Android lifecycle |
| `.cpp`, `.hpp`, `.h`, `.cc` | [C++ Review](file:///home/opencode/.config/opencode/skills/review-code/references/cpp.md) | Memory safety (RAII, leaks, use-after-free), security (injection, format strings), concurrency, modern C++ patterns |
| `.sql` | [PostgreSQL Review](file:///home/opencode/.config/opencode/skills/review-code/references/postgres.md) | RLS policies, missing indexes, seq scans, deadlock risks, schema design, cursor pagination, SKIP LOCKED |
| (no language match) | [General Review](file:///home/opencode/.config/opencode/skills/review-code/references/general.md) | Language-agnostic checks for any codebase — security, code quality, performance, best practices |

Each reference file is self-contained: verification commands, severity-tagged checklists (CRITICAL/HIGH/MEDIUM/LOW), language-specific diagnostic tooling, and anti-pattern tables. Open only the ones matching your diff.

## How to Use

1. **Identify file extensions** in the diff or review target
2. **Load only the matching reference(s)** from the dispatch table above — one reference per language family in the diff
3. **Run diagnostic tooling** — use the reference's verification commands first. For linting, type-checking, and formatting, use `aft_inspect` and language-specific tools directly (e.g., `npx tsc --noEmit`, `cargo check`, `mypy`). The `changed-files` tool identifies files in scope.
4. **Work through checklists by severity** — CRITICAL security items first, then HIGH code quality, then MEDIUM performance/best practices, then LOW style issues
5. **Report issues** using the output format below, tagged with the severity from the reference
6. **Verify post-review** — after issues are addressed, run the verification pipeline: type check → lint → tests → build → coverage (mirrors the ECC `/verify` command). Also check for leftover `console.log` statements and unformatted code.

## Review Output Format

All language references use a consistent output format:

```
[SEVERITY] Issue title
File: path/to/file:line
Issue: Description
Fix: What to change
```

## Approval Criteria (General)

| Verdict | Condition |
|---------|-----------|
| **Approve** | No CRITICAL or HIGH issues |
| **Warning** | MEDIUM issues only — merge with caution, note follow-ups |
| **Note** | LOW issues only — style/naming suggestions, non-blocking |
| **Block** | Any CRITICAL or HIGH issue — must fix before merge |

Individual language references may define additional language-specific criteria. The reference's criteria take precedence.

**Severity definitions** (consistent across all references):

| Severity | Scope | Examples |
|----------|-------|----------|
| **CRITICAL** | Security vulnerabilities, data loss, panics/crashes | Hardcoded secrets, SQL injection, unhandled panics, RLS gaps |
| **HIGH** | Correctness, significant quality, maintainability | >50-line functions, >800-line files, deep nesting, missing error handling, N+1 queries |
| **MEDIUM** | Performance, best practices, minor quality | Inefficient algorithms, missing docs, magic numbers, inconsistent patterns |
| **LOW** | Style, formatting, naming | Inconsistent naming, missing type annotations, formatting deviations |

## Diagnostic Tooling

Prefer direct commands and AFT tools over ad-hoc approaches:

| Tool | What It Does | When to Use |
|----------|-------------|-------------|
| `aft_inspect` | Codebase health snapshot — diagnostics, TODOs, dead code, unused exports | Before review — catch diagnostics automatically |
| `changed-files` | Lists session-changed files as a navigable tree with change indicators (+/~/-) | Before review — identify review scope |
| Language linters | `npx tsc --noEmit` (TS), `cargo check` (Rust), `mypy` (Python), `golangci-lint` (Go) | Before review — catch lint/type errors |
| Language formatters | `npx biome check` (TS), `cargo fmt` (Rust), `black` (Python), `go fmt` (Go) | After review — verify formatting |
| Test runners | `npx jest`, `cargo test`, `pytest`, `go test` | HIGH phase — verify changes don't break functionality |
| Coverage tools | Language-specific coverage reporters | Post-review — verify coverage requirements (≥80%) |

## Cross-Language Quality Rules

These quality rules apply across all languages during review:

- **Immutability first** — never mutate; always return new copies (spread, `Object.freeze`, immutable data structures)
- **File organization** — 200–400 lines typical, 800 max. Extract utilities from large components. Organize by feature, not by type.
- **No emojis in codebase** — comments and code should be professional text
- **No `console.log` / `print()` / `dump()` in production** — use proper logging frameworks
- **TODO/FIXME require tracking tickets** — every TODO needs a linked issue reference
- **Input validation on all external data** — use schema validation (Zod, Pydantic, etc.)
- **80% minimum test coverage** — 100% for auth, payments, and security-critical code
- **Descriptive naming** — no `x`, `tmp`, `data`; no magic numbers without named constants
- **Proper error handling** — no bare `catch`/`except`, no swallowed errors, context on re-throws

These checks supplement the language-specific checklists — apply them to every review regardless of language.

## Anti-Patterns

| Don't | Because |
|-------|---------|
| Review without loading the reference | Language-specific checks (N+1 in Eloquent, borrow-checker patterns in Rust) require the reference |
| Load all references at once | Context waste — each reference is a full checklist; load only the ones matching your diff |
| Apply one language's checks to another | Each language has distinct patterns and pitfalls |
| Skip diagnostic commands | Run the language-specific tooling (linters, type checkers, security scanners) before reporting |
| Skip security checks | Every reference prioritizes CRITICAL security checks first |

## Validation Checklist

Before completing a review, verify:

- [ ] Loaded the correct reference file(s) for every file extension in the diff
- [ ] Ran `aft_inspect` and language-specific linters before visual inspection
- [ ] Checked CRITICAL security items first, then HIGH, then MEDIUM, then LOW
- [ ] Applied cross-language quality rules (immutability, file size, emoji ban, console.log)
- [ ] All reported issues use the `[SEVERITY]` output format with file:line
- [ ] Approval verdict matches the criteria (Block if any CRITICAL/HIGH)
- [ ] Post-review verification pipeline completed (type check → lint → tests → build → coverage)

## Reference Files

- [`ts-js.md`](file:///home/opencode/.config/opencode/skills/review-code/references/ts-js.md) — TypeScript/JavaScript: security, type safety, React, bundle size, N+1, console.log, emoji, accessibility
- [`python.md`](file:///home/opencode/.config/opencode/skills/review-code/references/python.md) — Python: security, type hints, async, Pythonic patterns, framework checks (Django, FastAPI, Flask)
- [`rust.md`](file:///home/opencode/.config/opencode/skills/review-code/references/rust.md) — Rust: security, borrow checker, unsafe, ownership/lifetimes, concurrency
- [`go.md`](file:///home/opencode/.config/opencode/skills/review-code/references/go.md) — Go: security, error wrapping, goroutine leaks, nil pointers, interfaces, anti-patterns
- [`java.md`](file:///home/opencode/.config/opencode/skills/review-code/references/java.md) — Java: security, Spring Boot, JPA/database, concurrency, testing, Maven/Gradle
- [`php.md`](file:///home/opencode/.config/opencode/skills/review-code/references/php.md) — PHP: security, Eloquent N+1, type juggling, sessions, framework checks (Laravel, Livewire, Filament)
- [`kotlin.md`](file:///home/opencode/.config/opencode/skills/review-code/references/kotlin.md) — Kotlin: security, clean architecture, coroutines, Compose, Android lifecycle
- [`cpp.md`](file:///home/opencode/.config/opencode/skills/review-code/references/cpp.md) — C++: memory safety, security, concurrency, modern C++ patterns
- [`postgres.md`](file:///home/opencode/.config/opencode/skills/review-code/references/postgres.md) — PostgreSQL: RLS, indexes, seq scans, deadlocks, schema design, pagination
- [`general.md`](file:///home/opencode/.config/opencode/skills/review-code/references/general.md) — Fallback: language-agnostic review for any codebase
