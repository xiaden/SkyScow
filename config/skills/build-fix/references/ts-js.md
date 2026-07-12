# TypeScript / JavaScript Build Error Resolver

Fix TypeScript compilation errors, build failures, and dependency issues with minimal, surgical changes.

## Table of Contents

- [Diagnostic Commands](#diagnostic-commands)
- [Error Collection Workflow](#error-collection-workflow)
- [Common Fix Patterns](#common-fix-patterns)
- [Configuration Errors](#configuration-errors)
- [Dependency Issues](#dependency-issues)
- [Fix Strategy](#fix-strategy)
- [Minimal Diff Strategy](#minimal-diff-strategy)
- [Output Format](#output-format)
- [Quick Reference Commands](#quick-reference-commands)
- [Key Principles](#key-principles)
- [Stop Conditions](#stop-conditions)

## Diagnostic Commands

```bash
# TypeScript type check (no emit)
npx tsc --noEmit

# TypeScript with pretty output, all errors
npx tsc --noEmit --pretty --incremental false

# Check specific file
npx tsc --noEmit path/to/file.ts

# ESLint check
npx eslint . --ext .ts,.tsx,.js,.jsx

# Production build
npm run build

# Clear cache and rebuild
rm -rf .next node_modules/.cache && npm run build
```

## Error Collection Workflow

Before fixing, categorize and prioritize all errors:

```text
a) Run full type check
   - npx tsc --noEmit --pretty
   - Capture ALL errors, not just first

b) Categorize errors by type
   - Type inference failures       — implicit any, generic constraints
   - Missing type definitions      — .d.ts files, @types packages
   - Import/export errors          — module not found, wrong exports
   - Configuration errors          — tsconfig.json, build tool config
   - Dependency issues             — version conflicts, missing packages

c) Prioritize by impact
   - Blocking build: Fix first
   - Type errors: Fix in order they appear
   - Warnings: Fix if time permits (don't block build on warnings)
```

## Common Fix Patterns

| Error | Cause | Fix |
|-------|-------|-----|
| `Parameter 'x' implicitly has an 'any' type` | Missing type annotation with `noImplicitAny` | Add explicit type: `function add(x: number, y: number): number` |
| `Object is possibly 'undefined'` | Accessing property on nullable value | Use optional chaining `user?.name` or add null check |
| `Property 'age' does not exist on type 'User'` | Missing property in type definition | Add property to interface/type, mark optional if needed |
| `Cannot find module '@/lib/utils'` | Wrong path alias or missing package | Fix tsconfig `paths`, use relative import, or install package |
| `Type 'string' is not assignable to type 'number'` | Type mismatch | Parse/convert value: `parseInt("30", 10)` or change expected type |
| `Argument of type 'X' is not assignable to parameter of type 'Y'` | Wrong argument type | Fix argument type or add type guard/narrowing |
| `Type 'X' is not assignable to type 'Y'` (union) | Missing union member or wrong type | Add to union, narrow with type guard, or fix assignment |
| `Cannot find name 'X'` | Missing import or undeclared variable | Add import statement or declare variable |
| `Module '"X"' has no exported member 'Y'` | Wrong import name or outdated package | Fix import name, check package version, or update types |
| `Property 'X' is private and only accessible within class 'Y'` | Accessing private member | Use public API, add accessor method, or change visibility if appropriate |
| `Expected N arguments, but got M` | Wrong function call arity | Fix call to match function signature |
| `Type 'X' does not satisfy the constraint 'Y'` | Generic constraint violation | Ensure type argument satisfies the constraint |

## Null/Undefined Patterns

```typescript
// ERROR: Object is possibly 'undefined'
const name = user.name.toUpperCase()

// FIX 1: Optional chaining
const name = user?.name?.toUpperCase()

// FIX 2: Null check with default
const name = user?.name ? user.name.toUpperCase() : ''

// FIX 3: Non-null assertion (last resort — only if you know it's safe)
const name = user.name!.toUpperCase()
```

## Import/Module Errors

```typescript
// ERROR: Cannot find module '@/lib/utils'
import { formatDate } from '@/lib/utils'

// FIX 1: Verify tsconfig.json paths
// { "compilerOptions": { "paths": { "@/*": ["./src/*"] } } }

// FIX 2: Use relative import
import { formatDate } from '../lib/utils'

// FIX 3: Install missing package
// npm install <package-name>
// npm install -D @types/<package-name>
```

## Configuration Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `Unknown compiler option 'X'` | Typo in tsconfig.json or unsupported option | Fix option name or remove it |
| `File is not listed in 'include'` | File outside tsconfig scope | Add path to `include` array or move file |
| `Cannot write file because it would overwrite input` | `outDir` same as source dir | Set `outDir` to a different directory |
| `ESLint: Parsing error` | ESLint can't parse TS syntax | Configure `@typescript-eslint/parser` in ESLint config |

## Dependency Issues

| Error | Cause | Fix |
|-------|-------|-----|
| `Cannot find module 'X'` | Missing package | `npm install X` or `npm install -D @types/X` |
| `Could not find a declaration file for module 'X'` | Missing type definitions | `npm install -D @types/X` or add `declare module 'X'` |
| `Module '"X"' has no default export` | Named-only exports | Change to `import { Y } from 'X'` or `import * as X from 'X'` |
| Version conflict in lockfile | Incompatible peer dependencies | `npm dedupe` or resolve version constraints |

## Fix Strategy

For each error, follow this cycle:

```text
1. Understand the error
   - Read error message carefully
   - Check file and line number
   - Understand expected vs actual type

2. Find minimal fix
   - Add missing type annotation
   - Fix import statement
   - Add null check
   - Use type assertion (last resort only)

3. Verify fix doesn't break other code
   - Run tsc again after each fix
   - Check related files for type impact
   - Ensure no new errors introduced

4. Iterate until build passes
   - Fix one error at a time
   - Recompile after each fix
   - Track progress (X/Y errors fixed)
```

## Minimal Diff Strategy

**CRITICAL: Make smallest possible changes.**

### DO:
- Add type annotations where missing
- Add null checks where needed
- Fix imports/exports
- Add missing dependencies
- Update type definitions
- Fix configuration files

### DON'T:
- Refactor unrelated code
- Change architecture
- Rename variables/functions (unless causing error)
- Add new features
- Change logic flow (unless fixing error)
- Optimize performance
- Improve code style

## Output Format

**After each fix:**

```text
[FIXED] src/components/MarketCard.tsx:45
Error: Parameter 'market' implicitly has an 'any' type
Fix: Added type annotation `market: Market`
Remaining errors: 3
```

**Final summary:**

```markdown
# Build Error Resolution Report

**Build Target:** TypeScript check / Next.js build / ESLint
**Initial Errors:** X
**Errors Fixed:** Y
**Build Status:** PASSING / FAILING

## Errors Fixed

### 1. [Error Category]
**Location:** `src/components/MarketCard.tsx:45`
**Error Message:** Parameter 'market' implicitly has an 'any' type.
**Root Cause:** Missing type annotation on function parameter
**Fix Applied:**
- function formatMarket(market) {
+ function formatMarket(market: Market) {
**Lines Changed:** 1
**Impact:** None — type safety improvement only
```

```text
Build Status: SUCCESS/FAILED | Errors Fixed: N | Files Modified: list
```

## Quick Reference Commands

```bash
# Check for errors
npx tsc --noEmit

# Build Next.js
npm run build

# Clear cache and rebuild
rm -rf .next node_modules/.cache && npm run build

# Install missing dependencies
npm install

# Fix ESLint issues automatically
npx eslint . --fix
```

## Key Principles

- **Surgical fixes only** — change only what's needed to fix the error
- **Never** use `any` type to silence errors without explicit approval
- **Never** use `@ts-ignore` or `@ts-expect-error` to suppress errors without approval
- **Never** refactor unrelated code
- **Always** run `npx tsc --noEmit` after each fix to verify
- Fix root cause over suppressing symptoms

## Stop Conditions

Stop and report if:
- Same error persists after 3 fix attempts
- Fix introduces more errors than it resolves
- Error requires architectural changes beyond scope
- Dependency conflict requires major version upgrade
