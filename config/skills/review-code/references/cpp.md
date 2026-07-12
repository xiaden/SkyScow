# C++ Code Review

**Purpose:** Language-specific code review checklist for C++ — memory safety, security, concurrency, code quality, performance, and modern C++ best practices.
**Scope:** All `.cpp`, `.hpp`, `.h`, `.cc`, `.cxx`, `.hh` files including library code, application code, and tests.

## Verification Commands

```bash
# Static analysis
clang-tidy --checks='*,-llvmlibc-*' src/*.cpp -- -std=c++17
cppcheck --enable=all --suppress=missingIncludeSystem src/

# Build
cmake --build build 2>&1 | head -50

# Sanitizers (if available)
cmake -DCMAKE_CXX_FLAGS="-fsanitize=address,undefined" build && cmake --build build
```

### Quick-Scan
```bash
grep -rn "new " src/ --include="*.cpp" --include="*.hpp"     # Raw new — should be make_unique/make_shared
grep -rn "delete " src/ --include="*.cpp" --include="*.hpp"  # Raw delete — missing RAII
grep -rn "malloc(" src/ --include="*.cpp" --include="*.hpp"  # C-style allocation
grep -rn "using namespace std" src/ --include="*.hpp"        # Namespace pollution in headers
grep -rn "reinterpret_cast" src/ --include="*.cpp" --include="*.hpp"  # Unsafe casts
```

## [CRITICAL] Memory Safety

- **Raw new/delete**: Use `std::unique_ptr` or `std::shared_ptr`
- **Buffer overflows**: C-style arrays, `strcpy`, `sprintf` without bounds
- **Use-after-free**: Dangling pointers, invalidated iterators
- **Uninitialized variables**: Reading before assignment
- **Memory leaks**: Missing RAII, resources not tied to object lifetime
- **Null dereference**: Pointer access without null check

## [CRITICAL] Security

- **Command injection**: Unvalidated input in `system()` or `popen()`
- **Format string attacks**: User input in `printf` format string
- **Integer overflow**: Unchecked arithmetic on untrusted input
- **Hardcoded secrets**: API keys, passwords in source
- **Unsafe casts**: `reinterpret_cast` without justification

## [HIGH] Concurrency

- **Data races**: Shared mutable state without synchronization
- **Deadlocks**: Multiple mutexes locked in inconsistent order
- **Missing lock guards**: Manual `lock()`/`unlock()` instead of `std::lock_guard`
- **Detached threads**: `std::thread` without `join()` or `detach()`

## [HIGH] Code Quality

- **No RAII**: Manual resource management
- **Rule of Five violations**: Incomplete special member functions
- **Large functions**: Over 50 lines
- **Deep nesting**: More than 4 levels
- **C-style code**: `malloc`, C arrays, `typedef` instead of `using`

## [MEDIUM] Performance

- **Unnecessary copies**: Pass large objects by value instead of `const&`. **Impact: 2-10x overhead per call for large objects.**
- **Missing move semantics**: Not using `std::move` for sink parameters
- **String concatenation in loops**: Use `std::ostringstream` or `reserve()`
- **Missing `reserve()`**: Known-size vector without pre-allocation

## [MEDIUM] Best Practices

- **`const` correctness**: Missing `const` on methods, parameters, references
- **`auto` overuse/underuse**: Balance readability with type deduction
- **Include hygiene**: Missing include guards, unnecessary includes
- **Namespace pollution**: `using namespace std;` in headers

## Anti-Patterns

| Pattern | Severity | What to Look For |
|---------|----------|------------------|
| Raw `new`/`delete` | CRITICAL | Manual memory management — use `std::unique_ptr`/`std::make_unique` |
| `malloc`/`free` in C++ | HIGH | C-style allocation — use `new` or smart pointers |
| No RAII | CRITICAL | Resources not tied to object lifetime — use destructors |
| Rule of Five violation | HIGH | Missing copy/move/destructor — implement or `= default`/`= delete` |
| `using namespace std` in header | MEDIUM | Namespace pollution — fully qualify or use in `.cpp` only |
| `reinterpret_cast` without comment | CRITICAL | UB risk — add justification comment |
| `printf` with user input | CRITICAL | Format string attack — use `std::cout` or `fmt::print` |
| Manual `lock()`/`unlock()` | HIGH | Exception-unsafe — use `std::lock_guard` or `std::scoped_lock` |
| Pass-by-value for large objects | MEDIUM | Unnecessary copies — use `const&` |
| C-style arrays | HIGH | Buffer overflow risk — use `std::array` or `std::vector` |

## Review Output Format

For each issue:
```text
[CRITICAL] Raw pointer ownership
File: src/engine/renderer.cpp:142
Issue: `Texture* t = new Texture(path);` — raw new without RAII wrapper, potential leak on early return
Fix: Use `auto t = std::make_unique<Texture>(path);`
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
- **Warning**: MEDIUM issues only
- **Block**: CRITICAL or HIGH issues found

## ECC Tools

Prefer ECC tooling for automated checks before manual review:
- `lint-check` — detects linter (clang-tidy) and returns command
- `security-audit` — scans for secrets and code security anti-patterns
- `format-code` — detects formatter (clang-format) and returns command

For detailed C++ coding standards and anti-patterns, see `skill: cpp-coding-standards`.
