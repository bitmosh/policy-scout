# SPDX-License-Identifier: Apache-2.0
"""Tests for MCP tool handlers."""

import json
import textwrap
from unittest.mock import MagicMock, patch

from policy_scout.server.handlers import (
    handle_check,
    handle_get_report,
    handle_sandbox,
    handle_sweep,
)


class TestHandleCheck:
    def test_missing_command_returns_error(self):
        result = handle_check({})
        assert result.get("is_error") is True
        assert "command" in result.get("error", "").lower()

    def test_empty_command_returns_error(self):
        result = handle_check({"command": ""})
        assert result.get("is_error") is True

    def test_valid_command_returns_decision(self):
        result = handle_check({"command": "ls -la"})
        assert "decision" in result
        assert result["decision"] in {"ALLOW", "REQUIRE_APPROVAL", "DENY", "DENY_AND_ALERT", "UNKNOWN"}
        assert "risk_score" in result
        assert "reasons" in result

    def test_dangerous_command_is_not_allowed(self):
        result = handle_check({"command": "rm -rf /"})
        assert result.get("decision") in {"DENY", "DENY_AND_ALERT", "REQUIRE_APPROVAL"}

    def test_result_has_all_expected_fields(self):
        result = handle_check({"command": "echo hello"})
        for field in ("request_id", "command", "decision", "risk_score", "risk_band",
                      "category", "capabilities", "reasons"):
            assert field in result, f"Missing field: {field}"

    def test_with_intel_flag_accepted(self):
        # with_intel=False should still work without remote calls
        result = handle_check({"command": "npm install lodash", "with_intel": False})
        assert "decision" in result
        assert result.get("is_error") is not True


class TestHandleSandbox:
    def test_missing_command_returns_error(self):
        result = handle_sandbox({})
        assert result.get("is_error") is True

    def test_non_package_command_returns_error(self):
        # sandbox only supports npm/yarn/pnpm/bun install
        result = handle_sandbox({"command": "ls -la"})
        assert result.get("is_error") is True


class TestHandleSweep:
    def test_quick_sweep_returns_findings(self):
        result = handle_sweep({"mode": "quick"})
        assert "findings" in result
        assert "findings_count" in result
        assert isinstance(result["findings"], list)

    def test_project_sweep_uses_cwd(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = handle_sweep({"mode": "project", "project_root": str(tmp_path)})
        assert "findings" in result

    def test_default_mode_is_quick(self):
        result = handle_sweep({})
        assert "findings" in result
        assert result.get("is_error") is not True

    def test_sweep_result_has_required_keys(self):
        result = handle_sweep({"mode": "quick"})
        for key in ("sweep_id", "findings", "findings_count"):
            assert key in result, f"Missing key: {key}"


class TestHandleGetReport:
    def test_no_report_dir_returns_empty_list(self, tmp_path, monkeypatch):
        with patch("policy_scout.reports.writer.get_report_root", return_value=tmp_path / "nonexistent"):
            result = handle_get_report({})
        assert result.get("reports") == []

    def test_list_reports_empty_directory(self, tmp_path):
        with patch("policy_scout.reports.writer.get_report_root", return_value=tmp_path):
            result = handle_get_report({})
        assert isinstance(result.get("reports"), list)
        assert len(result["reports"]) == 0

    def test_list_reports_finds_valid_report(self, tmp_path):
        # Create a minimal report structure
        report_dir = tmp_path / "report_abc123"
        report_dir.mkdir()
        (report_dir / "report.json").write_text(json.dumps({
            "report_type": "command_decision",
            "created_at": "2026-01-01T00:00:00Z",
            "summary": "Test report",
        }))
        with patch("policy_scout.reports.writer.get_report_root", return_value=tmp_path):
            result = handle_get_report({})
        assert len(result["reports"]) == 1
        assert result["reports"][0]["report_id"] == "report_abc123"

    def test_fetch_specific_report(self, tmp_path):
        report_dir = tmp_path / "report_def456"
        report_dir.mkdir()
        payload = {"report_type": "sweep", "summary": "ok"}
        (report_dir / "report.json").write_text(json.dumps(payload))
        with patch("policy_scout.reports.writer.get_report_root", return_value=tmp_path):
            result = handle_get_report({"report_id": "report_def456"})
        assert result.get("report_id") == "report_def456"
        assert result["data"]["report_type"] == "sweep"

    def test_fetch_missing_report_returns_error(self, tmp_path):
        with patch("policy_scout.reports.writer.get_report_root", return_value=tmp_path):
            result = handle_get_report({"report_id": "report_doesnotexist"})
        assert result.get("is_error") is True
