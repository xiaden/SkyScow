# Planning & Decomposition Methodology

## Boundary

Design planning transforms requirements into semantic implementation obligations and a persistent implementation graph. It does not pre-pack worker packets or Manager frontiers.

```text
requirements / accepted DD
        ↓
semantic implementation obligations
        ↓
real prerequisite and producer-consumer relationships
        ↓
persistent GRAPH.json
```

`exec-manager` performs runtime scheduling after graph creation. Worker packets and Manager frontiers are ephemeral execution decisions, not design artifacts.

## Method

1. Read the authoritative request, accepted DD when present, repository facts, and relevant existing contracts.
2. Normalize requirements and preserve their provenance.
3. Derive bounded obligations at the smallest meaningful repository-work level. Do not turn files, commits, phases, plans, or arbitrary edits into obligations.
4. Assign one owner, acceptance condition, changed surface, and useful context hint to each obligation.
5. Model only real edges: prerequisites, producer/consumer contracts, migrations, registrations, generated artifacts, and required control/data flow.
6. Define contracts with one declared producer and explicit consumers. Record materialized actuals only after producer-owned implementation is accepted.
7. Validate requirement ownership, dependency closure, cycles, producer ancestry, contract compatibility, safe writes, and graph gaps.
8. Persist the graph through `exec-planner`; invoke the read-only semantic gate only when observable coordination risk exists and the complete graph is present.

## Least-commitment modeling

- Independent obligations remain independent.
- Do not add edges for layers, labels, alphabetical order, review order, commit order, or milestone aesthetics.
- Do not infer a dependency from likely future work; add the missing owner or report `GRAPH_GAP`.
- A context hint may guide later packet assembly but never defines a packet, phase, plan, model, or execution order.
- A downstream consumer may remain incomplete only during execution when its graph node is explicit and owns that integration.

## Graph authority

`GRAPH.json` owns requirements, obligations, dependencies, contracts, producer/consumer ownership, acceptance, provenance, and context hints for new work. Feature READMEs, `CONTRACTS.md`, plan files, and task letters are not second authorities. Historical artifacts remain readable under explicit legacy compatibility rules.

## Design and execution separation

Design/planning stops after graph creation or bounded graph amendment and deterministic validation. Runtime execution then:

1. derives the ready frontier;
2. claims compatible nodes with one packet-level write scope;
3. assembles ephemeral worker packets;
4. accepts per-node evidence and materialized contracts through the Manager;
5. repeats until terminal closure or a graph gap/blocker is surfaced;
6. hands the completed graph to canonical QA.

No packet, scheduler queue, execution round, plan, or phase artifact is persisted.

## DD and request provenance

An accepted request may produce a request-only graph. An accepted DD may produce a DD-backed graph whose `source.design_doc` identifies the DD bundle. Requirement mappings must preserve the request/DD source. Architectural contradictions route upstream; they are not resolved by the graph gate or scheduler.

## Quality and Git boundaries

Canonical QA applicability owns test, documentation, boundary, journey, domain-risk, and security selection. Do not insert universal tests, builds, security reviews, code reviews, or commits into decomposition. Git commits remain independent workflow boundaries and never define graph nodes, dependencies, readiness, completion, or archive state.

## Validation checklist

- Every requirement has an owner.
- Every obligation is bounded and verifiable.
- Every edge is a real prerequisite or producer/consumer relation.
- Producer/consumer contracts agree and have valid ancestry.
- The graph is acyclic and free of unowned gaps.
- Runtime packetization is deferred until execution.
- Graph-backed DD archival depends on completed linked graphs and terminal QA, not plan-file absence.
- Legacy plan terminology appears only in explicitly historical compatibility material.
