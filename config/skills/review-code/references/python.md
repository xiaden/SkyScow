# Python Code Review

**Purpose:** Language-specific code review checklist for Python — security, type hints, Pythonic patterns, and framework-specific checks.
**Scope:** All `.py` files including modules, scripts, and tests.

## Verification Commands

Run the repository's own commands for the changed surface; do not default to a toolchain the repository does not have. Select the evidence from the surface-to-evidence table in `config/instructions/validation-mandate.md`:
- Run the repository's own type-check / static-analysis command, when defined
- Run the repository's own lint command, when defined
- Run the repository's own formatter check, when defined
- Run the repository's own test command for the changed surface, when defined

Omit any check the repository does not define and report it as unavailable rather than inventing a command. Report gate evidence using the labels in `config/skills/ci-lint-test-gates/SKILL.md`.

## [CRITICAL] Security

Apply these checks when the changed surface is observably security-sensitive; the applicability owner is `config/skills/security-review/SKILL.md`. Non-security changes preserve existing security invariants under ordinary correctness review; any CRITICAL or HIGH issue found, by any path, still blocks merge.

- **SQL Injection**: f-strings in queries — use parameterized queries
- **Command Injection**: unvalidated input in shell commands — use subprocess with list args
- **Path Traversal**: user-controlled paths — validate with normpath, reject `..`
- **Eval/exec abuse**: Never use `eval()` or `exec()` on untrusted input
- **Unsafe deserialization**: pickle, yaml unsafe load — use safe alternatives
- **Hardcoded secrets**: API keys, passwords, tokens in source
- **Weak crypto**: MD5/SHA1 for security purposes
- **YAML unsafe load**: Use `yaml.safe_load()` not `yaml.load()`

## [CRITICAL] Error Handling
- **Bare except**: `except: pass` — catch specific exceptions
- **Swallowed exceptions**: silent failures — log and handle
- **Missing context managers**: manual file/resource management — use `with`

## [HIGH] Type Hints
- Public functions without type annotations
- Using `Any` when specific types are possible
- Missing `Optional` for nullable parameters

## [HIGH] Pythonic Patterns
- Use list comprehensions over C-style loops
- Use `isinstance()` not `type() ==`
- Use `Enum` not magic numbers
- Use `"".join()` not string concatenation in loops. **Impact: O(n²) with `+=` vs O(n) with `join`.**
- **Mutable default arguments**: `def f(x=[])` — use `def f(x=None)`

## [HIGH] Code Quality
- Functions > 50 lines, > 5 parameters (use dataclass)
- Deep nesting (> 4 levels)
- Duplicate code patterns
- Magic numbers without named constants

## [HIGH] Concurrency
- Shared state without locks — use `threading.Lock`
- Mixing sync/async incorrectly
- N+1 queries in loops — batch query. **Impact: 10-100x slower on large datasets.**

## [MEDIUM] Best Practices
- PEP 8: import order, naming, spacing
- Missing docstrings on public functions
- `print()` instead of `logging`
- `from module import *` — namespace pollution
- `value == None` — use `value is None`
- Shadowing builtins (`list`, `dict`, `str`)

## Framework Checks

### Django
- `select_related`/`prefetch_related` for N+1
- `atomic()` for multi-step operations
- Migration safety

### FastAPI
- CORS configuration
- Pydantic validation
- Response models
- No blocking in async

### Flask
- Proper error handlers
- CSRF protection

## Anti-Patterns

| Pattern | Severity | What to Look For |
|---------|----------|------------------|
| Mutable default arguments | CRITICAL | `def f(x=[])` — use `def f(x=None)` |
| `except: pass` | CRITICAL | Bare except without logging |
| Mixed sync/async | HIGH | Calling sync functions from async |
| `from module import *` | MEDIUM | Namespace pollution |
| `value == None` | MEDIUM | Use `value is None` |
| Shadowing builtins | MEDIUM | `list`, `dict`, `str` as variable names |
| `eval()`/`exec()` on user input | CRITICAL | Code injection vulnerability |
| `yaml.load()` without SafeLoader | CRITICAL | Arbitrary code execution |

## Review Output Format

```text
[SEVERITY] Issue title
File: path/to/file.py:42
Issue: Description
Fix: What to change
```

## Approval Criteria
- **Approve**: No CRITICAL or HIGH issues
- **Warning**: MEDIUM issues only (can merge with caution)
- **Block**: CRITICAL or HIGH issues found

### Quick-Scan
```bash
grep -rn "except:" --include="*.py"                     # Bare except
grep -rn "except Exception:" --include="*.py" | grep "pass"  # Swallowed exception
grep -rn "eval(" --include="*.py"                        # eval() usage
grep -rn "yaml.load(" --include="*.py"                   # Unsafe YAML loading
grep -rn "from .* import \*" --include="*.py"            # Star imports
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

Discover and run the repository's own commands before manual review — do not assume ECC or any specific toolchain is present:
- Lint — run the repository's own lint command for the changed files, when defined
- Format — run the repository's own formatter command for the changed files, when defined
- Tests — run the repository's own test command for the changed surface, when defined
- Coverage — verify against the repository-defined coverage gate when one exists; impose no universal threshold (see `config/instructions/validation-mandate.md`)
- Security — for observably security-sensitive surfaces, run the security review (canonical owner: `config/skills/security-review/SKILL.md`); non-security changes preserve existing security invariants under ordinary correctness review

Omit and report any command the repository does not define.
