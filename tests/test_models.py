# SPDX-License-Identifier: Apache-2.0
"""Tests for core data models."""

import pytest
from policy_scout.core.request import Actor, CommandRequest
from policy_scout.core.decision import RiskScore, PolicyDecision


def test_actor_creation():
    """Test Actor model creation."""
    actor = Actor(type="human", name="test_user")
    assert actor.type == "human"
    assert actor.name == "test_user"
    assert actor.trust_level == "unknown_actor"
    
    actor_dict = actor.to_dict()
    assert actor_dict["type"] == "human"
    assert actor_dict["name"] == "test_user"


def test_command_request_creation():
    """Test CommandRequest model creation."""
    actor = Actor(type="human", name="test_user")
    request = CommandRequest(
        actor=actor,
        command="ls",
        cwd="/home/user"
    )
    
    assert request.command == "ls"
    assert request.cwd == "/home/user"
    assert request.mode == "balanced"
    assert request.schema_version == 1
    
    request_dict = request.to_dict()
    assert request_dict["command"] == "ls"
    assert request_dict["mode"] == "balanced"


def test_risk_score_creation():
    """Test RiskScore model creation."""
    risk = RiskScore(
        risk_score=7,
        risk_band="high",
        components={"package_install": 2, "network_fetch": 1}
    )
    
    assert risk.risk_score == 7
    assert risk.risk_band == "high"
    assert risk.components["package_install"] == 2
    
    risk_dict = risk.to_dict()
    assert risk_dict["risk_score"] == 7
    assert risk_dict["risk_band"] == "high"


def test_policy_decision_creation():
    """Test PolicyDecision model creation."""
    decision = PolicyDecision(
        decision="SANDBOX_FIRST",
        risk_score=7,
        category="package_install",
        reasons=["Package installs may execute lifecycle scripts."]
    )
    
    assert decision.decision == "SANDBOX_FIRST"
    assert decision.risk_score == 7
    assert decision.category == "package_install"
    assert len(decision.reasons) == 1
    
    decision_dict = decision.to_dict()
    assert decision_dict["decision"] == "SANDBOX_FIRST"
    assert decision_dict["category"] == "package_install"


def test_decision_enum_values():
    """Test that only valid decision values are used."""
    valid_decisions = ["ALLOW", "ALLOW_LOGGED", "REQUIRE_APPROVAL", "SANDBOX_FIRST", "DENY", "DENY_AND_ALERT"]
    
    for decision in valid_decisions:
        dec = PolicyDecision(decision=decision)
        assert dec.decision == decision
