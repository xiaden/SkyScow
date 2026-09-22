"""Shared mutation primitives for implementation-graph tools."""
from __future__ import annotations

from typing import Any, Callable

from ..helpers.implementation_graph import mutate_graph


def mutate(graph_id: str, workspace_root, callback: Callable[[dict[str, Any]], dict[str, Any]], *, actor: str | None = None):
    # Actor is retained for tool-call compatibility; graph mutations record state
    # provenance in the callback payload rather than accepting an unsupported kwarg.
    return mutate_graph(workspace_root, graph_id, callback)
