---
name: build-fix
description: Diagnose and resolve build errors across languages with minimal, surgical changes — no refactoring, no architecture changes. Covers TypeScript/JavaScript, Rust, Go, C++, Java, and Kotlin. Use when a build fails (`npm run build`, `cargo build`, `go build`, `cmake --build`, `mvn compile`, `gradle build`), when type errors block development, or when dependency resolution fails.
---

# Build Error Resolution

**Purpose:** Diagnose and fix build errors with minimal, surgical changes. No refactoring. No architectural modifications. Get the build passing and move on.

## When to Use This Skill

**Trigger conditions:**
- `npm run build` / `npx tsc --noEmit` fails with TypeScript/JavaScript errors
- `cargo build` / `cargo check` fails with Rust compilation errors
- `go build ./...` fails with Go compilation errors
- `cmake --build build` fails with C++ errors
- `./mvnw compile` / `./gradlew build` fails with Java errors
- `./gradlew build` fails with Kotlin errors
- Dependency resolution errors, module not found, import/export issues
- Type errors blocking development

**Do NOT use this skill for:**
- Code refactoring or style improvements
- Architectural changes or redesign
- Adding new features
- Fixing failing tests (unless build failure is the root cause)
- Security issues

## Language Dispatch Table

Choose the reference file matching the file extension of the failing source:

| File Extension(s) | Language | Reference |
|---|---|---|
| `.ts`, `.tsx`, `.js`, `.jsx` | TypeScript / JavaScript | [`references/ts-js.md`](file:///home/opencode/.config/opencode/skills/build-fix/references/ts-js.md) |
| `.rs` | Rust | [`references/rust.md`](file:///home/opencode/.config/opencode/skills/build-fix/references/rust.md) |
| `.go` | Go | [`references/go.md`](file:///home/opencode/.config/opencode/skills/build-fix/references/go.md) |
| `.cpp`, `.hpp`, `.cc`, `.hh`, `.cxx`, `.hxx`, `.c`, `.h` | C++ / C | [`references/cpp.md`](file:///home/opencode/.config/opencode/skills/build-fix/references/cpp.md) |
| `.java` | Java | [`references/java.md`](file:///home/opencode/.config/opencode/skills/build-fix/references/java.md) |
| `.kt`, `.kts` | Kotlin | [`references/kotlin.md`](file:///home/opencode/.config/opencode/skills/build-fix/references/kotlin.md) |

## Workflow

1. **Identify the language** — determine which build tool and language are failing
2. **Load the matching reference** — use the dispatch table above to find the correct reference file
3. **Collect and categorize errors** — run diagnostic commands from the reference, capture all errors, and categorize by type (type errors, import/export, configuration, dependency). Prioritize: fix blocking build errors first, then type errors, then warnings.
4. **Apply minimal fixes** — fix one error at a time, verify after each change. For each error: understand the root cause → find the minimal fix → verify it doesn't break other code → iterate.
5. **Verify the build passes** — re-run the build command after all fixes, then run the test suite

## Core Principles

- **Surgical fixes only** — change only what's needed to fix the error
- **No refactoring** — don't reorganize, rename, or restructure unrelated code
- **No architecture changes** — don't redesign data models or control flow
- **Fix root cause** — don't suppress symptoms with type assertions, `any`, `@SuppressWarnings`, `#[allow(...)]`, or `//nolint`
- **Verify after each fix** — re-run the build to confirm the error is resolved and no new errors were introduced
- **Stop after 3 failed attempts** — if the same error persists, report and escalate

## Output Format

**After each fix** — report the change:

```text
[FIXED] src/components/MarketCard.tsx:45
Error: Parameter 'market' implicitly has an 'any' type
Fix: Added type annotation `market: Market`
Remaining errors: 3
```

**Final summary** — after all errors are resolved:

```text
Build Status: PASSING / FAILING
Language: [TypeScript | Rust | Go | C++ | Java | Kotlin]
Errors Fixed: N
Files Modified: [list]
Remaining Issues: [list or "none"]
```

## Validation Checklist

Before reporting completion, verify:

- [ ] Build command runs cleanly with zero errors
- [ ] No suppression comments added (`@ts-ignore`, `@ts-expect-error`, `#[allow(...)]`, `@SuppressWarnings`, `# noqa`, `//nolint`) without explicit approval
- [ ] Each fix is minimal — only lines directly related to the error were changed
- [ ] No refactoring or restructuring of unrelated code
- [ ] Tests still pass (run the test suite after all fixes)
- [ ] Output format is followed for each fix reported

## References

- **This skill's reference files:**
  - [`references/ts-js.md`](file:///home/opencode/.config/opencode/skills/build-fix/references/ts-js.md) — TypeScript/JavaScript build errors, type errors, ESLint violations
  - [`references/rust.md`](file:///home/opencode/.config/opencode/skills/build-fix/references/rust.md) — Rust compilation, borrow-checker, and clippy errors
  - [`references/go.md`](file:///home/opencode/.config/opencode/skills/build-fix/references/go.md) — Go build errors, vet issues, and staticcheck violations
  - [`references/cpp.md`](file:///home/opencode/.config/opencode/skills/build-fix/references/cpp.md) — C++ compilation, CMake issues, and linker errors
  - [`references/java.md`](file:///home/opencode/.config/opencode/skills/build-fix/references/java.md) — Java Maven/Gradle build errors and dependency issues
  - [`references/kotlin.md`](file:///home/opencode/.config/opencode/skills/build-fix/references/kotlin.md) — Kotlin Gradle build errors and detekt violations
- **Related skills:** `support-debugger` for root cause analysis when fixes keep failing
