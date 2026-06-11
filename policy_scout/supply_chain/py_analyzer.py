"""Python AST-based analysis for setup.py and build hook scripts."""

from __future__ import annotations

import ast
import re
import yaml
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional


_PATTERNS_PATH = Path(__file__).parent / "patterns" / "py_patterns.yaml"

_DANGEROUS_IMPORTS = frozenset({
    "subprocess", "os", "socket", "urllib", "urllib2",
    "requests", "httpx", "paramiko", "ftplib", "smtplib",
    "telnetlib", "poplib", "imaplib", "nntplib",
})

_SHELL_CALLS = frozenset({
    ("subprocess", "run"), ("subprocess", "call"), ("subprocess", "check_output"),
    ("subprocess", "check_call"), ("subprocess", "Popen"),
    ("os", "system"), ("os", "popen"),
    ("commands", "getoutput"), ("commands", "getstatusoutput"),
})

_NETWORK_CALLS = frozenset({
    ("urllib", "request"), ("urllib2", "urlopen"),
    ("requests", "get"), ("requests", "post"), ("requests", "put"),
    ("requests", "delete"), ("requests", "head"), ("requests", "patch"),
    ("httpx", "get"), ("httpx", "post"), ("httpx", "Client"),
})

_DYNAMIC_EXEC_BUILTINS = frozenset({"exec", "eval", "compile"})

_SENSITIVE_PATH_RE = re.compile(
    r'\.(?:bash(?:rc|_profile)|zshrc|profile|ssh|npmrc|aws|gnupg)',
    re.IGNORECASE,
)


@dataclass
class PyFinding:
    node_type: str
    description: str
    severity: str
    confidence: str
    line_number: int
    source: str = "py_analyzer"

    def to_dict(self) -> dict:
        return {
            "type": "supply_chain",
            "pattern_id": self.node_type,
            "description": self.description,
            "severity": self.severity,
            "confidence": self.confidence,
            "matched_text": "",
            "line_number": self.line_number,
            "source": self.source,
        }


class _SetupAnalyzer(ast.NodeVisitor):
    def __init__(self) -> None:
        self.findings: List[PyFinding] = []
        self._imported: Dict[str, str] = {}  # local_name -> module

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            top = alias.name.split(".")[0]
            local = alias.asname or alias.name.split(".")[0]
            self._imported[local] = top
            if top in _DANGEROUS_IMPORTS:
                self.findings.append(PyFinding(
                    node_type="py_dangerous_import",
                    description=f"Dangerous module imported: {alias.name}",
                    severity="medium",
                    confidence="medium",
                    line_number=node.lineno,
                ))
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module:
            top = node.module.split(".")[0]
            if top in _DANGEROUS_IMPORTS:
                for alias in node.names:
                    local = alias.asname or alias.name
                    self._imported[local] = top
                self.findings.append(PyFinding(
                    node_type="py_dangerous_import",
                    description=f"Dangerous module imported: {node.module}",
                    severity="medium",
                    confidence="medium",
                    line_number=node.lineno,
                ))
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        func_str = _ast_func_str(node.func)

        # Bare builtins: eval(), exec(), compile()
        if func_str in _DYNAMIC_EXEC_BUILTINS:
            self.findings.append(PyFinding(
                node_type="py_dynamic_exec",
                description=f"Dynamic code execution: {func_str}()",
                severity="high",
                confidence="high",
                line_number=node.lineno,
            ))

        # Module-qualified calls
        for (mod, fn) in _SHELL_CALLS:
            if func_str in (f"{mod}.{fn}", fn) and self._imported.get(func_str.split(".")[0]) == mod:
                self.findings.append(PyFinding(
                    node_type="py_shell_exec",
                    description=f"Shell execution: {func_str}()",
                    severity="high",
                    confidence="high",
                    line_number=node.lineno,
                ))
                break

        for (mod, fn) in _NETWORK_CALLS:
            if func_str in (f"{mod}.{fn}", fn) and self._imported.get(func_str.split(".")[0]) == mod:
                self.findings.append(PyFinding(
                    node_type="py_network_request",
                    description=f"Network request: {func_str}()",
                    severity="high",
                    confidence="high",
                    line_number=node.lineno,
                ))
                break

        # open() with write mode on sensitive path
        if func_str == "open" and node.args:
            path_arg = _ast_str_value(node.args[0])
            if path_arg and _SENSITIVE_PATH_RE.search(path_arg):
                mode = _ast_str_value(node.args[1]) if len(node.args) > 1 else ""
                if not mode or "w" in mode or "a" in mode:
                    self.findings.append(PyFinding(
                        node_type="py_file_write_sensitive",
                        description=f"Writing to sensitive path: {path_arg}",
                        severity="critical",
                        confidence="high",
                        line_number=node.lineno,
                    ))

        # os.environ access patterns
        if func_str in ("os.environ.get", "os.getenv"):
            first_arg = _ast_str_value(node.args[0]) if node.args else ""
            if first_arg and any(
                first_arg.startswith(pfx)
                for pfx in ("AWS_", "GITHUB_TOKEN", "GH_TOKEN", "NPM_TOKEN", "PYPI_TOKEN")
            ):
                self.findings.append(PyFinding(
                    node_type="py_env_access",
                    description=f"Accessing credential env var: {first_arg}",
                    severity="high",
                    confidence="medium",
                    line_number=node.lineno,
                ))

        self.generic_visit(node)


def _ast_func_str(func_node: ast.expr) -> str:
    if isinstance(func_node, ast.Name):
        return func_node.id
    if isinstance(func_node, ast.Attribute):
        prefix = _ast_func_str(func_node.value)
        return f"{prefix}.{func_node.attr}" if prefix else func_node.attr
    return ""


def _ast_str_value(node: ast.expr) -> Optional[str]:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _load_text_patterns() -> List[Dict]:
    if not _PATTERNS_PATH.exists():
        return []
    with _PATTERNS_PATH.open() as f:
        data = yaml.safe_load(f)
    return data.get("patterns", [])


def analyze_python_script(source: str, filename: str = "<script>") -> List[PyFinding]:
    """Analyze a Python script for supply chain risks.

    Uses AST as primary method; falls back to text patterns if parsing fails.
    """
    findings: List[PyFinding] = []

    try:
        tree = ast.parse(source, filename=filename)
        analyzer = _SetupAnalyzer()
        analyzer.visit(tree)
        findings.extend(analyzer.findings)
    except SyntaxError:
        # AST parse failed — fall back to text-pattern matching
        findings.extend(_text_pattern_fallback(source))

    return findings


def _text_pattern_fallback(source: str) -> List[PyFinding]:
    """Simple regex fallback for syntactically invalid Python scripts."""
    findings = []
    for entry in _load_text_patterns():
        for raw in entry.get("patterns", []):
            try:
                pat = re.compile(raw, re.IGNORECASE | re.MULTILINE)
            except re.error:
                continue
            for m in pat.finditer(source):
                line_no = source[: m.start()].count("\n") + 1
                findings.append(PyFinding(
                    node_type=entry["id"],
                    description=entry["description"],
                    severity=entry["severity"],
                    confidence="low",  # text patterns are lower confidence than AST
                    line_number=line_no,
                    source="py_analyzer_text",
                ))
    return findings
