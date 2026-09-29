# Change DAG Lifecycle

How an accepted DD becomes an executable **Change DAG**, and how that DAG is executed, recovered, and archived.

Four roles, deliberately separated:

- `change-dag-author` **constructs** the DAG — manager role: semantic graph, service-derived decomposition-frontier loop, reconciliation, validation — and amends mutable work during recovery. It never executes.
- `change-dag-worker` **lowers** one assigned semantic node into exact work, meaning decomposition, or lossless SCALE decomposition (per the `config/skills/change-dag-semantics/SKILL.md` doctrine), and may selectively dispatch the two read-only researchers; it is dispatched internally by the author manager and retrieves its own scope with `dag_decomposition_scope`. It never manages the frontier, mutates source, or executes.
- `nyx` **operates** the lifecycle tools (`dag_start`, `dag_status`, `dag_stop`, `dag_archive`).
- `dag_executor` **applies** terminal work deterministically and serially.

`change-dag-reviewer` is optional, bounded, and read-only, selected by Nyx. A reviewer `PASS` is evidence only; it does not authorize execution.

## Building the DAG

```mermaid
flowchart TD
    DD["Accepted Design Document"] --> S["dag_create with semantic graph"]
    S --> SEM["Semantic requirements<br/>postconditions, not actions"]
    SEM --> F{"dag_decomposition_frontier<br/>deepest unresolved nodes"}
    F --> W["change-dag-worker<br/>one per returned node"]
    W --> R["optional semantic/file<br/>researchers"]
    R --> W
    W --> X["Exact work nodes<br/>create • edit • remove • move • run"]
    X --> F
    F -->|no frontier left| VAL["dag_validate<br/>schema-valid • executable • resolved"]
    VAL --> REV["Optional change-dag-reviewer<br/>read-only evidence"]
    REV --> AUTH["Authored Change DAG"]
    VAL --> AUTH

    CTX["Bounded repository evidence<br/>live source • DD • request context"] -.-> F
```

- The initial semantic structure is the smallest skeleton grounded in known correctness/causal structure, submitted atomically through `dag_create(slug, semantic_graph)`; the Author does not pre-size nodes for one Worker context. Semantic nodes express postconditions, not implementation actions. Worker-discovered breadth may be refined later through lossless SCALE decomposition. The canonical semantic-node doctrine (MEANING vs SCALE, parent/child completeness, sibling/causal semantics, semantic/terminal boundary) is `config/skills/change-dag-semantics/SKILL.md`.
- The DAG's only edge is `requires`, and it is ALL-of: `requires` expresses what must become true for a semantic requirement to be fulfilled. A semantic node is satisfied only when every node it directly requires is satisfied. Nodes on the same semantic frontier assert authoring independence; the frontier service derives the frontier from `requires` edges only and never infers a missing causal relationship. Semantic siblings imply no authoring dependency through each other; if correct authoring of B requires accepted work from A, B must have a `requires` path to A rather than being represented as an independent sibling.
- Exact work is lowered one **decomposition frontier** at a time, from the deepest semantic nodes upward. The author manager queries `dag_decomposition_frontier(slug)` and dispatches one fresh bounded `change-dag-worker` per returned node; a frontier is the service-derived scheduling/reconciliation unit and a semantic node is the worker/context unit. The Worker retrieves its own scope with `dag_decomposition_scope(slug, node_id)`. The author reconciles only when results or conflicts require it, re-queries the frontier rather than tracking progress locally, and must not load the entire repository into one session.
- A semantic node may record persisted authoring intent with `dag_set_decomposition_only(slug, node_id, true)` when its obligation is fully decomposed into the semantic requirements it directly `requires` and it intentionally owns no direct terminal work. It is semantic-only: the node must directly require at least one semantic child, and a direct create/edit/remove/move/run child makes the DAG structurally invalid. `value=false` reopens the judgment. The field never affects runtime satisfaction, which still derives only from the satisfaction of `requires` children; only a bounded worker may call the setter.
- `dag_validate` reports `schema_valid`, `executable`, and `resolved`. A semantic node is locally resolved when it directly requires at least one terminal work node, or when it declares `decomposition_only=true` over semantic children only; `resolved` means every reachable semantic node is locally resolved. `executable` is the aggregate execution-admission/lint result: a DAG is executable only when it is structurally valid, `resolved`, and free of deterministic compiler/context admission conflicts. A DAG can be schema-valid and still unresolved; unresolved DAGs are valid authoring artifacts but are not executable.
- Optional review may be selected by Nyx for observable coordination or authority risks such as shared convergence, interface migrations, shared schemas, recovery amendments, or explicit user request. The author surfaces `review_triggers`; neither the author nor a worker dispatches the reviewer.

## Executing the DAG

```mermaid
flowchart TD
    START["dag_start(slug, retry?)"] --> PF["Parse + schema validate + compiler preflight"]
    PF -->|non-executable| REFUSE["Refused"]
    PF -->|executable| SAT{"Root already satisfied?"}
    SAT -->|yes| DONE["Idempotent root_satisfied<br/>no queue, lock, marker, launch, or checkpoint"]
    SAT -->|no| SLOT{"Workspace execution slot free?"}

    SLOT -->|no| Q["FIFO queue<br/>position reported as queued"]
    SLOT -->|yes| RUN["Detached dag_executor launches"]
    Q --> RUN

    RUN --> APPLY["Apply ready terminal work<br/>compile-conflict detection • in_progress marking"]
    APPLY --> RUNS["Run ready run nodes<br/>non-exclusive overlap • exclusive alone"]
    RUNS --> STATE{"Root satisfied?"}
    STATE -->|no, work remains| APPLY
    STATE -->|stopped or failed| REC["Reconcile interrupted work<br/>satisfied work preserved • interrupted run becomes failed"]
    STATE -->|yes| CKPT["Executor-owned local checkpoint<br/>starting-worktree evidence in Work Log (not publication)"]

    REC --> AMEND["change-dag-author amends mutable region"]
    AMEND --> START
    CKPT --> ARCH["dag_archive(slug, reason)"]
```

Key runtime facts:

- **One active executor per workspace.** The workspace execution lock is authoritative ownership/liveness; the PID is advisory control metadata. When the slot is busy, `dag_start` returns `queued` with a position.
- **An already-satisfied pending DAG is never relaunched.** When the root is already runtime-satisfied, `dag_start` returns an idempotent `root_satisfied` result before queueing, ownership, launch, or checkpointing. `retry=true` does not override it. Re-admitting a completed DAG would otherwise reach the executor-owned checkpoint path a second time and stage unrelated working-tree changes.
- **The queue is FIFO and duplicate-safe.** A slug already queued keeps its original position and request; it is not re-added.
- **Launch handoff is atomic.** Head selection, child launch, marker creation, and removal of exactly that entry happen under a short-lived queue lock, ordered after the execution lock, so a concurrent `dag_stop` cannot cause a removed DAG to launch or a different DAG to be dequeued.
- **`run` nodes are verification barriers.** They must not contain commit, push, PR, release, deploy, or other publication/lifecycle commands.
- **Detached execution with a synchronous fallback.** The executor runs out of band; a genuine detached-launch failure falls back synchronously.

## Status, stop, and recovery

Status values are `queued`, `running`, `root_satisfied`, and `idle`. There is no durable `quiescent` state.

- `dag_stop(slug)` is lifecycle control, not rollback. Satisfied work remains satisfied; a queued DAG can be removed. Interrupted mechanical work is reconciled; an interrupted `run` becomes failed.
- **A running DAG is immutable.** Do not mutate nodes or work while it runs.
- Recovery sequence: execution stops or fails → the executor reconciles interrupted work → `change-dag-author` amends the mutable failed/unresolved region → `dag_validate` → `dag_start(slug, retry=true)` retries the whole DAG. There is no node- or subgraph-execution mode.
- `anchor_commit` is provenance, not a commit binding. Live repository drift can produce ordinary terminal failure and recovery.

## Completion and archive

When the root becomes satisfied, the executor records inherited starting-worktree evidence and creates an executor-owned local checkpoint in the Work Log. Nyx does not create this checkpoint manually, and it is not publication.

`dag_archive(slug, reason)` retires a pending bundle into `artifacts/change-dags/archived/` and writes an `ARCHIVE.json` disposition record (`archived_at`, `reason`, `state_at_archive`, `artifacts_moved`) before the move.

Archival is lifecycle cleanup, not certification: a DAG may be archived after success, failure, abandonment, supersession, or cancellation, and the move implies none of those. It does **not** require `resolved`, `executable`, root satisfaction, an absence of failed nodes, or QA. Only operational-integrity gates apply: a running DAG must be stopped first, and a queued DAG must be cancelled with `dag_stop` before it can be archived. Derive whether execution completed from the recorded state, never from archive membership.

## QA boundary

QA is not a Change DAG phase and is not an archive gate. An archived DAG is never reopened for QA: use a bounded raw repair for a small defect, or a new remediation Change DAG for a substantial or cross-cutting defect.

## Canonical sources

- `config/agents/change-dag-author.md` — construction management, frontiers, amendment
- `config/agents/change-dag-worker.md` — bounded single-semantic-node lowering/decomposition
- `config/skills/change-dag-lifecycle/SKILL.md` — lifecycle operation
- `config/skills/change-dag-semantics/SKILL.md` — canonical semantic-node doctrine
- `config/tools/common/tools/dag_start.py`, `dag_status.py`, `dag_stop.py`, `dag_archive.py` — lifecycle tools
- `config/tools/common/tools/dag_executor.py`, `config/tools/common/helpers/change_dag_control.py` — execution and queue control
