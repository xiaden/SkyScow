---
description: Fix build and type errors with minimal changes
argument-hint: "<path or description of the build issue>"
---

# Build Fix

Fix build and type errors with minimal changes: $ARGUMENTS

Load the build-fix skill:

```
skill(name="build-fix")
```

## Your Task

1. **Discover the build command**: read the repository's declared scripts/config and run its build/type-check command; the build-fix skill's dispatch table maps language to command, and repository-defined scripts outrank generic fallbacks (`npm`/`npx`)
2. **Collect all errors**
3. **Fix errors one by one** with minimal changes
4. **Verify each fix** doesn't introduce new errors
5. **Run final check** to confirm all errors resolved

## Approach

### DO:
- PASS: Fix type errors with correct types
- PASS: Add missing imports
- PASS: Fix syntax errors
- PASS: Make minimal changes
- PASS: Preserve existing behavior
- PASS: Re-run the repository's build/type-check command after each change

### DON'T:
- FAIL: Refactor code
- FAIL: Add new features
- FAIL: Change architecture
- FAIL: Use `any` type (unless absolutely necessary)
- FAIL: Add `@ts-ignore` comments
- FAIL: Change business logic

## Common Error Fixes

| Error | Fix |
|-------|-----|
| Type 'X' is not assignable to type 'Y' | Add correct type annotation |
| Property 'X' does not exist | Add property to interface or fix property name |
| Cannot find module 'X' | Install package or fix import path |
| Argument of type 'X' is not assignable | Cast or fix function signature |
| Object is possibly 'undefined' | Add null check or optional chaining |

## Verification Steps

After fixes, run the repository-defined checks for the changed surface (do not assume `npm`/`npx` commands):
1. The repository's build/type-check command - should show 0 errors
2. The repository's build or release command - should succeed
3. The repository's test command, when one exists - tests should still pass; if none exists, report that fact instead of assuming `npm test`

---

**IMPORTANT**: Focus on fixing errors only. No refactoring, no improvements, no architectural changes. Get the build green with minimal diff.
