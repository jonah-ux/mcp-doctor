"""Command-line interface for mcp-doctor."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional, Sequence

from .core import Report, load_config, probe_server


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mcp-doctor",
        description="Diagnose an MCP stdio server or validate an MCP JSON config.",
    )
    subparsers = parser.add_subparsers(dest="action", required=True)
    config = subparsers.add_parser("config", help="validate a JSON server configuration")
    config.add_argument("path", type=Path)
    server = subparsers.add_parser("server", help="probe an MCP stdio server")
    server.add_argument("command", nargs="+", help="server command followed by its arguments")
    server.add_argument("--timeout", type=float, default=3.0, help="seconds to wait per response (default: 3)")
    for command in (config, server):
        command.add_argument("--json", action="store_true", dest="as_json", help="emit machine-readable JSON")
    return parser


def _render(report: Report, as_json: bool) -> None:
    if as_json:
        print(json.dumps(report.as_dict(), indent=2, sort_keys=True))
        return
    marker = "PASS" if report.ok else "FAIL"
    print(f"{marker}  {report.target}")
    for check in report.checks:
        print(f"  [{check.status.upper():4}] {check.name}: {check.message}")


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _parser().parse_args(argv)
    if args.action == "config":
        report = load_config(args.path)
    else:
        report = probe_server(args.command, timeout=max(args.timeout, 0.1))
    _render(report, args.as_json)
    return 0 if report.ok else 1


if __name__ == "__main__":
    sys.exit(main())
