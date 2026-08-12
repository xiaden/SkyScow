"""End-to-end tests for the production-hardened context_budget tool."""

from __future__ import annotations

import json
import math

import pytest

from common.helpers import budget_policy as bp
from common.tools import context_budget
from tests.conftest import build_workspace, copy_fixture

DEFAULT_POLICY = bp.DEFAULT_POLICY


def _overhead(policy: dict) -> int:
    return (
        policy["phase_reread_tokens"]
        + policy["worker_return_tokens"]
        + policy["qa_return_tokens"]
    )


def _expect_status(policy: dict, worst: int) -> str:
    if worst > policy["physical_limit"]:
        return "PHYSICAL_LIMIT_EXCEEDED"
    if worst > policy["manager_operational_limit"]:
        return "SPLIT_REQUIRED"
    return "VALID"


def _assert_planning_consistent(result: dict, policy: dict) -> None:
    """Projection internals must match the policy math exactly."""
    planning = result["planning"]
    weighted = result["measured"]["weighted_tokens"]
    phases = planning["phases"]
    overhead = _overhead(policy)
    multiplier = policy["correction_multiplier"]
    assert planning["normal_manager_tokens"] == weighted + phases * overhead
    assert planning["worst_case_manager_tokens"] == weighted + phases * overhead * multiplier
    assert planning["minimum_phases"] == max(1, math.ceil(weighted / policy["worker_phase_limit"]))
    assert planning["minimum_plans"] == max(
        1, math.ceil(planning["worst_case_manager_tokens"] / policy["manager_operational_limit"])
    )
    assert planning["status"] == _expect_status(policy, planning["worst_case_manager_tokens"])
    assert result["policy"]["worker_phase_limit"] == policy["worker_phase_limit"]


def _measure(workspace, files, policy_file=None, monkeypatch=None):
    if policy_file is not None and monkeypatch is not None:
        override = copy_fixture(workspace, policy_file, "override.yaml")
        monkeypatch.setenv("HOLYCODE_CONTEXT_BUDGET_POLICY", str(override))
    return context_budget.context_budget(files=files, workspace_root=workspace)


# ---------------------------------------------------------------------------
# Files-only input validation
# ---------------------------------------------------------------------------


class TestFilesOnlyValidation:
    def test_non_list(self, workspace):
        result = context_budget.context_budget(files="nope", workspace_root=workspace)
        assert result["error"] == "invalid_files"

    def test_empty_list(self, workspace):
        result = context_budget.context_budget(files=[], workspace_root=workspace)
        assert result["error"] == "invalid_files"

    def test_non_object_entry(self, workspace):
        result = context_budget.context_budget(files=["x"], workspace_root=workspace)
        assert result["error"] == "invalid_file"

    def test_unsupported_keys_rejected(self, workspace):
        copy_fixture(workspace, "inputs/app.py", "app.py")
        result = context_budget.context_budget(
            files=[{"path": "app.py", "start_line": 1, "end_line": 3, "policy": 999}],
            workspace_root=workspace,
        )
        assert result["error"] == "invalid_file"
        assert "unsupported keys" in result["message"]

    def test_missing_path(self, workspace):
        result = context_budget.context_budget(
            files=[{"start_line": 1, "end_line": 1}], workspace_root=workspace
        )
        assert result["error"] == "invalid_file"

    def test_bool_line_numbers_rejected(self, workspace):
        copy_fixture(workspace, "inputs/app.py", "app.py")
        result = context_budget.context_budget(
            files=[{"path": "app.py", "start_line": True, "end_line": 2}],
            workspace_root=workspace,
        )
        assert result["error"] == "invalid_line_range"

    def test_zero_line_numbers_rejected(self, workspace):
        copy_fixture(workspace, "inputs/app.py", "app.py")
        result = context_budget.context_budget(
            files=[{"path": "app.py", "start_line": 0, "end_line": 2}],
            workspace_root=workspace,
        )
        assert result["error"] == "invalid_line_range"

    def test_end_before_start(self, workspace):
        copy_fixture(workspace, "inputs/app.py", "app.py")
        result = context_budget.context_budget(
            files=[{"path": "app.py", "start_line": 5, "end_line": 2}],
            workspace_root=workspace,
        )
        assert result["error"] == "invalid_line_range"

    def test_traversal_rejected(self, workspace, tmp_path):
        (tmp_path / "secret.txt").write_text("classified")
        result = context_budget.context_budget(
            files=[{"path": "../secret.txt", "start_line": 1, "end_line": 1}],
            workspace_root=workspace,
        )
        assert result["error"] == "invalid_file"

    def test_absolute_path_outside_workspace(self, workspace, tmp_path):
        outside = tmp_path / "outside.txt"
        outside.write_text("x")
        result = context_budget.context_budget(
            files=[{"path": str(outside), "start_line": 1, "end_line": 1}],
            workspace_root=workspace,
        )
        assert result["error"] == "invalid_file"
        assert "outside workspace" in result["message"]

    def test_nonexistent_file(self, workspace):
        result = context_budget.context_budget(
            files=[{"path": "missing.py", "start_line": 1, "end_line": 1}],
            workspace_root=workspace,
        )
        assert result["error"] == "invalid_file"

    def test_directory_rejected(self, workspace):
        (workspace / "adir").mkdir()
        result = context_budget.context_budget(
            files=[{"path": "adir", "start_line": 1, "end_line": 1}],
            workspace_root=workspace,
        )
        assert result["error"] == "invalid_file"

    def test_range_exceeding_file(self, workspace):
        copy_fixture(workspace, "inputs/app.py", "app.py")
        result = context_budget.context_budget(
            files=[{"path": "app.py", "start_line": 1, "end_line": 9999}],
            workspace_root=workspace,
        )
        assert result["error"] == "read_error"

    def test_binary_file_read_error(self, workspace):
        (workspace / "blob.bin").write_bytes(b"\x00\xff\xfe not utf8 \x80")
        result = context_budget.context_budget(
            files=[{"path": "blob.bin", "start_line": 1, "end_line": 1}],
            workspace_root=workspace,
        )
        assert result["error"] == "read_error"


# ---------------------------------------------------------------------------
# Model selection from agent frontmatter
# ---------------------------------------------------------------------------


class TestModelSelection:
    def test_known_model_selects_deepseek(self, workspace):
        copy_fixture(workspace, "agents/known_model.md", "agents/known.md")
        copy_fixture(workspace, "inputs/app.py", "app.py")
        result = _measure(
            workspace,
            [
                {"path": "agents/known.md", "start_line": 1, "end_line": 6},
                {"path": "app.py", "start_line": 1, "end_line": 7},
            ],
        )
        assert result["model"] == "DS_V4_F_0731"

    def test_unknown_model_falls_back(self, workspace):
        copy_fixture(workspace, "agents/unknown_model.md", "agents/unknown.md")
        copy_fixture(workspace, "inputs/app.py", "app.py")
        result = _measure(
            workspace,
            [
                {"path": "agents/unknown.md", "start_line": 1, "end_line": 5},
                {"path": "app.py", "start_line": 1, "end_line": 7},
            ],
        )
        assert result["model"] == "DS_V4_F_0731"

    def test_missing_model_falls_back(self, workspace):
        copy_fixture(workspace, "agents/no_model.md", "agents/none.md")
        copy_fixture(workspace, "inputs/app.py", "app.py")
        result = _measure(
            workspace,
            [
                {"path": "agents/none.md", "start_line": 1, "end_line": 5},
                {"path": "app.py", "start_line": 1, "end_line": 7},
            ],
        )
        assert result["model"] == "DS_V4_F_0731"

    def test_malformed_model_falls_back(self, workspace):
        copy_fixture(workspace, "agents/malformed_model.md", "agents/bad.md")
        copy_fixture(workspace, "inputs/app.py", "app.py")
        result = _measure(
            workspace,
            [
                {"path": "agents/bad.md", "start_line": 1, "end_line": 5},
                {"path": "app.py", "start_line": 1, "end_line": 7},
            ],
        )
        assert result["model"] == "DS_V4_F_0731"

    def test_no_agent_files_falls_back(self, workspace):
        copy_fixture(workspace, "inputs/app.py", "app.py")
        result = _measure(workspace, [{"path": "app.py", "start_line": 1, "end_line": 7}])
        assert result["model"] == "DS_V4_F_0731"

    def test_mixed_known_models_fall_back(self, workspace, monkeypatch):
        # Two distinct allowlisted models -> deterministic fallback.
        monkeypatch.setattr(
            bp,
            "MODEL_TOKENIZER_MAP",
            {
                "omniroute/opencode-go/deepseek-v4-flash": "DS_V4_F_0731",
                "omniroute/opencode-go/gpt-5.6-luna": "o200k",
            },
        )
        copy_fixture(workspace, "agents/mixed_a.md", "agents/a.md")
        copy_fixture(workspace, "agents/mixed_b.md", "agents/b.md")
        copy_fixture(workspace, "inputs/app.py", "app.py")
        result = _measure(
            workspace,
            [
                {"path": "agents/a.md", "start_line": 1, "end_line": 5},
                {"path": "agents/b.md", "start_line": 1, "end_line": 5},
                {"path": "app.py", "start_line": 1, "end_line": 7},
            ],
        )
        assert result["model"] == bp.DEFAULT_MODEL


# ---------------------------------------------------------------------------
# Plan parsing and per-phase validation
# ---------------------------------------------------------------------------


class TestPlanParsing:
    def test_normal_single_phase(self, workspace):
        copy_fixture(workspace, "plans/normal_single_phase.md", "plans/TASK-x-A.md")
        copy_fixture(workspace, "inputs/app.py", "app.py")
        result = _measure(
            workspace,
            [
                {"path": "app.py", "start_line": 1, "end_line": 7},
                {"path": "plans/TASK-x-A.md", "start_line": 1, "end_line": 9},
            ],
        )
        planning = result["planning"]
        assert planning["explicit_phases"] is True
        assert planning["phases"] == 1
        assert len(planning["phases_detail"]) == 1
        detail = planning["phases_detail"][0]
        assert detail["number"] == 1
        assert detail["plan"] == "TASK-x-A.md"
        assert detail["steps"] == 3
        assert detail["complete_steps"] == 1
        assert detail["within_worker_limit"] is True
        _assert_planning_consistent(result, DEFAULT_POLICY)

    def test_multi_phase_sequential(self, workspace):
        copy_fixture(workspace, "plans/multi_phase.md", "plans/TASK-y-B.md")
        result = _measure(
            workspace,
            [{"path": "plans/TASK-y-B.md", "start_line": 1, "end_line": 20}],
        )
        planning = result["planning"]
        assert planning["explicit_phases"] is True
        assert planning["phases"] == 3
        assert [d["number"] for d in planning["phases_detail"]] == [1, 2, 3]
        assert [d["steps"] for d in planning["phases_detail"]] == [1, 2, 2]
        assert [d["complete_steps"] for d in planning["phases_detail"]] == [0, 0, 2]
        assert all(d["within_worker_limit"] for d in planning["phases_detail"])
        _assert_planning_consistent(result, DEFAULT_POLICY)

    def test_plan_range_is_ignored_for_parsing(self, workspace):
        # Only lines 1-2 supplied, but full plan structure must be parsed.
        copy_fixture(workspace, "plans/multi_phase.md", "plans/TASK-z-C.md")
        result = _measure(
            workspace,
            [{"path": "plans/TASK-z-C.md", "start_line": 1, "end_line": 2}],
        )
        assert result["planning"]["explicit_phases"] is True
        assert result["planning"]["phases"] == 3

    def test_multiple_plan_files_aggregate(self, workspace):
        copy_fixture(workspace, "plans/multi_phase.md", "plans/TASK-a.md")
        copy_fixture(workspace, "plans/normal_single_phase.md", "plans/TASK-b.md")
        result = _measure(
            workspace,
            [
                {"path": "plans/TASK-a.md", "start_line": 1, "end_line": 20},
                {"path": "plans/TASK-b.md", "start_line": 1, "end_line": 9},
            ],
        )
        planning = result["planning"]
        assert planning["explicit_phases"] is True
        assert planning["phases"] == 4
        assert {d["plan"] for d in planning["phases_detail"]} == {"TASK-a.md", "TASK-b.md"}

    def test_non_sequential_plan_rejected(self, workspace):
        copy_fixture(workspace, "plans/non_sequential.md", "plans/TASK-broken.md")
        result = _measure(
            workspace,
            [{"path": "plans/TASK-broken.md", "start_line": 1, "end_line": 9}],
        )
        assert result["error"] == "plan_validation"
        assert "sequential" in result["message"]

    def test_malformed_phase_number_plan_parse_error(self, workspace):
        copy_fixture(workspace, "plans/malformed_phase.md", "plans/TASK-bad.md")
        result = _measure(
            workspace,
            [{"path": "plans/TASK-bad.md", "start_line": 1, "end_line": 5}],
        )
        assert result["error"] == "plan_parse"

    def test_phase_without_steps_rejected(self, workspace):
        copy_fixture(workspace, "plans/empty_phase.md", "plans/TASK-empty.md")
        result = _measure(
            workspace,
            [{"path": "plans/TASK-empty.md", "start_line": 1, "end_line": 9}],
        )
        assert result["error"] == "plan_validation"
        assert "no steps" in result["message"]

    def test_plan_without_phases_falls_back(self, workspace):
        copy_fixture(workspace, "plans/no_phases.md", "plans/TASK-prose.md")
        result = _measure(
            workspace,
            [{"path": "plans/TASK-prose.md", "start_line": 1, "end_line": 4}],
        )
        planning = result["planning"]
        assert planning["explicit_phases"] is False
        assert planning["phases"] == planning["minimum_phases"]
        _assert_planning_consistent(result, DEFAULT_POLICY)

    def test_oversized_plan_exceeds_physical_limit(self, workspace):
        copy_fixture(workspace, "plans/oversized.md", "plans/TASK-huge.md")
        result = _measure(
            workspace,
            [{"path": "plans/TASK-huge.md", "start_line": 1, "end_line": 100}],
        )
        assert result["planning"]["explicit_phases"] is True
        assert result["planning"]["phases"] == 10
        assert result["planning"]["status"] == "PHYSICAL_LIMIT_EXCEEDED"
        _assert_planning_consistent(result, DEFAULT_POLICY)


# ---------------------------------------------------------------------------
# Projections and status classification
# ---------------------------------------------------------------------------


class TestProjections:
    def test_no_plan_worker_limit_fallback(self, workspace):
        copy_fixture(workspace, "inputs/app.py", "app.py")
        result = _measure(workspace, [{"path": "app.py", "start_line": 1, "end_line": 7}])
        planning = result["planning"]
        assert planning["explicit_phases"] is False
        weighted = result["measured"]["weighted_tokens"]
        expected = max(1, math.ceil(weighted / DEFAULT_POLICY["worker_phase_limit"]))
        assert planning["phases"] == expected
        assert planning["phases"] == planning["minimum_phases"]
        assert planning["status"] == "VALID"
        _assert_planning_consistent(result, DEFAULT_POLICY)

    def test_weighted_tokens_formula_applied(self, workspace):
        # Two sections from two files -> weight = 1 + 0.03 + 0.015 = 1.045.
        copy_fixture(workspace, "inputs/app.py", "app.py")
        copy_fixture(workspace, "agents/known_model.md", "agents/k.md")
        result = _measure(
            workspace,
            [
                {"path": "app.py", "start_line": 1, "end_line": 7},
                {"path": "agents/k.md", "start_line": 1, "end_line": 6},
            ],
        )
        measured = result["measured"]
        assert measured["weighted_tokens"] == math.ceil(
            measured["source_tokens"] * 1.045
        )

    def test_status_boundaries(self):
        # Unit-level boundary checks for VALID / SPLIT_REQUIRED / PHYSICAL.
        policy = dict(DEFAULT_POLICY)
        policy["worker_phase_limit"] = 10
        policy["manager_operational_limit"] = 100
        policy["physical_limit"] = 200
        policy["correction_multiplier"] = 3
        policy["phase_reread_tokens"] = 8
        policy["worker_return_tokens"] = 8
        policy["fixer_return_tokens"] = 8
        policy["qa_return_tokens"] = 12
        overhead = _overhead(policy)  # 8 + 8 + 12 = 28

        def run(weighted, phases):
            return context_budget._build_planning(
                policy, weighted, phases, True, []
            )

        # worst == operational -> VALID (not strict >)
        assert run(weighted=16, phases=1)["status"] == "VALID"  # 16 + 3*28 = 100
        # worst == physical -> SPLIT_REQUIRED (not strict >)
        result = run(weighted=116, phases=1)  # 116 + 84 = 200
        assert result["worst_case_manager_tokens"] == 200
        assert result["status"] == "SPLIT_REQUIRED"
        # worst > physical -> PHYSICAL_LIMIT_EXCEEDED
        result = run(weighted=117, phases=1)  # 201
        assert result["status"] == "PHYSICAL_LIMIT_EXCEEDED"

    def test_status_via_policy_override(self, workspace, monkeypatch):
        # End-to-end: tiny policy yields SPLIT_REQUIRED on a small file.
        copy_fixture(workspace, "inputs/app.py", "app.py")
        result = _measure(
            workspace,
            [{"path": "app.py", "start_line": 1, "end_line": 7}],
            policy_file="policy/tiny.yaml",
            monkeypatch=monkeypatch,
        )
        tiny = {"worker_phase_limit": 10, "manager_operational_limit": 100,
                "physical_limit": 200, "worker_return_tokens": 8,
                "fixer_return_tokens": 8, "qa_return_tokens": 12,
                "phase_reread_tokens": 8, "correction_multiplier": 3}
        _assert_planning_consistent(result, tiny)
        assert result["policy"]["source"] == "env"


# ---------------------------------------------------------------------------
# Compact output and leak prevention
# ---------------------------------------------------------------------------


class TestCompactOutput:
    def test_stable_keys(self, workspace):
        copy_fixture(workspace, "inputs/app.py", "app.py")
        result = _measure(workspace, [{"path": "app.py", "start_line": 1, "end_line": 7}])
        assert set(result) == {"model", "measured", "planning", "policy"}
        assert set(result["measured"]) == {"source_tokens", "weighted_tokens"}
        assert set(result["planning"]) == {
            "phases", "explicit_phases", "phases_detail", "minimum_phases",
            "minimum_plans", "normal_manager_tokens", "worst_case_manager_tokens",
            "status",
        }
        assert set(result["policy"]) == {
            "source", "worker_phase_limit", "manager_operational_limit",
            "physical_limit", "worker_return_tokens", "fixer_return_tokens",
            "qa_return_tokens", "phase_reread_tokens", "correction_multiplier",
        }

    def test_no_source_or_secret_leakage(self, workspace):
        copy_fixture(workspace, "agents/known_model.md", "agents/k.md")
        copy_fixture(workspace, "inputs/app.py", "app.py")
        result = _measure(
            workspace,
            [
                {"path": "agents/k.md", "start_line": 1, "end_line": 6},
                {"path": "app.py", "start_line": 1, "end_line": 7},
            ],
        )
        dump = json.dumps(result)
        assert "SECRET_MARKER_KNOWN" not in dump
        assert "def hello" not in dump
        assert "return 'world'" not in dump
        assert "model:" not in dump  # no frontmatter bodies

    def test_error_messages_bounded(self, workspace, tmp_path):
        # Malformed policy messages and read errors are bounded and stable.
        copy_fixture(workspace, "plans/malformed_phase.md", "plans/bad.md")
        result = _measure(workspace, [{"path": "plans/bad.md", "start_line": 1, "end_line": 5}])
        assert result["error"] == "plan_parse"
        assert len(result["message"]) <= 303

    def test_policy_source_defaults_when_absent(self, workspace):
        copy_fixture(workspace, "inputs/app.py", "app.py")
        result = _measure(workspace, [{"path": "app.py", "start_line": 1, "end_line": 7}])
        assert result["policy"]["source"] == "defaults"

    def test_policy_source_workspace_when_shipped(self, workspace, fixtures):
        copy_fixture(workspace, "policy/valid.yaml", "config/agent-context-budgets.yaml")
        copy_fixture(workspace, "inputs/app.py", "app.py")
        result = _measure(workspace, [{"path": "app.py", "start_line": 1, "end_line": 7}])
        assert result["policy"]["source"] == "workspace"

    def test_malformed_policy_uses_defaults_safely(self, workspace, fixtures, monkeypatch):
        copy_fixture(workspace, "policy/malformed.yaml", "config/agent-context-budgets.yaml")
        copy_fixture(workspace, "inputs/app.py", "app.py")
        result = _measure(workspace, [{"path": "app.py", "start_line": 1, "end_line": 7}])
        assert result["policy"]["source"] == "defaults"
        assert result["policy"]["worker_phase_limit"] == 48000
        assert result["policy"]["physical_limit"] == 128000


# ---------------------------------------------------------------------------
# Worker limit details
# ---------------------------------------------------------------------------


class TestWorkerLimitChecks:
    def test_within_worker_limit_flag_reflects_phase_size(self, workspace, monkeypatch):
        # A single phase over the worker limit must be flagged.
        copy_fixture(workspace, "plans/multi_phase.md", "plans/TASK-x.md")
        monkeypatch.setenv(
            "HOLYCODE_CONTEXT_BUDGET_POLICY",
            str(copy_fixture(workspace, "policy/tiny.yaml", "tiny.yaml")),
        )
        result = _measure(
            workspace,
            [{"path": "plans/TASK-x.md", "start_line": 1, "end_line": 20}],
        )
        assert result["planning"]["explicit_phases"] is True
        assert all(not d["within_worker_limit"] for d in result["planning"]["phases_detail"])
