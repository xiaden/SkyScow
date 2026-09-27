"""Compatibility facade for the Change DAG operations surface.

The implementation lives in cohesive sibling modules (suffix
``change_dag_ops_*``); this module exists for API stability and discoverability.
The shared mutation discipline -- read, reject while running, build a candidate,
validate with :func:`change_dag.validate_dag`, then persist atomically -- is
owned by ``change_dag_ops_mutation``, not reimplemented here.

Operation domains:

* ``change_dag_ops_create``   -- initial DAG creation from a handle-space graph
* ``change_dag_ops_mutation`` -- mutation of an existing persisted DAG
* ``change_dag_ops_views``    -- read-only preview / validate / show projections
* ``change_dag_ops_support``  -- shared low-level substrate (load/persist/lock)

Existing callers and tests keep importing the public operations directly::

    from common.helpers.change_dag_ops import create_dag, preview, validate
"""
from __future__ import annotations

from .change_dag_ops_create import create_dag
from .change_dag_ops_mutation import (
    add_requirement,
    add_work,
    remove_node,
    update_node,
)
from .change_dag_ops_views import preview, show, validate

__all__ = [
    "create_dag",
    "add_requirement",
    "add_work",
    "update_node",
    "remove_node",
    "preview",
    "validate",
    "show",
]
