# Subsystem Orientation: Examples & Patterns

## Table of Contents
- [Description Field Examples](#description-field-examples)
- [Full Annotated Example](#full-annotated-example)
- [When NOT to Create a Skill](#when-not-to-create-a-skill)

---

## Description Field Examples

The `description` is the trigger selector. It must name the subsystem explicitly and list the *tasks* that should load it. Be specific enough that it doesn't fire for every session.

### Good

```yaml
description: Use when working with the discovery worker system — process isolation,
  ML job dispatch, IPC pipe protocol, worker lifecycle, or BaseWorker subclassing.
  Also covers how the service connects to workers and handles worker crashes.
```

**Why it works:** Names the subsystem ("discovery worker system"), lists concrete tasks ("IPC pipe protocol", "BaseWorker subclassing", "worker lifecycle"), and narrows scope ("Also covers...").

```yaml
description: Use when working with the entity resolution pipeline — fuzzy matching,
  deduplication, blocking strategies, candidate generation, or the match/merge
  workflow. Covers resolver configuration, scoring, and batch vs streaming modes.
```

**Why it works:** Domain-specific nouns ("entity resolution pipeline", "blocking strategies", "match/merge workflow") that an agent can match against task descriptions.

```yaml
description: Use when working with the ArangoDB AQL query layer — custom AQL
  generation, query builder internals, bindVars escaping, UPSERT semantics,
  traversal queries, or cursor lifecycle management.
```

**Why it works:** Lists specific gotchas ("bindVars escaping", "UPSERT semantics") that trigger loading when an agent encounters problems in those areas.

### Bad

```yaml
description: Use when working with workers or ML.
```

**Why it fails:** Too vague — "workers or ML" matches hundreds of possible contexts. The agent can't determine when this skill is relevant.

```yaml
description: Use when working with the database.
```

**Why it fails:** Every project has a database. This loads on every session.

```yaml
description: Covers the batch processing system.
```

**Why it fails:** No trigger phrase ("Use when...", "Trigger when..."). The agent may not recognize this as a loadable skill.

---

## Full Annotated Example

Below is a complete, well-structured subsystem orientation skill. Use it as a reference for structure, tone, and level of detail.

```markdown
---
name: discovery-workers
description: Use when working with the discovery worker system — process
  isolation, ML job dispatch, IPC pipe protocol, worker lifecycle, or
  BaseWorker subclassing. Also covers how the service connects to workers
  and handles worker crashes.
---

# Discovery Worker Subsystem

The discovery service spawns isolated child processes (workers) to run ML
classification jobs. Each worker communicates with the service over a
bidirectional IPC pipe using a length-prefixed binary protocol. Workers are
stateless per job — they receive input, compute a result, and return it.
The service handles worker lifecycle (spawn, health check, reap) and routes
jobs to available workers. Workers are never pooled; each job gets a fresh
process to avoid GPU memory fragmentation from the ML runtime.

## Coverage

**Documented:** worker IPC protocol, pipe lifecycle, BaseWorker
subclassing, service ↔ worker connection setup, crash detection

**Not yet documented:** multi-GPU scheduling policy, worker memory
limits at the ML runtime level, graceful degradation when no GPU
is available

**Last extended:** 2026-06-03

## Key Files

| Area | File |
|------|------|
| Service-side worker manager | `src/discovery/worker_manager.py` |
| IPC protocol (shared) | `src/discovery/ipc_protocol.py` |
| BaseWorker class | `src/discovery/workers/base.py` |
| Worker entry point | `src/discovery/workers/main.py` |
| Pipe transport (shared) | `src/discovery/pipe_transport.py` |
| Worker registry | `src/discovery/worker_registry.py` |

## Critical Invariants

- The service must reap every worker it spawns — leaked zombie
  processes accumulate GPU memory (the ML runtime holds VRAM until
  the process exits)
- Pipe writes are not atomic — always use the length-prefixed
  framing from `ipc_protocol.py`, never write raw bytes
- Workers must never import service modules — the import chain
  pulls in the GPU context, which crashes if no GPU is present
- The worker entry point must `os._exit()` on unhandled errors —
  regular `sys.exit()` triggers atexit handlers that can hang
  on GPU cleanup

## Common Task Patterns

### Adding a new worker type
1. Subclass `BaseWorker` in `src/discovery/workers/`
2. Implement `process()` — return a dict, not raw bytes
3. Register in `worker_registry.py` under a unique type string
4. The service discovers new types automatically via the registry

### Debugging worker crashes
- Check `stderr` captured by `pipe_transport.py` (it buffers child
  stderr separately from the IPC pipe)
- Enable `DISCOVERY_WORKER_DEBUG=1` to keep worker processes alive
  after errors for `gdb` attachment
- The service logs worker exit codes in `worker_manager.py:reap()`

## Sources
- ADR-014: Worker process isolation model
- DD: discovery-pipeline (artifacts/designs/completed/discovery-pipeline.md)
```

---

## When NOT to Create a Skill

| Situation | Why | Better alternative |
|-----------|-----|-------------------|
| The subsystem changes frequently | Skill will be stale within weeks | Log observations in ADRs or session logs |
| The information is obvious from reading one file | No context burn to prevent | Don't create anything |
| The subsystem is one function or a thin wrapper | Over-documentation | A comment in the code is enough |
| You haven't actually done the research yet | Skill will be wrong and cause confident errors | Do the research first, then create the skill |
| A skill already exists for this area | Duplicate skills cause fragmentation | Extend the existing skill instead |

### The Coverage Section's Role in Triaging

The `## Coverage` section is the single most important signal for future agents. When an agent encounters a gap:

```
**Not yet documented:** multi-GPU scheduling policy, worker memory limits
```

...it knows the skill is incomplete and should not assume the skill covers those areas. A partial skill that labels its gaps is always preferable to no skill. A partial skill with **unlabeled** gaps causes confident wrong reasoning — worse than no skill.
