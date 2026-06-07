"""Package manager detection and configuration."""

import re
from typing import Optional, Tuple, List


def detect_package_manager(command: str) -> Optional[str]:
    """Detect package manager from command string.

    Args:
        command: Command string to analyze.

    Returns:
        Package manager name (npm, pnpm, yarn, bun) or None.
    """
    command_lower = command.lower()

    # npm patterns
    if re.match(r"^\s*npm\s+(install|i)(\s+.*)?$", command_lower):
        return "npm"

    # pnpm patterns
    if re.match(r"^\s*pnpm\s+(add|install)(\s+.*)?$", command_lower):
        return "pnpm"

    # yarn patterns
    if re.match(r"^\s*yarn\s+(add|install)(\s+.*)?$", command_lower):
        return "yarn"

    # bun patterns
    if re.match(r"^\s*bun\s+(add|install)(\s+.*)?$", command_lower):
        return "bun"

    return None


def get_package_files(package_manager: str) -> List[str]:
    """Get package files to copy for a given package manager.

    Args:
        package_manager: Package manager name.

    Returns:
        List of filenames to copy.
    """
    common_files = ["package.json"]

    if package_manager == "npm":
        return common_files + ["package-lock.json", "npm-shrinkwrap.json", ".npmrc"]
    elif package_manager == "pnpm":
        return common_files + ["pnpm-lock.yaml", "pnpm-workspace.yaml", ".pnpmrc"]
    elif package_manager == "yarn":
        return common_files + ["yarn.lock", ".yarnrc.yml"]
    elif package_manager == "bun":
        return common_files + ["bun.lockb", "bun.lock"]
    else:
        return common_files


def get_migration_allowlist(package_manager: str) -> List[str]:
    """Get migration allowlist for a given package manager.

    Args:
        package_manager: Package manager name.

    Returns:
        List of filenames allowed for migration.
    """
    common_files = ["package.json"]

    if package_manager == "npm":
        return common_files + ["package-lock.json", "npm-shrinkwrap.json"]
    elif package_manager == "pnpm":
        return common_files + ["pnpm-lock.yaml"]
    elif package_manager == "yarn":
        return common_files + ["yarn.lock"]
    elif package_manager == "bun":
        return common_files + ["bun.lockb", "bun.lock"]
    else:
        return common_files


def get_install_command(
    package_manager: str, command_args: List[str]
) -> Tuple[str, List[str]]:
    """Get the executable and arguments for a package manager.

    Args:
        package_manager: Package manager name.
        command_args: Original command arguments.

    Returns:
        Tuple of (executable, args).
    """
    if package_manager == "npm":
        return "npm", command_args
    elif package_manager == "pnpm":
        return "pnpm", command_args
    elif package_manager == "yarn":
        return "yarn", command_args
    elif package_manager == "bun":
        return "bun", command_args
    else:
        return "npm", command_args  # Fallback


def is_package_manager_available(package_manager: str) -> bool:
    """Check if a package manager executable is available.

    Args:
        package_manager: Package manager name.

    Returns:
        True if executable is available, False otherwise.
    """
    import shutil

    return shutil.which(package_manager) is not None
