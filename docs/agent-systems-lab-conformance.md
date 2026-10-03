# Agent Systems Lab MCP conformance

MCP Doctor remains the owner of `mcp-doctor/v1`. This fixture and test make its
native diagnostic boundary explicit without importing Agent Proof at runtime.

The owner proves clean contracts, warning-only missing timeouts, strict failure,
baseline drift, malformed-input refusal, stable finding codes, and name/digest
summary boundaries. Agent Proof owns the downstream `agent-proof/interop/v1`
projection; this repository does not create a second interop registry.

Run the focused test from a fresh checkout. All manifests are synthetic and no
MCP server or provider is contacted.
