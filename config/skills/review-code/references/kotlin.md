# Kotlin Code Review

**Purpose:** Language-specific code review checklist for Kotlin — security, clean architecture, coroutines, Compose, Android lifecycle, and Kotlin idioms.
**Scope:** All `.kt` and `.kts` files including Android apps, KMP modules, Compose Multiplatform, and server-side Kotlin.

## Verification Commands

Run the repository's own commands for the changed surface; do not default to a toolchain the repository does not have. Select the evidence from the surface-to-evidence table in `config/instructions/validation-mandate.md`:
- Run the repository's own type-check / compile command, when defined
- Run the repository's own lint command, when defined
- Run the repository's own formatter check, when defined
- Run the repository's own test command for the changed surface, when defined

Omit any check the repository does not define and report it as unavailable rather than inventing a command. Report gate evidence using the labels in `config/skills/ci-lint-test-gates/SKILL.md`.

### Quick-Scan
```bash
grep -rn '!!' src/ --include="*.kt"                    # Non-null assertions — potential crashes
grep -rn "GlobalScope" src/ --include="*.kt"            # Unstructured coroutine scope
grep -rn "Dispatchers.Main" src/ --include="*.kt"       # Check for IO on main thread
grep -rn "CancellationException" src/ --include="*.kt"  # Verify not swallowed
```

## [CRITICAL] Security

Apply these checks when the changed surface is observably security-sensitive; the applicability owner is `config/skills/security-review/SKILL.md`. Non-security changes preserve existing security invariants under ordinary correctness review; any CRITICAL or HIGH issue found, by any path, still blocks merge.

- **Exported component exposure** — Activities, services, or receivers exported without proper guards
- **Insecure crypto/storage** — Homegrown crypto, plaintext secrets, or weak keystore usage
- **Unsafe WebView/network config** — JavaScript bridges, cleartext traffic, permissive trust settings
- **Sensitive logging** — Tokens, credentials, PII, or secrets emitted to logs

If any CRITICAL security issue is present, stop and escalate to `security-reviewer`.

## [CRITICAL] Architecture

- **Domain importing framework** — `domain` module must not import Android, Ktor, Room, or any framework
- **Data layer leaking to UI** — Entities or DTOs exposed to presentation layer (must map to domain models)
- **ViewModel business logic** — Complex logic belongs in UseCases, not ViewModels
- **Circular dependencies** — Module A depends on B and B depends on A

## [HIGH] Coroutines & Flows

- **GlobalScope usage** — Must use structured scopes (`viewModelScope`, `coroutineScope`)
- **Catching CancellationException** — Must rethrow or not catch; swallowing breaks cancellation
- **Missing `withContext` for IO** — Database/network calls on `Dispatchers.Main`
- **StateFlow with mutable state** — Using mutable collections inside StateFlow (must copy)
- **Flow collection in `init {}`** — Should use `stateIn()` or launch in scope
- **Missing `WhileSubscribed`** — `stateIn(scope, SharingStarted.Eagerly)` when `WhileSubscribed` is appropriate

## [HIGH] Compose

- **Unstable parameters** — Composables receiving mutable types cause unnecessary recomposition. **Impact: 2-5x unnecessary recompositions.**
- **Side effects outside LaunchedEffect** — Network/DB calls must be in `LaunchedEffect` or ViewModel
- **NavController passed deep** — Pass lambdas instead of `NavController` references
- **Missing `key()` in LazyColumn** — Items without stable keys cause poor performance
- **`remember` with missing keys** — Computation not recalculated when dependencies change

## [MEDIUM] Kotlin Idioms

- **`!!` usage** — Non-null assertion; prefer `?.`, `?:`, `requireNotNull`, or `checkNotNull`
- **`var` where `val` works** — Prefer immutability
- **Java-style patterns** — Static utility classes (use top-level functions), getters/setters (use properties)
- **String concatenation** — Use string templates `"Hello $name"` instead of `"Hello " + name`
- **`when` without exhaustive branches** — Sealed classes/interfaces should use exhaustive `when`
- **Mutable collections exposed** — Return `List` not `MutableList` from public APIs

## [MEDIUM] Android Specific

- **Context leaks** — Storing `Activity` or `Fragment` references in singletons/ViewModels
- **Missing ProGuard rules** — Serialized classes without `@Keep` or ProGuard rules
- **Hardcoded strings** — User-facing strings not in `strings.xml` or Compose resources
- **Missing lifecycle handling** — Collecting Flows in Activities without `repeatOnLifecycle`

## Anti-Patterns

| Pattern | Severity | What to Look For |
|---------|----------|------------------|
| `GlobalScope.launch` / `GlobalScope.async` | HIGH | Unbounded coroutine — use `viewModelScope` or `coroutineScope` |
| `!!` on nullable | HIGH | Potential NPE — use `?.`, `?:`, or `requireNotNull` |
| Catching `CancellationException` | HIGH | Coroutine cancellation broken — rethrow or don't catch |
| `Dispatchers.Main` for DB/network | HIGH | UI thread blocking — use `withContext(Dispatchers.IO)` |
| `MutableList` in StateFlow | HIGH | Compose won't recompose — use immutable copy |
| Domain importing Android/Ktor | CRITICAL | Clean architecture violation — move to data/platform layer |
| `remember` without keys | MEDIUM | Stale computation — add dependency keys |
| `NavController` passed deep | MEDIUM | Tight coupling — pass lambdas instead |
| Exported component without guard | CRITICAL | Security vulnerability — add permission or intent filter |
| `Activity` stored in ViewModel | MEDIUM | Memory leak — use `ApplicationContext` or clear on `onCleared` |

## Review Output Format

For each issue:
```text
[CRITICAL] Domain module imports Android framework
File: domain/src/main/kotlin/com/app/domain/UserUseCase.kt:3
Issue: `import android.content.Context` — domain must be pure Kotlin with no framework dependencies.
Fix: Move Context-dependent logic to data or platforms layer. Pass data via repository interface.
```

## Review Summary

End every review with:
```
## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0     | pass   |
| HIGH     | 1     | block  |
| MEDIUM   | 2     | info   |
| LOW      | 0     | note   |

Verdict: BLOCK — HIGH issues must be fixed before merge.
```

## Approval Criteria

- **Approve**: No CRITICAL or HIGH issues
- **Block**: Any CRITICAL or HIGH issues — must fix before merge

## Repository Commands

Discover and run the repository's own commands before manual review — do not assume ECC or any specific toolchain is present:
- Lint — run the repository's own lint command for the changed files, when defined
- Format — run the repository's own formatter command for the changed files, when defined
- Tests — run the repository's own test command for the changed surface, when defined
- Coverage — verify against the repository-defined coverage gate when one exists; impose no universal threshold (see `config/instructions/validation-mandate.md`)
- Security — for observably security-sensitive surfaces, run the security review (canonical owner: `config/skills/security-review/SKILL.md`); non-security changes preserve existing security invariants under ordinary correctness review

Omit and report any command the repository does not define.
