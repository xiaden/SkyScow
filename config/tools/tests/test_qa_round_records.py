from __future__ import annotations

import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from common.helpers.qa_round_records import (
    load_records,
    record_identity,
    record_path,
    resolve_task_family,
    subject_identity,
    validate_record,
)
from common.tools.qa_record_read import qa_record_read
from common.tools.qa_record_write import qa_record_write

TOOLS_DIR = Path(__file__).resolve().parents[1]  # config/tools


def run_python_tool(module: str, payload: dict) -> dict:
    """Run a tool module exactly as the production plugin bridge does.

    The plugin shells out to ``python3 -m common.tools.<name>`` with cwd at
    ``config/tools`` and a JSON body on stdin that includes ``workspace_root``.
    """
    completed = subprocess.run(
        [sys.executable, "-m", module],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        cwd=TOOLS_DIR,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)


def record(writer="qa-test-generator", decision="REPAIRED", family="TASK-demo", agent=None):
    return {
        "task_family": family, "round": 1, "writer": writer,
        "agent": agent or writer,
        "subject": {"kind": "behavior", "file": "x.py", "symbol": "run"},
        "decision": decision, "evidence": "analyzer finding in x.py",
        "verification": "focused pytest passed", "changed_files": ["x.py"],
        "changed_symbols": ["run"],
        "source_kind": "fixer-issue" if writer == "exec-fixer" else "analyzer-finding",
        "source_ref": "finding-1",
        **({"repair": "updated run"} if writer == "exec-fixer" else {}),
    }


def test_identity_precedence_and_no_minting():
    assert resolve_task_family(dd_family="DD-family", plan_set_family="plan") == "DD-family"
    assert resolve_task_family(plan_set_family="plan", standalone="task") == "plan"
    assert resolve_task_family(standalone="task") == "task"
    with pytest.raises(ValueError, match="existing task-family identity"):
        resolve_task_family()


@pytest.mark.parametrize(
    "record_update",
    [
        {"progress": "still working"},
        {"thoughts": "private reasoning"},
        {"chain_of_thought": "hidden reasoning"},
        {"speculation": "maybe"},
        {"subject": ""},
        {"subject": {}},
        {"subject": {"kind": "behavior"}},
        {"subject": {"kind": "file"}},
        {"subject": {"file": "x.py"}},
        {"subject": {"symbol": "run"}},
        {"subject": {"kind": "  "}},
        {"round": 0},
        {"round": True},
        {"writer": "unknown-writer"},
        {"task_family": "../outside"},
        {"writer": "qa-test-generator/other"},
    ],
)
def test_schema_rejects_forbidden_unstable_and_unsafe_values(record_update):
    candidate = record()
    candidate.update(record_update)
    with pytest.raises(ValueError):
        validate_record(candidate)


def test_terminal_schema_and_fixer_scope(workspace):
    for decision in ("REPAIRED", "UNNECESSARY", "BLOCKED", "ESCALATED"):
        assert "error" not in qa_record_write(
            record(decision=decision) | {"subject": {"kind": "behavior", "symbol": decision}},
            workspace_root=workspace,
        )
    bad = record(); bad.pop("evidence")
    assert qa_record_write(bad, workspace_root=workspace)["error"] == "invalid_qa_record"
    assert qa_record_write(record(writer="exec-fixer", decision="BLOCKED"), workspace_root=workspace)["error"] == "invalid_qa_record"
    assert "error" not in qa_record_write(record(writer="exec-fixer", family="TASK-fix"), workspace_root=workspace)


def test_missing_malformed_and_cross_family_history_fail_closed(workspace):
    result = qa_record_read(workspace_root=workspace, task_family="TASK-none")
    assert json.loads(result["output"])["records"] == []
    path = record_path(workspace, "TASK-bad", 1, "qa-test-generator")
    path.parent.mkdir(parents=True)
    path.write_text('{bad\n', encoding="utf-8")
    assert qa_record_read(workspace_root=workspace, task_family="TASK-bad")["error"] == "invalid_qa_history"
    path.write_text(json.dumps(record(family="OTHER")) + "\n", encoding="utf-8")
    assert qa_record_read(workspace_root=workspace, task_family="TASK-bad")["error"] == "invalid_qa_history"


def test_write_returns_path_and_persists_before_return(workspace):
    result = qa_record_write(record(family="TASK-immediate"), workspace_root=workspace)
    assert "error" not in result
    returned = json.loads(result["output"])
    assert returned["path"] == "artifacts/logs/qa-rounds/TASK-immediate/round-1/qa-test-generator.jsonl"
    path = workspace / returned["path"]
    assert path.exists()
    assert json.loads(path.read_text(encoding="utf-8")) == returned["record"]


def test_repeat_writes_retain_every_same_writer_record(workspace):
    for index in range(5):
        result = qa_record_write(
            record(family="TASK-repeat") | {"subject": {"kind": "behavior", "symbol": f"run_{index}"}},
            workspace_root=workspace,
        )
        assert "error" not in result
    path = record_path(workspace, "TASK-repeat", 1, "qa-test-generator")
    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 5
    assert {json.loads(line)["subject"]["symbol"] for line in lines} == {f"run_{i}" for i in range(5)}


def test_concurrent_same_writer_appends_do_not_lose_lines(workspace):
    def write(index):
        return qa_record_write(
            record(family="TASK-same-writer") | {"subject": {"kind": "behavior", "symbol": f"run_{index}"}},
            workspace_root=workspace,
        )

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(write, range(20)))
    assert all("error" not in result for result in results)
    path = record_path(workspace, "TASK-same-writer", 1, "qa-test-generator")
    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 20
    assert {json.loads(line)["subject"]["symbol"] for line in lines} == {f"run_{i}" for i in range(20)}


def test_read_supports_round_writer_subject_and_decision_filters(workspace):
    entries = [
        record(family="TASK-filters") | {"round": 1, "writer": "qa-test-generator", "decision": "REPAIRED", "subject": {"kind": "behavior", "symbol": "alpha"}},
        record(family="TASK-filters") | {"round": 2, "writer": "qa-test-generator", "decision": "BLOCKED", "subject": {"kind": "behavior", "symbol": "beta"}},
        record(family="TASK-filters") | {"round": 2, "writer": "qa-docs-generator", "decision": "UNNECESSARY", "subject": {"kind": "interface", "symbol": "gamma"}},
    ]
    for entry in entries:
        assert "error" not in qa_record_write(entry, workspace_root=workspace)

    def read(**filters):
        result = qa_record_read(workspace_root=workspace, task_family="TASK-filters", **filters)
        assert "error" not in result
        return json.loads(result["output"])["records"]

    assert len(read(round=2)) == 2
    assert len(read(writer="qa-docs-generator")) == 1
    assert len(read(subject="beta")) == 1
    assert len(read(decision="UNNECESSARY")) == 1
    assert len(read(round=2, writer="qa-test-generator", subject="beta", decision="BLOCKED")) == 1
    assert len(read(source_kind="analyzer-finding")) == 3
    assert len(read(source_kind="fixer-issue")) == 0
    assert len(read(source_ref="finding-1")) == 3
    assert len(read(source_ref="no-such-ref")) == 0
    assert len(read(round=2, decision="BLOCKED", source_kind="analyzer-finding", source_ref="finding-1")) == 1


def test_plugin_registers_qa_bridges_through_python_runner():
    source = Path(__file__).parents[2] / "plugins" / "tools.ts"
    text = source.read_text(encoding="utf-8")
    blocks = {}
    for name in ("qa_record_write", "qa_record_read"):
        marker = f"{name}: tool("
        start = text.index(marker)
        end = text.index("\n  }),", start)
        block = text[start:end]
        blocks[name] = block
        assert f'runPythonTool("common.tools.{name}"' in block

    # The declared bridge argument surface must survive: the write bridge accepts
    # a record object, and the read bridge exposes explicit provenance filters.
    assert "record: tool.schema" in blocks["qa_record_write"]
    assert ".object({})" in blocks["qa_record_write"]
    assert "source_kind:" in blocks["qa_record_read"]
    assert "source_ref:" in blocks["qa_record_read"]


# --- Phase 2 regression coverage: fail-closed identity, complete schema, provenance ---


def test_duplicate_identity_rejected_fail_closed(workspace):
    assert "error" not in qa_record_write(record(family="TASK-dup"), workspace_root=workspace)
    second = qa_record_write(record(family="TASK-dup"), workspace_root=workspace)
    assert second["error"] == "invalid_qa_record"
    assert "duplicate" in second["message"]
    path = record_path(workspace, "TASK-dup", 1, "qa-test-generator")
    assert len(path.read_text(encoding="utf-8").splitlines()) == 1


def test_duplicate_identity_rejected_on_read(workspace):
    path = record_path(workspace, "TASK-dup-read", 1, "qa-test-generator")
    path.parent.mkdir(parents=True)
    line = json.dumps(record(family="TASK-dup-read")) + "\n"
    path.write_text(line + line, encoding="utf-8")
    assert qa_record_read(workspace_root=workspace, task_family="TASK-dup-read")["error"] == "invalid_qa_history"


def test_concurrent_duplicate_identity_yields_exactly_one(workspace):
    def write(_):
        return qa_record_write(record(family="TASK-concurrent-dup"), workspace_root=workspace)

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(write, range(8)))
    assert sum("error" in result for result in results) == 7
    path = record_path(workspace, "TASK-concurrent-dup", 1, "qa-test-generator")
    assert len(path.read_text(encoding="utf-8").splitlines()) == 1


def test_distinct_findings_and_independent_writers_allowed(workspace):
    assert "error" not in qa_record_write(
        record(family="TASK-multi") | {"subject": {"kind": "behavior", "symbol": "alpha"}},
        workspace_root=workspace,
    )
    assert "error" not in qa_record_write(
        record(family="TASK-multi") | {"subject": {"kind": "behavior", "symbol": "beta"}},
        workspace_root=workspace,
    )
    assert "error" not in qa_record_write(
        record(family="TASK-multi", writer="qa-docs-generator", decision="UNNECESSARY")
        | {"subject": {"kind": "interface", "symbol": "gamma"}, "changed_files": [], "changed_symbols": []},
        workspace_root=workspace,
    )
    assert "error" not in qa_record_write(
        record(family="TASK-multi", writer="exec-fixer") | {"subject": {"kind": "file", "file": "y.py"}},
        workspace_root=workspace,
    )
    assert len(qa_record_read(workspace_root=workspace, task_family="TASK-multi")["output"]) > 0
    read = json.loads(qa_record_read(workspace_root=workspace, task_family="TASK-multi")["output"])
    assert read["total"] == 4


@pytest.mark.parametrize("field", ["agent", "changed_files", "changed_symbols", "source_kind", "source_ref"])
def test_missing_complete_schema_fields_rejected(field):
    candidate = record()
    candidate.pop(field)
    with pytest.raises(ValueError, match="missing required fields"):
        validate_record(candidate)


def test_empty_changed_lists_only_for_no_change_outcomes(workspace):
    no_change = record(decision="UNNECESSARY") | {"changed_files": [], "changed_symbols": [], "subject": {"kind": "behavior", "symbol": "no-change"}}
    assert "error" not in qa_record_write(no_change, workspace_root=workspace)
    blocked = record(decision="BLOCKED") | {"changed_files": [], "changed_symbols": [], "subject": {"kind": "behavior", "symbol": "blocked"}}
    assert "error" not in qa_record_write(blocked, workspace_root=workspace)
    repaired = record(decision="REPAIRED") | {"changed_files": [], "changed_symbols": [], "subject": {"kind": "behavior", "symbol": "repaired"}}
    assert qa_record_write(repaired, workspace_root=workspace)["error"] == "invalid_qa_record"


def test_repaired_requires_change_and_verification(workspace):
    no_change = record() | {"changed_files": [], "changed_symbols": [], "subject": {"kind": "behavior", "symbol": "no-change"}}
    blocked = no_change | {"decision": "BLOCKED", "subject": {"kind": "behavior", "symbol": "blocked"}}
    assert "error" not in qa_record_write(blocked, workspace_root=workspace)
    result = qa_record_write(no_change, workspace_root=workspace)
    assert result["error"] == "invalid_qa_record"
    assert "REPAIRED" in result["message"]
    no_verification = record() | {"verification": "  ", "subject": {"kind": "behavior", "symbol": "unverified"}}
    assert qa_record_write(no_verification, workspace_root=workspace)["error"] == "invalid_qa_record"


def test_unnecessary_requires_evidence(workspace):
    result = qa_record_write(
        record(decision="UNNECESSARY") | {"evidence": "   ", "changed_files": [], "changed_symbols": []},
        workspace_root=workspace,
    )
    assert result["error"] == "invalid_qa_record"


def test_provenance_kind_and_reference_enforced(workspace):
    wrong_generator = record() | {"source_kind": "fixer-issue"}
    assert qa_record_write(wrong_generator, workspace_root=workspace)["error"] == "invalid_qa_record"
    wrong_fixer = record(writer="exec-fixer") | {"source_kind": "analyzer-finding"}
    assert qa_record_write(wrong_fixer, workspace_root=workspace)["error"] == "invalid_qa_record"
    unknown_kind = record() | {"source_kind": "unknown-finding"}
    assert qa_record_write(unknown_kind, workspace_root=workspace)["error"] == "invalid_qa_record"
    empty_ref = record() | {"source_ref": "  "}
    assert qa_record_write(empty_ref, workspace_root=workspace)["error"] == "invalid_qa_record"
    missing_ref = record()
    missing_ref.pop("source_ref")
    assert qa_record_write(missing_ref, workspace_root=workspace)["error"] == "invalid_qa_record"


def test_new_fields_survive_read_serialization(workspace):
    entry = record(family="TASK-serialize") | {
        "agent": "qa-docs-generator",
        "source_kind": "analyzer-finding",
        "source_ref": "analyzer://docs/finding-7",
        "changed_files": ["docs/a.md"],
        "changed_symbols": ["SectionA"],
    }
    assert "error" not in qa_record_write(entry, workspace_root=workspace)
    read = json.loads(qa_record_read(workspace_root=workspace, task_family="TASK-serialize")["output"])
    assert read["total"] == 1
    stored = read["records"][0]
    for field in ("agent", "source_kind", "source_ref", "changed_files", "changed_symbols"):
        assert stored[field] == entry[field]
    assert record_identity(stored) == record_identity(entry)


# --- Phase 3 coverage: writer isolation, no-change outcomes, identity normalization ---


def test_writer_mismatched_history_fails_closed_on_read(workspace):
    path = record_path(workspace, "TASK-mismatch", 1, "qa-docs-generator")
    path.parent.mkdir(parents=True)
    # A structurally valid qa-test-generator record stored in the qa-docs-generator history.
    path.write_text(json.dumps(record(family="TASK-mismatch")) + "\n", encoding="utf-8")
    assert qa_record_read(workspace_root=workspace, task_family="TASK-mismatch")["error"] == "invalid_qa_history"
    assert qa_record_read(workspace_root=workspace, task_family="TASK-mismatch", writer="qa-docs-generator")["error"] == "invalid_qa_history"
    missing = qa_record_read(workspace_root=workspace, task_family="TASK-mismatch", writer="qa-test-generator")
    assert "error" not in missing
    assert json.loads(missing["output"])["records"] == []


def test_escalated_allows_empty_changed_lists(workspace):
    escalated = record(decision="ESCALATED") | {
        "changed_files": [],
        "changed_symbols": [],
        "subject": {"kind": "behavior", "symbol": "escalated"},
    }
    assert "error" not in qa_record_write(escalated, workspace_root=workspace)


def test_object_subject_identity_is_key_order_independent(workspace):
    first = record(family="TASK-subject-order") | {"subject": {"kind": "behavior", "symbol": "run"}}
    assert "error" not in qa_record_write(first, workspace_root=workspace)
    second = record(family="TASK-subject-order") | {"subject": {"symbol": "run", "kind": "behavior"}}
    result = qa_record_write(second, workspace_root=workspace)
    assert result["error"] == "invalid_qa_record"
    assert "duplicate" in result["message"]


def test_writer_and_round_distinguish_same_subject(workspace):
    subject = {"kind": "behavior", "symbol": "shared"}
    assert "error" not in qa_record_write(record(family="TASK-writer-round") | {"subject": subject}, workspace_root=workspace)
    docs = record(family="TASK-writer-round", writer="qa-docs-generator", decision="UNNECESSARY") | {
        "subject": subject,
        "changed_files": [],
        "changed_symbols": [],
    }
    assert "error" not in qa_record_write(docs, workspace_root=workspace)
    assert "error" not in qa_record_write(
        record(family="TASK-writer-round") | {"round": 2, "subject": subject},
        workspace_root=workspace,
    )
    read = json.loads(qa_record_read(workspace_root=workspace, task_family="TASK-writer-round")["output"])
    assert read["total"] == 3


@pytest.mark.parametrize(
    "subject",
    [
        {"kind": "behavior"},
        {"kind": "interface"},
        {"file": "x.py"},
        {"symbol": "run"},
        {"module": "common.helpers"},
        {"contract": "item-3"},
        {"behavior": "raises"},
        {"interface": "qa_record_read"},
        {"kind": "behavior", "file": "   "},
    ],
)
def test_kind_only_and_single_key_subjects_are_rejected(subject):
    # Contract item 3: a stable subject is kind plus at least one identifying key.
    candidate = record() | {"subject": subject}
    with pytest.raises(ValueError, match="kind and at least one identifying key"):
        validate_record(candidate)


def test_kind_plus_any_identifying_key_is_accepted():
    for descriptor in ("file", "module", "symbol", "contract", "behavior", "interface"):
        assert validate_record(record() | {"subject": {"kind": "behavior", descriptor: "ident"}})


def test_string_subject_is_stripped_for_identity_but_persisted_raw(workspace):
    assert "error" not in qa_record_write(
        record(family="TASK-subject-text") | {"subject": "  finding text  "},
        workspace_root=workspace,
    )
    duplicate = record(family="TASK-subject-text") | {"subject": " finding text\n"}
    result = qa_record_write(duplicate, workspace_root=workspace)
    assert result["error"] == "invalid_qa_record"
    assert "duplicate" in result["message"]
    read = json.loads(qa_record_read(workspace_root=workspace, task_family="TASK-subject-text")["output"])
    assert read["total"] == 1
    assert read["records"][0]["subject"] == "  finding text  "


def test_unsupported_writer_filter_rejected(workspace):
    result = qa_record_read(workspace_root=workspace, task_family="TASK-x", writer="not-a-writer")
    assert result["error"] == "invalid_qa_history"
    assert result["message"] == "unsupported writer"


# --- Phase 4 coverage: untested enforced branches ---


def test_exec_fixer_requires_non_empty_repair(workspace):
    missing = record(writer="exec-fixer", family="TASK-fixer-repair-missing")
    missing.pop("repair")
    with pytest.raises(ValueError, match="repair"):
        validate_record(missing)
    assert qa_record_write(missing, workspace_root=workspace)["error"] == "invalid_qa_record"

    blank = record(writer="exec-fixer", family="TASK-fixer-repair-blank") | {"repair": "   "}
    with pytest.raises(ValueError, match="repair"):
        validate_record(blank)
    assert qa_record_write(blank, workspace_root=workspace)["error"] == "invalid_qa_record"


def test_unknown_decision_rejected(workspace):
    unknown = record(family="TASK-decision-unknown") | {"decision": "DONE"}
    with pytest.raises(ValueError, match="invalid decision"):
        validate_record(unknown)
    assert qa_record_write(unknown, workspace_root=workspace)["error"] == "invalid_qa_record"


def test_exec_fixer_rejects_generator_only_decision(workspace):
    unnecessary = record(writer="exec-fixer", family="TASK-fixer-decision", decision="UNNECESSARY")
    with pytest.raises(ValueError, match="invalid decision"):
        validate_record(unnecessary)
    assert qa_record_write(unnecessary, workspace_root=workspace)["error"] == "invalid_qa_record"


def test_docs_generator_provenance_is_writer_specific(workspace):
    wrong = record(writer="qa-docs-generator", family="TASK-docs-provenance") | {"source_kind": "fixer-issue"}
    assert qa_record_write(wrong, workspace_root=workspace)["error"] == "invalid_qa_record"
    right = record(writer="qa-docs-generator", family="TASK-docs-provenance-ok") | {"source_kind": "analyzer-finding"}
    assert "error" not in qa_record_write(right, workspace_root=workspace)


def test_task_family_and_plan_set_precedence():
    assert resolve_task_family(task_family="task") == "task"
    assert resolve_task_family(plan_set_family="plan", task_family="task") == "plan"
    assert resolve_task_family(task_family="task", standalone="standalone") == "task"


@pytest.mark.parametrize("field", ["task_family", "round", "writer", "subject", "decision", "verification"])
def test_missing_remaining_schema_fields_rejected(field):
    candidate = record()
    candidate.pop(field)
    with pytest.raises(ValueError, match="missing required fields"):
        validate_record(candidate)


def test_non_object_record_and_invalid_subject_type_rejected():
    with pytest.raises(ValueError, match="record must be an object"):
        validate_record("not-a-record")
    with pytest.raises(ValueError, match="subject must be a string or object"):
        validate_record(record() | {"subject": 123})


# --- Phase 5 coverage: production __main__ bridges, fail-closed shape branches ---


def test_write_bridge_entrypoint_round_trips_record(workspace):
    entry = record(family="TASK-bridge-write")
    result = run_python_tool(
        "common.tools.qa_record_write",
        {"record": entry, "workspace_root": str(workspace)},
    )
    assert "error" not in result
    returned = json.loads(result["output"])
    assert returned["path"] == "artifacts/logs/qa-rounds/TASK-bridge-write/round-1/qa-test-generator.jsonl"
    # The stdin "record" key is honored end to end, not silently dropped.
    assert returned["record"]["subject"] == entry["subject"]
    assert returned["record"]["source_ref"] == entry["source_ref"]
    assert returned["record"]["changed_files"] == entry["changed_files"]
    path = workspace / returned["path"]
    assert path.exists()
    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0]) == returned["record"]


def test_read_bridge_entrypoint_returns_written_history(workspace):
    missing = run_python_tool(
        "common.tools.qa_record_read",
        {"task_family": "TASK-bridge-read", "workspace_root": str(workspace)},
    )
    assert "error" not in missing
    empty_payload = json.loads(missing["output"])
    assert empty_payload["task_family"] == "TASK-bridge-read"
    assert empty_payload["records"] == []
    assert empty_payload["total"] == 0

    written = run_python_tool(
        "common.tools.qa_record_write",
        {"record": record(family="TASK-bridge-read"), "workspace_root": str(workspace)},
    )
    assert "error" not in written

    read = run_python_tool(
        "common.tools.qa_record_read",
        {"task_family": "TASK-bridge-read", "workspace_root": str(workspace)},
    )
    assert "error" not in read
    payload = json.loads(read["output"])
    assert payload["task_family"] == "TASK-bridge-read"
    assert payload["total"] == 1
    assert payload["records"][0]["source_ref"] == "finding-1"
    assert read["metadata"]["count"] == 1


@pytest.mark.parametrize(
    ("record_update", "match"),
    [
        ({"changed_files": "x.py"}, "changed_files must be a list"),
        ({"changed_files": [""]}, "changed_files entries must be non-empty strings"),
        ({"changed_files": ["   "]}, "changed_files entries must be non-empty strings"),
        ({"changed_files": [123]}, "changed_files entries must be non-empty strings"),
        ({"changed_symbols": "run"}, "changed_symbols must be a list"),
        ({"changed_symbols": [None]}, "changed_symbols entries must be non-empty strings"),
        ({"agent": 123}, "agent must be a string"),
        ({"agent": ""}, "Agent name cannot be empty"),
        ({"agent": "not a valid agent!"}, "Invalid agent name"),
    ],
)
def test_shape_and_type_fail_closed_branches(record_update, match, workspace):
    candidate = record() | record_update
    with pytest.raises(ValueError, match=match):
        validate_record(candidate)
    assert qa_record_write(candidate, workspace_root=workspace)["error"] == "invalid_qa_record"


def test_fixer_repair_must_be_text(workspace):
    candidate = record(writer="exec-fixer", family="TASK-fixer-repair-type") | {"repair": 123}
    with pytest.raises(ValueError, match="fixer repair must be text"):
        validate_record(candidate)
    assert qa_record_write(candidate, workspace_root=workspace)["error"] == "invalid_qa_record"


def test_record_path_rejects_unsupported_writer_and_invalid_round(workspace):
    with pytest.raises(ValueError, match="unsupported writer"):
        record_path(workspace, "TASK-path", 1, "unknown-writer")
    with pytest.raises(ValueError, match="round must be a positive integer"):
        record_path(workspace, "TASK-path", 0, "qa-test-generator")
    with pytest.raises(ValueError, match="round must be a positive integer"):
        record_path(workspace, "TASK-path", True, "qa-test-generator")


@pytest.mark.parametrize("bad_round", [0, -1, True])
def test_read_rejects_non_positive_round_filter(workspace, bad_round):
    result = qa_record_read(workspace_root=workspace, task_family="TASK-round-filter", round=bad_round)
    assert result["error"] == "invalid_qa_history"
    assert result["message"] == "round must be a positive integer"


def test_load_records_skips_blank_lines(workspace):
    path = record_path(workspace, "TASK-blank-lines", 1, "qa-test-generator")
    path.parent.mkdir(parents=True)
    first = json.dumps(record(family="TASK-blank-lines"))
    second = json.dumps(
        record(family="TASK-blank-lines") | {"subject": {"kind": "behavior", "symbol": "second"}}
    )
    path.write_text(first + "\n\n   \n" + second + "\n", encoding="utf-8")
    loaded = load_records(path, task_family="TASK-blank-lines", writer="qa-test-generator")
    assert [item["subject"]["symbol"] for item in loaded] == ["run", "second"]


def test_subject_identity_rejects_empty_and_unsupported_types():
    with pytest.raises(ValueError, match="subject cannot be empty"):
        subject_identity("   ")
    for value in (123, ["kind", "behavior"], None):
        with pytest.raises(ValueError, match="subject must be a string or object"):
            subject_identity(value)
