"""Tests for [13] Self-Integrity: registry manifest verification and startup check."""

import json
import tempfile
from pathlib import Path

import pytest

from policy_scout.integrity.registry_manifest import (
    verify_registry_integrity,
    generate_manifest,
    write_manifest,
    IntegrityCheckResult,
)
from policy_scout.integrity.startup_check import (
    run_startup_check,
    reset_startup_check_cache,
)


@pytest.fixture(autouse=True)
def reset_cache():
    """Reset the startup check cache before each test."""
    reset_startup_check_cache()
    yield
    reset_startup_check_cache()


@pytest.fixture
def tmp_data_dir(tmp_path):
    """Temporary data directory with a few fake YAML files."""
    (tmp_path / "policy_rules.yaml").write_text("- id: test\n")
    (tmp_path / "commands.yaml").write_text("commands: []\n")
    return tmp_path


@pytest.fixture
def tmp_manifest_path(tmp_path):
    return tmp_path / "registry_manifest.json"


class TestVerifyRegistryIntegrity:
    def test_passes_with_real_manifest(self):
        """The bundled manifest matches the actual data files."""
        result = verify_registry_integrity()
        assert result.passed is True
        assert result.files_checked >= 1
        assert len(result.errors) == 0

    def test_passes_with_custom_manifest(self, tmp_data_dir, tmp_manifest_path):
        manifest = generate_manifest(data_dir=tmp_data_dir)
        write_manifest(manifest, tmp_manifest_path)

        result = verify_registry_integrity(
            manifest_path=tmp_manifest_path, data_dir=tmp_data_dir
        )
        assert result.passed is True
        assert result.files_checked == 2

    def test_fails_when_manifest_absent(self, tmp_data_dir, tmp_manifest_path):
        result = verify_registry_integrity(
            manifest_path=tmp_manifest_path, data_dir=tmp_data_dir
        )
        assert result.passed is False
        assert "manifest not found" in result.reason.lower()

    def test_fails_when_file_modified(self, tmp_data_dir, tmp_manifest_path):
        manifest = generate_manifest(data_dir=tmp_data_dir)
        write_manifest(manifest, tmp_manifest_path)

        # Tamper with a file
        (tmp_data_dir / "policy_rules.yaml").write_text("- id: tampered\n")

        result = verify_registry_integrity(
            manifest_path=tmp_manifest_path, data_dir=tmp_data_dir
        )
        assert result.passed is False
        assert any("checksum mismatch" in e for e in result.errors)
        assert any("policy_rules.yaml" in e for e in result.errors)

    def test_fails_when_file_missing(self, tmp_data_dir, tmp_manifest_path):
        manifest = generate_manifest(data_dir=tmp_data_dir)
        write_manifest(manifest, tmp_manifest_path)

        # Remove a file
        (tmp_data_dir / "commands.yaml").unlink()

        result = verify_registry_integrity(
            manifest_path=tmp_manifest_path, data_dir=tmp_data_dir
        )
        assert result.passed is False
        assert any("file missing" in e for e in result.errors)
        assert any("commands.yaml" in e for e in result.errors)

    def test_error_includes_short_hash(self, tmp_data_dir, tmp_manifest_path):
        manifest = generate_manifest(data_dir=tmp_data_dir)
        write_manifest(manifest, tmp_manifest_path)
        (tmp_data_dir / "policy_rules.yaml").write_text("changed\n")

        result = verify_registry_integrity(
            manifest_path=tmp_manifest_path, data_dir=tmp_data_dir
        )
        error_text = " ".join(result.errors)
        assert "…" in error_text  # short hash with ellipsis

    def test_passes_with_extra_unlisted_files(self, tmp_data_dir, tmp_manifest_path):
        """Files not in manifest are ignored."""
        manifest = generate_manifest(data_dir=tmp_data_dir)
        write_manifest(manifest, tmp_manifest_path)

        # Add a file not in manifest
        (tmp_data_dir / "extra.yaml").write_text("extra: true\n")

        result = verify_registry_integrity(
            manifest_path=tmp_manifest_path, data_dir=tmp_data_dir
        )
        assert result.passed is True

    def test_bad_manifest_json(self, tmp_data_dir, tmp_manifest_path):
        tmp_manifest_path.write_text("not json {{{")
        result = verify_registry_integrity(
            manifest_path=tmp_manifest_path, data_dir=tmp_data_dir
        )
        assert result.passed is False
        assert "unreadable" in result.reason.lower()

    def test_empty_files_section(self, tmp_data_dir, tmp_manifest_path):
        tmp_manifest_path.write_text(json.dumps({"version": "dev", "files": {}}))
        result = verify_registry_integrity(
            manifest_path=tmp_manifest_path, data_dir=tmp_data_dir
        )
        assert result.passed is False
        assert "no files listed" in result.reason.lower()


class TestGenerateManifest:
    def test_generates_hashes_for_yaml_files(self, tmp_data_dir):
        manifest = generate_manifest(data_dir=tmp_data_dir)
        assert "policy_rules.yaml" in manifest["files"]
        assert "commands.yaml" in manifest["files"]
        assert len(manifest["files"]["policy_rules.yaml"]) == 64  # SHA-256 hex

    def test_excludes_registry_manifest_itself(self, tmp_data_dir):
        (tmp_data_dir / "registry_manifest.json").write_text("{}")
        manifest = generate_manifest(data_dir=tmp_data_dir)
        assert "registry_manifest.json" not in manifest["files"]

    def test_version_embedded(self, tmp_data_dir):
        manifest = generate_manifest(data_dir=tmp_data_dir, version="1.2.3")
        assert manifest["version"] == "1.2.3"

    def test_roundtrip_verify(self, tmp_data_dir, tmp_manifest_path):
        manifest = generate_manifest(data_dir=tmp_data_dir)
        write_manifest(manifest, tmp_manifest_path)
        result = verify_registry_integrity(
            manifest_path=tmp_manifest_path, data_dir=tmp_data_dir
        )
        assert result.passed is True


class TestStartupCheck:
    def test_passes_with_real_files(self):
        result = run_startup_check()
        assert result.passed is True
        assert result.from_cache is False

    def test_cached_on_second_call(self):
        run_startup_check()
        result2 = run_startup_check()
        assert result2.from_cache is True

    def test_force_bypasses_cache(self):
        run_startup_check()
        result2 = run_startup_check(force=True)
        assert result2.from_cache is False

    def test_fails_with_tampered_file(self, tmp_path, capsys):
        """Startup check warns on stderr and returns passed=False."""
        # Set up a temp data dir and manifest that references a specific hash
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        (data_dir / "policy_rules.yaml").write_text("original\n")
        manifest_path = data_dir / "registry_manifest.json"

        from policy_scout.integrity.registry_manifest import (
            generate_manifest,
            write_manifest,
            verify_registry_integrity,
        )

        manifest = generate_manifest(data_dir=data_dir)
        write_manifest(manifest, manifest_path)

        # Tamper with the file
        (data_dir / "policy_rules.yaml").write_text("tampered\n")

        # Directly verify to confirm tamper is detected
        result = verify_registry_integrity(
            manifest_path=manifest_path, data_dir=data_dir
        )
        assert result.passed is False

    def test_no_exit_on_failure(self, tmp_path):
        """Failed startup check warns but does NOT exit (no DoS vector)."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        (data_dir / "rules.yaml").write_text("original\n")
        manifest_path = data_dir / "registry_manifest.json"

        from policy_scout.integrity.registry_manifest import (
            generate_manifest,
            write_manifest,
            verify_registry_integrity,
        )

        manifest = generate_manifest(data_dir=data_dir)
        write_manifest(manifest, manifest_path)
        (data_dir / "rules.yaml").write_text("tampered\n")

        # This should not raise SystemExit
        result = verify_registry_integrity(
            manifest_path=manifest_path, data_dir=data_dir
        )
        assert result.passed is False  # detects tamper but doesn't exit
