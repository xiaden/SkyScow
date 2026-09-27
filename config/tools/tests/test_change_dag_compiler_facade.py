"""Compatibility facade for the Change DAG compiler package.

The compiler was split into cohesive ``change_dag_compiler_*`` modules while
``common.helpers.change_dag_compiler`` remains the public import surface. These
tests pin that re-export boundary so a future module move cannot silently break
source compatibility for existing callers and tests.
"""
from __future__ import annotations

import sys
from pathlib import Path

TOOLS = Path(__file__).parents[1]
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from common.helpers import change_dag_compiler  # noqa: E402
from common.helpers import change_dag_compiler_lowering  # noqa: E402
from common.helpers import change_dag_compiler_model  # noqa: E402
from common.helpers import change_dag_compiler_phase  # noqa: E402
from common.helpers import change_dag_compiler_reconcile  # noqa: E402
from common.helpers import change_dag_compiler_runtime  # noqa: E402


def test_facade_reexports_the_owning_implementations():
    assert change_dag_compiler.compile_phase is change_dag_compiler_phase.compile_phase
    assert change_dag_compiler.preflight is change_dag_compiler_phase.preflight
    assert change_dag_compiler.compile_operations is change_dag_compiler_lowering.compile_operations
    assert change_dag_compiler.apply_compiled is change_dag_compiler_runtime.apply_compiled
    assert change_dag_compiler.node_present is change_dag_compiler_runtime.node_present
    assert change_dag_compiler.Phase is change_dag_compiler_model.Phase


def test_facade_reexports_private_compat_helpers():
    assert change_dag_compiler._changed_span is change_dag_compiler_reconcile._changed_span
    assert change_dag_compiler._compose_replacements is change_dag_compiler_reconcile._compose_replacements
    assert change_dag_compiler._spans_conflict is change_dag_compiler_reconcile._spans_conflict
    assert change_dag_compiler._already_applied is change_dag_compiler_runtime._already_applied
    assert change_dag_compiler._move_outcome is change_dag_compiler_runtime._move_outcome


def test_facade_public_api_names_are_importable():
    for name in change_dag_compiler.__all__:
        assert hasattr(change_dag_compiler, name), name
