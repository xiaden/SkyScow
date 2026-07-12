# Go Design Patterns

**Purpose:** Deep-dive on idiomatic Go design patterns beyond the overview in the SKILL.md. Use this reference when designing new Go services or reviewing Go architecture decisions.

## Struct Embedding for Composition

```go
type BaseServer struct {
    db     *sql.DB
    logger *slog.Logger
}

type OrderServer struct {
    BaseServer            // Methods promoted
    paymentClient *PaymentClient
}

// OrderServer gets BaseServer's methods automatically
```

Interface satisfaction is implicit — no `implements` keyword.

## Small Interfaces (1-3 Methods)

```go
// One method: perfect
type Reader interface {
    Read(p []byte) (n int, err error)
}

// Two methods: often right
type Closer interface {
    Close() error
}

// Three methods: consider if too broad
type ReadCloser interface {
    Reader
    Closer
}
```

Prefer accepting interfaces, returning structs.

## Error Handling

```go
// Always wrap errors with context
if err != nil {
    return fmt.Errorf("reading config %s: %w", path, err)
}

// Sentinel errors for expected cases
var ErrNotFound = errors.New("resource not found")
// Check with errors.Is, not ==
if errors.Is(err, ErrNotFound) { ... }
```

## Context Propagation

```go
func HandleRequest(ctx context.Context, w http.ResponseWriter, r *http.Request) {
    // Context is first parameter
    ctx, cancel := context.WithTimeout(ctx, 5*time.Second)
    defer cancel()

    result, err := processOrder(ctx, orderID)
    if errors.Is(err, context.DeadlineExceeded) {
        http.Error(w, "request timed out", http.StatusGatewayTimeout)
        return
    }
}
```

## Functional Options

```go
type ServerOption func(*Server)

func WithPort(port int) ServerOption {
    return func(s *Server) { s.port = port }
}

func WithTimeout(d time.Duration) ServerOption {
    return func(s *Server) { s.timeout = d }
}

func NewServer(opts ...ServerOption) *Server {
    s := &Server{port: 8080, timeout: 30 * time.Second} // defaults
    for _, opt := range opts {
        opt(s)
    }
    return s
}
```

## Goroutines + Channels

```go
// Fan-out pattern
func ProcessOrders(ctx context.Context, orders []Order) <-chan Result {
    results := make(chan Result, len(orders))
    for _, o := range orders {
        o := o // capture
        go func() {
            select {
            case results <- processOne(ctx, o):
            case <-ctx.Done():
            }
        }()
    }
    return results
}
```

## System Design Checklist for Go Services

- [ ] Package layout follows Go conventions (`internal/`, `cmd/`, `pkg/`)
- [ ] Interfaces defined by consumers, not producers
- [ ] `context.Context` is first parameter in all request-scoped functions
- [ ] No `init()` functions with complex logic
- [ ] All exported functions have doc comments
- [ ] Error wrapping used (not `return err` without context)
- [ ] Race detector passes (`go build -race`)
- [ ] Goroutines have cancellation paths
- [ ] `defer mu.Unlock()` pattern used consistently
- [ ] Table-driven tests cover main code paths

## Red Flags

| Pattern | Severity | What to Look For |
|---------|----------|------------------|
| Simulated inheritance | HIGH | Deep embedding hierarchies — use flat composition |
| Overly large interfaces (>5 methods) | MEDIUM | Split into smaller interfaces |
| Goroutine leaks | CRITICAL | Goroutines without cancellation or done channels |
| `init()` abuse | MEDIUM | Complex logic in init functions |
| `interface{}` instead of generics | MEDIUM | Use Go 1.18+ generics |
| Type assertions without `ok` | CRITICAL | `v := x.(string)` can panic — use `v, ok := x.(string)` |
