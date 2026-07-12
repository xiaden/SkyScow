---
description: Extract patterns, learnings, and reusable insights from the current session
argument-hint: "[context or focus area]"
---

# Learn Command

Extract patterns, learnings, and reusable insights from the current session: $ARGUMENTS

## Your Task

Analyze the conversation and code changes to extract:

1. **Patterns discovered** — Recurring solutions or approaches that worked well
2. **Best practices applied** — Techniques that proved effective
3. **Mistakes to avoid** — Issues encountered and how they were resolved
4. **Reusable snippets** — Code patterns worth saving for future use
5. **Architecture insights** — Structural decisions and their rationale

## Output Format

### Patterns Discovered

**Pattern: [Name]**
- **Context:** When to use this pattern — the problem it solves
- **Implementation:** How to apply it — code structure, key decisions
- **Example:** Code snippet showing the pattern in action
- **Alternatives considered:** What else was tried and why it wasn't chosen

### Best Practices Applied

1. **[Practice name]**
   - **Why it works:** The principle or reasoning behind it
   - **When to apply:** Scenarios where this practice adds value
   - **When to skip:** Scenarios where this practice is unnecessary overhead

### Mistakes to Avoid

1. **[Mistake description]**
   - **What went wrong:** The failure mode or symptom
   - **Root cause:** Why it happened
   - **How to prevent:** Concrete preventative measures
   - **Detection:** How to catch this early in future work

### Reusable Patterns

For patterns that generalize beyond the current context:

```typescript
// Pattern: [Name]
// Use when: [condition]
function examplePattern(input: Input): Output {
  // Implementation
}
```

Describe:
- **What it does:** One-line summary
- **When to use:** Trigger conditions
- **Dependencies:** What it needs to work
- **Limitations:** When NOT to use it

### Architecture Insights

- **Decision:** [What was decided]
- **Context:** [Why at that time]
- **Consequences:** [What followed — good and bad]
- **If we did it again:** [What would change]

## Suggested Skill Updates

If patterns are significant and recurring, suggest updates to relevant skills:

- `skills/[domain]/SKILL.md` — Domain-specific patterns
- `instructions/[name].md` — Coding standards and guidelines
- `commands/[name].md` — Workflow automation improvements

Format for skill suggestions:

```
Skill: [skill-name]
Section: [where to add]
Content: [what to add or change]
Rationale: [why this improves the skill]
```

## Knowledge Capture Checklist

When extracting learnings, ensure:

- [ ] Pattern has a clear trigger condition (when to apply)
- [ ] Example is minimal but complete
- [ ] Alternatives are documented (why not other approaches)
- [ ] Scope is clear (what this pattern does NOT cover)
- [ ] Context is preserved (what made this pattern necessary)

---

**TIP**: Run `/learn` periodically during long sessions — especially before context compaction or when context windows are filling up. Patterns extracted early are patterns saved.
**TIP**: Focus on patterns that generalize. One-off fixes and project-specific details are less valuable to capture.
