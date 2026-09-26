# Change DAG Authoring & Decomposition Methodology

## Boundary

Change DAG authoring transforms requirements into semantic obligations and exact work. It does not execute the work or persist a projected planning worktree.

```text
requirements / accepted DD
        ↓
semantic obligations (conditions/postconditions)
        ↓
nesting / ALL-of satisfied_by edges
        ↓
exact work (create / edit / remove / move / run) on terminal frontier
        ↓
artifacts/change-dags/pending/{slug}/DAG.json
```

`change-dag-runner` performs execution admission and artifact lifecycle after authoring. Execution state and work evidence live in `EXECUTION_STATE.json` and `WORK_LOG.jsonl`; they are not design artifacts.

## Method

1. Read the authoritative request, accepted DD when present, repository facts, and relevant live surfaces.
2. Normalize requirements and preserve their provenance.
3. Generate the smallest complete **semantic** graph: conditions/postconditions, never implementation actions. Submit it atomically with `dag_create`.
4. Model `satisfied_by` as the only edge and interpret it as ALL-of. A semantic leaf with no children is an unresolved semantic leaf and is legal.
5. Lower exact work from the deepest construction frontier upward using `dag_add_create` / `dag_add_edit` / `dag_add_remove` / `dag_add_move` / `dag_add_run`, reading live source plus applicable accepted lower DAG patches via `dag_preview(path)`.
6. Preserve a run-barrier invariant: a semantic node has at most one direct `run` child, and that run is its only non-semantic child.
7. Validate with `dag_validate`; inspect with `dag_show` / `dag_preview`. Node IDs are service-assigned (`^N[0-9]+$`) and depth is derived, never persisted.

## Least-commitment modeling

- Independent obligations remain independent.
- Do not add edges for layers, labels, alphabetical order, review order, commit order, or milestone aesthetics.
- Do not infer a dependency from likely future work; add the missing semantic node instead.
- A semantic child must materially refine its parent; pure paraphrase or recursive restatement is invalid decomposition.
- A downstream consumer may remain unresolved during authoring only as an explicit unresolved semantic leaf.

## DAG authority

`DAG.json` owns the semantic requirements and exact terminal work for a change; `EXECUTION_STATE.json` owns terminal-node execution status; `WORK_LOG.jsonl` owns append-only evidence. The DD remains requirements authority when present. `CONTRACTS.md`, plan files, task letters, and implementation graphs are not second authorities. Historical artifacts remain readable under explicit legacy compatibility rules.

## Authoring and execution separation

Authoring stops after DAG creation/amendment and deterministic validation. Execution then:

1. runs a pre-execution conflict/applicability check;
2. executes satisfied/terminal nodes in dependency order under a workspace-wide lock, one DAG at a time;
3. records terminal-node evidence in the Work Log;
4. reports derived `root_satisfied` when the root is satisfied;
5. creates a local checkpoint commit on success (not publication).

No projected planning worktree, packet, scheduler queue, execution round, plan, or phase artifact is persisted. A running/in-progress DAG is immutable.

## DD and request provenance

An accepted request may produce a request-only DAG. An accepted DD may produce a DD-backed DAG that shares the DD slug; the DAG has no separate `source` field. Requirement mappings must preserve the request/DD source. Architectural contradictions route upstream; they are not resolved by review or execution.

## Quality and Git boundaries

Canonical QA applicability owns test, documentation, boundary, journey, domain-risk, and security selection. Do not insert universal tests, builds, security reviews, code reviews, or commits into decomposition; expose repository-defined changed-surface verification as `run` nodes only when it is part of satisfying the change. Publication/lifecycle commands (commit, push, PR, release, deploy) are excluded from `run` nodes. Git commits remain independent workflow boundaries and never define DAG nodes, dependencies, readiness, completion, or archive state.

## Validation checklist

- [ ] Every requirement maps to an owned semantic node.
- [ ] Each semantic node states a postcondition, not an action.
- [ ] Every semantic leaf is terminal exact work or an explicit unresolved leaf.
- [ ] Every `satisfied_by` edge is an ALL-of relation and the graph is acyclic.
- [ ] Run-barrier invariant holds (at most one direct run child per semantic node).
- [ ] Exact work is valid against live source plus applicable accepted lower DAG patches.
- [ ] Legacy plan/graph terminology does not appear in active authoring instructions.
