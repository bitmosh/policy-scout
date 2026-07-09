# SPDX-License-Identifier: Apache-2.0
"""MCP tool handlers — delegate to existing CLI logic."""

from __future__ import annotations

import io
from contextlib import redirect_stdout, redirect_stderr
from typing import Any, Optional


def _capture(fn, *args, **kwargs) -> tuple[Any, str, str]:
    """Run fn(*args, **kwargs) capturing stdout/stderr, return (result, stdout, stderr)."""
    out_buf = io.StringIO()
    err_buf = io.StringIO()
    result = None
    with redirect_stdout(out_buf), redirect_stderr(err_buf):
        try:
            result = fn(*args, **kwargs)
        except SystemExit:
            pass
    return result, out_buf.getvalue(), err_buf.getvalue()


def handle_check(params: dict) -> dict:
    """Handle policy_scout_check tool call."""
    from ..cli.main import check_command

    command = params.get("command", "")
    if not command:
        return {"error": "command parameter is required", "is_error": True}

    with_intel: bool = bool(params.get("with_intel", False))

    result, _stdout, stderr = _capture(
        check_command,
        command=command,
        json_output=False,
        audit_enabled=True,
        approval_enabled=False,
        report_enabled=False,
        with_intel=with_intel,
    )

    if result is None:
        return {
            "error": stderr.strip() or "check_command returned no result",
            "is_error": True,
        }

    return {
        "request_id": result.get("request_id", ""),
        "command": result.get("command", command),
        "decision": result.get("decision", "UNKNOWN"),
        "risk_score": result.get("risk_score", 0),
        "risk_band": result.get("risk_band", "unknown"),
        "category": result.get("category", ""),
        "capabilities": result.get("capabilities", []),
        "reasons": result.get("reasons", []),
        "recommended_next_action": result.get("recommended_next_action", ""),
        "confidence": result.get("confidence", ""),
        "policy_hits": result.get("policy_hits", []),
    }


def handle_sandbox(params: dict) -> dict:
    """Handle policy_scout_sandbox tool call."""
    from ..cli.main import handle_sandbox_command

    command = params.get("command", "")
    if not command:
        return {"error": "command parameter is required", "is_error": True}

    result, stdout, stderr = _capture(
        handle_sandbox_command,
        command=command,
        json_output=False,
        audit_enabled=True,
    )

    if result is None:
        return {
            "error": stderr.strip() or "sandbox returned no result",
            "stdout": stdout,
            "is_error": True,
        }

    return {
        "status": result.get("status", "unknown"),
        "command": result.get("command", command),
        "output": result.get("output", stdout),
        "exit_code": result.get("exit_code"),
        "packages_installed": result.get("packages_installed", []),
        "duration_ms": result.get("duration_ms"),
    }


def handle_sweep(params: dict) -> dict:
    """Handle policy_scout_sweep tool call."""
    import time
    from ..sweep.engine import run_project_sweep
    from ..sweep.quick_engine import run_quick_system_sweep
    from ..core.ids import generate_id

    mode = params.get("mode", "quick")
    project_root: Optional[str] = params.get("project_root")

    sweep_id = generate_id("sweep")
    start = time.time()

    try:
        if mode == "project":
            import os
            root = project_root or os.getcwd()
            sweep_result = run_project_sweep(project_root=root)
        else:
            sweep_result = run_quick_system_sweep()
    except Exception as exc:
        return {"error": f"Sweep failed: {exc}", "is_error": True}

    duration_ms = int((time.time() - start) * 1000)

    if hasattr(sweep_result, "to_dict"):
        d = sweep_result.to_dict()
    elif isinstance(sweep_result, dict):
        d = sweep_result
    else:
        d = {}

    findings_raw = d.get("findings", [])
    findings = []
    for f in findings_raw:
        if hasattr(f, "to_dict"):
            findings.append(f.to_dict())
        elif isinstance(f, dict):
            findings.append(f)
        else:
            findings.append({"description": str(f)})

    return {
        "sweep_id": d.get("sweep_id", sweep_id),
        "sweep_type": d.get("sweep_type", mode),
        "project_root": d.get("project_root", project_root or ""),
        "findings": findings,
        "findings_count": d.get("findings_count", {}),
        "duration_ms": d.get("duration_ms", duration_ms),
        "could_not_verify": d.get("could_not_verify", []),
    }


def handle_get_report(params: dict) -> dict:
    """Handle policy_scout_get_report tool call."""
    from pathlib import Path
    import json as _json
    from ..reports.writer import get_report_root

    report_root = get_report_root()
    report_id: Optional[str] = params.get("report_id")

    if not report_root.exists():
        return {"reports": [], "message": "No Scout Reports have been generated yet."}

    if report_id:
        # Fetch a specific report
        report_dir = report_root / report_id
        if not report_dir.is_dir():
            return {"error": f"Report '{report_id}' not found", "is_error": True}

        json_path = report_dir / "report.json"
        md_path = report_dir / "report.md"

        if json_path.exists():
            try:
                data = _json.loads(json_path.read_text())
                return {"report_id": report_id, "data": data}
            except Exception as exc:
                return {"error": f"Failed to read report JSON: {exc}", "is_error": True}
        elif md_path.exists():
            return {"report_id": report_id, "markdown": md_path.read_text()}
        else:
            return {"error": f"Report '{report_id}' has no readable files", "is_error": True}
    else:
        # List all reports
        reports = []
        for report_dir in sorted(report_root.iterdir(), reverse=True):
            if not report_dir.is_dir():
                continue
            rid = report_dir.name
            if not rid.startswith("report_"):
                continue
            json_path = report_dir / "report.json"
            md_path = report_dir / "report.md"
            if not (json_path.exists() or md_path.exists()):
                continue
            entry: dict = {"report_id": rid}
            if json_path.exists():
                try:
                    meta = _json.loads(json_path.read_text())
                    entry["type"] = meta.get("report_type", "")
                    entry["created_at"] = meta.get("created_at", "")
                    entry["summary"] = meta.get("summary", "")
                except Exception:
                    pass
            reports.append(entry)
        return {"reports": reports}


def handle_scan_content(params: dict) -> dict:
    """Handle policy_scout_scan_content tool call."""
    from ..sweep.prompt_injection import PromptInjectionAnalyzer

    content = params.get("content", "")
    if not content:
        return {"findings": [], "finding_count": 0}

    source: str = params.get("source", "<tool-response>")

    analyzer = PromptInjectionAnalyzer()
    raw_findings = analyzer.analyze_text(content, source=source)

    findings = [
        {
            "pattern_id": f.pattern_id,
            "description": f.description,
            "severity": f.severity,
            "confidence": f.confidence,
            "line_number": f.line_number,
            "matched_text": f.matched_text,
            "context": f.context,
        }
        for f in raw_findings
    ]

    return {
        "source": source,
        "finding_count": len(findings),
        "findings": findings,
        "safe_to_act_on": len(findings) == 0,
    }
