"""Command line contract checks for small MCP server manifests."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

VERSION = "0.2.4"
GROUPS = ("tools", "resources", "prompts")


def _finding(code: str, path: str, message: str, *, severity: str = "error") -> dict[str, str]:
    return {"code": code, "path": path, "message": message, "severity": severity}


def _load_document(path: str | None) -> dict[str, Any]:
    if path is None:
        return {group: [] for group in GROUPS}
    raw = sys.stdin.read() if path == "-" else Path(path).read_text(encoding="utf-8")
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError("the manifest root must be a JSON object")
    return value


def _validate(data: dict[str, Any]) -> tuple[list[dict[str, str]], dict[str, int]]:
    findings: list[dict[str, str]] = []
    counts = {group: 0 for group in GROUPS}
    for group in GROUPS:
        items = data.get(group, [])
        if not isinstance(items, list):
            findings.append(_finding("MCP005", group, f"{group} must be an array"))
            continue
        counts[group] = len(items)
        for index, item in enumerate(items):
            item_path = f"{group}[{index}]"
            if not isinstance(item, dict):
                findings.append(_finding("MCP006", item_path, "entry must be an object"))
                continue
            name = item.get("name")
            if not isinstance(name, str) or not name.strip():
                findings.append(_finding("MCP001", item_path, "missing name"))
            if group != "tools":
                continue
            label = name.strip() if isinstance(name, str) and name.strip() else item_path
            if not isinstance(item.get("description"), str) or not item["description"].strip():
                findings.append(_finding("MCP002", label, "tool needs a non-empty description"))
            if not isinstance(item.get("inputSchema"), dict):
                findings.append(_finding("MCP003", label, "tool needs an object inputSchema"))
            timeout = item.get("timeout")
            if timeout is None:
                findings.append(
                    _finding("MCP004", label, "declare a positive timeout", severity="warning")
                )
            elif isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or timeout <= 0:
                findings.append(_finding("MCP007", label, "timeout must be a positive number"))
    return findings, counts


def _render_text(result: dict[str, Any]) -> str:
    lines = [f"MCP Doctor {VERSION}"]
    for finding in result["findings"]:
        marker = "!" if finding["severity"] == "warning" else "x"
        lines.append(f"{marker} {finding['code']} {finding['path']}: {finding['message']}")
    counts = result["counts"]
    inventory = ", ".join(f"{counts[group]} {group}" for group in GROUPS)
    lines.append(
        f"{'ok contract passed' if result['ok'] else 'failed contract has errors'} ({inventory})"
    )
    if result["strict"] and any(f["severity"] == "error" for f in result["findings"]):
        lines.append("strict mode: warnings are treated as errors")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="mcp-doctor",
        description="Check MCP tools, resources, prompts, schemas, and safety metadata.",
    )
    parser.add_argument("command", choices=["check"])
    parser.add_argument("path", nargs="?", help="JSON manifest path; use '-' for stdin")
    parser.add_argument("--json", action="store_true", help="emit agent-friendly JSON")
    parser.add_argument("--strict", action="store_true", help="treat warnings as errors")
    parser.add_argument("--version", action="version", version=f"mcp-doctor {VERSION}")
    args = parser.parse_args(argv)

    input_error = False
    try:
        data = _load_document(args.path)
        findings, counts = _validate(data)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        input_error = True
        findings = [_finding("MCP000", args.path or "<input>", str(exc))]
        counts = {group: 0 for group in GROUPS}

    if args.strict:
        findings = [
            {**finding, "severity": "error"} if finding["severity"] == "warning" else finding
            for finding in findings
        ]
    result = {
        "schema": "mcp-doctor/v1",
        "version": VERSION,
        "strict": args.strict,
        "ok": not any(finding["severity"] == "error" for finding in findings),
        "findings": findings,
        "counts": counts,
    }
    print(json.dumps(result, indent=2, sort_keys=True) if args.json else _render_text(result))
    if input_error:
        return 2
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
