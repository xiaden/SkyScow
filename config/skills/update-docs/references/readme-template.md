# README Template

Use this template when updating a project README. All setup commands must be tested before committing.

```markdown
# Project Name

Brief description — what it does and who it's for (1-2 sentences).

## Quick Start

```bash
# Install dependencies
npm install

# Set up environment
cp .env.example .env.local
# Edit .env.local with your values

# Start development server
npm run dev
```

## Features

- **Feature Name** — What it does
- **Feature Name** — What it does

## Architecture

See [Codemap Index](docs/CODEMAPS/INDEX.md) for detailed architecture documentation.

### High-Level Overview

[Brief 2-3 sentence description of the architecture. Link to codemaps for details.]

## Configuration

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `API_KEY` | Yes | External service API key |

See `.env.example` for the full list.

## Documentation

- [Setup Guide](docs/GUIDES/setup.md)
- [API Reference](docs/GUIDES/api.md)
- [Architecture Codemaps](docs/CODEMAPS/INDEX.md)

## Development

```bash
# Run tests
npm test

# Lint
npm run lint

# Type check
npm run typecheck
```

## Contributing

[Brief contribution guidelines or link to CONTRIBUTING.md]
```

## Update Checklist

- [ ] Quick Start commands tested from a clean checkout
- [ ] Feature list matches actual implemented features
- [ ] Architecture section links to codemaps (not duplicated)
- [ ] Configuration table matches `.env.example`
- [ ] Documentation links point to files that exist
- [ ] Development commands work (test, lint, typecheck)
