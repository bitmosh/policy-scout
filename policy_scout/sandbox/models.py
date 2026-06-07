"""Sandbox result models."""

from dataclasses import dataclass, field
from typing import List, Dict, Any
from ..core.ids import generate_id, utcnow_iso


@dataclass
class LifecycleScript:
    """Represents a lifecycle script found in a package manifest."""

    package_name: str
    script_name: str
    script_content: str
    location: str


@dataclass
class SandboxResult:
    """Represents sandbox package install review result."""

    sandbox_id: str = field(default_factory=lambda: generate_id("sbx"))
    request_id: str = ""
    command: str = ""
    package_manager: str = "npm"
    temp_workspace: str = ""
    host_project_root: str = ""
    started_at: str = field(default_factory=utcnow_iso)
    completed_at: str = ""
    duration_ms: int = 0
    exit_code: int = 0
    stdout: str = ""
    stderr: str = ""
    manifest_changed: bool = False
    lockfile_changed: bool = False
    lifecycle_scripts_found: List[LifecycleScript] = field(default_factory=list)
    findings: List[Dict[str, Any]] = field(default_factory=list)
    migration_available: bool = True
    migration_requires_approval: bool = True
    schema_version: int = 1

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {
            "sandbox_id": self.sandbox_id,
            "request_id": self.request_id,
            "command": self.command,
            "package_manager": self.package_manager,
            "temp_workspace": self.temp_workspace,
            "host_project_root": self.host_project_root,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration_ms": self.duration_ms,
            "exit_code": self.exit_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "manifest_changed": self.manifest_changed,
            "lockfile_changed": self.lockfile_changed,
            "lifecycle_scripts_found": [
                {
                    "package_name": s.package_name,
                    "script_name": s.script_name,
                    "script_content": s.script_content,
                    "location": s.location,
                }
                for s in self.lifecycle_scripts_found
            ],
            "findings": self.findings,
            "migration_available": self.migration_available,
            "migration_requires_approval": self.migration_requires_approval,
            "schema_version": self.schema_version,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SandboxResult":
        """Create from dict."""
        lifecycle_scripts = [
            LifecycleScript(
                package_name=s["package_name"],
                script_name=s["script_name"],
                script_content=s["script_content"],
                location=s["location"],
            )
            for s in data.get("lifecycle_scripts_found", [])
        ]

        return cls(
            sandbox_id=data.get("sandbox_id", ""),
            request_id=data.get("request_id", ""),
            command=data.get("command", ""),
            package_manager=data.get("package_manager", "npm"),
            temp_workspace=data.get("temp_workspace", ""),
            host_project_root=data.get("host_project_root", ""),
            started_at=data.get("started_at", ""),
            completed_at=data.get("completed_at", ""),
            duration_ms=data.get("duration_ms", 0),
            exit_code=data.get("exit_code", 0),
            stdout=data.get("stdout", ""),
            stderr=data.get("stderr", ""),
            manifest_changed=data.get("manifest_changed", False),
            lockfile_changed=data.get("lockfile_changed", False),
            lifecycle_scripts_found=lifecycle_scripts,
            findings=data.get("findings", []),
            migration_available=data.get("migration_available", False),
            migration_requires_approval=data.get("migration_requires_approval", True),
            schema_version=data.get("schema_version", 1),
        )


@dataclass
class MigrationResult:
    """Represents sandbox migration result."""

    migration_id: str = field(default_factory=lambda: generate_id("mig"))
    sandbox_id: str = ""
    request_id: str = ""
    started_at: str = field(default_factory=utcnow_iso)
    completed_at: str = ""
    host_project_root: str = ""
    sandbox_workspace: str = ""
    files_planned: List[str] = field(default_factory=list)
    files_migrated: List[str] = field(default_factory=list)
    files_skipped: List[str] = field(default_factory=list)
    backups_created: List[str] = field(default_factory=list)
    blocked: bool = False
    block_reasons: List[str] = field(default_factory=list)
    success: bool = False
    schema_version: int = 1

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {
            "migration_id": self.migration_id,
            "sandbox_id": self.sandbox_id,
            "request_id": self.request_id,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "host_project_root": self.host_project_root,
            "sandbox_workspace": self.sandbox_workspace,
            "files_planned": self.files_planned,
            "files_migrated": self.files_migrated,
            "files_skipped": self.files_skipped,
            "backups_created": self.backups_created,
            "blocked": self.blocked,
            "block_reasons": self.block_reasons,
            "success": self.success,
            "schema_version": self.schema_version,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MigrationResult":
        """Create from dict."""
        return cls(
            migration_id=data.get("migration_id", ""),
            sandbox_id=data.get("sandbox_id", ""),
            request_id=data.get("request_id", ""),
            started_at=data.get("started_at", ""),
            completed_at=data.get("completed_at", ""),
            host_project_root=data.get("host_project_root", ""),
            sandbox_workspace=data.get("sandbox_workspace", ""),
            files_planned=data.get("files_planned", []),
            files_migrated=data.get("files_migrated", []),
            files_skipped=data.get("files_skipped", []),
            backups_created=data.get("backups_created", []),
            blocked=data.get("blocked", False),
            block_reasons=data.get("block_reasons", []),
            success=data.get("success", False),
            schema_version=data.get("schema_version", 1),
        )
