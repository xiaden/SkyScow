# Python Design Patterns

**Purpose:** Deep-dive on idiomatic Python design patterns beyond the overview in the SKILL.md. Use this reference when designing new Python modules or reviewing Python architecture decisions.

## Protocol (PEP 544) for Structural Subtyping

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class Drawable(Protocol):
    def draw(self, canvas: "Canvas") -> None: ...

class Circle:
    def draw(self, canvas: Canvas) -> None:
        canvas.render_circle(self.radius, self.center)

# Circle satisfies Drawable implicitly — no inheritance
def render_all(objects: list[Drawable], canvas: Canvas) -> None:
    for obj in objects:
        obj.draw(canvas)
```

Use Protocol when: you want duck typing with type safety, and multiple unrelated types happen to have the same shape.

## Dataclasses for Value Objects

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: str

    def __post_init__(self) -> None:
        if self.amount < 0:
            raise ValueError("Amount cannot be negative")
```

Use `frozen=True` for immutability. Add validation in `__post_init__`.

## Context Managers

```python
from contextlib import contextmanager

@contextmanager
def db_transaction(db: Database):
    tx = db.begin()
    try:
        yield tx
        tx.commit()
    except Exception:
        tx.rollback()
        raise

# Usage
with db_transaction(database) as tx:
    tx.execute("UPDATE accounts SET balance = balance - 100 WHERE id = 1")
```

## Decorators for Cross-Cutting Concerns

```python
from functools import wraps
import time

def timed(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        try:
            return func(*args, **kwargs)
        finally:
            elapsed = time.perf_counter() - start
            print(f"{func.__name__} took {elapsed:.3f}s")
    return wrapper
```

## Constructor-Based DI

```python
class OrderService:
    def __init__(self, repo: OrderRepository, payment: PaymentGateway):
        self._repo = repo
        self._payment = payment

# In tests:
order_service = OrderService(MockOrderRepo(), MockPaymentGateway())
```

## ABC vs Protocol Decision Guide

| Use ABC when... | Use Protocol when... |
|-----------------|---------------------|
| You want to enforce an interface contract | You want duck typing with type safety |
| Subclasses share implementation via `super()` | Unrelated types share the same interface shape |
| You need `@abstractmethod` enforcement at instantiation | You want `@runtime_checkable` for `isinstance` checks |

## Documentation Update Workflow for Python Projects

1. Run `pydoc` or `mkdocs build` to identify broken docs
2. Update docstrings in changed modules (Google-style or NumPy-style)
3. Regenerate API docs from docstrings
4. Update README with new features/changed APIs
5. Verify all `.. automodule::` directives resolve

## Red Flags

| Pattern | Severity | What to Look For |
|---------|----------|------------------|
| Protocol where ABC is better | MEDIUM | Prefer ABC for enforced contracts with shared implementation |
| Mutable default arguments | CRITICAL | `def f(x=[])` → use `def f(x=None)` with `x = x or []` |
| Mixed sync/async | HIGH | Don't call async functions from sync context without proper event loop management |
| `except: pass` | CRITICAL | Silently swallows all errors — catch specific exceptions |
| Import * | MEDIUM | `from module import *` pollutes namespace — import what you need |
