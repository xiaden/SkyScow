# Scope Decisions

How to decide what a single instruction file should cover, when to split, and how to avoid conflicting rules.

## Granularity

Each instruction file should cover **one coherent area**. The test for coherence: would a single `applyTo` pattern naturally cover all the conventions listed?

### When to Split

Split a file when:

| Situation | Example |
|-----------|---------|
| Two areas have conflicting conventions | `src/api/v1/**` uses snake_case params; `src/api/v2/**` uses camelCase |
| One file exceeds ~300 lines | Split by sub-area: `services-layer.instructions.md` → `services-auth.instructions.md` + `services-data.instructions.md` |
| The `applyTo` patterns don't overlap naturally | `src/api/**` and `src/cli/**` — different concerns, different audiences |
| Conventions are owned by different teams | Frontend `components/` vs backend `services/` — separation prevents churn |

### When to Combine

Combine into one file when:

| Situation | Example |
|-----------|---------|
| Two areas share identical conventions | `src/hooks/**` and `src/composables/**` both enforce the same composition rules |
| The combined content is under 100 lines | A lightweight convention file that covers a few sibling directories |
| Splitting would duplicate the same rules verbatim | Two route directories with the same validation, response, and error rules |

## Overlap Avoidance

Instruction files **must not** have overlapping `applyTo` patterns. When two files match the same path, the agent receives conflicting or duplicated instructions — neither outcome is acceptable.

### Detection

Audit `applyTo` patterns before adding a new file:

```bash
# Check if any existing instruction file already covers the path you're adding
grep -r "applyTo:" .opencode/instructions/ ~/.config/opencode/instructions/
```

### Resolution

When overlap is detected:

```yaml
# Bad — overlapping patterns
# File 1: applyTo: src/api/**
# File 2: applyTo: src/api/v2/**

# Resolution option A: Merge into one file
# applyTo: src/api/**

# Resolution option B: Narrow the broader pattern
# File 1: applyTo: src/api/v1/**
# File 2: applyTo: src/api/v2/**
```

Choose merge when the conventions are similar enough to coexist. Choose narrowing when `v1` and `v2` enforce different rules.

### Edge Case: Nested Conventions

Sometimes a subdirectory legitimately needs additional rules beyond its parent:

```yaml
# Parent: applies to all services
# applyTo: src/services/**

# Child: applies to auth services specifically, adding auth-specific rules
# applyTo: src/services/auth/**
```

**This is overlap.** The child's path is a subset of the parent's. The agent editing `src/services/auth/login.ts` would receive both sets of instructions.

Resolution: merge the auth-specific rules into the parent file as a subsection, or document them as a separate section in the same file with a conditional ("For auth services under `src/services/auth/`, additionally: …").
