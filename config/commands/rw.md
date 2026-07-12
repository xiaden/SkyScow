---
description: RW autonomous coding harness — spawns a director which gates eligibility (RAH preconditions, worktree setup), then mechanically loops: fresh manager per round (decomposes goals into dependency DAGs, fans out to isolated workers), then adversarial reviewer (goal-progress validation from diff). Director routes on CONTINUE or STOP verdict. Zero human steering during loop. Zero knobs.
argument-hint: "<task description>"
---

Write `.rw/goal.md`:

```markdown
# Goal
<user's task description, verbatim>

# Budget
max_rounds: 5
```

Then spawn `rw-director` via `task`:

```
task(
  subagent_type: "rw-director",
  description: "RW: <brief summary>",
  prompt: "Execute the RW harness loop. Read .rw/goal.md and run the loop until a terminal verdict. Report back."
)
```

---

## Architecture

The main agent spawns `rw-director` as a subagent. The director runs a sequential loop: each round spawns a fresh `rw-manager` (reads the goal, writes a plan, spawns isolated workers, returns when complete), then a fresh `rw-reviewer` (reads only the goal and codebase — not the plan — and returns CONTINUE or STOP). The director routes: CONTINUE loops, STOP reports with reason and exits.

**Eligibility (RAH Preconditions):** Only 1 of 6 multi-agent workflows beat single-agent (Guo et al., 2026). The director checks RAH preconditions before starting — skip RW when: the dependency cut is dense (near-complete coupling), the task is <30 lines of change, touches <5 files, or leaf verification cannot be automated. The director also gates on worktree availability, prompting the user to install if needed.

If the director returns STOP, relay the reason and reviewer findings for human judgment.
