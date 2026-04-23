# External Payload Contract

Environmental Fate MCP now exposes one stable public adapter contract: normalized external payload import.

## Public Profiles

- `normalized_external_payload_json`
- `normalized_external_payload_csv`

Inspect them through:
- `adapters://public-import-manifest`
- `fate_request_external_result_import`

Import through:
- `fate_import_external_result_payload`

## What the Public Contract Does

The public contract accepts a normalized external payload file plus a matched Environmental Fate scenario and run configuration.
It then returns a canonical `ConcentrationEstimationResult` under the `external_result_adapter` model family.

The import path preserves:
- scenario id
- run mode
- compartment mapping
- canonical concentration units
- provenance bundle continuity from the normalization boundary onward

The import path also discloses:
- unit conversions
- basis conversions
- unsupported steady-state interval bounds
- lack of native source-engine equation traces

This contract does not certify the source engine's scientific validity, regulatory suitability, or equivalence to native Environmental Fate MCP transport physics. It certifies only governed normalization into the published Fate MCP concentration contract.

## What Stays Non-Public

These remain governed adapter details rather than the stable public MCP API:
- branded desktop export shapes
- legacy desktop parsing shortcuts
- EUSES/EPI-specific harness details

Those paths may still exist inside the repository for validation and interoperability coverage, but they should not be treated as the long-term public contract.

## Request Shape

Use `ImportExternalResultPayloadRequest` with:
- `scenario`
- `run_options.model_family = external_result_adapter`
- `run_options.run_mode`
- `payload_path`
- `import_profile_id`

Use `fate_import_external_result_payload_skeleton` if you want a validated starting point.

## File Access Boundary

`payload_path` must resolve inside an allowed import root. By default, only shipped adapter fixtures under `config/adapter-fixtures` are allowed. Operators can add directories with `FATE_MCP_IMPORT_ROOTS` using the platform path separator. Symlinks are resolved before the boundary check, so links that point outside allowed roots are rejected.
