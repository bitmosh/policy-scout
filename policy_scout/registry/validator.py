# SPDX-License-Identifier: Apache-2.0
"""Registry validation."""

import re
from typing import List
from .models import (
    CommandRegistryEntry,
    PolicyRegistryEntry,
    CommandRegistry,
    PolicyRegistry,
)
from .schemas import (
    VALID_DECISIONS,
    VALID_CATEGORIES,
    VALID_CAPABILITIES,
    VALID_STATUS,
    VALID_RISK_LEVELS,
    VALID_RECOMMENDED_CONTROLS,
    PRIORITY_MIN,
    PRIORITY_MAX,
    VERSION_MIN,
)


class RegistryValidator:
    """Validates registry entries."""

    def validate_command_registry(self, registry: CommandRegistry) -> List[str]:
        """Validate a command registry and return list of errors."""
        errors = []

        # Check for duplicate IDs
        ids = set()
        for entry in registry.commands:
            if entry.id in ids:
                errors.append(f"Duplicate command registry entry ID: {entry.id}")
            ids.add(entry.id)

        # Validate each entry
        for entry in registry.commands:
            entry_errors = self.validate_command_entry(entry)
            errors.extend(entry_errors)

        return errors

    def validate_command_entry(self, entry: CommandRegistryEntry) -> List[str]:
        """Validate a single command registry entry."""
        errors = []

        # Check required fields
        if not entry.id:
            errors.append("Command entry missing required field: id")
        if not entry.title:
            errors.append(
                f"Command entry missing required field: id={entry.id or '<unknown>'}, title"
            )

        # Validate status
        if entry.status not in VALID_STATUS:
            errors.append(
                f"Invalid status '{entry.status}' for entry {entry.id}. Valid: {VALID_STATUS}"
            )

        # Validate categories
        for category in entry.categories:
            if category not in VALID_CATEGORIES:
                errors.append(
                    f"Invalid category '{category}' for entry {entry.id}. Valid: {VALID_CATEGORIES}"
                )

        # Validate capabilities
        for capability in entry.capabilities:
            if capability not in VALID_CAPABILITIES:
                errors.append(
                    f"Invalid capability '{capability}' for entry {entry.id}. Valid: {VALID_CAPABILITIES}"
                )

        # Validate default_risk
        if entry.default_risk not in VALID_RISK_LEVELS:
            errors.append(
                f"Invalid default_risk '{entry.default_risk}' for entry {entry.id}. Valid: {VALID_RISK_LEVELS}"
            )

        # Validate recommended_controls
        for control in entry.recommended_controls:
            if control not in VALID_RECOMMENDED_CONTROLS:
                errors.append(
                    f"Invalid recommended_control '{control}' for entry {entry.id}. Valid: {VALID_RECOMMENDED_CONTROLS}"
                )

        # Validate version
        if not isinstance(entry.version, int):
            errors.append(
                f"Invalid version type '{type(entry.version).__name__}' for entry {entry.id}. Must be int."
            )
        elif entry.version < VERSION_MIN:
            errors.append(
                f"Invalid version '{entry.version}' for entry {entry.id}. Must be >= {VERSION_MIN}."
            )

        # Validate regex pattern if present
        if "command_regex" in entry.match:
            try:
                re.compile(entry.match["command_regex"])
            except re.error as e:
                errors.append(f"Invalid regex pattern for entry {entry.id}: {e}")

        # Validate match block known keys
        VALID_MATCH_KEYS = {"command_regex"}
        for key in entry.match:
            if key not in VALID_MATCH_KEYS:
                errors.append(
                    f"Unknown key '{key}' in match block for entry {entry.id}. Valid: {VALID_MATCH_KEYS}"
                )

        return errors

    def validate_policy_registry(self, registry: PolicyRegistry) -> List[str]:
        """Validate a policy registry and return list of errors."""
        errors = []

        # Check for duplicate IDs
        ids = set()
        for entry in registry.policies:
            if entry.id in ids:
                errors.append(f"Duplicate policy registry entry ID: {entry.id}")
            ids.add(entry.id)

        # Validate each entry
        for entry in registry.policies:
            entry_errors = self.validate_policy_entry(entry)
            errors.extend(entry_errors)

        return errors

    def validate_policy_entry(self, entry: PolicyRegistryEntry) -> List[str]:
        """Validate a single policy registry entry."""
        errors = []

        # Check required fields
        if not entry.id:
            errors.append("Policy entry missing required field: id")
        if not entry.title:
            errors.append(
                f"Policy entry missing required field: id={entry.id or '<unknown>'}, title"
            )

        # Validate status
        if entry.status not in VALID_STATUS:
            errors.append(
                f"Invalid status '{entry.status}' for entry {entry.id}. Valid: {VALID_STATUS}"
            )

        # Validate decision
        if entry.decision not in VALID_DECISIONS:
            errors.append(
                f"Invalid decision '{entry.decision}' for entry {entry.id}. Valid: {VALID_DECISIONS}"
            )

        # Validate priority
        if not isinstance(entry.priority, int):
            errors.append(
                f"Invalid priority type '{type(entry.priority).__name__}' for entry {entry.id}. Must be int."
            )
        elif entry.priority < PRIORITY_MIN or entry.priority > PRIORITY_MAX:
            errors.append(
                f"Invalid priority '{entry.priority}' for entry {entry.id}. Must be {PRIORITY_MIN}-{PRIORITY_MAX}."
            )

        # Validate version
        if not isinstance(entry.version, int):
            errors.append(
                f"Invalid version type '{type(entry.version).__name__}' for entry {entry.id}. Must be int."
            )
        elif entry.version < VERSION_MIN:
            errors.append(
                f"Invalid version '{entry.version}' for entry {entry.id}. Must be >= {VERSION_MIN}."
            )

        # Validate categories in match
        if "categories" in entry.match:
            for category in entry.match["categories"]:
                if category not in VALID_CATEGORIES:
                    errors.append(
                        f"Invalid category '{category}' in match for entry {entry.id}. Valid: {VALID_CATEGORIES}"
                    )

        # Validate capabilities in match
        if "capabilities" in entry.match:
            for capability in entry.match["capabilities"]:
                if capability not in VALID_CAPABILITIES:
                    errors.append(
                        f"Invalid capability '{capability}' in match for entry {entry.id}. Valid: {VALID_CAPABILITIES}"
                    )

        # Validate exclude block using same rules as match
        if "exclude" in entry.match:
            exclude = entry.match["exclude"]
            if "categories" in exclude:
                for category in exclude["categories"]:
                    if category not in VALID_CATEGORIES:
                        errors.append(
                            f"Invalid category '{category}' in exclude for entry {entry.id}. Valid: {VALID_CATEGORIES}"
                        )
            if "capabilities" in exclude:
                for capability in exclude["capabilities"]:
                    if capability not in VALID_CAPABILITIES:
                        errors.append(
                            f"Invalid capability '{capability}' in exclude for entry {entry.id}. Valid: {VALID_CAPABILITIES}"
                        )

        # Validate regex pattern if present
        if "command_regex" in entry.match:
            try:
                re.compile(entry.match["command_regex"])
            except re.error as e:
                errors.append(f"Invalid regex pattern for entry {entry.id}: {e}")

        # Validate match/exclude block known keys
        VALID_MATCH_KEYS = {"categories", "capabilities", "command_regex"}
        VALID_EXCLUDE_KEYS = {"categories", "capabilities"}
        for key in entry.match:
            if key not in VALID_MATCH_KEYS and key != "exclude":
                errors.append(
                    f"Unknown key '{key}' in match block for entry {entry.id}. Valid: {VALID_MATCH_KEYS}"
                )
        if "exclude" in entry.match:
            for key in entry.match["exclude"]:
                if key not in VALID_EXCLUDE_KEYS:
                    errors.append(
                        f"Unknown key '{key}' in exclude block for entry {entry.id}. Valid: {VALID_EXCLUDE_KEYS}"
                    )

        return errors
