"""Evidence preservation for incident response.

Creates a ZIP archive of current system state for post-incident analysis.
"""

import json
import os
import platform
import subprocess
import sys
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

_DATA_DIR = Path.home() / ".local" / "share" / "policy-scout"


@dataclass
class EvidenceArchive:
    """Result of an evidence preservation run."""

    path: str
    artifact_count: int
    artifacts: list = field(default_factory=list)
    errors: list = field(default_factory=list)


def _run_cmd(args: list[str]) -> str:
    """Run a command and return stdout. Returns empty string on failure."""
    try:
        result = subprocess.run(
            args, capture_output=True, text=True, timeout=10
        )
        return result.stdout
    except Exception:
        return ""


def preserve_evidence(
    output_dir: Optional[Path] = None,
    audit_store=None,
) -> EvidenceArchive:
    """Capture current system state into a ZIP archive.

    Artifacts captured:
    - Audit database (SQLite) and JSONL file
    - Process list (ps aux)
    - Listening ports (ss -tlnp or netstat)
    - Shell profile structure (list of rc files, not contents)
    - Package manifests in current directory (package.json, pyproject.toml, etc.)
    - System info (hostname, uname, env variable names only)

    Returns EvidenceArchive with the path and count of captured artifacts.
    """
    if output_dir is None:
        output_dir = _DATA_DIR / "evidence"
    output_dir.mkdir(parents=True, exist_ok=True)

    from ..core.ids import utcnow_iso
    timestamp = utcnow_iso().replace(":", "").replace("-", "").replace("T", "_")[:15]
    archive_path = output_dir / f"evidence_{timestamp}.zip"

    artifacts: list[str] = []
    errors: list[str] = []

    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # --- System info (no sensitive values) ---
        try:
            system_info = {
                "hostname": platform.node(),
                "system": platform.system(),
                "release": platform.release(),
                "machine": platform.machine(),
                "python_version": platform.python_version(),
                "env_variable_names": sorted(os.environ.keys()),
                "captured_at": utcnow_iso(),
            }
            zf.writestr("system_info.json", json.dumps(system_info, indent=2))
            artifacts.append("system_info.json")
        except Exception as e:
            errors.append(f"system_info: {e}")

        # --- Audit SQLite DB ---
        audit_db = _DATA_DIR / "audit.db"
        if audit_db.exists():
            try:
                zf.write(audit_db, "audit.db")
                artifacts.append("audit.db")
            except Exception as e:
                errors.append(f"audit.db: {e}")

        # --- Audit JSONL ---
        env_jsonl = os.environ.get("POLICY_SCOUT_AUDIT_PATH")
        audit_jsonl = Path(env_jsonl) if env_jsonl else _DATA_DIR / "audit.jsonl"
        if audit_jsonl.exists():
            try:
                zf.write(audit_jsonl, "audit.jsonl")
                artifacts.append("audit.jsonl")
            except Exception as e:
                errors.append(f"audit.jsonl: {e}")

        # --- Process list ---
        try:
            ps_output = _run_cmd(["ps", "aux"])
            if ps_output:
                zf.writestr("processes.txt", ps_output)
                artifacts.append("processes.txt")
        except Exception as e:
            errors.append(f"processes: {e}")

        # --- Listening ports ---
        try:
            ports_output = _run_cmd(["ss", "-tlnp"])
            if not ports_output:
                ports_output = _run_cmd(["netstat", "-tlnp"])
            if ports_output:
                zf.writestr("ports.txt", ports_output)
                artifacts.append("ports.txt")
        except Exception as e:
            errors.append(f"ports: {e}")

        # --- Shell profile names (not contents) ---
        try:
            rc_files = []
            for pattern in ["~/.bashrc", "~/.bash_profile", "~/.zshrc", "~/.profile"]:
                p = Path(pattern).expanduser()
                if p.exists():
                    rc_files.append(str(p))
            zf.writestr("shell_profiles.json", json.dumps(rc_files, indent=2))
            artifacts.append("shell_profiles.json")
        except Exception as e:
            errors.append(f"shell_profiles: {e}")

        # --- Package manifests in CWD ---
        try:
            manifests = {}
            for name in ["package.json", "pyproject.toml", "Cargo.toml", "go.mod"]:
                p = Path.cwd() / name
                if p.exists():
                    manifests[name] = p.read_text()
            if manifests:
                zf.writestr(
                    "package_manifests.json", json.dumps(manifests, indent=2)
                )
                artifacts.append("package_manifests.json")
        except Exception as e:
            errors.append(f"package_manifests: {e}")

        # --- Git log (if in a repo) ---
        try:
            git_log = _run_cmd(["git", "log", "--oneline", "-20"])
            if git_log:
                zf.writestr("git_log.txt", git_log)
                artifacts.append("git_log.txt")
        except Exception as e:
            errors.append(f"git_log: {e}")

    result = EvidenceArchive(
        path=str(archive_path),
        artifact_count=len(artifacts),
        artifacts=artifacts,
        errors=errors,
    )

    if audit_store is not None:
        try:
            from ..audit.events import create_evidence_preserved_event
            audit_store.write(
                create_evidence_preserved_event(
                    archive_path=str(archive_path),
                    artifact_count=len(artifacts),
                )
            )
        except Exception:
            pass

    return result
