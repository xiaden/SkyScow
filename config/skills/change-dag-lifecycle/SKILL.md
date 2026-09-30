---
name: change-dag-lifecycle
description: Operate an authored Change DAG through dag_start, dag_status, dag_stop, retry, and dag_archive. Use when Nyx starts, monitors, recovers, retries, or archives Change DAG execution.
---

# Change DAG lifecycle

Nyx owns lifecycle control. `dag_executor` owns deterministic application. Change-DAG-Author performs one initial semantic `dag_create` and exits; the controller — the deterministic, Nyx-invoked construction-control surface (`dag_construction_state`, `dag_construction_review`, `dag_construction_start`, `dag_semantic_repair_start`) — owns construction motion, serialized Worker admission, mandatory review, repair routing, and final validation. Change-DAG-Reviewer is optional, bounded, and read-only. This skill operates the existing runtime; it does not define or modify it.

## Start

1. Confirm the DAG is present, schema-valid, and executable through the lifecycle tools.
2. Call `dag_start(slug, retry?)` for whole-DAG execution only.
3. If the root is already runtime-satisfied, `dag_start` returns an idempotent `root_satisfied` result instead of launching: no queue entry, execution lock, marker, launch, or checkpoint. `retry=true` never relaunches a satisfied DAG.
4. Interpret `running` as executor launched and `queued` as waiting for the workspace execution slot.
5. Unresolved semantic nodes may remain while authoring, but such a DAG is not executable: `dag_start` refuses any non-executable DAG — unresolved semantic state or a deterministic compiler/context conflict — surfacing all admission issues.
6. `anchor_commit` is provenance, not a commit binding. Live repository drift can produce ordinary terminal failure and recovery.

## Status

Poll `dag_status(slug?)` until the DAG is `root_satisfied` or idle/not active. Inspect failed and `in_progress` terminal nodes when execution stops. There is no durable `quiescent` state.

## Stop and recovery

- `dag_stop(slug)` is lifecycle control, not rollback. Satisfied work remains satisfied; a queued DAG may be removed. Nyx owns this operation but does not decide semantic construction or repair content.
- The runtime handles process termination and interrupted-work reconciliation. Interrupted mechanical work is reconciled; an interrupted `run` becomes failed.
- A running DAG is immutable. Do not mutate nodes or work while it runs.
- When execution stops with failed mutable work, route the bounded scope through the controller: exact terminal defects to `change-dag-fixer`, semantic/graph defects to `change-dag-semantic-repairer`, and authority issues to escalation. After the stopped DAG is repaired and validated, call `dag_start(slug, retry=true)` to retry the whole DAG.
- There is no node- or subgraph-execution mode.

## Completion and archive

- When the root becomes satisfied, the executor records inherited starting-worktree evidence, creates the executor-owned local checkpoint, and records it in the Work Log. Nyx does not stage or create this checkpoint manually; it is not publication.
- Provenance logging is enabled by default and disabled by `SKYSCOW_CHANGE_DAG_MUTATION_LOGGING=0`, `false`, or `off`; append failure after DAG persistence is nonfatal and exposed only as success metadata warning. No agent-facing mutation-log reader is provided.
- Call `dag_archive(slug, reason)` when retiring a DAG from the pending working set. `reason` is required and non-empty. The bundle separates `DAG.json` (current construction state), optional `DAG_MUTATIONS.jsonl` (construction provenance), `EXECUTION_STATE.json` (execution lifecycle), and `WORK_LOG.jsonl` (execution evidence); archival moves all of them as-is, adds an `ARCHIVE.json` disposition record (`archived_at`, `reason`, `state_at_archive`, `artifacts_moved`), and moves the bundle to `artifacts/change-dags/archived/`. Construction provenance is not merged into the Work Log. Provenance logging is enabled by default and disabled by `SKYSCOW_CHANGE_DAG_MUTATION_LOGGING=0`, `false`, or `off`; append failure after DAG persistence is nonfatal and exposed only as success metadata warning. No agent-facing mutation-log reader is provided.
- Archival is cleanup, not certification: a DAG may be archived after success, failure, abandonment, supersession, or cancellation. It does not require resolution, executability, root satisfaction, a failure-free state, or QA. Only operational safety applies: stop a running DAG first, and cancel a queued DAG with `dag_stop`. Read the disposition record for the outcome; archive location is not success evidence.

## QA boundary

Route completed work to independent QA after execution. QA is not a DAG phase or archive gate. A completed DAG is never reopened for QA: use a bounded raw repair for a small defect, or create a new remediation DAG for a substantial or cross-cutting defect.
