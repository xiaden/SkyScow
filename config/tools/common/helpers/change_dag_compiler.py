"""Compatibility facade for the Change DAG compiler.

The implementation lives in cohesive sibling modules (suffix
``change_dag_compiler_*``); this module exists for API stability and
discoverability. Importers may keep using::

    from common.helpers.change_dag_compiler import compile_phase
    from common.helpers import change_dag_compiler

Canonical architecture (do not add a second derivation path):

* :func:`compile_phase` is the **canonical operational primitive** -- the single
  authoritative answer to "given DAG + Execution State + repository view, what
  is the next compiler phase?" Execution and simulation both derive from it.
* :func:`compile_whole_dag` and :func:`compile_lower_work` are **simulations
  over the shared** :func:`_lower_progression` driver; preview compiles the
  whole DAG once and passes that compilation to :func:`preflight`.
* :func:`apply_compiled`, :func:`node_present`, :func:`source_fingerprint`,
  :func:`_already_applied`, and :func:`_move_outcome` are **runtime
  application/recovery compatibility exports**, not compiler derivation paths.

Module map:

* ``change_dag_compiler_model``     -- shared types and the repository view
* ``change_dag_compiler_graph``     -- gating, readiness, frontier calculations
* ``change_dag_compiler_reconcile`` -- same-frontier edit reconciliation
* ``change_dag_compiler_lowering``  -- mechanical create/edit/remove/move lowering
* ``change_dag_compiler_phase``     -- compile_phase / _lower_progression / simulations
* ``change_dag_compiler_runtime``   -- application and recovery classification
"""
from __future__ import annotations

from . import change_dag_compiler_reconcile as _reconcile
from . import change_dag_compiler_runtime as _runtime
from .change_dag_compiler_graph import (
    lower_work_frontiers,
    ready_run_nodes,
)
from .change_dag_compiler_lowering import compile_operations
from .change_dag_compiler_model import (
    Blocked,
    CompiledOp,
    Conflict,
    Phase,
)
from .change_dag_compiler_phase import (
    compile_lower_work,
    compile_phase,
    compile_whole_dag,
    preflight,
    summarize,
)
from .change_dag_compiler_runtime import (
    apply_compiled,
    node_present,
    source_fingerprint,
)

# Private helpers kept importable from the facade for existing callers/tests.
# These are compatibility re-exports, not part of the public API in ``__all__``.
_changed_span = _reconcile._changed_span
_compose_replacements = _reconcile._compose_replacements
_spans_conflict = _reconcile._spans_conflict
_already_applied = _runtime._already_applied
_move_outcome = _runtime._move_outcome

__all__ = [
    "CompiledOp",
    "Conflict",
    "Blocked",
    "Phase",
    "compile_operations",
    "compile_phase",
    "compile_whole_dag",
    "compile_lower_work",
    "lower_work_frontiers",
    "apply_compiled",
    "ready_run_nodes",
    "preflight",
    "node_present",
    "source_fingerprint",
    "summarize",
]
