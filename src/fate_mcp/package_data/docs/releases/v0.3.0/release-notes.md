# Environmental Fate MCP v0.3.0

Version: `0.3.0`
Release status: `ready_for_screening_release`
This is an internal bounded-screening release gate, not a statement of regulator acceptance, submission approval, or source-engine scientific equivalence.

## Highlights
- `139` JSON schemas and `135` generated examples are published for the release surface.
- `195` repository test functions and `57` tools / `21` prompts / `29` resources back the released MCP surface.
- `48` governed workflows are available across `3` supported model families and `1` experimental model family.
- `30` governed scientific validation claims and `25` governed scientific reference cases are included.
- `4` governed regulatory handoff profiles are published for downstream suite consumers.
- `4` synthetic erosion/sediment validation demo cases are published for reviewer-facing screening QA orientation.
- `4` governed external benchmark replay cases are published for deterministic screening corroboration.
- `7` governed default sensitivity profiles are published for reviewer-facing assumption transparency.

## Verification Summary
- Release checks passed: `35/35`.
- Mandatory scientific validation claims uncovered: `0`.
- Benchmarks passed: `True`.
- Defaults evidence governance passed: `True`.
- External corroboration governance passed: `True`.
- Downstream interoperability passed: `True`.
- Regulatory handoff governance passed: `True`.
- Scientific review artifacts passed: `True`.
- Erosion/sediment validation demo pack passed: `True`.
- External benchmark pack passed: `True`.
- Default sensitivity profiles passed: `True`.

## Scientific Change Log
- Shipped-default numeric deltas recorded this release: `0` parameter(s), with `0` marked as materially output-affecting.
- Defaults rebaseline review status: `reviewed_no_numeric_default_change`.
- Mandatory reference-family claims meeting the reviewer-grade corroboration bar: `10/10`.
- Machine-readable worksheet pack readiness: `10/10` claim-linked worksheet artifacts.
- `reference_mass_balance` remains the reviewer-grade anchor for decision-facing bounded screening.
- `advective_screening_mass_balance` remains experimental and non-promotable in this release.
- Adapter posture remains normalization parity only; this release does not claim source-engine scientific equivalence.

## Known Gaps
- No GIS-scale dispersion in v0.3.
- No rainfall-runoff generation, channel routing, deposition-field modelling, or native WEPP execution in v0.3.
- External benchmark packs are deterministic screening corroboration fixtures, not curated field validation datasets.
- Erosion/sediment validation demos remain synthetic screening-QA demonstrations, not curated field benchmark validation.
- No direct human dose calculation in Environmental Fate MCP.
- No dietary intake workflows in Environmental Fate MCP.
- No PBPK execution in Environmental Fate MCP.
- Branded desktop-model ingestion remains limited to governed adapter profiles; only normalized external payload JSON/CSV is a public MCP import contract in this release.

## Bundle Contents
- Machine-readable release reports are published alongside this note in the same directory.
- `scientific-trust-pack.md` provides a reviewer-ready trust summary for the release.
- `scientific-trust-brief.md` provides a compact one-shot trust briefing for reviewers and agents.
- `reference-corroboration-report.json` gives the mandatory reference-family corroboration matrix.
- `reference-worksheet-manifest.json` links each mandatory reference claim to its worksheet and expected-output artifacts.
- `reference-worksheet-pack/` contains the claim-linked worksheet and expected-output artifacts used for skeptical reviewer handoff.
- `advective-promotion-bar-report.json` explains why the advective family remains experimental in this release.
- `erosion-sediment-validation-demo-report.json` checks the synthetic erosion/sediment validation demo pack and expected fit classifications.
- `external-validation-benchmark-report.json` checks deterministic external benchmark replay cases and expected tolerances.
- `default-sensitivity-report.json` checks governed default sensitivity profile execution and boundary language.
- `scientific-validation-narrative.json` summarizes benchmark, sensitivity, probabilistic manifest, and boundary interpretation for reviewers.
- `release-bundle-manifest.json` records SHA-256 checksums for the bundled release files.
- `SHA256SUMS` provides a reviewer-friendly checksum list for manual verification.

## Intended Use
This release remains an auditable environmental screening MCP inside the broader ToxMCP suite.
It does not claim to be a final regulatory decision engine, a PBPK engine, a dietary intake engine, or a full GIS dispersion platform.
