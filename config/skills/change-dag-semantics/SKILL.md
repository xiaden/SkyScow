---
name: change-dag-semantics
description: Defines Change DAG semantic nodes and valid semantic decomposition. Use when authoring, reviewing, or refining semantic nodes and their decomposition; do not use for terminal work realization, DAG lifecycle operation, or owner routing.
---

## Semantic node definition

A postcondition over a bounded subject scope whose satisfaction contributes directly to satisfying its parent/root obligation.

A semantic node describes WHAT must be true; it must not be an implementation action. Valid: “All QueryService callers use the bulk lookup contract.” Invalid: “Edit query_service.py to call bulk_lookup().”

**Subject identity clarification.** Naming an established repository or domain subject is valid when it bounds the postcondition. Prescribing the implementation action, or gratuitously choosing the representation that satisfies it, is not.

Examples:

- VALID: “All callers of QueryService use the bulk lookup contract.”
- VALID: “API consumers preserve canonical lookup semantics.”
- VALID: “Requirements-store behavior is regression verified.”
- INVALID: “Edit src/query_service.py.”
- INVALID: “Call bulk_lookup() from lines 40-60.”
- INVALID: “Add tests to test_query_service.py.”

## Two decomposition reasons

Semantic decomposition has exactly two legitimate motivations: MEANING and SCALE.

### MEANING

The parent contains multiple distinct required states that need separate reasoning and/or causal structure. For example, parent “Requirements persist and reads expose them.” may have children “Requirements persist according to lifecycle semantics.” and “Reads expose applicable current requirements.”

### SCALE

The same coherent postcondition spans too much implementation surface for one bounded Worker authoring context. For example, parent “All consumers use canonical lookup semantics.” may have children “All API consumers use canonical lookup semantics.”, “All background consumers use canonical lookup semantics.”, and “All CLI consumers use canonical lookup semantics.”

For SCALE:

- Preserve the parent’s semantic predicate and narrow only the subject scope.
- Children must be collectively exhaustive for the delegated parent scope.
- Prefer independently authorable partitions.
- File count alone is not a semantic criterion.
- Implementation breadth/context cost MAY justify decomposition.
- Partition axes may be subsystem, package, caller family, migration cohort, component, generated/manual boundary, or another repository-grounded scope.

Do not introduce a `workset` node type or a taxonomy field.

## Parent/child completeness

For a `decomposition_only` semantic parent, the primary completeness test is:

satisfaction(all direct semantic children) implies satisfaction(parent)

For SCALE decomposition, conceptually `union(child subject scopes) = delegated parent subject scope`. No formal persisted scope sets or new schema fields are required.

For MEANING decomposition, the combined child postconditions must fully account for the delegated parent obligation. Pure paraphrase or recursive restatement is invalid.

## Sibling and causal semantics

Sibling semantic nodes assert authoring independence. The canonical operational test is:

Could B be correctly authored if A's implementation had not yet been proposed or accepted?

YES → they may remain independent siblings. NO → B requires A.

Numeric node order, shared files, the same subsystem, similar implementation order, or similar depth do not create causality. SCALE siblings are not automatically dependent merely because they implement the same parent predicate.

## Semantic versus terminal boundary

Semantic means desired state/postcondition. Terminal means exact create/edit/remove/move/run realization. For example, semantic “API consumers use canonical lookup semantics.” contrasts with terminal `edit foo.py` / `edit bar.py`.

A semantic node may recursively refine until exact lowering is safely bounded.

## Mixed semantic and terminal children

The current structural rules are unchanged by this skill. Prefer either complete direct realization through terminals, or complete semantic delegation through children. Mixed semantic children plus parent-owned terminal work are allowed only when the parent retains a clear residual semantic responsibility represented by those terminals. Do not use mixed structure merely because work was discovered incrementally.

A semantic node may have at most one direct `run` child. When it directly requires a `run`, every other required child must be semantic. `edit` is the only composable direct terminal kind; `create`/`remove`/`move`/`run` are exclusive.

## Scale is not split by file

Reject this anti-pattern: parent “All callers use X.” → children “Edit foo.py.” / “Edit bar.py.” Those are implementation actions, not semantic scale partitions.

A valid scale partition is “All API callers use X.” / “All worker callers use X.” / “All CLI callers use X.” It preserves the same predicate while narrowing subject scope.

A repository path MAY appear in a semantic requirement only when the path itself is an authoritative subject/contract, not merely because it is the file expected to be edited.
