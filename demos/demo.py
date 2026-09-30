import json
import pathlib
import tempfile

from mcp_doctor.cli import main

ROOT = pathlib.Path(__file__).parents[1]

print("MCP Doctor demo: a clean contract is boring on purpose")
main(["check", str(ROOT / "examples" / "valid-server.json")])
print()
print("MCP Doctor demo: the broken fixture is useful because it fails loudly")
main(["check", str(ROOT / "examples" / "invalid-server.json")])
