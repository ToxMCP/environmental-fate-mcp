# Adapter SPI

External model-family adapters must normalize into Environmental Fate MCP contracts rather than expose model-native payloads directly.

## Required obligations

- declare supported workflow classes and model family identifiers
- return normalized `concentration_surface` records
- preserve scenario identifiers, geography, and time semantics
- attach provenance and limitation notes
- surface any unsupported semantics instead of silently dropping them

## Reference boundary

The bundled `adapter_stub` plugin is a synthetic example that exercises the normalization path without binding Environmental Fate MCP to a specific external engine.
The bundled `external_result_adapter` harness goes further by normalizing a concrete engine-like payload shape with compartment-code mapping and unit validation.
The normalized JSON/CSV payload shape is now a public MCP contract through `fate_import_external_result_payload` and `adapters://public-import-manifest`.
Concrete legacy or branded desktop importers remain governed harness details rather than the stable public MCP contract.
These adapter paths support contract normalization and provenance continuity only; they do not certify source-engine scientific validity or scientific equivalence to native Environmental Fate MCP physics.

## Internal fixture path

Illustrative engine-like payload fixtures are stored at:

- `config/adapter-fixtures/illustrative_external_engine_payload.json`
- `config/adapter-fixtures/illustrative_external_engine_payload.csv`
- `config/adapter-fixtures/legacy_screening_desktop_export.csv`
- `config/adapter-fixtures/legacy_screening_desktop_export_weight_basis.csv`

The harness loader accepts both normalized `.json` and `.csv` interchange formats, and can also detect the legacy desktop export CSV shape for governed internal adapter testing and import normalization.
Legacy imports may carry `steady_state` or `time_bucket` semantics, and the adapter validation dossier now checks that those time bounds survive normalization.
The full adapter import catalog is exposed through `adapters://import-manifest`, while the stable public subset is exposed through `adapters://public-import-manifest`.
Accepted non-canonical concentration units are governed through `defaults://adapter-unit-conversions` rather than hard-coded in the harness.
Soil and sediment weight-basis aliases such as `mg/kg ww` are also normalized through that governed registry, with canonical Environmental Fate MCP outputs preserved on a dry-weight `mg/kg` basis.
