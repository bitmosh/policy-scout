# SPDX-License-Identifier: Apache-2.0
"""Lifecycle script inspection for sandbox."""

import json
from pathlib import Path
from typing import List
from .models import LifecycleScript


# Lifecycle script names to inspect
LIFECYCLE_SCRIPTS = [
    "preinstall",
    "install",
    "postinstall",
    "prepack",
    "prepare",
    "prepublish",
    "prepublishOnly",
]


def inspect_lifecycle_scripts(sandbox_workspace: Path) -> List[LifecycleScript]:
    """Inspect lifecycle scripts in package manifests.
    
    Args:
        sandbox_workspace: Path to the sandbox workspace.
        
    Returns:
        List of LifecycleScript objects found.
    """
    scripts_found = []
    
    # Inspect root package.json
    package_json_path = sandbox_workspace / "package.json"
    if package_json_path.exists():
        scripts_found.extend(
            _inspect_package_json(package_json_path, "root")
        )
    
    # Inspect installed package package.json files
    node_modules_path = sandbox_workspace / "node_modules"
    if node_modules_path.exists():
        for package_dir in node_modules_path.iterdir():
            if package_dir.is_dir():
                package_json = package_dir / "package.json"
                if package_json.exists():
                    scripts_found.extend(
                        _inspect_package_json(package_json, package_dir.name)
                    )
    
    return scripts_found


def _inspect_package_json(package_json_path: Path, package_name: str) -> List[LifecycleScript]:
    """Inspect a single package.json for lifecycle scripts.
    
    Args:
        package_json_path: Path to the package.json file.
        package_name: Name of the package.
        
    Returns:
        List of LifecycleScript objects found.
    """
    scripts_found = []
    
    try:
        content = package_json_path.read_text()
        package_data = json.loads(content)
        
        scripts = package_data.get("scripts", {})
        
        for script_name in LIFECYCLE_SCRIPTS:
            if script_name in scripts:
                script_content = scripts[script_name]
                scripts_found.append(
                    LifecycleScript(
                        package_name=package_name,
                        script_name=script_name,
                        script_content=script_content,
                        location=str(package_json_path)
                    )
                )
    except Exception:
        # If we can't parse the package.json, skip it
        pass
    
    return scripts_found
