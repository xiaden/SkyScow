# Python Code Review

**Purpose:** Language-specific code review checklist for Python — security, type hints, Pythonic patterns, and framework-specific checks.
**Scope:** All `.py` files including modules, scripts, and tests.

## Verification Commands
```bash
mypy .                                     # Type checking
ruff check .                               # Fast linting
black --check .                            # Format check
bandit -r .                                # Security scan
pytest --cov --cov-report=term-missing     # Test coverage (or --cov=<PACKAGE>)
```

## [CRITICAL] Security
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

## ECC Tools

Prefer ECC tooling for automated checks before manual review:
- `lint-check` — detects `ruff`/`pylint` and returns command
- `format-code` — detects `black` and returns command
- `security-audit` — scans for secrets, eval abuse, and unsafe deserialization
- `run-tests` — detects `pytest` and runs test suite
