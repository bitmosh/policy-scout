"""Sandbox module for package install review."""

from policy_scout.sandbox.models import SandboxResult
from policy_scout.sandbox.temp_workspace import create_sandbox_workspace
from policy_scout.sandbox.package_files import copy_package_files
from policy_scout.sandbox.npm_runner import run_npm_install
from policy_scout.sandbox.lifecycle_inspector import inspect_lifecycle_scripts
from policy_scout.sandbox.diff import capture_manifest_diffs
from policy_scout.sandbox.result_writer import write_sandbox_result

__all__ = [
    "SandboxResult",
    "create_sandbox_workspace",
    "copy_package_files",
    "run_npm_install",
    "inspect_lifecycle_scripts",
    "capture_manifest_diffs",
    "write_sandbox_result",
]
