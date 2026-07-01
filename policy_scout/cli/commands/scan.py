"""scan and git command handlers."""

import json
import sys

from ...audit.store import AuditStore


def handle_scan_command(args) -> None:
    """Handle all scan subcommands."""
    from ...scan.engine import SecretScanner
    from ...audit.events import create_secret_scan_completed_event, create_secret_finding_event
    from pathlib import Path

    audit_store = AuditStore() if not getattr(args, "no_audit", False) else None
    scanner = SecretScanner()

    sub = getattr(args, "scan_subcommand", None)
    if not sub:
        print("Error: No scan subcommand provided. Use: dir, file, staged, history", file=sys.stderr)
        sys.exit(1)

    if sub == "dir":
        root = Path(getattr(args, "path", "."))
        if not root.is_dir():
            print(f"Error: Not a directory: {root}", file=sys.stderr)
            sys.exit(1)
        summary = scanner.scan_directory(root, run_entropy=getattr(args, "entropy", False))

    elif sub == "file":
        path = Path(args.path)
        if not path.is_file():
            print(f"Error: File not found: {path}", file=sys.stderr)
            sys.exit(1)
        summary = scanner.scan_file(path, run_entropy=getattr(args, "entropy", False))

    elif sub == "staged":
        repo = Path(getattr(args, "repo", None) or ".")
        summary = scanner.scan_staged(repo_root=repo)

    elif sub == "history":
        repo = Path(getattr(args, "repo", None) or ".")
        summary = scanner.scan_history(
            repo_root=repo,
            max_commits=getattr(args, "max_commits", 200),
            since_ref=getattr(args, "since", None),
        )
    elif sub == "injection":
        _handle_scan_injection(args, audit_store)
        return
    else:
        print(f"Error: Unknown scan subcommand: {sub}", file=sys.stderr)
        sys.exit(1)

    # Audit
    if audit_store:
        for finding in summary.findings:
            audit_store.write(
                create_secret_finding_event(
                    scan_id=summary.scan_id,
                    secret_type=finding.secret_type,
                    service=finding.service,
                    severity=finding.severity,
                    source=finding.source,
                    line=finding.line,
                )
            )
        audit_store.write(
            create_secret_scan_completed_event(
                scan_id=summary.scan_id,
                scan_type=summary.scan_type,
                target=summary.target,
                finding_count=summary.finding_count,
                severity_counts=summary.severity_counts(),
                files_scanned=summary.files_scanned,
                duration_ms=summary.duration_ms,
            )
        )

    if getattr(args, "json", False):
        print(json.dumps(summary.to_dict(), indent=2))
    else:
        _print_scan_summary(summary)

    sys.exit(summary.severity_exit_code)


def _print_scan_summary(summary) -> None:
    """Print human-readable scan output."""
    counts = summary.severity_counts()
    print(f"\nSecret Scan — {summary.scan_type}: {summary.target}")
    print(f"  Files scanned : {summary.files_scanned}")
    if summary.commits_scanned:
        print(f"  Commits scanned: {summary.commits_scanned}")
    print(f"  Duration      : {summary.duration_ms}ms")
    print(f"  Findings      : {summary.finding_count}")

    if not summary.findings:
        print("\n  No secrets detected.")
        return

    # Group by severity for display
    for severity in ("critical", "high", "medium", "low"):
        group = [f for f in summary.findings if f.severity == severity]
        if not group:
            continue
        label = severity.upper()
        print(f"\n  [{label}] {len(group)} finding(s)")
        for f in group:
            commit_suffix = f" (commit {f.commit[:8]})" if f.commit else ""
            print(f"    {f.source}:{f.line}  {f.service}/{f.secret_type}{commit_suffix}")
            print(f"      Redacted: {f.redacted_value}")
            print(f"      Action  : {f.guidance[:120]}")

    if summary.errors:
        print(f"\n  Errors ({len(summary.errors)}):")
        for e in summary.errors[:5]:
            print(f"    {e}")


def handle_git_command(args) -> None:
    """Handle all git subcommands."""
    from ...git.context import get_git_context
    from ...git.hooks import get_hooks_status, install_hooks, uninstall_hooks
    from ...git.lockfile_diff import check_lockfile_changes
    from ...git.staged_scanner import scan_staged_full
    from pathlib import Path

    sub = getattr(args, "git_subcommand", None)
    if not sub:
        print(
            "Error: No git subcommand provided. Use: context, hooks, lockfile-check, staged-check",
            file=sys.stderr,
        )
        sys.exit(1)

    if sub == "context":
        repo = Path(getattr(args, "repo", None) or ".")
        ctx = get_git_context(cwd=repo)
        if ctx is None:
            print("Not a git repository.", file=sys.stderr)
            sys.exit(1)
        if getattr(args, "json", False):
            print(json.dumps(ctx.to_dict(), indent=2))
        else:
            print(f"Branch  : {ctx.branch or '(detached)'}")
            print(f"Commit  : {ctx.commit or '(none)'}")
            print(f"Dirty   : {'yes' if ctx.dirty else 'no'}")
            print(f"Remote  : {ctx.remote or '(none)'}")
            print(f"Root    : {ctx.repo_root}")

    elif sub == "hooks":
        hooks_sub = getattr(args, "git_hooks_subcommand", None)
        repo = Path(getattr(args, "repo", None) or ".")

        if hooks_sub == "install":
            try:
                report = install_hooks(repo_root=repo)
                if getattr(args, "json", False):
                    print(json.dumps(report.to_dict(), indent=2))
                else:
                    print(f"Hooks installed in: {report.hooks_dir}")
                    for h in report.hooks:
                        status = "installed" if h.installed else "failed"
                        print(f"  {h.name}: {status}")
            except RuntimeError as e:
                print(f"Error: {e}", file=sys.stderr)
                sys.exit(1)

        elif hooks_sub == "uninstall":
            try:
                report = uninstall_hooks(repo_root=repo)
                if getattr(args, "json", False):
                    print(json.dumps(report.to_dict(), indent=2))
                else:
                    print("Hooks uninstalled.")
                    for h in report.hooks:
                        status = "removed" if not h.installed else "kept (not managed)"
                        print(f"  {h.name}: {status}")
            except RuntimeError as e:
                print(f"Error: {e}", file=sys.stderr)
                sys.exit(1)

        elif hooks_sub == "status":
            report = get_hooks_status(repo_root=repo)
            if getattr(args, "json", False):
                print(json.dumps(report.to_dict(), indent=2))
            else:
                print(f"Hooks directory: {report.hooks_dir or '(not found)'}")
                for h in report.hooks:
                    managed_note = " (managed)" if h.managed else " (third-party)" if h.installed else ""
                    print(f"  {h.name}: {'installed' if h.installed else 'not installed'}{managed_note}")
        else:
            print("Error: No hooks subcommand. Use: install, uninstall, status", file=sys.stderr)
            sys.exit(1)

    elif sub == "lockfile-check":
        repo = Path(getattr(args, "repo", None) or ".")
        ref = getattr(args, "ref", "HEAD")
        result = check_lockfile_changes(repo_root=repo, compare_ref=ref)
        if getattr(args, "json", False):
            print(json.dumps(result.to_dict(), indent=2))
        else:
            print(f"Lockfiles found: {result.lockfiles_found}")
            print(f"Lockfiles changed: {result.lockfiles_changed}")
            for diff in result.diffs:
                if diff.error:
                    print(f"  {diff.lockfile}: ERROR — {diff.error}")
                elif diff.has_changes:
                    print(f"  {diff.lockfile}: CHANGED (+{len(diff.added)} -{len(diff.removed)} ~{diff.modified})")
                    for line in diff.added[:5]:
                        print(f"    + {line}")
                    for line in diff.removed[:5]:
                        print(f"    - {line}")
                else:
                    print(f"  {diff.lockfile}: OK")
        sys.exit(2 if result.any_changes else 0)

    elif sub == "staged-check":
        repo = Path(getattr(args, "repo", None) or ".")
        result = scan_staged_full(repo_root=repo)
        if getattr(args, "json", False):
            print(json.dumps(result.to_dict(), indent=2))
        else:
            _print_staged_check(result)
        sys.exit(result.severity_exit_code)

    else:
        print(f"Error: Unknown git subcommand: {sub}", file=sys.stderr)
        sys.exit(1)


def _print_staged_check(result) -> None:
    """Print human-readable staged-check output."""
    if result.is_clean and not result.has_ci_changes:
        print("Pre-commit check: CLEAN — no secrets or sensitive files detected.")
        return

    if result.has_sensitive_files:
        print(f"\n[BLOCK] {len(result.sensitive_files)} sensitive file(s) staged:")
        for w in result.sensitive_files:
            print(f"  {w.path}")
            print(f"    Reason: {w.reason}")

    if result.has_secrets and result.secret_scan:
        sc = result.secret_scan
        print(f"\n[BLOCK] {sc.finding_count} secret(s) detected in staged files:")
        for f in sc.findings:
            severity_label = f.severity.upper()
            print(f"  [{severity_label}] {f.source}:{f.line}  {f.service}/{f.secret_type}")
            print(f"    Redacted: {f.redacted_value}")
            print(f"    Action  : {f.guidance[:120]}")

    if result.has_ci_changes:
        print(f"\n[WARN] {len(result.ci_workflow_changes)} CI workflow file(s) changed:")
        for path in result.ci_workflow_changes:
            print(f"  {path}")
        print("  Review CI workflow changes carefully before committing.")

    if result.errors:
        print(f"\n[ERROR] Scan errors:")
        for e in result.errors:
            print(f"  {e}")


def _handle_scan_injection(args, audit_store) -> None:
    """Run prompt injection scan against a file or directory."""
    from pathlib import Path
    from ...sweep.prompt_injection import PromptInjectionAnalyzer, scan_agent_readable_files
    from ...audit.events import EventType
    from ...audit.store import AuditEvent

    target = Path(getattr(args, "path", "."))
    json_output = getattr(args, "json", False)

    findings = []
    if target.is_file():
        analyzer = PromptInjectionAnalyzer()
        raw = analyzer.analyze_file(target)
        findings = [f.to_sweep_finding() for f in raw]
    elif target.is_dir():
        findings = scan_agent_readable_files(str(target))
    else:
        print(f"Error: Not a file or directory: {target}", file=sys.stderr)
        sys.exit(1)

    # Emit audit events
    if audit_store:
        for f in findings:
            audit_store.write(AuditEvent(
                event_type=EventType.INJECTION_PATTERN_FOUND,
                summary=f"Injection pattern '{f.category}' in {f.location}",
                data={
                    "location": f.location,
                    "severity": f.severity,
                    "confidence": f.confidence,
                    "title": f.title,
                },
            ))

    result = {
        "target": str(target),
        "finding_count": len(findings),
        "findings": [f.to_dict() for f in findings],
    }

    if json_output:
        print(json.dumps(result, indent=2))
    else:
        print(f"\nPrompt Injection Scan: {target}")
        print(f"  Findings: {len(findings)}")
        if findings:
            print()
            for f in findings:
                print(f"  [{f.severity.upper()}] {f.title}")
                print(f"    Location: {f.location}")
                print(f"    Confidence: {f.confidence}")
                print()
        else:
            print("  No injection patterns detected.")

    if findings:
        worst = max(f.severity for f in findings)
        sys.exit(20 if worst == "critical" else 10)
    sys.exit(0)
