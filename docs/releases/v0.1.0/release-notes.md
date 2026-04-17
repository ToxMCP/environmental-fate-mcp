# Environmental Fate MCP v0.1.0

Version: `0.1.0`
Release status: `ready_for_screening_release`

## Highlights
- `107` JSON schemas and `103` generated examples are published for the release surface.
- `39` governed workflows are available across `3` supported model families and `1` experimental model family.
- `30` governed scientific validation claims and `25` governed scientific reference cases are included.
- `4` governed regulatory handoff profiles are published for downstream suite consumers.

## Verification Summary
- Release checks passed: `19/19`.
- Mandatory scientific validation claims uncovered: `0`.
- Benchmarks passed: `True`.
- Downstream interoperability passed: `True`.
- Regulatory handoff governance passed: `True`.
- Scientific review artifacts passed: `True`.

## Known Gaps
- No GIS-scale dispersion in v0.1.
- No direct human dose calculation in Environmental Fate MCP.
- No dietary intake workflows in Environmental Fate MCP.
- No PBPK execution in Environmental Fate MCP.
- Adapter stub is illustrative and not a validated external engine.

## Bundle Contents
- Machine-readable release reports are published alongside this note in the same directory.
- `release-bundle-manifest.json` records SHA-256 checksums for the bundled release files.
- `SHA256SUMS` provides a reviewer-friendly checksum list for manual verification.

## Intended Use
This release remains an auditable environmental screening MCP inside the broader ToxMCP suite.
It does not claim to be a final regulatory decision engine, a PBPK engine, a dietary intake engine, or a full GIS dispersion platform.
