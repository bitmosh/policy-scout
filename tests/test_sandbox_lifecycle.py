"""Tests for sandbox lifecycle script inspection."""

import json
import tempfile
from pathlib import Path
from policy_scout.sandbox.lifecycle_inspector import inspect_lifecycle_scripts, LIFECYCLE_SCRIPTS


def test_inspect_lifecycle_scripts_root_package():
    """Test inspecting lifecycle scripts in root package.json."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        
        # Create package.json with lifecycle scripts
        package_json = workspace / "package.json"
        package_json.write_text(json.dumps({
            "name": "test",
            "version": "1.0.0",
            "scripts": {
                "preinstall": "echo 'preinstall'",
                "postinstall": "echo 'postinstall'",
                "test": "echo 'test'"
            }
        }))
        
        scripts = inspect_lifecycle_scripts(workspace)
        
        assert len(scripts) == 2  # preinstall and postinstall
        script_names = [s.script_name for s in scripts]
        assert "preinstall" in script_names
        assert "postinstall" in script_names
        assert "test" not in script_names  # Not a lifecycle script


def test_inspect_lifecycle_scripts_node_modules():
    """Test inspecting lifecycle scripts in node_modules packages."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        node_modules = workspace / "node_modules"
        node_modules.mkdir()
        
        # Create a package in node_modules
        pkg_dir = node_modules / "example-package"
        pkg_dir.mkdir()
        package_json = pkg_dir / "package.json"
        package_json.write_text(json.dumps({
            "name": "example-package",
            "version": "1.0.0",
            "scripts": {
                "install": "node install.js"
            }
        }))
        
        scripts = inspect_lifecycle_scripts(workspace)
        
        assert len(scripts) == 1
        assert scripts[0].package_name == "example-package"
        assert scripts[0].script_name == "install"


def test_inspect_lifecycle_scripts_no_scripts():
    """Test when no lifecycle scripts are present."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        
        # Create package.json without lifecycle scripts
        package_json = workspace / "package.json"
        package_json.write_text(json.dumps({
            "name": "test",
            "version": "1.0.0",
            "scripts": {
                "test": "echo 'test'",
                "build": "echo 'build'"
            }
        }))
        
        scripts = inspect_lifecycle_scripts(workspace)
        
        assert len(scripts) == 0


def test_inspect_lifecycle_scripts_no_package_json():
    """Test when package.json doesn't exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        
        scripts = inspect_lifecycle_scripts(workspace)
        
        assert len(scripts) == 0


def test_inspect_lifecycle_scripts_invalid_json():
    """Test handling of invalid package.json."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        
        # Create invalid package.json
        package_json = workspace / "package.json"
        package_json.write_text("invalid json {")
        
        scripts = inspect_lifecycle_scripts(workspace)
        
        # Should not crash, just skip
        assert len(scripts) == 0


def test_lifecycle_script_structure():
    """Test lifecycle script object structure."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        
        package_json = workspace / "package.json"
        package_json.write_text(json.dumps({
            "name": "test",
            "scripts": {
                "postinstall": "node setup.js"
            }
        }))
        
        scripts = inspect_lifecycle_scripts(workspace)
        
        assert len(scripts) == 1
        script = scripts[0]
        assert script.package_name == "root"
        assert script.script_name == "postinstall"
        assert script.script_content == "node setup.js"
        assert str(workspace / "package.json") in script.location


def test_lifecycle_script_names_constant():
    """Test that LIFECYCLE_SCRIPTS contains expected script names."""
    expected_scripts = [
        "preinstall",
        "install",
        "postinstall",
        "prepack",
        "prepare",
        "prepublish",
        "prepublishOnly",
    ]
    
    for script in expected_scripts:
        assert script in LIFECYCLE_SCRIPTS
