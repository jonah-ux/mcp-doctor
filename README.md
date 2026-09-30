# MCP Doctor

![MCP server contract linter workflow](docs/header.svg)

**Check tools, resources, prompts, schemas, and safety metadata before an agent sees them.**

MCP Doctor is a small, offline-friendly CLI for catching missing names, descriptions,
input schemas, and timeouts in an MCP server manifest. It emits stable diagnostic codes
for humans and machine callers, so a CI job or coding agent can act on the same result.

## Try it in 30 seconds

```bash
python -m pip install git+https://github.com/jonah-ux/mcp-doctor.git@main
mcp-doctor check examples/valid-server.json
```

```text
MCP Doctor 0.2.0
ok contract passed (1 tools, 1 resources, 1 prompts)
```

Try the failing fixture to see actionable diagnostics:

```bash
mcp-doctor check examples/invalid-server.json
mcp-doctor check examples/valid-server.json --json
```

The JSON schema is intentionally tiny and stable:

```json
{"schema":"mcp-doctor/v1","ok":true,"findings":[],"counts":{"tools":1,"resources":1,"prompts":1}}
```

## Agent-friendly usage

Pass `-` to read a manifest from stdin. Use `--strict` when a missing timeout should fail CI;
otherwise it is reported as a warning. Exit codes are `0` for a clean or warning-only report,
`1` for contract findings, and `2` for unreadable or malformed input.

```bash
cat server.json | mcp-doctor check - --strict --json
```

## Development

```bash
python -m unittest discover -s tests
python -m build --sdist --wheel
python demos/demo.py
```

Read the [release guide](docs/releasing.md) before publishing. The project does not claim
permissions, isolation, verification, or provider behavior beyond the fields it can prove.

MIT licensed. Contributions and sanitized bug reports are welcome.
