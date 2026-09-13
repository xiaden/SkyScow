# Artifact Context — Usage Examples

## Contents
- [RnD-Manager Using This Skill](#example-rnd-manager-using-this-skill)
- [Nyx Using This Skill](#example-nyx-using-this-skill)

---

## Example: RnD-Manager Using This Skill

```
# Before writing the design doc:

1. Identify task: design — "notification system for scan completion"
   Scope: src/services, src/workflows/processing, frontend/

2. Spawn Support-Librarian:
   "Search the artifact corpus for everything relevant to this task:
   Task: design — notification system for scan completion
   Scope: src/services, src/workflows/processing, frontend/
   Specific concerns:
   - Are there existing ADRs about event-driven patterns?
   - Has anyone tried WebSocket-based notifications before?
   Return a structured briefing..."

3. Librarian returns:
   - Constraint: ADR-003 requires state flags, not event pipelines
   - Warning: Log shows WebSocket attempt was abandoned (connection pooling issues)
   - Context: DD-schema-refactor-v1 added event tracking tables

4. RnD-Manager passes the briefing into the complete DD workflow. After the
   adversarial, architecture, complexity, and estimation stages, DDAuthor
   writes the design doc that:
   - Uses state-flag polling instead of event pipeline (respects ADR-003)
   - Avoids WebSockets (heeds warning)
   - Leverages existing event tracking tables (uses context)
```

## Example: Nyx Using This Skill

```
# Before routing a feature to R&D:

1. Identify task: design — "playlist generation from ML embeddings"
   Scope: src/components/ml, src/workflows

2. Spawn Support-Librarian with task context

3. Librarian returns:
   - Constraint: ADR-001 mandates ONNX for all ML inference
   - Context: Prior design doc exists for embedding pipeline

4. Nyx includes in dispatch to RnD-Manager:
   "Design playlist generation feature.
   Constraints from artifact review:
   - Must use ONNX runtime (ADR-001)
   - Prior embedding pipeline design exists — build on it, don't redesign"
```
