"""Compatibility facade for the Change DAG operations surface.

The ops module was split into cohesive ``change_dag_ops_*`` modules while
``common.helpers.change_dag_ops`` remains the public import surface. These tests
pin the re-export boundary so a future module move cannot silently break source
compatibility for the agent-facing tools and tests.
"""
from __future__ import annotations

import sys
from pathlib import Path

TOOLS = Path(__file__).parents[1]
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from common.helpers import change_dag_ops  # noqa: E402
from common.helpers import change_dag_ops_create  # noqa: E402
from common.helpers import change_dag_ops_mutation  # noqa: E402
from common.helpers import change_dag_ops_views  # noqa: E402


def test_facade_reexports_the_owning_implementations():
    assert change_dag_ops.create_dag is change_dag_ops_create.create_dag
    assert change_dag_ops.add_requirement is change_dag_ops_mutation.add_requirement
    assert change_dag_ops.add_work is change_dag_ops_mutation.add_work
    assert change_dag_ops.update_node is change_dag_ops_mutation.update_node
    assert change_dag_ops.remove_node is change_dag_ops_mutation.remove_node
    assert change_dag_ops.preview is change_dag_ops_views.preview
    assert change_dag_ops.validate is change_dag_ops_views.validate
    assert change_dag_ops.show is change_dag_ops_views.show


def test_facade_public_api_names_are_importable():
    for name in change_dag_ops.__all__:
        assert hasattr(change_dag_ops, name), name
