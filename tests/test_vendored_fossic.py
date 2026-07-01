"""Packaging regression tests for the vendored Fossic Python binding."""

from pathlib import Path
import tomllib


ROOT = Path(__file__).resolve().parents[1]
VENDOR_ROOT = ROOT / "vendor" / "fossic"


def test_policy_scout_has_no_remote_fossic_dependency() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    dependencies = project["project"]["dependencies"]

    assert not any("fossic" in dependency.lower() for dependency in dependencies)
    assert not any("git+" in dependency.lower() for dependency in dependencies)


def test_vendored_fossic_binding_sources_are_complete() -> None:
    required = [
        VENDOR_ROOT / "Cargo.toml",
        VENDOR_ROOT / "Cargo.lock",
        VENDOR_ROOT / "src" / "lib.rs",
        VENDOR_ROOT / "crates" / "fossic-similarity-hnsw" / "Cargo.toml",
        VENDOR_ROOT / "fossic-py" / "Cargo.toml",
        VENDOR_ROOT / "fossic-py" / "pyproject.toml",
        VENDOR_ROOT / "fossic-py" / "python" / "fossic" / "__init__.py",
        VENDOR_ROOT / "VENDORING.md",
        VENDOR_ROOT / "LICENSE-MIT",
    ]

    assert all(path.is_file() for path in required)
    assert not list(VENDOR_ROOT.rglob("*.so"))
    assert not list(VENDOR_ROOT.rglob("*.pyc"))
    assert not list(VENDOR_ROOT.rglob("__pycache__"))


def test_ci_installs_fossic_from_vendor_directory() -> None:
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8"
    )

    assert "pip install ./vendor/fossic/fossic-py" in workflow
    assert "github.com/bitmosh/fossic" not in workflow
    assert "Configure git for private dependencies" not in workflow

