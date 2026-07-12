# Drift Report Format

Use this format when reporting documentation drift. Every claim should be traceable to a specific file and line.

```markdown
## Drift Report — [Area]
**Checked:** YYYY-MM-DD

### Stale References
- `docs/setup.md` line 12: references `src/old-helper.ts` — file no longer exists
- `README.md` line 45: documents `createWidget(opts)` — signature changed to `createWidget(opts, callback)`

### Missing Documentation
- `src/auth/middleware.ts` exports `validateToken` — not documented anywhere
- New env var `REDIS_URL` in `.env.example` — not mentioned in setup docs

### Accurate (no changes needed)
- API endpoint docs match route definitions ✓
- Architecture codemap matches current module structure ✓
```

## Sections

| Section | What to include |
|---------|----------------|
| **Stale References** | Paths, signatures, or examples in docs that no longer match actual code |
| **Missing Documentation** | Exported symbols, env vars, or features not covered by any doc |
| **Accurate** | Items verified correct — builds confidence that unchanged areas are still valid |

**Key rule:** Every stale/missing item must reference a source-of-truth location in the codebase (file path, symbol name, env var name).
