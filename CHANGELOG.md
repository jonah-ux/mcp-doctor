# Changelog

## Unreleased

- **Fix:** `MCP004` (missing `timeout`) no longer fires by default. `timeout` is not part of the MCP Tool object, so every spec-compliant server failed `--strict`. It is now opt-in with `--require-timeout`. A timeout that is present is still validated (`MCP007`, `MCP009`).
- Add `MCP011` (error): a resource must have a non-empty `uri`, as `resources/list` requires.
- Add `MCP012`: `inputSchema.required` must be an array of names (error), and every required name should be defined in `properties` (warning).
- Verified against the `tools/list` output of all 7 modelcontextprotocol/servers reference servers (53 tools): all pass `--strict` with no findings.

- Add deterministic contract fingerprints and baseline drift reports with added, removed, and changed entry digests.
- Add `--fail-on-drift` for CI gates while preserving warning-only baseline comparisons by default.
- Bump the source candidate to 0.3.0 and expose the fingerprint in JSON and text reports.

- Add stable diagnostic severities and codes for malformed manifests.
- Add stdin input, strict mode, human-readable summaries, and explicit input exit codes.
- Add valid and invalid fixtures plus behavior-focused CLI tests.

## 0.1.0 - 2026-09-30

Initial focused release with a stable CLI contract and synthetic demo.
