# SPDX-License-Identifier: Apache-2.0
"""Tests for pnpm/yarn/bun sandbox execution support."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from policy_scout.sandbox.diff import (
    capture_manifest_diffs,
    take_file_snapshot,
    _LOCKFILE_NAMES,
)
from policy_scout.supply_chain.transitive import (
    run_list_for_pm,
    run_pnpm_list,
    run_npm_list,
)


# ─── take_file_snapshot ───────────────────────────────────────────────────────


class TestTakeFileSnapshot:
    def test_npm_snapshots_npm_lockfiles(self, tmp_path):
        (tmp_path / "package.json").write_text('{"name":"test"}')
        (tmp_path / "package-lock.json").write_text('{"lockfileVersion":3}')
        snap = take_file_snapshot(tmp_path, "npm")
        assert "package.json" in snap
        assert "package-lock.json" in snap
        assert "pnpm-lock.yaml" not in snap
        assert "yarn.lock" not in snap

    def test_pnpm_snapshots_pnpm_lockfile(self, tmp_path):
        (tmp_path / "package.json").write_text('{"name":"test"}')
        (tmp_path / "pnpm-lock.yaml").write_text("lockfileVersion: '6.0'")
        snap = take_file_snapshot(tmp_path, "pnpm")
        assert "package.json" in snap
        assert "pnpm-lock.yaml" in snap
        assert "package-lock.json" not in snap

    def test_yarn_snapshots_yarn_lock(self, tmp_path):
        (tmp_path / "package.json").write_text('{"name":"test"}')
        (tmp_path / "yarn.lock").write_text("# yarn lockfile v1")
        snap = take_file_snapshot(tmp_path, "yarn")
        assert "package.json" in snap
        assert "yarn.lock" in snap
        assert "package-lock.json" not in snap

    def test_bun_snapshots_bun_lockfile(self, tmp_path):
        (tmp_path / "package.json").write_text('{"name":"test"}')
        (tmp_path / "bun.lockb").write_bytes(b"\x00bun")
        snap = take_file_snapshot(tmp_path, "bun")
        assert "package.json" in snap
        assert "bun.lockb" in snap

    def test_missing_files_snapshot_as_empty_string(self, tmp_path):
        snap = take_file_snapshot(tmp_path, "npm")
        assert snap.get("package-lock.json") == ""

    def test_defaults_to_npm(self, tmp_path):
        (tmp_path / "package-lock.json").write_text("{}")
        snap = take_file_snapshot(tmp_path)
        assert "package-lock.json" in snap


# ─── capture_manifest_diffs ───────────────────────────────────────────────────


class TestCaptureManifestDiffs:
    def test_npm_lockfile_change_detected(self):
        before = {"package.json": "{}", "package-lock.json": "old"}
        after  = {"package.json": "{}", "package-lock.json": "new"}
        manifest_changed, lockfile_changed, diffs = capture_manifest_diffs(
            before, after, "npm"
        )
        assert not manifest_changed
        assert lockfile_changed
        assert "package-lock.json" in diffs

    def test_pnpm_lockfile_change_detected(self):
        before = {"package.json": "{}", "pnpm-lock.yaml": "old"}
        after  = {"package.json": "{}", "pnpm-lock.yaml": "new"}
        _, lockfile_changed, diffs = capture_manifest_diffs(before, after, "pnpm")
        assert lockfile_changed
        assert "pnpm-lock.yaml" in diffs

    def test_yarn_lockfile_change_detected(self):
        before = {"package.json": "{}", "yarn.lock": "old"}
        after  = {"package.json": "{}", "yarn.lock": "new"}
        _, lockfile_changed, diffs = capture_manifest_diffs(before, after, "yarn")
        assert lockfile_changed
        assert "yarn.lock" in diffs

    def test_bun_lockfile_change_detected(self):
        before = {"package.json": "{}", "bun.lockb": "old"}
        after  = {"package.json": "{}", "bun.lockb": "new"}
        _, lockfile_changed, diffs = capture_manifest_diffs(before, after, "bun")
        assert lockfile_changed
        assert "bun.lockb" in diffs

    def test_manifest_change_detected(self):
        before = {"package.json": '{"deps":{}}', "package-lock.json": "x"}
        after  = {"package.json": '{"deps":{"lodash":"^4"}}', "package-lock.json": "x"}
        manifest_changed, lockfile_changed, _ = capture_manifest_diffs(
            before, after, "npm"
        )
        assert manifest_changed
        assert not lockfile_changed

    def test_no_changes_returns_false_false(self):
        snap = {"package.json": "{}", "package-lock.json": "same"}
        manifest_changed, lockfile_changed, diffs = capture_manifest_diffs(
            snap, snap, "npm"
        )
        assert not manifest_changed
        assert not lockfile_changed
        assert diffs == {}

    def test_defaults_to_npm(self):
        before = {"package.json": "{}", "package-lock.json": "old"}
        after  = {"package.json": "{}", "package-lock.json": "new"}
        _, lockfile_changed, _ = capture_manifest_diffs(before, after)
        assert lockfile_changed

    def test_npm_does_not_flag_pnpm_lockfile(self):
        # pnpm-lock.yaml is not in the npm package files list
        before = {"package.json": "{}", "pnpm-lock.yaml": "old"}
        after  = {"package.json": "{}", "pnpm-lock.yaml": "new"}
        _, lockfile_changed, _ = capture_manifest_diffs(before, after, "npm")
        assert not lockfile_changed


# ─── run_list_for_pm dispatcher ───────────────────────────────────────────────


class TestRunListForPm:
    def test_npm_calls_npm_list(self, tmp_path):
        fake_output = json.dumps({"name": "proj", "dependencies": {}})
        with patch("policy_scout.supply_chain.transitive.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout=fake_output, stderr=""
            )
            result = run_list_for_pm("npm", tmp_path)
        assert result is not None
        cmd = mock_run.call_args[0][0]
        assert cmd[0] == "npm"

    def test_pnpm_calls_pnpm_list(self, tmp_path):
        fake_output = json.dumps([{"name": "proj", "dependencies": {}}])
        with patch("policy_scout.supply_chain.transitive.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout=fake_output, stderr=""
            )
            result = run_list_for_pm("pnpm", tmp_path)
        assert result is not None
        cmd = mock_run.call_args[0][0]
        assert cmd[0] == "pnpm"

    def test_yarn_returns_none(self, tmp_path):
        result = run_list_for_pm("yarn", tmp_path)
        assert result is None

    def test_bun_returns_none(self, tmp_path):
        result = run_list_for_pm("bun", tmp_path)
        assert result is None

    def test_unknown_pm_returns_none(self, tmp_path):
        result = run_list_for_pm("unknown", tmp_path)
        assert result is None


class TestRunPnpmList:
    def test_array_output_normalised(self, tmp_path):
        payload = [{"name": "proj", "version": "1.0.0", "dependencies": {
            "lodash": {"version": "4.17.21"}
        }}]
        with patch("policy_scout.supply_chain.transitive.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout=json.dumps(payload), stderr=""
            )
            result = run_pnpm_list(tmp_path)
        assert result is not None
        assert result["name"] == "proj"
        assert "dependencies" in result

    def test_dict_output_returned_directly(self, tmp_path):
        payload = {"name": "proj", "dependencies": {}}
        with patch("policy_scout.supply_chain.transitive.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout=json.dumps(payload), stderr=""
            )
            result = run_pnpm_list(tmp_path)
        assert result == payload

    def test_empty_stdout_returns_none(self, tmp_path):
        with patch("policy_scout.supply_chain.transitive.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="err")
            result = run_pnpm_list(tmp_path)
        assert result is None

    def test_file_not_found_returns_none(self, tmp_path):
        with patch(
            "policy_scout.supply_chain.transitive.subprocess.run",
            side_effect=FileNotFoundError,
        ):
            result = run_pnpm_list(tmp_path)
        assert result is None

    def test_timeout_returns_none(self, tmp_path):
        import subprocess
        with patch(
            "policy_scout.supply_chain.transitive.subprocess.run",
            side_effect=subprocess.TimeoutExpired(["pnpm"], 30),
        ):
            result = run_pnpm_list(tmp_path)
        assert result is None

    def test_invalid_json_returns_none(self, tmp_path):
        with patch("policy_scout.supply_chain.transitive.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout="not json", stderr=""
            )
            result = run_pnpm_list(tmp_path)
        assert result is None


# ─── lockfile name constants ──────────────────────────────────────────────────


class TestLockfileNames:
    def test_all_pm_lockfiles_covered(self):
        for name in ("package-lock.json", "npm-shrinkwrap.json",
                     "pnpm-lock.yaml", "yarn.lock", "bun.lockb", "bun.lock"):
            assert name in _LOCKFILE_NAMES
