"""Runtime application and interruption-recovery classification.

Compiler-adjacent runtime behavior, not DAG lowering: :func:`apply_compiled`
writes compiled operations through the atomic patch primitives, and the
reconciliation helpers classify live state after an interruption
(:func:`_already_applied`, :func:`source_fingerprint`, :func:`_move_outcome`,
:func:`node_present`). It depends on the model and patch primitives only; it
must never derive compiler phases.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any

from . import change_dag
from . import change_dag_patch
from .change_dag_compiler_model import CompiledOp
from .change_dag_patch import (
    FilePatch,
    PatchContextError,
    PatchError,
    apply_patches,
    atomic_replace,
    parse_unified_diff,
    read_text_preserving,
)


def apply_compiled(ops: list[CompiledOp], workspace_root: Path) -> list[dict]:
    """Apply compiled ops atomically, re-verifying against current live state."""
    workspace_root = Path(workspace_root)
    results: list[dict] = []

    def evidence(op: CompiledOp) -> dict:
        extra: dict = {}
        if op.patch_text is not None:
            extra["patch"] = op.patch_text
        if op.content is not None:
            extra["content"] = op.content
        if op.op == "move":
            extra["from_path"] = op.from_path
            extra["to_path"] = op.to_path
            extra["overwrite"] = bool(op.overwrite)
        return extra

    def failure(op: CompiledOp, error: str, message: str = "") -> dict:
        entry = {"path": op.path, "nodes": list(op.nodes), "ok": False,
                 "action": op.op, "error": error}
        entry.update(evidence(op))
        if message:
            entry["message"] = message
        return entry

    for op in ops:
        if op.op == "create":
            path = workspace_root / op.path
            if path.exists() or path.is_symlink():
                results.append(failure(op, "context_mismatch"))
                continue
            try:
                atomic_replace(path, (op.content or "").encode("utf-8"))
            except OSError as exc:
                results.append(failure(op, "io_error", str(exc)))
                continue
            results.append({"path": op.path, "nodes": list(op.nodes), "ok": True, "action": "create", **evidence(op)})
        elif op.op == "edit":
            path = workspace_root / op.path
            if op.base_text is not None:
                # A reconciled frontier: re-verify the exact accepted base rather
                # than replaying peer patches in numeric order.
                try:
                    current = read_text_preserving(path)
                except PatchError:
                    results.append(failure(op, "context_mismatch"))
                    continue
                if current != op.base_text:
                    results.append(failure(op, "context_mismatch"))
                    continue
                updated = op.applied if op.applied is not None else current
            else:
                try:
                    current = read_text_preserving(path)
                    updated = apply_patches(current, op.patches or [], path=op.path)
                except PatchError:
                    results.append(failure(op, "context_mismatch"))
                    continue
            try:
                atomic_replace(path, updated.encode("utf-8"))
            except OSError as exc:
                results.append(failure(op, "io_error", str(exc)))
                continue
            results.append({"path": op.path, "nodes": list(op.nodes), "ok": True, "action": "edit", **evidence(op)})
        elif op.op == "remove":
            path = workspace_root / op.path
            try:
                if path.exists() or path.is_symlink():
                    path.unlink()
            except OSError as exc:
                results.append(failure(op, "io_error", str(exc)))
                continue
            results.append({"path": op.path, "nodes": list(op.nodes), "ok": True, "action": "remove", **evidence(op)})
        elif op.op == "move":
            source = workspace_root / (op.from_path or "")
            destination = workspace_root / (op.to_path or "")
            if not source.is_file():
                results.append(failure(op, "context_mismatch"))
                continue
            if not op.overwrite and (destination.exists() or destination.is_symlink()):
                results.append(failure(op, "context_mismatch"))
                continue
            try:
                # One native filesystem rename. No shell `mv`, no copy+unlink,
                # and no cross-filesystem emulation: if the filesystem cannot
                # perform the rename atomically the operation fails normally.
                if op.overwrite:
                    os.replace(source, destination)
                else:
                    os.rename(source, destination)
            except OSError as exc:
                results.append(failure(op, "io_error", str(exc)))
                continue
            results.append({"path": op.path, "nodes": list(op.nodes), "ok": True, "action": "move", **evidence(op)})
    return results


def _already_applied(current: str, patches: list[FilePatch]) -> bool:
    """True only with exact proof that ``current`` is the patches' intended result.

    Interruption reconciliation must never conclude that an interrupted edit
    succeeded without proof, so the previous "no new-side lines matched" vacuous
    success is replaced by an exact region comparison:

    * Each hunk's *new side* (context ``' '`` and added ``'+'`` lines) must match
      ``current`` contiguously. Because the region is exactly the new side, a
      replaced/removed line cannot remain inside it.
    * The position of that region in the resulting file is the hunk's F4 target:
      ``old_start - 1`` plus the accumulated ``new_count - old_count`` delta of
      the earlier hunks for a hunk that removes or keeps content, and
      ``old_start`` plus that delta for a zero-``old_count`` insertion -- the same
      coordinate :func:`change_dag_patch.apply_file_patch` writes to. It is never
      ``new_start - 1`` plus that delta, which double-counts the delta when a
      patch already carries resulting-file starts.
    * A deletion-only hunk has no new-side line to anchor the proof, so it can
      never, by itself, make the patch "applied"; the file stays ambiguous.

    Partial application, an overlapping external edit, or a wrong coordinate all
    fail the exact comparison and therefore classify as ambiguous upstream.
    """
    text = change_dag_patch.normalize_eol(current)
    lines = text.split("\n")
    if text.endswith("\n"):
        lines = lines[:-1]
    offset = 0
    proven = False
    for file_patch in patches:
        for hunk in file_patch.hunks:
            position = (
                hunk.old_start + offset
                if hunk.old_count == 0
                else hunk.old_start - 1 + offset
            )
            new_lines = [raw[1:] for raw in hunk.lines if raw[:1] in (" ", "+")]
            if position < 0 or position + len(new_lines) > len(lines):
                return False
            if lines[position : position + len(new_lines)] != new_lines:
                return False
            if new_lines:
                proven = True
            elif any(raw[:1] == "-" for raw in hunk.lines):
                # No new-side line exists to prove the intended result, and the
                # removed content is gone from view: not provably applied.
                return False
            offset += hunk.new_count - hunk.old_count
    return proven


def source_fingerprint(path: Path) -> dict[str, Any] | None:
    """Small content fingerprint of a move source, or ``None`` when unreadable.

    Operation-local recovery evidence only: it identifies the intended moved
    file across an interruption. It is not a provenance registry, snapshot
    store, or ownership record, and it never replaces the native rename.
    """
    try:
        data = Path(path).read_bytes()
    except OSError:
        return None
    return {"sha256": hashlib.sha256(data).hexdigest(), "size": len(data)}


def _move_outcome(node: dict, workspace_root: Path, fingerprint: dict | None, *, require_fingerprint: bool = False) -> str:
    """Conservatively classify an interrupted move from live path state."""
    source = workspace_root / str(node.get("from_path", ""))
    destination = workspace_root / str(node.get("to_path", ""))
    overwrite = bool(node.get("overwrite", False))
    from_exists = source.exists()
    to_exists = destination.exists() or destination.is_symlink()
    if from_exists and to_exists:
        # The source survived and something occupies the destination: nothing
        # here proves the rename happened.
        return "ambiguous"
    if from_exists:
        return "absent"
    if not to_exists:
        return "ambiguous"
    if fingerprint is not None:
        return "present" if source_fingerprint(destination) == fingerprint else "ambiguous"
    # Without recorded evidence, interruption reconciliation must not infer that
    # an occupied destination came from this move. The legacy node_present query
    # remains permissive for non-overwriting moves when no recovery evidence was
    # requested; the executor passes require_fingerprint=True during recovery.
    if require_fingerprint:
        return "ambiguous"
    return "ambiguous" if overwrite else "present"


def node_present(dag: dict, node_id: str, workspace_root: Path, *, fingerprint: dict | None = None, require_fingerprint: bool = False) -> str:
    """Classify a mechanical node against live state: present/absent/ambiguous.

    ``fingerprint`` is a move node's recorded pre-rename source fingerprint
    (see :func:`source_fingerprint`). When supplied, a destination only proves a
    move when its content matches, so reconciliation never claims a move merely
    because an unrelated file sits at the destination.
    """
    workspace_root = Path(workspace_root)
    node = change_dag.node_map(dag).get(node_id)
    if not isinstance(node, dict):
        return "ambiguous"
    kind = node.get("type")
    if kind == "create":
        path = workspace_root / str(node.get("path", ""))
        if not path.exists():
            return "absent"
        try:
            text = read_text_preserving(path)
        except PatchError:
            return "ambiguous"
        return "present" if text == node.get("content", "") else "ambiguous"
    if kind == "edit":
        path = workspace_root / str(node.get("path", ""))
        try:
            current = read_text_preserving(path)
            patches = parse_unified_diff(str(node.get("patch", "")))
        except PatchError:
            return "ambiguous"
        try:
            updated = apply_patches(current, patches, path=str(node.get("path", "")))
        except PatchContextError:
            return "present" if _already_applied(current, patches) else "ambiguous"
        except PatchError:
            return "ambiguous"
        if updated == current:
            return "present"
        if _already_applied(current, patches):
            # The new side is present, yet the patch still applies (an insertion
            # whose added content cannot be told apart from the pre-existing
            # file). It is neither provably applied nor provably safe to re-apply.
            return "ambiguous"
        return "absent"
    if kind == "remove":
        path = workspace_root / str(node.get("path", ""))
        return "present" if not path.exists() else "absent"
    if kind == "move":
        return _move_outcome(node, workspace_root, fingerprint, require_fingerprint=require_fingerprint)
    return "ambiguous"
