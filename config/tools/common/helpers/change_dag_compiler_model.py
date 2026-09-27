"""Shared Change DAG compiler model: operation/conflict/blocked/phase types.

This is the lowest compiler layer. It owns the value types produced by lowering
and the read-only repository view that compilation and simulation both read
through. It deliberately depends only on :mod:`change_dag` and
:mod:`change_dag_patch`; it must never import a higher compiler layer, so every
other ``change_dag_compiler_*`` module may depend on it without a cycle.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from . import change_dag
from .change_dag_patch import PatchError, read_text_preserving

MECHANICAL_TYPES = ("create", "edit", "remove", "move")


@dataclass
class CompiledOp:
    nodes: list[str]
    op: str
    path: str
    from_path: str | None = None
    to_path: str | None = None
    content: str | None = None
    patches: list | None = None
    # Concrete patch text and resulting content for Work Log/recovery evidence.
    patch_text: str | None = None
    applied: str | None = None
    # Accepted lower-work base for multi-peer composition; application rechecks it.
    base_text: str | None = None
    # Move destination replacement policy; false is the default recoverable collision.
    overwrite: bool = False


@dataclass
class Conflict:
    path: str
    nodes: list[str]
    reason: str
    # ``intra_dag`` is deterministic/non-executable; ``runtime`` is recoverable drift.
    scope: str = "intra_dag"


@dataclass
class Blocked:
    node_id: str
    reason: str


@dataclass
class Phase:
    """The shared next step for runtime execution and in-memory simulation."""

    ops: list[CompiledOp]
    conflicts: list[Conflict]
    blocked: list[Blocked]
    ready_runs: list[str]


class _RepoView:
    """Read-only file access used by compilation.

    The default view reads the live repository. Whole-DAG preflight passes a
    simulated overlay so higher work is lowered against the *in-memory* result of
    accepted lower work, never a projected worktree and never a repository write.
    """

    def __init__(self, workspace_root: Path, overlay: dict[str, str] | None = None,
                 removed: set[str] | None = None) -> None:
        self._root = Path(workspace_root)
        self._overlay = overlay if overlay is not None else {}
        self._removed = removed if removed is not None else set()

    def is_dag_written(self, path: str) -> bool:
        """True when the simulated DAG has already written this path."""
        return path in self._overlay

    def is_dag_removed(self, path: str) -> bool:
        """True when the simulated DAG has already removed this path."""
        return path in self._removed

    def exists(self, path: str) -> bool:
        if path in self._overlay:
            return True
        if path in self._removed:
            return False
        return (self._root / path).exists()

    def is_file(self, path: str) -> bool:
        if path in self._overlay:
            return True
        if path in self._removed:
            return False
        return (self._root / path).is_file()

    def read(self, path: str) -> str:
        if path in self._overlay:
            return self._overlay[path]
        if path in self._removed:
            raise PatchError(f"path was removed by earlier DAG work: {path}")
        return read_text_preserving(self._root / path)

    def put(self, path: str, content: str) -> None:
        self._overlay[path] = content
        self._removed.discard(path)

    def delete(self, path: str) -> None:
        self._overlay.pop(path, None)
        self._removed.add(path)


def _finalize(conflicts: list[Conflict], blocked: list[Blocked]) -> None:
    """Apply the compiler's deterministic conflict/blocked ordering.

    Shared by lowering (:func:`compile_operations`) and the progression driver so
    every returned conflict/blocked list uses one canonical ordering.
    """
    conflicts.sort(key=lambda conflict: (conflict.path, conflict.reason, conflict.nodes))
    blocked.sort(key=lambda entry: change_dag._numeric_id(entry.node_id))
