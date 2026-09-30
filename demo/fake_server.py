"""A tiny fake MCP server used by the demo and tests."""

from __future__ import annotations

import json
import sys


def read_message():
    headers = {}
    while True:
        line = sys.stdin.buffer.readline()
        if not line or line == b"\r\n":
            break
        key, value = line.decode().strip().split(":", 1)
        headers[key.lower()] = value.strip()
    length = int(headers["content-length"])
    return json.loads(sys.stdin.buffer.read(length))


def send(message):
    body = json.dumps(message, separators=(",", ":")).encode()
    sys.stdout.buffer.write(f"Content-Length: {len(body)}\r\n\r\n".encode() + body)
    sys.stdout.buffer.flush()


def main():
    while True:
        try:
            request = read_message()
        except (EOFError, KeyError, ValueError, json.JSONDecodeError):
            return
        if not request:
            return
        if request.get("id") == 1:
            send({
                "jsonrpc": "2.0",
                "id": 1,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "mcp-doctor-demo", "version": "0.1.0"},
                },
            })
        elif request.get("id") == 2:
            send({
                "jsonrpc": "2.0",
                "id": 2,
                "result": {"tools": [{"name": "hello", "description": "Say hello"}]},
            })


if __name__ == "__main__":
    main()
