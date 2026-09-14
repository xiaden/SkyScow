# Compatibility Boundaries

No backwards-compatibility shims. When an internal API, schema, artifact format, or architecture is replaced, migrate all active callers and delete the superseded implementation in the same change. Do not retain aliases, deprecated parameter names, fallback readers, dual-write paths, legacy branches, or compatibility wrappers. Git is the source-code archive. If persisted data requires migration, write an explicit one-way migration to the current format; the active application supports only the current format.

## External-boundary exception (deterministic classification)

Compatibility code may exist only at an explicitly identified externally owned boundary. The canonical definition and lifecycle of this exception are owned by `/home/opencode/.config/opencode/skills/code-migration/SKILL.md`; do not maintain a divergent copy here.

Compatibility is permitted only when the boundary is explicitly identified and named in the change, the compatibility path is marked as temporary migration infrastructure, and a removal condition is defined — the observable event after which the path is deleted. Every internal surface still follows the no-shim rule above. The boundary classes and the lifecycle of this exception are canonically defined in `/home/opencode/.config/opencode/skills/code-migration/SKILL.md` ("External-Boundary Exception"); apply them there.

If an explicit persisted or public boundary requires classification, classify it against the canonical boundary classes in that skill and apply its lifecycle conditions; do not skip the classification. Otherwise, do not stop to ask whether an explicitly requested replacement should preserve the old internal path: it should not.

Every trigger in this file is an observable repository or task fact.
