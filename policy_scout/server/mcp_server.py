# SPDX-License-Identifier: Apache-2.0
"""JSON-RPC 2.0 MCP server over stdio."""

from __future__ import annotations

import json
import sys
import traceback
from typing import Any, Optional

from .session import McpSession, set_session
from .tool_definitions import TOOL_DEFINITIONS, TOOL_NAMES

# Protocol version we advertise
_MCP_VERSION = "2024-11-05"
_SERVER_NAME = "policy-scout"
_SERVER_VERSION = "0.2.0"


# ── JSON-RPC helpers ──────────────────────────────────────────────────────────

def _ok(request_id: Any, result: Any) -> dict:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _err(request_id: Any, code: int, message: str, data: Any = None) -> dict:
    error: dict = {"code": code, "message": message}
    if data is not None:
        error["data"] = data
    return {"jsonrpc": "2.0", "id": request_id, "error": error}


def _send(obj: dict, out=None) -> None:
    """Write a JSON-RPC message to stdout (or supplied stream)."""
    line = json.dumps(obj, separators=(",", ":"))
    stream = out or sys.stdout
    stream.write(line + "\n")
    stream.flush()


# ── Request handlers ──────────────────────────────────────────────────────────

def _handle_initialize(req_id: Any, params: dict, session: McpSession) -> dict:
    info = params.get("clientInfo", {})
    session.client_name = info.get("name", "unknown")
    session.client_version = info.get("version", "unknown")
    session.initialized = True

    return _ok(req_id, {
        "protocolVersion": _MCP_VERSION,
        "capabilities": {
            "tools": {"listChanged": False},
        },
        "serverInfo": {
            "name": _SERVER_NAME,
            "version": _SERVER_VERSION,
        },
    })


def _handle_tools_list(req_id: Any) -> dict:
    return _ok(req_id, {"tools": TOOL_DEFINITIONS})


def _handle_tools_call(req_id: Any, params: dict, session: McpSession) -> dict:
    from ..audit.store import AuditStore
    from ..audit.events import EventType
    from ..audit.store import AuditEvent
    from ..core.ids import generate_id

    tool_name: str = params.get("name", "")
    tool_params: dict = params.get("arguments", {}) or {}

    if tool_name not in TOOL_NAMES:
        return _err(req_id, -32601, f"Unknown tool: {tool_name}")

    session.record_tool_call()
    call_id = generate_id("mcp")

    # Emit audit event
    audit = AuditStore()
    audit.write(AuditEvent(
        event_type=EventType.MCP_TOOL_CALL_RECEIVED,
        summary=f"MCP tool call: {tool_name}",
        data={
            "call_id": call_id,
            "tool_name": tool_name,
            "session_id": session.session_id,
            "client": session.client_name,
        },
    ))

    # Dispatch to handler
    try:
        result_data = _dispatch(tool_name, tool_params)
        is_error = result_data.pop("is_error", False) if isinstance(result_data, dict) else False

        audit.write(AuditEvent(
            event_type=EventType.MCP_TOOL_CALL_COMPLETED,
            summary=f"MCP tool completed: {tool_name}",
            data={
                "call_id": call_id,
                "tool_name": tool_name,
                "is_error": is_error,
            },
        ))

        content = [{"type": "text", "text": json.dumps(result_data, indent=2)}]
        return _ok(req_id, {"content": content, "isError": is_error})

    except Exception as exc:
        tb = traceback.format_exc()
        audit.write(AuditEvent(
            event_type=EventType.MCP_TOOL_CALL_COMPLETED,
            summary=f"MCP tool error: {tool_name}",
            data={"call_id": call_id, "tool_name": tool_name, "is_error": True, "error": str(exc)},
        ))
        content = [{"type": "text", "text": f"Internal error: {exc}\n{tb}"}]
        return _ok(req_id, {"content": content, "isError": True})


def _dispatch(tool_name: str, params: dict) -> dict:
    from .handlers import handle_check, handle_sandbox, handle_sweep, handle_get_report, handle_scan_content

    if tool_name == "policy_scout_check":
        return handle_check(params)
    if tool_name == "policy_scout_sandbox":
        return handle_sandbox(params)
    if tool_name == "policy_scout_sweep":
        return handle_sweep(params)
    if tool_name == "policy_scout_get_report":
        return handle_get_report(params)
    if tool_name == "policy_scout_scan_content":
        return handle_scan_content(params)
    raise ValueError(f"Unhandled tool: {tool_name}")


# ── Main dispatch loop ────────────────────────────────────────────────────────

def _process_message(msg: dict, session: McpSession) -> Optional[dict]:
    """Process one JSON-RPC message. Returns response dict or None for notifications."""
    method = msg.get("method", "")
    req_id = msg.get("id")  # None for notifications
    params = msg.get("params") or {}

    if method == "initialize":
        return _handle_initialize(req_id, params, session)

    if method == "initialized":
        return None  # notification, no response

    if not session.initialized and method != "initialize":
        if req_id is None:
            return None  # silently drop unrecognized notifications before init
        return _err(req_id, -32002, "Server not initialized")

    if method == "tools/list":
        return _handle_tools_list(req_id)

    if method == "tools/call":
        return _handle_tools_call(req_id, params, session)

    if method == "ping":
        return _ok(req_id, {})

    # Unknown method — only error if it had an id (requests, not notifications)
    if req_id is not None:
        return _err(req_id, -32601, f"Method not found: {method}")

    return None


def run_server(stdin=None, stdout=None) -> None:
    """Run the MCP stdio server loop until EOF."""
    from ..audit.store import AuditStore, AuditEvent
    from ..audit.events import EventType
    from ..core.ids import generate_id

    in_stream = stdin or sys.stdin
    out_stream = stdout or sys.stdout

    session_id = generate_id("mcp")
    session = McpSession(session_id=session_id)
    set_session(session)

    audit = AuditStore()
    audit.write(AuditEvent(
        event_type=EventType.MCP_SERVER_STARTED,
        summary="MCP server started",
        data={"session_id": session_id, "protocol_version": _MCP_VERSION},
    ))

    try:
        for raw_line in in_stream:
            raw_line = raw_line.strip()
            if not raw_line:
                continue
            try:
                msg = json.loads(raw_line)
            except json.JSONDecodeError as exc:
                _send(_err(None, -32700, f"Parse error: {exc}"), out_stream)
                continue

            try:
                response = _process_message(msg, session)
            except Exception as exc:
                response = _err(msg.get("id"), -32603, f"Internal error: {exc}")

            if response is not None:
                _send(response, out_stream)
    finally:
        audit.write(AuditEvent(
            event_type=EventType.MCP_SESSION_ENDED,
            summary="MCP session ended",
            data={"session_id": session_id, "tool_calls": session.tool_calls},
        ))
        set_session(None)
