---
name: command-creation-guide
description: Guidelines for creating effective OpenCode commands. Covers command definition in opencode.json, frontmatter fields, prompt structure, and best practices. Load when creating or updating commands.
---

# Command Creation Guide for OpenCode

Commands are reusable prompts that guide OpenCode to deliver consistent, high-quality outcomes. They appear in the command palette and can be invoked with `/command-name`.

## When to Use This Skill

**Trigger:** creating a new command, editing an existing command, or asked about command conventions.

**Do NOT use this skill when:**
- Creating an agent definition (use `customize-opencode`)
- Creating a skill (use `making-editing-skills`)


## What Are Commands?

Key characteristics:

- **Reusable**: Define once, use many times across sessions
- **Consistent**: Ensure the same quality and approach every time
- **Discoverable**: Appear in command palette with descriptions
- **Configurable**: Can specify agent, model, and tool restrictions

## Command Definition

Commands can be defined in two ways:

### 1. Standalone Markdown Files (Recommended)

Create `.md` files in a `commands/` directory. The filename becomes the command name.

**Locations:**
- Global: `~/.config/opencode/commands/`
- Per-project: `.opencode/commands/`

**Format:**
```markdown
---
description: What this command does
agent: build
model: anthropic/claude-sonnet-4-20250514
argument-hint: "<arg1> <arg2>"
---

The actual prompt text. Use $ARGUMENTS to reference the user's input.
```

**Example — `~/.config/opencode/commands/review-pr.md`:**
```markdown
---
description: Review a pull request for code quality and best practices
agent: build
argument-hint: "<pr-number>"
---

Review pull request #$ARGUMENTS:

1. Fetch the PR details
2. Read all changed files
3. Check for code quality, security, and test coverage
4. Provide specific, actionable feedback
```

Invoke with: `/review-pr 123`

**Subdirectories** create namespaced commands:
```
~/.config/opencode/commands/
├── git/
│   ├── commit.md      → /git:commit
│   └── pr.md          → /git:pr
└── testing/
    └── unit.md        → /testing:unit
```

### 2. Inline in opencode.json

Commands can also be defined inline under the `commands` key:

```json
{
  "commands": {
    "command-name": {
      "description": "What this command does",
      "prompt": "The actual prompt text...",
      "agent": "build",
      "model": "anthropic/claude-sonnet-4-20250514",
      "tools": ["edit", "bash"]
    }
  }
}
```

Prefer standalone files — they're easier to version, share, and maintain.

## Command Fields

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `description` | string | Brief description of what the command does (shown in command palette) |
| `prompt` | string | The actual prompt text that guides the agent |

### Optional Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `agent` | string | current | Which agent to use (e.g., `build`, `plan`, custom agent name) |
| `model` | string | current | Model override (e.g., `anthropic/claude-sonnet-4-20250514`) |
| `tools` | array | all | Restrict which tools the command can use |

## Prompt Structure

### Using Arguments

Commands accept arguments via `$ARGUMENTS`. Everything after the command name becomes the argument string.

Invocation: `/fix-issue 123` → `$ARGUMENTS` = `"123"`

### Prompt Writing Guidelines

1. **Start with a clear directive**: "Create", "Fix", "Review", "Generate"
2. **Provide context**: What information does the agent need?
3. **Define the workflow**: Step-by-step instructions
4. **Specify outputs**: Where should results be saved?
5. **Include validation**: How to verify success?

For concrete JSON examples of working commands, see [`references/patterns.md`](file:///home/opencode/.config/opencode/skills/command-creation-guide/references/patterns.md).

## Best Practices

### Description

Write clear, actionable descriptions that explain:
- **What** the command does
- **When** to use it
- **Keywords** users might search for

| Quality | Example |
|---------|---------|
| **Good** | `"Create a detailed implementation plan for a feature with requirements, technical approach, and testing strategy"` |
| **Poor** | `"Makes a plan"` |

### Agent Selection

Choose the appropriate agent:

- **build**: For commands that make changes (edit files, run commands)
- **plan**: For commands that analyze or plan without making changes
- **Custom agents**: For specialized tasks (e.g., `security-auditor`, `test-generator`)

### Tool Restrictions

Limit tools to the minimum needed for the task. Use `"tools": ["read", "grep", "glob"]` for analysis-only commands.

### Model Selection

Override the model only when the task genuinely benefits from a different capability tier. Use faster/cheaper models for simple summarization tasks, and more capable models for complex analysis.

## Maintenance

- Review when workflows change
- Update when tools are added/removed
- Commit command definitions to git
- Document changes in commit messages

## Validation Checklist

Before committing a command:

- [ ] `description` clearly states purpose and use cases
- [ ] `prompt` provides clear, step-by-step instructions
- [ ] `agent` is appropriate for the task
- [ ] `tools` are restricted to minimum needed (if applicable)
- [ ] `model` is overridden only when necessary
- [ ] Arguments are used correctly (if applicable)
- [ ] Command has been tested with representative inputs
- [ ] Output location/format is specified
- [ ] Validation steps are included

## References

- **This skill's references:**
  - [`references/patterns.md`](file:///home/opencode/.config/opencode/skills/command-creation-guide/references/patterns.md) — Full JSON examples for common patterns (basic, code generation, debugging, documentation, multi-step workflow, conditional logic)
  - [`references/troubleshooting.md`](file:///home/opencode/.config/opencode/skills/command-creation-guide/references/troubleshooting.md) — Command not appearing, command fails, command too slow
- **Canonical source:** <https://opencode.ai/config.json> — JSON Schema for `commands` config
- **Related skills:** `customize-opencode`, `making-editing-skills`
