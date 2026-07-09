# SPDX-License-Identifier: Apache-2.0
"""Generic package manager runner for sandbox."""

import subprocess
import time
from pathlib import Path
from typing import Tuple
from ..audit.redaction import redact_string


def run_package_manager_install(
    package_manager: str,
    sandbox_workspace: Path,
    command_args: list,
    timeout: int = 60
) -> Tuple[int, str, str, int]:
    """Run package manager install in the sandbox workspace.
    
    Args:
        package_manager: Package manager name (npm, pnpm, yarn, bun).
        sandbox_workspace: Path to the sandbox workspace.
        command_args: Command arguments (e.g., ["install", "lodash"]).
        timeout: Timeout in seconds.
        
    Returns:
        Tuple of (exit_code, stdout, stderr, duration_ms).
    """
    start_time = time.time()
    
    try:
        # Run package manager install in the sandbox workspace
        result = subprocess.run(
            [package_manager] + command_args,
            cwd=sandbox_workspace,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        exit_code = result.returncode
        stdout = result.stdout
        stderr = result.stderr
        
    except subprocess.TimeoutExpired:
        exit_code = -1
        stdout = ""
        stderr = f"Command timed out after {timeout} seconds"
    except FileNotFoundError:
        exit_code = -1
        stdout = ""
        stderr = f"Package manager executable not found: {package_manager}"
    except Exception as e:
        exit_code = -1
        stdout = ""
        stderr = str(e)
    
    duration_ms = int((time.time() - start_time) * 1000)
    
    # Redact sensitive information from output
    stdout = redact_string(stdout)
    stderr = redact_string(stderr)
    
    return exit_code, stdout, stderr, duration_ms
