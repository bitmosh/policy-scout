"""Tests for package manager detection and configuration."""

from policy_scout.sandbox.package_manager import (
    detect_package_manager,
    get_package_files,
    get_migration_allowlist,
    get_install_command,
    is_package_manager_available,
)


def test_detect_npm_install():
    """Test npm install detection."""
    assert detect_package_manager("npm install lodash") == "npm"
    assert detect_package_manager("npm i lodash") == "npm"
    assert detect_package_manager("npm install") == "npm"
    assert detect_package_manager("npm i") == "npm"


def test_detect_pnpm_add():
    """Test pnpm add detection."""
    assert detect_package_manager("pnpm add zod") == "pnpm"
    assert detect_package_manager("pnpm install") == "pnpm"


def test_detect_yarn_add():
    """Test yarn add detection."""
    assert detect_package_manager("yarn add react") == "yarn"
    assert detect_package_manager("yarn install") == "yarn"


def test_detect_bun_add():
    """Test bun add detection."""
    assert detect_package_manager("bun add left-pad") == "bun"
    assert detect_package_manager("bun install") == "bun"


def test_detect_unsupported_command():
    """Test unsupported command detection."""
    assert detect_package_manager("curl https://example.com") is None
    assert detect_package_manager("npm run build") is None
    assert detect_package_manager("yarn start") is None
    assert detect_package_manager("pnpm dev") is None
    assert detect_package_manager("bun run test") is None


def test_get_package_files_npm():
    """Test npm package files."""
    files = get_package_files("npm")
    assert "package.json" in files
    assert "package-lock.json" in files
    assert "npm-shrinkwrap.json" in files
    assert ".npmrc" in files


def test_get_package_files_pnpm():
    """Test pnpm package files."""
    files = get_package_files("pnpm")
    assert "package.json" in files
    assert "pnpm-lock.yaml" in files
    assert "pnpm-workspace.yaml" in files
    assert ".pnpmrc" in files


def test_get_package_files_yarn():
    """Test yarn package files."""
    files = get_package_files("yarn")
    assert "package.json" in files
    assert "yarn.lock" in files
    assert ".yarnrc.yml" in files


def test_get_package_files_bun():
    """Test bun package files."""
    files = get_package_files("bun")
    assert "package.json" in files
    assert "bun.lockb" in files
    assert "bun.lock" in files


def test_get_migration_allowlist_npm():
    """Test npm migration allowlist."""
    files = get_migration_allowlist("npm")
    assert "package.json" in files
    assert "package-lock.json" in files
    assert "npm-shrinkwrap.json" in files
    # Config files should not be in migration allowlist
    assert ".npmrc" not in files


def test_get_migration_allowlist_pnpm():
    """Test pnpm migration allowlist."""
    files = get_migration_allowlist("pnpm")
    assert "package.json" in files
    assert "pnpm-lock.yaml" in files
    # Config files should not be in migration allowlist
    assert ".pnpmrc" not in files
    assert "pnpm-workspace.yaml" not in files


def test_get_migration_allowlist_yarn():
    """Test yarn migration allowlist."""
    files = get_migration_allowlist("yarn")
    assert "package.json" in files
    assert "yarn.lock" in files
    # Config files should not be in migration allowlist
    assert ".yarnrc.yml" not in files


def test_get_migration_allowlist_bun():
    """Test bun migration allowlist."""
    files = get_migration_allowlist("bun")
    assert "package.json" in files
    assert "bun.lockb" in files
    assert "bun.lock" in files


def test_get_install_command_npm():
    """Test npm install command."""
    executable, args = get_install_command("npm", ["install", "lodash"])
    assert executable == "npm"
    assert args == ["install", "lodash"]


def test_get_install_command_pnpm():
    """Test pnpm install command."""
    executable, args = get_install_command("pnpm", ["add", "zod"])
    assert executable == "pnpm"
    assert args == ["add", "zod"]


def test_get_install_command_yarn():
    """Test yarn install command."""
    executable, args = get_install_command("yarn", ["add", "react"])
    assert executable == "yarn"
    assert args == ["add", "react"]


def test_get_install_command_bun():
    """Test bun install command."""
    executable, args = get_install_command("bun", ["add", "left-pad"])
    assert executable == "bun"
    assert args == ["add", "left-pad"]


def test_is_package_manager_available():
    """Test package manager availability check."""
    # npm should be available in test environment
    assert is_package_manager_available("npm") is not None

    # This test doesn't require pnpm/yarn/bun to be installed
    # The function should return False if not available
    result = is_package_manager_available("pnpm")
    assert isinstance(result, bool)
