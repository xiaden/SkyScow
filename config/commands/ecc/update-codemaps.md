---
description: Generate or update codemaps for codebase navigation. Creates architecture, module, and file maps in docs/CODEMAPS/.
argument-hint: "[module or scope to update]"
---

# Update Codemaps

Generate or update codemaps: $ARGUMENTS

## Codemap Types

### Architecture Map (`docs/CODEMAPS/ARCHITECTURE.md`)
High-level system overview, component relationships, data flow diagrams.

### Module Map (`docs/CODEMAPS/MODULES.md`)
Module descriptions, public APIs, dependencies.

### File Map (`docs/CODEMAPS/FILES.md`)
Directory structure, file purposes, key files.

## Codemap Format

```markdown
### [Module Name]

**Purpose**: [Brief description]
**Location**: `src/[path]/`
**Key Files**:
- file.ts — purpose
**Dependencies**: [Module A], [Module B]
**Exports**: functionName() — description
```

## Process

1. Scan directory structure
2. Parse imports/exports
3. Build dependency graph
4. Generate markdown maps
5. Validate links
