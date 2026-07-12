# Rust Code Review

**Purpose:** Language-specific code review checklist for Rust — safety, idiomatic patterns, ownership/lifetimes, concurrency, and error handling.
**Scope:** All `.rs` files including library crates, binary crates, and tests.

## Verification Commands
- `cargo check` — type and borrow checker errors
- `cargo clippy -- -D warnings` — lint with deny
- `cargo fmt --check` — formatting check
- `cargo test` — all tests pass

## [CRITICAL] Security

### SQL Injection
```rust
// Bad
format!("SELECT * FROM users WHERE id = {}", user_id)
// Good: use parameterized queries via sqlx, diesel, etc.
sqlx::query("SELECT * FROM users WHERE id = $1").bind(user_id)
```

### Command Injection
```rust
// Bad
Command::new("sh").arg("-c").arg(format!("echo {}", user_input))
// Good
Command::new("echo").arg(user_input)
```

### Unsafe without justification
- Missing `// SAFETY:` comment on every unsafe block
- Use-after-free via raw pointers

### Hardcoded Secrets
- API keys, passwords, tokens in source code

## [CRITICAL] Error Handling
- **Silenced errors**: `let _ = result;` on `#[must_use]` types
- **Missing error context**: `return Err(e)` without `.context()` or `.map_err()`
- **Panic in production**: `panic!()`, `todo!()`, `unreachable!()` in production paths
- **`Box<dyn Error>` in libraries**: Use `thiserror` for typed errors

## [HIGH] Ownership and Lifetimes
- **Unnecessary cloning**: `.clone()` to satisfy borrow checker without understanding root cause. **Impact: 2-10x memory and CPU overhead for large structures.**
- **String instead of &str**: Taking `String` when `&str` suffices
- **Vec instead of slice**: Taking `Vec<T>` when `&[T]` suffices

## [HIGH] Concurrency
- **Blocking in async**: `std::thread::sleep`, `std::fs` in async context. **Impact: stalls the entire async runtime — all concurrent tasks block.**
- **Unbounded channels**: `mpsc::channel()`/`tokio::sync::mpsc::unbounded_channel()` need justification — prefer bounded channels
- **`Mutex` poisoning ignored**: Not handling `PoisonError`
- **Missing `Send`/`Sync` bounds**: Types shared across threads

## [HIGH] Code Quality
- Large functions: Over 50 lines
- Wildcard match on business enums: `_ =>` hiding new variants
- Dead code: Unused functions, imports, variables

## Anti-Patterns

| Pattern | Severity | What to Look For |
|---------|----------|------------------|
| `Rc<RefCell<T>>` to fight borrow checker | HIGH | Reconsider ownership model |
| Trait objects when generics suffice | MEDIUM | Lost performance, unnecessary Box allocations |
| `unwrap()` in production | CRITICAL | Every unwrap is a potential panic |
| `.clone()` everywhere | MEDIUM | Not understanding lifetimes — use references or Cow |
| Blocking in async context | CRITICAL | `std::thread::sleep`, `std::fs` in async functions |

## Review Output Format

For each issue:
```
[SEVERITY] Issue title
File: path/to/file:line
Issue: Description
Fix: Suggested code change
```

## Approval Criteria
- **Approve**: No CRITICAL or HIGH issues
- **Warning**: MEDIUM issues only
- **Block**: CRITICAL or HIGH issues found

### Quick-Scan
```bash
grep -rn "unwrap()" src/ --include="*.rs"               # Potential panics in production
grep -rn "\.clone()" src/ --include="*.rs"               # Unnecessary cloning
grep -rn 'let _ =' src/ --include="*.rs"                 # Silenced #[must_use] errors
grep -rn "unsafe {" src/ --include="*.rs"                 # Unsafe blocks — verify SAFETY comments
grep -rn "std::thread::sleep" src/ --include="*.rs"     # Blocking in async context
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
- `lint-check` — detects clippy/cargo-check and returns command
- `format-code` — detects `rustfmt` and returns command
- `security-audit` — scans for secrets and unsafe code patterns
- `run-tests` — detects `cargo test` and runs test suite
