"""Tests for [09] Incident Response: lockdown, playbooks, preserve, clearance."""

import json
import tempfile
import zipfile
from pathlib import Path
from unittest.mock import patch

import pytest

from policy_scout.response.lockdown import (
    activate_lockdown,
    deactivate_lockdown,
    is_lockdown_active,
    get_lockdown_reason,
    LOCKDOWN_PATH,
)
from policy_scout.response.playbooks import (
    load_playbooks,
    enrich_report_findings,
    PlaybookRegistry,
    Playbook,
)
from policy_scout.response.preserve import preserve_evidence
from policy_scout.response.clearance import run_clearance_check


@pytest.fixture(autouse=True)
def no_real_lockdown(tmp_path, monkeypatch):
    """Redirect LOCKDOWN_PATH to a temp file so tests don't affect the real state."""
    fake_lockdown = tmp_path / "lockdown.active"
    monkeypatch.setattr(
        "policy_scout.response.lockdown.LOCKDOWN_PATH", fake_lockdown
    )
    # Also patch it in clearance since it imports from lockdown
    monkeypatch.setattr(
        "policy_scout.response.clearance.is_lockdown_active",
        lambda: fake_lockdown.exists(),
    )
    yield fake_lockdown


# ── Lockdown ──────────────────────────────────────────────────────────────────


class TestLockdown:
    def test_inactive_by_default(self, no_real_lockdown):
        assert not is_lockdown_active()

    def test_activate_creates_file(self, no_real_lockdown):
        activate_lockdown(reason="test")
        assert no_real_lockdown.exists()

    def test_deactivate_removes_file(self, no_real_lockdown):
        activate_lockdown(reason="test")
        deactivate_lockdown()
        assert not no_real_lockdown.exists()

    def test_deactivate_when_inactive_is_noop(self, no_real_lockdown):
        result = deactivate_lockdown()
        assert result is True

    def test_reason_persisted(self, no_real_lockdown):
        activate_lockdown(reason="suspected compromise")
        reason = get_lockdown_reason()
        assert reason == "suspected compromise"

    def test_reason_none_when_inactive(self, no_real_lockdown):
        assert get_lockdown_reason() is None

    def test_reason_default_when_no_message(self, no_real_lockdown):
        activate_lockdown()
        reason = get_lockdown_reason()
        assert reason is not None
        assert len(reason) > 0

    def test_activate_returns_true_on_success(self, no_real_lockdown):
        assert activate_lockdown() is True

    def test_deactivate_returns_true_on_success(self, no_real_lockdown):
        activate_lockdown()
        assert deactivate_lockdown() is True


# ── Policy engine lockdown integration ────────────────────────────────────────


class TestPolicyEngineLockdown:
    def test_lockdown_denies_destructive(self, no_real_lockdown):
        from policy_scout.policy.engine import PolicyEngine
        from policy_scout.classify.command_classifier import ClassificationResult
        from policy_scout.core.decision import RiskScore

        activate_lockdown(reason="test")

        engine = PolicyEngine()
        classification = ClassificationResult(
            command_family="rm",
            categories=["destructive"],
            capabilities=[],
            confidence=0.9,
            structure={},
            registry_hits=[],
        )
        risk = RiskScore(risk_score=60, risk_band="high")
        decision = engine.evaluate(classification, risk)

        assert decision.decision == "DENY"
        assert "lockdown" in decision.reasons[0].lower()

    def test_lockdown_allows_safe_reads(self, no_real_lockdown):
        from policy_scout.policy.engine import PolicyEngine
        from policy_scout.classify.command_classifier import ClassificationResult
        from policy_scout.core.decision import RiskScore

        activate_lockdown(reason="test")

        engine = PolicyEngine()
        classification = ClassificationResult(
            command_family="ls",
            categories=["safe_read"],
            capabilities=[],
            confidence=0.95,
            structure={},
            registry_hits=[],
        )
        risk = RiskScore(risk_score=10, risk_band="low")
        decision = engine.evaluate(classification, risk)

        assert decision.decision == "ALLOW_LOGGED"

    def test_normal_evaluation_when_not_in_lockdown(self, no_real_lockdown):
        from policy_scout.policy.engine import PolicyEngine
        from policy_scout.classify.command_classifier import ClassificationResult
        from policy_scout.core.decision import RiskScore

        # Lockdown NOT active
        engine = PolicyEngine()
        classification = ClassificationResult(
            command_family="ls",
            categories=["safe_read"],
            capabilities=[],
            confidence=0.95,
            structure={},
            registry_hits=[],
        )
        risk = RiskScore(risk_score=5, risk_band="low")
        decision = engine.evaluate(classification, risk)

        # Normal evaluation — not lockdown-specific
        assert decision.decision in ("ALLOW", "ALLOW_LOGGED", "DENY", "REQUIRE_APPROVAL", "SANDBOX_FIRST")
        assert "lockdown" not in " ".join(decision.reasons).lower()


# ── Playbooks ─────────────────────────────────────────────────────────────────


class TestPlaybooks:
    def test_loads_bundled_playbooks(self):
        registry = load_playbooks()
        assert len(registry) > 0

    def test_finds_playbook_by_category(self):
        registry = load_playbooks()
        matches = registry.find("suspicious_package", "high")
        assert len(matches) >= 1
        assert matches[0].title

    def test_no_match_below_threshold(self):
        registry = load_playbooks()
        matches = registry.find("suspicious_package", "low")
        assert len(matches) == 0

    def test_no_match_unknown_category(self):
        registry = load_playbooks()
        matches = registry.find("no_such_category_xyz", "critical")
        assert len(matches) == 0

    def test_enrich_findings_attaches_playbook(self):
        findings = [
            {
                "category": "suspicious_package",
                "severity": "high",
                "description": "Suspicious package detected",
            }
        ]
        enriched = enrich_report_findings(findings)
        assert "response_playbook" in enriched[0]
        playbook = enriched[0]["response_playbook"]
        assert "title" in playbook
        assert "immediate_actions" in playbook

    def test_enrich_skips_low_severity(self):
        findings = [
            {"category": "suspicious_package", "severity": "low"}
        ]
        enriched = enrich_report_findings(findings)
        assert "response_playbook" not in enriched[0]

    def test_enrich_skips_unknown_category(self):
        findings = [
            {"category": "unknown_xyz", "severity": "critical"}
        ]
        enriched = enrich_report_findings(findings)
        assert "response_playbook" not in enriched[0]

    def test_empty_playbook_registry(self):
        registry = PlaybookRegistry([])
        findings = [{"category": "suspicious_package", "severity": "high"}]
        enriched = enrich_report_findings(findings, registry=registry)
        assert "response_playbook" not in enriched[0]

    def test_load_from_missing_file(self, tmp_path):
        registry = load_playbooks(path=tmp_path / "nonexistent.yaml")
        assert len(registry) == 0

    def test_playbook_to_dict(self):
        playbook = Playbook(
            id="test",
            categories=["test"],
            severity_threshold="high",
            title="Test Playbook",
            summary="A test playbook",
            immediate_actions=["action 1"],
        )
        d = playbook.to_dict()
        assert d["title"] == "Test Playbook"
        assert d["immediate_actions"] == ["action 1"]


# ── Evidence Preservation ─────────────────────────────────────────────────────


class TestPreserveEvidence:
    def test_creates_zip_archive(self, tmp_path):
        result = preserve_evidence(output_dir=tmp_path)
        assert Path(result.path).exists()
        assert result.path.endswith(".zip")

    def test_archive_is_valid_zip(self, tmp_path):
        result = preserve_evidence(output_dir=tmp_path)
        assert zipfile.is_zipfile(result.path)

    def test_captures_system_info(self, tmp_path):
        result = preserve_evidence(output_dir=tmp_path)
        with zipfile.ZipFile(result.path) as zf:
            names = zf.namelist()
            assert "system_info.json" in names
            info = json.loads(zf.read("system_info.json"))
            assert "hostname" in info
            assert "env_variable_names" in info

    def test_artifact_count_positive(self, tmp_path):
        result = preserve_evidence(output_dir=tmp_path)
        assert result.artifact_count > 0

    def test_result_has_artifact_list(self, tmp_path):
        result = preserve_evidence(output_dir=tmp_path)
        assert "system_info.json" in result.artifacts


# ── Clearance ────────────────────────────────────────────────────────────────


class TestClearance:
    def test_returns_clearance_result(self, no_real_lockdown):
        activate_lockdown(reason="test")
        result = run_clearance_check()
        assert result.cleared is True or result.cleared is False
        assert len(result.checks) > 0
        assert result.summary

    def test_check_names_present(self, no_real_lockdown):
        activate_lockdown()
        result = run_clearance_check()
        check_names = [c.name for c in result.checks]
        assert "registry_integrity" in check_names
        assert "audit_chain" in check_names

    def test_lockdown_check_passes_when_active(self, no_real_lockdown):
        activate_lockdown()
        result = run_clearance_check()
        lockdown_check = next(
            (c for c in result.checks if c.name == "lockdown_active"), None
        )
        assert lockdown_check is not None
        assert lockdown_check.passed is True

    def test_lockdown_check_fails_when_inactive(self, no_real_lockdown):
        # Lockdown NOT active
        result = run_clearance_check()
        lockdown_check = next(
            (c for c in result.checks if c.name == "lockdown_active"), None
        )
        assert lockdown_check is not None
        assert lockdown_check.passed is False

    def test_registry_integrity_passes(self, no_real_lockdown):
        activate_lockdown()
        result = run_clearance_check()
        integrity_check = next(
            (c for c in result.checks if c.name == "registry_integrity"), None
        )
        assert integrity_check is not None
        assert integrity_check.passed is True

    def test_passed_and_failed_counts(self, no_real_lockdown):
        activate_lockdown()
        result = run_clearance_check()
        assert result.passed_count + result.failed_count == len(result.checks)
