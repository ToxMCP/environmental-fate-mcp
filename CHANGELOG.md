# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Structured request/response logging with correlation IDs for all MCP tool calls.
- `integrity_hash` field on `ConcentrationSurfaceBundle` for tamper-evident output signing.
- `regulatory_use_disclaimer` on every concentration bundle stating the output is not a dose or risk quotient.
- Adapter trace disclaimer on external-result normalized surfaces.
- `reconciliation_thresholds.json` governed defaults for mass spread, fraction spread, and cosine similarity thresholds.
- `temperature_c` field on scenarios with a limitation note when non-default temperatures are used.
- Scientific invariant tests for mass-balance closure, advection bounds, linear mass scaling, and half-life monotonicity.
- Auto-escalation of scientific review outcome to `escalate_model_review` when any surface carries an `ERROR` quality flag.

### Changed
- Non-positive half-life now raises a fatal `FateValidationError` instead of being silently clamped to 0.1 day.
- Probabilistic iteration cap reduced from unbounded to maximum 10,000 via Pydantic schema validation.
- Resource path inputs (`schema_name`, `example_name`, `doc_name`) are now validated against a whitelist before filesystem access.
- Contract artifact generation moved from import-time side effect in `server.py` to explicit `create_server()` initialization.
- Hard-coded reconciliation thresholds in `runtime.py` are now loaded from `defaults/v1/reconciliation_thresholds.json`.

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
