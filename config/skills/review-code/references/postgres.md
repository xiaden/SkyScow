# PostgreSQL Code Review

**Purpose:** Language-specific review checklist for PostgreSQL — query performance, schema design, security (RLS), concurrency, and monitoring.
**Scope:** SQL files, database migrations, stored procedures, and application database access patterns.

## Verification Commands
```bash
# Connect to database
psql $DATABASE_URL

# Check for slow queries (requires pg_stat_statements)
psql -c "SELECT query, mean_exec_time, calls FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 10;"

# Check table sizes
psql -c "SELECT relname, pg_size_pretty(pg_total_relation_size(relid)) FROM pg_stat_user_tables ORDER BY pg_total_relation_size(relid) DESC;"

# Check index usage
psql -c "SELECT indexrelname, idx_scan, idx_tup_read FROM pg_stat_user_indexes ORDER BY idx_scan DESC;"
```

## [CRITICAL] Security & RLS
- **Enable RLS for multi-tenant data**: `ALTER TABLE orders ENABLE ROW LEVEL SECURITY;`
- **RLS policies use optimized pattern**: `(SELECT auth.uid())` not bare `auth.uid()` (100x faster)
- **Force RLS**: `ALTER TABLE orders FORCE ROW LEVEL SECURITY;` — prevents app-level bypass
- **Index all RLS policy columns** for performance

### RLS Example
```sql
-- BAD: Per-row function call
CREATE POLICY orders_policy ON orders
  USING (auth.uid() = user_id);  -- Called 1M times for 1M rows!
-- GOOD: Wrapped in SELECT (cached, called once)
CREATE POLICY orders_policy ON orders
  USING ((SELECT auth.uid()) = user_id);  -- 100x faster
```

### RLS Full Pattern
```sql
-- BAD: Application-only filtering
SELECT * FROM orders WHERE user_id = $current_user_id;
-- Bug means all orders exposed!

-- GOOD: Database-enforced RLS
ALTER TABLE orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE orders FORCE ROW LEVEL SECURITY;

CREATE POLICY orders_user_policy ON orders
  FOR ALL
  USING (user_id = current_setting('app.current_user_id')::bigint);

-- Supabase pattern
CREATE POLICY orders_user_policy ON orders
  FOR ALL
  TO authenticated
  USING (user_id = auth.uid());
```

## [CRITICAL] Schema Design
- **Data type selection**: `bigint` not `int`, `text` not `varchar(255)`, `timestamptz` not `timestamp`, `boolean` not `varchar(5)`, `numeric(10,2)` not `float`
- **Primary key strategy**: `bigint GENERATED ALWAYS AS IDENTITY` for single DB, UUIDv7 for distributed
- **Foreign keys have indexes**: Always index foreign key columns

### Data Type Selection
```sql
-- BAD: Poor type choices
CREATE TABLE users (
  id int,                           -- Overflows at 2.1B
  email varchar(255),               -- Artificial limit
  created_at timestamp,             -- No timezone
  is_active varchar(5),             -- Should be boolean
  balance float                     -- Precision loss
);

-- GOOD: Proper types
CREATE TABLE users (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  email text NOT NULL,
  created_at timestamptz DEFAULT now(),
  is_active boolean DEFAULT true,
  balance numeric(10,2)
);
```

### Primary Key Strategy
```sql
-- Single database: IDENTITY (default, recommended)
CREATE TABLE users (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY
);

-- Distributed systems: UUIDv7 (time-ordered)
CREATE EXTENSION IF NOT EXISTS pg_uuidv7;
CREATE TABLE orders (
  id uuid DEFAULT uuid_generate_v7() PRIMARY KEY
);
```

## [HIGH] Indexes

### Index on WHERE and JOIN Columns
**Impact:** 100-1000x faster queries on large tables
```sql
-- BAD: No index on foreign key
CREATE TABLE orders (
  id bigint PRIMARY KEY,
  customer_id bigint REFERENCES customers(id)
  -- Missing index!
);

-- GOOD: Index on foreign key
CREATE TABLE orders (
  id bigint PRIMARY KEY,
  customer_id bigint REFERENCES customers(id)
);
CREATE INDEX orders_customer_id_idx ON orders (customer_id);
```

### Index Type Selection
| Index Type | Use Case | Operators |
|------------|----------|-----------|
| **B-tree** (default) | Equality, range | `=`, `<`, `>`, `BETWEEN`, `IN` |
| **GIN** | Arrays, JSONB, full-text | `@>`, `?`, `?&`, `?\|`, `@@` |
| **BRIN** | Large time-series tables | Range queries on sorted data |
| **Hash** | Equality only | `=` (marginally faster than B-tree) |

### Composite Index Best Practices
**Impact:** 5-10x faster multi-column queries
```sql
-- BAD: Separate indexes
CREATE INDEX orders_status_idx ON orders (status);
CREATE INDEX orders_created_idx ON orders (created_at);

-- GOOD: Composite index (equality columns first, then range)
CREATE INDEX orders_status_created_idx ON orders (status, created_at);
```

## [HIGH] N+1 Query Prevention
```sql
-- BAD: N+1 pattern
SELECT id FROM users WHERE active = true;  -- Returns 100 IDs
-- Then 100 queries:
SELECT * FROM orders WHERE user_id = 1;
SELECT * FROM orders WHERE user_id = 2;
-- ... 98 more

-- GOOD: Single query with ANY
SELECT * FROM orders WHERE user_id = ANY(ARRAY[1, 2, 3, ...]);

-- GOOD: JOIN
SELECT u.id, u.name, o.*
FROM users u
LEFT JOIN orders o ON o.user_id = u.id
WHERE u.active = true;
```

## [HIGH] Concurrency & Locking
- **Keep transactions short** — don't make API calls inside transactions
- **Use SKIP LOCKED for queues** — workers skip locked rows instead of waiting
- **Lock duration** should be milliseconds, not seconds

### Keep Transactions Short
```sql
-- BAD: Lock held during external API call
BEGIN;
SELECT * FROM orders WHERE id = 1 FOR UPDATE;
-- HTTP call takes 5 seconds...
UPDATE orders SET status = 'paid' WHERE id = 1;
COMMIT;

-- GOOD: Minimal lock duration
-- Do API call first, OUTSIDE transaction
BEGIN;
UPDATE orders SET status = 'paid', payment_id = $1
WHERE id = $2 AND status = 'pending'
RETURNING *;
COMMIT;  -- Lock held for milliseconds
```

### SKIP LOCKED Pattern
**Impact:** 10x throughput for worker queues
```sql
-- BAD: Workers wait for each other
SELECT * FROM jobs WHERE status = 'pending' LIMIT 1 FOR UPDATE;

-- GOOD: Workers skip locked rows
UPDATE jobs
SET status = 'processing', worker_id = $1, started_at = now()
WHERE id = (
  SELECT id FROM jobs
  WHERE status = 'pending'
  ORDER BY created_at
  LIMIT 1
  FOR UPDATE SKIP LOCKED
)
RETURNING *;
```

## [MEDIUM] Pagination
- **Cursor-based pagination**: Always O(1) regardless of depth
```sql
-- BAD: OFFSET gets slower with depth (scans 200,000 rows)
SELECT * FROM products ORDER BY id LIMIT 20 OFFSET 199980;
-- GOOD: Cursor-based (uses index, O(1))
SELECT * FROM products WHERE id > 199980 ORDER BY id LIMIT 20;
```

## [MEDIUM] Monitoring
- Set up query analysis and performance tracking via pg_stat_statements
- Monitor table bloat and index usage
- Track connection pool utilization

## Anti-Patterns

| Pattern | Impact | Fix |
|---------|--------|-----|
| RLS function per row | 100x slower | Wrap in `(SELECT ...)` |
| OFFSET pagination | O(n) scan depth | Use cursor-based pagination |
| No foreign key index | Full table scans on JOIN | Add index on FK column |
| API calls inside transaction | Locks held for seconds | Do API calls outside transaction |
| Wrong data types | Overflow, precision loss, bloat | Use proper PostgreSQL types |
| Separate indexes for multi-column | Missed composite index benefit | Use composite index with equality cols first |

## Review Checklist
- [ ] All WHERE/JOIN columns indexed
- [ ] Composite indexes in correct column order
- [ ] Proper data types (bigint, text, timestamptz, numeric)
- [ ] RLS enabled on multi-tenant tables
- [ ] RLS policies use `(SELECT auth.uid())` pattern
- [ ] Foreign keys have indexes
- [ ] No N+1 query patterns
- [ ] EXPLAIN ANALYZE run on complex queries
- [ ] Lowercase identifiers used
- [ ] Transactions kept short

## Review Output Format

For each issue:
```
[SEVERITY] Issue title
File: path/to/file:line
Issue: Description
Fix: Suggested SQL change
```

## Approval Criteria
- **Approve**: No CRITICAL or HIGH issues
- **Warning**: MEDIUM issues only (pagination, monitoring gaps)
- **Block**: Any RLS gaps, unindexed FKs, N+1 patterns, or locking issues

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

## ECC Tools

Prefer ECC tooling for automated checks before manual review:
- `security-audit` — scans for SQL injection patterns and hardcoded connection strings
- `lint-check` — detects SQL linters and returns command
