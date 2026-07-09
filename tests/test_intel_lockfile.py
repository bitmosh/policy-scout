# SPDX-License-Identifier: Apache-2.0
"""Tests for lockfile integrity checker."""

import json
import tempfile
from pathlib import Path

from policy_scout.intel.local.lockfile_integrity import (
    LockfileIntegrityAdapter,
    check_lockfile_integrity,
)


def _write_lockfile(tmp_path: Path, data: dict) -> str:
    p = tmp_path / "package-lock.json"
    p.write_text(json.dumps(data))
    return str(p)


class TestCheckLockfileIntegrity:
    def test_no_lockfile_returns_ok(self):
        result = check_lockfile_integrity("/nonexistent/path/package-lock.json")
        assert result.ok is True
        assert result.packages_checked == 0

    def test_v2_all_valid(self, tmp_path):
        data = {
            "lockfileVersion": 2,
            "packages": {
                "node_modules/lodash": {
                    "version": "4.17.21",
                    "resolved": "https://registry.npmjs.org/lodash/-/lodash-4.17.21.tgz",
                    "integrity": "sha512-v2kDEe57lecTulaDIuNTPy3Ry4gLGJ6Z1O3vE1krgXZNrsQ+LFTGHVxVjcXPs17LhbZkFezoKFQ27v2RJNB7Q==",
                },
            },
        }
        result = check_lockfile_integrity(_write_lockfile(tmp_path, data))
        assert result.ok is True
        assert result.packages_checked == 1

    def test_v2_missing_integrity(self, tmp_path):
        data = {
            "lockfileVersion": 2,
            "packages": {
                "node_modules/evil-package": {
                    "version": "1.0.0",
                    "resolved": "https://example.com/evil-1.0.0.tgz",
                    # integrity field absent
                },
            },
        }
        result = check_lockfile_integrity(_write_lockfile(tmp_path, data))
        assert result.ok is False
        assert "node_modules/evil-package" in result.packages_missing_integrity

    def test_v2_bad_integrity_format(self, tmp_path):
        data = {
            "lockfileVersion": 2,
            "packages": {
                "node_modules/bad": {
                    "version": "1.0.0",
                    "resolved": "https://example.com/bad.tgz",
                    "integrity": "not-a-valid-sri-string",
                },
            },
        }
        result = check_lockfile_integrity(_write_lockfile(tmp_path, data))
        assert result.ok is False
        assert "node_modules/bad" in result.packages_bad_integrity

    def test_v1_valid(self, tmp_path):
        data = {
            "lockfileVersion": 1,
            "dependencies": {
                "lodash": {
                    "version": "4.17.21",
                    "resolved": "https://registry.npmjs.org/lodash/-/lodash-4.17.21.tgz",
                    "integrity": "sha512-v2kDEe57lecTulaDIuNTPy3Ry4gLGJ6Z1O3vE1krgXZNrsQ+LFTGHVxVjcXPs17LhbZkFezoKFQ27v2RJNB7Q==",
                },
            },
        }
        result = check_lockfile_integrity(_write_lockfile(tmp_path, data))
        assert result.ok is True
        assert result.packages_checked == 1

    def test_root_package_skipped(self, tmp_path):
        data = {
            "lockfileVersion": 2,
            "packages": {
                "": {"name": "my-app", "version": "1.0.0"},  # root entry, should be skipped
                "node_modules/lodash": {
                    "version": "4.17.21",
                    "resolved": "https://registry.npmjs.org/lodash/-/lodash-4.17.21.tgz",
                    "integrity": "sha512-v2kDEe57lecTulaDIuNTPy3Ry4gLGJ6Z1O3vE1krgXZNrsQ+LFTGHVxVjcXPs17LhbZkFezoKFQ27v2RJNB7Q==",
                },
            },
        }
        result = check_lockfile_integrity(_write_lockfile(tmp_path, data))
        assert result.packages_checked == 1

    def test_invalid_json(self, tmp_path):
        p = tmp_path / "package-lock.json"
        p.write_text("this is not json {{{")
        result = check_lockfile_integrity(str(p))
        assert result.ok is False


class TestLockfileIntegrityAdapter:
    def test_non_npm_skipped(self):
        adapter = LockfileIntegrityAdapter()
        result = adapter.enrich_package("pypi", "requests")
        assert result.lockfile_integrity_ok is None

    def test_npm_no_lockfile(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        adapter = LockfileIntegrityAdapter()
        result = adapter.enrich_package("npm", "lodash")
        assert result.lockfile_integrity_ok is None  # no lockfile found

    def test_npm_valid_lockfile(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        lf = tmp_path / "package-lock.json"
        lf.write_text(json.dumps({
            "lockfileVersion": 2,
            "packages": {
                "node_modules/lodash": {
                    "version": "4.17.21",
                    "resolved": "https://registry.npmjs.org/lodash/-/lodash-4.17.21.tgz",
                    "integrity": "sha512-v2kDEe57lecTulaDIuNTPy3Ry4gLGJ6Z1O3vE1krgXZNrsQ+LFTGHVxVjcXPs17LhbZkFezoKFQ27v2RJNB7Q==",
                },
            },
        }))
        adapter = LockfileIntegrityAdapter()
        result = adapter.enrich_package("npm", "lodash")
        assert result.lockfile_integrity_ok is True
