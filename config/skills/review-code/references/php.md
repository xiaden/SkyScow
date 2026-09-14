# PHP Code Review

**Purpose:** Language-specific code review checklist for PHP — security, error handling, PHP standards, Eloquent/Laravel patterns, and framework-specific checks.
**Scope:** All `.php` files including controllers, models, services, middleware, and tests. Covers Laravel, Livewire, Filament, and plain PHP.

## Verification Commands

Run the repository's own commands for the changed surface; do not default to a toolchain the repository does not have. Select the evidence from the surface-to-evidence table in `/home/opencode/.config/opencode/instructions/validation-mandate.md`:
- Run the repository's own type-check / static-analysis command, when defined
- Run the repository's own lint command, when defined
- Run the repository's own formatter check, when defined
- Run the repository's own test command for the changed surface, when defined

Omit any check the repository does not define and report it as unavailable rather than inventing a command. Report gate evidence using the labels in `/home/opencode/.config/opencode/skills/ci-lint-test-gates/SKILL.md`.

### Quick-Scan
```bash
grep -rn "dd(" app/ --include="*.php"       # Debug statements left in code
grep -rn "dump(" app/ --include="*.php"     # Debug statements left in code
grep -rn '->create($request->all()' app/ --include="*.php"  # Mass assignment
grep -rn "DB::raw" app/ --include="*.php"   # Raw queries — verify parameterized
grep -rn 'catch (\\Exception' app/ --include="*.php"  # Swallowed exceptions
```

## [CRITICAL] Security

Apply these checks when the changed surface is observably security-sensitive; the applicability owner is `/home/opencode/.config/opencode/skills/security-review/SKILL.md`. Non-security changes preserve existing security invariants under ordinary correctness review; any CRITICAL or HIGH issue found, by any path, still blocks merge.

- **SQL Injection**: raw string interpolation in queries — use Eloquent or parameterized queries
- **Mass Assignment**: `$guarded = []` or calling `create($request->all())` — whitelist `$fillable`
- **Command Injection**: `shell_exec()`, `exec()`, `system()` with unvalidated input
- **Path Traversal**: user-controlled paths in `Storage` or file functions — validate and sanitize
- **eval/assert abuse**, `unserialize()` on untrusted data, **hardcoded secrets**
- **Weak crypto**: MD5 for passwords, self-implemented encryption
- **XSS**: `{!! $userInput !!}` in Blade without purification — use `{{ }}` or `HTMLPurifier`

## [CRITICAL] Error Handling

- **Bare try/catch**: `catch (\Exception $e) {}` — log and handle, never silently swallow
- **Missing validation**: controller actions without FormRequest or validation rules
- **Unvalidated file uploads**: missing MIME type, size, or extension checks

## [HIGH] PHP Standards

- Missing `declare(strict_types=1)` in non-views
- Public methods without type hints for parameters and return types
- Using `mixed` when a specific union type is possible
- Missing `readonly` on constructor-promoted properties that are never reassigned
- Missing `final` on classes not designed for inheritance

## [HIGH] Eloquent / Laravel Patterns

- **N+1 queries**: missing `with()` for relationships in loops or serialization. **Impact: 10-100x slower on related models.**
- Missing `$fillable` or `$casts` on models
- Business logic in controllers: should be in Actions/Services
- Direct `$request->all()` without validation: use FormRequest with `$request->validated()`
- `DB::raw()` or `whereRaw()` with user input: use parameterized bindings

## [HIGH] Code Quality

- Functions > 50 lines, methods > 5 parameters (use DTO or Value Object)
- Deep nesting (> 4 levels) — extract early returns or guard clauses
- Duplicate code patterns — extract to service or trait
- Magic numbers without named constants or enums

## [MEDIUM] Best Practices

- PSR-12: import order, spacing, brace placement, naming conventions
- Missing docblocks on complex public methods
- `dd()`/`dump()`/`var_dump()` left in committed code
- Unused or overly broad `use` imports — import only what you need, keep them clean
- `count($collection)` vs `$collection->isEmpty()` — prefer `isEmpty()` for intent-revealing checks; use `count()` only when a numeric count is actually needed
- Shadowing builtins (`$collection`, `$request`, `$model` in narrow closures)

## Framework Checks

### Laravel
- N+1 via `with()`/`load()`, `$fillable`/`$casts`, FormRequest validation, route model binding, `Gate`/`Policy` authorization, Sanctum token abilities, queue idempotency

### Livewire
- Proper `#[Rule]` attributes, authorization in `authorize()`, wire:model security

### Filament
- Form/table authorization, `canAccess()`, policy registration

### Plain PHP
- PDO prepared statements, password_hash/password_verify, header-based CSRF

## Anti-Patterns

| Pattern | Severity | What to Look For |
|---------|----------|------------------|
| `$guarded = []` | CRITICAL | Open mass assignment — whitelist `$fillable` |
| `create($request->all())` | CRITICAL | Unvalidated mass assignment — use `$request->validated()` |
| `{!! $var !!}` without purification | CRITICAL | XSS vector — use `{{ }}` or `HTMLPurifier` |
| Missing `with()` in loops | HIGH | N+1 queries — add eager loading |
| `catch (\Exception $e) {}` | CRITICAL | Swallowed exception — log and handle |
| `dd()`/`dump()` committed | MEDIUM | Debug code in production |
| `DB::raw()` with user input | CRITICAL | SQL injection — use parameterized bindings |
| `shell_exec()` with input | CRITICAL | Command injection — validate and sanitize |
| Missing `strict_types` | HIGH | Type coercion bugs — add `declare(strict_types=1)` |
| Missing `final` on non-inheritance classes | HIGH | Unintended extension — add `final` |

## Review Output Format

```text
[SEVERITY] Issue title
File: path/to/file.php:42
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

- **Approve**: The repository-defined automated checks pass (when such checks are defined) AND no CRITICAL or HIGH issues
- **Warning**: The repository-defined automated checks pass and MEDIUM issues only (can merge with caution)
- **Block**: Any repository-defined automated check fails OR CRITICAL/HIGH issues found

## Repository Commands

Discover and run the repository's own commands before manual review — do not assume ECC or any specific toolchain is present:
- Lint — run the repository's own lint command for the changed files, when defined
- Format — run the repository's own formatter command for the changed files, when defined
- Tests — run the repository's own test command for the changed surface, when defined
- Coverage — verify against the repository-defined coverage gate when one exists; impose no universal threshold (see `/home/opencode/.config/opencode/instructions/validation-mandate.md`)
- Security — for observably security-sensitive surfaces, run the security review (canonical owner: `/home/opencode/.config/opencode/skills/security-review/SKILL.md`); non-security changes preserve existing security invariants under ordinary correctness review

Omit and report any command the repository does not define.

For detailed PHP patterns, security examples, and code samples, see skills: `laravel-patterns`, `laravel-security`, `laravel-tdd`.
