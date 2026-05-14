# Environmental Fate MCP v0.5.0

Version: `0.5.0`
Release status: `ready_for_screening_release`
This is an internal bounded-screening release gate, not a statement of regulator acceptance, submission approval, or source-engine scientific equivalence.

## Highlights
- `143` JSON schemas and `139` generated examples are published for the release surface.
- `232` repository test functions and `57` tools / `22` prompts / `32` resources back the released MCP surface.
- `48` governed workflows are available across `3` supported model families and `2` experimental model family.
- `34` governed scientific validation claims and `28` governed scientific reference cases are included.
- `4` governed regulatory handoff profiles are published for downstream suite consumers.
- `4` synthetic erosion/sediment validation demo cases are published for reviewer-facing screening QA orientation.
- `8` governed external benchmark replay cases are published for deterministic screening corroboration.
- `11` governed default sensitivity profiles are published for reviewer-facing assumption transparency.
- `2` experimental fugacity screening method profiles are published with Level I/II validation checks.
- `34` claim rows and `5` model-family rows are published in the scientific evidence-quality matrix.
- Release asset provenance is supported through GitHub Artifact Attestations for the wheel, sdist, checksums, release-bundle manifest, and trust pack.

## Verification Summary
- Release checks passed: `37/37`.
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
- Fugacity screening validation passed: `True`.
- Scientific evidence-quality matrix passed: `True`.

## Scientific Change Log
- Shipped-default numeric deltas recorded this release: `0` parameter(s), with `0` marked as materially output-affecting.
- Defaults rebaseline review status: `reviewed_no_numeric_default_change`.
- Mandatory reference-family claims meeting the reviewer-grade corroboration bar: `10/10`.
- Machine-readable worksheet pack readiness: `10/10` claim-linked worksheet artifacts.
- `reference_mass_balance` remains the reviewer-grade anchor for decision-facing bounded screening.
- `advective_screening_mass_balance` remains experimental and non-promotable in this release.
- Adapter posture remains normalization parity only; this release does not claim source-engine scientific equivalence.
- Release attestations, when present on GitHub release assets, establish build provenance only; they are not scientific validation or regulator acceptance.

## Known Gaps
- No GIS-scale dispersion in v0.5.
- No rainfall-runoff generation, channel routing, deposition-field modelling, SWAT/PRZM execution, or native WEPP execution in v0.5.
- Fugacity equilibrium screening is experimental Level I/II-style partitioning only; no Level III intermedia-transfer, advective export, calibration, field validation, or regulatory acceptance claim is added.
- External benchmark packs are deterministic screening corroboration fixtures, not curated field validation datasets.
- The evidence-quality matrix grades release-review evidence posture only; it does not add field validation, calibration evidence, regulator acceptance, or model promotion.
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
- `fugacity-screening-validation-report.json` checks experimental Level I/II fugacity mass conservation, loss balance, and boundary language.
- `scientific-evidence-quality-matrix-report.json` separates reviewer-grade, source-grounded, internal-oracle, synthetic-demo, and deferred/gap evidence tiers.
- `scientific-validation-narrative.json` summarizes benchmark, sensitivity, probabilistic manifest, and boundary interpretation for reviewers.
- `release-bundle-manifest.json` records SHA-256 checksums for the bundled release files.
- `SHA256SUMS` provides a reviewer-friendly checksum list for manual verification.

## Intended Use
This release remains an auditable environmental screening MCP inside the broader ToxMCP suite.
It does not claim to be a final regulatory decision engine, a PBPK engine, a dietary intake engine, or a full GIS dispersion platform.
