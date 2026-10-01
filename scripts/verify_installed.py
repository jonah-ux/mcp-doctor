"""Exercise a wheel/sdist consumer, without importing the source checkout."""

import json
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    with (root / "pyproject.toml").open("rb") as handle:
        version = tomllib.load(handle)["project"]["version"]
    # -I excludes the checkout, PYTHONPATH, and the user site from import resolution.
    with tempfile.TemporaryDirectory() as directory:
        cwd = Path(directory)
        origin = subprocess.check_output(
            [sys.executable, "-I", "-c", "import mcp_doctor; print(mcp_doctor.__file__)"],
            cwd=cwd, text=True,
        ).strip()
        if Path(origin).resolve().is_relative_to(root):
            raise RuntimeError("consumer resolved the source checkout")

        def run(*args: str, expected: int = 0) -> str:
            result = subprocess.run(
                [sys.executable, "-I", "-m", "mcp_doctor.cli", *args],
                cwd=cwd, text=True, capture_output=True, timeout=15,
            )
            if result.returncode != expected:
                raise RuntimeError(
                    f"Expected exit {expected}, got {result.returncode}: {result.stderr}"
                )
            return result.stdout

        if run("--version").strip() != f"mcp-doctor {version}":
            raise RuntimeError("installed CLI version differs from package version")
        if "--strict" not in run("--help"):
            raise RuntimeError("installed help omitted strict mode")
        clean = json.loads(run("check", str(root / "examples/valid-server.json"), "--json"))
        if not clean["ok"] or clean["schema"] != "mcp-doctor/v1":
            raise RuntimeError("valid contract did not pass")
        broken = json.loads(run(
            "check", str(root / "examples/invalid-server.json"),
            "--strict", "--json", expected=1,
        ))
        codes = {finding["code"] for finding in broken["findings"]}
        if broken["ok"] or not {"MCP002", "MCP004"} <= codes:
            raise RuntimeError("invalid contract lost its stable diagnostics")
        missing = json.loads(run("check", str(cwd / "absent.json"), "--json", expected=2))
        if missing["findings"][0]["code"] != "MCP000":
            raise RuntimeError("unreadable input lost its error contract")
    print(f"Installed consumer verified: {version}; import={origin}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
