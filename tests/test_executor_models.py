"""Tests for executor models."""

from policy_scout.executor.models import ExecutionResult


def test_execution_result_creation():
    """Test ExecutionResult creation."""
    result = ExecutionResult(
        execution_id="exec_123",
        request_id="req_123",
        decision_id="dec_123",
        command="echo hello",
        cwd="/home/user/project",
    )

    assert result.execution_id == "exec_123"
    assert result.request_id == "req_123"
    assert result.decision_id == "dec_123"
    assert result.command == "echo hello"
    assert result.cwd == "/home/user/project"
    assert result.route == "direct"
    assert result.schema_version == 1


def test_execution_result_to_dict():
    """Test ExecutionResult serialization."""
    result = ExecutionResult(
        execution_id="exec_123",
        request_id="req_123",
        decision_id="dec_123",
        command="echo hello",
        cwd="/home/user/project",
        exit_code=0,
        duration_ms=100,
        stdout="hello",
        stderr="",
    )

    data = result.to_dict()

    assert data["execution_id"] == "exec_123"
    assert data["request_id"] == "req_123"
    assert data["decision_id"] == "dec_123"
    assert data["command"] == "echo hello"
    assert data["cwd"] == "/home/user/project"
    assert data["route"] == "direct"
    assert data["exit_code"] == 0
    assert data["duration_ms"] == 100
    assert data["stdout"] == "hello"
    assert data["stderr"] == ""
    assert data["schema_version"] == 1


def test_execution_result_defaults():
    """Test ExecutionResult default values."""
    result = ExecutionResult(
        execution_id="exec_123",
        request_id="req_123",
        decision_id="dec_123",
        command="echo hello",
        cwd="/home/user/project",
    )

    assert result.route == "direct"
    assert result.started_at is not None
    assert result.completed_at is None
    assert result.exit_code is None
    assert result.duration_ms is None
    assert result.stdout is None
    assert result.stderr is None
    assert result.schema_version == 1


def test_execution_result_id_prefix():
    """Test that execution IDs use exec_ prefix."""
    result = ExecutionResult(
        execution_id="exec_abc123",
        request_id="req_123",
        decision_id="dec_123",
        command="echo hello",
        cwd="/home/user/project",
    )

    assert result.execution_id.startswith("exec_")
