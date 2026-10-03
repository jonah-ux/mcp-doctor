# Release provenance

MCP Doctor publishes source releases from annotated `vMAJOR.MINOR.PATCH` tags. The release workflow
checks the semantic tag, builds a wheel and sdist, writes `SHA256SUMS`, and verifies a clean wheel
consumer before publishing prerelease assets.

The public audit checks these workflow markers, the dependency/license declarations, and the tracked
source surface. It does not claim that GitHub, a package index, or a downstream machine provides a
complete supply-chain guarantee. Artifact verification is only `pass` when an explicit distribution
directory and checksum manifest are supplied; otherwise the audit reports `unavailable`.
