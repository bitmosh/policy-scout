# SPDX-License-Identifier: Apache-2.0
"""Tests for JavaScript pattern checks."""

import os
import tempfile
from policy_scout.sweep.javascript_patterns import check_javascript_patterns


def test_check_javascript_patterns_detects_eval():
    """Test detection of eval in JavaScript files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create JS file with eval
        js_path = os.path.join(tmpdir, "script.js")
        with open(js_path, "w") as f:
            f.write("const code = 'console.log(\"hello\")';\neval(code);")
        
        findings = check_javascript_patterns(tmpdir, "sweep_123")
        
        assert len(findings) > 0
        assert any(f.category == "obfuscated_payload" for f in findings)


def test_check_javascript_patterns_detects_child_process():
    """Test detection of child_process in JavaScript files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create JS file with child_process
        js_path = os.path.join(tmpdir, "script.js")
        with open(js_path, "w") as f:
            f.write("const { exec } = require('child_process');\nexec('ls');")
        
        findings = check_javascript_patterns(tmpdir, "sweep_123")
        
        assert len(findings) > 0
        assert any(f.category == "obfuscated_payload" for f in findings)


def test_check_javascript_patterns_harmless_code():
    """Test that harmless JavaScript doesn't create high-severity findings."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create harmless JS file
        js_path = os.path.join(tmpdir, "script.js")
        with open(js_path, "w") as f:
            f.write("function add(a, b) { return a + b; }\nconsole.log(add(1, 2));")
        
        findings = check_javascript_patterns(tmpdir, "sweep_123")
        
        # Should not have high-severity findings for harmless code
        high_severity = [f for f in findings if f.severity == "high"]
        assert len(high_severity) == 0


def test_check_javascript_patterns_skips_node_modules():
    """Test that node_modules directory is skipped."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create node_modules directory with suspicious JS
        node_modules = os.path.join(tmpdir, "node_modules")
        os.makedirs(node_modules)
        
        js_path = os.path.join(node_modules, "script.js")
        with open(js_path, "w") as f:
            f.write("eval('code');")
        
        findings = check_javascript_patterns(tmpdir, "sweep_123")
        
        # Should skip node_modules
        assert len(findings) == 0
