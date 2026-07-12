# Automated Verification

## Contents
- [When This Applies](#when-this-applies)
- [Pre-Commit Verification Loop](#pre-commit-verification-loop)
- [OpenCode-Specific Manual Steps](#opencode-specific-manual-steps)
- [Build Troubleshooting](#build-troubleshooting)
- [Enforcement](#enforcement)

---

## When This Applies

- Before **every** commit — run the full verification loop
- When working in OpenCode where hooks are unavailable — manual steps replace automated checks
- When a build fails — follow the troubleshooting protocol before changing code
- When setting up a new project — configure verification tooling first

**Do NOT use this reference when:**
- Debugging runtime errors — use the `build-error-resolver` agent or see [build-fix command](file:///home/opencode/.config/opencode/ECC/commands/build-fix.md)
- Configuring CI pipelines — this covers local pre-commit verification, not CI/CD
- Reviewing code that isn't yours — see [git-conventions.md](file:///home/opencode/.config/opencode/skills/ecc-coding-standards/references/git-conventions.md) for PR review

---

## Pre-Commit Verification Loop

Before every commit, run these checks in order. Each gate must pass before proceeding to the next:

| Step | Check | Command / Tool | Success Criterion |
|------|-------|----------------|-------------------|
| 1. Type Check | Compile-time type errors | `npx tsc --noEmit` (TS), `cargo check` (Rust), `go build` (Go) | Zero errors |
| 2. Lint | Code style and static analysis violations | `npm run lint` or `npx eslint` | Zero errors and warnings |
| 3. Format | Code formatting consistency | `npx prettier --write` or `npx @biomejs/biome format --write` | No unstaged formatting changes |
| 4. Tests | Unit, integration, and E2E correctness | `npm test` | All tests pass; zero skipped or ignored |
| 5. Coverage | Test coverage meets tiered targets | `npm test -- --coverage` | 100% critical, 80% standard, 70% UI (see [tdd-workflow.md](file:///home/opencode/.config/opencode/skills/ecc-coding-standards/references/tdd-workflow.md)) |
| 6. Build | Production build succeeds | `npm run build` | Build completes without errors or warnings |

**Violation examples:**
- Running `git commit` without any verification — assumes code is correct
- Fixing a lint error by disabling the rule instead of fixing the code
- Skipping the build step because "it worked in dev mode"

**Correct pattern:**
```
# Full pre-commit sequence
npx tsc --noEmit          # Step 1: types
npm run lint              # Step 2: lint
npx prettier --write .    # Step 3: format
npm test                  # Step 4: tests
npm test -- --coverage    # Step 5: coverage
npm run build             # Step 6: build
# → Only now: git commit
```

---

## OpenCode-Specific Manual Steps

OpenCode does not support Claude Code's hook system. The following automated checks must be performed manually after every code edit batch:

### After Writing or Editing Code

- **Format the file.** Run `prettier --write <file>` or the detected formatter for JS/TS files before committing.
- **Run the type checker.** `npx tsc --noEmit` after every edit batch — catch type errors early, not at commit time.
- **Check for `console.log` statements.** Search changed files for `console.log` and remove any debugging output:
  ```
  grep -n "console\.log" <file>
  ```
  Debug logging belongs behind a proper logger; `console.log` in production source is a violation.

### Before Committing

- **Run the full security checklist.** Verify C01-C08 gates manually — no automated pre-commit hook will stop you.
- **Verify no secrets in code.** Scan the diff for hardcoded keys, tokens, or passwords:
  ```
  git diff --cached | grep -E '(api[_-]?key|secret|password|token)\s*[:=]\s*['"'"'"]'
  ```
- **Run the full test suite.** Don't rely on CI to catch what you can verify locally.

**Violation examples:**
- Pushing code that hasn't been formatted because "the hook would have done it"
- Committing `console.log` statements left from debugging
- Expecting a pre-commit hook to catch type errors — OpenCode has no hooks; it's your responsibility

---

## Build Troubleshooting

When a build or type check fails, follow this protocol before changing any code:

### Protocol

1. **Read the error.** Copy the full error message — type error, build failure, or test failure. What exactly is expected vs. actual?
2. **Run in isolation.** Reproduce the failure with the same command. If it's a type error, run `tsc --noEmit` on just the failing file.
3. **Fix incrementally.** Fix one error at a time. Run the check after each fix to confirm it resolves without introducing new errors.
4. **Verify the fix.** After all fixes, run the full verification loop again.

### Build Fix Rules

| DO (PASS) | DON'T (FAIL) |
|-----------|--------------|
| Fix type errors with correct types | Refactor code or change architecture |
| Add missing imports | Add new features or change behavior |
| Fix syntax errors | Use `any` type or `@ts-ignore` to silence errors |
| Make minimal changes | Change business logic |
| Run type check after each fix | Batch multiple fixes without verification |

### Common Type Errors

| Error | Fix |
|-------|-----|
| Type 'X' is not assignable to type 'Y' | Add correct type annotation or fix the assignment |
| Property 'X' does not exist on type 'Y' | Add property to interface or fix the property name |
| Cannot find module 'X' | Install package or fix the import path |
| Object is possibly 'undefined' | Add null check or optional chaining (`?.`) |
| Argument of type 'X' is not assignable | Fix function signature or cast only as last resort |

**Violation examples:**
- Adding `@ts-ignore` instead of fixing the underlying type error
- Changing business logic to "make the test pass" rather than fixing the real issue
- Refactoring unrelated code during a build fix — one concern per change

---

## Enforcement

- **No commit without verification.** The full loop (typecheck → lint → format → tests → coverage → build) is a blocking gate.
- **No `console.log` in committed code.** Grep for it before committing; production source must use a proper logger.
- **No type suppression without justification.** `@ts-ignore` and `any` require inline comments explaining why a proper fix isn't possible.
- **Build failures block all other work.** A broken build is the top priority — fix it before writing new code.
