# Go Code Review

**Purpose:** Language-specific code review checklist for Go — security, error handling, concurrency, and idiomatic Go patterns.
**Scope:** All `.go` files including library packages, main packages, and tests.

## Verification Commands
```bash
# Static analysis
go vet ./...
staticcheck ./...
golangci-lint run

# Race detection
go build -race ./...
go test -race ./...

# Security scanning
govulncheck ./...
```

## [CRITICAL] Security

### SQL Injection
```go
// Bad
db.Query("SELECT * FROM users WHERE id = " + userID)
// Good
db.Query("SELECT * FROM users WHERE id = $1", userID)
```

### Command Injection
```go
// Bad
exec.Command("sh", "-c", "echo " + userInput)
// Good
exec.Command("echo", userInput)
```

### Path Traversal
```go
// Bad
os.ReadFile(filepath.Join(baseDir, userPath))
// Good
cleanPath := filepath.Clean(userPath)
if strings.HasPrefix(cleanPath, "..") {
    return ErrInvalidPath
}
```

### Other Security Checks
- **Race Conditions**: Shared state without synchronization
- **Unsafe Package**: Use of `unsafe` without justification
- **Hardcoded Secrets**: API keys, passwords in source
- **Insecure TLS**: `InsecureSkipVerify: true`
- **Weak Crypto**: Use of MD5/SHA1 for security purposes

## [CRITICAL] Error Handling

### Ignored Errors
```go
// Bad
result, _ := doSomething()
// Good
result, err := doSomething()
if err != nil {
    return fmt.Errorf("do something: %w", err)
}
```

### Missing Error Wrapping
```go
// Bad
return err
// Good
return fmt.Errorf("load config %s: %w", path, err)
```

### Panic Instead of Error
- Using `panic` for recoverable errors

### errors.Is/As
```go
// Bad
if err == sql.ErrNoRows
// Good
if errors.Is(err, sql.ErrNoRows)
```

## [HIGH] Concurrency

### Goroutine Leaks
**Impact: memory exhaustion over time — unbounded goroutines never terminate.**

```go
// Bad: No way to stop goroutine
go func() {
    for { doWork() }
}()
// Good: Context for cancellation
go func() {
    for {
        select {
        case <-ctx.Done():
            return
        default:
            doWork()
        }
    }
}()
```

### Other Concurrency Checks
- **Race Conditions**: Run `go build -race ./...`
- **Unbuffered Channel Deadlock**: Sending without receiver
- **Missing sync.WaitGroup**: Goroutines without coordination
- **Context Not Propagated**: Ignoring context in nested calls
- **Mutex Misuse**: Not using `defer mu.Unlock()`

### Mutex Misuse
```go
// Bad: Unlock might not be called on panic
mu.Lock()
doSomething()
mu.Unlock()
// Good
mu.Lock()
defer mu.Unlock()
doSomething()
```

## [HIGH] Code Quality
- **Large Functions**: Functions over 50 lines
- **Deep Nesting**: More than 4 levels of indentation
- **Interface Pollution**: Defining interfaces not used for abstraction
- **Package-Level Variables**: Mutable global state
- **Naked Returns**: In functions longer than a few lines

### Non-Idiomatic Code
```go
// Bad
if err != nil {
    return err
} else {
    doSomething()
}
// Good: Early return
if err != nil {
    return err
}
doSomething()
```

## [MEDIUM] Performance

### Inefficient String Building
```go
// Bad
for _, s := range parts { result += s }
// Good
var sb strings.Builder
for _, s := range parts { sb.WriteString(s) }
```

### Other Performance Checks
- **Slice Pre-allocation**: Not using `make([]T, 0, cap)`
- **Pointer vs Value Receivers**: Inconsistent usage
- **Unnecessary Allocations**: Creating objects in hot paths
- **N+1 Queries**: Database queries in loops. **Impact: 10-100x slower on large datasets.**
- **Missing Connection Pooling**: Creating new DB connections per request. **Impact: connection exhaustion under load.**
- **Missing Connection Pooling**: Creating new DB connections per request

## [MEDIUM] Best Practices

### Context First
```go
// Bad
func Process(id string, ctx context.Context)
// Good
func Process(ctx context.Context, id string)
```

### Other Best Practices
- **Accept Interfaces, Return Structs**: Functions should accept interface parameters
- **Table-Driven Tests**: Tests should use table-driven pattern
- **Godoc Comments**: Exported functions need documentation
- **Error Messages**: Should be lowercase, no punctuation

```go
// Bad
return errors.New("Failed to process data.")
// Good
return errors.New("failed to process data")
```

- **Package Naming**: Short, lowercase, no underscores

## Anti-Patterns

| Pattern | Severity | What to Look For |
|---------|----------|------------------|
| `init()` Abuse | HIGH | Complex logic in init functions |
| Empty Interface Overuse | MEDIUM | Using `interface{}` instead of generics |
| Type Assertions Without ok | CRITICAL | `v := x.(string)` can panic |
| Deferred Call in Loop | HIGH | Resource accumulation |
| Silent Error Ignore | CRITICAL | `result, _ := doSomething()` |

### Type Assertions Without ok
```go
// Bad
v := x.(string)
// Good
v, ok := x.(string)
if !ok { return ErrInvalidType }
```

### Deferred Call in Loop
```go
// Bad: Files opened until function returns
for _, path := range paths {
    f, _ := os.Open(path)
    defer f.Close()
}
// Good: Close in loop iteration
for _, path := range paths {
    func() {
        f, _ := os.Open(path)
        defer f.Close()
        process(f)
    }()
}
```

## Review Output Format

For each issue:
```text
[CRITICAL] SQL Injection vulnerability
File: internal/repository/user.go:42
Issue: User input directly concatenated into SQL query
Fix: Use parameterized query

query := "SELECT * FROM users WHERE id = " + userID  // Bad
query := "SELECT * FROM users WHERE id = $1"         // Good
db.Query(query, userID)
```

## Approval Criteria
- **Approve**: No CRITICAL or HIGH issues
- **Warning**: MEDIUM issues only (can merge with caution)
- **Block**: CRITICAL or HIGH issues found

### Quick-Scan
```bash
grep -rn 'defer ' --include="*.go" | grep "for "       # Deferred call in loop
grep -rn ',_ :=' --include="*.go"                       # Ignored errors
grep -rn '\.Unlock()' --include="*.go" | grep -v defer   # Unlock without defer
grep -rn 'interface{}' --include="*.go"                  # Empty interface overuse
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
- `lint-check` — detects `golangci-lint` and returns command
- `security-audit` — scans for secrets and dependency vulnerabilities
- `run-tests` — detects Go test runner and runs suite
