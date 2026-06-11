"""Tests for canary file system."""

import json
from pathlib import Path

from policy_scout.canary.tokens import (
    extract_canary_token,
    generate_canary_token,
    is_canary_token,
)
from policy_scout.canary.installer import (
    CANARY_FILENAME,
    install_canary,
    remove_canary,
)
from policy_scout.canary.checker import check_canary_status


# ── Token generation ──────────────────────────────────────────────────────────

class TestCanaryTokens:
    def test_token_format(self):
        token = generate_canary_token()
        assert token.startswith("PSCANARY-")
        assert token.endswith("-DO-NOT-ACT")

    def test_token_uniqueness(self):
        tokens = {generate_canary_token() for _ in range(20)}
        assert len(tokens) == 20

    def test_is_canary_token_valid(self):
        token = generate_canary_token()
        assert is_canary_token(token)

    def test_is_canary_token_invalid(self):
        assert not is_canary_token("not-a-token")
        assert not is_canary_token("PSCANARY-toolong-EXTRA-DO-NOT-ACT")

    def test_extract_token_from_text(self):
        token = generate_canary_token()
        text = f"some preamble\nCanary token: {token}\nmore text"
        extracted = extract_canary_token(text)
        assert extracted == token

    def test_extract_token_none_when_absent(self):
        assert extract_canary_token("no token here") is None

    def test_extract_token_first_match(self):
        t1 = generate_canary_token()
        t2 = generate_canary_token()
        text = f"{t1} and {t2}"
        extracted = extract_canary_token(text)
        assert extracted == t1


# ── Installer ─────────────────────────────────────────────────────────────────

class TestCanaryInstaller:
    def test_install_creates_file(self, tmp_path):
        result = install_canary(tmp_path)
        canary = tmp_path / CANARY_FILENAME
        assert canary.exists()
        assert result["path"] == str(canary)
        assert result["already_existed"] is False

    def test_install_writes_valid_token(self, tmp_path):
        result = install_canary(tmp_path)
        assert is_canary_token(result["token"])

    def test_install_token_in_file(self, tmp_path):
        result = install_canary(tmp_path)
        content = (tmp_path / CANARY_FILENAME).read_text()
        assert result["token"] in content

    def test_install_idempotent(self, tmp_path):
        r1 = install_canary(tmp_path)
        r2 = install_canary(tmp_path)
        assert r2["already_existed"] is True
        assert r1["token"] == r2["token"]

    def test_remove_deletes_file(self, tmp_path):
        install_canary(tmp_path)
        removed = remove_canary(tmp_path)
        assert removed is True
        assert not (tmp_path / CANARY_FILENAME).exists()

    def test_remove_nonexistent_returns_false(self, tmp_path):
        removed = remove_canary(tmp_path)
        assert removed is False

    def test_canary_file_has_suppression_comment(self, tmp_path):
        install_canary(tmp_path)
        content = (tmp_path / CANARY_FILENAME).read_text()
        assert "policy-scout-injection-allow" in content


# ── Checker ───────────────────────────────────────────────────────────────────

class TestCanaryChecker:
    def test_not_installed_returns_false(self, tmp_path):
        status = check_canary_status(tmp_path)
        assert status.installed is False

    def test_installed_returns_true(self, tmp_path):
        install_canary(tmp_path)
        status = check_canary_status(tmp_path)
        assert status.installed is True

    def test_token_in_status(self, tmp_path):
        result = install_canary(tmp_path)
        status = check_canary_status(tmp_path)
        assert status.token == result["token"]

    def test_no_audit_hits_initially(self, tmp_path, monkeypatch):
        install_canary(tmp_path)
        # Point at a non-existent audit log
        monkeypatch.setenv("POLICY_SCOUT_AUDIT_PATH", str(tmp_path / "no_audit.jsonl"))
        status = check_canary_status(tmp_path)
        assert status.audit_hits == []

    def test_to_dict_shape(self, tmp_path):
        install_canary(tmp_path)
        status = check_canary_status(tmp_path)
        d = status.to_dict()
        assert "installed" in d
        assert "token" in d
        assert "audit_hit_count" in d
        assert "audit_hits" in d
