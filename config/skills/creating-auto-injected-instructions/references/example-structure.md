# Example Instruction Structures

Annotated examples of auto-injected instruction files for common use cases.

## Example 1: API Route Conventions

```markdown
---
name: API Routes
description: Conventions for HTTP route handlers — validation, response shaping, error handling
applyTo: src/api/**, src/routes/**
---

# API Routes

**Purpose:** Handle HTTP requests, validate input, shape responses. Route handlers contain no business logic — they delegate to services.

## File Naming

- One file per resource: `src/api/users.ts`, `src/api/orders.ts`
- Test files: `src/api/users.test.ts`

## Required Structure

Every route handler must:

1. Validate request parameters using the schema in `src/schemas/`
2. Call the appropriate service method
3. Return a response using `ApiResponse.success()` or `ApiResponse.error()`

## Forbidden Patterns

- **No direct database access** — routes call services, services access the database
- **No business logic** — no loops, transformations, or conditionals beyond input validation
- **No raw error responses** — always use `ApiResponse.error(code, message)`

## Validation

Run `npm run lint:api` after editing route files.
```

**Why this works:**
- `applyTo` covers two related directories that share identical conventions
- The purpose statement explains the layer's role immediately
- "Required Structure" is numbered for scanability
- "Forbidden Patterns" uses bold keywords so the agent can grep mentally
- Validation step is concrete and runnable

## Example 2: Database Migration Rules

```markdown
---
name: Database Migrations
description: Rules for database migration files — naming, idempotency, rollback requirements
applyTo: db/migrations/**
---

# Database Migrations

**Purpose:** Add, alter, or remove database schema objects. Every migration must be reversible.

## File Naming

`YYYYMMDDHHMMSS_descriptive-name.sql`

Example: `20260709120000_add-user-email-index.sql`

## Required Structure

Each migration file must contain two sections separated by `-- ## DOWN ##`:

```sql
-- Up migration: the change being applied
CREATE INDEX idx_users_email ON users(email);

-- ## DOWN ##

-- Down migration: reverses the above
DROP INDEX IF EXISTS idx_users_email;
```

## Rules

- **Idempotent:** Every `CREATE` must be guarded with `IF NOT EXISTS`. Every `DROP` with `IF EXISTS`.
- **Reversible:** Every up migration must have a corresponding down migration.
- **No data changes in schema migrations** — data migrations belong in `db/seeds/`.

## Validation

Run `npm run db:validate` before committing any migration file.
```

**Why this works:**
- The file naming convention includes a date-stamp template
- The DOWN separator convention is shown in-line with a concrete example
- Rules are scoped to migration-specific concerns (idempotency, reversibility)
- Explicit boundary: "no data changes" pushes that responsibility elsewhere
