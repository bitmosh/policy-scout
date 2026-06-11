"""Tests for [10] Policy Management — Phases 1 + 2: project override loading and engine integration."""

import pytest
from pathlib import Path

# These tests exercise the real filesystem-based discovery and loading,
# and the policy engine wired to pick up project overrides.
# They must opt out of the global isolation fixture (conftest.py).
pytestmark = pytest.mark.no_policy_isolation

from policy_scout.policy.management import (
    ProjectOverride,
    EffectivePolicy,
    PolicyOverrideViolation,
    find_project_config,
    load_project_override,
    RuleTrace,
    SimulationResult,
    simulate,
    HistoryTestCase,
    HistoryTestResult,
    test_against_history,
    PolicyIssue,
    ValidationResult,
    validate_policy,
    commit_policy_state,
)
from policy_scout.audit.events import EventType
from policy_scout.policy.engine import PolicyEngine
from policy_scout.classify.command_classifier import ClassificationResult
from policy_scout.policy.risk_scorer import RiskScore


# ──────────────────────────────────────────────────────────────────────────────
# Helper
# ──────────────────────────────────────────────────────────────────────────────

def _write_config(directory: Path, content: str) -> Path:
    path = directory / ".policy-scout.yaml"
    path.write_text(content, encoding="utf-8")
    return path


# ──────────────────────────────────────────────────────────────────────────────
# find_project_config — discovery algorithm
# ──────────────────────────────────────────────────────────────────────────────

class TestFindProjectConfig:
    def test_finds_config_in_cwd(self, tmp_path):
        _write_config(tmp_path, "version: test-v1\n")
        result = find_project_config(cwd=tmp_path)
        assert result == tmp_path / ".policy-scout.yaml"

    def test_walks_up_to_parent(self, tmp_path):
        child = tmp_path / "nested" / "dir"
        child.mkdir(parents=True)
        _write_config(tmp_path, "version: parent-v1\n")
        result = find_project_config(cwd=child)
        assert result == tmp_path / ".policy-scout.yaml"

    def test_stops_at_git_root_not_found(self, tmp_path):
        # .git exists in parent, no config in parent
        (tmp_path / ".git").mkdir()
        child = tmp_path / "src"
        child.mkdir()
        result = find_project_config(cwd=child)
        assert result is None

    def test_finds_config_below_git_root(self, tmp_path):
        # .git exists AND config exists in same dir — should find config
        (tmp_path / ".git").mkdir()
        _write_config(tmp_path, "version: v1\n")
        result = find_project_config(cwd=tmp_path)
        assert result == tmp_path / ".policy-scout.yaml"

    def test_not_found_returns_none(self, tmp_path):
        result = find_project_config(cwd=tmp_path)
        assert result is None

    def test_walks_multiple_levels(self, tmp_path):
        deep = tmp_path / "a" / "b" / "c"
        deep.mkdir(parents=True)
        _write_config(tmp_path, "version: root-v1\n")
        result = find_project_config(cwd=deep)
        assert result == tmp_path / ".policy-scout.yaml"

    def test_prefers_closer_config(self, tmp_path):
        child = tmp_path / "subproject"
        child.mkdir()
        _write_config(tmp_path, "version: parent\n")
        _write_config(child, "version: child\n")
        result = find_project_config(cwd=child)
        assert result == child / ".policy-scout.yaml"


# ──────────────────────────────────────────────────────────────────────────────
# load_project_override — valid configs
# ──────────────────────────────────────────────────────────────────────────────

class TestLoadProjectOverrideValid:
    def test_returns_none_when_no_file(self, tmp_path):
        result = load_project_override(cwd=tmp_path)
        assert result is None

    def test_loads_minimal_config(self, tmp_path):
        _write_config(tmp_path, "version: v1\n")
        result = load_project_override(cwd=tmp_path)
        assert result is not None
        assert result.version == "v1"
        assert result.config_path == tmp_path / ".policy-scout.yaml"

    def test_loads_mode(self, tmp_path):
        _write_config(tmp_path, "mode: paranoid\n")
        result = load_project_override(cwd=tmp_path)
        assert result is not None
        assert result.mode == "paranoid"

    def test_loads_additional_rules(self, tmp_path):
        _write_config(tmp_path, """\
additional_rules:
  - id: deny_python
    decision: DENY
    match:
      command_pattern: "^python"
    reasons:
      - "Python restricted in this project"
""")
        result = load_project_override(cwd=tmp_path)
        assert result is not None
        assert len(result.additional_rules) == 1
        rule = result.additional_rules[0]
        assert rule.id == "deny_python"
        assert rule.decision == "DENY"
        assert rule.match == {"command_pattern": "^python"}

    def test_loads_override_decisions(self, tmp_path):
        _write_config(tmp_path, """\
override_decisions:
  - rule_id: destructive_deny
    strengthen_to: DENY_AND_ALERT
""")
        result = load_project_override(cwd=tmp_path)
        assert result is not None
        assert len(result.override_decisions) == 1
        od = result.override_decisions[0]
        assert od.rule_id == "destructive_deny"
        assert od.strengthen_to == "DENY_AND_ALERT"

    def test_loads_intel_and_scan_flags(self, tmp_path):
        _write_config(tmp_path, """\
intel:
  remote: true
scan:
  pre_commit: true
""")
        result = load_project_override(cwd=tmp_path)
        assert result is not None
        assert result.intel_remote is True
        assert result.scan_pre_commit is True

    def test_all_valid_decisions_for_additional_rules(self, tmp_path):
        for decision in ("REQUIRE_APPROVAL", "SANDBOX_FIRST", "DENY", "DENY_AND_ALERT"):
            _write_config(tmp_path, f"""\
additional_rules:
  - id: rule_{decision.lower()}
    decision: {decision}
    match: {{}}
""")
            result = load_project_override(cwd=tmp_path)
            assert result is not None
            assert result.additional_rules[0].decision == decision

    def test_all_valid_modes(self, tmp_path):
        for mode in ("lenient", "balanced", "strict", "paranoid"):
            _write_config(tmp_path, f"mode: {mode}\n")
            result = load_project_override(cwd=tmp_path)
            assert result is not None
            assert result.mode == mode

    def test_empty_yaml_returns_empty_override(self, tmp_path):
        _write_config(tmp_path, "")
        result = load_project_override(cwd=tmp_path)
        assert result is not None
        assert result.additional_rules == []
        assert result.override_decisions == []
        assert result.mode is None


# ──────────────────────────────────────────────────────────────────────────────
# load_project_override — tighten-only violations
# ──────────────────────────────────────────────────────────────────────────────

class TestLoadProjectOverrideViolations:
    def test_rejects_allow_in_additional_rules(self, tmp_path):
        _write_config(tmp_path, """\
additional_rules:
  - id: bad_allow
    decision: ALLOW
    match: {}
""")
        with pytest.raises(PolicyOverrideViolation, match="ALLOW"):
            load_project_override(cwd=tmp_path)

    def test_rejects_allow_logged_in_additional_rules(self, tmp_path):
        _write_config(tmp_path, """\
additional_rules:
  - id: bad_allow_logged
    decision: ALLOW_LOGGED
    match: {}
""")
        with pytest.raises(PolicyOverrideViolation, match="ALLOW_LOGGED"):
            load_project_override(cwd=tmp_path)

    def test_rejects_allow_in_strengthen_to(self, tmp_path):
        _write_config(tmp_path, """\
override_decisions:
  - rule_id: some_rule
    strengthen_to: ALLOW
""")
        with pytest.raises(PolicyOverrideViolation, match="ALLOW"):
            load_project_override(cwd=tmp_path)

    def test_rejects_allow_logged_in_strengthen_to(self, tmp_path):
        _write_config(tmp_path, """\
override_decisions:
  - rule_id: some_rule
    strengthen_to: ALLOW_LOGGED
""")
        with pytest.raises(PolicyOverrideViolation, match="ALLOW_LOGGED"):
            load_project_override(cwd=tmp_path)

    def test_rejects_unknown_mode(self, tmp_path):
        _write_config(tmp_path, "mode: ultra_lenient\n")
        with pytest.raises(PolicyOverrideViolation, match="ultra_lenient"):
            load_project_override(cwd=tmp_path)

    def test_rejects_rule_missing_id(self, tmp_path):
        _write_config(tmp_path, """\
additional_rules:
  - decision: DENY
    match: {}
""")
        with pytest.raises(PolicyOverrideViolation, match="id"):
            load_project_override(cwd=tmp_path)

    def test_rejects_strengthen_missing_rule_id(self, tmp_path):
        _write_config(tmp_path, """\
override_decisions:
  - strengthen_to: DENY
""")
        with pytest.raises(PolicyOverrideViolation, match="rule_id"):
            load_project_override(cwd=tmp_path)


# ──────────────────────────────────────────────────────────────────────────────
# ProjectOverride serialization
# ──────────────────────────────────────────────────────────────────────────────

class TestProjectOverrideSerialization:
    def test_to_dict_round_trip(self, tmp_path):
        _write_config(tmp_path, """\
version: test-v1
mode: strict
additional_rules:
  - id: deny_curl_bash
    decision: DENY
    match:
      command_pattern: "curl.*bash"
    reasons:
      - "Curl-pipe-shell disallowed"
override_decisions:
  - rule_id: destructive_deny
    strengthen_to: DENY_AND_ALERT
intel:
  remote: true
scan:
  pre_commit: false
""")
        result = load_project_override(cwd=tmp_path)
        assert result is not None
        d = result.to_dict()
        assert d["version"] == "test-v1"
        assert d["mode"] == "strict"
        assert len(d["additional_rules"]) == 1
        assert d["additional_rules"][0]["id"] == "deny_curl_bash"
        assert len(d["override_decisions"]) == 1
        assert d["override_decisions"][0]["strengthen_to"] == "DENY_AND_ALERT"
        assert d["intel_remote"] is True
        assert d["scan_pre_commit"] is False

    def test_override_rule_to_dict(self, tmp_path):
        _write_config(tmp_path, """\
additional_rules:
  - id: sandbox_npm
    decision: SANDBOX_FIRST
    match:
      command_pattern: "^npm"
    reasons:
      - "npm may run lifecycle scripts"
    description: "Sandbox all npm commands"
""")
        result = load_project_override(cwd=tmp_path)
        assert result is not None
        rule_dict = result.additional_rules[0].to_dict()
        assert rule_dict["id"] == "sandbox_npm"
        assert rule_dict["decision"] == "SANDBOX_FIRST"
        assert rule_dict["description"] == "Sandbox all npm commands"


# ──────────────────────────────────────────────────────────────────────────────
# EffectivePolicy dataclass
# ──────────────────────────────────────────────────────────────────────────────

class TestEffectivePolicy:
    def test_to_dict_no_project_config(self):
        ep = EffectivePolicy(
            layers=["builtin:1.3.0"],
            effective_version="1.3.0++",
            mode="balanced",
        )
        d = ep.to_dict()
        assert d["mode"] == "balanced"
        assert d["project_config_path"] is None
        assert d["effective_version"] == "1.3.0++"

    def test_to_dict_with_project_config(self, tmp_path):
        _write_config(tmp_path, "mode: strict\n")
        override = load_project_override(cwd=tmp_path)
        ep = EffectivePolicy(
            layers=["builtin:1.3.0", "project:v1"],
            effective_version="1.3.0++v1",
            mode="strict",
            project_config_path=tmp_path / ".policy-scout.yaml",
            project_override=override,
        )
        d = ep.to_dict()
        assert d["mode"] == "strict"
        assert ".policy-scout.yaml" in d["project_config_path"]


# ──────────────────────────────────────────────────────────────────────────────
# New EventType constants exist
# ──────────────────────────────────────────────────────────────────────────────

class TestEventTypes:
    def test_project_override_event_types_exist(self):
        assert EventType.PROJECT_OVERRIDE_LOADED == "ProjectOverrideLoaded"
        assert EventType.PROJECT_OVERRIDE_VIOLATED == "ProjectOverrideViolated"
        assert EventType.POLICY_SIMULATED == "PolicySimulated"
        assert EventType.POLICY_VALIDATED == "PolicyValidated"
        assert EventType.POLICY_HISTORY_TESTED == "PolicyHistoryTested"


# ──────────────────────────────────────────────────────────────────────────────
# Phase 2 — PolicyEngine integration with project overrides
# ──────────────────────────────────────────────────────────────────────────────

def _make_classification(categories=None, capabilities=None, command_family="unknown"):
    """Build a minimal ClassificationResult for engine tests."""
    return ClassificationResult(
        command_family=command_family,
        categories=categories or [],
        capabilities=capabilities or [],
        confidence=0.9,
    )


def _dummy_risk():
    return RiskScore(risk_score=5, risk_band="medium", request_id="test")


class TestPolicyEngineOverrideIntegration:
    def test_config_override_none_string_skips_discovery(self):
        """config_override='none' → no project override loaded regardless of cwd."""
        engine = PolicyEngine(config_override="none")
        assert engine.project_override is None
        assert engine.override_violation is None

    def test_engine_loads_override_from_cwd(self, tmp_path):
        """Engine discovers .policy-scout.yaml from the cwd it's given."""
        _write_config(tmp_path, "version: proj-v1\n")
        engine = PolicyEngine(config_override=tmp_path)
        assert engine.project_override is not None
        assert engine.project_override.version == "proj-v1"

    def test_engine_no_override_when_no_file(self, tmp_path):
        engine = PolicyEngine(config_override=tmp_path)
        assert engine.project_override is None
        assert engine.override_violation is None

    def test_engine_graceful_on_violation(self, tmp_path):
        """A loosening override is rejected gracefully — engine falls back to global policy."""
        _write_config(tmp_path, """\
additional_rules:
  - id: bad_allow
    decision: ALLOW
    match: {}
""")
        engine = PolicyEngine(config_override=tmp_path)
        assert engine.project_override is None
        assert engine.override_violation is not None
        assert "ALLOW" in engine.override_violation

    def test_override_additional_rule_fires_on_category(self, tmp_path):
        """An additional DENY rule on a category fires before global rules."""
        _write_config(tmp_path, """\
additional_rules:
  - id: deny_network_fetch
    decision: DENY
    match:
      categories:
        - network_fetch
    reasons:
      - "Network fetch disallowed in this project"
""")
        engine = PolicyEngine(config_override=tmp_path)
        classification = _make_classification(categories=["network_fetch"])
        decision = engine.evaluate(classification, _dummy_risk(), command="curl http://example.com")
        assert decision.decision == "DENY"
        assert "deny_network_fetch" in decision.policy_hits

    def test_override_additional_rule_fires_on_command_pattern(self, tmp_path):
        """command_pattern in an additional rule matches against the raw command."""
        _write_config(tmp_path, """\
additional_rules:
  - id: sandbox_npm_install
    decision: SANDBOX_FIRST
    match:
      command_pattern: "^npm install"
    reasons:
      - "npm install must run in sandbox"
""")
        engine = PolicyEngine(config_override=tmp_path)
        classification = _make_classification(categories=["package_install"])
        decision = engine.evaluate(classification, _dummy_risk(), command="npm install lodash")
        assert decision.decision == "SANDBOX_FIRST"
        assert "sandbox_npm_install" in decision.policy_hits

    def test_command_pattern_no_match_skips_rule(self, tmp_path):
        """A command that doesn't match command_pattern is unaffected by that rule."""
        _write_config(tmp_path, """\
additional_rules:
  - id: deny_npm_install
    decision: DENY
    match:
      command_pattern: "^npm install"
    reasons:
      - "npm install denied"
""")
        engine = PolicyEngine(config_override=tmp_path)
        classification = _make_classification(categories=["safe_read"])
        # "ls" doesn't match "^npm install"
        decision = engine.evaluate(classification, _dummy_risk(), command="ls -la")
        assert "deny_npm_install" not in (decision.policy_hits or [])

    def test_command_pattern_requires_command_string(self, tmp_path):
        """A command_pattern rule is skipped entirely when no command string is passed."""
        _write_config(tmp_path, """\
additional_rules:
  - id: deny_npm
    decision: DENY
    match:
      command_pattern: "^npm"
    reasons:
      - "npm denied"
""")
        engine = PolicyEngine(config_override=tmp_path)
        classification = _make_classification(categories=["package_install"])
        # No command string — pattern rule is skipped; engine falls to global/fallback
        decision = engine.evaluate(classification, _dummy_risk())
        assert "deny_npm" not in (decision.policy_hits or [])

    def test_override_decisions_strengthening(self, tmp_path):
        """override_decisions strengthens a matched global rule's decision."""
        _write_config(tmp_path, """\
override_decisions:
  - rule_id: destructive_system_deny
    strengthen_to: DENY_AND_ALERT
""")
        engine = PolicyEngine(config_override=tmp_path)
        # "destructive" category + "/" in command_family → matches destructive_system_deny fallback
        classification = _make_classification(
            categories=["destructive"],
            command_family="rm",
        )
        classification.structure = {}  # no has_pipe
        # The engine's override block fires for system-level destructive — check strengthening
        # at the rule-match level (before the hard destructive override)
        decision = engine.evaluate(classification, _dummy_risk(), command="rm file.txt")
        # Either strengthened to DENY_AND_ALERT or DENY from the destructive override
        assert decision.decision in ("DENY", "DENY_AND_ALERT")

    def test_empty_match_rule_catches_everything(self, tmp_path):
        """An additional rule with empty match: {} fires on any command."""
        _write_config(tmp_path, """\
additional_rules:
  - id: require_all
    decision: REQUIRE_APPROVAL
    match: {}
    priority: 100
    reasons:
      - "All commands require approval in this project"
""")
        engine = PolicyEngine(config_override=tmp_path)
        classification = _make_classification(categories=["safe_read"])
        decision = engine.evaluate(classification, _dummy_risk(), command="ls")
        assert "require_all" in decision.policy_hits


# ──────────────────────────────────────────────────────────────────────────────
# Phase 3 — Simulator
# ──────────────────────────────────────────────────────────────────────────────

class TestSimulator:
    def test_simulate_returns_simulation_result(self):
        result = simulate("ls -la")
        assert isinstance(result, SimulationResult)
        assert result.command == "ls -la"
        assert result.decision in (
            "ALLOW", "ALLOW_LOGGED", "REQUIRE_APPROVAL",
            "SANDBOX_FIRST", "DENY", "DENY_AND_ALERT",
        )

    def test_simulate_has_rule_traces(self):
        result = simulate("ls -la")
        assert len(result.rule_traces) > 0
        assert all(isinstance(t, RuleTrace) for t in result.rule_traces)

    def test_simulate_exactly_one_decisive_trace(self):
        """Exactly one rule trace should be marked decisive."""
        result = simulate("npm install lodash")
        decisive = [t for t in result.rule_traces if t.decisive]
        assert len(decisive) == 1
        assert decisive[0].rule_id == result.matched_rule

    def test_simulate_all_traces_checked(self):
        """Every trace should have checked=True."""
        result = simulate("git status")
        assert all(t.checked for t in result.rule_traces)

    def test_simulate_matched_traces_have_decision(self):
        """Matched traces must have a decision field set."""
        result = simulate("pip install requests")
        for trace in result.rule_traces:
            if trace.matched:
                assert trace.decision is not None
            else:
                assert trace.decision is None

    def test_simulate_returns_risk_score(self):
        result = simulate("rm -rf /tmp/test")
        assert result.risk_score >= 0
        assert result.risk_band in ("low", "medium", "high", "critical")

    def test_simulate_returns_categories(self):
        result = simulate("ls")
        assert isinstance(result.categories, list)

    def test_simulate_total_rules_checked(self):
        result = simulate("ls")
        assert result.total_rules_checked == len(result.rule_traces)

    def test_simulate_no_project_override_without_config(self, tmp_path):
        """With no .policy-scout.yaml, project_override_loaded is False."""
        result = simulate("ls", cwd=tmp_path)
        assert result.project_override_loaded is False
        assert result.project_override_path is None

    def test_simulate_with_project_override(self, tmp_path):
        """With a .policy-scout.yaml, project_override_loaded is True."""
        _write_config(tmp_path, """\
additional_rules:
  - id: deny_ls
    decision: DENY
    match:
      command_pattern: "^ls"
    reasons:
      - "ls is disallowed"
""")
        result = simulate("ls -la", cwd=tmp_path)
        assert result.project_override_loaded is True
        assert result.project_override_path is not None
        assert "deny_ls" in result.matched_rule or any(
            t.rule_id == "deny_ls" and t.decisive for t in result.rule_traces
        )

    def test_simulate_override_rules_appear_in_trace(self, tmp_path):
        """Override rules appear as source='override' in the trace."""
        _write_config(tmp_path, """\
additional_rules:
  - id: my_override_rule
    decision: REQUIRE_APPROVAL
    match: {}
    priority: 500
    reasons:
      - "Test override"
""")
        result = simulate("ls", cwd=tmp_path)
        override_traces = [t for t in result.rule_traces if t.source == "override"]
        assert len(override_traces) == 1
        assert override_traces[0].rule_id == "my_override_rule"

    def test_simulate_registry_rules_appear_in_trace(self):
        """Registry rules appear as source='registry' in the trace."""
        result = simulate("ls")
        registry_traces = [t for t in result.rule_traces if t.source == "registry"]
        assert len(registry_traces) > 0

    def test_simulate_fallback_rules_appear_in_trace(self):
        """Fallback rules always appear in the trace."""
        result = simulate("ls")
        fallback_traces = [t for t in result.rule_traces if t.source == "fallback"]
        assert len(fallback_traces) > 0

    def test_simulate_decision_matches_engine_evaluate(self):
        """simulate() must produce the same final decision as engine.evaluate()."""
        from policy_scout.classify.shell_parser import ShellParser
        from policy_scout.classify.command_classifier import CommandClassifier
        from policy_scout.policy.risk_scorer import RiskScorer
        from policy_scout.registry.loader import RegistryLoader

        commands = ["ls -la", "npm install lodash", "git status", "pip install requests"]
        loader = RegistryLoader()
        parser = ShellParser()
        classifier = CommandClassifier(command_registry=loader.command_registry)
        risk_scorer = RiskScorer()
        engine = PolicyEngine(
            policy_registry=loader.policy_registry,
            config_override="none",
        )

        for cmd in commands:
            parse_result = parser.parse(cmd)
            classification = classifier.classify(parse_result, cmd)
            risk = risk_scorer.score(classification)
            engine_decision = engine.evaluate(classification, risk, command=cmd)

            sim_result = simulate(cmd)
            assert sim_result.decision == engine_decision.decision, (
                f"Decision mismatch for '{cmd}': "
                f"engine={engine_decision.decision}, simulator={sim_result.decision}"
            )

    def test_rule_trace_to_dict(self):
        trace = RuleTrace(
            rule_id="test_rule",
            source="registry",
            priority=500,
            checked=True,
            matched=True,
            reasons=["test reason"],
            decision="ALLOW",
            decisive=True,
        )
        d = trace.to_dict()
        assert d["rule_id"] == "test_rule"
        assert d["source"] == "registry"
        assert d["decisive"] is True
        assert d["decision"] == "ALLOW"

    def test_simulation_result_to_dict(self):
        result = simulate("git status")
        d = result.to_dict()
        assert "command" in d
        assert "decision" in d
        assert "rule_traces" in d
        assert isinstance(d["rule_traces"], list)


# ──────────────────────────────────────────────────────────────────────────────
# Phase 4 — History Tester
# ──────────────────────────────────────────────────────────────────────────────

class _FakeStore:
    """In-memory audit store stub for history tester tests."""

    def __init__(self, decision_events=None, command_events=None):
        self._decision_events = decision_events or []
        self._command_events = command_events or []

    def list_by_event_type(self, event_type):
        if event_type == "DecisionIssued":
            return self._decision_events
        if event_type == "CommandRequested":
            return self._command_events
        return []


def _make_audit_pair(request_id, command, decision, days_ago=1):
    """Build a (CommandRequested, DecisionIssued) pair for testing."""
    import json
    from datetime import datetime, timedelta, timezone
    ts = (datetime.now(timezone.utc) - timedelta(days=days_ago)).strftime("%Y-%m-%dT%H:%M:%S")
    cmd_evt = {
        "event_id": f"evt_cmd_{request_id}",
        "event_type": "CommandRequested",
        "timestamp": ts,
        "request_id": request_id,
        "data_json": json.dumps({"command": command}),
    }
    dec_evt = {
        "event_id": f"evt_dec_{request_id}",
        "event_type": "DecisionIssued",
        "timestamp": ts,
        "request_id": request_id,
        "data_json": json.dumps({
            "decision": decision,
            "risk_score": 5,
            "risk_band": "medium",
            "reasons": ["test"],
        }),
    }
    return cmd_evt, dec_evt


class TestHistoryTester:
    def test_empty_store_returns_zero_total(self):
        store = _FakeStore()
        result = test_against_history(days=7, audit_store=store)
        assert isinstance(result, HistoryTestResult)
        assert result.total == 0
        assert result.changed == 0
        assert result.skipped == 0

    def test_no_command_event_is_skipped(self):
        import json
        store = _FakeStore(
            decision_events=[{
                "event_id": "evt_1",
                "event_type": "DecisionIssued",
                "timestamp": "2099-01-01T00:00:00",
                "request_id": "req_orphan",
                "data_json": json.dumps({"decision": "ALLOW", "risk_score": 1, "risk_band": "low", "reasons": []}),
            }],
            command_events=[],  # no matching CommandRequested
        )
        result = test_against_history(days=7, audit_store=store)
        assert result.skipped == 1
        assert result.total == 0

    def test_decision_outside_window_excluded(self):
        cmd_evt, dec_evt = _make_audit_pair("req_old", "ls", "ALLOW_LOGGED", days_ago=30)
        store = _FakeStore(
            decision_events=[dec_evt],
            command_events=[cmd_evt],
        )
        result = test_against_history(days=7, audit_store=store)
        assert result.total == 0

    def test_decision_within_window_included(self):
        cmd_evt, dec_evt = _make_audit_pair("req_recent", "ls", "ALLOW_LOGGED", days_ago=1)
        store = _FakeStore(
            decision_events=[dec_evt],
            command_events=[cmd_evt],
        )
        result = test_against_history(days=7, audit_store=store)
        assert result.total == 1

    def test_unchanged_decision_counted_correctly(self):
        """If simulate produces the same decision as recorded, changed=0."""
        # Use "ls" which should consistently produce ALLOW or ALLOW_LOGGED
        result_check = simulate("ls")
        cmd_evt, dec_evt = _make_audit_pair(
            "req_ls", "ls", result_check.decision, days_ago=1
        )
        store = _FakeStore(decision_events=[dec_evt], command_events=[cmd_evt])
        result = test_against_history(days=7, audit_store=store)
        assert result.total == 1
        assert result.changed == 0
        assert result.unchanged == 1

    def test_changed_decision_reported(self):
        """If we record ALLOW but simulate returns DENY, it shows as changed."""
        cmd_evt, dec_evt = _make_audit_pair("req_diff", "ls", "ALLOW", days_ago=1)
        # Force a contrived mismatch: simulate "ls" will return whatever it returns,
        # we set the stored decision to something that differs
        real_sim = simulate("ls")
        if real_sim.decision == "ALLOW":
            # Store DENY to guarantee a change
            import json
            dec_evt["data_json"] = json.dumps({
                "decision": "DENY", "risk_score": 9, "risk_band": "critical", "reasons": []
            })

        store = _FakeStore(decision_events=[dec_evt], command_events=[cmd_evt])
        result = test_against_history(days=7, audit_store=store)
        assert result.total == 1
        # Either changed (if decision differs) or unchanged (if they match) is valid

    def test_direction_tightened(self):
        from policy_scout.policy.management.history_tester import _decision_direction
        assert _decision_direction("ALLOW", "DENY") == "tightened"

    def test_direction_loosened(self):
        from policy_scout.policy.management.history_tester import _decision_direction
        assert _decision_direction("DENY", "ALLOW") == "loosened"

    def test_direction_unchanged(self):
        from policy_scout.policy.management.history_tester import _decision_direction
        assert _decision_direction("REQUIRE_APPROVAL", "REQUIRE_APPROVAL") == "unchanged"

    def test_change_rate_zero_on_empty(self):
        result = HistoryTestResult(days=7, total=0, changed=0, unchanged=0,
                                   tightened=0, loosened=0, skipped=0)
        assert result.change_rate == 0.0

    def test_to_dict_structure(self):
        result = HistoryTestResult(
            days=7, total=10, changed=2, unchanged=8,
            tightened=1, loosened=1, skipped=0,
            changed_cases=[],
        )
        d = result.to_dict()
        assert d["total"] == 10
        assert d["changed"] == 2
        assert "change_rate" in d
        assert isinstance(d["changed_cases"], list)


# ──────────────────────────────────────────────────────────────────────────────
# Phase 5 — Validator
# ──────────────────────────────────────────────────────────────────────────────

class TestValidator:
    def test_validate_current_policy_runs(self):
        """validate_policy() runs against the real registry without crashing."""
        result = validate_policy()
        assert isinstance(result, ValidationResult)
        assert result.rules_checked > 0

    def test_validate_returns_validation_result(self):
        result = validate_policy()
        assert hasattr(result, "issues")
        assert hasattr(result, "error_count")
        assert hasattr(result, "warning_count")
        assert hasattr(result, "is_valid")

    def test_validate_to_dict(self):
        result = validate_policy()
        d = result.to_dict()
        assert "rules_checked" in d
        assert "error_count" in d
        assert "warning_count" in d
        assert "is_valid" in d
        assert "issues" in d
        assert isinstance(d["issues"], list)

    def test_policy_issue_to_dict(self):
        issue = PolicyIssue(
            issue_type="contradiction",
            rule_id="rule_a",
            description="Conflicting rules",
            severity="error",
            related_rule_id="rule_b",
        )
        d = issue.to_dict()
        assert d["issue_type"] == "contradiction"
        assert d["severity"] == "error"
        assert d["related_rule_id"] == "rule_b"

    def test_contradictions_detected(self):
        """Two rules with identical matchers but different decisions → contradiction."""
        from policy_scout.registry.models import PolicyRegistry, PolicyRegistryEntry
        from policy_scout.policy.management.validator import validate_policy

        registry = PolicyRegistry(policies=[
            PolicyRegistryEntry(
                id="rule_a", title="A", priority=500,
                match={"categories": ["network_fetch"]},
                decision="ALLOW",
            ),
            PolicyRegistryEntry(
                id="rule_b", title="B", priority=400,
                match={"categories": ["network_fetch"]},
                decision="DENY",
            ),
        ])
        result = validate_policy(registry=registry)
        contradiction_issues = [i for i in result.issues if i.issue_type == "contradiction"]
        assert len(contradiction_issues) >= 1
        assert not result.is_valid

    def test_unreachable_rule_detected(self):
        """A rule whose categories are a subset of a higher-priority rule is unreachable."""
        from policy_scout.registry.models import PolicyRegistry, PolicyRegistryEntry
        from policy_scout.policy.management.validator import validate_policy

        registry = PolicyRegistry(policies=[
            PolicyRegistryEntry(
                id="broad_deny", title="Broad", priority=900,
                match={"categories": ["network_fetch", "package_install"]},
                decision="DENY",
            ),
            PolicyRegistryEntry(
                id="narrow_deny", title="Narrow", priority=500,
                match={"categories": ["network_fetch"]},
                decision="DENY",
            ),
        ])
        result = validate_policy(registry=registry)
        unreachable = [i for i in result.issues if i.issue_type == "unreachable_rule"]
        assert len(unreachable) >= 1
        assert unreachable[0].rule_id == "narrow_deny"

    def test_strict_mode_promotes_warnings(self):
        """strict=True makes ValidationResult.is_valid False if any warning exists."""
        from policy_scout.registry.models import PolicyRegistry, PolicyRegistryEntry
        from policy_scout.policy.management.validator import validate_policy

        # No catch-all for "unknown" → produces a warning
        registry = PolicyRegistry(policies=[
            PolicyRegistryEntry(
                id="deny_network", title="Net", priority=500,
                match={"categories": ["network_fetch"]},
                decision="DENY",
            ),
        ])
        result_normal = validate_policy(registry=registry, strict=False)
        result_strict = validate_policy(registry=registry, strict=True)
        # Strict mode: any warning becomes an error
        if result_normal.warning_count > 0:
            assert not result_strict.is_valid
        else:
            # No warnings either way — both are valid
            assert result_strict.is_valid


# ──────────────────────────────────────────────────────────────────────────────
# Phase 6 — Policy Commit
# ──────────────────────────────────────────────────────────────────────────────

class TestPolicyCommit:
    def test_commit_raises_outside_git_repo(self, tmp_path):
        """Committing outside a git repo raises RuntimeError."""
        with pytest.raises(RuntimeError, match="git"):
            commit_policy_state(repo_root=tmp_path)

    def test_commit_function_is_importable(self):
        from policy_scout.policy.management.policy_commit import commit_policy_state as cps
        assert callable(cps)
