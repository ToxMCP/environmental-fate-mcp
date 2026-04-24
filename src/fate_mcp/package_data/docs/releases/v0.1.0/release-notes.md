# Environmental Fate MCP v0.1.0

Version: `0.1.0`
Release status: `ready_for_screening_release`
This is an internal bounded-screening release gate, not a statement of regulator acceptance, submission approval, or source-engine scientific equivalence.

## Highlights
- `110` JSON schemas and `106` generated examples are published for the release surface.
- `163` repository test functions and `50` tools / `19` prompts / `24` resources back the released MCP surface.
- `41` governed workflows are available across `3` supported model families and `1` experimental model family.
- `30` governed scientific validation claims and `25` governed scientific reference cases are included.
- `4` governed regulatory handoff profiles are published for downstream suite consumers.

## Verification Summary
- Release checks passed: `32/32`.
- Mandatory scientific validation claims uncovered: `0`.
- Benchmarks passed: `True`.
- Defaults evidence governance passed: `True`.
- External corroboration governance passed: `True`.
- Downstream interoperability passed: `True`.
- Regulatory handoff governance passed: `True`.
- Scientific review artifacts passed: `True`.

## Scientific Change Log
- Shipped-default numeric deltas recorded this release: `0` parameter(s), with `0` marked as materially output-affecting.
- Defaults rebaseline review status: `reviewed_no_numeric_default_change`.
- Mandatory reference-family claims meeting the reviewer-grade corroboration bar: `10/10`.
- Machine-readable worksheet pack readiness: `10/10` claim-linked worksheet artifacts.
- `reference_mass_balance` remains the reviewer-grade anchor for decision-facing bounded screening.
- `advective_screening_mass_balance` remains experimental and non-promotable in this release.
- Adapter posture remains normalization parity only; this release does not claim source-engine scientific equivalence.

## Known Gaps
- No GIS-scale dispersion in v0.1.
- No direct human dose calculation in Environmental Fate MCP.
- No dietary intake workflows in Environmental Fate MCP.
- No PBPK execution in Environmental Fate MCP.
- Branded desktop-model ingestion remains limited to governed adapter profiles; only normalized external payload JSON/CSV is a public MCP import contract in v0.1.

## Bundle Contents
- Machine-readable release reports are published alongside this note in the same directory.
- `scientific-trust-pack.md` provides a reviewer-ready trust summary for the release.
- `scientific-trust-brief.md` provides a compact one-shot trust briefing for reviewers and agents.
- `reference-corroboration-report.json` gives the mandatory reference-family corroboration matrix.
- `reference-worksheet-manifest.json` links each mandatory reference claim to its worksheet and expected-output artifacts.
- `reference-worksheet-pack/` contains the claim-linked worksheet and expected-output artifacts used for skeptical reviewer handoff.
- `advective-promotion-bar-report.json` explains why the advective family remains experimental in this release.
- `release-bundle-manifest.json` records SHA-256 checksums for the bundled release files.
- `SHA256SUMS` provides a reviewer-friendly checksum list for manual verification.

## Intended Use
This release remains an auditable environmental screening MCP inside the broader ToxMCP suite.
It does not claim to be a final regulatory decision engine, a PBPK engine, a dietary intake engine, or a full GIS dispersion platform.
