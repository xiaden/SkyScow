# Java Code Review

**Purpose:** Language-specific code review checklist for Java — security, Spring Boot architecture, JPA/database, concurrency, testing, and Java idioms.
**Scope:** All `.java` files including Spring Boot services, JPA entities, controllers, repositories, and tests. Supports Maven and Gradle projects.

## Verification Commands

First, determine the build tool by checking for `pom.xml` (Maven) or `build.gradle`/`build.gradle.kts` (Gradle).

### Maven
```bash
./mvnw compile -q 2>&1 || mvn compile -q 2>&1
./mvnw verify -q 2>&1 || mvn verify -q 2>&1
./mvnw checkstyle:check 2>&1 || echo "checkstyle not configured"
./mvnw spotbugs:check 2>&1 || echo "spotbugs not configured"
./mvnw dependency-check:check 2>&1 || echo "dependency-check not configured"
./mvnw test 2>&1
```

### Gradle
```bash
./gradlew compileJava 2>&1
./gradlew check 2>&1
./gradlew test 2>&1
```

### Quick-Scan (Both)
```bash
grep -rn "@Autowired" src/main/java --include="*.java"
grep -rn "FetchType.EAGER" src/main/java --include="*.java"
grep -rn "catch (Exception" src/main/java --include="*.java"
grep -rn "\.get()" src/main/java --include="*.java"   # Optional.get() without isPresent
```

## [CRITICAL] Security

- **SQL injection**: String concatenation in `@Query` or `JdbcTemplate` — use bind parameters (`:param` or `?`)
- **Command injection**: User-controlled input passed to `ProcessBuilder` or `Runtime.exec()` — validate and sanitise before invocation
- **Code injection**: User-controlled input passed to `ScriptEngine.eval(...)` — avoid executing untrusted scripts
- **Path traversal**: User-controlled input passed to `new File(userInput)`, `Paths.get(userInput)` without validation
- **Hardcoded secrets**: API keys, passwords, tokens in source — must come from environment or secrets manager
- **PII/token logging**: `log.info(...)` calls near auth code that expose passwords or tokens
- **Missing `@Valid`**: Raw `@RequestBody` without Bean Validation
- **CSRF disabled without justification**: Document why if disabled for stateless JWT APIs

If any CRITICAL security issue is found, stop and escalate to `security-reviewer`.

## [CRITICAL] Error Handling

- **Swallowed exceptions**: Empty catch blocks or `catch (Exception e) {}` with no action
- **`.get()` on Optional**: Calling `repository.findById(id).get()` without `.isPresent()` — use `.orElseThrow()`
- **Missing `@RestControllerAdvice`**: Exception handling scattered across controllers
- **Wrong HTTP status**: Returning `200 OK` with null body instead of `404`, or missing `201` on creation

## [HIGH] Spring Boot Architecture

- **Field injection**: `@Autowired` on fields — constructor injection is required
- **Business logic in controllers**: Controllers must delegate to the service layer immediately
- **`@Transactional` on wrong layer**: Must be on service layer, not controller or repository
- **Missing `@Transactional(readOnly = true)`**: Read-only service methods must declare this
- **Entity exposed in response**: JPA entity returned directly from controller — use DTO or record projection

## [HIGH] JPA / Database

- **N+1 query problem**: `FetchType.EAGER` on collections — use `JOIN FETCH` or `@EntityGraph`. **Impact: 10-100x slower on large datasets.**
- **Unbounded list endpoints**: Returning `List<T>` without `Pageable` and `Page<T>`
- **Missing `@Modifying`**: Any `@Query` that mutates data requires `@Modifying` + `@Transactional`
- **Dangerous cascade**: `CascadeType.ALL` with `orphanRemoval = true` — confirm intent is deliberate

## [MEDIUM] Concurrency and State

- **Mutable singleton fields**: Non-final instance fields in `@Service` / `@Component` are a race condition
- **Unbounded `@Async`**: `CompletableFuture` or `@Async` without a custom `Executor`
- **Blocking `@Scheduled`**: Long-running scheduled methods that block the scheduler thread

## [MEDIUM] Java Idioms and Performance

- **String concatenation in loops**: Use `StringBuilder` or `String.join`
- **Raw type usage**: Unparameterised generics (`List` instead of `List<T>`)
- **Missed pattern matching**: `instanceof` check followed by explicit cast — use pattern matching (Java 16+)
- **Null returns from service layer**: Prefer `Optional<T>` over returning null

## [MEDIUM] Testing

- **`@SpringBootTest` for unit tests**: Use `@WebMvcTest` for controllers, `@DataJpaTest` for repositories
- **Missing Mockito extension**: Service tests must use `@ExtendWith(MockitoExtension.class)`
- **`Thread.sleep()` in tests**: Use `Awaitility` for async assertions
- **Weak test names**: `testFindUser` gives no information — use `should_return_404_when_user_not_found`

## Anti-Patterns

| Pattern | Severity | What to Look For |
|---------|----------|------------------|
| `@Autowired` field injection | HIGH | `@Autowired private X x;` — use constructor injection |
| `.get()` on Optional | CRITICAL | `.get()` without `.isPresent()` — use `.orElseThrow()` |
| Entity returned from controller | HIGH | JPA entity in `@RestController` response — map to DTO |
| `FetchType.EAGER` on collections | HIGH | Eager collections — prefer `LAZY` + `JOIN FETCH` |
| `catch (Exception e) {}` | CRITICAL | Swallowed exceptions — always log or rethrow |
| `@Transactional` on controller | HIGH | Transaction boundary wrong — move to service layer |
| `@SpringBootTest` for unit tests | MEDIUM | Heavy context load — use `@WebMvcTest` or `@DataJpaTest` |
| `Thread.sleep()` in tests | MEDIUM | Flaky timing — use `Awaitility` |
| Raw types (`List` not `List<T>`) | MEDIUM | Lost type safety — add generic parameter |

## Review Output Format

For each issue:
```text
[CRITICAL] Field injection in OrderService
File: src/main/java/com/app/service/OrderService.java:15
Issue: `@Autowired private PaymentService paymentService` — field injection hides dependencies
Fix: Use constructor injection: `public OrderService(PaymentService paymentService) { this.paymentService = paymentService; }`
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
- **Warning**: MEDIUM issues only
- **Block**: CRITICAL or HIGH issues found

## ECC Tools

Prefer ECC tooling for automated checks before manual review:
- `lint-check` — detects linter (checkstyle, spotbugs) and returns command
- `security-audit` — scans for secrets and dependency vulnerabilities
- `run-tests` — detects build tool and runs test suite
- `dependency-analyzer` — lists outdated/vulnerable dependencies

For detailed patterns and examples:
- **Spring Boot**: See `skill: springboot-patterns`
- **Quarkus**: See `skill: quarkus-patterns`
