"""Command line contract checks for small MCP server manifests."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

VERSION = "0.3.0"
GROUPS = ("tools", "resources", "prompts")


def _finding(code: str, path: str, message: str, *, severity: str = "error") -> dict[str, str]:
    return {"code": code, "path": path, "message": message, "severity": severity}


def _reject_nonfinite_json_constant(_value: str) -> None:
    """Keep Python's permissive JSON decoder inside the JSON specification."""

    raise ValueError("JSON must not contain NaN or Infinity")


def _load_document(path: str | None) -> dict[str, Any]:
    if path is None:
        return {group: [] for group in GROUPS}
    raw = sys.stdin.read() if path == "-" else Path(path).read_text(encoding="utf-8")
    value = json.loads(raw, parse_constant=_reject_nonfinite_json_constant)
    if not isinstance(value, dict):
        raise ValueError("the manifest root must be a JSON object")
    return value


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _contract_records(data: dict[str, Any]) -> dict[str, str]:
    """Return stable entry names and digests without printing manifest contents."""
    buckets: dict[str, list[str]] = {}
    for group in GROUPS:
        items = data.get(group, [])
        if not isinstance(items, list):
            continue
        for item in items:
            if isinstance(item, dict):
                name = item.get("name")
                label = name.strip() if isinstance(name, str) and name.strip() else "<unnamed>"
            else:
                label = "<invalid>"
            key = f"{group}:{label}"
            buckets.setdefault(key, []).append(_sha256(_canonical_json(item)))

    records: dict[str, str] = {}
    for base, digests in sorted(buckets.items()):
        ordered = sorted(digests)
        for index, digest in enumerate(ordered, start=1):
            key = base if len(ordered) == 1 else f"{base}[{index}]"
            records[key] = digest
    return records


def _fingerprint(data: dict[str, Any]) -> str:
    return _sha256(_canonical_json(_contract_records(data)))


def _baseline_diff(current: dict[str, str], baseline: dict[str, str]) -> dict[str, Any]:
    current_keys = set(current)
    baseline_keys = set(baseline)
    changed = [
        {"key": key, "baseline_sha256": baseline[key], "current_sha256": current[key]}
        for key in sorted(current_keys & baseline_keys)
        if current[key] != baseline[key]
    ]
    added = [{"key": key, "sha256": current[key]} for key in sorted(current_keys - baseline_keys)]
    removed = [{"key": key, "sha256": baseline[key]} for key in sorted(baseline_keys - current_keys)]
    return {"added": added, "removed": removed, "changed": changed}


def _required_findings(label: str, schema: dict[str, Any]) -> list[dict[str, str]]:
    """Flag `required` names that the schema never defines in `properties`."""
    required = schema.get("required")
    if required is None:
        return []
    if not isinstance(required, list) or not all(isinstance(name, str) for name in required):
        return [_finding("MCP012", label, "inputSchema.required must be an array of names")]
    properties = schema.get("properties")
    defined = set(properties) if isinstance(properties, dict) else set()
    missing = sorted(set(required) - defined)
    if not missing:
        return []
    return [
        _finding(
            "MCP012",
            label,
            "inputSchema.required names undefined properties: " + ", ".join(missing),
            severity="warning",
        )
    ]


def _validate(
    data: dict[str, Any], *, require_timeout: bool = False
) -> tuple[list[dict[str, str]], dict[str, int]]:
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
            if group == "resources":
                uri = item.get("uri")
                if not isinstance(uri, str) or not uri.strip():
                    findings.append(_finding("MCP011", item_path, "resource needs a non-empty uri"))
            if group != "tools":
                continue
            label = name.strip() if isinstance(name, str) and name.strip() else item_path
            if not isinstance(item.get("description"), str) or not item["description"].strip():
                findings.append(_finding("MCP002", label, "tool needs a non-empty description"))
            schema = item.get("inputSchema")
            if not isinstance(schema, dict):
                findings.append(_finding("MCP003", label, "tool needs an object inputSchema"))
            else:
                findings.extend(_required_findings(label, schema))
            # `timeout` is not part of the MCP Tool object; clients own timeouts.
            # It is checked only as an opt-in manifest extension.
            timeout = item.get("timeout")
            if timeout is None:
                if require_timeout:
                    findings.append(
                        _finding("MCP004", label, "declare a positive timeout", severity="warning")
                    )
            elif isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or timeout <= 0:
                findings.append(_finding("MCP007", label, "timeout must be a positive number"))
            elif isinstance(timeout, float) and not math.isfinite(timeout):
                findings.append(_finding("MCP009", label, "timeout must be a finite positive number"))
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
    lines.append(f"fingerprint {result['fingerprint']}")
    baseline = result.get("baseline")
    if baseline:
        if baseline["match"]:
            lines.append(f"baseline matched ({baseline['fingerprint']})")
        else:
            lines.append(
                "baseline drift: "
                f"{len(baseline['added'])} added, "
                f"{len(baseline['removed'])} removed, "
                f"{len(baseline['changed'])} changed"
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
    parser.add_argument(
        "--require-timeout",
        action="store_true",
        help="warn when a tool omits the non-standard `timeout` manifest extension",
    )
    parser.add_argument("--baseline", help="compare the current contract with another manifest")
    parser.add_argument(
        "--fail-on-drift",
        action="store_true",
        help="return exit 1 when --baseline differs",
    )
    parser.add_argument("--version", action="version", version=f"mcp-doctor {VERSION}")
    args = parser.parse_args(argv)

    input_error = False
    baseline_error = False
    data: dict[str, Any] = {group: [] for group in GROUPS}
    try:
        data = _load_document(args.path)
        findings, counts = _validate(data, require_timeout=args.require_timeout)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        input_error = True
        findings = [_finding("MCP000", args.path or "<input>", str(exc))]
        counts = {group: 0 for group in GROUPS}

    baseline_result: dict[str, Any] | None = None
    if args.baseline:
        try:
            if args.baseline == "-":
                raise ValueError("baseline must be a file path, not stdin")
            baseline_data = _load_document(args.baseline)
            baseline_records = _contract_records(baseline_data)
            current_records = _contract_records(data)
            diff = _baseline_diff(current_records, baseline_records)
            baseline_result = {
                "path": args.baseline,
                "fingerprint": _fingerprint(baseline_data),
                "match": not any(diff.values()),
                **diff,
            }
            if not baseline_result["match"]:
                findings.append(
                    _finding(
                        "MCP010",
                        "<baseline>",
                        "manifest differs from baseline",
                        severity="error" if args.fail_on_drift else "warning",
                    )
                )
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            baseline_error = True
            findings.append(_finding("MCP008", args.baseline, str(exc)))

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
        "fingerprint": _fingerprint(data),
        "baseline": baseline_result,
    }
    print(json.dumps(result, indent=2, sort_keys=True) if args.json else _render_text(result))
    if input_error or baseline_error:
        return 2
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
