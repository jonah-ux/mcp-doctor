# Mcp Server Contract Linter

![MCP server contract linter workflow](docs/header.svg)

**Check tools, resources, prompts, schemas, and safety metadata before an agent sees them.**

## Install

```bash
pip install git+https://github.com/jonah-ux/mcp-doctor.git@v0.1.0
```

## Quick start

```bash
mcp-doctor --help
```

The first release is intentionally small, offline-friendly, and easy to inspect. JSON output is designed for agents; diagnostics stay explicit.

## Development

```bash
python -m unittest discover -s tests
python -m build --sdist --wheel
python demos/demo.py
```

## Limits

Read the command help and [release guide](docs/releasing.md) before using this in automation. This project does not claim permissions, isolation, verification, or provider behavior beyond the output fields it can prove.

MIT licensed. Contributions and sanitized bug reports are welcome.
