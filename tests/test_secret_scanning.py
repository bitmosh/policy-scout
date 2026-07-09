# SPDX-License-Identifier: Apache-2.0
"""Tests for [04] Secret Scanning."""

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ──────────────────────────────────────────────────────────────────────────────
# Entropy
# ──────────────────────────────────────────────────────────────────────────────

from policy_scout.scan.entropy import shannon_entropy, find_high_entropy_strings


def test_shannon_entropy_empty():
    assert shannon_entropy("") == 0.0


def test_shannon_entropy_uniform():
    # All same char → 0 bits
    assert shannon_entropy("aaaa") == 0.0


def test_shannon_entropy_binary():
    # 50/50 split → 1 bit
    val = shannon_entropy("ab")
    assert abs(val - 1.0) < 0.01


def test_shannon_entropy_realistic_key():
    # A realistic AWS-style key should be high entropy
    key = "AKIAIOSFODNN7ABCDE12"
    h = shannon_entropy(key)
    assert h > 3.0


def test_find_high_entropy_strings_finds_token():
    # Synthetic token that looks like a real secret
    text = 'TOKEN = "wJalrXUtnFEMI9CXIEXAMPLEKEYvalue1234567890abc"'
    matches = find_high_entropy_strings(text, min_entropy=3.5, min_length=20)
    assert len(matches) >= 1


def test_find_high_entropy_strings_skips_urls():
    text = "endpoint = https://example.com/api/v1/resource"
    matches = find_high_entropy_strings(text, min_entropy=3.5, min_length=10)
    # URLs should be filtered
    assert all("https" not in m.value for m in matches)


def test_find_high_entropy_strings_skips_git_hash():
    text = "commit: a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2"
    matches = find_high_entropy_strings(text, min_entropy=3.5, min_length=40)
    assert len(matches) == 0


# ──────────────────────────────────────────────────────────────────────────────
# Pattern matcher
# ──────────────────────────────────────────────────────────────────────────────

from policy_scout.scan.patterns import (
    load_patterns,
    SecretPatternMatcher,
    _redact_value,
)


def test_load_patterns_returns_list():
    specs = load_patterns()
    assert isinstance(specs, list)
    assert len(specs) > 0


def test_load_patterns_all_have_required_fields():
    specs = load_patterns()
    for s in specs:
        assert s.id
        assert s.service
        assert s.pattern
        assert s.severity in ("critical", "high", "medium", "low")


def test_redact_value_short():
    assert _redact_value("abc") == "***"


def test_redact_value_long():
    result = _redact_value("AKIAIOSFODNN7ABCDE12123")
    assert result.startswith("AKIA")
    assert "***" in result
    assert result.endswith("23")


def test_pattern_matcher_detects_aws_key():
    specs = load_patterns()
    matcher = SecretPatternMatcher(specs)
    text = "export AWS_ACCESS_KEY_ID=AKIAIOSFODNN7ABCDE12"
    findings = matcher.scan_text(text, source="test.sh")
    aws_finds = [f for f in findings if f.secret_type == "aws_access_key"]
    assert len(aws_finds) == 1
    assert aws_finds[0].severity == "critical"
    assert aws_finds[0].line == 1


def test_pattern_matcher_detects_github_token():
    specs = load_patterns()
    matcher = SecretPatternMatcher(specs)
    text = "GH_TOKEN=ghp_" + "A" * 36
    findings = matcher.scan_text(text, source="env.sh")
    github_finds = [f for f in findings if f.secret_type == "github_token_classic"]
    assert len(github_finds) == 1


def test_pattern_matcher_detects_pem_header():
    specs = load_patterns()
    matcher = SecretPatternMatcher(specs)
    text = "-----BEGIN RSA PRIVATE KEY-----\nMIIE...\n-----END RSA PRIVATE KEY-----"
    findings = matcher.scan_text(text, source="key.pem")
    pem_finds = [f for f in findings if f.secret_type == "private_key_pem"]
    assert len(pem_finds) == 1
    assert pem_finds[0].severity == "critical"


def test_pattern_matcher_detects_connection_string():
    specs = load_patterns()
    matcher = SecretPatternMatcher(specs)
    text = "DATABASE_URL=postgresql://user:secretpass@db.example.com:5432/mydb"
    findings = matcher.scan_text(text, source=".env")
    conn_finds = [f for f in findings if f.secret_type == "connection_string"]
    assert len(conn_finds) == 1


def test_pattern_matcher_skips_placeholder():
    specs = load_patterns()
    matcher = SecretPatternMatcher(specs)
    # changeme should be filtered
    text = "export AWS_ACCESS_KEY_ID=AKIAchangemechangeme1"
    findings = matcher.scan_text(text, source="test.sh")
    assert len(findings) == 0


def test_pattern_matcher_entropy_gate_filters_low_entropy():
    specs = load_patterns()
    # aws_secret_key requires entropy_min=4.5 + context pattern
    # A low-entropy 40-char string should be filtered
    matcher = SecretPatternMatcher(specs)
    text = "aws_secret_access_key=AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    findings = matcher.scan_text(text, source="test.sh")
    secret_key_finds = [f for f in findings if f.secret_type == "aws_secret_key"]
    assert len(secret_key_finds) == 0


def test_pattern_matcher_line_numbers():
    specs = load_patterns()
    matcher = SecretPatternMatcher(specs)
    text = "line1\nline2\nexport AWS_ACCESS_KEY_ID=AKIAIOSFODNN7ABCDE12\nline4"
    findings = matcher.scan_text(text, source="test.sh")
    aws_finds = [f for f in findings if f.secret_type == "aws_access_key"]
    assert len(aws_finds) == 1
    assert aws_finds[0].line == 3


def test_pattern_matcher_multiline_offset():
    specs = load_patterns()
    matcher = SecretPatternMatcher(specs)
    text = "line1\nGH_TOKEN=ghp_" + "B" * 36
    findings = matcher.scan_text(text, source="test.sh", line_offset=5)
    github_finds = [f for f in findings if f.secret_type == "github_token_classic"]
    assert len(github_finds) == 1
    assert github_finds[0].line == 7  # line 2 + offset 5


# ──────────────────────────────────────────────────────────────────────────────
# File scanner
# ──────────────────────────────────────────────────────────────────────────────

from policy_scout.scan.file_scanner import scan_file, scan_directory, ScanResult


def test_scan_file_with_secret(tmp_path):
    specs = load_patterns()
    matcher = SecretPatternMatcher(specs)
    f = tmp_path / "creds.env"
    f.write_text("AWS_ACCESS_KEY_ID=AKIAIOSFODNN7ABCDE12\n")
    findings = scan_file(f, matcher)
    assert len(findings) >= 1
    assert any(fn.secret_type == "aws_access_key" for fn in findings)


def test_scan_file_clean(tmp_path):
    specs = load_patterns()
    matcher = SecretPatternMatcher(specs)
    f = tmp_path / "clean.py"
    f.write_text("print('hello world')\n")
    findings = scan_file(f, matcher)
    assert findings == []


def test_scan_file_skips_binary(tmp_path):
    specs = load_patterns()
    matcher = SecretPatternMatcher(specs)
    f = tmp_path / "binary.bin"
    f.write_bytes(b"\x00\x01\x02" + b"AKIAIOSFODNN7ABCDE12" + b"\x00")
    findings = scan_file(f, matcher)
    assert findings == []


def test_scan_file_skips_oversized(tmp_path):
    specs = load_patterns()
    matcher = SecretPatternMatcher(specs)
    f = tmp_path / "big.txt"
    # Write > 1 MB
    f.write_bytes(b"x" * (1024 * 1024 + 1))
    findings = scan_file(f, matcher)
    assert findings == []


def test_scan_directory_finds_secret(tmp_path):
    specs = load_patterns()
    matcher = SecretPatternMatcher(specs)
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / ".env").write_text(
        "DB_PASS=postgresql://admin:s3cr3t@db.local:5432/prod\n"
    )
    result = scan_directory(tmp_path, matcher)
    assert result.files_scanned >= 1
    assert len(result.findings) >= 1


def test_scan_directory_skips_git_dir(tmp_path):
    specs = load_patterns()
    matcher = SecretPatternMatcher(specs)
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    (git_dir / "config").write_text(
        "AWS_ACCESS_KEY_ID=AKIAIOSFODNN7ABCDE12\n"
    )
    result = scan_directory(tmp_path, matcher)
    # .git dir should be skipped; no findings
    git_findings = [
        f for f in result.findings if ".git" in f.source
    ]
    assert len(git_findings) == 0


def test_scan_result_severity_exit_code_clean():
    r = ScanResult()
    assert r.severity_exit_code == 0


def test_scan_result_severity_exit_code_critical(tmp_path):
    specs = load_patterns()
    matcher = SecretPatternMatcher(specs)
    f = tmp_path / ".env"
    f.write_text("KEY=AKIAIOSFODNN7ABCDE12\n")
    result = scan_directory(tmp_path, matcher)
    assert result.severity_exit_code == 2


# ──────────────────────────────────────────────────────────────────────────────
# Guidance
# ──────────────────────────────────────────────────────────────────────────────

from policy_scout.scan.guidance import generate_guidance
from policy_scout.scan.patterns import SecretFinding


def _make_finding(**kw):
    defaults = dict(
        secret_type="aws_access_key",
        service="AWS",
        severity="critical",
        source="test.sh",
        line=1,
        column=0,
        redacted_value="AKIA***LE",
        guidance="Rotate immediately.",
    )
    defaults.update(kw)
    return SecretFinding(**defaults)


def test_generate_guidance_no_history():
    f = _make_finding()
    g = generate_guidance(f, is_in_history=False)
    assert "Rotate" in g
    assert "git history" not in g


def test_generate_guidance_with_history():
    f = _make_finding()
    g = generate_guidance(f, is_in_history=True)
    assert "git history" in g
    assert "filter-repo" in g


def test_generate_guidance_empty_guidance_field():
    f = _make_finding(guidance="")
    g = generate_guidance(f, is_in_history=False)
    assert "aws_access_key" in g or "AWS" in g


# ──────────────────────────────────────────────────────────────────────────────
# Engine (SecretScanner)
# ──────────────────────────────────────────────────────────────────────────────

from policy_scout.scan.engine import SecretScanner, ScanSummary


def test_secret_scanner_loads_patterns():
    scanner = SecretScanner()
    assert scanner.pattern_count > 0


def test_secret_scanner_scan_directory(tmp_path):
    (tmp_path / "secret.env").write_text(
        "GH_TOKEN=ghp_" + "X" * 36 + "\n"
    )
    scanner = SecretScanner()
    summary = scanner.scan_directory(tmp_path)
    assert isinstance(summary, ScanSummary)
    assert summary.scan_type == "directory"
    assert summary.finding_count >= 1
    github_finds = [f for f in summary.findings if f.secret_type == "github_token_classic"]
    assert len(github_finds) >= 1


def test_secret_scanner_scan_file_clean(tmp_path):
    f = tmp_path / "clean.py"
    f.write_text("x = 1\n")
    scanner = SecretScanner()
    summary = scanner.scan_file(f)
    assert summary.scan_type == "file"
    assert summary.finding_count == 0


def test_scan_summary_to_dict(tmp_path):
    f = tmp_path / "s.env"
    f.write_text("AWS_ACCESS_KEY_ID=AKIAIOSFODNN7ABCDE12\n")
    scanner = SecretScanner()
    summary = scanner.scan_directory(tmp_path)
    d = summary.to_dict()
    assert d["scan_type"] == "directory"
    assert "findings" in d
    assert "severity_counts" in d


# ──────────────────────────────────────────────────────────────────────────────
# Git scanner (unit: mock subprocess)
# ──────────────────────────────────────────────────────────────────────────────

from policy_scout.scan.git_scanner import scan_staged, scan_history


def _make_matcher():
    return SecretPatternMatcher(load_patterns())


def test_scan_staged_no_staged_files(monkeypatch):
    def fake_run(args, **kwargs):
        r = MagicMock()
        r.returncode = 0
        r.stdout = ""
        r.stderr = ""
        return r

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = scan_staged(_make_matcher())
    assert result.files_scanned == 0
    assert result.findings == []


def test_scan_staged_with_secret(monkeypatch):
    calls = []

    def fake_run(args, **kwargs):
        r = MagicMock()
        if "--name-only" in args:
            r.returncode = 0
            r.stdout = "deploy/.env\n"
            r.stderr = ""
        else:
            # git show :deploy/.env
            r.returncode = 0
            r.stdout = "AWS_ACCESS_KEY_ID=AKIAIOSFODNN7ABCDE12\n"
            r.stderr = ""
        calls.append(args)
        return r

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = scan_staged(_make_matcher())
    assert result.files_scanned == 1
    assert any(f.secret_type == "aws_access_key" for f in result.findings)


def test_scan_staged_git_error(monkeypatch):
    def fake_run(args, **kwargs):
        r = MagicMock()
        r.returncode = 128
        r.stdout = ""
        r.stderr = "not a git repository"
        return r

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = scan_staged(_make_matcher())
    assert len(result.errors) >= 1


def test_scan_history_no_commits(monkeypatch):
    def fake_run(args, **kwargs):
        r = MagicMock()
        r.returncode = 0
        r.stdout = ""
        r.stderr = ""
        return r

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = scan_history(_make_matcher(), max_commits=10)
    assert result.commits_scanned == 0
    assert result.findings == []


def test_scan_history_commit_with_secret(monkeypatch):
    commit_hash = "abc123def456abc1"

    def fake_run(args, **kwargs):
        r = MagicMock()
        r.returncode = 0
        if args[1] == "log":
            r.stdout = f"{commit_hash}\n"
        elif args[1] == "diff-tree":
            r.stdout = f"A\tsecrets/.env\n"
        else:
            # git show abc123:.env
            r.stdout = "GH_TOKEN=ghp_" + "Z" * 36 + "\n"
        r.stderr = ""
        return r

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = scan_history(_make_matcher(), max_commits=5)
    assert result.commits_scanned >= 1
    github_finds = [f for f in result.findings if f.secret_type == "github_token_classic"]
    assert len(github_finds) >= 1
    # Commit hash attached
    assert github_finds[0].commit == commit_hash
