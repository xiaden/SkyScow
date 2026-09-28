# Routing Authority

SkyScow separates four concerns that are easy to conflate: *who owns the next unit of work*,
*how the work is handed off*, *doing the work*, and *returning the result*. Each concern has
exactly one owner.

| Layer | Owner | Responsibility |
|---|---|---|
| Controller / bootstrap | `nyx` (agent) | Receives the request, captures request context, controls Change DAG lifecycle, and owns return transitions. It boots into the routing authority; it does not restate routing policy. |
| Owner selection | [`work-routing`](../../config/skills/work-routing/SKILL.md) (skill) | The single general authority for direct-versus-delegated work, task tiers, bounded localization, implementation-size routing, R&D evaluation routing, progressive research escalation, researcher scope signals, and support/QA owner selection. |
| Handoff construction | [`dispatching-agents`](../../config/skills/dispatching-agents/SKILL.md) (skill) | Given an already-selected owner, builds the dispatch prompt from that owner's per-agent reference and output contract. It does not choose the owner. |
| Domain execution | The selected specialist agent | Performs the bounded work within its declared capability boundary and returns its output contract. |

```
Nyx                      -> controller / bootstrap
work-routing             -> owner selection
dispatching-agents       -> handoff construction
specialist agent         -> domain execution
```

Specialist agent files declare their own capability boundaries, inputs, and outputs. They do not
maintain a competing general routing matrix or task-tier policy. Agent-authoring guidance
(`making-editing-agents`) teaches this split so regenerated agents do not reintroduce unfamiliarity
or file-count based routing.

The routing rules themselves live only in the canonical skill. This document describes the authority
split, not the policy; do not duplicate the rules here.

## References

- [`config/skills/work-routing/SKILL.md`](../../config/skills/work-routing/SKILL.md) — canonical owner-selection policy
- [`config/skills/dispatching-agents/SKILL.md`](../../config/skills/dispatching-agents/SKILL.md) — dispatch mechanics
- [`config/agents/nyx.md`](../../config/agents/nyx.md) — controller / bootstrap
- [R&D and design documents](rnd-and-design.md) — RnD-Manager route and design-evidence ownership
