# Codemap Template

Use this template when generating codemaps. Fill in sections from `aft_outline` and `aft_zoom` output — do not hand-write descriptions.

```markdown
# [Area Name] Codemap

**Last Updated:** YYYY-MM-DD
**Scope:** [directory or module path]

## Overview

One paragraph: what this area does and why it exists.

## Architecture

ASCII diagram showing component relationships:

```
┌─────────────┐     ┌─────────────┐
│  Component A │────▶│  Component B │
└─────────────┘     └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  Component C │
                    └─────────────┘
```

## Key Modules

| Module | Purpose | Key Exports | Depends On |
|--------|---------|-------------|------------|
| `src/foo/bar.ts` | What it does | `fn1`, `fn2`, `Type1` | `./baz`, `external-lib` |
| `src/foo/baz.ts` | What it does | `fn3` | — |

## Data Flow

Describe how data enters, transforms, and exits this area:

1. Input arrives via [entry point]
2. [Component A] processes it by [action]
3. Result passes to [Component B] for [action]
4. Output is [format/location]

## External Dependencies

| Package | Purpose | Version |
|---------|---------|---------|
| package-name | Why it's used | ^1.0.0 |

## Environment Variables

| Variable | Required | Default | Purpose |
|----------|----------|---------|---------|
| `FOO_URL` | Yes | — | Connection string for foo service |

## Known Issues / TODOs

- [ ] Any tracked issues or known limitations
```

## Generation Checklist

- [ ] All module descriptions sourced from JSDoc/TSDoc or `aft_outline`
- [ ] Architecture diagram reflects actual imports/dependencies
- [ ] Key exports match `aft_outline` output for each module
- [ ] Data flow verified against call graph (`aft_zoom` with `callgraph: true`)
- [ ] External dependencies match `package.json`
- [ ] Environment variables match `.env.example`
- [ ] Freshness timestamp is current
