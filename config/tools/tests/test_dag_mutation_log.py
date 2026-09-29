"""Focused tests for bounded Change DAG mutation-log reads."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from common.helpers.change_dag_mutation_log import mutation_log_path
from common.helpers.change_dag_ops_create import create_dag
from common.tools.dag_mutation_log import dag_mutation_log


def _create(workspace: Path, slug: str = "demo") -> None:
    result = create_dag(
        workspace,
        slug,
        {
            "root": "root",
            "nodes": {
                "root": {"requirement": "root", "requires": ["child"]},
                "child": {"requirement": "child"},
            },
        },
    )
    assert "error" not in result


def _write_events(workspace: Path, slug: str = "demo", count: int = 4) -> None:
    path = mutation_log_path(workspace, slug)
    path.write_text(
        "".join(json.dumps({"sequence": sequence, "operation": f"op-{sequence}"}) + "\n" for sequence in range(1, count + 1)),
        encoding="utf-8",
    )


def _payload(result: dict) -> dict:
    assert "error" not in result
    return json.loads(result["output"])


def test_returns_recent_entries_with_offset_and_bounded_limit(workspace):
    _create(workspace)
    _write_events(workspace)

    payload = _payload(dag_mutation_log("demo", offset=1, limit=2, workspace_root=workspace))

    assert payload == {
        "slug": "demo",
        "location": "pending",
        "offset": 1,
        "limit": 2,
        "total": 4,
        "entries": [
            {"sequence": 3, "operation": "op-3"},
            {"sequence": 2, "operation": "op-2"},
        ],
    }


def test_rejects_invalid_bounds(workspace):
    _create(workspace)

    assert dag_mutation_log("demo", offset=-1, workspace_root=workspace)["error"] == "invalid_bounds"
    assert dag_mutation_log("demo", limit=0, workspace_root=workspace)["error"] == "invalid_bounds"
    assert dag_mutation_log("demo", limit=51, workspace_root=workspace)["error"] == "invalid_bounds"


def test_missing_legacy_log_is_empty(workspace):
    _create(workspace)
    mutation_log_path(workspace, "demo").unlink()

    payload = _payload(dag_mutation_log("demo", workspace_root=workspace))

    assert payload["location"] == "pending"
    assert payload["entries"] == []
    assert payload["total"] == 0


def test_reads_archived_log_without_mutating_it(workspace):
    _create(workspace)
    _write_events(workspace)
    pending_bundle = workspace / "artifacts/change-dags/pending/demo"
    archived_bundle = workspace / "artifacts/change-dags/archived/demo"
    archived_bundle.parent.mkdir(parents=True)
    shutil.move(str(pending_bundle), str(archived_bundle))
    before = (archived_bundle / "DAG_MUTATIONS.jsonl").read_bytes()

    payload = _payload(dag_mutation_log("demo", limit=1, workspace_root=workspace))

    assert payload["location"] == "archived"
    assert payload["entries"] == [{"sequence": 4, "operation": "op-4"}]
    assert (archived_bundle / "DAG_MUTATIONS.jsonl").read_bytes() == before


def test_plugin_registers_bounded_mutation_log_bridge():
    source = Path(__file__).parents[2] / "plugins" / "tools.ts"
    text = source.read_text(encoding="utf-8")
    start = text.index("dag_mutation_log: tool(")
    end = text.index("\n  }),", start)
    block = text[start:end]

    assert 'runPythonTool("common.tools.dag_mutation_log"' in block
    assert "offset:" in block
    assert "limit:" in block
