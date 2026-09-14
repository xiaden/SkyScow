# Automated Verification

## Contents
- [When This Applies](#when-this-applies)
- [Pre-Commit Verification Loop](#pre-commit-verification-loop)
- [OpenCode-Specific Manual Steps](#opencode-specific-manual-steps)
- [Build Troubleshooting](#build-troubleshooting)
- [Enforcement](#enforcement)

---

## When This Applies

- Before **every** commit — run the repository-defined, surface-selected verification for the changed surface (see [Pre-Commit Verification Loop](#pre-commit-verification-loop))
- When working in OpenCode where hooks are unavailable — manual steps replace automated checks
- When a build fails — follow the troubleshooting protocol before changing code
- When setting up a new project — configure verification tooling first

**Do NOT use this reference when:**
- Debugging runtime errors — use the `build-error-resolver` agent or see [build-fix command](file:///home/opencode/.config/opencode/ECC/commands/build-fix.md)
- Configuring CI pipelines — this covers local pre-commit verification, not CI/CD
- Reviewing code that isn't yours — see [git-conventions.md](file:///home/opencode/.config/opencode/skills/ecc-coding-standards/references/git-conventions.md) for PR review

---

## Pre-Commit Verification Loop

Select the verification for the changed surface from the surface-to-evidence table in
`/home/opencode/.config/opencode/instructions/validation-mandate.md`. Repository-native commands and conventions outrank any
generic list, and no fixed universal sequence is imposed.

The loop below is a template, not a universal gate. Apply a row only when the repository actually
defines that command for the changed surface; skip rows whose command does not exist and report the
absence — never invent or run a command the repository does not define.

| Step | Check | Command / Tool | Success Criterion |
|------|-------|----------------|-------------------|
| 1. Type Check | Compile-time type errors, when the repository defines a type checker | The repository's own type-check command | Zero errors |
| 2. Lint | Code style and static analysis violations, when the repository defines a linter | The repository's own lint command | Zero errors and warnings |
| 3. Format | Code formatting consistency, when the repository defines a formatter | The repository's own format command | No unstaged formatting changes |
| 4. Tests | Behavioral correctness for the changed surface, when the repository defines tests | The repository's own test command | All configured tests pass |
| 5. Repository verification | Surface-selected evidence from `/home/opencode/.config/opencode/instructions/validation-mandate.md` | The repository's own configured command(s) | Passes; coverage is a diagnostic, never a universal percentage |
| 6. Build | Production build succeeds, when the changed surface produces a build | The repository's own build command | Build completes without errors or warnings |

**Violation examples:**
- Running `git commit` without any verification — assumes code is correct
- Inventing a command the repository does not define — for example `npm test` or `npx tsc` where no Node toolchain exists
- Fixing a lint error by disabling the rule instead of fixing the code
- Skipping an applicable surface check because "it worked in dev mode"

**Correct pattern:**
```
# Run the repository-defined commands for the changed surface, in the order the repository defines.
# Select them from /home/opencode/.config/opencode/instructions/validation-mandate.md.
# Omit any check whose command the repository does not define, and report it as unavailable.
# → Only after every applicable check passes: git commit
```

---

## OpenCode-Specific Manual Steps

OpenCode does not support Claude Code's hook system. The following checks must be performed manually after a code edit batch, applying each only when the repository defines the corresponding command:

### After Writing or Editing Code

- **Format the file.** Run the repository's own formatter command for the changed files, when one is defined; omit and report it when the repository defines none.
- **Run the type checker.** Run the repository's own type-check command after every edit batch, when one is defined — catch type errors early, not at commit time. Omit and report a repository that defines no type checker.
- **Check for `console.log` statements.** Search changed files for `console.log` and remove any debugging output:
  ```
  grep -n "console\.log" <file>
  ```
  Debug logging belongs behind a proper logger; `console.log` in production source is a violation.

### Before Committing

- **Preserve existing security invariants.** When the changed surface is observably security-sensitive (canonical owner: `/home/opencode/.config/opencode/skills/security-review/SKILL.md`), run the security review and verify the C01-C08 gates manually — no automated pre-commit hook will stop you. For non-security changes, confirm the existing security invariants under ordinary correctness review.
- **Verify no secrets in code.** Scan the diff for hardcoded keys, tokens, or passwords:
  ```
  git diff --cached | grep -E '(api[_-]?key|secret|password|token)\s*[:=]\s*['"'"'"]'
  ```
- **Run the tests for the changed surface.** Run the repository's own test command when one is defined; omit and report it otherwise. Don't rely on CI to catch what you can verify locally.

**Violation examples:**
- Pushing code that hasn't been formatted because "the hook would have done it"
- Committing `console.log` statements left from debugging
- Expecting a pre-commit hook to catch type errors — OpenCode has no hooks; it's your responsibility

---

## Build Troubleshooting

When a build or type check fails, follow this protocol before changing any code:

### Protocol

1. **Read the error.** Copy the full error message — type error, build failure, or test failure. What exactly is expected vs. actual?
2. **Run in isolation.** Reproduce the failure with the same command. If it's a type error, run the repository's own type-check command on just the failing file.
3. **Fix incrementally.** Fix one error at a time. Run the check after each fix to confirm it resolves without introducing new errors.
4. **Verify the fix.** After all fixes, re-run the repository-defined verification for the changed surface.

### Build Fix Rules

| DO (PASS) | DON'T (FAIL) |
|-----------|--------------|
| Fix type errors with correct types | Refactor code or change architecture |
| Add missing imports | Add new features or change behavior |
| Fix syntax errors | Use `any` type or `@ts-ignore` to silence errors |
| Make minimal changes | Change business logic |
| Run the repository's type/build check after each fix | Batch multiple fixes without verification |

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

- **No commit without verification.** Run the repository-selected verification for the changed surface (see `/home/opencode/.config/opencode/instructions/validation-mandate.md`); every applicable check is a blocking gate. A check whose command the repository does not define is omitted and reported, never invented.
- **No `console.log` in committed code.** Grep for it before committing; production source must use a proper logger.
- **No type suppression without justification.** `@ts-ignore` and `any` require inline comments explaining why a proper fix isn't possible.
- **Build failures block all other work.** A broken build is the top priority — fix it before writing new code.
