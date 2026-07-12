---
name: ecc-coding-standards
description: Enforce security gates, immutability patterns, TDD workflow, and git conventions across all implementation work. Use when writing code, reviewing PRs, starting a new feature, or verifying commit readiness. Do NOT use for architecture decisions, dependency selection, or deployment configuration.
---

# ECC Coding Standards

**Purpose:** Apply a unified development methodology — security gates, code quality, test-driven development, and documentation discipline — to every implementation and review task.

---

## When to Use

**Trigger conditions:**

- Writing or modifying source code in any language
- Reviewing a pull request or code diff
- Starting a new feature or bug fix
- Preparing a commit (security checklist C01-C08 must pass)
- Setting up project conventions for a new codebase

**Do NOT use when:**

- Making architecture or design decisions (use ADRs instead)
- Selecting dependencies or frameworks
- Configuring CI/CD pipelines or deployment
- Debugging runtime issues unrelated to code quality
- Working on documentation that isn't code-adjacent (use project docs conventions)

---

## Methodology Overview

These five areas form a development lifecycle. Apply them in order during implementation:

1. **Security** — Gate every commit against C01-C08 before merging
2. **Code Quality** — Enforce immutability, small files, and explicit error handling while writing
3. **Testing** — Drive implementation with TDD (RED → GREEN → REFACTOR), verify tiered coverage
4. **Git & Documentation** — Structure commits, PRs, and feature workflows to make the above verifiable
5. **Automated Verification** — Run the pre-commit verification loop (typecheck → lint → format → tests → coverage) before every commit

No area is optional. A commit that passes security but skips tests is incomplete.

---

## Reference Dispatch

Each area has a dedicated reference file. Route to the one that matches your current task:

| You are... | Load | Contains |
|------------|------|----------|
| Preparing a commit; handling secrets, auth, or user input | [`references/security-checklist.md`](file:///home/opencode/.config/opencode/skills/ecc-coding-standards/references/security-checklist.md) | Security gates C01-C08 |
| Writing or reviewing code; refactoring | [`references/coding-standards.md`](file:///home/opencode/.config/opencode/skills/ecc-coding-standards/references/coding-standards.md) | Immutability, file size, error handling rules |
| Before writing implementation; tests are failing | [`references/tdd-workflow.md`](file:///home/opencode/.config/opencode/skills/ecc-coding-standards/references/tdd-workflow.md) | RED → GREEN → REFACTOR workflow, coverage thresholds |
| Creating commits, PRs, or planning a feature branch | [`references/git-conventions.md`](file:///home/opencode/.config/opencode/skills/ecc-coding-standards/references/git-conventions.md) | Commit structure, PR workflow, feature branching, code review severity levels |
| Before committing; build is failing; working in OpenCode (no hooks) | [`references/verification.md`](file:///home/opencode/.config/opencode/skills/ecc-coding-standards/references/verification.md) | Pre-commit verification loop, OpenCode manual steps, build troubleshooting |

---

## Validation Checklist

Before completing any implementation task, verify against these gates:

### Security
- [ ] C01-C08 gates pass for all files in the diff
- [ ] No secrets or credentials in code or commit messages
- [ ] Input validation present for all user-facing entry points

### Code Quality
- [ ] No new files exceed the size limit (see coding-standards reference)
- [ ] State mutations return new objects, never modify in place
- [ ] Error handling catches specific types, logs context

### Testing
- [ ] Tests were written before implementation (TDD: RED first)
- [ ] Coverage meets tiered target (100% critical, 80% standard, 70% UI) across unit, integration, and E2E
- [ ] All tests pass — no skipped or ignored tests

### Git & Documentation
- [ ] Commit messages follow conventional commit format
- [ ] PR description references relevant issues or tasks
- [ ] Feature workflow documentation updated if applicable

### Verification
- [ ] Type check passes (`tsc --noEmit` or equivalent)
- [ ] Lint passes with zero errors
- [ ] Formatter applied to all changed files
- [ ] All tests pass (unit, integration, E2E)
- [ ] Coverage meets tiered target (100% critical, 80% standard, 70% UI)
- [ ] Build succeeds without warnings

---

## Anti-Patterns

| Anti-Pattern | Correct Approach |
|--------------|-----------------|
| Skipping security checklist before commit | Run C01-C08 on every commit, no exceptions |
| Mutating state in place | Return new objects; use spread/immutable patterns |
| Writing code before tests | Write failing test first (RED), then implement (GREEN) |
| Catching generic `Error` or bare `except` | Catch specific exception types; log context |
| Skipping coverage verification | Run coverage tool; require tiered targets (100% critical, 80% standard, 70% UI) |
| Vague commit messages like "fix bug" | Use conventional commits: `fix(auth): handle expired token refresh` |
| Committing without running the verification loop | Run typecheck → lint → format → tests → coverage before every commit |
| Skipping formatter on changed files | Run formatter (prettier/biome) on every changed file before commit |
