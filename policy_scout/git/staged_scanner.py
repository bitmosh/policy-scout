# SPDX-License-Identifier: Apache-2.0
"""Staged-file security scan: secrets + sensitive file additions + CI workflow changes."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from ..scan.engine import SecretScanner, ScanSummary
from ..scan.git_scanner import _run_git


# Files that should never be committed
_SENSITIVE_FILE_PATTERNS = [
    ".env",
    ".env.local",
    ".env.production",
    ".env.development",
    "*.pem",
    "*.key",
    "id_rsa",
    "id_ed25519",
    "id_ecdsa",
    "*.pfx",
    "*.p12",
    "*.jks",
    "*.keystore",
    "credentials.json",
    "service-account.json",
    "gcloud-credentials.json",
    ".aws/credentials",
    ".ssh/id_rsa",
    ".netrc",
    "htpasswd",
    ".htpasswd",
]

# CI workflow directory patterns
_CI_WORKFLOW_PATHS = [
    ".github/workflows/",
    ".gitlab-ci.yml",
    ".circleci/",
    "Jenkinsfile",
    ".travis.yml",
    "azure-pipelines.yml",
    "bitbucket-pipelines.yml",
    ".woodpecker.yml",
]


@dataclass
class SensitiveFileWarning:
    """A sensitive file that was added to the git index."""

    path: str
    reason: str

    def to_dict(self) -> dict:
        return {"path": self.path, "reason": self.reason}


@dataclass
class StagedCheckResult:
    """Combined result of staged-file secret scan + sensitive file check."""

    secret_scan: Optional[ScanSummary] = None
    sensitive_files: list = field(default_factory=list)
    ci_workflow_changes: list = field(default_factory=list)
    errors: list = field(default_factory=list)

    @property
    def has_secrets(self) -> bool:
        return self.secret_scan is not None and self.secret_scan.finding_count > 0

    @property
    def has_sensitive_files(self) -> bool:
        return len(self.sensitive_files) > 0

    @property
    def has_ci_changes(self) -> bool:
        return len(self.ci_workflow_changes) > 0

    @property
    def is_clean(self) -> bool:
        return not self.has_secrets and not self.has_sensitive_files

    @property
    def severity_exit_code(self) -> int:
        secret_code = self.secret_scan.severity_exit_code if self.secret_scan else 0
        sensitive_code = 2 if self.has_sensitive_files else 0
        return max(secret_code, sensitive_code)

    def to_dict(self) -> dict:
        return {
            "has_secrets": self.has_secrets,
            "has_sensitive_files": self.has_sensitive_files,
            "has_ci_changes": self.has_ci_changes,
            "is_clean": self.is_clean,
            "severity_exit_code": self.severity_exit_code,
            "secret_scan": self.secret_scan.to_dict() if self.secret_scan else None,
            "sensitive_files": [w.to_dict() for w in self.sensitive_files],
            "ci_workflow_changes": self.ci_workflow_changes,
            "errors": self.errors,
        }


def _get_staged_file_list(repo_root: Optional[Path]) -> list[str]:
    """Return list of staged file paths (added/modified/renamed)."""
    rc, stdout, _ = _run_git(
        ["diff", "--cached", "--name-only", "--diff-filter=ACMR"],
        cwd=repo_root,
    )
    if rc != 0:
        return []
    return [f.strip() for f in stdout.splitlines() if f.strip()]


def _is_sensitive_file(path: str) -> Optional[str]:
    """Return a reason string if the path matches a sensitive file pattern, else None."""
    lower = path.lower()
    filename = lower.split("/")[-1]

    # Exact filename matches
    for pattern in _SENSITIVE_FILE_PATTERNS:
        if pattern.startswith("*"):
            # Extension match
            if filename.endswith(pattern[1:]):
                return f"Matches sensitive file pattern: {pattern}"
        elif lower.endswith(pattern.lower()):
            return f"Sensitive file: {pattern}"

    # .env prefix
    if filename.startswith(".env"):
        return "Environment file (.env*) should not be committed"

    return None


def _is_ci_workflow(path: str) -> bool:
    """Return True if the path is a CI workflow file."""
    for prefix in _CI_WORKFLOW_PATHS:
        if path.startswith(prefix) or path == prefix.rstrip("/"):
            return True
    return False


def scan_staged_full(
    repo_root: Optional[Path] = None,
    scanner: Optional[SecretScanner] = None,
) -> StagedCheckResult:
    """Run a full staged-file check: secrets + sensitive files + CI workflow changes."""
    result = StagedCheckResult()

    staged = _get_staged_file_list(repo_root)

    # Secret scan
    sc = scanner or SecretScanner()
    try:
        secret_summary = sc.scan_staged(repo_root=repo_root)
        result.secret_scan = secret_summary
    except Exception as e:
        result.errors.append(f"Secret scan error: {e}")

    # Sensitive file warnings
    for path in staged:
        reason = _is_sensitive_file(path)
        if reason:
            result.sensitive_files.append(SensitiveFileWarning(path=path, reason=reason))

    # CI workflow changes (informational — not blocking by default)
    for path in staged:
        if _is_ci_workflow(path):
            result.ci_workflow_changes.append(path)

    return result
