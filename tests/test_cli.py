import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from mcp_doctor import __version__
from mcp_doctor.cli import main


class CliTests(unittest.TestCase):
    def test_version_flag_uses_package_version(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            with self.assertRaises(SystemExit) as raised:
                main(["--version"])
        self.assertEqual(raised.exception.code, 0)
        self.assertEqual(output.getvalue().strip(), f"mcp-doctor {__version__}")

    def run_cli(self, *args: str, stdin: str = "") -> tuple[int, str]:
        output = io.StringIO()
        with contextlib.redirect_stdout(output), mock.patch("sys.stdin", io.StringIO(stdin)):
            code = main(list(args))
        return code, output.getvalue()

    def write_manifest(self, value: object) -> str:
        handle = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        with handle:
            json.dump(value, handle)
        self.addCleanup(lambda: Path(handle.name).unlink(missing_ok=True))
        return handle.name

    def test_clean_manifest_passes_and_reports_inventory(self):
        path = self.write_manifest(
            {"tools": [{"name": "search", "description": "Find things", "inputSchema": {}, "timeout": 5}]}
        )
        code, output = self.run_cli("check", path, "--json")
        result = json.loads(output)
        self.assertEqual(code, 0)
        self.assertTrue(result["ok"])
        self.assertEqual(result["counts"]["tools"], 1)
        self.assertEqual(result["findings"], [])

    def test_spec_tool_without_timeout_passes_strict(self):
        # `timeout` is not part of the MCP Tool object, so a spec-shaped tool must pass.
        path = self.write_manifest(
            {"tools": [{"name": "search", "description": "Find things", "inputSchema": {"type": "object"}}]}
        )
        code, output = self.run_cli("check", path, "--strict", "--json")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output)["findings"], [])

    def test_missing_timeout_is_opt_in_warning_unless_strict(self):
        path = self.write_manifest(
            {"tools": [{"name": "search", "description": "Find things", "inputSchema": {}}]}
        )
        code, output = self.run_cli("check", path, "--require-timeout", "--json")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output)["findings"][0]["code"], "MCP004")

        strict_code, strict_output = self.run_cli(
            "check", path, "--require-timeout", "--strict", "--json"
        )
        self.assertEqual(strict_code, 1)
        self.assertFalse(json.loads(strict_output)["ok"])

    def test_present_timeout_is_still_validated_without_opt_in(self):
        path = self.write_manifest(
            {"tools": [{"name": "search", "description": "Find", "inputSchema": {}, "timeout": 0}]}
        )
        code, output = self.run_cli("check", path, "--json")
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(output)["findings"][0]["code"], "MCP007")

    def test_resource_without_uri_is_an_error(self):
        path = self.write_manifest({"resources": [{"name": "readme"}]})
        code, output = self.run_cli("check", path, "--json")
        self.assertEqual(code, 1)
        finding = json.loads(output)["findings"][0]
        self.assertEqual((finding["code"], finding["severity"]), ("MCP011", "error"))

        ok_path = self.write_manifest({"resources": [{"uri": "docs://readme", "name": "readme"}]})
        ok_code, _ = self.run_cli("check", ok_path, "--json")
        self.assertEqual(ok_code, 0)

    def test_required_names_must_be_defined_properties(self):
        schema = {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query", "limit"]}
        path = self.write_manifest({"tools": [{"name": "search", "description": "Find", "inputSchema": schema}]})
        code, output = self.run_cli("check", path, "--json")
        self.assertEqual(code, 0)
        finding = json.loads(output)["findings"][0]
        self.assertEqual((finding["code"], finding["severity"]), ("MCP012", "warning"))
        self.assertIn("limit", finding["message"])
        self.assertNotIn("query", finding["message"])

        bad = {"type": "object", "required": "query"}
        bad_path = self.write_manifest({"tools": [{"name": "search", "description": "Find", "inputSchema": bad}]})
        bad_code, bad_output = self.run_cli("check", bad_path, "--json")
        self.assertEqual(bad_code, 1)
        self.assertEqual(json.loads(bad_output)["findings"][0]["severity"], "error")

    def test_invalid_tool_has_stable_codes_and_text_output(self):
        path = self.write_manifest({"tools": [{"name": "", "description": "", "inputSchema": {}}]})
        code, output = self.run_cli("check", path)
        self.assertEqual(code, 1)
        self.assertIn("MCP001", output)
        self.assertIn("MCP002", output)

    def test_stdin_and_bad_json_are_explicit(self):
        code, output = self.run_cli(
            "check",
            "-",
            "--json",
            stdin='{"tools": [{"name": "search", "description": "Find", "inputSchema": {}, "timeout": 1}]}',
        )
        self.assertEqual(code, 0)
        self.assertTrue(json.loads(output)["ok"])

        bad_code, bad_output = self.run_cli("check", "-", "--json", stdin="{")
        self.assertEqual(bad_code, 2)
        self.assertEqual(json.loads(bad_output)["findings"][0]["code"], "MCP000")

    def test_baseline_is_deterministic_and_reports_drift(self):
        baseline = self.write_manifest(
            {
                "tools": [
                    {"name": "search", "description": "Find things", "inputSchema": {}, "timeout": 5},
                    {"name": "write", "description": "Write things", "inputSchema": {}, "timeout": 5},
                ]
            }
        )
        current = self.write_manifest(
            {
                "tools": [
                    {"name": "write", "description": "Write more things", "inputSchema": {}, "timeout": 5},
                    {"name": "search", "description": "Find things", "inputSchema": {}, "timeout": 5},
                    {"name": "delete", "description": "Delete things", "inputSchema": {}, "timeout": 5},
                ]
            }
        )
        code, output = self.run_cli("check", current, "--baseline", baseline, "--json")
        result = json.loads(output)
        self.assertEqual(code, 0)
        self.assertFalse(result["baseline"]["match"])
        self.assertEqual([item["key"] for item in result["baseline"]["added"]], ["tools:delete"])
        self.assertEqual([item["key"] for item in result["baseline"]["changed"]], ["tools:write"])
        self.assertEqual(result["findings"][0]["code"], "MCP010")
        self.assertEqual(result["findings"][0]["severity"], "warning")

        strict_code, strict_output = self.run_cli(
            "check", current, "--baseline", baseline, "--fail-on-drift", "--json"
        )
        strict_result = json.loads(strict_output)
        self.assertEqual(strict_code, 1)
        self.assertFalse(strict_result["ok"])
        self.assertEqual(strict_result["findings"][0]["severity"], "error")

    def test_baseline_bad_json_is_explicit(self):
        baseline = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        baseline.write("{")
        baseline.close()
        self.addCleanup(lambda: Path(baseline.name).unlink(missing_ok=True))
        code, output = self.run_cli("check", "-", "--baseline", baseline.name, "--json", stdin="{}")
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(output)["findings"][0]["code"], "MCP008")


if __name__ == "__main__":
    unittest.main()
