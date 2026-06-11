# Implementation Plan — Gap 12: Git Integration

## Problem
Policy Scout sweeps the filesystem but is blind to git events — the most security-relevant moments in a developer's day. Staging a `.env` file, modifying a CI workflow, force-pushing, adding a lockfile entry from an unexpected source — none of these trigger Policy Scout in its current form.

## Goal
Pre-commit hook that scans staged changes (secrets + injection patterns + CI modifications), sweep enhancements that incorporate git status, and a lockfile tamper detection check via git diff.

---

## New Module: `policy_scout/git/`

```
policy_scout/git/
├── __init__.py
├── hooks.py            # hook installer / uninstaller
├── staged_scanner.py   # scan staged diff for security issues
├── history_scanner.py  # scan git log for secrets + risky patterns
├── lockfile_diff.py    # detect lockfile tampered without package.json change
└── context.py          # git repo detection + metadata
```

---

## Implementation Approach

### Step 1 — Git Context (`context.py`)

Every git operation needs to know it's in a valid git repo:

```python
@dataclass
class GitContext:
    repo_root: Path
    current_branch: str
    is_detached_head: bool
    has_staged_changes: bool
    has_unstaged_changes: bool

def get_git_context(cwd: Path | None = None) -> GitContext | None:
    """Return GitContext if in a git repo, None otherwise."""
    cwd = cwd or Path.cwd()
    try:
        root = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=str(cwd), capture_output=True, text=True, check=True
        ).stdout.strip()
        branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=root, capture_output=True, text=True, check=True
        ).stdout.strip()
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=root, capture_output=True, text=True, check=True
        ).stdout
        return GitContext(
            repo_root=Path(root),
            current_branch=branch,
            is_detached_head=(branch == "HEAD"),
            has_staged_changes=any(line[:2].strip() == '' and line[0] != '?' for line in status.splitlines()),
            has_unstaged_changes=any(line[1] != ' ' for line in status.splitlines()),
        )
    except subprocess.CalledProcessError:
        return None
```

### Step 2 — Staged Scanner (`staged_scanner.py`)

Parse `git diff --cached` and scan added lines for:
1. Secrets (via the scan engine from Gap 4)
2. Prompt injection patterns (via Gap 7's analyzer)
3. Sensitive file additions (`.env`, `*_rsa`, `*.pem`)
4. CI workflow modifications

```python
@dataclass
class StagedFinding:
    severity: str
    category: str
    file: str
    line: int
    description: str
    evidence: str        # redacted

def scan_staged_changes(cwd: Path | None = None) -> list[StagedFinding]:
    diff = subprocess.run(
        ["git", "diff", "--cached", "--unified=0", "--name-status"],
        cwd=str(cwd or Path.cwd()),
        capture_output=True, text=True, check=True
    ).stdout

    # Also get the actual diff content for scanning
    diff_content = subprocess.run(
        ["git", "diff", "--cached", "--unified=0"],
        cwd=str(cwd or Path.cwd()),
        capture_output=True, text=True, check=True
    ).stdout

    findings = []
    findings.extend(_check_sensitive_file_additions(diff))
    findings.extend(_scan_added_lines_for_secrets(diff_content))
    findings.extend(_scan_ci_workflow_modifications(diff))
    findings.extend(_check_lockfile_package_mismatch(diff))

    return findings

def _check_sensitive_file_additions(name_status_diff: str) -> list[StagedFinding]:
    SENSITIVE_PATTERNS = [
        (r'\.env$', 'critical', 'Environment file staged for commit'),
        (r'\.env\.\w+$', 'high', 'Environment override file staged for commit'),
        (r'_rsa$', 'critical', 'SSH private key staged for commit'),
        (r'_ecdsa$', 'critical', 'SSH private key staged for commit'),
        (r'_ed25519$', 'critical', 'SSH private key staged for commit'),
        (r'\.pem$', 'critical', 'PEM-format key/certificate staged for commit'),
        (r'\.p12$', 'critical', 'PKCS#12 keystore staged for commit'),
        (r'\.pfx$', 'critical', 'PKCS#12 keystore staged for commit'),
        (r'credentials\.json$', 'critical', 'Credentials file staged for commit'),
        (r'service[_-]?account.*\.json$', 'critical', 'Service account key staged for commit'),
    ]
    findings = []
    for line in name_status_diff.splitlines():
        if not line.startswith(('A', 'M')):  # Added or Modified
            continue
        filepath = line.split('\t', 1)[1].strip()
        for pattern, severity, description in SENSITIVE_PATTERNS:
            if re.search(pattern, filepath, re.I):
                findings.append(StagedFinding(
                    severity=severity,
                    category="sensitive_file_staged",
                    file=filepath,
                    line=0,
                    description=description,
                    evidence=filepath,
                ))
    return findings

def _scan_ci_workflow_modifications(name_status_diff: str) -> list[StagedFinding]:
    CI_PATTERNS = [
        r'\.github/workflows/.*\.ya?ml$',
        r'\.gitlab-ci\.ya?ml$',
        r'\.circleci/config\.ya?ml$',
        r'Jenkinsfile$',
        r'\.buildkite/pipeline\.ya?ml$',
    ]
    findings = []
    for line in name_status_diff.splitlines():
        if not line.startswith(('A', 'M')):
            continue
        filepath = line.split('\t', 1)[1].strip()
        for pattern in CI_PATTERNS:
            if re.search(pattern, filepath, re.I):
                findings.append(StagedFinding(
                    severity="high",
                    category="ci_workflow_modified",
                    file=filepath,
                    line=0,
                    description="CI/CD workflow file modified — review for unexpected changes",
                    evidence=filepath,
                ))
    return findings
```

### Step 3 — Lockfile Tamper Detection (`lockfile_diff.py`)

A modified lockfile without a corresponding modification to the package manifest is a red flag for supply-chain tampering.

```python
def check_lockfile_tamper(cwd: Path | None = None) -> list[StagedFinding]:
    cwd = cwd or Path.cwd()
    findings = []

    LOCKFILE_MANIFEST_PAIRS = [
        ("package-lock.json", "package.json"),
        ("yarn.lock", "package.json"),
        ("pnpm-lock.yaml", "package.json"),
        ("bun.lockb", "package.json"),
        ("poetry.lock", "pyproject.toml"),
        ("Cargo.lock", "Cargo.toml"),
        ("Gemfile.lock", "Gemfile"),
    ]

    staged_files = _get_staged_files(cwd)

    for lockfile, manifest in LOCKFILE_MANIFEST_PAIRS:
        lockfile_staged = any(f.endswith(lockfile) for f in staged_files)
        manifest_staged = any(f.endswith(manifest) for f in staged_files)

        if lockfile_staged and not manifest_staged:
            # Lockfile changed, manifest didn't — suspicious
            findings.append(StagedFinding(
                severity="high",
                category="lockfile_modified_without_manifest",
                file=lockfile,
                line=0,
                description=(
                    f"{lockfile} was modified but {manifest} was not. "
                    "Lockfile changes without manifest changes may indicate supply-chain tampering."
                ),
                evidence=f"staged: {lockfile}, not staged: {manifest}",
            ))

    return findings
```

### Step 4 — History Scanner (`history_scanner.py`)

Scan recent git history for secrets and risky patterns. This is the same scanner from Gap 4's `git_scanner.py` but with additional git-specific checks:

```python
def scan_history_for_security_issues(
    depth: int = 50,
    since: str | None = None,
    cwd: Path | None = None,
) -> list[HistoryFinding]:
    findings = []
    # Secret scanning (covered in Gap 4 plan)
    findings.extend(scan_history_for_secrets(depth=depth, since=since))
    # Additional git-specific checks:
    findings.extend(_check_force_push_in_log(cwd))
    findings.extend(_check_ci_workflow_history(depth=depth, cwd=cwd))
    return findings

def _check_ci_workflow_history(depth: int, cwd: Path | None) -> list[HistoryFinding]:
    """Flag commits that modified CI workflows in the last N commits."""
    log = subprocess.run(
        ["git", "log", f"-{depth}", "--name-only", "--format=%H %s", "--", ".github/workflows/"],
        cwd=str(cwd or Path.cwd()),
        capture_output=True, text=True,
    ).stdout
    if log.strip():
        # Parse commits that touched workflow files
        ...
```

### Step 5 — Hook Installer (`hooks.py`)

```python
GIT_HOOK_SCRIPT = """\
#!/bin/sh
# Policy Scout pre-commit hook
# Installed by: policy-scout git install-hooks

set -e

if command -v policy-scout >/dev/null 2>&1; then
    policy-scout scan --staged --exit-code
    exit $?
fi

# policy-scout not found — warn but don't block
echo "WARNING: policy-scout not found in PATH. Pre-commit scan skipped." >&2
exit 0
"""

def install_hooks(cwd: Path | None = None) -> HookInstallResult:
    ctx = get_git_context(cwd)
    if not ctx:
        return HookInstallResult(success=False, reason="Not in a git repository")

    hooks_dir = ctx.repo_root / ".git" / "hooks"
    pre_commit_path = hooks_dir / "pre-commit"

    if pre_commit_path.exists():
        existing_content = pre_commit_path.read_text()
        if "policy-scout" in existing_content:
            return HookInstallResult(success=True, reason="Already installed")
        # Append to existing hook
        with open(pre_commit_path, 'a') as f:
            f.write("\n# Policy Scout scan\n")
            f.write("policy-scout scan --staged --exit-code 2>/dev/null || true\n")
        return HookInstallResult(success=True, reason="Appended to existing hook")
    else:
        pre_commit_path.write_text(GIT_HOOK_SCRIPT)
        pre_commit_path.chmod(0o755)
        return HookInstallResult(success=True, reason="Created new pre-commit hook")

def uninstall_hooks(cwd: Path | None = None) -> HookUninstallResult:
    ctx = get_git_context(cwd)
    if not ctx:
        return HookUninstallResult(success=False, reason="Not in a git repository")
    pre_commit_path = ctx.repo_root / ".git" / "hooks" / "pre-commit"
    if not pre_commit_path.exists():
        return HookUninstallResult(success=True, reason="No hook found")
    content = pre_commit_path.read_text()
    if "policy-scout" not in content:
        return HookUninstallResult(success=True, reason="Policy Scout not in hook")
    # Remove just the policy-scout lines
    new_content = "\n".join(
        line for line in content.splitlines()
        if "policy-scout" not in line
    )
    if new_content.strip():
        pre_commit_path.write_text(new_content)
    else:
        pre_commit_path.unlink()
    return HookUninstallResult(success=True, reason="Removed from hook")
```

### Step 6 — Sweep Integration

Add git-aware checks to `sweep/engine.py`:

```python
def run_project_sweep(self, root: Path) -> SweepResult:
    ...
    ctx = get_git_context(root)
    if ctx:
        # Check for lockfile/manifest mismatches in current working tree
        findings.extend(lockfile_diff.check_lockfile_tamper_in_working_tree(root))
        # Check for untracked executable files (not in .gitignore)
        findings.extend(self._check_untracked_executables(ctx))
        # Incorporate git-status awareness
        findings.extend(self._check_recently_modified_sensitive_files(ctx))
    ...

def _check_recently_modified_sensitive_files(self, ctx: GitContext) -> list[Finding]:
    """Files modified since last commit that match sensitive patterns."""
    modified = subprocess.run(
        ["git", "diff", "--name-only", "HEAD"],
        cwd=str(ctx.repo_root), capture_output=True, text=True
    ).stdout.strip().splitlines()
    ...
```

---

## CLI Commands

```bash
# Hook management
policy-scout git install-hooks      # install pre-commit hook
policy-scout git uninstall-hooks    # remove pre-commit hook
policy-scout git hook-status        # check hook installation state

# Scanning
policy-scout scan --staged          # scan staged changes (used by hook)
policy-scout scan --staged --exit-code  # non-zero exit on critical findings
policy-scout git scan-history [--depth 50] [--since 2026-01-01]

# Lockfile tamper check
policy-scout git check-lockfiles    # check all lockfiles in working tree
```

---

## New Audit Event Types

```
GitHookInstalled        — pre-commit hook was installed
PreCommitScanRan        — hook triggered a scan
LockfileTamperSuspected — lockfile changed without manifest
CIWorkflowModified      — CI workflow file changed (staged or historical)
```

---

## Integration Points

- `sweep/engine.py` — add git-aware sub-checkers
- `scan/git_scanner.py` (Gap 4) — shared scanner logic
- `cli/main.py` — register `git` command group
- `audit/events.py` — four new event types
- `doctor.py` — check hook installation status

---

## Test Strategy

- Unit test `check_lockfile_tamper()` with fixture staged-file lists (lockfile staged without manifest)
- Unit test `_check_sensitive_file_additions()` with fixture `git diff --name-status` output
- Unit test `_scan_ci_workflow_modifications()` with fixture diffs
- Unit test `install_hooks()` against a temporary git repo (create real repo in temp dir)
- Unit test `uninstall_hooks()` including partial hook removal
- Integration test: create temp git repo, stage a `.env` file, run `policy-scout scan --staged`, verify critical finding
- Integration test: create temp git repo, modify `package-lock.json` but not `package.json`, run `policy-scout scan --staged`, verify lockfile tamper finding

---

## Effort Estimate

| Component | Lines | Complexity |
|-----------|-------|------------|
| `context.py` | ~80 | Low |
| `staged_scanner.py` | ~250 | Medium |
| `lockfile_diff.py` | ~120 | Low |
| `history_scanner.py` | ~150 | Low-Medium |
| `hooks.py` | ~150 | Low-Medium |
| Sweep engine integration | ~100 delta | Low |
| CLI commands | ~120 | Low |
| Tests | ~400 | Medium |
| **Total** | **~1370** | |

---

## Open Questions

1. Should `install-hooks` also install a `pre-push` hook to scan history before pushing? Recommendation: yes, as an opt-in `--with-pre-push` flag. Pre-push is higher impact (blocks exfiltration to remote) but also higher friction.
2. What happens if the pre-commit hook fails because `policy-scout` is unavailable? Recommendation: the hook script always exits 0 when policy-scout is not found, only warns. Never block commits when the tool is unavailable — that would break onboarding.
3. Should the lockfile tamper check also run on the full project sweep (not just staged)? Recommendation: yes — check for lockfile/manifest modification timestamp mismatches in the working tree even when not in a commit flow.
