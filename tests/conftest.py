"""
Global test fixtures.

Key fixture: `isolate_policy_config` — prevents any real .policy-scout.yaml on
the developer's machine from leaking into tests. Once Phase 2 wires the project
override into PolicyEngine.evaluate(), every test that instantiates the engine
would otherwise inherit the repo-root config.

Tests that explicitly exercise the override loading (test_policy_management.py)
pass an explicit `cwd` argument and therefore bypass the patch entirely.
"""

import pytest
from unittest.mock import patch


@pytest.fixture(autouse=True)
def isolate_policy_config(request):
    """Patch find_project_config to return None during all test runs.

    Tests that exercise override loading directly must mark themselves with
    @pytest.mark.no_policy_isolation to opt out.
    """
    if request.node.get_closest_marker("no_policy_isolation"):
        yield
        return
    with patch(
        "policy_scout.policy.management.project_override.find_project_config",
        return_value=None,
    ):
        yield
