"""Shell command parser for basic structure detection."""

import re
import shlex
from dataclasses import dataclass, field
from ..core.ids import generate_id


@dataclass
class ParseResult:
    """Represents parsed shell structure."""

    parse_id: str = field(default_factory=lambda: generate_id("parse"))
    request_id: str = ""
    success: bool = True
    confidence: float = 1.0
    tokens: list = field(default_factory=list)
    primary_command: str = ""
    args: list = field(default_factory=list)
    structure: dict = field(default_factory=dict)
    warnings: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "parse_id": self.parse_id,
            "request_id": self.request_id,
            "success": self.success,
            "confidence": self.confidence,
            "tokens": self.tokens,
            "primary_command": self.primary_command,
            "args": self.args,
            "structure": self.structure,
            "warnings": self.warnings,
        }


class ShellParser:
    """Parses shell commands to detect structure and extract tokens."""

    def parse(self, command: str, request_id: str = "") -> ParseResult:
        """Parse a shell command and return structured information."""
        result = ParseResult(request_id=request_id)

        try:
            # Strip leading environment variable assignments
            # e.g., "VAR=value npm install" -> "npm install"
            stripped_command = self._strip_env_assignments(command)

            # Try to tokenize using shlex
            tokens = shlex.split(stripped_command)
            result.tokens = tokens

            if tokens:
                result.primary_command = tokens[0]
                result.args = tokens[1:]

            # Detect structural features (use original command for structure detection)
            result.structure = self._detect_structure(command)

            # Calculate confidence based on complexity
            result.confidence = self._calculate_confidence(result.structure)

        except (ValueError, shlex.Error) as e:
            result.success = False
            result.confidence = 0.3
            result.warnings.append(f"Parse error: {e}")
            # Fallback: simple split
            tokens = command.split()
            result.tokens = tokens
            if tokens:
                result.primary_command = tokens[0]
                result.args = tokens[1:]

        return result

    def _strip_env_assignments(self, command: str) -> str:
        """Strip leading environment variable assignments from command.

        Examples:
            "VAR=value npm install" -> "npm install"
            "FOO=bar BAZ=qux command" -> "command"
            "npm install" -> "npm install"
        """
        # Match pattern: KEY=value (possibly quoted) at start
        # Continue stripping until we hit a non-assignment token
        parts = command.split()
        i = 0
        while i < len(parts):
            part = parts[i]
            # Check if this looks like an env assignment
            if "=" in part and not part.startswith("-"):
                # It's an env assignment, skip it
                i += 1
            else:
                # Not an env assignment, stop here
                break

        # Return the remaining parts
        if i < len(parts):
            return " ".join(parts[i:])
        return command

    def _detect_structure(self, command: str) -> dict:
        """Detect shell structural features."""
        structure = {
            "has_pipe": False,
            "has_redirect": False,
            "has_chain_operator": False,
            "has_subshell": False,
            "has_command_substitution": False,
            "has_background_execution": False,
            "shell_complexity": 1,
        }

        # Pipe detection
        if "|" in command:
            structure["has_pipe"] = True
            structure["shell_complexity"] += 2

        # Redirect detection
        if re.search(r"[<>]", command):
            structure["has_redirect"] = True
            structure["shell_complexity"] += 1

        # Chain operators (&&, ||, ;)
        if re.search(r"(&&|\|\|;)", command):
            structure["has_chain_operator"] = True
            structure["shell_complexity"] += 2

        # Subshell detection
        if re.search(r"\([^)]*\)", command):
            structure["has_subshell"] = True
            structure["shell_complexity"] += 2

        # Command substitution $(...) or `...`
        if re.search(r"\$\([^)]*\)|`[^`]*`", command):
            structure["has_command_substitution"] = True
            structure["shell_complexity"] += 2

        # Background execution &
        if command.rstrip().endswith("&"):
            structure["has_background_execution"] = True
            structure["shell_complexity"] += 1

        return structure

    def _calculate_confidence(self, structure: dict) -> float:
        """Calculate parse confidence based on shell complexity."""
        complexity = structure.get("shell_complexity", 1)

        # Higher complexity = lower confidence
        if complexity <= 1:
            return 1.0
        elif complexity <= 3:
            return 0.9
        elif complexity <= 5:
            return 0.7
        elif complexity <= 7:
            return 0.5
        else:
            return 0.3
