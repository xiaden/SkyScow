# R&D and Design Documents

How an idea or architectural problem becomes a **Design Document (DD)**.

Nyx owns routing into R&D. `rnd-manager` owns the R&D graph, the requirement ledger, risk dispositions, and DD acceptance. `rnd-dd-author` writes the DD but does not orchestrate, reinterpret, or repair earlier decisions.

```mermaid
flowchart TD
    U["Idea or architectural problem"] --> C["Nyx captures request context (CTX)"]
    C --> R["rnd-estimator route decision"]

    R -->|RESEARCH_ONLY| RO["Bounded research only"]
    R -->|DAG_ONLY| DAGO["Change-DAG-Author — no DD"]
    R -->|DD_REQUIRED| G["Manager-composed R&D graph"]

    G --> EV["Evidence<br/>librarian • researcher"]
    G --> EX["External pair<br/>ideator → counter-ideator"]
    G --> AR["Architect<br/>tradeoff analysis"]
    G --> RP["Repository pair<br/>improver → counter-improver"]
    G --> CX["Complexity advisor"]

    EV --> M{"Manager decisions<br/>findings get a disposition"}
    EX --> M
    AR --> M
    RP --> M
    CX --> M

    M -->|DD_REQUIRED and evidence sufficient| DD["rnd-dd-author writes DD.md (pending)"]
    M -->|needs user decision| ND["NEEDS_DECISION"]
    M -->|no design needed| DONE["Return to Nyx"]

    DD --> V{"Manager conformance gate"}
    V -->|PASS| ACC["Accepted DD"]
    V -->|Gap| M
```

## Authority boundaries

- The original user request is the authoritative product specification. The Manager extracts an **immutable requirement ledger** and passes it unchanged downstream. Findings, recommendations, and estimates never become requirements or authorization on their own.
- A missing or unreadable `artifacts/requests/CTX_*.md` snapshot blocks DD authoring.
- `rnd-refiner` runs exactly one Manager-selected adversarial pair per invocation. It does not choose the architecture, decide dispositions, or authorize implementation.
- Material adversarial findings return to the Manager, which assigns exactly one disposition: `MITIGATE`, `ACCEPT_RISK`, `NOT_APPLICABLE`, or `DEFER_TO_OWNER`. Only `MITIGATE` authorizes a bounded correction.
- `support-pattern-enforcer` output is advisory evidence; it does not authorize implementation.

## Route decision

For a new design request, `rnd-estimator` runs first unless the user explicitly asks for a DD:

| Route | Meaning |
|---|---|
| `DAG_ONLY` | Route to `change-dag-author`; do not create a DD. |
| `DD_REQUIRED` | Compose a DD graph. An explicit DD request selects this directly. |
| `RESEARCH_ONLY` | Dispatch bounded research and stop — no partial DD. |

The route is not a fixed worker list. The Manager selects only capabilities whose inputs are missing or whose bounded challenge is useful, and records a short rationale for each selected or materially skipped capability.

## Conditional capabilities

| Capability | Selected when |
|---|---|
| `support-librarian` | Prior ADRs, ASRs, DDs, logs, or dead ends materially constrain the design |
| `support-researcher` | Repository integration points or external/API facts are unknown or need verification |
| External pair (`rnd-ideator` → `rnd-counter-ideator`) | External technology or approach space is open and consequential |
| `rnd-architect` | Multiple credible survivors still need concrete implementation tradeoffs |
| Repository pair (`rnd-improver` → `rnd-counter-improver`) | An accepted direction needs repository-native adaptation and its fit warrants challenge |
| `rnd-complexity-advisor` | The design introduces meaningful abstraction, lifecycle, dependency, compatibility, registry, or scope complexity |
| `rnd-estimator` | Early route selection, or a later estimate is useful downstream |

Genuinely independent librarian and researcher work may run concurrently; dependent nodes stay ordered. The external pair may return zero, one, or multiple surviving approaches with evidence. The Manager or the user selects one accepted direction before any repository pair runs.

## Design document authoring

`rnd-dd-author` is invoked only after the selected inputs exist and Manager decisions are resolved. It writes a single DD to:

```text
artifacts/designs/pending/{slug}/DD.md
```

It may record only Manager-authorized bounded corrections. Missing selected inputs block authoring; it does not spawn replacement agents.

## Acceptance

Before accepting, the Manager compares the captured request context, the immutable ledger, accepted constraints, selected reports, adversarial outcomes, dispositions, and the final DD. The completion gate requires every material finding to have a disposition and every ledger item to map to the DD.

An accepted DD is `Complete (accepted)`, `Approved`, or `Completed`. An accepted DD may remain in `pending/` only if it names a prerequisite disposition, an owner, and a transition condition; otherwise it is stale and cannot proceed to decomposition, execution, or archival.

## Canonical sources

- `config/agents/nyx.md` — routing and the request-context gate
- `config/agents/rnd-manager.md` — graph composition, dispositions, conformance gate
- `config/agents/rnd-refiner.md` — bounded adversarial pair execution
- `config/agents/rnd-dd-author.md` — DD authoring
- `config/skills/dispatching-agents/SKILL.md` — dispatch contracts and accepted-DD statuses
