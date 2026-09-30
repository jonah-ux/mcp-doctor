"""Core checks for MCP configuration files and stdio servers.

The implementation intentionally speaks only the small JSON-RPC subset needed
for a useful first diagnostic: ``initialize`` followed by ``tools/list``.
"""

from __future__ import annotations

import json
import os
import selectors
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence


@dataclass
class Check:
    """One diagnostic result."""

    name: str
    status: str
    message: str
    details: Dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "message": self.message,
            **({"details": self.details} if self.details else {}),
        }


@dataclass
class Report:
    """A collection of checks with a stable JSON representation."""

    target: str
    checks: List[Check]

    @property
    def ok(self) -> bool:
        return all(check.status == "pass" for check in self.checks)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "target": self.target,
            "ok": self.ok,
            "checks": [check.as_dict() for check in self.checks],
        }


def _check(name: str, status: str, message: str, **details: Any) -> Check:
    return Check(name=name, status=status, message=message, details=details)


def load_config(path: Path) -> Report:
    """Validate a JSON MCP config and report every actionable issue."""

    checks: List[Check] = []
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        return Report(str(path), [_check("read", "fail", f"cannot read file: {exc}")])

    try:
        document = json.loads(raw)
    except json.JSONDecodeError as exc:
        return Report(
            str(path),
            [_check("json", "fail", f"invalid JSON at line {exc.lineno}, column {exc.colno}")],
        )

    if not isinstance(document, dict):
        return Report(str(path), [_check("shape", "fail", "top-level JSON value must be an object")])

    servers = document.get("mcpServers", document.get("servers"))
    if servers is None:
        return Report(
            str(path),
            [_check("servers", "fail", "missing 'mcpServers' (or compatibility key 'servers')")],
        )
    if not isinstance(servers, dict) or not servers:
        return Report(str(path), [_check("servers", "fail", "servers must be a non-empty object")])

    checks.append(_check("json", "pass", "valid JSON"))
    checks.append(_check("servers", "pass", f"found {len(servers)} server configuration(s)"))
    for name, config in servers.items():
        label = f"server:{name}"
        if not isinstance(name, str) or not name.strip():
            checks.append(_check(label, "fail", "server name must be a non-empty string"))
            continue
        if not isinstance(config, dict):
            checks.append(_check(label, "fail", "server configuration must be an object"))
            continue
        command = config.get("command")
        args = config.get("args", [])
        if not isinstance(command, str) or not command.strip():
            checks.append(_check(label, "fail", "missing non-empty 'command'"))
        elif not isinstance(args, list) or not all(isinstance(arg, str) for arg in args):
            checks.append(_check(label, "fail", "'args' must be a list of strings"))
        else:
            checks.append(_check(label, "pass", f"command configured: {command}"))
    return Report(str(path), checks)


def _frame(message: Dict[str, Any]) -> bytes:
    body = json.dumps(message, separators=(",", ":")).encode("utf-8")
    return b"Content-Length: " + str(len(body)).encode("ascii") + b"\r\n\r\n" + body


def _read_message(stream: Any, timeout: float) -> Dict[str, Any]:
    """Read one Content-Length framed JSON-RPC message from a pipe."""

    selector = selectors.DefaultSelector()
    selector.register(stream, selectors.EVENT_READ)
    deadline = time.monotonic() + timeout
    header = bytearray()
    while b"\r\n\r\n" not in header:
        remaining = deadline - time.monotonic()
        if remaining <= 0 or not selector.select(remaining):
            raise TimeoutError("timed out waiting for server headers")
        chunk = os.read(stream.fileno(), 1)
        if not chunk:
            raise EOFError("server closed stdout before sending a response")
        header.extend(chunk)
        if len(header) > 8192:
            raise ValueError("response headers exceed 8192 bytes")
    header_text, _, remainder = bytes(header).partition(b"\r\n\r\n")
    content_length = None
    for line in header_text.decode("ascii", errors="strict").split("\r\n"):
        key, separator, value = line.partition(":")
        if separator and key.lower() == "content-length":
            content_length = int(value.strip())
    if content_length is None or content_length < 0:
        raise ValueError("response is missing a valid Content-Length header")
    payload = bytearray(remainder)
    while len(payload) < content_length:
        remaining = deadline - time.monotonic()
        if remaining <= 0 or not selector.select(remaining):
            raise TimeoutError("timed out waiting for server body")
        chunk = os.read(stream.fileno(), content_length - len(payload))
        if not chunk:
            raise EOFError("server closed stdout during response")
        payload.extend(chunk)
    value = json.loads(bytes(payload[:content_length]).decode("utf-8"))
    if not isinstance(value, dict):
        raise ValueError("response JSON must be an object")
    return value


def probe_server(
    command: Sequence[str], *, timeout: float = 3.0, cwd: Optional[Path] = None
) -> Report:
    """Run a stdio MCP server and check initialization plus tool listing."""

    target = " ".join(command)
    checks: List[Check] = []
    if not command:
        return Report(target, [_check("command", "fail", "command cannot be empty")])
    try:
        process = subprocess.Popen(
            list(command),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(cwd) if cwd else None,
        )
    except OSError as exc:
        return Report(target, [_check("launch", "fail", f"could not launch server: {exc}")])

    try:
        assert process.stdin is not None and process.stdout is not None
        process.stdin.write(
            _frame(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "clientInfo": {"name": "mcp-doctor", "version": "0.1.0"},
                    },
                }
            )
        )
        process.stdin.flush()
        initialized = _read_message(process.stdout, timeout)
        if initialized.get("id") != 1 or "error" in initialized:
            raise ValueError("initialize returned an error or unexpected id")
        checks.append(_check("initialize", "pass", "server accepted MCP initialization"))
        process.stdin.write(_frame({"jsonrpc": "2.0", "method": "notifications/initialized"}))
        process.stdin.write(_frame({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}))
        process.stdin.flush()
        tools = _read_message(process.stdout, timeout)
        if tools.get("id") != 2 or "error" in tools:
            raise ValueError("tools/list returned an error or unexpected id")
        result = tools.get("result", {})
        tool_list = result.get("tools", []) if isinstance(result, dict) else []
        if not isinstance(tool_list, list):
            raise ValueError("tools/list response has a non-list tools field")
        checks.append(_check("tools/list", "pass", f"server listed {len(tool_list)} tool(s)"))
    except (EOFError, OSError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
        checks.append(_check("protocol", "fail", str(exc)))
    finally:
        process.kill()
        process.wait()
    return Report(target, checks)
