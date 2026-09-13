# Skill-First Operating Procedure

Before starting any non-trivial task:

1. **Skills first** — Check the `<available_skills>` block. Load skills relevant to the task with the `skill` tool. Do not assume you already know the procedures.
2. **References second** — After loading a skill, inspect its root instructions for task-relevant references. Open those references explicitly before acting; the skill summary and the `<skill_files>` listing are not the reference contents.
3. **Task third** — Only begin the work once the applicable skill instructions and task-relevant reference material have been loaded.

This applies to every agent. Skipping a skill load is not neutral — it means operating without the procedural knowledge that was built to prevent exactly the mistake you're about to make.

## Git/GitHub hard precondition

Before performing or initiating any Git/GitHub operation, load every applicable generic Git/GitHub skill and any required repo-local conventions skill. Missing or unloaded skills are a hard (near-hard) stop: do not proceed from memory or guess; fall back to the official Git or GitHub documentation rather than improvising.

This precondition is complementary to the general skill-first procedure above. The applicable Git/GitHub skill owns the operation procedure and references; this instruction only establishes the loading and fallback requirement.

For a Git/GitHub operation whose applicable skill or required reference is unavailable, stop or use the official documentation (`docs.github.com`, `git-scm.com/docs`) rather than improvising.

Non-Git/GitHub tasks follow the usual skill-first procedure and are not subject to this Git/GitHub-specific precondition.

