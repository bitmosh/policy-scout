# SPDX-License-Identifier: Apache-2.0
"""Policy Scout doctor command for health diagnostics."""

import sys
import os
import json
import platform
import shutil
import importlib.util
from typing import Dict, Any
from pathlib import Path


def get_python_version() -> str:
    """Get Python version."""
    return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"


def get_platform_info() -> Dict[str, str]:
    """Get platform information."""
    return {
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor(),
    }


def get_policy_scout_version() -> str:
    """Get Policy Scout version or fallback."""
    try:
        from policy_scout import __version__

        return __version__
    except (ImportError, AttributeError):
        return "v0.1-alpha"


def check_cli_import_health() -> Dict[str, Any]:
    """Check if CLI can be imported."""
    spec = importlib.util.find_spec("policy_scout.cli.main")
    if spec is not None:
        return {"status": "ok", "message": "CLI import successful"}
    return {"status": "error", "message": "CLI import failed: module not found"}


def check_python_version() -> Dict[str, Any]:
    """Check Python version compatibility."""
    version = sys.version_info
    if version.major == 3 and version.minor >= 12:
        return {
            "status": "ok",
            "message": f"Python {version.major}.{version.minor}.{version.micro} is compatible (>= 3.12)",
        }
    return {
        "status": "error",
        "message": f"Python {version.major}.{version.minor}.{version.micro} is not compatible (requires >= 3.12)",
    }


def check_registry_file(name: str, path: str) -> Dict[str, Any]:
    """Check if a registry file loads successfully."""
    try:
        from policy_scout.registry.loader import RegistryLoader

        loader = RegistryLoader()
        if name == "command_registry":
            data = loader.load_command_registry(Path(path))
            entry_count = len(data.commands)
            return {
                "status": "ok",
                "message": f"{name} loaded successfully",
                "entry_count": entry_count,
            }
        elif name == "default_policy":
            data = loader.load_policy_registry(Path(path))
            entry_count = len(data.policies)
            return {
                "status": "ok",
                "message": f"{name} loaded successfully",
                "entry_count": entry_count,
            }
    except FileNotFoundError:
        return {"status": "error", "message": f"{name} not found at {path}"}
    except Exception as e:
        return {"status": "error", "message": f"{name} load failed: {e}"}


def check_eval_cases(path: str) -> Dict[str, Any]:
    """Check if eval cases load successfully."""
    try:
        from policy_scout.evals.loader import load_eval_cases

        cases = load_eval_cases(path)
        return {
            "status": "ok",
            "message": "eval_cases.yaml loaded successfully",
            "entry_count": len(cases),
        }
    except FileNotFoundError:
        return {"status": "error", "message": f"eval_cases.yaml not found at {path}"}
    except Exception as e:
        return {"status": "error", "message": f"eval_cases.yaml load failed: {e}"}


def check_audit_store() -> Dict[str, Any]:
    """Check audit store availability (read-only check)."""
    try:
        # Default path from SQLiteAuditStore
        db_path = str(Path.home() / ".local" / "share" / "policy-scout" / "audit.db")

        # Support environment variable override
        env_path = os.environ.get("POLICY_SCOUT_AUDIT_DB_PATH")
        if env_path:
            db_path = env_path

        db_dir = Path(db_path).parent

        # Check if directory exists (read-only check)
        if not db_dir.exists():
            return {
                "status": "warning",
                "message": f"Audit directory does not exist: {db_dir}",
                "path": str(db_path),
            }

        # Check if directory is writable
        if not os.access(db_dir, os.W_OK):
            return {
                "status": "error",
                "message": f"Audit directory is not writable: {db_dir}",
                "path": str(db_path),
            }

        return {
            "status": "ok",
            "message": f"Audit store available at {db_path}",
            "path": str(db_path),
        }
    except Exception as e:
        return {"status": "error", "message": f"Audit store check failed: {e}"}


def check_lockdown_status() -> Dict[str, Any]:
    """Check whether lockdown mode is currently active."""
    try:
        from policy_scout.response.lockdown import is_lockdown_active, get_lockdown_reason

        if is_lockdown_active():
            reason = get_lockdown_reason() or "No reason recorded"
            return {
                "status": "warning",
                "message": f"LOCKDOWN ACTIVE — {reason}",
            }
        return {"status": "ok", "message": "Lockdown inactive"}
    except Exception as e:
        return {"status": "error", "message": f"Lockdown check failed: {e}"}


def check_registry_integrity() -> Dict[str, Any]:
    """Check SHA-256 integrity of bundled registry files against manifest."""
    try:
        from policy_scout.integrity.registry_manifest import verify_registry_integrity

        result = verify_registry_integrity()

        if result.passed:
            return {
                "status": "ok",
                "message": f"All {result.files_checked} registry files verified",
                "files_checked": result.files_checked,
            }
        else:
            detail = "; ".join(result.errors[:3])
            return {
                "status": "error" if result.files_checked > 0 else "warning",
                "message": f"{result.reason} {detail}",
                "errors": result.errors,
            }
    except Exception as e:
        return {"status": "error", "message": f"Integrity check failed: {e}"}


def check_audit_chain_head() -> Dict[str, Any]:
    """Check that the JSONL audit chain head is accessible and consistent."""
    import json as _json

    try:
        audit_jsonl_path_str = os.environ.get(
            "POLICY_SCOUT_AUDIT_PATH",
            str(Path.home() / ".local" / "share" / "policy-scout" / "audit.jsonl"),
        )
        jsonl_path = Path(audit_jsonl_path_str)
        head_path = Path(str(jsonl_path) + ".chain_head")

        if not jsonl_path.exists():
            return {
                "status": "warning",
                "message": "JSONL audit file not found — no chain state yet",
            }

        if not head_path.exists():
            return {
                "status": "warning",
                "message": "Chain head file absent — file may predate chain integrity feature",
            }

        head = _json.loads(head_path.read_text())
        seq = head.get("seq", 0)
        mac = head.get("mac", "")

        if not mac or len(mac) != 64:
            return {
                "status": "error",
                "message": f"Chain head corrupted — unexpected mac length ({len(mac)})",
            }

        return {
            "status": "ok",
            "message": f"Audit chain head at seq={seq}",
            "seq": seq,
        }
    except Exception as e:
        return {"status": "error", "message": f"Audit chain head check failed: {e}"}


def check_report_directory() -> Dict[str, Any]:
    """Check report directory availability (read-only check)."""
    try:
        # Default path from reports
        report_root = Path.home() / ".local" / "share" / "policy-scout" / "reports"

        # Support environment variable override
        env_path = os.environ.get("POLICY_SCOUT_REPORT_ROOT")
        if env_path:
            report_root = Path(env_path)

        # Check if directory exists (read-only check)
        if not report_root.exists():
            return {
                "status": "warning",
                "message": f"Report directory does not exist: {report_root}",
                "path": str(report_root),
            }

        # Check if directory is writable
        if not os.access(report_root, os.W_OK):
            return {
                "status": "error",
                "message": f"Report directory is not writable: {report_root}",
                "path": str(report_root),
            }

        return {
            "status": "ok",
            "message": f"Report directory available at {report_root}",
            "path": str(report_root),
        }
    except Exception as e:
        return {"status": "error", "message": f"Report directory check failed: {e}"}


def check_intel_adapters() -> Dict[str, Any]:
    """Check threat intel adapter availability and data file freshness."""
    try:
        from pathlib import Path as _Path
        import yaml as _yaml

        data_dir = _Path(__file__).parent / "data"
        issues = []
        warnings = []

        for fname in ("top_npm_packages.yaml", "top_pypi_packages.yaml", "known_bad_registry.yaml"):
            p = data_dir / fname
            if not p.exists():
                issues.append(f"{fname} missing")
                continue
            raw = _yaml.safe_load(p.read_text()) or {}
            generated_at = raw.get("generated_at", "")
            if generated_at:
                try:
                    from datetime import date
                    gen = date.fromisoformat(str(generated_at))
                    age_days = (date.today() - gen).days
                    if age_days > 90:
                        warnings.append(f"{fname} is {age_days} days old (> 90 day freshness threshold)")
                except (ValueError, TypeError):
                    pass

        if issues:
            return {"status": "error", "message": f"Missing intel data files: {', '.join(issues)}"}
        if warnings:
            return {"status": "warning", "message": "; ".join(warnings)}
        return {"status": "ok", "message": "Local intel adapters ready"}
    except Exception as e:
        return {"status": "error", "message": f"Intel adapter check failed: {e}"}


def check_watch_daemon() -> Dict[str, Any]:
    """Check watch daemon status and platform support."""
    try:
        from policy_scout.watch.daemon import daemon_status
        from policy_scout.watch.fs_watcher import platform_watch_supported

        supported, reason = platform_watch_supported()
        if not supported:
            return {"status": "warning", "message": f"Watch mode not supported: {reason}"}

        status = daemon_status()
        if status.get("running"):
            return {
                "status": "ok",
                "message": f"Watch daemon running (PID {status.get('pid')})",
                "pid": status.get("pid"),
            }
        elif status.get("stale"):
            return {
                "status": "warning",
                "message": f"Stale PID file (PID {status.get('pid')} not alive)",
            }
        return {"status": "ok", "message": "Watch daemon not running (idle)"}
    except Exception as e:
        return {"status": "error", "message": f"Watch daemon check failed: {e}"}


def check_general_sandbox() -> Dict[str, Any]:
    """Check general sandbox prerequisites (unshare, user namespaces, strace, overlayfs)."""
    try:
        from policy_scout.sandbox.general.prereqs import check_sandbox_prerequisites
        prereqs = check_sandbox_prerequisites()
        if prereqs.available:
            extras = []
            if not prereqs.strace_available:
                extras.append("strace not found (syscall tracing disabled)")
            if not prereqs.overlayfs_available:
                extras.append("overlayfs unavailable (fallback: no fs diff)")
            msg = "General sandbox available"
            if extras:
                msg += "; " + "; ".join(extras)
            return {"status": "ok", "message": msg, "details": prereqs.to_dict()}
        missing = prereqs.missing()
        return {
            "status": "warning",
            "message": f"General sandbox not available: {'; '.join(missing)}",
            "details": prereqs.to_dict(),
        }
    except Exception as e:
        return {"status": "error", "message": f"General sandbox check failed: {e}"}


def check_mcp_registration() -> Dict[str, Any]:
    """Check whether the Policy Scout PreToolUse hook is registered in Claude Code settings."""
    try:
        import json as _json

        checked: list[str] = []
        installed_in: list[str] = []

        for settings_path in [
            Path(".claude/settings.json"),
            Path.home() / ".claude" / "settings.json",
        ]:
            if not settings_path.exists():
                continue
            checked.append(str(settings_path))
            try:
                data = _json.loads(settings_path.read_text())
                pre_tool = data.get("hooks", {}).get("PreToolUse", [])
                has_hook = any(
                    any(h.get("command", "").startswith("policy-scout check --hook-mode")
                        for h in entry.get("hooks", []))
                    for entry in pre_tool
                )
                if has_hook:
                    installed_in.append(str(settings_path))
            except Exception:
                pass

        if installed_in:
            return {
                "status": "ok",
                "message": f"PreToolUse hook registered in: {', '.join(installed_in)}",
                "installed_in": installed_in,
            }
        if checked:
            return {
                "status": "warning",
                "message": "PreToolUse hook not found. Run: policy-scout serve install",
                "checked": checked,
            }
        return {
            "status": "warning",
            "message": "No Claude Code settings found. Run: policy-scout serve install",
        }
    except Exception as e:
        return {"status": "error", "message": f"MCP registration check failed: {e}"}


def check_package_manager(name: str) -> Dict[str, Any]:
    """Check if a package manager is available."""
    exe_path = shutil.which(name)
    if exe_path:
        return {
            "status": "ok",
            "message": f"{name} available at {exe_path}",
            "path": exe_path,
        }
    return {"status": "warning", "message": f"{name} not found in PATH"}


def get_registry_paths() -> Dict[str, str]:
    """Get default registry file paths."""
    # Fallback paths since core.paths doesn't exist
    # __file__ is policy_scout/doctor.py, so parent.parent is the repo root
    # data files are in policy_scout/data/
    package_dir = Path(__file__).parent
    data_dir = package_dir / "data"
    return {
        "command_registry": str(data_dir / "command_registry.yaml"),
        "default_policy": str(data_dir / "default_policy.yaml"),
        "eval_cases": str(data_dir / "eval_cases.yaml"),
    }


def run_doctor_checks() -> Dict[str, Any]:
    """Run all doctor health checks."""
    results = {
        "policy_scout_version": get_policy_scout_version(),
        "python_version": get_python_version(),
        "platform": get_platform_info(),
        "checks": {},
    }

    # CLI import health
    results["checks"]["cli_import"] = check_cli_import_health()

    # Python version
    results["checks"]["python_version"] = check_python_version()

    # Get registry paths
    paths = get_registry_paths()

    # Check registries
    results["checks"]["command_registry"] = check_registry_file(
        "command_registry", paths["command_registry"]
    )
    results["checks"]["default_policy"] = check_registry_file(
        "default_policy", paths["default_policy"]
    )
    results["checks"]["eval_cases"] = check_eval_cases(paths["eval_cases"])

    # Check lockdown status
    results["checks"]["lockdown_status"] = check_lockdown_status()

    # Check registry integrity
    results["checks"]["registry_integrity"] = check_registry_integrity()

    # Check data directories
    results["checks"]["audit_store"] = check_audit_store()
    results["checks"]["audit_chain_head"] = check_audit_chain_head()
    results["checks"]["report_directory"] = check_report_directory()

    # Check intel adapters
    results["checks"]["intel_adapters"] = check_intel_adapters()

    # Check watch daemon
    results["checks"]["watch_daemon"] = check_watch_daemon()

    # Check MCP server registration
    results["checks"]["mcp_registration"] = check_mcp_registration()

    # Check general sandbox prerequisites
    results["checks"]["general_sandbox"] = check_general_sandbox()

    # Check optional package managers
    results["checks"]["npm"] = check_package_manager("npm")
    results["checks"]["pnpm"] = check_package_manager("pnpm")
    results["checks"]["yarn"] = check_package_manager("yarn")
    results["checks"]["bun"] = check_package_manager("bun")

    return results


def format_doctor_output(results: Dict[str, Any], json_mode: bool = False) -> str:
    """Format doctor output for human or JSON."""
    if json_mode:
        return json.dumps(results, indent=2)

    lines = []
    lines.append("Policy Scout Doctor")
    lines.append("=" * 50)
    lines.append("")

    lines.append(f"Version: {results['policy_scout_version']}")
    lines.append(f"Python: {results['python_version']}")
    lines.append(
        f"Platform: {results['platform']['system']} {results['platform']['release']}"
    )
    lines.append("")

    lines.append("Health Checks:")
    lines.append("-" * 50)

    for check_name, check_result in results["checks"].items():
        status = check_result.get("status", "unknown")
        message = check_result.get("message", "No message")

        if status == "ok":
            lines.append(f"✓ {check_name}: {message}")
        elif status == "warning":
            lines.append(f"⚠ {check_name}: {message}")
        elif status == "error":
            lines.append(f"✗ {check_name}: {message}")
        else:
            lines.append(f"? {check_name}: {message}")

        # Add extra info if available
        if "entry_count" in check_result:
            lines.append(f"  Entries: {check_result['entry_count']}")
        if "path" in check_result:
            lines.append(f"  Path: {check_result['path']}")

    lines.append("")

    # Overall status
    has_errors = any(c.get("status") == "error" for c in results["checks"].values())
    if has_errors:
        lines.append("Overall Status: ERROR - Some checks failed")
    else:
        lines.append("Overall Status: OK - All checks passed")

    return "\n".join(lines)
