---
name: change-dag-lifecycle
description: Operate an authored Change DAG through dag_start, dag_status, dag_stop, retry, and dag_archive. Use when Nyx starts, monitors, recovers, retries, or archives Change DAG execution.
---

# Change DAG lifecycle

Nyx owns lifecycle control. `dag_executor` owns deterministic application. Change-DAG-Author owns DAG construction and amendment; it cannot execute. Change-DAG-Reviewer is optional, bounded, and read-only. This skill operates the existing runtime; it does not define or modify it.

## Start

1. Confirm the DAG is present, schema-valid, and executable through the lifecycle tools.
2. Call `dag_start(slug, retry?)` for whole-DAG execution only.
3. Interpret `running` as executor launched and `queued` as waiting for the workspace execution slot.
4. Unresolved semantic nodes may remain while authoring, but such a DAG is not executable: `dag_start` refuses any non-executable DAG — unresolved semantic state or a deterministic compiler/context conflict — surfacing all admission issues.
5. `anchor_commit` is provenance, not a commit binding. Live repository drift can produce ordinary terminal failure and recovery.

## Status

Poll `dag_status(slug?)` until the DAG is `root_satisfied` or idle/not active. Inspect failed and `in_progress` terminal nodes when execution stops. There is no durable `quiescent` state.

## Stop and recovery

- `dag_stop(slug)` is lifecycle control, not rollback. Satisfied work remains satisfied; a queued DAG may be removed.
- The runtime handles process termination and interrupted-work reconciliation. Interrupted mechanical work is reconciled; an interrupted `run` becomes failed.
- A running DAG is immutable. Do not mutate nodes or work while it runs.
- When execution stops with failed mutable work, route the bounded scope to Change-DAG-Author. After amendment and validation, call `dag_start(slug, retry=true)` to retry the whole DAG.
- There is no node- or subgraph-execution mode.

## Completion and archive

- When the root becomes satisfied, the executor records inherited starting-worktree evidence, creates the executor-owned local checkpoint, and records it in the Work Log. Nyx does not stage or create this checkpoint manually; it is not publication.
- Call `dag_archive(slug, reason)` when retiring a DAG from the pending working set. `reason` is required and non-empty; the bundle gains an `ARCHIVE.json` disposition record (`archived_at`, `reason`, `state_at_archive`, `artifacts_moved`) and moves to `artifacts/change-dags/archived/`.
- Archival is cleanup, not certification: a DAG may be archived after success, failure, abandonment, supersession, or cancellation. It does not require resolution, executability, root satisfaction, a failure-free state, or QA. Only operational safety applies: stop a running DAG first, and cancel a queued DAG with `dag_stop`. Read the disposition record for the outcome; archive location is not success evidence.

## QA boundary

Route completed work to independent QA after execution. QA is not a DAG phase or archive gate. A completed DAG is never reopened for QA: use a bounded raw repair for a small defect, or create a new remediation DAG for a substantial or cross-cutting defect.
