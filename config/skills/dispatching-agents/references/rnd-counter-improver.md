# RnD-CounterImprover

Dispatch RnD-CounterImprover to validate repository fit — checking actual paths, ownership, lifecycle, dependencies, and unnecessary mechanisms, while allowing evidence-backed `GOOD_ENOUGH` validation.

## When to Dispatch

**Dispatch when:**
- RnD-Refiner delegates repository-fit validation when the Manager selects the repository pair or a bounded follow-up
- You have a repository-native realization and want it stress-tested against actual local fit and consequential external risks
- You need evidence-grounded repository-fit analysis of what could go wrong at implementation time

**Do NOT dispatch when:**
- You need approach-level critique — use `rnd-counter-ideator` instead
- You need repository-native adaptation — use `rnd-improver` instead
- You need implementation analysis — use `rnd-architect` instead
- You're doing a standard code review — use QA agents instead

## Dispatch Template

```
Validate the repository-native realization recorded in [LOG_PATH]. Recommend, but do not decide, `MITIGATE`, `ACCEPT_RISK`, `NOT_APPLICABLE`, or `DEFER_TO_OWNER` for evidence-backed risks; preserve provenance, applicability, and currentness analysis. When findings require a decision, return a concrete continuation payload containing `phase: PAUSED_FOR_MANAGER`, `log_path`, the existing session identities, all findings or a substantiated `GOOD_ENOUGH` / `NO_MATERIAL_CONCERNS` result, and `requires_manager_disposition: true`. Do not self-authorize mitigation or invoke a correction. A bounded follow-up may resume only after RnD-Manager supplies exactly one of `MITIGATE`, `ACCEPT_RISK`, `NOT_APPLICABLE`, or `DEFER_TO_OWNER` per material finding; only listed `MITIGATE` entries may authorize correction.

Trace actual call/runtime paths, abstractions, ownership, lifecycle, process/supervision boundaries, dependency/API semantics, and filesystem/network/container behavior. Challenge mechanisms that duplicate repository-owned behavior and ask whether each addition is required by local evidence. If the realization is coherent and no material applicable mismatch remains, return a substantiated `GOOD_ENOUGH` / `NO_MATERIAL_CONCERNS` payload with paths and assumptions checked; do not force cross-mechanism risks, library gotchas, or unsupported edge cases. Return the complete review payload with section identity and minimal control metadata to Refiner; Refiner validates and appends it to the shared adversarial log.

White-hat adversary — success is measured by how much the final repository-native realization improves, or is credibly validated. Read-only.
```

## Required Fields

| Field | Description | Example |
|-------|-------------|---------|
| `[LOG_PATH]` | Path to the shared adversarial log with the repository-native realization | `artifacts/designs/pending/collab-editing/ADVERSARIAL.md` |

## Expected Output

- A complete risk assessment or substantiated `GOOD_ENOUGH` / `NO_MATERIAL_CONCERNS` payload for Refiner to validate and append as evidence and recommendations only, including provenance and applicability; Manager decides disposition and only approved `MITIGATE` can authorize correction
- A successful validation may conclude no material repository-fit contradiction or unnecessary mechanism after documenting the falsification attempt
- Applicable edge cases and integration risks grounded in repository paths
- continuation payload with the existing session identities and an explicit Manager-disposition requirement; no direct correction or self-authorization
- Library-specific gotchas only when consequential and supported by evidence
- Risks ranked by context relevance

This agent is part of the Manager-selected `rnd-refiner` repository pair. It is typically spawned by RnD-Refiner, not dispatched directly. Direct dispatch is rare and only for standalone adversarial review of an existing repository-native realization.

## How It Works
RnD-CounterImprover reads the repository-native realization from the shared adversarial log and selected design context, traces local paths and ownership first, and uses external evidence only when needed to verify a consequential dependency/API or failure mechanism. It ranks applicable findings by context relevance and returns risk assessment or good-enough validation payloads. It is a white-hat adversary — success is measured by improving or credibly validating the realization, not by finding more risks.

## GitHub Actions context (when relevant)

If the dispatched work touches Git/GitHub evidence, include in the dispatch:

- **GitHub Actions context:** the target workflow/repository and what evidence is needed (workflow definitions, `gh` run/log/artifact outcomes).
- **Remote-Docker constraint:** local Docker is unavailable; any Docker/attestation work targets GitHub-hosted runners (`gg-artifacts`).
- **PAT/`gh` assumption:** read evidence via the existing PAT-authenticated `gh` CLI directly through the terminal (`gg-env`); this agent critiques, it does not implement or execute the workflow.
- **Result-iteration requirement:** when the risk assessment depends on run/artifact results, require the agent to state how collected results feed the next iteration (`gg-actions`).

Keep the exact-reference and authoritative-request conventions above intact when composing the dispatch.
