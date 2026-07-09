# SPDX-License-Identifier: Apache-2.0
"""Tests for sandbox models."""

from policy_scout.sandbox.models import SandboxResult, LifecycleScript


def test_sandbox_result_structure():
    """Test sandbox result has required fields."""
    result = SandboxResult(
        sandbox_id="sbx_test123",
        request_id="req_test",
        command="npm install lodash",
        package_manager="npm",
        temp_workspace="/tmp/sbx_test123",
        exit_code=0,
        duration_ms=2400,
        manifest_changed=True,
        lockfile_changed=True,
    )

    assert result.sandbox_id == "sbx_test123"
    assert result.request_id == "req_test"
    assert result.command == "npm install lodash"
    assert result.package_manager == "npm"
    assert result.temp_workspace == "/tmp/sbx_test123"
    assert result.exit_code == 0
    assert result.duration_ms == 2400
    assert result.manifest_changed
    assert result.lockfile_changed
    assert result.migration_available
    assert result.migration_requires_approval
    assert result.schema_version == 1


def test_sandbox_result_to_dict():
    """Test sandbox result serialization."""
    result = SandboxResult(
        sandbox_id="sbx_test123",
        request_id="req_test",
        command="npm install lodash",
        package_manager="npm",
        temp_workspace="/tmp/sbx_test123",
        exit_code=0,
        duration_ms=2400,
    )

    result_dict = result.to_dict()

    assert result_dict["sandbox_id"] == result.sandbox_id
    assert result_dict["request_id"] == result.request_id
    assert result_dict["command"] == result.command
    assert result_dict["package_manager"] == result.package_manager
    assert result_dict["temp_workspace"] == result.temp_workspace
    assert result_dict["exit_code"] == result.exit_code
    assert result_dict["duration_ms"] == result.duration_ms


def test_sandbox_result_from_dict():
    """Test sandbox result deserialization."""
    data = {
        "sandbox_id": "sbx_test123",
        "request_id": "req_test",
        "command": "npm install lodash",
        "package_manager": "npm",
        "temp_workspace": "/tmp/sbx_test123",
        "exit_code": 0,
        "duration_ms": 2400,
        "manifest_changed": True,
        "lockfile_changed": True,
        "lifecycle_scripts_found": [],
        "findings": [],
        "migration_available": True,
        "migration_requires_approval": True,
        "schema_version": 1,
    }

    result = SandboxResult.from_dict(data)

    assert result.sandbox_id == "sbx_test123"
    assert result.request_id == "req_test"
    assert result.command == "npm install lodash"
    assert result.package_manager == "npm"
    assert result.temp_workspace == "/tmp/sbx_test123"
    assert result.exit_code == 0
    assert result.duration_ms == 2400


def test_lifecycle_script_structure():
    """Test lifecycle script structure."""
    script = LifecycleScript(
        package_name="lodash",
        script_name="postinstall",
        script_content="echo 'installing'",
        location="/tmp/node_modules/lodash/package.json",
    )

    assert script.package_name == "lodash"
    assert script.script_name == "postinstall"
    assert script.script_content == "echo 'installing'"
    assert script.location == "/tmp/node_modules/lodash/package.json"


def test_sandbox_id_starts_with_sbx():
    """Test that sandbox ID starts with sbx_."""
    result = SandboxResult()
    assert result.sandbox_id.startswith("sbx_")
