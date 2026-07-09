# SPDX-License-Identifier: Apache-2.0
"""Tests for data cleanup — plan and execute paths."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from policy_scout.data_cleanup import (
    execute_cleanup,
    format_cleanup_result_human,
    format_cleanup_result_json,
    plan_cleanup,
    validate_path_under_root,
)


# ─── helpers ─────────────────────────────────────────────────────────────────


def _make_plan(data_root: Path, items: list) -> dict:
    """Build a minimal execute-ready plan dict with data_root as the root."""
    return {
        "target": "demo",
        "dry_run": False,
        "target_root": str(data_root),
        "planned_items": items,
        "total_items": len(items),
        "total_bytes": sum(i.get("size_bytes", 0) for i in items),
        "warnings": [],
        "could_not_verify": [],
    }


# ─── validate_path_under_root ────────────────────────────────────────────────


class TestValidatePathUnderRoot:
    def test_child_path_valid(self, tmp_path):
        child = tmp_path / "sub" / "file.txt"
        assert validate_path_under_root(child, tmp_path) is True

    def test_root_itself_valid(self, tmp_path):
        assert validate_path_under_root(tmp_path, tmp_path) is True

    def test_sibling_path_invalid(self, tmp_path):
        sibling = tmp_path.parent / "other"
        assert validate_path_under_root(sibling, tmp_path) is False

    def test_parent_path_invalid(self, tmp_path):
        assert validate_path_under_root(tmp_path.parent, tmp_path) is False


# ─── execute_cleanup — dry_run guard ─────────────────────────────────────────


class TestExecuteCleanupDryRunGuard:
    def test_dry_run_true_blocks_execution(self, tmp_path):
        plan = _make_plan(tmp_path, [])
        plan["dry_run"] = True
        result = execute_cleanup(plan)
        assert result["executed"] is False
        assert "dry_run" in result["error"]

    def test_plan_with_error_blocks_execution(self, tmp_path):
        plan = {"target": "demo", "dry_run": False, "error": "bad target"}
        result = execute_cleanup(plan)
        assert result["executed"] is False

    def test_missing_target_root_blocks_execution(self):
        plan = {"target": "demo", "dry_run": False, "planned_items": []}
        result = execute_cleanup(plan)
        assert result["executed"] is False


# ─── execute_cleanup — file deletion ─────────────────────────────────────────


class TestExecuteCleanupDeletion:
    def test_deletes_file(self, tmp_path):
        f = tmp_path / "old_result.json"
        f.write_text("{}")
        plan = _make_plan(tmp_path, [{"path": str(f), "type": "file", "size_bytes": 2}])
        with patch("policy_scout.data_cleanup.get_data_root", return_value=tmp_path):
            result = execute_cleanup(plan)
        assert result["executed"] is True
        assert result["deleted_count"] == 1
        assert result["failed_count"] == 0
        assert not f.exists()

    def test_deletes_directory_recursively(self, tmp_path):
        d = tmp_path / "sandbox_abc"
        d.mkdir()
        (d / "file.txt").write_text("data")
        plan = _make_plan(tmp_path, [{"path": str(d), "type": "directory", "size_bytes": 4}])
        with patch("policy_scout.data_cleanup.get_data_root", return_value=tmp_path):
            result = execute_cleanup(plan)
        assert result["deleted_count"] == 1
        assert not d.exists()

    def test_freed_bytes_summed(self, tmp_path):
        f1 = tmp_path / "a.txt"
        f2 = tmp_path / "b.txt"
        f1.write_text("hello")
        f2.write_text("world")
        plan = _make_plan(tmp_path, [
            {"path": str(f1), "type": "file", "size_bytes": 5},
            {"path": str(f2), "type": "file", "size_bytes": 5},
        ])
        with patch("policy_scout.data_cleanup.get_data_root", return_value=tmp_path):
            result = execute_cleanup(plan)
        assert result["freed_bytes"] == 10
        assert result["deleted_count"] == 2

    def test_already_gone_counts_as_success(self, tmp_path):
        ghost = tmp_path / "gone.txt"
        plan = _make_plan(tmp_path, [{"path": str(ghost), "type": "file", "size_bytes": 0}])
        with patch("policy_scout.data_cleanup.get_data_root", return_value=tmp_path):
            result = execute_cleanup(plan)
        assert result["executed"] is True
        assert result["failed_count"] == 0

    def test_empty_plan_runs_cleanly(self, tmp_path):
        plan = _make_plan(tmp_path, [])
        with patch("policy_scout.data_cleanup.get_data_root", return_value=tmp_path):
            result = execute_cleanup(plan)
        assert result["executed"] is True
        assert result["deleted_count"] == 0
        assert result["freed_bytes"] == 0


# ─── execute_cleanup — path traversal safety ─────────────────────────────────


class TestExecuteCleanupPathSafety:
    def test_path_outside_data_root_skipped(self, tmp_path):
        outside = tmp_path.parent / "outside_ps_test.txt"
        outside.write_text("sensitive")
        try:
            items = [{"path": str(outside), "type": "file", "size_bytes": 9}]
            plan = {
                "target": "demo",
                "dry_run": False,
                "target_root": str(tmp_path),
                "planned_items": items,
                "total_items": 1,
                "total_bytes": 9,
                "warnings": [],
                "could_not_verify": [],
            }
            with patch(
                "policy_scout.data_cleanup.get_data_root", return_value=tmp_path
            ):
                result = execute_cleanup(plan)
            assert outside.exists(), "File outside data root must not be deleted"
            assert result["failed_count"] == 1
            assert result["deleted_count"] == 0
        finally:
            outside.unlink(missing_ok=True)

    def test_symlink_inside_root_deleted(self, tmp_path):
        target = tmp_path / "real.txt"
        target.write_text("data")
        link = tmp_path / "link.txt"
        link.symlink_to(target)
        plan = _make_plan(tmp_path, [{"path": str(link), "type": "symlink", "size_bytes": 0}])
        with patch("policy_scout.data_cleanup.get_data_root", return_value=tmp_path):
            result = execute_cleanup(plan)
        assert result["deleted_count"] == 1
        assert not link.exists()
        assert target.exists()


# ─── formatters ──────────────────────────────────────────────────────────────


class TestFormatCleanupResult:
    def _ok_result(self):
        return {
            "target": "demo",
            "executed": True,
            "target_root": "/tmp/ps/demo",
            "deleted_items": [{"path": "/tmp/ps/demo/x", "size_bytes": 100}],
            "failed_items": [],
            "deleted_count": 1,
            "failed_count": 0,
            "freed_bytes": 100,
        }

    def test_human_output_contains_deleted_count(self):
        out = format_cleanup_result_human(self._ok_result())
        assert "1 item" in out
        assert "100" in out

    def test_human_output_not_executed(self):
        result = {"target": "demo", "executed": False, "error": "dry_run=True"}
        out = format_cleanup_result_human(result)
        assert "Error" in out

    def test_json_output_parseable(self):
        out = format_cleanup_result_json(self._ok_result())
        data = json.loads(out)
        assert data["deleted_count"] == 1
        assert data["freed_bytes"] == 100

    def test_json_output_with_failures(self):
        result = self._ok_result()
        result["failed_items"] = [{"path": "/tmp/ps/demo/y", "reason": "Permission denied"}]
        result["failed_count"] = 1
        out = format_cleanup_result_json(result)
        data = json.loads(out)
        assert data["failed_count"] == 1


# ─── plan_cleanup (existing behaviour unchanged) ─────────────────────────────


class TestPlanCleanupUnchanged:
    def test_unsupported_target_returns_error(self):
        plan = plan_cleanup("nonexistent")
        assert "error" in plan
        assert plan["dry_run"] is True

    def test_missing_directory_returns_zero_items(self, tmp_path):
        missing = tmp_path / "no_such_dir"
        with patch("policy_scout.data_cleanup.get_target_root", return_value=missing):
            with patch("policy_scout.data_cleanup.get_data_root", return_value=tmp_path):
                plan = plan_cleanup("demo")
        assert plan["total_items"] == 0
        assert plan["dry_run"] is True

    def test_returns_dry_run_true(self, tmp_path):
        with patch("policy_scout.data_cleanup.get_target_root", return_value=tmp_path):
            with patch("policy_scout.data_cleanup.get_data_root", return_value=tmp_path.parent):
                plan = plan_cleanup("demo")
        assert plan["dry_run"] is True
