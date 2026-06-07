"""Tests for direct executor."""

from policy_scout.executor.direct_executor import DirectExecutor


def test_executor_does_not_execute_non_allowed():
    """Test that executor does not execute non-ALLOW/ALLOW_LOGGED decisions."""
    executor = DirectExecutor()

    # Test DENY decision
    result = executor.execute(
        command="echo hello",
        cwd="/tmp",
        request_id="req_123",
        decision_id="dec_123",
        decision="DENY",
    )

    assert result.exit_code is None
    assert result.duration_ms is None
    assert result.stdout is None
    assert result.stderr is None
    assert result.completed_at is not None

    # Test REQUIRE_APPROVAL decision
    result = executor.execute(
        command="echo hello",
        cwd="/tmp",
        request_id="req_123",
        decision_id="dec_123",
        decision="REQUIRE_APPROVAL",
    )

    assert result.exit_code is None
    assert result.duration_ms is None
    assert result.stdout is None
    assert result.stderr is None

    # Test SANDBOX_FIRST decision
    result = executor.execute(
        command="echo hello",
        cwd="/tmp",
        request_id="req_123",
        decision_id="dec_123",
        decision="SANDBOX_FIRST",
    )

    assert result.exit_code is None
    assert result.duration_ms is None
    assert result.stdout is None
    assert result.stderr is None


def test_executor_executes_allowed_command():
    """Test that executor executes ALLOW decision."""
    executor = DirectExecutor()

    result = executor.execute(
        command="echo hello",
        cwd="/tmp",
        request_id="req_123",
        decision_id="dec_123",
        decision="ALLOW",
    )

    assert result.exit_code == 0
    assert result.duration_ms is not None
    assert result.stdout is not None
    assert "hello" in result.stdout
    assert result.completed_at is not None


def test_executor_executes_allow_logged_command():
    """Test that executor executes ALLOW_LOGGED decision."""
    executor = DirectExecutor()

    result = executor.execute(
        command="echo world",
        cwd="/tmp",
        request_id="req_123",
        decision_id="dec_123",
        decision="ALLOW_LOGGED",
    )

    assert result.exit_code == 0
    assert result.duration_ms is not None
    assert result.stdout is not None
    assert "world" in result.stdout
    assert result.completed_at is not None


def test_executor_captures_non_zero_exit_code():
    """Test that executor captures non-zero exit codes."""
    executor = DirectExecutor()

    result = executor.execute(
        command="exit 1",
        cwd="/tmp",
        request_id="req_123",
        decision_id="dec_123",
        decision="ALLOW",
    )

    assert result.exit_code == 1
    assert result.duration_ms is not None
    assert result.completed_at is not None


def test_executor_redacts_secrets():
    """Test that executor redacts secret-like values."""
    executor = DirectExecutor()

    result = executor.execute(
        command='echo "OPENAI_API_KEY=sk-test123"',
        cwd="/tmp",
        request_id="req_123",
        decision_id="dec_123",
        decision="ALLOW",
    )

    assert result.exit_code == 0
    assert result.stdout is not None
    # Should be redacted
    assert "sk-test123" not in result.stdout
    assert "<redacted:" in result.stdout


def test_executor_limits_output_size():
    """Test that executor limits inline output size."""
    executor = DirectExecutor()

    # Create a command that produces large output
    large_output = "x" * 20000
    result = executor.execute(
        command=f"echo '{large_output}'",
        cwd="/tmp",
        request_id="req_123",
        decision_id="dec_123",
        decision="ALLOW",
    )

    assert result.exit_code == 0
    assert result.stdout is not None
    # Should be truncated
    assert len(result.stdout) < 20000
    assert "truncated" in result.stdout


def test_executor_execution_started_event():
    """Test CommandExecutionStarted event creation."""
    executor = DirectExecutor()

    event = executor.create_execution_started_event(
        request_id="req_123",
        execution_id="exec_123",
        command="echo hello",
    )

    assert event.event_type == "CommandExecutionStarted"
    assert event.request_id == "req_123"
    assert event.data["execution_id"] == "exec_123"
    assert event.data["command"] == "echo hello"


def test_executor_execution_completed_event():
    """Test CommandExecutionCompleted event creation."""
    executor = DirectExecutor()

    event = executor.create_execution_completed_event(
        request_id="req_123",
        execution_id="exec_123",
        command="echo hello",
        exit_code=0,
        duration_ms=100,
    )

    assert event.event_type == "CommandExecutionCompleted"
    assert event.request_id == "req_123"
    assert event.data["execution_id"] == "exec_123"
    assert event.data["exit_code"] == 0
    assert event.data["duration_ms"] == 100


def test_executor_execution_blocked_event():
    """Test CommandExecutionBlocked event creation."""
    executor = DirectExecutor()

    event = executor.create_execution_blocked_event(
        request_id="req_123",
        execution_id="exec_123",
        command="rm -rf /",
        decision="DENY",
        reason="Command denied by policy",
    )

    assert event.event_type == "CommandExecutionBlocked"
    assert event.request_id == "req_123"
    assert event.data["execution_id"] == "exec_123"
    assert event.data["decision"] == "DENY"
    assert event.data["reason"] == "Command denied by policy"


def test_executor_execution_failed_event():
    """Test CommandExecutionFailed event creation."""
    executor = DirectExecutor()

    event = executor.create_execution_failed_event(
        request_id="req_123",
        execution_id="exec_123",
        command="invalid-command",
        error_message="Command not found",
    )

    assert event.event_type == "CommandExecutionFailed"
    assert event.request_id == "req_123"
    assert event.data["execution_id"] == "exec_123"
    assert event.data["error"] == "Command not found"
