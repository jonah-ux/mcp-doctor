# MCP Doctor

![MCP server contract linter workflow](docs/header.svg)

**Check tools, resources, prompts, schemas, and safety metadata before an agent sees them.**

[![CI](https://github.com/jonah-ux/mcp-doctor/actions/workflows/ci.yml/badge.svg)](https://github.com/jonah-ux/mcp-doctor/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11%2B-3776ab)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-22c55e)](LICENSE)

MCP Doctor is a small, offline-friendly CLI for catching missing names, descriptions,
input schemas, and timeouts in an MCP server manifest. It emits stable diagnostic codes
for humans and machine callers, so a CI job or coding agent can act on the same result.

## Try it in 30 seconds

```bash
python -m pip install git+https://github.com/jonah-ux/mcp-doctor.git@main
mcp-doctor check examples/valid-server.json
```

```text
MCP Doctor 0.2.4
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

## See it work

The demo shows both sides of the contract: a clean manifest passes, while a missing description and timeout fail with stable diagnostic codes.

```text
MCP Doctor 0.2.4
ok contract passed (1 tools, 1 resources, 1 prompts)

x MCP002 search: tool needs a non-empty description
! MCP004 search: declare a positive timeout
```

## Related tools

Use [Agent Policy](https://github.com/jonah-ux/agent-policy) for capability decisions, [Agent Eval Kit](https://github.com/jonah-ux/agent-eval-kit) for repeatable command fixtures, and [Agent Proof](https://github.com/jonah-ux/agent-proof) to retain the diagnostic result.

## Development

```bash
python -m unittest discover -s tests
python -m build --sdist --wheel
python demos/demo.py
```

Read the [release guide](docs/releasing.md) before publishing. The project does not claim
permissions, isolation, verification, or provider behavior beyond the fields it can prove.

MIT licensed. Contributions and sanitized bug reports are welcome.
