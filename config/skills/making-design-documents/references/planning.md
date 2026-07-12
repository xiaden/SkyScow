# Planning & Decomposition Methodology

**Purpose:** Systematic approach to breaking features into actionable implementation plans. Use when converting requirements into phased steps with clear dependencies.

## Table of Contents

- [Planning Process](#planning-process)
- [Step Breakdown](#step-breakdown)
- [Phase Grouping](#phase-grouping)
- [Plan Format Template](#plan-format-template)
- [Best Practices](#best-practices)
- [Refactor Planning](#refactor-planning)
- [Red Flags](#red-flags)

---

## Planning Process

### 1. Requirements Analysis

- Understand the feature request completely — ask clarifying questions if needed
- Identify success criteria, assumptions, and constraints
- List functional and non-functional requirements explicitly

### 2. Architecture Review

- Analyze existing codebase structure and identify affected components
- Review similar implementations in the codebase for reusable patterns
- Consider what stays, what changes, and what's new

### 3. Step Breakdown

See [Step Breakdown](#step-breakdown) below.

### 4. Phase Grouping

See [Phase Grouping](#phase-grouping) below.

### 5. Implementation Order

- Prioritize by dependencies (foundation first, polish last)
- Group related changes to reduce cognitive overhead
- Enable incremental testing — every phase should be independently testable

---

## Step Breakdown

Each step must include:

- **Clear, specific actions** — exact file paths, function names, variable names
- **Dependencies** — what must be done before this step
- **Estimated complexity** — Low / Medium / High
- **Potential risks** — what could go wrong, and how to mitigate

---

## Phase Grouping

Group steps into phases by dependency and cohesion:

- Each phase should produce a **verifiable outcome** (compiling code, passing tests, deployable state)
- Order phases by dependency chain — no phase should depend on a later phase
- Minimize context switching within a phase

---

## Plan Format Template

```markdown
# Implementation Plan: [Feature Name]

## Overview
[2-3 sentence summary]

## Requirements
- [Requirement 1]
- [Requirement 2]

## Architecture Changes
- [Change 1: file path and description]
- [Change 2: file path and description]

## Implementation Steps

### Phase 1: [Phase Name]
1. **[Step Name]** (File: path/to/file.ts)
   - Action: Specific action to take
   - Why: Reason for this step
   - Dependencies: None / Requires step X
   - Risk: Low/Medium/High

2. **[Step Name]** (File: path/to/file.ts)
   ...

### Phase 2: [Phase Name]
...

## Testing Strategy
- Unit tests: [files to test]
- Integration tests: [flows to test]
- E2E tests: [user journeys to test]

## Risks & Mitigations
- **Risk**: [Description]
  - Mitigation: [How to address]

## Success Criteria
- [ ] Criterion 1
- [ ] Criterion 2
```

---

## Best Practices

1. **Be specific** — use exact file paths, function names, variable names
2. **Consider edge cases** — think about error scenarios, null values, empty states
3. **Minimize changes** — prefer extending existing code over rewriting
4. **Maintain patterns** — follow existing project conventions
5. **Enable testing** — structure changes to be easily testable
6. **Think incrementally** — each step should be verifiable
7. **Document decisions** — explain why, not just what

---

## Refactor Planning

When planning refactors specifically:

1. Identify code smells and technical debt
2. List specific improvements needed
3. Preserve existing functionality
4. Create backwards-compatible changes when possible
5. Plan for gradual migration if needed

---

## Red Flags

Check the plan for these warning signs:

- Large functions (>50 lines)
- Deep nesting (>4 levels)
- Duplicated code
- Missing error handling
- Hardcoded values
- Missing tests
- Performance bottlenecks

A great plan is specific, actionable, and considers both the happy path and edge cases. The best plans enable confident, incremental implementation.
