import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from mcp_doctor.cli import main


class CliTests(unittest.TestCase):
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

    def test_missing_timeout_is_warning_unless_strict(self):
        path = self.write_manifest(
            {"tools": [{"name": "search", "description": "Find things", "inputSchema": {}}]}
        )
        code, output = self.run_cli("check", path, "--json")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output)["findings"][0]["code"], "MCP004")

        strict_code, strict_output = self.run_cli("check", path, "--strict", "--json")
        self.assertEqual(strict_code, 1)
        self.assertFalse(json.loads(strict_output)["ok"])

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


if __name__ == "__main__":
    unittest.main()
