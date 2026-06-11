"""Tests for the MCP JSON-RPC 2.0 server protocol."""

import io
import json

from policy_scout.server.mcp_server import (
    _err,
    _ok,
    _process_message,
    _send,
)
from policy_scout.server.session import McpSession
from policy_scout.server.tool_definitions import TOOL_DEFINITIONS, TOOL_NAMES


# ── Helpers ───────────────────────────────────────────────────────────────────

def _session(initialized: bool = False) -> McpSession:
    s = McpSession(session_id="test_session")
    s.initialized = initialized
    return s


def _rpc(method: str, params: dict | None = None, req_id: int = 1) -> dict:
    msg: dict = {"jsonrpc": "2.0", "method": method, "id": req_id}
    if params is not None:
        msg["params"] = params
    return msg


# ── JSON-RPC helpers ──────────────────────────────────────────────────────────

class TestJsonRpcHelpers:
    def test_ok_shape(self):
        r = _ok(1, {"foo": "bar"})
        assert r["jsonrpc"] == "2.0"
        assert r["id"] == 1
        assert r["result"] == {"foo": "bar"}
        assert "error" not in r

    def test_err_shape(self):
        r = _err(1, -32600, "Invalid Request")
        assert r["jsonrpc"] == "2.0"
        assert r["id"] == 1
        assert r["error"]["code"] == -32600
        assert r["error"]["message"] == "Invalid Request"
        assert "result" not in r

    def test_err_with_data(self):
        r = _err(2, -32001, "oops", data={"detail": "x"})
        assert r["error"]["data"] == {"detail": "x"}

    def test_send_writes_newline(self):
        buf = io.StringIO()
        _send({"jsonrpc": "2.0", "id": 1, "result": {}}, buf)
        line = buf.getvalue()
        assert line.endswith("\n")
        parsed = json.loads(line.strip())
        assert parsed["jsonrpc"] == "2.0"


# ── Tool definitions ──────────────────────────────────────────────────────────

class TestToolDefinitions:
    def test_five_tools_defined(self):
        assert len(TOOL_DEFINITIONS) == 5

    def test_tool_names_match_set(self):
        names = {t["name"] for t in TOOL_DEFINITIONS}
        assert names == TOOL_NAMES

    def test_required_fields_present(self):
        for tool in TOOL_DEFINITIONS:
            assert "name" in tool
            assert "description" in tool
            assert "inputSchema" in tool
            assert tool["inputSchema"]["type"] == "object"

    def test_check_tool_has_command_required(self):
        check = next(t for t in TOOL_DEFINITIONS if t["name"] == "policy_scout_check")
        assert "command" in check["inputSchema"]["required"]

    def test_sandbox_tool_has_command_required(self):
        sb = next(t for t in TOOL_DEFINITIONS if t["name"] == "policy_scout_sandbox")
        assert "command" in sb["inputSchema"]["required"]


# ── Protocol dispatch ─────────────────────────────────────────────────────────

class TestProcessMessage:
    def test_initialize_succeeds(self):
        session = _session()
        resp = _process_message(
            _rpc("initialize", {"protocolVersion": "2024-11-05", "clientInfo": {"name": "test", "version": "0.1"}}),
            session,
        )
        assert resp is not None
        assert "result" in resp
        assert resp["result"]["protocolVersion"] == "2024-11-05"
        assert session.initialized is True
        assert session.client_name == "test"

    def test_initialized_notification_returns_none(self):
        session = _session(initialized=True)
        resp = _process_message({"jsonrpc": "2.0", "method": "initialized"}, session)
        assert resp is None

    def test_tools_list_returns_all_tools(self):
        session = _session(initialized=True)
        resp = _process_message(_rpc("tools/list"), session)
        assert resp is not None
        assert "tools" in resp["result"]
        assert len(resp["result"]["tools"]) == 5

    def test_ping_returns_empty_result(self):
        session = _session(initialized=True)
        resp = _process_message(_rpc("ping"), session)
        assert resp is not None
        assert resp["result"] == {}

    def test_unknown_method_returns_error(self):
        session = _session(initialized=True)
        resp = _process_message(_rpc("nonexistent/method"), session)
        assert resp is not None
        assert "error" in resp
        assert resp["error"]["code"] == -32601

    def test_request_before_initialize_returns_error(self):
        session = _session(initialized=False)
        resp = _process_message(_rpc("tools/list"), session)
        assert resp is not None
        assert "error" in resp

    def test_notification_before_initialize_returns_error_only_if_has_id(self):
        # Notification (no id) before init — should return None, not an error
        session = _session(initialized=False)
        resp = _process_message({"jsonrpc": "2.0", "method": "some/notif"}, session)
        # No id → treated as notification → None
        assert resp is None

    def test_unknown_tool_returns_error(self):
        session = _session(initialized=True)
        resp = _process_message(
            _rpc("tools/call", {"name": "nonexistent_tool", "arguments": {}}),
            session,
        )
        assert resp is not None
        assert "error" in resp


# ── Session ───────────────────────────────────────────────────────────────────

class TestMcpSession:
    def test_record_tool_call_increments(self):
        s = McpSession(session_id="s1")
        assert s.tool_calls == 0
        s.record_tool_call()
        s.record_tool_call()
        assert s.tool_calls == 2

    def test_to_dict(self):
        s = McpSession(session_id="s2", client_name="claude", initialized=True)
        d = s.to_dict()
        assert d["session_id"] == "s2"
        assert d["client_name"] == "claude"
        assert d["initialized"] is True
        assert "tool_calls" in d
