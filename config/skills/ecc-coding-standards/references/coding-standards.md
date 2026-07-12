# Coding Standards

## When This Applies

- While writing any new source code
- During code review — reviewer checks compliance
- When refactoring existing code — apply these standards to touched files
- When onboarding to a project — these are the baseline expectations

## Rules

### Immutability (CRITICAL)

Always create new objects; never mutate existing state.

**Violation:**
```javascript
function updateUser(user, name) {
  user.name = name  // MUTATION — caller's object is silently changed
  return user
}
```

**Correct:**
```javascript
function updateUser(user, name) {
  return { ...user, name }  // New object; original is untouched
}
```

### File Organization

Many small files > few large files.

| Rule | Limit | Rationale |
|------|-------|-----------|
| File size | 200-400 lines typical, 800 max | Files over 800 lines are hard to navigate and review |
| Function size | <50 lines | Long functions indicate multiple responsibilities |
| Nesting depth | ≤4 levels | Deep nesting signals missing extraction |
| Organization | By feature/domain, not by type | `features/auth/` > `controllers/`, `models/`, `views/` |

### Error Handling

Always handle errors explicitly with context.

**Violation:**
```typescript
try {
  await riskyOperation()
} catch (e) {
  console.log(e)  // Lost context, no recovery, generic log
}
```

**Correct:**
```typescript
try {
  const result = await riskyOperation()
  return result
} catch (error) {
  logger.error('riskyOperation failed', { cause: error, userId: user.id })
  throw new ApplicationError('Unable to complete operation', { cause: error })
}
```

### Input Validation

Validate all external input at the boundary using schema libraries.

**Violation:**
```typescript
app.post('/users', (req, res) => {
  db.create({ email: req.body.email })  // No validation — accepts anything
})
```

**Correct:**
```typescript
import { z } from 'zod'

const CreateUserSchema = z.object({
  email: z.string().email(),
  age: z.number().int().min(0).max(150),
})

app.post('/users', (req, res) => {
  const input = CreateUserSchema.parse(req.body)  // Throws on invalid input
  db.create(input)
})
```

### Code Quality Checklist

Before marking work complete, verify:

- [ ] Code is readable and well-named
- [ ] Functions are small (<50 lines)
- [ ] Files are focused (<800 lines)
- [ ] No deep nesting (>4 levels)
- [ ] Proper error handling with context
- [ ] No `console.log` statements left in source
- [ ] No hardcoded values (use constants or config)
- [ ] No mutation (immutable patterns used throughout)

## Enforcement

- **Linting:** Configure ESLint/Pylint rules for nesting depth, file length, function length
- **PR review:** Reviewer checks immutability, error handling, and input validation on every diff
- **Static analysis:** Run type checker and linter in CI; fail on violations
- **Code size alerts:** Flag files >800 lines or functions >50 lines in review
