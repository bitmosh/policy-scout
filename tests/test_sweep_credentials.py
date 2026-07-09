# SPDX-License-Identifier: Apache-2.0
"""Tests for credential reference checks."""

import os
import tempfile
from policy_scout.sweep.credentials import check_credential_references


def test_check_credential_references_detects_env():
    """Test detection of .env reference."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create file with .env reference
        js_path = os.path.join(tmpdir, "config.js")
        with open(js_path, "w") as f:
            f.write("require('dotenv').config();")
        
        findings = check_credential_references(tmpdir, "sweep_123")
        
        assert len(findings) > 0
        assert any(f.category == "credential_file_access" for f in findings)


def test_check_credential_references_detects_api_key():
    """Test detection of API_KEY reference."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create file with API_KEY reference
        py_path = os.path.join(tmpdir, "config.py")
        with open(py_path, "w") as f:
            f.write("API_KEY = os.environ.get('API_KEY')")
        
        findings = check_credential_references(tmpdir, "sweep_123")
        
        assert len(findings) > 0
        assert any(f.category == "credential_file_access" for f in findings)


def test_check_credential_references_harmless():
    """Test that harmless code doesn't create findings."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create harmless file
        js_path = os.path.join(tmpdir, "app.js")
        with open(js_path, "w") as f:
            f.write("function hello() { return 'world'; }")
        
        findings = check_credential_references(tmpdir, "sweep_123")
        
        # Should not have findings for harmless code
        assert len(findings) == 0


def test_check_credential_references_skips_node_modules():
    """Test that node_modules directory is skipped."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create node_modules directory with credential reference
        node_modules = os.path.join(tmpdir, "node_modules")
        os.makedirs(node_modules)
        
        js_path = os.path.join(node_modules, "config.js")
        with open(js_path, "w") as f:
            f.write("API_KEY = 'test'")
        
        findings = check_credential_references(tmpdir, "sweep_123")
        
        # Should skip node_modules
        assert len(findings) == 0
