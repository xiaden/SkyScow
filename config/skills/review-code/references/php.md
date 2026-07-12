# PHP Code Review

**Purpose:** Language-specific code review checklist for PHP — security, error handling, PHP standards, Eloquent/Laravel patterns, and framework-specific checks.
**Scope:** All `.php` files including controllers, models, services, middleware, and tests. Covers Laravel, Livewire, Filament, and plain PHP.

## Verification Commands

```bash
./vendor/bin/phpstan analyse --level max   # Type safety and errors
./vendor/bin/psalm --show-info=true        # Static analysis
./vendor/bin/pint --test                   # PSR-12 formatting
./vendor/bin/phpunit --coverage-text       # Test coverage
composer audit                             # Dependency vulnerabilities
```

### Quick-Scan
```bash
grep -rn "dd(" app/ --include="*.php"       # Debug statements left in code
grep -rn "dump(" app/ --include="*.php"     # Debug statements left in code
grep -rn '->create($request->all()' app/ --include="*.php"  # Mass assignment
grep -rn "DB::raw" app/ --include="*.php"   # Raw queries — verify parameterized
grep -rn 'catch (\\Exception' app/ --include="*.php"  # Swallowed exceptions
```

## [CRITICAL] Security

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

- **Approve**: All automated checks pass (PHPStan, Psalm, PHPUnit, Pint) AND no CRITICAL or HIGH issues
- **Warning**: All automated checks pass and MEDIUM issues only (can merge with caution)
- **Block**: Any automated check fails OR CRITICAL/HIGH issues found

## ECC Tools

Prefer ECC tooling for automated checks before manual review:
- `lint-check` — detects linter (PHPStan, Psalm) and returns command
- `format-code` — detects formatter (Pint) and returns command
- `security-audit` — scans for secrets and dependency vulnerabilities
- `run-tests` — detects framework and runs PHPUnit

For detailed PHP patterns, security examples, and code samples, see skills: `laravel-patterns`, `laravel-security`, `laravel-tdd`.
