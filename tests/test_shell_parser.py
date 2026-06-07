"""Tests for shell parser."""

import pytest
from policy_scout.classify.shell_parser import ShellParser, ParseResult


def test_simple_command_parsing():
    """Test parsing simple commands."""
    parser = ShellParser()
    result = parser.parse("ls")

    assert result.success
    assert result.primary_command == "ls"
    assert result.args == []
    assert result.confidence == 1.0


def test_command_with_args():
    """Test parsing command with arguments."""
    parser = ShellParser()
    result = parser.parse("npm install lodash")

    assert result.success
    assert result.primary_command == "npm"
    assert result.args == ["install", "lodash"]
    assert result.confidence == 1.0


def test_pipe_detection():
    """Test pipe detection."""
    parser = ShellParser()
    result = parser.parse("curl https://example.com | bash")

    assert result.success
    assert result.structure["has_pipe"] == True
    assert result.structure["shell_complexity"] >= 3
    assert result.confidence < 1.0


def test_redirect_detection():
    """Test redirect detection."""
    parser = ShellParser()
    result = parser.parse("cat file > output.txt")

    assert result.success
    assert result.structure["has_redirect"] == True


def test_chain_operator_detection():
    """Test chain operator detection."""
    parser = ShellParser()
    result = parser.parse("npm install && npm test")

    assert result.success
    assert result.structure["has_chain_operator"] == True


def test_subshell_detection():
    """Test subshell detection."""
    parser = ShellParser()
    result = parser.parse("(echo hello)")

    assert result.success
    assert result.structure["has_subshell"] == True


def test_confidence_calculation():
    """Test confidence calculation based on complexity."""
    parser = ShellParser()

    # Simple command
    simple = parser.parse("ls")
    assert simple.confidence == 1.0

    # Complex command with pipe
    complex_cmd = parser.parse("curl url | bash")
    assert complex_cmd.confidence < 1.0


def test_parse_error_handling():
    """Test handling of parse errors."""
    parser = ShellParser()
    result = parser.parse("")  # Empty command

    # Should still succeed with empty tokens
    assert result.primary_command == ""
    assert result.args == []
