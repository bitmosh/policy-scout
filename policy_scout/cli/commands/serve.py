"""serve command handlers."""

import json
import sys


def handle_serve_command(args) -> None:
    """Handle serve subcommands (mcp, install, status)."""
    sub = getattr(args, "serve_subcommand", None)

    if sub == "mcp":
        from ...server.mcp_server import run_server
        run_server()

    elif sub == "install":
        _handle_serve_install(
            scope=getattr(args, "scope", "project"),
            json_output=getattr(args, "json", False),
        )

    elif sub == "status":
        _handle_serve_status(json_output=getattr(args, "json", False))

    else:
        print("Error: No serve subcommand provided (mcp|install|status)", file=sys.stderr)
        sys.exit(1)


def _handle_serve_install(scope: str = "project", json_output: bool = False) -> None:
    """Install a Claude Code PreToolUse hook that calls policy-scout check --hook-mode."""
    from pathlib import Path

    hook_entry = {
        "matcher": ".*",
        "hooks": [
            {
                "type": "command",
                "command": "policy-scout check --hook-mode -- $CLAUDE_TOOL_INPUT",
            }
        ],
    }

    if scope == "project":
        settings_path = Path(".claude/settings.json")
    else:
        settings_path = Path.home() / ".claude" / "settings.json"

    settings_path.parent.mkdir(parents=True, exist_ok=True)

    existing: dict = {}
    if settings_path.exists():
        try:
            existing = json.loads(settings_path.read_text())
        except Exception:
            existing = {}

    hooks = existing.setdefault("hooks", {})
    pre_tool = hooks.setdefault("PreToolUse", [])

    # Avoid duplicates
    already_installed = any(
        any(h.get("command", "").startswith("policy-scout check --hook-mode")
            for h in entry.get("hooks", []))
        for entry in pre_tool
    )

    if not already_installed:
        pre_tool.append(hook_entry)
        settings_path.write_text(json.dumps(existing, indent=2))
        status = "installed"
    else:
        status = "already_installed"

    result = {
        "status": status,
        "scope": scope,
        "settings_path": str(settings_path),
    }

    if json_output:
        print(json.dumps(result, indent=2))
    else:
        if status == "installed":
            print(f"Policy Scout hook installed in {settings_path}")
        else:
            print(f"Policy Scout hook already present in {settings_path}")


def _handle_serve_status(json_output: bool = False) -> None:
    """Show MCP server / hook registration status."""
    from pathlib import Path

    project_settings = Path(".claude/settings.json")
    user_settings = Path.home() / ".claude" / "settings.json"

    def _check_hook(path: Path) -> bool:
        if not path.exists():
            return False
        try:
            data = json.loads(path.read_text())
            pre_tool = data.get("hooks", {}).get("PreToolUse", [])
            return any(
                any(h.get("command", "").startswith("policy-scout check --hook-mode")
                    for h in entry.get("hooks", []))
                for entry in pre_tool
            )
        except Exception:
            return False

    project_hook = _check_hook(project_settings)
    user_hook = _check_hook(user_settings)

    result = {
        "project_hook_installed": project_hook,
        "user_hook_installed": user_hook,
        "project_settings_path": str(project_settings),
        "user_settings_path": str(user_settings),
    }

    if json_output:
        print(json.dumps(result, indent=2))
    else:
        print("Policy Scout serve status:")
        print(f"  Project hook: {'installed' if project_hook else 'not installed'} ({project_settings})")
        print(f"  User hook:    {'installed' if user_hook else 'not installed'} ({user_settings})")
