# Skill-First Operating Procedure

Before starting any non-trivial task:

1. **Skills first** — Check the `<available_skills>` block. Load skills relevant to the task with the `skill` tool. Do not assume you already know the procedures.
2. **References second** — After loading a skill, inspect its root instructions for task-relevant references. Open those references explicitly before acting; the skill summary and the `<skill_files>` listing are not the reference contents.
3. **Task third** — Only begin the work once the applicable skill instructions and task-relevant reference material have been loaded.

This applies to every agent. Skipping a skill load is not neutral — it means operating without the procedural knowledge that was built to prevent exactly the mistake you're about to make.

## Git/GitHub hard precondition

Before performing or initiating any Git/GitHub operation, load every applicable generic `gg-*` skill (gg-core, gg-repos, gg-actions, gg-env, gg-artifacts, gg-docs, gg-router for routing, ggt-conventions for repo-local conventions) — missing or unloaded skills are a hard (near-hard) stop: do not proceed from memory or guess; fall back to the official docs rather than improvising.

This single precondition applies before every Git/GitHub operation class:

- **Local Git operations** (commits, branches, merge/rebase, worktrees, reflog, signing, hooks, config) — load `gg-core`.
- **Remotes, pull requests, and repository collaboration** — load `gg-repos`.
- **Workflow security and dispatch** — load `gg-actions`.
- **Docker artifact build/attestation** — load `gg-artifacts`.
- **Pages documentation publication** — load `gg-docs`.
- **Routing an unclassified Git/GitHub task** — load `gg-router`; repo-local conventions — load `ggt-conventions`.

This is one canonical precondition with minimal duplication, not a separate enforcement system. Skill-first loading is the primary behavior-standardization mechanism; executable checks, templates, and GitHub policy are complementary validation and infrastructure, not prerequisites for standardization. It preserves the "Skills first / References second / Task third" ordering above.

## Worked examples (progressive disclosure in practice)

The examples below show the skill-first order applied to real Git/GitHub tasks. Three obligations hold in every one:

- **Skills MUST be loaded and applied before work begins.** Open the relevant `gg-*` skill with the `skill` tool before performing the operation. Loading is not a formality — the skill's steps are the procedure you follow, so a skipped load means operating without the procedural knowledge the operation requires.
- **References MUST be loaded on demand.** When the loaded skill points to a task-relevant reference, explicitly open that reference before acting. If the reference points to more required material, follow it as well. The root skill and the sampled `<skill_files>` list are not enough.
- **Never dump every skill, and never guess from memory.** Load only the skills that apply to the task at hand, and only the references needed for the applicable path. When the applicable skill or required reference is unavailable, stop or fall back to the official docs — do not improvise.

### Example A — GitHub Actions workflow change, end to end

Task: "Tighten the permissions on our CI workflow, re-run it, and fetch the artifacts."

Load order: load `gg-router` only if you are unsure which skill owns the task; otherwise load `gg-actions` directly. Add `gg-env` for credential/PAT handling, and `gg-core` (local branch/commit) plus `gg-repos` (push/remotes) as the loop needs them.

1. Load `gg-actions`.
2. Read its root instructions and explicitly open the operation reference `workflow-lifecycle.md`. Its task index also points to `workflow-permissions.md` for the permissions review, so open that reference before changing permissions.
3. If either reference links to additional required policy or credential material, open that material before acting; do not stop after the first reference.
4. Inspect existing workflows: `gh workflow list`; `gh workflow view <name> --yaml`; `gh run list`.
5. Create a branch and commit the permission change (local state, `gg-core`): `git switch -c ci-perms`, then commit.
6. Push: `git push -u origin ci-perms` (`gg-repos`).
7. Dispatch the run: `gh workflow run <name> --ref ci-perms`.
8. Watch: `gh run watch <run-id> --exit-status`.
9. View status and logs: `gh run view <run-id>`; `gh run view <run-id> --log` (or `--log-failed`).
10. Download artifacts: `gh run download <run-id> -n <artifact> -D ./out`.
11. Cancel stale runs: `gh run cancel <run-id>`; clean up the temporary branch: `git push origin --delete ci-perms`.
12. Read the collected logs/artifacts, fix the code or workflow, commit, push, and re-dispatch — repeat until verification passes. Do not claim success on an unverified run.

The `gh` flag set changes across CLI releases; validate the local `gh` version and behavior first (see `gg-env` and `ggt-conventions`) rather than running these from memory.

### Example B — local Git work

Task: "Commit the changes on this branch and open a worktree for a parallel fix."

Load `gg-core` (the local-history owner). If a repo-local fact bears on the task, also load `ggt-conventions` to check this workspace's constraints (e.g. no remote, no local Docker). Follow `gg-core`'s `commit-branch.md` reference and `worktrees.md` reference on demand. Open both references before creating the commit or worktree; if either points to another required rule, follow that link first. Branch/commit/worktree are local-only, so no `gh` is involved.

### Example C — remote Docker / artifact work

Task: "Build the image with SLSA provenance and publish it to GHCR pinned by digest."

Load `gg-artifacts` (the hosted remote-Docker owner) and `gg-env` (credentials/visibility). Because local Docker is unavailable, check `ggt-conventions` to confirm that limitation before choosing GitHub-hosted runners. Follow `gg-artifacts`' `build-attested-image.md` reference and the shared `credentials-and-visibility.md` table on demand; explicitly open each before building or publishing.

### Example D — applicable skill unavailable

Task: a Git/GitHub operation whose applicable `gg-*` skill is missing from `<available_skills>` or whose required reference cannot be opened.

This is a hard (near-hard) stop. Do not proceed from memory or guess. Stop, or fall back to the official GitHub/Git documentation (docs.github.com, git-scm.com) rather than improvising.

### Example E — non-Git/GitHub tasks are not gated

Task: "Summarize this codebase's architecture." / "Write a unit test for module X."

These are not Git/GitHub operations. The precondition above does not apply: no `gg-*` skill load is required and no stop is triggered. Load the relevant general skills per the usual skill-first procedure, and follow their applicable references to completion, but the Git/GitHub hard precondition does not gate them.

## Execution Communication

Tool-using agents execute silently by default.

While work can proceed:

- Emit tool calls, not conversational progress.
- Do not narrate plans, intentions, reasoning, observations, or next actions.
- Do not use assistant content as working memory.
- Persist information needed by other agents in the appropriate plan, log, or artifact.

Assistant prose during execution is permitted only when:

- human interaction is required,
- execution is blocked and control must return to the caller, or
- the agent's explicit role includes user-facing communication.

After execution, return only the agent's defined output/report.
