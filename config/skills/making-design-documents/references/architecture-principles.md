# Architecture Principles & Trade-off Analysis

**Purpose:** Universal architectural principles, trade-off analysis methodology, cross-language patterns, and system design checklist for feature design. Load this when evaluating architecture decisions, comparing approaches, or completing a system design review.

## Contents

- [Architectural Principles](#architectural-principles)
- [Trade-off Analysis](#trade-off-analysis)
- [Common Cross-Language Patterns](#common-cross-language-patterns)
- [System Design Checklist](#system-design-checklist)
- [Architectural Anti-Patterns](#architectural-anti-patterns)

---

## Architectural Principles

Five principles that guide every design decision. Evaluate your design against each one.

### 1. Modularity & Separation of Concerns

- Single Responsibility Principle — each component does one thing well
- High cohesion, low coupling — related code lives together; unrelated code stays apart
- Clear interfaces between components — contracts, not implementation details
- Independent deployability — modules should be testable and deployable in isolation

**Red flag:** A module that needs 5+ imports from unrelated parts of the codebase to function.

### 2. Scalability

- Horizontal scaling capability — can you add more instances?
- Stateless design where possible — state lives in databases, caches, or message queues
- Efficient database queries — index on query patterns, not just primary keys
- Caching strategies — identify hot paths that benefit from caching
- Load balancing considerations — design for multiple instances from day one

**Red flag:** State stored in memory that would be lost on restart or won't sync across instances.

### 3. Maintainability

- Clear code organization — a new developer should find things by following names
- Consistent patterns — don't solve the same problem three different ways
- Comprehensive documentation — ADRs for decisions, docstrings for public APIs
- Easy to test — dependencies are injectable, side effects are isolated
- Simple to understand — the simplest solution that meets requirements

**Red flag:** The answer to "why is it done this way?" is "we've always done it that way."

### 4. Security

- Defense in depth — validate at every layer, not just the perimeter
- Principle of least privilege — components get exactly the permissions they need
- Input validation at boundaries — API gates, not internal calls
- Secure by default — opt-in to unsafe behavior, not opt-out of safe defaults
- Audit trail — log who did what when, especially for state-changing operations

**Red flag:** "We'll add security later" — retrofitting security is exponentially harder.

### 5. Performance

- Efficient algorithms — O(n²) on a hot path is a design bug, not an optimization target
- Minimal network requests — batch, cache, or eliminate round trips
- Optimized database queries — understand the query plan before deploying
- Appropriate caching — cache invalidation is one of the two hard problems
- Lazy loading — don't fetch what you don't need yet

**Red flag:** Premature optimization — optimizing before measuring. Profile first.

---

## Trade-off Analysis

For every significant design decision, document the trade-offs explicitly. This forces clarity and creates a record for future maintainers.

### The Four-Part Format

For each design decision, document:

1. **Pros** — benefits and advantages of the chosen approach
2. **Cons** — drawbacks and limitations you're accepting
3. **Alternatives considered** — other options evaluated, with reasons for rejection
4. **Decision** — final choice and the rationale that tipped the scales

### Example

```markdown
## Decision: Database per Service vs. Shared Database

### Pros (Database per Service)
- Independent scaling per service
- No schema coupling between teams
- Each service chooses optimal DB type

### Cons
- Cross-service queries require API calls or events
- Eventual consistency challenges
- Operational overhead of managing multiple databases

### Alternatives Considered
- **Shared database**: Simpler queries, but creates tight coupling and scaling bottlenecks
- **CQRS with shared DB**: Splits read/write but doesn't solve coupling

### Decision
Database per service. The team has experience with event-driven architectures and the
operational overhead is acceptable given our need for independent service scaling.
```

### When to Use Trade-off Analysis

- Choosing between two or more architectural approaches
- Making a decision that constrains future options
- Adopting a new pattern or technology
- Any choice where reasonable people could disagree

Trade-off analyses often become ADRs. When the decision is significant enough to document for posterity, use the ADR workflow.

---

## Common Cross-Language Patterns

These patterns transcend language ecosystems. Combine them with the language-specific patterns in `rust-design.md`, `go-design.md`, `python-design.md`, and `typescript-design.md`.

### Frontend Patterns

| Pattern | Description | When to Use |
|---------|-------------|-------------|
| **Component Composition** | Build complex UI from simple, focused components | Always — composability is the default |
| **Container/Presenter** | Separate data fetching logic from presentation | When a component has both data dependencies and rendering complexity |
| **Custom Hooks / Composables** | Reusable stateful logic extracted from components | When the same state pattern appears in 3+ components |
| **Context / Provide-Inject** | Avoid prop drilling through intermediate components | When 3+ levels of components pass the same data without using it |
| **Code Splitting** | Lazy-load routes and heavy dependencies | When bundle size impacts initial load time |

### Backend Patterns

| Pattern | Description | When to Use |
|---------|-------------|-------------|
| **Repository Pattern** | Abstract data access behind an interface | When you need to swap storage backends or test without a real database |
| **Service Layer** | Business logic lives in services, not controllers | Always — controllers handle HTTP, services handle logic |
| **Middleware / Interceptor** | Cross-cutting request/response processing | Auth, logging, rate limiting, CORS — anything every endpoint needs |
| **Event-Driven Architecture** | Services communicate via events, not direct calls | When services need to react to changes in other services without coupling |
| **CQRS** | Separate read models from write models | When read and write patterns differ significantly (e.g., complex queries vs. simple writes) |

### Data Patterns

| Pattern | Description | When to Use |
|---------|-------------|-------------|
| **Normalized Database** | Reduce redundancy through table relationships | Default for transactional (OLTP) workloads |
| **Denormalized for Reads** | Duplicate data to optimize query performance | When read latency is critical and write volume is moderate |
| **Event Sourcing** | Store state changes as an append-only event log | When you need full audit trail or temporal queries |
| **Caching Layers** | Redis, CDN, in-memory caches at strategic points | When the same data is read frequently with infrequent updates |
| **Eventual Consistency** | Accept temporary inconsistency for availability | Distributed systems where strong consistency would block operations |

---

## System Design Checklist

Run through this checklist when designing a new feature or system. Not every item applies to every design, but each skipped item should be a conscious decision.

### Functional Requirements

- [ ] User stories documented — what does the user need to accomplish?
- [ ] API contracts defined — request/response shapes, error formats, auth requirements
- [ ] Data models specified — entities, relationships, constraints
- [ ] UI/UX flows mapped — happy path, empty states, error states, loading states
- [ ] Edge cases identified — null/empty inputs, boundary values, concurrent access

### Non-Functional Requirements (NFRs)

- [ ] **Performance targets** — latency p50/p99, throughput (requests/second), response time budgets
- [ ] **Scalability requirements** — expected growth, horizontal vs. vertical scaling strategy
- [ ] **Security requirements** — auth model, data classification, compliance needs (GDPR, SOC2, HIPAA)
- [ ] **Availability targets** — uptime percentage (99.9%? 99.99%?), SLA definitions
- [ ] **Reliability** — error budgets, retry strategies, circuit breakers, graceful degradation

### Technical Design

- [ ] Architecture diagram created — boxes and arrows, even a napkin sketch counts
- [ ] Component responsibilities defined — each component has clear ownership
- [ ] Data flow documented — how data moves between components and across boundaries
- [ ] Integration points identified — external services, third-party APIs, internal dependencies
- [ ] Error handling strategy defined — what fails, how it fails, what the user sees
- [ ] Testing strategy planned — unit, integration, E2E coverage targets per component

### Operations

- [ ] Deployment strategy defined — how does this reach production? Feature flags? Canary?
- [ ] Monitoring and alerting planned — what metrics matter? What thresholds trigger alerts?
- [ ] Backup and recovery strategy — what data needs backing up? How is it restored?
- [ ] Rollback plan documented — can this change be reverted cleanly?
- [ ] Migration plan for existing data — schema changes, data backfills, breaking changes

---

## Architectural Anti-Patterns

These are design-level red flags that transcend any single language. The language-specific references (`rust-design.md`, `go-design.md`, etc.) cover language-level red flags; these are the architectural ones.

| Anti-Pattern | Severity | What to Look For |
|--------------|----------|------------------|
| **Big Ball of Mud** | CRITICAL | No clear module boundaries, everything depends on everything, changes ripple unpredictably |
| **Golden Hammer** | HIGH | Using the same solution for every problem ("everything is a microservice", "just use a queue") |
| **Premature Optimization** | MEDIUM | Optimizing before measuring, adding complexity for hypothetical performance gains |
| **Not Invented Here** | MEDIUM | Rejecting existing libraries or patterns to build custom versions without clear justification |
| **Analysis Paralysis** | MEDIUM | Over-planning, under-building — the design doc is perfect but nothing ships |
| **Magic** | HIGH | Unclear, undocumented behavior that "just works" — until it doesn't, and nobody knows why |
| **Tight Coupling** | HIGH | Changing one component requires changing another — they ship and break together |
| **God Object** | HIGH | One class/module does everything — knows too much, changes too often, impossible to test in isolation |
| **Distributed Monolith** | CRITICAL | Services that look independent but share a database or can't deploy independently |

### When You Spot an Anti-Pattern

1. **Document it** — log what you found and where
2. **Assess impact** — is it actively causing problems or just a latent risk?
3. **Plan the fix** — don't rewrite everything; refactor incrementally
4. **Write an ADR** — if the fix involves a significant design change
