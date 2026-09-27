"""Same-frontier edit reconciliation for the Change DAG compiler.

One cohesive reasoning unit: editing one path from several peer edit nodes.
It parses a single edit node's patch, extracts base-coordinate changed spans,
composes replacements, detects overlap, and reconciles peers that share one
lower-work base. It must not lower whole operations or decide graph gating.
"""
from __future__ import annotations

from . import change_dag
from .change_dag_patch import (
    FilePatch,
    PatchContextError,
    PatchError,
    apply_file_patch,
    detect_eol,
    normalize_eol,
    parse_unified_diff,
)


def _parse_edit_node_patch(node_id: str, node: dict, path: str) -> FilePatch:
    """Parse one file patch and require its canonical target to equal ``path``.

    Generic multi-file parsing remains available to other callers; edit nodes do
    not accept multiple sections or special targets such as ``/dev/null``.
    """
    patches = parse_unified_diff(node["patch"])
    if len(patches) != 1:
        raise PatchError(
            f"edit node {node_id} must describe exactly one file operation, but its "
            f"patch contains {len(patches)} file sections"
        )
    parsed = patches[0]
    try:
        target = change_dag.canonical_path(parsed.path)
    except ValueError as exc:
        raise PatchError(
            f"edit node {node_id} patch target {parsed.path!r} is not a usable "
            f"workspace-relative path: {exc}"
        ) from exc
    if target != path:
        raise PatchError(
            f"edit node {node_id} patch target {parsed.path!r} does not match "
            f"declared path {path!r}"
        )
    return parsed


def _parse_edit_nodes(
    nodes_map: dict[str, dict], node_ids: list[str], path: str
) -> tuple[list[FilePatch], list[str]]:
    parsed: list[FilePatch] = []
    owners: list[str] = []
    for node_id in node_ids:
        parsed.append(_parse_edit_node_patch(node_id, nodes_map[node_id], path))
        owners.append(node_id)
    return parsed, owners


def _changed_span(hunk) -> tuple[int, int, list[str]] | None:
    """Return the changed span in original-file coordinates."""
    changed = [index for index, raw in enumerate(hunk.lines) if raw[:1] in {"+", "-"}]
    if not changed:
        return None
    if hunk.old_count == 0:
        # Zero-count insertions use the same anchor as apply_file_patch.
        anchor = hunk.old_start
        new_lines = [raw[1:] for raw in hunk.lines if raw[:1] == "+"]
        return anchor, anchor, new_lines
    first, last = changed[0], changed[-1]
    base_start = hunk.old_start - 1 + sum(
        1 for raw in hunk.lines[:first] if raw[:1] in {" ", "-"}
    )
    base_end = hunk.old_start - 1 + sum(
        1 for raw in hunk.lines[: last + 1] if raw[:1] in {" ", "-"}
    )
    new_lines = [raw[1:] for raw in hunk.lines[first : last + 1] if raw[:1] in {" ", "+"}]
    return base_start, base_end, new_lines


def _compose_replacements(base: str, replacements: list[tuple[int, int, list[str]]]) -> str:
    """Apply base-coordinate replacements simultaneously (descending, indices hold)."""
    eol = detect_eol(base)
    normalized = normalize_eol(base)
    trailing = normalized.endswith("\n")
    lines = normalized.split("\n")
    if trailing:
        lines = lines[:-1]
    for start, end, new_lines in sorted(
        replacements, key=lambda item: (item[0], item[1]), reverse=True
    ):
        lines[start:end] = new_lines
    result = "\n".join(lines)
    if trailing:
        result += "\n"
    if eol != "\n":
        result = result.replace("\n", eol)
    return result


def _spans_conflict(
    left: tuple[int, int, list[str]], right: tuple[int, int, list[str]]
) -> bool:
    """True when two base-coordinate replacements cannot be composed."""
    left_start, left_end, _left_lines = left
    right_start, right_end, _right_lines = right
    if left_start == left_end and right_start == right_end:
        # Two pure insertions at the same anchor have no defined order.
        return left_start == right_start
    return left_start < right_end and right_start < left_end


def _overlap_components(
    proposals: list[tuple[str, list[tuple[int, int, list[str]]]]],
) -> list[list[str]]:
    """Group peers whose changed spans overlap (one deterministic cluster each)."""
    adjacency: dict[int, set[int]] = {index: set() for index in range(len(proposals))}
    for left in range(len(proposals)):
        for right in range(left + 1, len(proposals)):
            if any(
                _spans_conflict(first, second)
                for first in proposals[left][1]
                for second in proposals[right][1]
            ):
                adjacency[left].add(right)
                adjacency[right].add(left)
    clusters: list[list[str]] = []
    visited: set[int] = set()
    for index in range(len(proposals)):
        if index in visited or not adjacency[index]:
            continue
        stack = [index]
        members: list[str] = []
        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)
            members.append(proposals[current][0])
            stack.extend(sorted(adjacency[current] - visited))
        clusters.append(sorted(members, key=change_dag._numeric_id))
    clusters.sort(key=lambda group: change_dag._numeric_id(group[0]))
    return clusters


def _reconcile_frontier_edits(
    base: str,
    edit_nodes: list[str],
    nodes_map: dict[str, dict],
    depths: dict[str, int],
    path: str,
    *,
    base_is_authored: bool,
    base_nodes: list[str] | None = None,
) -> tuple[str, list[tuple[list[str], str, str]]]:
    """Reconcile same-frontier peers against one lower-work base.

    Deeper frontiers transform the base; peers at one depth compose only
    non-overlapping changes against that shared base. Returns text and conflicts.
    """
    problems: list[tuple[list[str], str, str]] = []
    frontiers: dict[int, list[str]] = {}
    for node_id in edit_nodes:
        frontiers.setdefault(depths.get(node_id) or 0, []).append(node_id)

    def applies_to(text: str, peer: str) -> bool:
        """True when ``peer`` applies cleanly to ``text`` (parse + exact apply)."""
        try:
            file_patch = _parse_edit_node_patch(peer, nodes_map[peer], path)
            apply_file_patch(text, file_patch, path=path)
        except PatchError:
            return False
        return True

    current = base
    # Provenance of the content a failing hunk is compared against. ``base`` is
    # DAG-produced when it is a create's content or an earlier segment's result
    # (``base_is_authored``); deeper frontiers accepted inside this call also
    # transform ``current``. Only a failure attributable to such accepted
    # DAG-produced content is a deterministic contradiction -- a failure against
    # pure live content is ordinary recoverable drift, regardless of which hunk
    # failed. ``contributors`` names the accepted work reflected in ``current``.
    contributors: list[str] = list(base_nodes or [])
    transformed = False
    for depth in sorted(frontiers, reverse=True):
        before = len(problems)
        peers = frontiers[depth]
        applied: list[tuple[str, list[tuple[int, int, list[str]]]]] = []
        failed: list[tuple[str, Exception]] = []
        for peer in peers:
            try:
                parsed = [_parse_edit_node_patch(peer, nodes_map[peer], path)]
            except PatchError as exc:
                failed.append((peer, exc))
                continue
            probe = current
            try:
                for file_patch in parsed:
                    probe = apply_file_patch(probe, file_patch, path=path)
            except PatchError as exc:
                failed.append((peer, exc))
                continue
            spans: list[tuple[int, int, list[str]]] = []
            for file_patch in parsed:
                for hunk in file_patch.hunks:
                    span = _changed_span(hunk)
                    if span is not None:
                        spans.append(span)
            applied.append((peer, spans))

        if failed and applied:
            # A peer that fails against the shared accepted state but applies to
            # peer output is attempting a same-frontier dependency.
            peer_output = _compose_replacements(
                current, [span for _peer, spans in applied for span in spans]
            )
            resolved: set[str] = set()
            for peer, exc in failed:
                if not isinstance(exc, PatchContextError):
                    continue
                try:
                    probe = peer_output
                    for file_patch in [_parse_edit_node_patch(peer, nodes_map[peer], path)]:
                        probe = apply_file_patch(probe, file_patch, path=path)
                except PatchError:
                    continue
                problems.append((
                    [peer, *[other for other, _spans in applied]],
                    f"context_conflict: {peer} requires content produced by same-frontier "
                    f"peer work in {path}",
                    "intra_dag",
                ))
                resolved.add(peer)
            failed = [item for item in failed if item[0] not in resolved]

        for peer, exc in failed:
            if isinstance(exc, PatchContextError):
                # Intra-DAG only when the content the hunk failed against is
                # DAG-produced: the base itself is authored, or a deeper frontier
                # transformed ``current`` into content this peer cannot consume
                # while it still applies to the pristine base (so the
                # transformation caused the mismatch). A later hunk index alone
                # proves nothing about provenance.
                dag_produced = base_is_authored or (
                    transformed and applies_to(base, peer)
                )
                if not dag_produced:
                    problems.append(([peer], f"context_conflict: {exc.message}", "runtime"))
                    continue
                attribution = [peer, *contributors]
                if contributors:
                    message = (
                        f"context_conflict: {peer} does not apply to the content produced by "
                        f"{', '.join(contributors)} for {path}: {exc.message}"
                    )
                elif base_is_authored:
                    message = (
                        f"context_conflict: {peer} does not apply to the content produced by "
                        f"earlier DAG work for {path}: {exc.message}"
                    )
                else:  # pragma: no cover - dag_produced implies a contributor
                    message = (
                        f"context_conflict: {peer} does not apply to the accepted lower state "
                        f"for {path}: {exc.message}"
                    )
                problems.append((attribution, message, "intra_dag"))
            else:
                problems.append(([peer], f"compile_conflict: malformed patch: {exc}", "intra_dag"))

        for cluster in _overlap_components(applied):
            problems.append((
                cluster,
                f"context_conflict: same-frontier peers {cluster} modify overlapping "
                f"source in {path}",
                "intra_dag",
            ))

        if len(problems) == before and applied:
            current = _compose_replacements(
                current, [span for _peer, spans in applied for span in spans]
            )
            contributors.extend(peer for peer, _spans in applied)
            transformed = True
    return current, problems
