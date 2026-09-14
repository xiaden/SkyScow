# Skill-First Operating Procedure

Before starting any non-trivial task, load a skill when at least one of these observable conditions holds:

1. **The skill owns a required rule** — the task must satisfy a rule whose canonical owner is that skill.
2. **The task enters the skill's domain** — the work touches the surfaces, tools, or file classes the skill's description covers.
3. **The repository or workflow requires it** — a repository policy, layer instruction, or plan step mandates the skill.
4. **You need its information to act correctly** — proceeding without it would rely on guessed or remembered procedure, not the task's actual requirements.

This is progressive disclosure, not preloading. Do not load a skill or reference merely because its keywords overlap with the task. Once a skill is loaded, open only the references the current work needs, explicitly and at the point of need; the skill summary and the `<skill_files>` listing are not the reference contents. Begin the work once the applicable skill instructions and the task-relevant reference material for the current step are loaded.

If a skill or reference is required by one of the conditions above but is unavailable, report it as a required-but-unavailable input rather than improvising around it.

This applies to every agent. A skill load is how you obtain the procedural knowledge the task requires; skip it only when none of the observable conditions above holds.

## Git/GitHub hard precondition

Before performing or initiating any Git/GitHub operation, load every applicable generic Git/GitHub skill and any required repo-local conventions skill. Missing or unloaded skills are a hard (near-hard) stop: do not proceed from memory or guess; fall back to the official Git or GitHub documentation rather than improvising.

This precondition is complementary to the general skill-first procedure above. The applicable Git/GitHub skill owns the operation procedure and references; this instruction only establishes the loading and fallback requirement.

For a Git/GitHub operation whose applicable skill or required reference is unavailable, stop or use the official documentation (`docs.github.com`, `git-scm.com/docs`) rather than improvising.

Non-Git/GitHub tasks follow the usual skill-first procedure and are not subject to this Git/GitHub-specific precondition.

