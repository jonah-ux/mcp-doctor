import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from mcp_doctor.cli import main


FIXTURE = Path(__file__).parent / "../conformance/agent-systems-lab.json"


class AgentSystemsLabConformanceTests(unittest.TestCase):
    def run_cli(self, *args, stdin=""):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), mock.patch("sys.stdin", io.StringIO(stdin)):
            code = main(list(args))
        return code, json.loads(output.getvalue())

    def write(self, value):
        handle = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        with handle:
            json.dump(value, handle)
        self.addCleanup(lambda: Path(handle.name).unlink(missing_ok=True))
        return handle.name

    def test_manifest_pins_native_owner_and_shared_adapter(self):
        manifest = json.loads(FIXTURE.read_text(encoding="utf-8"))
        self.assertEqual(manifest["schema"], "agent-systems-lab-mcp-conformance/v1")
        self.assertEqual(manifest["owner"], "mcp-doctor")
        self.assertEqual(manifest["native_schema"], "mcp-doctor/v1")
        self.assertEqual(manifest["shared_adapter"]["schema"], "agent-proof/interop/v1")
        self.assertEqual(len(manifest["cases"]), 5)
        self.assertTrue(manifest["privacy"]["entry_names_and_digests_only"])

    def test_clean_warning_and_strict_states_match_manifest(self):
        clean = self.write({"tools": [{"name": "search", "description": "Find", "inputSchema": {}, "timeout": 5}]})
        code, result = self.run_cli("check", clean, "--json")
        self.assertEqual(code, 0)
        self.assertTrue(result["ok"])
        missing_timeout = self.write({"tools": [{"name": "search", "description": "Find", "inputSchema": {}}]})
        warning_code, warning = self.run_cli("check", missing_timeout, "--require-timeout", "--json")
        self.assertEqual(warning_code, 0)
        self.assertEqual(warning["findings"][0]["code"], "MCP004")
        strict_code, strict = self.run_cli(
            "check", missing_timeout, "--require-timeout", "--strict", "--json"
        )
        self.assertEqual(strict_code, 1)
        self.assertFalse(strict["ok"])
        self.assertEqual(strict["findings"][0]["severity"], "error")

    def test_baseline_drift_and_malformed_input_fail_closed(self):
        baseline = self.write({"tools": [{"name": "search", "description": "Find", "inputSchema": {}, "timeout": 5}]})
        current = self.write({"tools": [{"name": "search", "description": "Changed", "inputSchema": {}, "timeout": 5}]})
        code, result = self.run_cli("check", current, "--baseline", baseline, "--fail-on-drift", "--json")
        self.assertEqual(code, 1)
        self.assertFalse(result["baseline"]["match"])
        self.assertEqual(result["findings"][0]["code"], "MCP010")
        malformed_code, malformed = self.run_cli("check", "-", "--json", stdin="{")
        self.assertEqual(malformed_code, 2)
        self.assertEqual(malformed["findings"][0]["code"], "MCP000")
