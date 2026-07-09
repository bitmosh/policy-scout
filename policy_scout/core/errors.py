# SPDX-License-Identifier: Apache-2.0
"""Policy Scout error types."""


class PolicyScoutError(Exception):
    """Base exception for Policy Scout errors."""
    pass


class RegistryValidationError(PolicyScoutError):
    """Raised when registry validation fails."""
    pass


class PolicyEngineError(PolicyScoutError):
    """Raised when policy engine fails."""
    pass


class ClassificationError(PolicyScoutError):
    """Raised when command classification fails."""
    pass
