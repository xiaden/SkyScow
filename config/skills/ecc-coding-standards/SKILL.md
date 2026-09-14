---
name: ecc-coding-standards
description: Enforce security gates, immutability patterns, TDD workflow, and git conventions across all implementation work. Use when writing code, reviewing PRs, starting a new feature, or verifying commit readiness. Do NOT use for architecture decisions, dependency selection, or deployment configuration.
---

# ECC Coding Standards

**Purpose:** Apply a unified development methodology — security gates, code quality, test-first development where an executable behavioral oracle exists, and documentation discipline — to every implementation and review task.

---

## When to Use

**Trigger conditions:**

- Writing or modifying source code in any language
- Reviewing a pull request or code diff
- Starting a new feature or bug fix
- Preparing a commit (security checklist C01-C08 applies when the changed surface is observably security-sensitive; canonical owner: `config/skills/security-review/SKILL.md`)
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

1. **Security** — Gate observably security-sensitive changes against C01-C08 before merging; security-sensitive surface applicability is owned by `config/skills/security-review/SKILL.md`. For non-security changes, preserve existing security invariants under ordinary correctness review.
2. **Code Quality** — Enforce immutability, small files, and explicit error handling while writing
3. **Testing** — Apply RED → GREEN → REFACTOR when a meaningful executable behavioral oracle exists: a regression test can reproduce the defect, the repository already uses that style, or a spec-first test reduces ambiguity. Do not force artificial RED for static config, packaging, Dockerfiles, deployment manifests, docs, mechanical migrations, build metadata, or infrastructure — there the proof is a build, smoke, or runtime check. Coverage is a diagnostic selected per `config/instructions/validation-mandate.md`; no universal percentage.
4. **Git & Documentation** — Structure commits, PRs, and feature workflows to make the above verifiable
5. **Automated Verification** — Select the verification evidence for the observable changed surface from the surface-to-evidence table in `config/instructions/validation-mandate.md`; run the repository's own commands, apply each check only when the repository defines that command, and omit and report an undefined command rather than inventing one

No area is optional for the surface where it applies. A change with an executable behavioral oracle is incomplete without behavioral evidence; a change whose observable proof is a build, smoke, or runtime check is incomplete without that check.

---

## Reference Dispatch

Each area has a dedicated reference file. Route to the one that matches your current task:

| You are... | Load | Contains |
|------------|------|----------|
| Preparing a commit; handling secrets, auth, or user input | [`references/security-checklist.md`](file:///home/opencode/.config/opencode/skills/ecc-coding-standards/references/security-checklist.md) | Security gates C01-C08, applied when the changed surface is observably security-sensitive (canonical owner: `config/skills/security-review/SKILL.md`) |
| Writing or reviewing code; refactoring | [`references/coding-standards.md`](file:///home/opencode/.config/opencode/skills/ecc-coding-standards/references/coding-standards.md) | Immutability, file size, error handling rules |
| Before writing implementation; tests are failing | [`references/tdd-workflow.md`](file:///home/opencode/.config/opencode/skills/ecc-coding-standards/references/tdd-workflow.md) | RED → GREEN → REFACTOR guidance and when it applies; repository-defined coverage |
| Creating commits, PRs, or planning a feature branch | [`references/git-conventions.md`](file:///home/opencode/.config/opencode/skills/ecc-coding-standards/references/git-conventions.md) | Commit structure, PR workflow, feature branching, code review severity levels |
| Before committing; build is failing; working in OpenCode (no hooks) | [`references/verification.md`](file:///home/opencode/.config/opencode/skills/ecc-coding-standards/references/verification.md) | Pre-commit verification loop, OpenCode manual steps, build troubleshooting |

---

## Validation Checklist

Before completing any implementation task, verify against these gates:

### Security
- [ ] For observably security-sensitive changes, C01-C08 gates pass for the affected files in the diff (canonical owner: `config/skills/security-review/SKILL.md`); non-security changes preserve existing security invariants under ordinary correctness review
- [ ] No secrets or credentials in code or commit messages
- [ ] Input validation present for all user-facing entry points

### Code Quality
- [ ] No new files exceed the size limit (see coding-standards reference)
- [ ] State mutations return new objects, never modify in place
- [ ] Error handling catches specific types, logs context

### Testing
- [ ] Where an executable behavioral oracle exists, tests were written before implementation (RED first); otherwise the change was proven by the surface-appropriate build/smoke/runtime check (see `config/instructions/validation-mandate.md`)
- [ ] Coverage is a useful diagnostic when the repository supports it; honor a repository-defined coverage threshold when one exists — impose no universal percentage (see `config/instructions/validation-mandate.md`)
- [ ] Tests pass, when the repository defines tests — no skipped or ignored tests

### Git & Documentation
- [ ] Commit messages follow conventional commit format
- [ ] PR description references relevant issues or tasks
- [ ] Feature workflow documentation updated if applicable

### Verification
- [ ] Verification evidence is selected for the observable changed surface from the surface-to-evidence table in `config/instructions/validation-mandate.md`; no fixed universal sequence is imposed
- [ ] Each check below was applied only when the repository defines that command for the changed surface; an undefined command (type check, lint, formatter, tests, build) is omitted and reported, never invented
- [ ] Type check passes, when the repository defines a type-check command
- [ ] Lint passes with zero errors, when the repository defines a lint command
- [ ] Formatter applied to all changed files, when the repository defines a formatter
- [ ] Tests pass for the changed surface, when the repository defines tests; no universal unit+integration+E2E stacking is required
- [ ] Coverage is reported from the repository's own policy when such a gate exists; no universal percentage is imposed (see `config/instructions/validation-mandate.md`)
- [ ] Build succeeds without warnings, when the changed surface produces a build

---

## Anti-Patterns

| Anti-Pattern | Correct Approach |
|--------------|-----------------|
| Skipping security checks on an observably security-sensitive surface | Apply the C01-C08 gates only when the changed surface is observably security-sensitive (canonical owner: `config/skills/security-review/SKILL.md`); non-security changes preserve existing security invariants under ordinary correctness review. CRITICAL/HIGH still block. |
| Mutating state in place | Return new objects; use spread/immutable patterns |
| Writing code before tests on a surface with an executable behavioral oracle | Write failing test first (RED), then implement (GREEN); for static config, packaging, docs, build metadata, or infrastructure, rely on the build/smoke/runtime proof |
| Catching generic `Error` or bare `except` | Catch specific exception types; log context |
| Applying a universal coverage percentage | Coverage is a diagnostic when the repository supports it; honor a repository-defined coverage threshold when one exists — impose no universal percentage (see `config/instructions/validation-mandate.md`) |
| Vague commit messages like "fix bug" | Use conventional commits: `fix(auth): handle expired token refresh` |
| Committing without verification | Select and run the repository-defined evidence for the observable changed surface from the surface-to-evidence table in `config/instructions/validation-mandate.md`; omit and report any command the repository does not define |
| Skipping formatter on changed files | When the repository defines a formatter, run it on every changed file before commit; omit and report a repository that defines none (see `config/instructions/validation-mandate.md`) |
