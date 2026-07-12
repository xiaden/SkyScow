---
name: making-design-documents
description: Produce language-idiomatic design documents for features. Covers design patterns for Rust, Go, Python, and TypeScript/JS — each in its own reference file loaded on demand. Use when designing a new feature, evaluating cross-language design trade-offs, or writing Architecture Decision Records (ADRs). For decomposing a design document into implementation plans, use decomposing-design-documents. Not for trivial single-file changes, pure bug-fixes, or mechanical plan execution.
---

# Making Design Documents

**Purpose:** Produce language-idiomatic design documents (DDs) for features. Load this before writing a design doc or evaluating architectural trade-offs. For decomposing a DD into implementation plans, use `decomposing-design-documents`.

---

## Progressive Disclosure

This skill uses the three-level loading system:

| Level | What loads | When |
|-------|-----------|------|
| **1. Metadata** | `name` + `description` from frontmatter | Always — listed in the `<available_skills>` block |
| **2. Body** | This SKILL.md (core workflow, language selection, anti-patterns) | When the agent decides the task involves feature design or planning |
| **3. References** | Language-specific design patterns, architectural principles & trade-off analysis, decomposition methodology | Only when the agent reads the relevant reference for the target language, design principle, or planning task |

### What Goes Where

| Keep in SKILL.md (always loaded) | Move to references/ (loaded on demand) |
|----------------------------------|----------------------------------------|
| Design workflow overview | Full decomposition methodology (`planning.md`) |
| Architectural principles quick-reference | Detailed principles, trade-off analysis, cross-language patterns (`architecture-principles.md`) |
| Language selection table | Language-specific idiomatic patterns (`rust-design.md`, `go-design.md`, etc.) |
| Anti-patterns quick-reference | Detailed code examples, ADR templates, and design checklists |
| ADR guidance (when to write one) | Language-specific ADR templates |
| Pointers to `references/` | Step-by-step plan breakdown instructions |

---

## When to Use

**Load this skill when:**

- Designing a new feature or system architecture
- Creating an implementation plan from requirements
- Evaluating design trade-offs across languages
- Writing Architecture Decision Records (ADRs)

**Do NOT use this skill when:**

- Making a trivial, single-file change with no architectural implications
- You already have a validated plan and just need to execute it mechanically
- The task is pure bug-fixing with no design component
- You need to decompose a design document into task plans — use `decomposing-design-documents` instead

---

## Design Workflow

Good feature design follows a consistent process regardless of language. Start here before picking a language-specific reference:

1. **Requirements analysis** — understand the feature completely before decomposing. Identify success criteria, functional requirements, and non-functional requirements (performance, scalability, security, availability). List assumptions and constraints explicitly.
2. **Architecture review** — analyze existing codebase structure, identify affected components, find reusable patterns. Consider what stays, what changes, and what's new.
3. **Trade-off analysis** — for each significant design decision, document pros, cons, alternatives considered, and the rationale. When the decision constrains future work, write an ADR. See the [Architectural Principles](#architectural-principles) section and [`references/architecture-principles.md`](file:///home/opencode/.config/opencode/skills/making-design-documents/references/architecture-principles.md) for the full methodology.
For decomposing a design document into implementation plans with dependency ordering, contracts, and cross-validation, use `decomposing-design-documents`. The design skill's job stops at producing the design document.

For the full architecture principles methodology and trade-off analysis: [`references/architecture-principles.md`](file:///home/opencode/.config/opencode/skills/making-design-documents/references/architecture-principles.md).

---

## Architectural Principles

Five universal principles that guide every design decision. Evaluate your design against each before committing to an approach:

| Principle | Core Question | Red Flag |
|-----------|---------------|----------|
| **Modularity** | Can components be tested and deployed independently? | A module needs 5+ imports from unrelated parts of the codebase |
| **Scalability** | Can this handle 10× the load by adding instances? | State stored in memory that won't sync across instances |
| **Maintainability** | Can a new developer find and understand the relevant code in 10 minutes? | "We've always done it that way" is the only justification |
| **Security** | Is every input validated at the boundary? Every state change audited? | "We'll add security later" |
| **Performance** | Is the bottleneck measured, not guessed? | Optimizing before profiling |

**Trade-off analysis** — for every significant design decision, document pros, cons, alternatives, and rationale. When the decision constrains future work, write an ADR.

For the full principles with detailed descriptions, the four-part trade-off analysis methodology (with example), common cross-language patterns (Frontend, Backend, Data), the system design checklist (Functional, NFRs, Technical, Operations), and architectural anti-patterns: [`references/architecture-principles.md`](file:///home/opencode/.config/opencode/skills/making-design-documents/references/architecture-principles.md).

---

## Language-Specific Design Patterns

Different languages have idiomatic ways to express common design concerns. Choose patterns that feel native to the language, not patterns ported from another ecosystem.

**Load the reference file for the language you're designing in:**

| Language | Reference | Key Concerns |
|----------|-----------|--------------|
| **Rust** | [`references/rust-design.md`](file:///home/opencode/.config/opencode/skills/making-design-documents/references/rust-design.md) | Enums for state machines, ownership/RAII, trait-based polymorphism, error types |
| **Go** | [`references/go-design.md`](file:///home/opencode/.config/opencode/skills/making-design-documents/references/go-design.md) | Struct embedding, small interfaces, context propagation, functional options |
| **Python** | [`references/python-design.md`](file:///home/opencode/.config/opencode/skills/making-design-documents/references/python-design.md) | Protocol vs ABC, dataclasses, context managers, decorator-based cross-cutting |
| **TypeScript/JS** | [`references/typescript-design.md`](file:///home/opencode/.config/opencode/skills/making-design-documents/references/typescript-design.md) | Discriminated unions, branded types, Zod validation, Result types |

Each reference contains: pattern overview with code examples, red flags table, and language-specific ADR templates or design checklists. References are one level deep — load the one for your language, not all of them.

---

## Architecture Decision Records (ADRs)

For significant design decisions, create an ADR using the two-step workflow (`adr_suggest` → `adr_commit`). Each ADR captures:

- **Status** — Proposed, Accepted, Deprecated, or Superseded
- **Context** — what situation requires a decision and why it matters
- **Decision** — the choice made, with justification
- **Consequences** — positive outcomes, negative trade-offs, and risks accepted
- **Alternatives considered** — what was rejected and why

```markdown
# ADR-NNN: [Title]

**Status:** Proposed | Accepted | Deprecated
**Date:** YYYY-MM-DD

## Context
Describe the problem and why it needs a decision.

## Decision
State the chosen approach with justification.

## Consequences
- Positive: ...
- Negative: ...
- Tradeoffs: ...

## Alternatives Considered
- **Approach A**: Description and reason for rejection
- **Approach B**: Description and reason for rejection
```

Language-specific references include ADR templates adapted to each ecosystem (e.g., Rust ADR template with `crate` and `edition` fields, TypeScript template with `runtime` field).

---

## Anti-Patterns

Design-level red flags that transcend any single language. The language-specific references cover language-level gotchas; these are the architectural ones:

| Anti-Pattern | What to Look For |
|--------------|------------------|
| **Language tourism** | Applying Rust's `Result` in Python instead of using exceptions idiomatically. Use native patterns. |
| **Pattern-first design** | Picking a pattern ("let's use CQRS!") before understanding the problem. Start with requirements, then find the pattern. |
| **Big Ball of Mud** | No clear module boundaries — changes ripple unpredictably. Fix: define interfaces and enforce them. |
| **Golden Hammer** | Using the same solution for every problem. Fix: evaluate each problem on its own terms. |
| **Tight Coupling** | Changing one component requires changing another. Fix: depend on abstractions, not implementations. |
| **God Object** | One class/module does everything — knows too much, impossible to test in isolation. Fix: split by responsibility. |
| **Analysis paralysis** | Perfect design doc, zero code shipped. The best plans enable incremental implementation and are refined as you learn. |
| **Over-decomposition** | Splitting a feature into 20 phases when 4 would do. Each phase boundary adds overhead. |
| **Skipping ADRs** | What's obvious today may be mysterious in 6 months. If the decision constrains future work, write it down. |
| **Distributed Monolith** | Services that look independent but share a database or can't deploy independently. |
| **Magic** | Undocumented behavior that "just works" — until it doesn't, and nobody knows why. |

For full descriptions including severity levels and remediation strategies, see [`references/architecture-principles.md`](file:///home/opencode/.config/opencode/skills/making-design-documents/references/architecture-principles.md) § Architectural Anti-Patterns.

---

## References

All detail lives in `references/`, loaded on demand at Level 3:

| File | Contents |
|------|----------|
| [`references/architecture-principles.md`](file:///home/opencode/.config/opencode/skills/making-design-documents/references/architecture-principles.md) | Architectural principles, trade-off analysis methodology, cross-language patterns (Frontend/Backend/Data), system design checklist, architectural anti-patterns |
| [`references/planning.md`](file:///home/opencode/.config/opencode/skills/making-design-documents/references/planning.md) | Full decomposition methodology, plan format template, best practices |
| [`references/rust-design.md`](file:///home/opencode/.config/opencode/skills/making-design-documents/references/rust-design.md) | Rust patterns: enums, ownership/RAII, trait polymorphism, error types |
| [`references/go-design.md`](file:///home/opencode/.config/opencode/skills/making-design-documents/references/go-design.md) | Go patterns: interfaces, embedding, context, functional options |
| [`references/python-design.md`](file:///home/opencode/.config/opencode/skills/making-design-documents/references/python-design.md) | Python patterns: protocols, dataclasses, context managers, decorators |
| [`references/typescript-design.md`](file:///home/opencode/.config/opencode/skills/making-design-documents/references/typescript-design.md) | TS/JS patterns: discriminated unions, branded types, Zod, Result types |
