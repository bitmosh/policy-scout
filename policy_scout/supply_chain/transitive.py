"""Transitive dependency tree analysis using npm list --json output."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


@dataclass
class TransitiveAnalysisResult:
    package_count: int
    max_depth: int
    findings: List[Dict[str, Any]] = field(default_factory=list)
    error: str = ""

    def to_dict(self) -> dict:
        return {
            "package_count": self.package_count,
            "max_depth": self.max_depth,
            "findings": self.findings,
            "finding_count": len(self.findings),
        }


def run_npm_list(sandbox_workspace: Path, timeout: int = 30) -> Optional[Dict]:
    """Run `npm list --json --depth=999` and return the parsed output."""
    try:
        proc = subprocess.run(
            ["npm", "list", "--json", "--depth=999"],
            cwd=str(sandbox_workspace),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        # npm list exits non-zero when there are peer-dep issues; still parse stdout
        if proc.stdout.strip():
            return json.loads(proc.stdout)
    except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
        pass
    return None


def _make_finding(name: str, version: str, depth: int, intel_result) -> Dict[str, Any]:
    return {
        "type": "supply_chain",
        "pattern_id": "transitive_threat",
        "description": (
            f"Threat intel hit on transitive dependency: {name}@{version}"
            f" (depth {depth})"
        ),
        "severity": intel_result.top_severity(),
        "confidence": intel_result.confidence,
        "matched_text": f"{name}@{version}",
        "line_number": 0,
        "source": "transitive_analysis",
        "depth": depth,
        "intel": intel_result.to_dict(),
    }


def _walk_tree(
    deps: Dict[str, Any],
    intel_adapter,
    ecosystem: str,
    depth: int,
    seen: Set[str],
    findings: List[Dict],
    max_depth_ref: List[int],
) -> None:
    if depth > max_depth_ref[0]:
        max_depth_ref[0] = depth

    for name, meta in deps.items():
        version = meta.get("version", "unknown") if isinstance(meta, dict) else "unknown"
        key = f"{name}@{version}"
        if key in seen:
            continue
        seen.add(key)

        if intel_adapter is not None:
            try:
                result = intel_adapter.enrich_package(ecosystem, name, version)
                if result.has_findings:
                    findings.append(_make_finding(name, version, depth, result))
            except Exception:
                pass

        sub_deps = meta.get("dependencies", {}) if isinstance(meta, dict) else {}
        if sub_deps:
            _walk_tree(sub_deps, intel_adapter, ecosystem, depth + 1, seen, findings, max_depth_ref)


def analyze_tree(
    npm_list_json: Dict[str, Any],
    ecosystem: str = "npm",
    intel_adapter=None,
) -> TransitiveAnalysisResult:
    """Walk an npm list --json tree and check each package against intel."""
    deps = npm_list_json.get("dependencies", {})
    findings: List[Dict] = []
    seen: Set[str] = set()
    max_depth_ref = [0]

    _walk_tree(deps, intel_adapter, ecosystem, depth=1, seen=seen,
               findings=findings, max_depth_ref=max_depth_ref)

    return TransitiveAnalysisResult(
        package_count=len(seen),
        max_depth=max_depth_ref[0],
        findings=findings,
    )
