import json
import subprocess
import sys
from pathlib import Path

import pytest

from mcp_doctor.core import load_config, probe_server


ROOT = Path(__file__).parents[1]


def test_load_config_accepts_mcp_servers(tmp_path):
    path = tmp_path / "mcp.json"
    path.write_text(json.dumps({"mcpServers": {"demo": {"command": "python", "args": ["demo.py"]}}}))
    report = load_config(path)
    assert report.ok
    assert report.as_dict()["checks"][-1]["status"] == "pass"


def test_load_config_reports_invalid_json(tmp_path):
    path = tmp_path / "broken.json"
    path.write_text("{oops")
    report = load_config(path)
    assert not report.ok
    assert report.checks[0].name == "json"


def test_load_config_reports_bad_server_shape(tmp_path):
    path = tmp_path / "mcp.json"
    path.write_text(json.dumps({"mcpServers": {"demo": {"args": []}}}))
    report = load_config(path)
    assert not report.ok
    assert any(check.name == "server:demo" and check.status == "fail" for check in report.checks)


def test_probe_server_handshake():
    report = probe_server([sys.executable, str(ROOT / "demo" / "fake_server.py")])
    assert report.ok
    assert [check.name for check in report.checks] == ["initialize", "tools/list"]


def test_probe_server_missing_command():
    report = probe_server([str(ROOT / "does-not-exist")])
    assert not report.ok
    assert report.checks[0].name == "launch"


def test_cli_json_and_exit_code(tmp_path):
    path = tmp_path / "mcp.json"
    path.write_text(json.dumps({"mcpServers": {"demo": {"command": "python", "args": []}}}))
    result = subprocess.run(
        [sys.executable, "-m", "mcp_doctor", "config", str(path), "--json"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert json.loads(result.stdout)["ok"] is True
