"""Tests for sandbox manifest/lockfile diff capture."""

import tempfile
from pathlib import Path
from policy_scout.sandbox.diff import (
    take_file_snapshot,
    capture_manifest_diffs,
    _simple_diff,
)


def test_take_file_snapshot():
    """Test taking snapshot of package files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)

        # Create package.json
        package_json = workspace / "package.json"
        package_json.write_text('{"name": "test", "version": "1.0.0"}')

        snapshot = take_file_snapshot(workspace)

        assert "package.json" in snapshot
        assert snapshot["package.json"] == '{"name": "test", "version": "1.0.0"}'
        assert snapshot["package-lock.json"] == ""
        assert snapshot["npm-shrinkwrap.json"] == ""


def test_take_file_snapshot_empty_workspace():
    """Test snapshot of empty workspace."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)

        snapshot = take_file_snapshot(workspace)

        assert snapshot["package.json"] == ""
        assert snapshot["package-lock.json"] == ""
        assert snapshot["npm-shrinkwrap.json"] == ""


def test_capture_manifest_diffs_no_changes():
    """Test diff capture when no changes occurred."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)

        before = {"package.json": '{"name": "test"}'}
        after = {"package.json": '{"name": "test"}'}

        manifest_changed, lockfile_changed, diffs = capture_manifest_diffs(
            workspace, before, after
        )

        assert not manifest_changed
        assert not lockfile_changed
        # When no changes, key may not be in diffs
        assert "package.json" not in diffs or diffs["package.json"] == "No changes"


def test_capture_manifest_diffs_package_json_changed():
    """Test diff capture when package.json changed."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)

        before = {"package.json": '{"name": "test"}'}
        after = {
            "package.json": '{"name": "test", "dependencies": {"lodash": "^4.0.0"}}'
        }

        manifest_changed, lockfile_changed, diffs = capture_manifest_diffs(
            workspace, before, after
        )

        assert manifest_changed
        assert not lockfile_changed
        assert "Content changed" in diffs["package.json"]


def test_capture_manifest_diffs_lockfile_created():
    """Test diff capture when lockfile is created."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)

        before = {"package-lock.json": ""}
        after = {"package-lock.json": '{"lockfileVersion": 2}'}

        manifest_changed, lockfile_changed, diffs = capture_manifest_diffs(
            workspace, before, after
        )

        assert not manifest_changed
        assert lockfile_changed
        assert diffs["package-lock.json"] == "File created"


def test_capture_manifest_diffs_lockfile_changed():
    """Test diff capture when lockfile changed."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)

        before = {"package-lock.json": '{"lockfileVersion": 1}'}
        after = {"package-lock.json": '{"lockfileVersion": 2}'}

        manifest_changed, lockfile_changed, diffs = capture_manifest_diffs(
            workspace, before, after
        )

        assert not manifest_changed
        assert lockfile_changed
        assert "Content changed" in diffs["package-lock.json"]


def test_simple_diff_no_changes():
    """Test simple diff with no changes."""
    diff = _simple_diff("same content", "same content")
    assert diff == "No changes"


def test_simple_diff_created():
    """Test simple diff when file created."""
    diff = _simple_diff("", "new content")
    assert diff == "File created"


def test_simple_diff_deleted():
    """Test simple diff when file deleted."""
    diff = _simple_diff("old content", "")
    assert diff == "File deleted"


def test_simple_diff_changed():
    """Test simple diff when content changed."""
    diff = _simple_diff("line1\nline2", "line1\nline2\nline3")
    assert "Content changed" in diff
    assert "2 lines" in diff
    assert "3 lines" in diff
