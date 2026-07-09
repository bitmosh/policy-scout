# SPDX-License-Identifier: Apache-2.0
"""Direct executor for policy-gated command execution."""

import subprocess
import time

from ..audit.redaction import redact_string
from ..audit.events import AuditEvent
from ..core.ids import generate_id, utcnow_iso
from .models import ExecutionResult


class DirectExecutor:
    """Executes commands directly on the host after policy decision."""

    def __init__(self):
        """Initialize the direct executor."""
        pass

    def execute(
        self,
        command: str,
        cwd: str,
        request_id: str,
        decision_id: str,
        decision: str,
        execution_id: str = None,
    ) -> ExecutionResult:
        """
        Execute a command based on policy decision.

        Args:
            command: The command to execute
            cwd: Current working directory
            request_id: The request ID
            decision_id: The decision ID
            decision: The policy decision (ALLOW, ALLOW_LOGGED, etc.)
            execution_id: Optional pre-generated execution ID

        Returns:
            ExecutionResult with execution details

        Raises:
            ValueError: If decision is not ALLOW or ALLOW_LOGGED
        """
        if execution_id is None:
            execution_id = generate_id("exec")
        result = ExecutionResult(
            execution_id=execution_id,
            request_id=request_id,
            decision_id=decision_id,
            command=command,
            cwd=cwd,
            route="direct",
        )

        # Only execute ALLOW or ALLOW_LOGGED commands
        if decision not in ["ALLOW", "ALLOW_LOGGED"]:
            result.completed_at = utcnow_iso()
            result.exit_code = None
            result.duration_ms = None
            return result

        # Execute the command
        start_time = time.time()
        result.started_at = utcnow_iso()

        try:
            process = subprocess.Popen(
                command,
                shell=True,
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            stdout, stderr = process.communicate()
            exit_code = process.returncode

            # Redact sensitive data
            redacted_stdout = redact_string(stdout) if stdout else None
            redacted_stderr = redact_string(stderr) if stderr else None

            # Limit output size for inline storage (max 10KB)
            max_inline_size = 10240
            if redacted_stdout and len(redacted_stdout) > max_inline_size:
                redacted_stdout = redacted_stdout[:max_inline_size] + "... (truncated)"
            if redacted_stderr and len(redacted_stderr) > max_inline_size:
                redacted_stderr = redacted_stderr[:max_inline_size] + "... (truncated)"

            result.stdout = redacted_stdout
            result.stderr = redacted_stderr
            result.exit_code = exit_code

        except Exception as e:
            result.exit_code = -1
            result.stderr = f"Execution error: {str(e)}"

        end_time = time.time()
        result.duration_ms = int((end_time - start_time) * 1000)
        result.completed_at = utcnow_iso()

        return result

    def create_execution_started_event(
        self, request_id: str, execution_id: str, command: str, approval_id: str = ""
    ) -> AuditEvent:
        """Create a CommandExecutionStarted event."""
        data = {
            "execution_id": execution_id,
            "command": command,
        }
        if approval_id:
            data["approval_id"] = approval_id
        return AuditEvent(
            event_type="CommandExecutionStarted",
            request_id=request_id,
            summary=f"Command execution started: {command}",
            data=data,
        )

    def create_execution_completed_event(
        self,
        request_id: str,
        execution_id: str,
        command: str,
        exit_code: int,
        duration_ms: int,
    ) -> AuditEvent:
        """Create a CommandExecutionCompleted event."""
        return AuditEvent(
            event_type="CommandExecutionCompleted",
            request_id=request_id,
            summary=f"Command execution completed with exit code: {exit_code}",
            data={
                "execution_id": execution_id,
                "command": command,
                "exit_code": exit_code,
                "duration_ms": duration_ms,
            },
        )

    def create_execution_blocked_event(
        self,
        request_id: str,
        execution_id: str,
        command: str,
        decision: str,
        reason: str,
    ) -> AuditEvent:
        """Create a CommandExecutionBlocked event."""
        return AuditEvent(
            event_type="CommandExecutionBlocked",
            request_id=request_id,
            summary=f"Command execution blocked: {decision}",
            data={
                "execution_id": execution_id,
                "command": command,
                "decision": decision,
                "reason": reason,
            },
        )

    def create_execution_failed_event(
        self,
        request_id: str,
        execution_id: str,
        command: str,
        error_message: str,
    ) -> AuditEvent:
        """Create a CommandExecutionFailed event."""
        return AuditEvent(
            event_type="CommandExecutionFailed",
            request_id=request_id,
            summary="Command execution failed",
            data={
                "execution_id": execution_id,
                "command": command,
                "error": error_message,
            },
        )
