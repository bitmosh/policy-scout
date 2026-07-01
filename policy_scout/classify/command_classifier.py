"""Command classifier for categorizing commands and detecting capabilities."""

import re
from dataclasses import dataclass, field
from typing import Any, Optional
from ..core.ids import generate_id
from ..registry.models import CommandRegistry, RegistryHit
from .shell_parser import ParseResult


@dataclass
class ClassificationResult:
    """Represents command classification."""

    classification_id: str = field(default_factory=lambda: generate_id("class"))
    request_id: str = ""
    command_family: str = "unknown"
    subcommand: str = ""
    categories: list[str] = field(default_factory=list)
    capabilities: list[str] = field(default_factory=list)
    classification_method: str = "pattern_match"
    confidence: float = 0.0
    structure: dict[str, Any] = field(default_factory=dict)
    registry_hits: list[dict[str, Any]] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "classification_id": self.classification_id,
            "request_id": self.request_id,
            "command_family": self.command_family,
            "subcommand": self.subcommand,
            "categories": self.categories,
            "capabilities": self.capabilities,
            "classification_method": self.classification_method,
            "confidence": self.confidence,
            "structure": self.structure,
            "registry_hits": self.registry_hits,
            "notes": self.notes,
        }


class CommandClassifier:
    """Classifies commands into categories and detects capabilities."""

    # Fallback patterns for things not in registry
    NETWORK_EXECUTE_PATTERNS = [
        (r"curl.*\|\s*(bash|sh|python|node)", "network_execute"),
        (r"wget.*\|\s*(bash|sh|python|node)", "network_execute"),
        (r"bash\s+-c.*\$\(curl", "network_execute"),  # bash -c "$(curl ...)"
        (r"bash\s+-c.*\$\(wget", "network_execute"),  # bash -c "$(wget ...)"
        (r"sh\s+-c.*\$\(curl", "network_execute"),
        (r"sh\s+-c.*\$\(wget", "network_execute"),
    ]

    NETWORK_FETCH_PATTERNS = [
        (r"^(curl|wget)\b", "network_fetch"),
    ]

    # Credential-adjacent patterns
    _CRED_READER = r"(?:cat|less|head|tail|more|bat)"
    CREDENTIAL_PATTERNS = [
        (rf"{_CRED_READER}\s+.*\.env", "credential_adjacent"),
        (rf"{_CRED_READER}\s+.*\.npmrc", "credential_adjacent"),
        (rf"{_CRED_READER}\s+.*\.ssh", "credential_adjacent"),
        (rf"{_CRED_READER}\s+.*id_rsa", "credential_adjacent"),
        (rf"{_CRED_READER}\s+.*id_ed25519", "credential_adjacent"),
        (rf"{_CRED_READER}\s+.*\.aws/credentials", "credential_adjacent"),
        (r"grep\s+-r\s+.*TOKEN", "credential_adjacent"),
        (r"grep\s+-r\s+.*SECRET", "credential_adjacent"),
    ]

    # Destructive patterns
    DESTRUCTIVE_SYSTEM_PATTERNS = [
        (r"rm\s+-rf\s+/", "destructive"),
        (r"rm\s+-rf\s+~", "destructive"),
        (r"rm\s+-rf\s+/\w+", "destructive"),  # rm -rf /usr, /etc, etc.
    ]

    DESTRUCTIVE_PROJECT_PATTERNS = [
        (r"rm\s+-rf\s+\w+", "destructive"),  # rm -rf node_modules, dist, build, etc.
        (r"find\s+.*\s+-delete\b", "destructive"),
        (r"git\s+clean\s+-fdx", "destructive"),
    ]

    # Safe read patterns
    SAFE_READ_PATTERNS = [
        (r"^(ls|pwd|git\s+status|git\s+log|git\s+diff)\b", "safe_read"),
        (
            r"^(cat|less|more|head|tail|bat)\s+[^\s~$\.>]",
            "safe_read",
        ),  # Not reading hidden/config files, no redirect
    ]

    # Test/inspection patterns
    INSPECTION_PATTERNS = [
        (r"^(npm|pnpm|yarn|bun)\s+test\b", "local_inspection"),
        (r"^(npm|pnpm|yarn|bun)\s+run\s+(lint|format|build)\b", "local_inspection"),
    ]

    # Shell script patterns
    SHELL_SCRIPT_PATTERNS = [
        (r"^(bash|sh|zsh)\s+-c\b", "shell_script"),
    ]

    def __init__(self, command_registry: Optional[CommandRegistry] = None):
        """Initialize classifier with optional command registry."""
        self.command_registry = command_registry

    def classify(
        self, parse_result: ParseResult, command: str, request_id: str = ""
    ) -> ClassificationResult:
        """Classify a command based on parse result and patterns."""
        result = ClassificationResult(request_id=request_id)
        result.structure = parse_result.structure

        # Extract command family and subcommand
        result.command_family = parse_result.primary_command
        if parse_result.args:
            result.subcommand = parse_result.args[0] if parse_result.args else ""

        # Reconstruct command without env assignments for registry matching
        # Use primary_command + args instead of original command
        normalized_command = " ".join(
            [parse_result.primary_command] + parse_result.args
        )

        # Try registry-based classification first
        if self.command_registry:
            self._classify_from_registry(normalized_command, result)

        # Apply fallback patterns for things not in registry (use original command for pattern matching)
        self._classify_credential_adjacent(command, result)
        self._classify_destructive(command, result)
        self._classify_network_execute(command, result)
        self._classify_network_fetch(command, result)
        self._classify_inspection(command, result)
        self._classify_safe_read(command, result)
        self._classify_redirect_write(command, result)
        self._classify_shell_script(command, result)

        # If no category matched, mark as unknown
        if not result.categories:
            result.categories = ["unknown"]
            result.confidence = 0.3
        else:
            result.confidence = 0.95

        # Assign capabilities based on categories
        result.capabilities = self._assign_capabilities(result.categories)

        # Add system-destructive capability for system-destructive commands
        self._add_system_destructive_capability(command, result)

        # Set classification method
        if result.registry_hits:
            result.classification_method = "registry_match"
        else:
            result.classification_method = "pattern_match"

        return result

    def _classify_from_registry(self, command: str, result: ClassificationResult):
        """Classify using command registry entries."""
        if not self.command_registry:
            return

        for entry in self.command_registry.commands:
            if entry.status != "active":
                continue

            # Check regex match
            if "command_regex" in entry.match:
                try:
                    if re.search(entry.match["command_regex"], command):
                        # Add categories from registry
                        for category in entry.categories:
                            if category not in result.categories:
                                result.categories.append(category)

                        # Add capabilities from registry
                        for capability in entry.capabilities:
                            if capability not in result.capabilities:
                                result.capabilities.append(capability)

                        # Record registry hit
                        hit = RegistryHit(
                            registry_name="command_registry",
                            entry_id=entry.id,
                            confidence=0.95,
                        )
                        result.registry_hits.append(hit.to_dict())

                        result.notes.append(f"Matched registry entry: {entry.id}")
                        result.confidence = 0.95
                except re.error:
                    # Invalid regex should have been caught by validation
                    pass

    def _classify_credential_adjacent(self, command: str, result: ClassificationResult):
        """Check for credential-adjacent patterns."""
        for pattern, category in self.CREDENTIAL_PATTERNS:
            if re.search(pattern, command):
                if category not in result.categories:
                    result.categories.append(category)
                result.notes.append("Command may access credential-adjacent files")

    def _classify_destructive(self, command: str, result: ClassificationResult):
        """Check for destructive patterns."""
        # Check system-destructive patterns first
        for pattern, category in self.DESTRUCTIVE_SYSTEM_PATTERNS:
            if re.search(pattern, command):
                if category not in result.categories:
                    result.categories.append(category)
                result.notes.append("Command has destructive system potential")
                return  # System destructive takes precedence

        # Check project-destructive patterns
        for pattern, category in self.DESTRUCTIVE_PROJECT_PATTERNS:
            if re.search(pattern, command):
                if category not in result.categories:
                    result.categories.append(category)
                result.notes.append("Command has destructive project potential")

    def _classify_network_execute(self, command: str, result: ClassificationResult):
        """Check for network-fetched shell execution."""
        for pattern, category in self.NETWORK_EXECUTE_PATTERNS:
            if re.search(pattern, command):
                if category not in result.categories:
                    result.categories.append(category)
                result.notes.append("Command fetches and executes remote content")

    def _classify_network_fetch(self, command: str, result: ClassificationResult):
        """Check for network fetch patterns."""
        for pattern, category in self.NETWORK_FETCH_PATTERNS:
            if re.search(pattern, command):
                if category not in result.categories:
                    result.categories.append(category)
                result.notes.append("Command fetches remote content")

    def _classify_inspection(self, command: str, result: ClassificationResult):
        """Check for inspection/test patterns."""
        for pattern, category in self.INSPECTION_PATTERNS:
            if re.search(pattern, command):
                if category not in result.categories:
                    result.categories.append(category)
                result.notes.append("Command inspects project state")

    def _classify_safe_read(self, command: str, result: ClassificationResult):
        """Check for safe read patterns."""
        for pattern, category in self.SAFE_READ_PATTERNS:
            if re.search(pattern, command):
                if category not in result.categories:
                    result.categories.append(category)
                result.notes.append("Command reads local data")

    def _classify_shell_script(self, command: str, result: ClassificationResult):
        """Check for shell script patterns."""
        for pattern, category in self.SHELL_SCRIPT_PATTERNS:
            if re.search(pattern, command):
                if category not in result.categories:
                    result.categories.append(category)
                result.notes.append("Command executes shell script")

    def _classify_redirect_write(self, command: str, result: ClassificationResult):
        """Check for redirect write patterns.

        If a command has a redirect (>) and is not already classified as destructive,
        it should be classified as project_write to reflect write risk.
        """
        if result.structure.get("has_redirect") and ">" in command:
            # Check if it's a write redirect (>, not <)
            if ">" in command and "<" not in command.split(">")[0]:
                # Only add if not already destructive (destructive takes precedence)
                if (
                    "destructive" not in result.categories
                    and "project_write" not in result.categories
                ):
                    result.categories.append("project_write")
                    result.notes.append("Command writes via redirect")

    def _assign_capabilities(self, categories: list[str]) -> list[str]:
        """Assign capabilities based on categories."""
        capabilities = []

        capability_map = {
            "safe_read": ["filesystem.read"],
            "local_inspection": ["filesystem.read", "process.inspect"],
            "package_install": [
                "network.fetch",
                "filesystem.project_write",
                "package.install",
                "lifecycle.execute_possible",
            ],
            "package_execute": [
                "network.fetch",
                "package.execute",
                "shell.execute",
                "filesystem.project_write_possible",
            ],
            "network_fetch": ["network.fetch", "filesystem.write_possible"],
            "network_execute": [
                "network.fetch",
                "shell.execute",
                "system.mutation_possible",
                "credential.access_possible",
            ],
            "credential_adjacent": ["filesystem.read", "credential.access_possible"],
            "destructive": [
                "destructive.mutation",
                "filesystem.project_write",
            ],
            "shell_script": ["shell.execute"],
            "project_write": ["filesystem.read", "filesystem.project_write"],
            "unknown": [],
        }

        for category in categories:
            if category in capability_map:
                for cap in capability_map[category]:
                    if cap not in capabilities:
                        capabilities.append(cap)

        return capabilities

    def _add_system_destructive_capability(
        self, command: str, result: ClassificationResult
    ):
        """Add system_write capability for system-destructive commands."""
        for pattern, category in self.DESTRUCTIVE_SYSTEM_PATTERNS:
            if re.search(pattern, command):
                if "filesystem.system_write" not in result.capabilities:
                    result.capabilities.append("filesystem.system_write")
                break
