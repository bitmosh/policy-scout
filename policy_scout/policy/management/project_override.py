# SPDX-License-Identifier: Apache-2.0
"""Per-project policy override: discovery, loading, and tighten-only validation."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]


# Decisions that may appear in project additional_rules / strengthen_to.
# ALLOW and ALLOW_LOGGED are forbidden — project overrides may only tighten.
ALLOWED_OVERRIDE_DECISIONS = frozenset({
    "REQUIRE_APPROVAL",
    "SANDBOX_FIRST",
    "DENY",
    "DENY_AND_ALERT",
})

# Mode strictness ordering (lower index = less strict).
_MODE_ORDER = ["lenient", "balanced", "strict", "paranoid"]


class PolicyOverrideViolation(ValueError):
    """Raised when a project override attempts to loosen global policy."""


@dataclass
class OverrideRule:
    """A single additional rule declared in a project override."""

    id: str
    decision: str
    match: dict = field(default_factory=dict)
    reasons: list = field(default_factory=list)
    description: str = ""
    priority: int = 800  # default: fires after critical safety rules but before most global rules

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "decision": self.decision,
            "match": self.match,
            "reasons": self.reasons,
            "description": self.description,
            "priority": self.priority,
        }


@dataclass
class DecisionStrengthening:
    """Strengthen an existing global rule's decision for this project."""

    rule_id: str
    strengthen_to: str

    def to_dict(self) -> dict:
        return {"rule_id": self.rule_id, "strengthen_to": self.strengthen_to}


@dataclass
class ProjectOverride:
    """Parsed and validated contents of a .policy-scout.yaml file."""

    config_path: Path
    version: str = ""
    mode: Optional[str] = None          # if set, must be >= effective global mode
    additional_rules: list = field(default_factory=list)   # list[OverrideRule]
    override_decisions: list = field(default_factory=list) # list[DecisionStrengthening]
    intel_remote: Optional[bool] = None
    scan_pre_commit: Optional[bool] = None
    raw: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, raw: dict, config_path: Path) -> "ProjectOverride":
        additional_rules = []
        for r in raw.get("additional_rules", []):
            additional_rules.append(OverrideRule(
                id=r.get("id", ""),
                decision=r.get("decision", ""),
                match=r.get("match", {}),
                reasons=r.get("reasons", []),
                description=r.get("description", ""),
                priority=int(r.get("priority", 800)),
            ))

        override_decisions = []
        for o in raw.get("override_decisions", []):
            override_decisions.append(DecisionStrengthening(
                rule_id=o.get("rule_id", ""),
                strengthen_to=o.get("strengthen_to", ""),
            ))

        intel = raw.get("intel", {}) or {}
        scan = raw.get("scan", {}) or {}

        return cls(
            config_path=config_path,
            version=str(raw.get("version", "")),
            mode=raw.get("mode"),
            additional_rules=additional_rules,
            override_decisions=override_decisions,
            intel_remote=intel.get("remote"),
            scan_pre_commit=scan.get("pre_commit"),
            raw=raw,
        )

    def to_dict(self) -> dict:
        return {
            "config_path": str(self.config_path),
            "version": self.version,
            "mode": self.mode,
            "additional_rules": [r.to_dict() for r in self.additional_rules],
            "override_decisions": [o.to_dict() for o in self.override_decisions],
            "intel_remote": self.intel_remote,
            "scan_pre_commit": self.scan_pre_commit,
        }


@dataclass
class EffectivePolicy:
    """The merged result of all config layers for a given evaluation context."""

    layers: list                     # e.g. ["builtin:1.3.0", "global:", "project:v2"]
    effective_version: str           # computed from layer versions
    project_config_path: Optional[Path] = None
    mode: str = "balanced"
    project_override: Optional[ProjectOverride] = None

    def to_dict(self) -> dict:
        return {
            "layers": self.layers,
            "effective_version": self.effective_version,
            "mode": self.mode,
            "project_config_path": str(self.project_config_path) if self.project_config_path else None,
        }


def find_project_config(cwd: Optional[Path] = None) -> Optional[Path]:
    """Walk up from cwd looking for .policy-scout.yaml, stopping at git root."""
    current = (cwd or Path.cwd()).resolve()
    while True:
        candidate = current / ".policy-scout.yaml"
        if candidate.exists():
            return candidate
        # Stop at git root — don't escape into parent repos
        if (current / ".git").exists():
            return None
        parent = current.parent
        if parent == current:
            return None  # filesystem root
        current = parent


def _validate_tighten_only(override: ProjectOverride) -> None:
    """Raise PolicyOverrideViolation if any part of the override loosens policy."""
    for rule in override.additional_rules:
        if not rule.id:
            raise PolicyOverrideViolation(
                f"additional_rules entry is missing required 'id' field"
            )
        if rule.decision not in ALLOWED_OVERRIDE_DECISIONS:
            raise PolicyOverrideViolation(
                f"Rule '{rule.id}' has decision '{rule.decision}' — project overrides "
                f"may not use ALLOW or ALLOW_LOGGED (only: {sorted(ALLOWED_OVERRIDE_DECISIONS)})"
            )

    for strengthening in override.override_decisions:
        if not strengthening.rule_id:
            raise PolicyOverrideViolation(
                "override_decisions entry is missing required 'rule_id' field"
            )
        if strengthening.strengthen_to not in ALLOWED_OVERRIDE_DECISIONS:
            raise PolicyOverrideViolation(
                f"override_decisions entry for '{strengthening.rule_id}' has "
                f"strengthen_to='{strengthening.strengthen_to}' — must be one of "
                f"{sorted(ALLOWED_OVERRIDE_DECISIONS)}"
            )

    if override.mode is not None and override.mode not in _MODE_ORDER:
        raise PolicyOverrideViolation(
            f"mode '{override.mode}' is not valid — must be one of {_MODE_ORDER}"
        )


def load_project_override(cwd: Optional[Path] = None) -> Optional[ProjectOverride]:
    """
    Discover and load the project override for the given working directory.

    Returns None if no .policy-scout.yaml is found.
    Raises PolicyOverrideViolation if the config attempts to loosen policy.
    Raises RuntimeError if PyYAML is not available or the file is malformed.
    """
    config_path = find_project_config(cwd)
    if config_path is None:
        return None

    if yaml is None:
        raise RuntimeError(
            "PyYAML is required to load .policy-scout.yaml — install pyyaml"
        )

    try:
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        raise RuntimeError(
            f"Failed to parse {config_path}: {exc}"
        ) from exc

    if not isinstance(raw, dict):
        raise RuntimeError(
            f"{config_path} must be a YAML mapping, got {type(raw).__name__}"
        )

    override = ProjectOverride.from_dict(raw, config_path=config_path)
    _validate_tighten_only(override)
    return override


