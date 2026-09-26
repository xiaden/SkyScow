# Change-DAG-Runner

Dispatch Change-DAG-Runner to run and archive a validated Change DAG.

## When to Dispatch

- A validated Change DAG exists and needs whole-DAG execution admission, status polling, and artifact lifecycle.
- A queued/running DAG must be stopped, reconciled, or archived.

**Do NOT dispatch when:**
- DAG topology is missing or wrong — use Change-DAG-Author.
- Review of semantic/work validity is the task — use Change-DAG-Reviewer.
- Diagnosis is the task — use Support-Debugger.

## Dispatch Template

```text
Run and steward Change DAG [SLUG].

Context:
- [REQUEST_OR_DD_PATH]
- [DAG_CONTEXT]
- [SOURCE_CONTEXT]

The runner must:
- Confirm the DAG is schema-valid and executable, then launch or queue it with dag_start(slug).
- Poll dag_status(slug) until the DAG is root_satisfied or idle/not active.
- Stop or reconcile an interrupted/failed DAG with dag_stop(slug) when recovery is needed.
- On completion, confirm the executor recorded inherited starting-worktree state,
  ran `git add -A`, and created a local checkpoint commit (SHA/evidence in WORK_LOG).
- Archive only through dag_archive(slug), which requires execution completion
  (root satisfied; no failed or in_progress terminal nodes) and does not depend on QA.

Do not edit production code, author/amend DAG topology outside the stopped mutable
region, dispatch or record QA, push, or claim release/global-green completion.

task:
  slug: "[SLUG]"
```

## Required Fields

| Field | Description |
| --- | --- |
| `[SLUG]` | Change DAG identity (shared slug with its DD when applicable) |
| request/DD context | Requirement provenance and accepted architecture |
| DAG context | Semantic/work structure, statuses, blockers |
| source context | Bounded files and repository facts for recovery/verification |

## Execution rules

- One DAG runs at a time per workspace. Admission serializes on a workspace-wide flock; when another run is active the DAG is `queued` with a queue position.
- `dag_start(slug, retry?)` re-runs preflight and refuses a presently non-executable DAG. It does not require `resolved`, a clean working tree, root satisfaction, or `HEAD == anchor_commit`.
- A running/in-progress DAG is immutable. Recovery stops the DAG (`dag_stop`) or waits for failure, then the stopped mutable region may be edited and execution retried.
- Terminal node states are `not_satisfied` / `in_progress` / `satisfied` / `failed`; derived `root_satisfied` means the root is satisfied. There is no durable quiescent state.
- The checkpoint commit on success is executor lifecycle behavior, not a `run` node and not publication. It is not produced for failed or unresolved partial execution.

## QA and Archive

QA is independent and is neither dispatched by nor recorded by this runner. It is not stored in `EXECUTION_STATE` and is not a DAG phase, archive gate, or lock holder. Small defects after a completed DAG are addressed by a bounded raw edit; substantial defects start a new `{dd-slug}-fix-N` Change DAG.

`dag_archive(slug)` requires only execution completion. Publication remains owned by `qa-push-manager`, which enforces QA before publication independently of DAG archival.

## Expected Output

```yaml
status: DONE | BLOCKED | ESCALATE
summary: "..."
slug: "[SLUG]"
execution:
  state: root_satisfied | idle
  starting_worktree: "..."
  checkpoint_commit: "..."
archive: {status: ARCHIVED | PENDING}
blockers: []
```
