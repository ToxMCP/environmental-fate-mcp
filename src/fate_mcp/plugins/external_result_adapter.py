from __future__ import annotations

import csv
from datetime import datetime
from io import StringIO
from pathlib import Path

from pydantic import BaseModel, Field

from fate_mcp.errors import FateRegistryError, FateValidationError
from fate_mcp.models import (
    AdapterSemanticMapping,
    SemanticLossClassification,
    AdapterFixtureDescriptor,
    AdapterImportManifest,
    AdapterImportProfile,
    Compartment,
    ConcentrationEstimationResult,
    ConcentrationSurface,
    EnvironmentalReleaseScenario,
    FateAssumptionRecord,
    FateModelRunOptions,
    FateRunSummary,
    LimitationNote,
    Media,
    ModelFamily,
    QualityFlag,
    RunMode,
    Severity,
    SourceClassification,
    TimeWindow,
)
from fate_mcp.plugins.base import PluginKey
from fate_mcp.plugins.reference_mass_balance import ReferenceMassBalancePlugin
from fate_mcp.provenance import ProvenanceBuilder
from fate_mcp.result_meta import ResultMetadata


class ExternalEngineSurfacePayload(BaseModel):
    compartment_code: str
    concentration: float = Field(ge=0.0)
    unit: str
    context_scope: str
    mode: str = "steady_state"
    interval_start: datetime | None = None
    interval_end: datetime | None = None
    notes: list[str] = Field(default_factory=list)


class ExternalEngineResultPayload(BaseModel):
    engine_name: str
    engine_version: str
    surfaces: list[ExternalEngineSurfacePayload]


EXTERNAL_PAYLOAD_CSV_COLUMNS = [
    "engine_name",
    "engine_version",
    "compartment_code",
    "concentration",
    "unit",
    "context_scope",
    "mode",
    "interval_start",
    "interval_end",
    "notes",
]
REQUIRED_EXTERNAL_PAYLOAD_CSV_COLUMNS = [
    "engine_name",
    "engine_version",
    "compartment_code",
    "concentration",
    "unit",
    "context_scope",
    "mode",
    "interval_start",
    "interval_end",
]

LEGACY_DESKTOP_EXPORT_TYPE = "legacy_screening_desktop_export_v1"
EUSES_EXPORT_TYPE = "euses_screening_export_v1"
EPI_SUITE_EXPORT_TYPE = "epi_suite_screening_export_v1"
SUPPORTED_DESKTOP_EXPORT_TYPES = {
    LEGACY_DESKTOP_EXPORT_TYPE,
    EUSES_EXPORT_TYPE,
    EPI_SUITE_EXPORT_TYPE,
}
LEGACY_DESKTOP_EXPORT_COLUMNS = [
    "compartment_label",
    "bulk_concentration",
    "bulk_unit",
    "interval_start",
    "interval_end",
    "notes",
]
LEGACY_DESKTOP_COMPARTMENT_LABEL_MAP = {
    "regional air": "AIR_REGIONAL",
    "surface water": "WATER_SURFACE",
    "agricultural soil": "SOIL_TOP",
    "freshwater sediment": "SEDIMENT_FRESH",
}
ADAPTER_IMPORT_PROFILES = [
    AdapterImportProfile(
        profile_id="normalized_external_payload_json",
        display_name="Normalized External Payload JSON",
        accepted_extensions=[".json"],
        accepted_modes=[RunMode.STEADY_STATE, RunMode.TIME_BUCKET],
        description="Canonical engine-like JSON payload consumed directly by the adapter harness.",
    ),
    AdapterImportProfile(
        profile_id="normalized_external_payload_csv",
        display_name="Normalized External Payload CSV",
        accepted_extensions=[".csv"],
        accepted_modes=[RunMode.STEADY_STATE, RunMode.TIME_BUCKET],
        description="Canonical engine-like CSV payload consumed directly by the adapter harness.",
    ),
    AdapterImportProfile(
        profile_id=LEGACY_DESKTOP_EXPORT_TYPE,
        display_name="Legacy Screening Desktop Export",
        accepted_extensions=[".csv"],
        accepted_modes=[RunMode.STEADY_STATE, RunMode.TIME_BUCKET],
        description="Concrete legacy desktop screening export normalized into Fate MCP concentrations.",
    ),
    AdapterImportProfile(
        profile_id=EUSES_EXPORT_TYPE,
        display_name="EUSES Desktop Screening Export",
        accepted_extensions=[".csv"],
        accepted_modes=[RunMode.STEADY_STATE, RunMode.TIME_BUCKET],
        description="EUSES screening export normalized into Fate MCP concentrations.",
        semantic_mapping=AdapterSemanticMapping(
            semantic_loss=SemanticLossClassification.MINOR,
            compartment_semantics="EUSES regional compartments map to Fate MCP generic compartments.",
            time_semantics="Steady-state mode maps end-of-duration screening without resolving multi-year temporal profiles.",
            spatial_scale_semantics="Regional scale assumed; continental scale explicitly excluded from screening normalizations.",
            basis_semantics="Dry weight normalization applied to soil/sediment.",
            release_partition_semantics="Release fractions map 1:1."
        ),
    ),
    AdapterImportProfile(
        profile_id=EPI_SUITE_EXPORT_TYPE,
        display_name="EPI Suite Desktop Screening Export",
        accepted_extensions=[".csv"],
        accepted_modes=[RunMode.STEADY_STATE, RunMode.TIME_BUCKET],
        description="EPI Suite screening export normalized into Fate MCP concentrations.",
        semantic_mapping=AdapterSemanticMapping(
            semantic_loss=SemanticLossClassification.MATERIAL_BUT_BOUNDED,
            compartment_semantics="Level III Mackay compartments map directly to Fate MCP.",
            time_semantics="Steady state assumed as standard EPI Suite Level III default.",
            spatial_scale_semantics="Default generic environment area.",
            basis_semantics="Dry weight mapped.",
            release_partition_semantics="Maps directly to Level III emission modes."
        ),
    ),
]
ADAPTER_FIXTURE_CATALOG = [
    {
        "fixture_name": "illustrative_external_engine_payload_json",
        "path": "config/adapter-fixtures/illustrative_external_engine_payload.json",
        "import_profile": "normalized_external_payload_json",
        "format": "json",
        "expected_engine_name": "illustrative-external-engine",
        "supported_modes": [RunMode.STEADY_STATE],
    },
    {
        "fixture_name": "illustrative_external_engine_payload_csv",
        "path": "config/adapter-fixtures/illustrative_external_engine_payload.csv",
        "import_profile": "normalized_external_payload_csv",
        "format": "csv",
        "expected_engine_name": "illustrative-external-engine",
        "supported_modes": [RunMode.STEADY_STATE],
    },
    {
        "fixture_name": "illustrative_external_engine_payload_alt_units",
        "path": "config/adapter-fixtures/illustrative_external_engine_payload_alt_units.csv",
        "import_profile": "normalized_external_payload_csv",
        "format": "csv",
        "expected_engine_name": "illustrative-external-engine",
        "supported_modes": [RunMode.STEADY_STATE],
    },
    {
        "fixture_name": "legacy_screening_desktop_export",
        "path": "config/adapter-fixtures/legacy_screening_desktop_export.csv",
        "import_profile": LEGACY_DESKTOP_EXPORT_TYPE,
        "format": "csv",
        "expected_engine_name": "legacy-screening-desktop",
        "supported_modes": [RunMode.STEADY_STATE],
    },
    {
        "fixture_name": "legacy_screening_desktop_export_time_bucket",
        "path": "config/adapter-fixtures/legacy_screening_desktop_export_time_bucket.csv",
        "import_profile": LEGACY_DESKTOP_EXPORT_TYPE,
        "format": "csv",
        "expected_engine_name": "legacy-screening-desktop",
        "supported_modes": [RunMode.TIME_BUCKET],
    },
    {
        "fixture_name": "legacy_screening_desktop_export_weight_basis",
        "path": "config/adapter-fixtures/legacy_screening_desktop_export_weight_basis.csv",
        "import_profile": LEGACY_DESKTOP_EXPORT_TYPE,
        "format": "csv",
        "expected_engine_name": "legacy-screening-desktop",
        "supported_modes": [RunMode.STEADY_STATE],
    },
    {
        "fixture_name": "euses_screening_export",
        "path": "config/adapter-fixtures/euses_screening_export.csv",
        "import_profile": EUSES_EXPORT_TYPE,
        "format": "csv",
        "expected_engine_name": "euses-screening-desktop",
        "supported_modes": [RunMode.STEADY_STATE],
    },
    {
        "fixture_name": "epi_suite_screening_export",
        "path": "config/adapter-fixtures/epi_suite_screening_export.csv",
        "import_profile": EPI_SUITE_EXPORT_TYPE,
        "format": "csv",
        "expected_engine_name": "epi-suite-screening",
        "supported_modes": [RunMode.STEADY_STATE],
    },
]


def _external_payload_format(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".json", ".csv"}:
        return suffix
    raise FateValidationError(
        code="unsupported_external_payload_format",
        message=f"Unsupported external payload format: {path.suffix or '<none>'}.",
        suggestion="Use a .json or .csv file for external payload interchange.",
        details={"path": str(path)},
    )


def _csv_value(row: dict[str, str | None], column: str) -> str | None:
    value = row.get(column)
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _required_csv_value(row: dict[str, str | None], row_number: int, column: str) -> str:
    value = _csv_value(row, column)
    if value is None:
        raise FateValidationError(
            code="external_payload_csv_missing_value",
            message=f"CSV payload row {row_number} is missing required column {column}.",
            suggestion="Populate the required engine and surface columns before importing the payload.",
            details={"row": row_number, "column": column},
        )
    return value


def _parse_legacy_export_metadata(text: str) -> tuple[dict[str, str], str]:
    lines = text.splitlines()
    metadata: dict[str, str] = {}
    table_start_index: int | None = None
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            continue
        row = next(csv.reader([line]))
        if row and row[0].strip() == LEGACY_DESKTOP_EXPORT_COLUMNS[0]:
            table_start_index = index
            break
        if len(row) != 2:
            raise FateValidationError(
                code="legacy_external_payload_invalid_metadata",
                message=f"Legacy desktop export metadata line is malformed: {line}",
                suggestion="Use key,value metadata rows before the compartment table.",
            )
        metadata[row[0].strip()] = row[1].strip()
    if table_start_index is None:
        raise FateValidationError(
            code="legacy_external_payload_missing_table",
            message="Legacy desktop export is missing the compartment table header.",
            suggestion="Add a compartment_label table after the metadata section.",
        )
    return metadata, "\n".join(lines[table_start_index:])


def external_payload_from_json(text: str) -> ExternalEngineResultPayload:
    return ExternalEngineResultPayload.model_validate_json(text)


def external_payload_to_json(payload: ExternalEngineResultPayload) -> str:
    return payload.model_dump_json(indent=2)


def external_payload_from_csv(text: str) -> ExternalEngineResultPayload:
    reader = csv.DictReader(StringIO(text))
    if reader.fieldnames is None:
        raise FateValidationError(
            code="external_payload_csv_missing_header",
            message="CSV payload is missing a header row.",
            suggestion="Add a header row with the supported external payload columns.",
        )
    missing_columns = sorted(set(REQUIRED_EXTERNAL_PAYLOAD_CSV_COLUMNS) - set(reader.fieldnames))
    if missing_columns:
        raise FateValidationError(
            code="external_payload_csv_missing_columns",
            message=f"CSV payload is missing required columns: {missing_columns}.",
            suggestion="Include all required engine and surface columns in the CSV header.",
            details={"missingColumns": missing_columns},
        )

    engine_names = set()
    engine_versions = set()
    surfaces = []

    for row_number, row in enumerate(reader, start=2):
        if not any((value or "").strip() for value in row.values()):
            continue
        engine_name = _required_csv_value(row, row_number, "engine_name")
        engine_version = _required_csv_value(row, row_number, "engine_version")
        concentration_text = _required_csv_value(row, row_number, "concentration")
        try:
            concentration = float(concentration_text)
        except ValueError as exc:
            raise FateValidationError(
                code="external_payload_csv_invalid_concentration",
                message=f"CSV payload row {row_number} has a non-numeric concentration value: {concentration_text}.",
                suggestion="Provide numeric concentration values in the canonical Fate MCP unit for the mapped compartment.",
                details={"row": row_number, "value": concentration_text},
            ) from exc

        engine_names.add(engine_name)
        engine_versions.add(engine_version)
        notes_text = _csv_value(row, "notes")
        surfaces.append(
            ExternalEngineSurfacePayload(
                compartment_code=_required_csv_value(row, row_number, "compartment_code"),
                concentration=concentration,
                unit=_required_csv_value(row, row_number, "unit"),
                context_scope=_required_csv_value(row, row_number, "context_scope"),
                mode=_csv_value(row, "mode") or "steady_state",
                interval_start=_csv_value(row, "interval_start"),
                interval_end=_csv_value(row, "interval_end"),
                notes=[item.strip() for item in notes_text.split("|")] if notes_text else [],
            )
        )

    if not surfaces:
        raise FateValidationError(
            code="external_payload_csv_empty",
            message="CSV payload does not contain any surface rows.",
            suggestion="Provide at least one normalized external surface row before importing the payload.",
        )
    if len(engine_names) != 1 or len(engine_versions) != 1:
        raise FateValidationError(
            code="external_payload_csv_inconsistent_engine_metadata",
            message="CSV payload mixes multiple engine_name or engine_version values.",
            suggestion="Normalize the CSV so every row belongs to a single external engine export.",
            details={
                "engineNames": sorted(engine_names),
                "engineVersions": sorted(engine_versions),
            },
        )
    return ExternalEngineResultPayload(
        engine_name=next(iter(engine_names)),
        engine_version=next(iter(engine_versions)),
        surfaces=surfaces,
    )


def _require_time_bucket_bounds(
    row: dict[str, str | None],
    row_number: int,
    context: str,
) -> tuple[str, str]:
    interval_start = _required_csv_value(row, row_number, "interval_start")
    interval_end = _required_csv_value(row, row_number, "interval_end")
    if interval_start is None or interval_end is None:
        raise FateValidationError(
            code=f"{context}_missing_interval_bounds",
            message=f"{context.replace('_', ' ')} row {row_number} is missing interval bounds for time_bucket mode.",
            suggestion="Provide interval_start and interval_end for every time_bucket surface row.",
            details={"row": row_number},
        )
    return interval_start, interval_end


def external_payload_from_legacy_desktop_export_csv(text: str) -> ExternalEngineResultPayload:
    metadata, table_text = _parse_legacy_export_metadata(text)
    export_type = metadata.get("export_type")
    if export_type not in SUPPORTED_DESKTOP_EXPORT_TYPES:
        raise FateValidationError(
            code="legacy_external_payload_unknown_type",
            message=f"Unsupported legacy desktop export type: {export_type or '<missing>'}.",
            suggestion=f"Set export_type to one of {SUPPORTED_DESKTOP_EXPORT_TYPES} for this importer.",
            details={"exportType": export_type},
        )
    profile = next((p for p in ADAPTER_IMPORT_PROFILES if p.profile_id == export_type), None)
    if profile and profile.semantic_mapping and profile.semantic_mapping.semantic_loss == SemanticLossClassification.NON_EQUIVALENT:
        raise FateValidationError(
            code="adapter_semantic_loss_non_equivalent",
            message=f"Export type {export_type} cannot be imported because semantic loss is NON_EQUIVALENT.",
            suggestion="Use an import profile that maps structurally equivalent or bounded compartments and modes.",
            details={"exportType": export_type}
        )
    mode = metadata.get("mode", "steady_state") or "steady_state"
    if mode not in {"steady_state", "time_bucket"}:
        raise FateValidationError(
            code="legacy_external_payload_invalid_mode",
            message=f"Unsupported legacy desktop export mode: {mode}.",
            suggestion="Use steady_state or time_bucket in the legacy export metadata.",
            details={"mode": mode},
        )
    missing_metadata = sorted(
        key for key in ("engine_name", "engine_version", "region_id") if not metadata.get(key)
    )
    if missing_metadata:
        raise FateValidationError(
            code="legacy_external_payload_missing_metadata",
            message=f"Legacy desktop export is missing required metadata: {missing_metadata}.",
            suggestion="Provide engine_name, engine_version, and region_id in the metadata section.",
            details={"missingMetadata": missing_metadata},
        )

    reader = csv.DictReader(StringIO(table_text))
    missing_columns = sorted(set(LEGACY_DESKTOP_EXPORT_COLUMNS[:3]) - set(reader.fieldnames or []))
    if missing_columns:
        raise FateValidationError(
            code="legacy_external_payload_missing_columns",
            message=f"Legacy desktop export is missing required columns: {missing_columns}.",
            suggestion="Include compartment_label, bulk_concentration, and bulk_unit in the compartment table.",
            details={"missingColumns": missing_columns},
        )
    if mode == "time_bucket":
        missing_time_columns = sorted(set(("interval_start", "interval_end")) - set(reader.fieldnames or []))
        if missing_time_columns:
            raise FateValidationError(
                code="legacy_external_payload_missing_time_columns",
                message=f"Legacy desktop export is missing required time-bucket columns: {missing_time_columns}.",
                suggestion="Include interval_start and interval_end in the legacy compartment table for time_bucket mode.",
                details={"missingColumns": missing_time_columns},
            )

    surfaces = []
    for row_number, row in enumerate(reader, start=2):
        if not any((value or "").strip() for value in row.values()):
            continue
        label = _required_csv_value(row, row_number, "compartment_label")
        compartment_info = LEGACY_DESKTOP_COMPARTMENT_LABEL_MAP.get(label.strip().lower())
        if compartment_info is None:
            raise FateValidationError(
                code="legacy_external_payload_unknown_compartment",
                message=f"Unsupported legacy desktop compartment label: {label}.",
                suggestion="Map the compartment label into a supported Fate MCP compartment before importing.",
                details={"compartmentLabel": label},
            )
        compartment_code = compartment_info
        provided_unit = _required_csv_value(row, row_number, "bulk_unit")
        concentration_text = _required_csv_value(row, row_number, "bulk_concentration")
        try:
            concentration = float(concentration_text)
        except ValueError as exc:
            raise FateValidationError(
                code="legacy_external_payload_invalid_concentration",
                message=f"Legacy desktop export row {row_number} has a non-numeric concentration value: {concentration_text}.",
                suggestion="Provide numeric bulk_concentration values in canonical units.",
                details={"row": row_number, "value": concentration_text},
            ) from exc
        notes = []
        note_text = _csv_value(row, "notes")
        if note_text:
            notes.append(note_text)
        notes.append("Imported from a concrete legacy desktop screening export shape.")
        interval_start = None
        interval_end = None
        if mode == "time_bucket":
            interval_start, interval_end = _require_time_bucket_bounds(
                row,
                row_number,
                "legacy_external_payload",
            )
        surfaces.append(
            ExternalEngineSurfacePayload(
                compartment_code=compartment_code,
                concentration=concentration,
                unit=provided_unit,
                context_scope=metadata["region_id"],
                mode=mode,
                interval_start=interval_start,
                interval_end=interval_end,
                notes=notes,
            )
        )

    if not surfaces:
        raise FateValidationError(
            code="legacy_external_payload_empty",
            message="Legacy desktop export does not contain any compartment rows.",
            suggestion="Provide at least one compartment row in the legacy export table.",
        )

    return ExternalEngineResultPayload(
        engine_name=metadata["engine_name"],
        engine_version=metadata["engine_version"],
        surfaces=surfaces,
    )


def external_payload_to_csv(payload: ExternalEngineResultPayload) -> str:
    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=EXTERNAL_PAYLOAD_CSV_COLUMNS)
    writer.writeheader()
    for surface in payload.surfaces:
        writer.writerow(
            {
                "engine_name": payload.engine_name,
                "engine_version": payload.engine_version,
                "compartment_code": surface.compartment_code,
                "concentration": surface.concentration,
                "unit": surface.unit,
                "context_scope": surface.context_scope,
                "mode": surface.mode,
                "interval_start": surface.interval_start.isoformat() if surface.interval_start else "",
                "interval_end": surface.interval_end.isoformat() if surface.interval_end else "",
                "notes": " | ".join(surface.notes),
            }
        )
    return buffer.getvalue().rstrip("\r\n")


def load_external_payload(path: Path) -> ExternalEngineResultPayload:
    payload_format = _external_payload_format(path)
    text = path.read_text()
    if payload_format == ".json":
        return external_payload_from_json(text)
    try:
        return external_payload_from_csv(text)
    except FateValidationError as exc:
        if exc.payload.code not in {
            "external_payload_csv_missing_header",
            "external_payload_csv_missing_columns",
        }:
            raise
    return external_payload_from_legacy_desktop_export_csv(text)


def build_adapter_import_manifest(repo_root: Path) -> AdapterImportManifest:
    fixtures = [
        AdapterFixtureDescriptor(
            fixture_name=item["fixture_name"],
            path=item["path"],
            import_profile=item["import_profile"],
            format=item["format"],
            expected_engine_name=item["expected_engine_name"],
            supported_modes=item["supported_modes"],
        )
        for item in ADAPTER_FIXTURE_CATALOG
        if (repo_root / item["path"]).exists()
    ]
    return AdapterImportManifest(
        profiles=ADAPTER_IMPORT_PROFILES,
        fixtures=fixtures,
    )


def adapter_fixture_descriptor(repo_root: Path, fixture_name: str) -> AdapterFixtureDescriptor | None:
    manifest = build_adapter_import_manifest(repo_root)
    for fixture in manifest.fixtures:
        if fixture.fixture_name == fixture_name:
            return fixture
    return None


def write_external_payload(path: Path, payload: ExternalEngineResultPayload) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload_format = _external_payload_format(path)
    serialized = (
        external_payload_to_json(payload)
        if payload_format == ".json"
        else external_payload_to_csv(payload)
    )
    path.write_text(serialized + "\n")
    return path


COMPARTMENT_CODE_MAP = {
    "AIR_REGIONAL": (Media.AIR, Compartment.AMBIENT_AIR, "mg/m3"),
    "WATER_SURFACE": (Media.WATER, Compartment.SURFACE_WATER, "mg/L"),
    "SOIL_TOP": (Media.SOIL, Compartment.AGRICULTURAL_SOIL, "mg/kg"),
    "SEDIMENT_FRESH": (Media.SEDIMENT, Compartment.FRESHWATER_SEDIMENT, "mg/kg"),
}

COMPARTMENT_TO_CODE = {
    Compartment.AMBIENT_AIR: "AIR_REGIONAL",
    Compartment.SURFACE_WATER: "WATER_SURFACE",
    Compartment.AGRICULTURAL_SOIL: "SOIL_TOP",
    Compartment.FRESHWATER_SEDIMENT: "SEDIMENT_FRESH",
}


def build_external_payload_from_reference(
    result: ConcentrationEstimationResult,
) -> ExternalEngineResultPayload:
    surfaces = []
    for surface in result.surfaces:
        surfaces.append(
            ExternalEngineSurfacePayload(
                compartment_code=COMPARTMENT_TO_CODE[surface.compartment],
                concentration=surface.concentration_value,
                unit=surface.concentration_unit,
                context_scope=surface.geographic_scope.region_id,
                mode=surface.time_window.mode.value,
                interval_start=surface.time_window.start,
                interval_end=surface.time_window.end,
                notes=["Generated by harness from a model-native-like external payload."],
            )
        )
    return ExternalEngineResultPayload(
        engine_name="illustrative-external-engine",
        engine_version="2026.04",
        surfaces=surfaces,
    )


def normalize_external_payload(
    payload: ExternalEngineResultPayload,
    scenario: EnvironmentalReleaseScenario,
    run_options: FateModelRunOptions,
    provenance_builder: ProvenanceBuilder,
) -> ConcentrationEstimationResult:
    normalized_surfaces = []
    assumptions: list[FateAssumptionRecord] = [
        FateAssumptionRecord(
            parameter="external_engine_name",
            value=payload.engine_name,
            unit=None,
            source_classification=SourceClassification.DERIVED,
            rationale="Engine name captured from normalized external-model payload.",
        ),
        FateAssumptionRecord(
            parameter="external_engine_version",
            value=payload.engine_version,
            unit=None,
            source_classification=SourceClassification.DERIVED,
            rationale="Engine version captured from normalized external-model payload.",
        ),
    ]
    warnings = []
    payload_modes = {record.mode for record in payload.surfaces}
    if len(payload_modes) != 1:
        raise FateValidationError(
            code="mixed_external_payload_modes",
            message=f"External payload mixes incompatible run modes: {sorted(payload_modes)}.",
            suggestion="Normalize imported external payloads so all rows use one run mode per result set.",
            details={"payloadModes": sorted(payload_modes)},
        )
    payload_mode = next(iter(payload_modes))
    if payload_mode != run_options.run_mode.value:
        raise FateValidationError(
            code="external_payload_run_mode_mismatch",
            message=(
                f"External payload mode {payload_mode} does not match requested run mode {run_options.run_mode.value}."
            ),
            suggestion="Align the declared run mode with the imported external payload time semantics.",
            details={
                "payloadMode": payload_mode,
                "requestedRunMode": run_options.run_mode.value,
            },
        )

    for record in payload.surfaces:
        if record.compartment_code not in COMPARTMENT_CODE_MAP:
            raise FateValidationError(
                code="unknown_external_compartment_code",
                message=f"Unsupported external compartment code: {record.compartment_code}",
                suggestion="Extend the adapter mapping table before normalizing this payload.",
            )
        medium, compartment, expected_unit = COMPARTMENT_CODE_MAP[record.compartment_code]
        try:
            normalization = provenance_builder.defaults_registry.normalize_adapter_concentration(
                record.compartment_code,
                record.concentration,
                record.unit,
            )
        except FateRegistryError as exc:
            raise FateValidationError(
                code=exc.payload.code,
                message=exc.payload.message,
                suggestion=exc.payload.suggestion,
                details=exc.payload.details | {"compartmentCode": record.compartment_code},
            ) from exc
        time_window = (
            TimeWindow(mode=RunMode.STEADY_STATE)
            if record.mode == "steady_state"
            else TimeWindow(
                mode=RunMode.TIME_BUCKET,
                start=record.interval_start,
                end=record.interval_end,
                bucket_label=(
                    f"{record.compartment_code.lower()}_{record.interval_start.strftime('%Y%m%dT%H%M%S')}"
                    if record.interval_start
                    else record.compartment_code.lower()
                ),
            )
        )
        unsupported_limitations = []
        if record.mode == "steady_state" and (record.interval_start is not None or record.interval_end is not None):
            unsupported_limitations.append(
                LimitationNote(
                    code="adapter_unsupported_time_bounds",
                    message="Time interval bounds were provided in steady_state mode and were ignored during normalization.",
                )
            )
        normalized_surfaces.append(
            ConcentrationSurface(
                scenario_id=scenario.scenario_id,
                medium=medium,
                compartment=compartment,
                geographic_scope=scenario.geographic_scope.model_copy(update={"notes": record.context_scope}),
                time_window=time_window,
                concentration_value=normalization.value,
                concentration_unit=normalization.unit,
                model_family=ModelFamily.EXTERNAL_RESULT_ADAPTER,
                fit_for_purpose=run_options.fit_for_purpose,
                provenance=provenance_builder.bundle(scenario.evidence_sources),
                limitations=[
                    LimitationNote(
                        code="external_result_adapter",
                        message="Surface was normalized from an external engine-like payload through the adapter harness.",
                    ),
                    *unsupported_limitations,
                    *(
                        [
                            LimitationNote(
                                code="adapter_basis_normalization",
                                message=(
                                    f"{record.compartment_code} was normalized to the governed "
                                    f"{normalization.canonical_basis} basis before export."
                                ),
                            )
                        ]
                        if normalization.basis_conversion_applied
                        else []
                    ),
                ],
            )
        )
        if normalization.was_converted:
            warnings.append(
                QualityFlag(
                    code="adapter_unit_conversion_applied",
                    severity=Severity.INFO,
                    message=(
                        f"Converted {record.compartment_code} from {record.unit} to canonical unit "
                        f"{expected_unit} before normalization."
                    ),
                )
            )
        if normalization.basis_conversion_applied:
            warnings.append(
                QualityFlag(
                    code="adapter_basis_conversion_applied",
                    severity=Severity.INFO,
                    message=(
                        f"Converted {record.compartment_code} from {normalization.source_basis} to "
                        f"{normalization.canonical_basis} basis using governed screening defaults."
                    ),
                )
            )
        if record.notes:
            warnings.append(
                QualityFlag(
                    code="external_payload_note",
                    severity=Severity.INFO,
                    message=" | ".join(record.notes),
                )
            )

    run_summary = FateRunSummary(
        scenario_id=scenario.scenario_id,
        model_family=ModelFamily.EXTERNAL_RESULT_ADAPTER,
        run_mode=run_options.run_mode,
        surfaces_emitted=len(normalized_surfaces),
        assumptions_applied=assumptions,
        escalation_concerns=run_options.escalation_concerns,
        warnings=warnings,
        result_metadata=ResultMetadata.completed(result_id=f"result-{scenario.scenario_id}-external"),
    )
    return ConcentrationEstimationResult(
        surfaces=normalized_surfaces,
        run_summary=run_summary,
        assumptions=assumptions,
    )


class ExternalResultAdapterHarnessPlugin(ReferenceMassBalancePlugin):
    key = PluginKey(
        run_mode=RunMode.STEADY_STATE,
        model_family=ModelFamily.EXTERNAL_RESULT_ADAPTER,
    )
    limitations = [
        "External-result adapter harness normalizes an engine-like payload shape into Fate MCP outputs.",
        "Harness is integration-oriented and not a validation claim for a specific branded engine.",
    ]

    def __init__(self, defaults_registry, provenance_builder: ProvenanceBuilder) -> None:
        super().__init__(defaults_registry, provenance_builder)

    def run(
        self,
        scenario: EnvironmentalReleaseScenario,
        run_options: FateModelRunOptions,
    ) -> ConcentrationEstimationResult:
        baseline = super().run(
            scenario,
            run_options.model_copy(update={"model_family": ModelFamily.REFERENCE_MASS_BALANCE}),
        )
        payload = build_external_payload_from_reference(baseline)
        return normalize_external_payload(payload, scenario, run_options, self.provenance_builder)
