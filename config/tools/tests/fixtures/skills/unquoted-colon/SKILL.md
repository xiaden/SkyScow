---
name: unquoted-colon
description: Use when a plain scalar contains a colon: like this one.
---

# Fixture: unquoted colon

Intentional regression fixture. The unquoted `: ` inside the plain-scalar
`description` makes the frontmatter invalid YAML, which is exactly the
OpenCode discovery/registry inconsistency this validator guards against.

This skill must be rejected by `scripts/validate_skills.py`.
