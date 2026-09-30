#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
PYTHON="${PYTHON:-python3}"
"$PYTHON" -m mcp_doctor.cli config demo/mcp.json
"$PYTHON" -m mcp_doctor.cli server "$PYTHON" demo/fake_server.py
