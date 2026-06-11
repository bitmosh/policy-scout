"""Supply chain attack detection — multi-layer analysis."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from ..sandbox.models import LifecycleScript
from .js_analyzer import JSAnalyzer, ScriptFinding
from .py_analyzer import analyze_python_script, PyFinding


def _is_python_script(script_content: str, script_name: str) -> bool:
    return (
        script_name.endswith(".py")
        or script_content.startswith("#!")
        and ("python" in script_content.splitlines()[0])
    )


def analyze_lifecycle_scripts(
    scripts: List[LifecycleScript],
    project_root: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """Run supply chain analysis on a list of LifecycleScript objects.

    Returns a list of finding dicts compatible with SandboxResult.findings.
    """
    js_analyzer = JSAnalyzer()
    findings: List[Dict[str, Any]] = []

    for script in scripts:
        content = script.script_content
        ctx = {
            "package_name": script.package_name,
            "script_name": script.script_name,
        }

        if _is_python_script(content, script.script_name):
            raw = analyze_python_script(content, filename=script.script_name)
            for f in raw:
                d = f.to_dict()
                d["package_name"] = script.package_name
                d["script_name"] = script.script_name
                findings.append(d)
        else:
            raw = js_analyzer.analyze(content, context=ctx)
            for f in raw:
                d = f.to_dict()
                d["package_name"] = script.package_name
                d["script_name"] = script.script_name
                findings.append(d)

    return findings
