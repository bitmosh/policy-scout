# SPDX-License-Identifier: Apache-2.0
"""Tests for sandbox workspace creation."""

import os
import tempfile
from pathlib import Path
from policy_scout.sandbox.temp_workspace import create_sandbox_workspace, get_sandbox_root, cleanup_sandbox_workspace


def test_get_sandbox_root_default():
    """Test default sandbox root path."""
    os.environ.pop("POLICY_SCOUT_SANDBOX_ROOT", None)
    root = get_sandbox_root()
    expected = Path.home() / ".local" / "share" / "policy-scout" / "sandboxes"
    assert root == expected


def test_get_sandbox_root_env_override():
    """Test sandbox root with environment override."""
    test_path = "/tmp/test-sandboxes"
    os.environ["POLICY_SCOUT_SANDBOX_ROOT"] = test_path
    root = get_sandbox_root()
    assert root == Path(test_path)
    os.environ.pop("POLICY_SCOUT_SANDBOX_ROOT", None)


def test_create_sandbox_workspace():
    """Test sandbox workspace creation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        os.environ["POLICY_SCOUT_SANDBOX_ROOT"] = tmpdir
        
        try:
            workspace = create_sandbox_workspace("sbx_test123")
            
            assert workspace.exists()
            assert workspace.is_dir()
            assert workspace.name == "sbx_test123"
            assert workspace.parent == Path(tmpdir)
        finally:
            os.environ.pop("POLICY_SCOUT_SANDBOX_ROOT", None)


def test_create_sandbox_workspace_generates_id():
    """Test that workspace creation generates ID if not provided."""
    with tempfile.TemporaryDirectory() as tmpdir:
        os.environ["POLICY_SCOUT_SANDBOX_ROOT"] = tmpdir
        
        try:
            workspace = create_sandbox_workspace()
            
            assert workspace.exists()
            assert workspace.name.startswith("sbx_")
        finally:
            os.environ.pop("POLICY_SCOUT_SANDBOX_ROOT", None)


def test_cleanup_sandbox_workspace():
    """Test sandbox workspace cleanup."""
    with tempfile.TemporaryDirectory() as tmpdir:
        os.environ["POLICY_SCOUT_SANDBOX_ROOT"] = tmpdir
        
        try:
            workspace = create_sandbox_workspace("sbx_test123")
            assert workspace.exists()
            
            success = cleanup_sandbox_workspace(workspace)
            assert success
            assert not workspace.exists()
        finally:
            os.environ.pop("POLICY_SCOUT_SANDBOX_ROOT", None)


def test_cleanup_nonexistent_workspace():
    """Test cleanup of nonexistent workspace returns True."""
    workspace = Path("/tmp/nonexistent-sbx-test")
    success = cleanup_sandbox_workspace(workspace)
    assert success
