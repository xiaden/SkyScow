# Rust Design Patterns

**Purpose:** Deep-dive on idiomatic Rust design patterns beyond the overview in the SKILL.md. Use this reference when designing new Rust modules or reviewing Rust architecture decisions.

## Enum State Machines

Rust enums with data fields model state machines naturally:

```rust
enum ProtocolState {
    Disconnected,
    Connecting { attempt: u32, addr: SocketAddr },
    Connected { session: SessionId },
    Reconnecting { backoff: Duration },
}
```

Each variant can carry different data. Add methods with `impl`:

```rust
impl ProtocolState {
    fn is_active(&self) -> bool {
        matches!(self, ProtocolState::Connected { .. })
    }
}
```

Red flag: Using boolean flags (`is_connected: bool`) and match on them instead of encoding state in the enum type.

## Result/Option for Error Handling

Use idiomatic error types with `thiserror`:

```rust
#[derive(thiserror::Error, Debug)]
pub enum ConfigError {
    #[error("config file not found: {0}")]
    NotFound(PathBuf),
    #[error("parse error at {path}:{line}")]
    ParseError { path: PathBuf, line: usize, source: serde_json::Error },
}
```

For application code, use `anyhow::Result` for convenience; for libraries, always use custom error types.

## Traits + Generics for Polymorphism

Preference order for dispatch:
1. **Generics with trait bounds** (`fn process<T: Processor>(t: T)`) — static dispatch, zero cost
2. **`impl Trait`** (`fn process(t: impl Processor)`) — syntax sugar for generics
3. **Trait objects** (`Box<dyn Processor>`) — dynamic dispatch, necessary for heterogeneous collections

When to use trait objects:
- Collecting different types that implement the same trait into a `Vec<Box<dyn Trait>>`
- Reducing compile time by hiding implementations
- Plugin architectures where types are unknown at compile time

## Newtype Pattern

Zero-cost wrappers for type safety:

```rust
#[derive(Debug, Clone, Copy)]
pub struct UserId(u64);

#[derive(Debug, Clone, Copy)]
pub struct OrderId(u64);
```

Prevents passing `OrderId` where `UserId` is expected. Derive `Deref` if forwarding is needed; implement `From`/`Into` for conversions.

## Builder Pattern

```rust
#[derive(Default)]
pub struct QueryBuilder {
    table: Option<String>,
    filters: Vec<String>,
    limit: Option<usize>,
}

impl QueryBuilder {
    pub fn table(mut self, name: &str) -> Self { self.table = Some(name.to_string()); self }
    pub fn filter(mut self, expr: &str) -> Self { self.filters.push(expr.to_string()); self }
    pub fn limit(mut self, n: usize) -> Self { self.limit = Some(n); self }
    pub fn build(self) -> Result<Query, BuildError> {
        let table = self.table.ok_or(BuildError::MissingTable)?;
        Ok(Query { table, filters: self.filters, limit: self.limit })
    }
}
```

## RAII via Drop

```rust
struct ProfilerScope {
    name: &'static str,
    start: Instant,
}

impl ProfilerScope {
    fn new(name: &'static str) -> Self {
        println!("[PROFILE] starting: {}", name);
        ProfilerScope { name, start: Instant::now() }
    }
}

impl Drop for ProfilerScope {
    fn drop(&mut self) {
        let elapsed = self.start.elapsed();
        println!("[PROFILE] {} took {:?}", self.name, elapsed);
    }
}
```

## ADR Template for Rust Projects

```markdown
# ADR-NNN: [Title]

**Status:** Proposed | Accepted | Deprecated  
**Rust Version Target:** Edition 2021  
**Crate:** (which crate this affects)

## Context
Describe the problem and why it needs a decision.

## Decision
State the chosen approach with Rust-specific justification.

## Consequences
- Positive: ...
- Negative: ...
- Tradeoffs: ...

## Alternatives Considered
- Approach A: (why rejected)
- Approach B: (why rejected)
```

## Red Flags

| Pattern | Severity | What to Look For |
|---------|----------|------------------|
| `Rc<RefCell<T>>` proliferation | HIGH | Fighting borrow checker — rethink ownership model |
| Trait objects when generics suffice | MEDIUM | Lost performance, unnecessary `Box` allocations |
| `unwrap()` in production | CRITICAL | Every unwrap is a potential panic |
| `.clone()` everywhere | MEDIUM | Not understanding lifetimes — use references or `Cow` |
| Blocking in async context | CRITICAL | `std::thread::sleep`, `std::fs` calls in async functions |
