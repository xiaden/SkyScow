# Historical Subagent Protocol (LEGACY)

> This reference is retained only to read or migrate historical plan artifacts. New work must use the persistent implementation graph through `exec-planner`; do not invoke this protocol to create plans, parts, rounds, or `CONTRACTS.md`.

## Legacy input

Historical callers may provide:

1. a legacy task/part description;
2. repository and request context;
3. historical contract or ledger text;
4. any existing plan path that must be migrated or inspected.

The caller must label every supplied artifact `LEGACY` and must not treat it as active graph authority.

## Migration behavior

When a historical plan is encountered:

1. read it without mutating it;
2. recover requirements, obligations, owners, contracts, dependencies, acceptance, and provenance;
3. compare those facts with the active `GRAPH.json`, if one exists;
4. report missing, contradictory, superseded, or ownerless facts to `exec-planner` as a bounded graph amendment request;
5. never create a replacement `TASK-*` file, plan group, execution round, README part index, or second contracts authority.

A historical plan may inform a graph amendment, but it cannot authorize claims, worker packets, completion, QA, or archival.

## Graph-native handoff

The active handoff contains:

- graph ID and current structure/state revisions;
- source request or accepted DD;
- normalized requirements and requirement ownership;
- bounded implementation obligations and node IDs;
- real prerequisite and producer/consumer edges;
- canonical contracts and declared producers/consumers;
- acceptance conditions, changed surfaces, provenance, and context hints;
- explicit graph gaps or architecture contradictions.

Runtime packet assembly belongs to `exec-manager`. This reference does not define worker phases, manager plans, execution rounds, or persisted packets.

## Verification boundary

Expose repository-defined, changed-surface verification commands and evidence when known. Do not manufacture universal test, lint, build, security, documentation, review, or commit steps. QA applicability remains owned by `config/instructions/qa-applicability.md`; applicable analyzers/generators run before final normal QA synthesis.

## Prohibited legacy behavior for new work

- creating `artifacts/plans/pending/TASK-*.md`;
- deriving dependency edges from letters, layers, file order, or review order;
- treating `CONTRACTS.md` or a README as active authority;
- requiring a plan or phase to be globally runnable before downstream-owned work exists;
- persisting worker/manager packets;
- using a legacy plan as a claim, completion, QA, or archive boundary.
