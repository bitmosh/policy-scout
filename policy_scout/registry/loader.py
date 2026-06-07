"""Registry loading from YAML files."""

import yaml
from pathlib import Path
from typing import Optional
from .models import (
    CommandRegistry,
    PolicyRegistry,
    CommandRegistryEntry,
    PolicyRegistryEntry,
)
from .validator import RegistryValidator
from ..core.errors import RegistryValidationError


class RegistryLoader:
    """Loads and validates registries from YAML files."""

    def __init__(self, data_dir: Optional[Path] = None):
        """Initialize loader with data directory."""
        if data_dir is None:
            # Default to policy_scout/data
            self.data_dir = Path(__file__).parent.parent / "data"
        else:
            self.data_dir = data_dir

        self.validator = RegistryValidator()
        self._command_registry: Optional[CommandRegistry] = None
        self._policy_registry: Optional[PolicyRegistry] = None

    def load_command_registry(self, path: Optional[Path] = None) -> CommandRegistry:
        """Load command registry from YAML file."""
        if path is None:
            path = self.data_dir / "command_registry.yaml"

        if not path.exists():
            raise FileNotFoundError(f"Command registry not found: {path}")

        with open(path, "r") as f:
            data = yaml.safe_load(f)

        # Validate YAML structure
        if data is None:
            raise RegistryValidationError(f"Command registry file is empty: {path}")
        if not isinstance(data, dict):
            raise RegistryValidationError(
                f"Command registry must be a dict, got {type(data).__name__}: {path}"
            )
        if "commands" not in data:
            raise RegistryValidationError(
                f"Command registry missing required key 'commands': {path}"
            )
        if not isinstance(data["commands"], list):
            raise RegistryValidationError(
                f"Command registry 'commands' must be a list, got {type(data['commands']).__name__}: {path}"
            )

        # Parse entries
        registry = CommandRegistry(version=data.get("version", 1))
        for cmd_data in data.get("commands", []):
            # Validate required fields before dataclass construction
            if "id" not in cmd_data:
                raise RegistryValidationError(
                    f"Command entry missing required field 'id': {path}"
                )
            if "title" not in cmd_data:
                raise RegistryValidationError(
                    f"Command entry missing required field 'title' (id: {cmd_data.get('id', '<unknown>')}): {path}"
                )

            entry = CommandRegistryEntry(
                id=cmd_data["id"],
                title=cmd_data["title"],
                description=cmd_data.get("description", ""),
                match=cmd_data.get("match", {}),
                categories=cmd_data.get("categories", []),
                capabilities=cmd_data.get("capabilities", []),
                default_risk=cmd_data.get("default_risk", "R3"),
                recommended_controls=cmd_data.get("recommended_controls", []),
                version=cmd_data.get("version", 1),
                status=cmd_data.get("status", "active"),
            )
            registry.commands.append(entry)

        # Validate
        errors = self.validator.validate_command_registry(registry)
        if errors:
            raise RegistryValidationError(
                f"Command registry validation failed ({path}):\n" + "\n".join(errors)
            )

        self._command_registry = registry
        return registry

    def load_policy_registry(self, path: Optional[Path] = None) -> PolicyRegistry:
        """Load policy registry from YAML file."""
        if path is None:
            path = self.data_dir / "default_policy.yaml"

        if not path.exists():
            raise FileNotFoundError(f"Policy registry not found: {path}")

        with open(path, "r") as f:
            data = yaml.safe_load(f)

        # Validate YAML structure
        if data is None:
            raise RegistryValidationError(f"Policy registry file is empty: {path}")
        if not isinstance(data, dict):
            raise RegistryValidationError(
                f"Policy registry must be a dict, got {type(data).__name__}: {path}"
            )
        if "policies" not in data:
            raise RegistryValidationError(
                f"Policy registry missing required key 'policies': {path}"
            )
        if not isinstance(data["policies"], list):
            raise RegistryValidationError(
                f"Policy registry 'policies' must be a list, got {type(data['policies']).__name__}: {path}"
            )

        # Parse entries
        registry = PolicyRegistry(version=data.get("version", 1))
        for policy_data in data.get("policies", []):
            # Validate required fields before dataclass construction
            if "id" not in policy_data:
                raise RegistryValidationError(
                    f"Policy entry missing required field 'id': {path}"
                )
            if "title" not in policy_data:
                raise RegistryValidationError(
                    f"Policy entry missing required field 'title' (id: {policy_data.get('id', '<unknown>')}): {path}"
                )

            entry = PolicyRegistryEntry(
                id=policy_data["id"],
                title=policy_data["title"],
                priority=policy_data["priority"],
                match=policy_data.get("match", {}),
                decision=policy_data.get("decision", "DENY"),
                reasons=policy_data.get("reasons", []),
                recommended_next_action=policy_data.get("recommended_next_action"),
                version=policy_data.get("version", 1),
                status=policy_data.get("status", "active"),
            )
            registry.policies.append(entry)

        # Validate
        errors = self.validator.validate_policy_registry(registry)
        if errors:
            raise RegistryValidationError(
                f"Policy registry validation failed ({path}):\n" + "\n".join(errors)
            )

        self._policy_registry = registry
        return registry

    def load_all(self) -> tuple[CommandRegistry, PolicyRegistry]:
        """Load both command and policy registries."""
        command_registry = self.load_command_registry()
        policy_registry = self.load_policy_registry()
        return command_registry, policy_registry

    @property
    def command_registry(self) -> CommandRegistry:
        """Get command registry, loading if necessary."""
        if self._command_registry is None:
            return self.load_command_registry()
        return self._command_registry

    @property
    def policy_registry(self) -> PolicyRegistry:
        """Get policy registry, loading if necessary."""
        if self._policy_registry is None:
            return self.load_policy_registry()
        return self._policy_registry
