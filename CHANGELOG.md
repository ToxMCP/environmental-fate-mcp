# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.5.0] - 2026-05-03

### Added
- Governed scientific evidence-quality rubric exposed at `defaults://scientific-evidence-quality-rubric`.
- Claim-by-claim and model-family evidence-quality matrix exposed at `release://scientific-evidence-quality-matrix-report`.
- Public evidence-quality matrix guide and release-gated validator checks for false field-validation, calibration, regulatory-acceptance, and source-engine-equivalence claims.

### Changed
- Release metadata now reports evidence-quality matrix claim rows and model-family posture rows.
- Scientific trust pack, trust brief, public release guide, validation framework, operator guide, and applicability docs now include evidence-quality matrix interpretation.

## [0.4.0] - 2026-05-03

### Added
- Experimental non-default `fugacity_equilibrium_screening` model family for Level I/II equilibrium screening challenge review.
- Governed fugacity method profiles, validation report, prompt guidance, reference cases, benchmark support, and sensitivity profiles.

### Changed
- Public trust artifacts now describe fugacity screening as experimental Level I/II only, not Level III, routing, calibration, source-engine equivalence, field validation, or regulator acceptance.

## [0.3.1] - 2026-05-01

### Added
- GitHub release provenance workflow that builds wheel/sdist assets, uploads release checksums, and generates Sigstore-backed artifact attestations through GitHub Artifact Attestations.
- Release provenance guide with online verification commands for attested wheel, sdist, and checksum assets.

### Changed
- Public release docs now describe signed release asset provenance as a supply-chain trust layer, separate from scientific validation or regulator acceptance.

## [0.3.0] - 2026-05-01

### Added
- Governed external benchmark replay pack with release-gated deterministic tolerance checks.
- Governed default sensitivity profiles and `fate_build_default_sensitivity_report` for reviewer-facing assumption transparency.
- Optional probabilistic sample manifests with summary mode, capped row records, iteration health, and stable hashes.
- v0.3.0 scientific validation narrative and release reports for benchmark, sensitivity, and probabilistic audit interpretation.

### Changed
- Public release docs and release bundle now point at the v0.3.0 scientific trust surface.
- Release validator now fails closed on malformed benchmark packs or default sensitivity profile drift.

## [0.2.1] - 2026-05-01

### Added
- `reported_time_semantics` on concentration surfaces to clarify that `steady_state` means end-of-duration screening, not infinite-time equilibrium.
- Conservative external-payload import limits for payload bytes and surface rows, with operator overrides.
- Runtime-level probabilistic iteration guard matching the public request schema cap.

### Changed
- Public release docs now point at the `v0.2.1` patch release surface.
- Non-historical v0.1 wording updated to current-public-release language.
- Release-fraction invariant wording is now more explicit in reviewer-facing docs.

### Security
- External JSON/CSV/legacy payload imports now fail closed on oversized files or excessive rows before normalization.

## [0.2.0] - 2026-05-01

### Added
- Structured request/response logging with correlation IDs for all MCP tool calls.
- `integrity_hash` field on `ConcentrationSurfaceBundle` for tamper-evident output signing.
- `integrity_hash` field on `RegulatoryHandoffPackage` for end-to-end tamper-evident downstream handoff export.
- `regulatory_use_disclaimer` on every concentration bundle stating the output is not a dose or risk quotient.
- `regulatory_use_disclaimer` on every regulatory handoff package preserving the concentration-only boundary.
- Adapter trace disclaimer on external-result normalized surfaces.
- `reconciliation_thresholds.json` governed defaults for mass spread, fraction spread, and cosine similarity thresholds.
- `temperature_c` field on scenarios with a limitation note when non-default temperatures are used.
- Scientific invariant tests for mass-balance closure, advection bounds, linear mass scaling, and half-life monotonicity.
- Auto-escalation of scientific review outcome to `escalate_model_review` when any surface carries an `ERROR` quality flag.
- Public governance docs (`SECURITY.md`, `SUPPORT.md`, `CONTRIBUTING.md`) and GitHub collaboration templates.
- A public release checklist for tagged release preparation and repository-setting review.
- A deterministic public release bundle generator with release notes, checksums, and machine-readable release reports.
- Governed synthetic erosion/sediment validation demo pack with release-gated classification checks for public screening-QA orientation.

### Changed
- Project license changed from MIT to Apache License 2.0.
- Non-positive half-life now raises a fatal `FateValidationError` instead of being silently clamped to 0.1 day.
- Probabilistic iteration cap reduced from unbounded to maximum 10,000 via Pydantic schema validation.
- Resource path inputs (`schema_name`, `example_name`, `doc_name`) are now validated against a whitelist before filesystem access.
- Contract artifact generation is now deterministic across reruns so committed examples remain reproducible.
- `create_server()` now validates shipped artifacts instead of regenerating schemas/examples/default manifests at startup.
- CI now gates on the full release validator and a startup smoke check, not only artifact generation plus `pytest`.
- Hard-coded reconciliation thresholds in `runtime.py` are now loaded from `defaults/v1/reconciliation_thresholds.json`.

### Removed
- Internal audit bundles, patch helpers, and scratch research exports from the public repository surface.

### Security
- Closed path-traversal vectors in MCP resource handlers.
- Added request/response audit logging to support regulatory traceability.

## [0.1.0] - 2025-04-08

### Added
- Initial release of the Environmental Fate MCP server.
- Reference mass-balance and advective screening model families.
- Time-bucket and steady-state run modes.
- Release-evidence reconciliation with quality-weighted averaging.
- Scientific validation claims framework with 30 governed claims.
- Benchmark fixture suite (54+ fixtures) with deterministic tolerances.
- Regulatory handoff profiles for ToxMCP suite integration.
- External result adapter supporting JSON, CSV, and legacy desktop exports.
- Provenance builder with four-way source classification.
- Model-family selection, comparison, and challenge review workflows.
