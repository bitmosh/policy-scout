# SPDX-License-Identifier: Apache-2.0
"""Tests for risk band derivation."""

from policy_scout.core.decision import derive_risk_band


def test_risk_band_low_0():
    """Test risk score 0 maps to low."""
    assert derive_risk_band(0) == "low"


def test_risk_band_low_1():
    """Test risk score 1 maps to low."""
    assert derive_risk_band(1) == "low"


def test_risk_band_low_2():
    """Test risk score 2 maps to low."""
    assert derive_risk_band(2) == "low"


def test_risk_band_medium_3():
    """Test risk score 3 maps to medium."""
    assert derive_risk_band(3) == "medium"


def test_risk_band_medium_4():
    """Test risk score 4 maps to medium."""
    assert derive_risk_band(4) == "medium"


def test_risk_band_high_5():
    """Test risk score 5 maps to high."""
    assert derive_risk_band(5) == "high"


def test_risk_band_high_6():
    """Test risk score 6 maps to high."""
    assert derive_risk_band(6) == "high"


def test_risk_band_high_7():
    """Test risk score 7 maps to high."""
    assert derive_risk_band(7) == "high"


def test_risk_band_critical_8():
    """Test risk score 8 maps to critical."""
    assert derive_risk_band(8) == "critical"


def test_risk_band_critical_9():
    """Test risk score 9 maps to critical."""
    assert derive_risk_band(9) == "critical"


def test_risk_band_critical_10():
    """Test risk score 10 maps to critical."""
    assert derive_risk_band(10) == "critical"


def test_risk_band_boundary_low_medium():
    """Test boundary between low and medium."""
    assert derive_risk_band(2) == "low"
    assert derive_risk_band(3) == "medium"


def test_risk_band_boundary_medium_high():
    """Test boundary between medium and high."""
    assert derive_risk_band(4) == "medium"
    assert derive_risk_band(5) == "high"


def test_risk_band_boundary_high_critical():
    """Test boundary between high and critical."""
    assert derive_risk_band(7) == "high"
    assert derive_risk_band(8) == "critical"
