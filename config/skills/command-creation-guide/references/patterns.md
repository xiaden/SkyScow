# Command Patterns

Concrete JSON examples for common command scenarios. Reference these when building commands that match one of these patterns.

- [Basic Template](#basic-template)
- [Code Generation](#code-generation)
- [Debugging](#debugging)
- [Documentation](#documentation)
- [Multi-Step Workflow](#multi-step-workflow)
- [Conditional Logic](#conditional-logic)

## Basic Template

```json
{
  "commands": {
    "create-plan": {
      "description": "Create a detailed implementation plan for a feature",
      "prompt": "Create a detailed implementation plan for the following feature:\n\n$ARGUMENTS\n\nInclude:\n1. Requirements analysis\n2. Technical approach\n3. Step-by-step implementation tasks\n4. Testing strategy\n5. Potential risks and mitigations\n\nSave the plan to artifacts/plans/pending/",
      "agent": "plan"
    }
  }
}
```

### Using Arguments

Commands can accept arguments via `$ARGUMENTS`:

```json
{
  "commands": {
    "fix-issue": {
      "description": "Fix a specific issue by number",
      "prompt": "Fix issue #$ARGUMENTS:\n\n1. Read the issue description\n2. Understand the problem\n3. Implement the fix\n4. Add tests\n5. Verify the fix works\n\nReference the issue in your commit message.",
      "agent": "build"
    }
  }
}
```

Invoke with: `/fix-issue 123`

### Tool Restrictions

Limit tools to the minimum needed for the task:

```json
{
  "commands": {
    "analyze-code": {
      "description": "Analyze code structure without making changes",
      "prompt": "Analyze the codebase structure:\n\n1. Map module dependencies\n2. Identify circular dependencies\n3. Find unused code\n4. Suggest improvements\n\nDo NOT make any changes - analysis only.",
      "agent": "plan",
      "tools": ["read", "grep", "glob"]
    }
  }
}
```

### Model Selection

Override the model for specific needs:

```json
{
  "commands": {
    "quick-summary": {
      "description": "Generate a quick summary of recent changes",
      "prompt": "Summarize the recent git commits:\n\n1. Get the last 10 commits\n2. Group by theme\n3. Provide a concise summary\n\nKeep it brief and actionable.",
      "model": "anthropic/claude-haiku-4-20250514"
    }
  }
}
```

## Code Generation

```json
{
  "commands": {
    "generate-component": {
      "description": "Generate a new React component with tests and styles",
      "prompt": "Generate a new React component:\n\nComponent name: $ARGUMENTS\n\nCreate:\n1. Component file with TypeScript\n2. Test file with comprehensive tests\n3. Style file (CSS modules)\n4. Export from index.ts\n\nFollow the project's component structure and naming conventions.",
      "agent": "build"
    }
  }
}
```

## Debugging

```json
{
  "commands": {
    "debug-error": {
      "description": "Debug an error message and suggest fixes",
      "prompt": "Debug this error:\n\n$ARGUMENTS\n\n1. Analyze the error message\n2. Find where it occurs in the codebase\n3. Identify the root cause\n4. Suggest 2-3 possible fixes\n5. Recommend the best approach\n\nProvide clear, actionable steps to resolve the issue.",
      "agent": "build"
    }
  }
}
```

## Documentation

```json
{
  "commands": {
    "write-docs": {
      "description": "Generate documentation for a module or function",
      "prompt": "Generate documentation for: $ARGUMENTS\n\nInclude:\n1. Purpose and overview\n2. Parameters and return values\n3. Usage examples\n4. Edge cases and limitations\n5. Related functions/modules\n\nWrite in clear, concise language suitable for developers.",
      "agent": "build"
    }
  }
}
```

## Multi-Step Workflow

```json
{
  "commands": {
    "refactor-module": {
      "description": "Refactor a module following best practices",
      "prompt": "Refactor module: $ARGUMENTS\n\nPhase 1: Analysis\n1. Read the module and all dependencies\n2. Identify code smells and issues\n3. Document current behavior\n\nPhase 2: Planning\n1. Create a refactoring plan\n2. Identify breaking changes\n3. Plan test updates\n\nPhase 3: Implementation\n1. Apply refactoring changes\n2. Update tests\n3. Update documentation\n\nPhase 4: Validation\n1. Run all tests\n2. Check for regressions\n3. Verify behavior unchanged\n\nSave plan to artifacts/plans/pending/ before starting implementation.",
      "agent": "build"
    }
  }
}
```

## Conditional Logic

```json
{
  "commands": {
    "deploy": {
      "description": "Deploy to specified environment",
      "prompt": "Deploy to environment: $ARGUMENTS\n\n1. Validate environment name (dev/staging/prod)\n2. Run pre-deployment checks:\n   - All tests pass\n   - No uncommitted changes\n   - Dependencies up to date\n3. Build the application\n4. Deploy to $ARGUMENTS\n5. Run smoke tests\n6. Report deployment status\n\nIf environment is 'prod', require explicit confirmation before proceeding.",
      "agent": "build"
    }
  }
}
```
