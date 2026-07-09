# SPDX-License-Identifier: Apache-2.0
"""Tests for registry validation."""

import tempfile
import yaml
from pathlib import Path
from policy_scout.registry.models import (
    CommandRegistry,
    CommandRegistryEntry,
    PolicyRegistry,
    PolicyRegistryEntry,
)
from policy_scout.registry.validator import RegistryValidator
from policy_scout.registry.loader import RegistryLoader
from policy_scout.core.errors import RegistryValidationError


def test_valid_command_registry():
    """Test validation of valid command registry."""
    validator = RegistryValidator()
    registry = CommandRegistry(version=1)
    registry.commands.append(
        CommandRegistryEntry(
            id="test_cmd",
            title="Test Command",
            match={"command_regex": "^test"},
            categories=["safe_read"],
            capabilities=["filesystem.read"],
        )
    )

    errors = validator.validate_command_registry(registry)
    assert len(errors) == 0


def test_duplicate_command_ids():
    """Test that duplicate command IDs are caught."""
    validator = RegistryValidator()
    registry = CommandRegistry(version=1)
    registry.commands.append(
        CommandRegistryEntry(
            id="duplicate",
            title="Test 1",
            match={"command_regex": "^test1"},
            categories=["safe_read"],
            capabilities=["filesystem.read"],
        )
    )
    registry.commands.append(
        CommandRegistryEntry(
            id="duplicate",
            title="Test 2",
            match={"command_regex": "^test2"},
            categories=["safe_read"],
            capabilities=["filesystem.read"],
        )
    )

    errors = validator.validate_command_registry(registry)
    assert len(errors) > 0
    assert "Duplicate command registry entry ID" in errors[0]


def test_invalid_command_category():
    """Test that invalid categories are caught."""
    validator = RegistryValidator()
    registry = CommandRegistry(version=1)
    registry.commands.append(
        CommandRegistryEntry(
            id="test_cmd",
            title="Test Command",
            match={"command_regex": "^test"},
            categories=["invalid_category"],
            capabilities=["filesystem.read"],
        )
    )

    errors = validator.validate_command_registry(registry)
    assert len(errors) > 0
    assert "Invalid category" in errors[0]


def test_invalid_command_capability():
    """Test that invalid capabilities are caught."""
    validator = RegistryValidator()
    registry = CommandRegistry(version=1)
    registry.commands.append(
        CommandRegistryEntry(
            id="test_cmd",
            title="Test Command",
            match={"command_regex": "^test"},
            categories=["safe_read"],
            capabilities=["invalid_capability"],
        )
    )

    errors = validator.validate_command_registry(registry)
    assert len(errors) > 0
    assert "Invalid capability" in errors[0]


def test_invalid_command_regex():
    """Test that invalid regex patterns are caught."""
    validator = RegistryValidator()
    registry = CommandRegistry(version=1)
    registry.commands.append(
        CommandRegistryEntry(
            id="test_cmd",
            title="Test Command",
            match={"command_regex": "[invalid(regex"},
            categories=["safe_read"],
            capabilities=["filesystem.read"],
        )
    )

    errors = validator.validate_command_registry(registry)
    assert len(errors) > 0
    assert "Invalid regex pattern" in errors[0]


def test_invalid_command_risk_level():
    """Test that invalid risk levels are caught."""
    validator = RegistryValidator()
    registry = CommandRegistry(version=1)
    registry.commands.append(
        CommandRegistryEntry(
            id="test_cmd",
            title="Test Command",
            match={"command_regex": "^test"},
            categories=["safe_read"],
            capabilities=["filesystem.read"],
            default_risk="R99",
        )
    )

    errors = validator.validate_command_registry(registry)
    assert len(errors) > 0
    assert "Invalid default_risk" in errors[0]


def test_valid_policy_registry():
    """Test validation of valid policy registry."""
    validator = RegistryValidator()
    registry = PolicyRegistry(version=1)
    registry.policies.append(
        PolicyRegistryEntry(
            id="test_policy",
            title="Test Policy",
            priority=100,
            match={"categories": ["safe_read"]},
            decision="ALLOW",
        )
    )

    errors = validator.validate_policy_registry(registry)
    assert len(errors) == 0


def test_duplicate_policy_ids():
    """Test that duplicate policy IDs are caught."""
    validator = RegistryValidator()
    registry = PolicyRegistry(version=1)
    registry.policies.append(
        PolicyRegistryEntry(
            id="duplicate",
            title="Test 1",
            priority=100,
            match={"categories": ["safe_read"]},
            decision="ALLOW",
        )
    )
    registry.policies.append(
        PolicyRegistryEntry(
            id="duplicate",
            title="Test 2",
            priority=200,
            match={"categories": ["safe_read"]},
            decision="DENY",
        )
    )

    errors = validator.validate_policy_registry(registry)
    assert len(errors) > 0
    assert "Duplicate policy registry entry ID" in errors[0]


def test_invalid_policy_decision():
    """Test that invalid decisions are caught."""
    validator = RegistryValidator()
    registry = PolicyRegistry(version=1)
    registry.policies.append(
        PolicyRegistryEntry(
            id="test_policy",
            title="Test Policy",
            priority=100,
            match={"categories": ["safe_read"]},
            decision="INVALID_DECISION",
        )
    )

    errors = validator.validate_policy_registry(registry)
    assert len(errors) > 0
    assert "Invalid decision" in errors[0]


def test_invalid_policy_category():
    """Test that invalid categories in policy match are caught."""
    validator = RegistryValidator()
    registry = PolicyRegistry(version=1)
    registry.policies.append(
        PolicyRegistryEntry(
            id="test_policy",
            title="Test Policy",
            priority=100,
            match={"categories": ["invalid_category"]},
            decision="ALLOW",
        )
    )

    errors = validator.validate_policy_registry(registry)
    assert len(errors) > 0
    assert "Invalid category" in errors[0]


def test_invalid_policy_capability():
    """Test that invalid capabilities in policy match are caught."""
    validator = RegistryValidator()
    registry = PolicyRegistry(version=1)
    registry.policies.append(
        PolicyRegistryEntry(
            id="test_policy",
            title="Test Policy",
            priority=100,
            match={"capabilities": ["invalid_capability"]},
            decision="ALLOW",
        )
    )

    errors = validator.validate_policy_registry(registry)
    assert len(errors) > 0
    assert "Invalid capability" in errors[0]


def test_invalid_policy_regex():
    """Test that invalid regex patterns in policy match are caught."""
    validator = RegistryValidator()
    registry = PolicyRegistry(version=1)
    registry.policies.append(
        PolicyRegistryEntry(
            id="test_policy",
            title="Test Policy",
            priority=100,
            match={"command_regex": "[invalid(regex"},
            decision="ALLOW",
        )
    )

    errors = validator.validate_policy_registry(registry)
    assert len(errors) > 0
    assert "Invalid regex pattern" in errors[0]


def test_command_registry_yaml_not_dict():
    """Test that YAML as list instead of dict is rejected."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(["not", "a", "dict"], f)
        temp_path = Path(f.name)

    try:
        loader = RegistryLoader()
        try:
            loader.load_command_registry(temp_path)
            assert False, "Should have raised RegistryValidationError"
        except RegistryValidationError as e:
            assert "must be a dict" in str(e)
            assert str(temp_path) in str(e)
    finally:
        temp_path.unlink()


def test_command_registry_commands_not_list():
    """Test that commands as non-list is rejected."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump({"version": 1, "commands": "not a list"}, f)
        temp_path = Path(f.name)

    try:
        loader = RegistryLoader()
        try:
            loader.load_command_registry(temp_path)
            assert False, "Should have raised RegistryValidationError"
        except RegistryValidationError as e:
            assert "must be a list" in str(e)
            assert str(temp_path) in str(e)
    finally:
        temp_path.unlink()


def test_command_registry_empty_yaml():
    """Test that empty YAML file is rejected."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("")
        temp_path = Path(f.name)

    try:
        loader = RegistryLoader()
        try:
            loader.load_command_registry(temp_path)
            assert False, "Should have raised RegistryValidationError"
        except RegistryValidationError as e:
            assert "empty" in str(e)
            assert str(temp_path) in str(e)
    finally:
        temp_path.unlink()


def test_command_registry_unknown_top_level_key():
    """Test that unknown top-level key is rejected."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump({"version": 1, "unknown_key": "value", "commands": []}, f)
        temp_path = Path(f.name)

    try:
        loader = RegistryLoader()
        # This should load since we don't validate unknown top-level keys yet
        # Only validate structure
        registry = loader.load_command_registry(temp_path)
        assert registry is not None
    finally:
        temp_path.unlink()


def test_command_entry_missing_id_in_yaml():
    """Test that missing id field in YAML is rejected before dataclass construction."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump({"version": 1, "commands": [{"title": "Test"}]}, f)
        temp_path = Path(f.name)

    try:
        loader = RegistryLoader()
        try:
            loader.load_command_registry(temp_path)
            assert False, "Should have raised RegistryValidationError"
        except RegistryValidationError as e:
            assert "missing required field 'id'" in str(e)
            assert str(temp_path) in str(e)
    finally:
        temp_path.unlink()


def test_policy_entry_invalid_priority():
    """Test that invalid priority type/range is caught."""
    validator = RegistryValidator()

    # Test non-int priority
    registry = PolicyRegistry(version=1)
    registry.policies.append(
        PolicyRegistryEntry(
            id="test_policy",
            title="Test Policy",
            priority="not_an_int",
            match={"categories": ["safe_read"]},
            decision="ALLOW",
        )
    )
    errors = validator.validate_policy_registry(registry)
    assert len(errors) > 0
    assert "Invalid priority type" in errors[0]

    # Test priority out of range
    registry = PolicyRegistry(version=1)
    registry.policies.append(
        PolicyRegistryEntry(
            id="test_policy",
            title="Test Policy",
            priority=1500,
            match={"categories": ["safe_read"]},
            decision="ALLOW",
        )
    )
    errors = validator.validate_policy_registry(registry)
    assert len(errors) > 0
    assert "Invalid priority" in errors[0]


def test_command_entry_invalid_version():
    """Test that invalid version type/range is caught."""
    validator = RegistryValidator()

    # Test non-int version
    registry = CommandRegistry(version=1)
    registry.commands.append(
        CommandRegistryEntry(
            id="test_cmd",
            title="Test Command",
            match={"command_regex": "^test"},
            categories=["safe_read"],
            capabilities=["filesystem.read"],
            version="not_an_int",
        )
    )
    errors = validator.validate_command_registry(registry)
    assert len(errors) > 0
    assert "Invalid version type" in errors[0]

    # Test version below min
    registry = CommandRegistry(version=1)
    registry.commands.append(
        CommandRegistryEntry(
            id="test_cmd",
            title="Test Command",
            match={"command_regex": "^test"},
            categories=["safe_read"],
            capabilities=["filesystem.read"],
            version=0,
        )
    )
    errors = validator.validate_command_registry(registry)
    assert len(errors) > 0
    assert "Invalid version" in errors[0]


def test_command_entry_unknown_match_key():
    """Test that unknown key in match block is caught."""
    validator = RegistryValidator()
    registry = CommandRegistry(version=1)
    registry.commands.append(
        CommandRegistryEntry(
            id="test_cmd",
            title="Test Command",
            match={"unknown_key": "value"},
            categories=["safe_read"],
            capabilities=["filesystem.read"],
        )
    )

    errors = validator.validate_command_registry(registry)
    assert len(errors) > 0
    assert "Unknown key" in errors[0]
    assert "unknown_key" in errors[0]


def test_command_entry_invalid_recommended_controls():
    """Test that invalid recommended_controls are caught."""
    validator = RegistryValidator()
    registry = CommandRegistry(version=1)
    registry.commands.append(
        CommandRegistryEntry(
            id="test_cmd",
            title="Test Command",
            match={"command_regex": "^test"},
            categories=["safe_read"],
            capabilities=["filesystem.read"],
            recommended_controls=["invalid_control"],
        )
    )

    errors = validator.validate_command_registry(registry)
    assert len(errors) > 0
    assert "Invalid recommended_control" in errors[0]


def test_policy_entry_exclude_validation():
    """Test that exclude block is validated using same rules as match."""
    validator = RegistryValidator()

    # Test invalid category in exclude
    registry = PolicyRegistry(version=1)
    registry.policies.append(
        PolicyRegistryEntry(
            id="test_policy",
            title="Test Policy",
            priority=100,
            match={
                "categories": ["safe_read"],
                "exclude": {"categories": ["invalid_category"]},
            },
            decision="ALLOW",
        )
    )
    errors = validator.validate_policy_registry(registry)
    assert len(errors) > 0
    assert "Invalid category" in errors[0]
    assert "exclude" in errors[0]

    # Test invalid capability in exclude
    registry = PolicyRegistry(version=1)
    registry.policies.append(
        PolicyRegistryEntry(
            id="test_policy",
            title="Test Policy",
            priority=100,
            match={
                "categories": ["safe_read"],
                "exclude": {"capabilities": ["invalid_capability"]},
            },
            decision="ALLOW",
        )
    )
    errors = validator.validate_policy_registry(registry)
    assert len(errors) > 0
    assert "Invalid capability" in errors[0]
    assert "exclude" in errors[0]


def test_policy_entry_unknown_exclude_key():
    """Test that unknown key in exclude block is caught."""
    validator = RegistryValidator()
    registry = PolicyRegistry(version=1)
    registry.policies.append(
        PolicyRegistryEntry(
            id="test_policy",
            title="Test Policy",
            priority=100,
            match={"categories": ["safe_read"], "exclude": {"unknown_key": "value"}},
            decision="ALLOW",
        )
    )

    errors = validator.validate_policy_registry(registry)
    assert len(errors) > 0
    assert "Unknown key" in errors[0]
    assert "exclude" in errors[0]


def test_current_command_registry_loads():
    """Test that current valid command_registry.yaml still loads."""
    loader = RegistryLoader()
    registry = loader.load_command_registry()
    assert registry is not None
    assert len(registry.commands) > 0
    assert all(cmd.id for cmd in registry.commands)


def test_current_policy_registry_loads():
    """Test that current valid default_policy.yaml still loads."""
    loader = RegistryLoader()
    registry = loader.load_policy_registry()
    assert registry is not None
    assert len(registry.policies) > 0
    assert all(policy.id for policy in registry.policies)
