# TypeScript / JavaScript Design Patterns

**Purpose:** Deep-dive on idiomatic TypeScript and JavaScript design patterns beyond the overview in SKILL.md. Use this reference when designing new TS/JS modules or reviewing TypeScript architecture decisions.

## Table of Contents

- [Discriminated Unions](#discriminated-unions)
- [Branded Types](#branded-types)
- [Result / Either Types](#result--either-types)
- [Zod / Runtime Validation](#zod--runtime-validation)
- [Dependency Injection](#dependency-injection)
- [ADR Template for TypeScript Projects](#adr-template-for-typescript-projects)
- [Red Flags](#red-flags)

---

## Discriminated Unions

Tagged unions with a literal `type`/`kind` field enable exhaustive pattern matching:

```typescript
type Result<T, E> =
  | { success: true; data: T }
  | { success: false; error: E };

type Action =
  | { type: "ADD_ITEM"; payload: Item }
  | { type: "REMOVE_ITEM"; id: string }
  | { type: "CLEAR_CART" };

function reduce(state: CartState, action: Action): CartState {
  switch (action.type) {
    case "ADD_ITEM":
      return { ...state, items: [...state.items, action.payload] };
    case "REMOVE_ITEM":
      return { ...state, items: state.items.filter(i => i.id !== action.id) };
    case "CLEAR_CART":
      return { ...state, items: [] };
  }
}
```

Use for: state machines, action types, API response variants. TypeScript will warn if a `switch` doesn't cover all variants.

---

## Branded Types

Intersection with a unique symbol prevents mixing semantically different primitives:

```typescript
declare const __brand: unique symbol;
type Brand<T, B extends string> = T & { [__brand]: B };

type UserId = Brand<string, "UserId">;
type OrderId = Brand<string, "OrderId">;

function getUser(id: UserId): User { ... }

// Error: OrderId is not assignable to UserId
getUser(someOrderId);
```

Use for: IDs, tokens, any primitive where accidental mixing causes bugs. Zero runtime cost — erased at compile time.

---

## Result / Either Types

Error handling without exceptions — return values instead of throwing:

```typescript
type Result<T, E = Error> =
  | { success: true; data: T }
  | { success: false; error: E };

function parseConfig(raw: string): Result<Config, ParseError> {
  try {
    return { success: true, data: JSON.parse(raw) };
  } catch (e) {
    return { success: false, error: new ParseError("invalid JSON", { cause: e }) };
  }
}

// Caller must handle both paths
const result = parseConfig(raw);
if (!result.success) {
  logger.error("config parse failed", result.error);
  return defaultConfig;
}
useConfig(result.data);
```

Use at: API boundaries, config parsing, any operation where the caller should explicitly handle failure. Libraries like `neverthrow` provide `map`, `andThen`, `match` helpers.

---

## Zod / Runtime Validation

Validate at the edge; derive types from schemas:

```typescript
import { z } from "zod";

const UserSchema = z.object({
  id: z.string().uuid(),
  email: z.string().email(),
  age: z.number().int().min(0).optional(),
});

type User = z.infer<typeof UserSchema>;

// At the API boundary:
function handleCreateUser(body: unknown) {
  const parsed = UserSchema.safeParse(body);
  if (!parsed.success) {
    return { status: 400, errors: parsed.error.issues };
  }
  return createUser(parsed.data);
}
```

Use for: API request/response validation, config file parsing, environment variable validation. Derive TypeScript types from the schema — single source of truth.

---

## Dependency Injection

Pass dependencies explicitly via function parameters or constructor:

```typescript
class OrderService {
  constructor(
    private repo: OrderRepository,
    private payment: PaymentGateway,
    private logger: Logger,
  ) {}

  async placeOrder(order: NewOrder): Promise<Result<OrderId>> {
    this.logger.info("placing order", { orderId: order.id });
    const saved = await this.repo.save(order);
    const charged = await this.payment.charge(saved.total);
    if (!charged.success) return { success: false, error: charged.error };
    return { success: true, data: saved.id };
  }
}

// In tests:
const service = new OrderService(mockRepo, mockPayment, mockLogger);
```

Prefer constructor injection for classes, parameter injection for functions. Default to real implementations; override in tests.

---

## ADR Template for TypeScript Projects

```markdown
# ADR-NNN: [Title]

**Status:** Proposed | Accepted | Deprecated
**Runtime:** Node.js | Deno | Bun | Browser
**Package:** (which package this affects)

## Context
Describe the problem and why it needs a decision.

## Decision
State the chosen approach with TypeScript-specific justification.

## Consequences
- Positive: ...
- Negative: ...
- Tradeoffs: ...

## Alternatives Considered
- Approach A: (why rejected)
- Approach B: (why rejected)
```

---

## Red Flags

| Pattern | Severity | What to Look For |
|---------|----------|------------------|
| `any` anywhere | HIGH | Defeats the purpose of TypeScript — use `unknown` + narrowing |
| Overly generic types | MEDIUM | Obscures intent — prefer concrete types, add generics when needed |
| Missing `as const` on union literals | LOW | Widens types unexpectedly — use `as const` for literal unions |
| Optional chaining chains (`.?.?.?`) | MEDIUM | Usually means the type is too loose — tighten the shape |
| `@ts-ignore` / `@ts-expect-error` without comment | HIGH | Suppresses real errors — add a comment explaining why it's safe |
| Mixing `class` and plain objects | MEDIUM | Pick one model per domain — don't mix class instances with POJOs for the same concept |
