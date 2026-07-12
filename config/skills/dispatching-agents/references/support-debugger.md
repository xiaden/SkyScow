# Support-Debugger

Dispatch Support-Debugger to diagnose test failures, runtime errors, lint errors, and unexpected behavior.

## When to Dispatch

**Dispatch when:**
- Tests fail and the root cause is unclear after a quick scan of the affected files
- A runtime error occurs and the stack trace is ambiguous
- Lint errors appear that aren't explained by the immediate diff
- Observed behavior contradicts expectations and the cause is non-obvious
- Exec-Manager hits a blocker after 3+ failed fix attempts on the same issue

**Do NOT dispatch when:**
- The error is an obvious typo or missing import — fix it directly
- The test failure is clearly caused by the code you just wrote
- You haven't read the affected files yet — do your own investigation first
- A simple `aft_search` or `read` would answer the question

## Dispatch Template

Fill in every field. Use `N/A` only when the field is genuinely unknown.

```
Diagnose this failure:

Context files:
- {plan file being executed, if applicable}
- {contracts file, if applicable}
- {any other relevant context files}

failure:
  type: TEST_FAILURE | RUNTIME_ERROR | LINT_ERROR | UNEXPECTED_BEHAVIOR
  symptom: "{describe what went wrong}"
  errorMessage: "{full error text}"
  location:
    file: "{file path if known}"
    line: {line number if known}
  observedBehavior: "{what actually happened}"     # for UNEXPECTED_BEHAVIOR only
  expectedBehavior: "{what should have happened}"  # for UNEXPECTED_BEHAVIOR only
```

## Required Fields

| Field | Description | Required |
|-------|-------------|----------|
| `type` | One of `TEST_FAILURE`, `RUNTIME_ERROR`, `LINT_ERROR`, `UNEXPECTED_BEHAVIOR` | Always |
| `symptom` | Human-readable description of what went wrong | Always |
| `errorMessage` | Full error text, copy-pasted verbatim from logs | Always |
| `location.file` | File path if known | When known |
| `location.line` | Line number if known | When known |
| `observedBehavior` | What actually happened | `UNEXPECTED_BEHAVIOR` only |
| `expectedBehavior` | What should have happened | `UNEXPECTED_BEHAVIOR` only |

## Expected Output

| Field | Description |
|-------|-------------|
| `rootCause` | Explanation of what caused the failure |
| `fixComplexity` | One of `SIMPLE`, `NEEDS_PLAN`, `INCONCLUSIVE` |
| `suggestedFix` | Concrete fix suggestion (present only when complexity is `SIMPLE`) |

## Routing After Diagnosis

| Complexity | Meaning | Action |
|------------|---------|--------|
| `SIMPLE` | Root cause clear, fix scoped to 1–2 files | Spawn Exec-Fixer with `suggestedFix`, run lint, run tests, then full QA review |
| `NEEDS_PLAN` | Fix requires coordinated changes across 3+ files or layers | Spawn Exec-Planner (AMEND) with `rootCause`, re-execute affected phases, then QA review |
| `INCONCLUSIVE` | Debugger couldn't determine root cause | Escalate to Director with full debugger report. Do NOT attempt random fixes. |

## Dispatch Examples

### TEST_FAILURE

```
Diagnose this failure:

Context files:
- artifacts/plans/pending/TASK-A-refactor-auth.md
- src/auth/service.ts
- src/auth/__tests__/service.test.ts
- src/auth/middleware.ts

failure:
  type: TEST_FAILURE
  symptom: "Auth service unit tests fail after refactoring token validation into a separate module. 8 of 12 tests in service.test.ts fail with 'token not found' errors, but the token is being passed in the test setup."
  errorMessage: "FAIL src/auth/__tests__/service.test.ts
  ● AuthService › validateToken › returns user for valid token
    TokenNotFoundError: token not found
      45 |     const result = await service.validateToken(testToken);
      46 |     expect(result.userId).toBe('user-1');
    ..."
  location:
    file: "src/auth/__tests__/service.test.ts"
    line: 45
```

### RUNTIME_ERROR

```
Diagnose this failure:

Context files:
- src/workflows/order-processing.ts
- src/services/payment-gateway.ts
- src/models/order.ts

failure:
  type: RUNTIME_ERROR
  symptom: "Order processing workflow crashes at the payment step. The payment gateway returns a 500, but the error handler in the workflow doesn't catch it."
  errorMessage: "TypeError: Cannot read properties of undefined (reading 'id')
    at PaymentGateway.processCharge (src/services/payment-gateway.ts:89:35)
    at OrderWorkflow.execute (src/workflows/order-processing.ts:142:22)
    at process.<anonymous> (src/workflows/order-processing.ts:200:5)"
  location:
    file: "src/services/payment-gateway.ts"
    line: 89
```

### LINT_ERROR

```
Diagnose this failure:

Context files:
- src/components/DataTable.tsx
- src/types/data-table.ts
- src/hooks/use-data-table.ts

failure:
  type: LINT_ERROR
  symptom: "TypeScript reports 'Property rows does not exist on type DataTableProps'. The type definition does include 'rows', and this compiled fine before refactoring. The error appeared after renaming IDataTableProps to DataTableProps."
  errorMessage: "src/components/DataTable.tsx:34:15 - error TS2339: Property 'rows' does not exist on type 'DataTableProps'.
  34   const { rows, columns, pagination } = props;
                   ~~~~"
  location:
    file: "src/components/DataTable.tsx"
    line: 34
```

### UNEXPECTED_BEHAVIOR

```
Diagnose this failure:

Context files:
- src/services/notification-service.ts
- src/services/email-provider.ts
- src/config/notification-config.ts

failure:
  type: UNEXPECTED_BEHAVIOR
  symptom: "Notification service sends emails to users who have opted out. The opt-out check exists in the code and passes unit tests, but in production, opted-out users still receive emails."
  errorMessage: "N/A — no error is thrown. Emails are sent successfully to opted-out users."
  location:
    file: "src/services/notification-service.ts"
    line: N/A
  observedBehavior: "User with optOut=true in the database received 3 notification emails in the past hour."
  expectedBehavior: "User with optOut=true should receive zero emails. The sendEmail method should return early after checking the opt-out flag."
```

## Common Dispatch Mistakes

| Mistake | Why it fails | Fix |
|---------|-------------|-----|
| Vague symptom: "tests fail" | Debugger doesn't know scope or pattern | Specify which tests, how many, and what they share |
| Truncated error: "...45 more lines" | Debugger can't see the full stack | Copy-paste the entire error |
| Missing context files | Debugger wastes turns asking for files | List every file you've touched or suspect |
| No `observedBehavior` / `expectedBehavior` for UNEXPECTED_BEHAVIOR | Debugger can't diagnose what "wrong" means | Always include both fields |
| Dispatching for obvious typos or missing imports | Wastes Debugger context on trivial fixes | Fix typos and missing imports directly |

## Dispatch Decision Tree

```
Failure encountered
├─ Error message clearly points to a typo or missing import?
│  └─ Fix directly (no dispatch)
├─ Error is in code you just wrote?
│  └─ Read the affected files yourself first
│     ├─ Cause is obvious after reading → Fix directly
│     └─ Cause is unclear → Dispatch Support-Debugger
├─ Error is pre-existing (not from your changes)?
│  └─ Dispatch Support-Debugger (don't guess at pre-existing issues)
└─ Same fix has failed 3+ times?
   └─ Dispatch Support-Debugger (you're in a loop)
```
