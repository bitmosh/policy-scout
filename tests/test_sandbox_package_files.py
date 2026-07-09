# SPDX-License-Identifier: Apache-2.0
"""Tests for sandbox package file copying."""

import json
import tempfile
from pathlib import Path
from policy_scout.sandbox.package_files import (
    copy_package_files,
    has_token_like_content,
    create_minimal_package_json,
)


def test_has_token_like_content_with_token():
    """Test detection of token-like content."""
    with tempfile.TemporaryDirectory() as tmpdir:
        npmrc_path = Path(tmpdir) / ".npmrc"
        npmrc_path.write_text("//registry.npmjs.org/:_authToken=secret123")

        assert has_token_like_content(npmrc_path)


def test_has_token_like_content_without_token():
    """Test that safe content is not flagged."""
    with tempfile.TemporaryDirectory() as tmpdir:
        npmrc_path = Path(tmpdir) / ".npmrc"
        npmrc_path.write_text("registry=https://registry.npmjs.org")

        assert not has_token_like_content(npmrc_path)


def test_has_token_like_content_nonexistent():
    """Test that nonexistent file returns False."""
    assert not has_token_like_content(Path("/tmp/nonexistent"))


def test_copy_package_files():
    """Test copying package files from host to sandbox."""
    with tempfile.TemporaryDirectory() as tmpdir:
        host_dir = Path(tmpdir) / "host"
        sandbox_dir = Path(tmpdir) / "sandbox"
        host_dir.mkdir()
        sandbox_dir.mkdir()

        # Create package.json
        package_json = host_dir / "package.json"
        package_json.write_text('{"name": "test", "version": "1.0.0"}')

        copied, skipped = copy_package_files(host_dir, sandbox_dir)

        assert "package.json" in copied
        assert (sandbox_dir / "package.json").exists()
        assert (
            sandbox_dir / "package.json"
        ).read_text() == '{"name": "test", "version": "1.0.0"}'


def test_copy_package_files_skips_token_npmrc():
    """Test that token-bearing .npmrc is skipped."""
    with tempfile.TemporaryDirectory() as tmpdir:
        host_dir = Path(tmpdir) / "host"
        sandbox_dir = Path(tmpdir) / "sandbox"
        host_dir.mkdir()
        sandbox_dir.mkdir()

        # Create token-bearing .npmrc
        npmrc = host_dir / ".npmrc"
        npmrc.write_text("//registry.npmjs.org/:_authToken=secret123")

        copied, skipped = copy_package_files(host_dir, sandbox_dir)

        assert ".npmrc" in skipped
        assert ".npmrc" not in copied
        assert not (sandbox_dir / ".npmrc").exists()


def test_copy_package_files_copies_safe_npmrc():
    """Test that safe .npmrc is copied."""
    with tempfile.TemporaryDirectory() as tmpdir:
        host_dir = Path(tmpdir) / "host"
        sandbox_dir = Path(tmpdir) / "sandbox"
        host_dir.mkdir()
        sandbox_dir.mkdir()

        # Create safe .npmrc
        npmrc = host_dir / ".npmrc"
        npmrc.write_text("registry=https://registry.npmjs.org")

        copied, skipped = copy_package_files(host_dir, sandbox_dir)

        assert ".npmrc" in copied
        assert ".npmrc" not in skipped
        assert (sandbox_dir / ".npmrc").exists()


def test_copy_package_files_only_copies_existing():
    """Test that only existing files are copied."""
    with tempfile.TemporaryDirectory() as tmpdir:
        host_dir = Path(tmpdir) / "host"
        sandbox_dir = Path(tmpdir) / "sandbox"
        host_dir.mkdir()
        sandbox_dir.mkdir()

        copied, skipped = copy_package_files(host_dir, sandbox_dir)

        assert len(copied) == 0
        assert len(skipped) == 0


def test_create_minimal_package_json():
    """Test creating minimal package.json in sandbox."""
    with tempfile.TemporaryDirectory() as tmpdir:
        sandbox_dir = Path(tmpdir)

        package_json_path = create_minimal_package_json(sandbox_dir, "test-package")

        assert package_json_path.exists()
        content = json.loads(package_json_path.read_text())
        assert content["name"] == "test-package"
        assert content["version"] == "1.0.0"
        assert content["private"]


def test_create_minimal_package_json_without_package_name():
    """Test creating minimal package.json without package name."""
    with tempfile.TemporaryDirectory() as tmpdir:
        sandbox_dir = Path(tmpdir)

        package_json_path = create_minimal_package_json(sandbox_dir)

        assert package_json_path.exists()
        content = json.loads(package_json_path.read_text())
        assert content["name"] == "sandbox-review"


def test_host_package_json_not_mutated():
    """Test that host package.json is not mutated during copy."""
    with tempfile.TemporaryDirectory() as tmpdir:
        host_dir = Path(tmpdir) / "host"
        sandbox_dir = Path(tmpdir) / "sandbox"
        host_dir.mkdir()
        sandbox_dir.mkdir()

        # Create package.json
        package_json = host_dir / "package.json"
        original_content = '{"name": "test", "version": "1.0.0"}'
        package_json.write_text(original_content)

        copy_package_files(host_dir, sandbox_dir)

        # Verify host file unchanged
        assert package_json.read_text() == original_content
