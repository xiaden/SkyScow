# Process-Artifact Context — Usage Examples

## Contents
- [RnD-Manager Using This Skill](#example-rnd-manager-using-this-skill)
- [Nyx Using This Skill](#example-nyx-using-this-skill)

---

## Example: RnD-Manager Using This Skill

```
# Before writing the design doc:

1. Identify task: design — "notification system for scan completion"
   Scope: src/services, src/workflows/processing, frontend/

2. Load current governance when it is materially relevant.
   The workspace-local `architecture-decisions` skill indexes governing ADRs and the
   `system-requirements` skill indexes active ASRs; read a known record by identity:
   adr_read(name="ADR-003") / asr_read(name="ASR-0001").

3. Spawn Support-Librarian for process history:
   "Search the retained process artifacts for everything relevant to this task:
   Task: design — notification system for scan completion
   Scope: src/services, src/workflows/processing, frontend/
   Specific concerns:
   - Has anyone tried WebSocket-based notifications before?
   - What dead ends were recorded in the notification/event area?
   Return a structured briefing with warnings, context, and open questions.
   Do not search for governing ADRs/ASRs — the caller loads the governance skill."

4. Librarian returns process history:
   - Warning: Log shows WebSocket attempt was abandoned (connection pooling issues)
   - Context: prior design doc DD-schema-refactor-v1 added event tracking tables

5. RnD-Manager composes the smallest sufficient DD graph from the governance record,
   process history, and request evidence. After the selected evidence and decision
   gates, DDAuthor writes the design doc that:
   - Uses state-flag polling instead of event pipeline (respects ADR-003 from the
     `architecture-decisions` skill)
   - Avoids WebSockets (heeds the recorded dead end)
   - Leverages existing event tracking tables (uses context)
```

## Example: Nyx Using This Skill

```
# Before routing a feature to R&D:

1. Identify task: design — "playlist generation from ML embeddings"
   Scope: src/components/ml, src/workflows

2. Load the workspace-local `architecture-decisions` skill for governing decisions
   (e.g. adr_read(name="ADR-001")), then spawn Support-Librarian for process history.

3. Librarian returns process history:
   - Context: Prior design doc exists for embedding pipeline
   - Warning: An earlier TF Lite spike was abandoned as a dead end

4. Nyx includes in dispatch to RnD-Manager:
   "Design playlist generation feature.
   Constraints from governance and artifact review:
   - Must use ONNX runtime (ADR-001, from the `architecture-decisions` skill)
   - Prior embedding pipeline design exists — build on it, don't redesign"
```
