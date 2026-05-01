from __future__ import annotations

import functools
import json
import logging
import logging.handlers
import os
import re
import time
import uuid
from contextvars import ContextVar
from pathlib import Path

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from fate_mcp.benchmarks import benchmark_manifest
from fate_mcp.compat import ensure_supported_python_version
from fate_mcp.contracts import build_contract_manifest, ensure_contract_artifacts_current
from fate_mcp.defaults import DefaultsRegistry
from fate_mcp.errors import FateValidationError
from fate_mcp.guidance import build_doc_manifest, read_doc
from fate_mcp.integrations import (
    apply_physchem_evidence,
    assess_erosion_sediment_validation_fit,
    assess_release_scenario_fit,
    build_erosion_sediment_validation_case,
    build_model_family_comparison_brief,
    build_model_family_comparison_packet,
    build_model_family_comparison_review_brief,
    build_model_family_comparison_review_packet,
    build_model_family_challenge_scientific_dossier,
    build_model_family_challenge_scientific_dossier_brief,
    build_model_family_challenge_review_brief,
    build_model_family_challenge_review_packet,
    build_model_family_selection_review_brief,
    build_model_family_selection_review_packet,
    build_probabilistic_review_brief,
    build_probabilistic_review_packet,
    build_run_scientific_trust_brief as build_run_scientific_trust_brief_artifact,
    build_scientific_methods_dossier,
    build_scientific_methods_dossier_brief,
    build_run_parameter_manifest,
    build_scientific_review_brief,
    build_scientific_review_packet,
    build_run_uncertainty_summary,
    build_regulatory_handoff_review_brief,
    build_regulatory_handoff_review_packet,
    build_concentration_surface_bundle,
    compare_fate_scenarios,
    estimate_event_sediment_yield_musle,
    estimate_sediment_associated_chemical_load,
    estimate_soil_loss_rusle,
    export_exposure_consumption_package,
    export_regulatory_handoff_package,
    preview_model_family_comparison_review,
    preview_model_family_challenge_review,
    preview_model_family_selection_review,
    preview_scientific_review_outcome,
    preview_regulatory_handoff_resolution,
    recommend_model_family_selection,
    recommend_regulatory_handoff_profile,
    screen_erosion_transport_relevance,
    summarize_regulatory_handoff_package,
)
from fate_mcp.models import (
    AssessErosionSedimentValidationFitRequest,
    ApplyPhyschemEvidenceRequest,
    AssessReleaseScenarioFitRequest,
    BuildErosionSedimentValidationCaseRequest,
    BuildModelFamilyComparisonBriefRequest,
    BuildModelFamilyComparisonPacketRequest,
    BuildModelFamilyComparisonReviewBriefRequest,
    BuildModelFamilyComparisonReviewPacketRequest,
    BuildModelFamilyChallengeScientificDossierBriefRequest,
    BuildModelFamilyChallengeScientificDossierRequest,
    BuildModelFamilyChallengeReviewBriefRequest,
    BuildModelFamilyChallengeReviewPacketRequest,
    BuildModelFamilySelectionReviewBriefRequest,
    BuildModelFamilySelectionReviewPacketRequest,
    BuildProbabilisticReviewBriefRequest,
    BuildProbabilisticReviewPacketRequest,
    BuildScientificMethodsDossierBriefRequest,
    BuildScientificMethodsDossierRequest,
    BuildRunParameterManifestRequest,
    BuildRunScientificTrustBriefRequest,
    BuildScientificReviewBriefRequest,
    BuildScientificReviewPacketRequest,
    BuildRunUncertaintySummaryRequest,
    BuildRegulatoryHandoffReviewBriefRequest,
    BuildRegulatoryHandoffReviewPacketRequest,
    BuildConcentrationSurfaceBundleRequest,
    BuildEnvironmentalReleaseScenarioRequest,
    CompareFateScenariosRequest,
    ConcentrationEstimationResult,
    ConcentrationSurfaceBundle,
    EnvironmentalReleaseScenario,
    EstimateProbabilisticMultimediaConcentrationsRequest,
    EstimateMultimediaConcentrationsRequest,
    EstimateEventSedimentYieldMusleRequest,
    EstimateSedimentAssociatedChemicalLoadRequest,
    EstimateSoilLossRusleRequest,
    ErosionSedimentValidationCaseResult,
    ErosionSedimentValidationFitResult,
    EventSedimentYieldMusleResult,
    ExposureConsumptionPackage,
    ImportExternalResultPayloadRequest,
    ErosionTransportRelevanceResult,
    FateModelRunOptions,
    FateScenarioComparisonRecord,
    Media,
    ModelFamily,
    ModelFamilyChallengeReviewBrief,
    ModelFamilyChallengeReviewPacket,
    ModelFamilyChallengeReviewPreview,
    ModelFamilyChallengeScientificDossier,
    ModelFamilyChallengeScientificDossierBrief,
    ModelFamilyComparisonBrief,
    ModelFamilyComparisonPacket,
    ModelFamilyComparisonReviewBrief,
    ModelFamilyComparisonReviewPacket,
    ModelFamilyComparisonReviewPreview,
    ModelFamilySelectionRecommendation,
    ModelFamilySelectionReviewBrief,
    ModelFamilySelectionReviewPacket,
    ModelFamilySelectionReviewPreview,
    ReleaseFraction,
    ScreenErosionTransportRelevanceRequest,
    SedimentAssociatedChemicalLoadResult,
    SoilLossRusleResult,
    ExportConcentrationSurfaceBundleRequest,
    ExportExposureConsumptionPackageRequest,
    ExportRegulatoryHandoffPackageRequest,
    PhyschemEvidenceApplicationResult,
    PreviewModelFamilyComparisonReviewRequest,
    PreviewModelFamilyChallengeReviewRequest,
    PreviewModelFamilySelectionReviewRequest,
    PreviewScientificReviewOutcomeRequest,
    PreviewRegulatoryHandoffResolutionRequest,
    RecommendModelFamilySelectionRequest,
    ReconcileReleaseEvidenceRequest,
    RecommendRegulatoryHandoffProfileRequest,
    ProbabilisticConcentrationResult,
    ProbabilisticReviewBrief,
    ProbabilisticReviewPacket,
    RegulatoryHandoffPackage,
    RegulatoryHandoffPackageSummary,
    RegulatoryHandoffProfileRecommendation,
    RegulatoryHandoffResolutionPreview,
    RegulatoryHandoffReviewBrief,
    RegulatoryHandoffReviewPacket,
    ReleaseEvidenceReconciliationResult,
    ReleaseScenarioFitAssessment,
    RunParameterManifest,
    RunScientificTrustBrief,
    RunUncertaintySummary,
    SummarizeRegulatoryHandoffPackageRequest,
    ScientificMethodsDossier,
    ScientificMethodsDossierBrief,
    ScientificReviewBrief,
    ScientificReviewOutcomePreview,
    ScientificReviewPacket,
)
from fate_mcp.plugins.external_result_adapter import (
    PUBLIC_ADAPTER_IMPORT_PROFILE_IDS,
    adapter_fixture_descriptor,
    build_adapter_import_manifest,
    build_public_adapter_import_manifest,
    load_external_payload,
    normalize_external_payload,
)
from fate_mcp.package_metadata import PACKAGE_NAME, VERSION
from fate_mcp.release_artifacts import REPORT_DESCRIPTIONS, REPORT_FILENAMES, build_release_reports
from fate_mcp.resources import (
    IMPORT_ROOTS_ENV,
    configured_import_roots,
    path_is_relative_to,
    resolve_resource_root,
)
from fate_mcp.runtime import FateRuntime


REPO_ROOT = resolve_resource_root()
RUNTIME = FateRuntime(REPO_ROOT)
DEFAULTS = DefaultsRegistry(REPO_ROOT)
mcp = FastMCP(PACKAGE_NAME, json_response=True)

logger = logging.getLogger("fate_mcp")
correlation_id_var: ContextVar[str] = ContextVar("correlation_id")

_RESOURCE_NAME_RE = re.compile(r"^[a-zA-Z0-9_\-\.]+$")


def _validate_resource_name(name: str) -> str:
    if not _RESOURCE_NAME_RE.match(name):
        raise ValueError(f"Invalid resource name: {name}")
    return name


class _JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Extract structured fields that we inject in _log_tool_call
        if hasattr(record, "correlation_id"):
            payload["correlation_id"] = record.correlation_id
        if hasattr(record, "tool_name"):
            payload["tool_name"] = record.tool_name
        if hasattr(record, "duration_ms"):
            payload["duration_ms"] = record.duration_ms
        if hasattr(record, "request_ids"):
            payload["request_ids"] = record.request_ids
        if hasattr(record, "response_ids"):
            payload["response_ids"] = record.response_ids
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def _configure_logging() -> None:
    if logger.handlers:
        return
    logger.setLevel(logging.INFO)

    # Stdout handler (human-readable)
    stream_handler = logging.StreamHandler()
    stream_formatter = logging.Formatter("%(asctime)s %(levelname)s: %(message)s")
    stream_handler.setFormatter(stream_formatter)
    logger.addHandler(stream_handler)

    # Optional file handler (structured JSON Lines)
    audit_log_path = os.environ.get("FATE_MCP_AUDIT_LOG_PATH")
    if audit_log_path:
        file_handler = logging.handlers.RotatingFileHandler(
            audit_log_path, maxBytes=10 * 1024 * 1024, backupCount=5
        )
        file_formatter = _JsonLogFormatter()
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)


def _extract_log_ids(obj) -> dict[str, str]:
    ids: dict[str, str] = {}
    if obj is None:
        return ids
    for key in (
        "scenario_id",
        "run_id",
        "model_family",
        "bundle_id",
        "package_id",
        "review_packet_id",
        "dossier_id",
        "comparison_packet_id",
        "selection_profile_id",
        "challenge_review_profile_id",
        "handoff_profile_id",
    ):
        val = getattr(obj, key, None)
        if val is not None and isinstance(val, str):
            ids[key] = val
    return ids


def _log_tool_call(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        _configure_logging()
        corr_id = f"corr-{uuid.uuid4().hex[:12]}"
        token = correlation_id_var.set(corr_id)
        tool_name = getattr(fn, "__name__", "unknown")
        start = time.perf_counter()
        request_ids = _extract_log_ids(args[0] if args else None)
        req_parts = " ".join(f"{k}={v}" for k, v in request_ids.items())
        elapsed_ms = 0.0
        result = None
        response_ids: dict[str, str] = {}
        exc_info = None
        try:
            result = fn(*args, **kwargs)
            elapsed_ms = (time.perf_counter() - start) * 1000
            response_ids = _extract_log_ids(result)
            resp_parts = " ".join(f"{k}={v}" for k, v in response_ids.items())
            logger.info(
                "[corr=%s] [tool=%s] completed in %.2fms %s %s",
                corr_id,
                tool_name,
                elapsed_ms,
                req_parts,
                resp_parts,
                extra={
                    "correlation_id": corr_id,
                    "tool_name": tool_name,
                    "duration_ms": round(elapsed_ms, 3),
                    "request_ids": request_ids,
                    "response_ids": response_ids,
                },
            )
            return result
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - start) * 1000
            exc_info = (type(exc), exc, None)
            logger.error(
                "[corr=%s] [tool=%s] failed after %.2fms %s error=%s",
                corr_id,
                tool_name,
                elapsed_ms,
                req_parts,
                exc.__class__.__name__,
                exc_info=exc_info,
                extra={
                    "correlation_id": corr_id,
                    "tool_name": tool_name,
                    "duration_ms": round(elapsed_ms, 3),
                    "request_ids": request_ids,
                    "response_ids": {},
                },
            )
            raise
        finally:
            correlation_id_var.reset(token)

    return wrapper


_original_tool = mcp.tool


def _default_tool_annotations(tool_name: str) -> ToolAnnotations:
    return ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=tool_name != "fate_estimate_probabilistic_multimedia_concentrations",
        openWorldHint=tool_name == "fate_import_external_result_payload",
    )


def _tool_kwargs_for(fn, kwargs: dict) -> dict:
    tool_kwargs = dict(kwargs)
    if tool_kwargs.get("annotations") is None:
        tool_kwargs["annotations"] = _default_tool_annotations(getattr(fn, "__name__", "unknown"))
    return tool_kwargs


def _logged_tool(*args, **kwargs):
    if len(args) == 1 and callable(args[0]) and not kwargs:
        fn = args[0]
        return _original_tool(**_tool_kwargs_for(fn, {}))(_log_tool_call(fn))

    def decorator(fn):
        return _original_tool(*args, **_tool_kwargs_for(fn, kwargs))(_log_tool_call(fn))

    return decorator


mcp.tool = _logged_tool


def _regulatory_handoff_profile_or_error(profile_id: str):
    profile = DEFAULTS.regulatory_handoff_profile(profile_id)
    if profile is None:
        raise ValueError(
            f"Unknown regulatory handoff profile {profile_id}. Inspect defaults://regulatory-handoff-profiles."
        )
    return profile


def _scientific_review_profile_or_error(model_family: str):
    profile = DEFAULTS.scientific_review_profile(model_family)
    if profile is None:
        raise ValueError(
            f"Unknown scientific review profile for {model_family}. Inspect defaults://scientific-review-profiles."
        )
    return profile


def _model_family_comparison_profile_or_error(profile_id: str):
    profile = DEFAULTS.model_family_comparison_profile(profile_id)
    if profile is None:
        raise ValueError(
            f"Unknown model-family comparison profile {profile_id}. Inspect defaults://model-family-comparison-profiles."
        )
    return profile


def _model_family_selection_profile_or_error(profile_id: str):
    profile = DEFAULTS.model_family_selection_profile(profile_id)
    if profile is None:
        raise ValueError(
            f"Unknown model-family selection profile {profile_id}. Inspect defaults://model-family-selection-profiles."
        )
    return profile


def _model_family_challenge_review_profile_or_error(profile_id: str):
    profile = DEFAULTS.model_family_challenge_review_profile(profile_id)
    if profile is None:
        raise ValueError(
            f"Unknown model-family challenge review profile {profile_id}. Inspect defaults://model-family-challenge-review-profiles."
        )
    return profile


def _public_adapter_import_profile_or_error(profile_id: str):
    manifest = build_public_adapter_import_manifest(REPO_ROOT)
    for profile in manifest.profiles:
        if profile.profile_id == profile_id:
            return profile
    raise ValueError(
        f"Unknown public adapter import profile {profile_id}. Inspect adapters://public-import-manifest."
    )


def _resolve_external_payload_path(payload_path: str) -> Path:
    raw_path = Path(payload_path).expanduser()
    allowed_roots = configured_import_roots(REPO_ROOT)
    candidates: list[Path] = []

    def add_candidate(path: Path) -> None:
        if path not in candidates:
            candidates.append(path)

    if raw_path.is_absolute():
        add_candidate(raw_path)
    else:
        add_candidate(REPO_ROOT / raw_path)
        for root in allowed_roots:
            add_candidate(root / raw_path)
        add_candidate(Path.cwd() / raw_path)
    for candidate in candidates:
        if candidate.exists():
            resolved = candidate.resolve()
            if any(path_is_relative_to(resolved, root) for root in allowed_roots):
                return resolved
            raise FateValidationError(
                code="external_payload_path_not_allowed",
                message=f"External payload path {payload_path} is outside the configured import roots.",
                suggestion=(
                    "Place the payload under config/adapter-fixtures or add an operator import "
                    f"directory through {IMPORT_ROOTS_ENV}."
                ),
                details={
                    "payloadPath": str(resolved),
                    "allowedRoots": [str(root) for root in allowed_roots],
                },
            )
    allowed_text = ", ".join(str(root) for root in allowed_roots) or "<none>"
    raise FateValidationError(
        code="external_payload_path_not_found",
        message=f"External payload path {payload_path} was not found.",
        suggestion=(
            "Provide an existing .json or .csv payload path under an allowed import root. "
            f"Current import roots: {allowed_text}."
        ),
        details={"payloadPath": payload_path, "allowedRoots": [str(root) for root in allowed_roots]},
    )


@mcp.tool()
def fate_build_environmental_release_scenario(
    request: BuildEnvironmentalReleaseScenarioRequest,
) -> EnvironmentalReleaseScenario:
    """Validate and normalize an environmental release scenario."""
    return RUNTIME.build_environmental_release_scenario(request)


@mcp.tool()
def fate_estimate_multimedia_concentrations(
    request: EstimateMultimediaConcentrationsRequest,
) -> ConcentrationEstimationResult:
    """Estimate deterministic or bounded concentration surfaces from a release scenario."""
    return RUNTIME.estimate(request.scenario, request.run_options)


@mcp.tool()
def fate_estimate_probabilistic_multimedia_concentrations(
    request: EstimateProbabilisticMultimediaConcentrationsRequest,
) -> ProbabilisticConcentrationResult:
    """Estimate probabilistic percentile concentration surfaces by orchestrating governed distribution sampling over the deterministic kernels."""
    return RUNTIME.estimate_probabilistic(
        request.scenario,
        request.run_options,
        iterations=request.iterations,
        seed=request.seed,
    )


@mcp.tool()
def fate_screen_erosion_transport_relevance(
    request: ScreenErosionTransportRelevanceRequest,
) -> ErosionTransportRelevanceResult:
    """Screen whether erosion-mediated particle transport is relevant for a release scenario."""
    return screen_erosion_transport_relevance(request, RUNTIME.provenance)


@mcp.tool()
def fate_estimate_soil_loss_rusle(
    request: EstimateSoilLossRusleRequest,
) -> SoilLossRusleResult:
    """Estimate scalar RUSLE annual soil loss for bounded erosion screening."""
    return estimate_soil_loss_rusle(request, RUNTIME.provenance)


@mcp.tool()
def fate_estimate_event_sediment_yield_musle(
    request: EstimateEventSedimentYieldMusleRequest,
) -> EventSedimentYieldMusleResult:
    """Estimate scalar MUSLE event sediment yield from caller-provided runoff and peak flow."""
    return estimate_event_sediment_yield_musle(request, RUNTIME.provenance)


@mcp.tool()
def fate_estimate_sediment_associated_chemical_load(
    request: EstimateSedimentAssociatedChemicalLoadRequest,
) -> SedimentAssociatedChemicalLoadResult:
    """Estimate sediment-associated chemical load from sediment yield and explicit delivery assumptions."""
    return estimate_sediment_associated_chemical_load(request, RUNTIME.provenance)


@mcp.tool()
def fate_build_erosion_sediment_validation_case(
    request: BuildErosionSedimentValidationCaseRequest,
) -> ErosionSedimentValidationCaseResult:
    """Build a bounded inline validation case for scalar erosion/sediment screening outputs."""
    return build_erosion_sediment_validation_case(request, RUNTIME.provenance)


@mcp.tool()
def fate_assess_erosion_sediment_validation_fit(
    request: AssessErosionSedimentValidationFitRequest,
) -> ErosionSedimentValidationFitResult:
    """Assess observed-versus-predicted fit for a scalar erosion/sediment validation case."""
    return assess_erosion_sediment_validation_fit(request, RUNTIME.provenance)


@mcp.tool()
def fate_import_external_result_payload(
    request: ImportExternalResultPayloadRequest,
) -> ConcentrationEstimationResult:
    """Import a public normalized external payload into canonical Environmental Fate MCP concentration outputs."""
    profile = _public_adapter_import_profile_or_error(request.import_profile_id)
    if request.import_profile_id not in PUBLIC_ADAPTER_IMPORT_PROFILE_IDS:
        raise FateValidationError(
            code="external_payload_profile_not_public",
            message=f"Adapter import profile {request.import_profile_id} is not a public MCP import contract.",
            suggestion="Use a public normalized external payload profile from adapters://public-import-manifest.",
            details={"importProfileId": request.import_profile_id},
        )
    if request.run_options.model_family != ModelFamily.EXTERNAL_RESULT_ADAPTER:
        raise FateValidationError(
            code="external_payload_requires_external_result_adapter_model_family",
            message=(
                "Public external payload import requires run_options.model_family to be external_result_adapter."
            ),
            suggestion="Set run_options.model_family to external_result_adapter for normalized payload import.",
            details={"modelFamily": request.run_options.model_family.value},
        )
    if request.run_options.run_mode not in profile.accepted_modes:
        raise FateValidationError(
            code="external_payload_profile_run_mode_mismatch",
            message=(
                f"Import profile {profile.profile_id} does not accept run mode {request.run_options.run_mode.value}."
            ),
            suggestion="Choose a compatible public import profile or align the run mode with the payload semantics.",
            details={
                "importProfileId": profile.profile_id,
                "runMode": request.run_options.run_mode.value,
                "acceptedModes": [mode.value for mode in profile.accepted_modes],
            },
        )
    payload_path = _resolve_external_payload_path(request.payload_path)
    if payload_path.suffix.lower() not in profile.accepted_extensions:
        raise FateValidationError(
            code="external_payload_profile_extension_mismatch",
            message=(
                f"Import profile {profile.profile_id} does not accept files with suffix {payload_path.suffix or '<none>'}."
            ),
            suggestion="Use the matching public JSON or CSV profile for the payload you are importing.",
            details={
                "payloadPath": str(payload_path),
                "importProfileId": profile.profile_id,
                "acceptedExtensions": profile.accepted_extensions,
            },
        )
    payload = load_external_payload(payload_path)
    result = normalize_external_payload(
        payload,
        request.scenario,
        request.run_options,
        RUNTIME.provenance,
    )
    assumptions = result.assumptions + [
        RUNTIME.provenance.derived(
            "external_import_profile_id",
            profile.profile_id,
            None,
            "Public adapter import profile used to normalize the external payload.",
        ),
        RUNTIME.provenance.derived(
            "external_payload_source_path",
            str(payload_path),
            None,
            "Resolved path of the external payload imported through the public MCP contract.",
        ),
    ]
    run_summary = result.run_summary.model_copy(update={"assumptions_applied": assumptions})
    return result.model_copy(update={"assumptions": assumptions, "run_summary": run_summary})


@mcp.tool()
def fate_build_environmental_release_scenario_skeleton() -> str:
    """Return a validated, example-populated JSON skeleton for BuildEnvironmentalReleaseScenarioRequest."""
    skeleton = BuildEnvironmentalReleaseScenarioRequest(
        chemical_identity={"preferredName": "Example substance"},
        total_release_mass_kg=10.0,
        release_fractions=[
            ReleaseFraction(medium=Media.WATER, fraction=0.5),
            ReleaseFraction(medium=Media.SOIL, fraction=0.5),
        ],
        duration_days=30.0,
        region_id="eu_screening_default",
        context_label="regional_screening",
    )
    return skeleton.model_dump_json(indent=2)


@mcp.tool()
def fate_estimate_multimedia_concentrations_skeleton() -> str:
    """Return a validated, example-populated JSON skeleton for EstimateMultimediaConcentrationsRequest."""
    scenario = BuildEnvironmentalReleaseScenarioRequest(
        chemical_identity={"preferredName": "Example substance"},
        total_release_mass_kg=10.0,
        release_fractions=[ReleaseFraction(medium=Media.WATER, fraction=1.0)],
        duration_days=30.0,
    )
    from fate_mcp.runtime import FateRuntime
    runtime = FateRuntime(REPO_ROOT)
    built_scenario = runtime.build_environmental_release_scenario(scenario)
    request = EstimateMultimediaConcentrationsRequest(
        scenario=built_scenario,
        run_options=FateModelRunOptions(
            region_profile_id=built_scenario.geographic_scope.region_id,
            model_family=ModelFamily.REFERENCE_MASS_BALANCE,
        ),
    )
    return request.model_dump_json(indent=2)


@mcp.tool()
def fate_estimate_probabilistic_multimedia_concentrations_skeleton() -> str:
    """Return a validated, example-populated JSON skeleton for EstimateProbabilisticMultimediaConcentrationsRequest."""
    scenario = BuildEnvironmentalReleaseScenarioRequest(
        chemical_identity={"preferredName": "Example substance"},
        total_release_mass_kg=10.0,
        release_fractions=[ReleaseFraction(medium=Media.WATER, fraction=1.0)],
        duration_days=30.0,
    )
    from fate_mcp.runtime import FateRuntime
    runtime = FateRuntime(REPO_ROOT)
    built_scenario = runtime.build_environmental_release_scenario(scenario)
    request = EstimateProbabilisticMultimediaConcentrationsRequest(
        scenario=built_scenario,
        run_options=FateModelRunOptions(
            region_profile_id=built_scenario.geographic_scope.region_id,
            model_family=ModelFamily.REFERENCE_MASS_BALANCE,
        ),
        iterations=100,
        seed=42,
    )
    return request.model_dump_json(indent=2)


@mcp.tool()
def fate_import_external_result_payload_skeleton() -> str:
    """Return a validated, example-populated JSON skeleton for ImportExternalResultPayloadRequest."""
    scenario = BuildEnvironmentalReleaseScenarioRequest(
        chemical_identity={"preferredName": "Example external payload import"},
        total_release_mass_kg=10.0,
        release_fractions=[
            ReleaseFraction(medium=Media.AIR, fraction=0.5),
            ReleaseFraction(medium=Media.WATER, fraction=0.5),
        ],
        duration_days=30.0,
    )
    built_scenario = RUNTIME.build_environmental_release_scenario(scenario)
    request = ImportExternalResultPayloadRequest(
        scenario=built_scenario,
        run_options=FateModelRunOptions(
            region_profile_id=built_scenario.geographic_scope.region_id,
            model_family=ModelFamily.EXTERNAL_RESULT_ADAPTER,
        ),
        payload_path="config/adapter-fixtures/illustrative_external_engine_payload.json",
        import_profile_id="normalized_external_payload_json",
    )
    return request.model_dump_json(indent=2)


@mcp.tool()
def fate_export_regulatory_handoff_package_skeleton() -> str:
    """Return a validated, example-populated JSON skeleton for ExportRegulatoryHandoffPackageRequest."""
    scenario = BuildEnvironmentalReleaseScenarioRequest(
        chemical_identity={"preferredName": "Example substance"},
        total_release_mass_kg=10.0,
        release_fractions=[ReleaseFraction(medium=Media.WATER, fraction=1.0)],
        duration_days=30.0,
    )
    from fate_mcp.runtime import FateRuntime
    runtime = FateRuntime(REPO_ROOT)
    built_scenario = runtime.build_environmental_release_scenario(scenario)
    result = runtime.estimate(
        built_scenario,
        FateModelRunOptions(
            region_profile_id=built_scenario.geographic_scope.region_id,
            model_family=ModelFamily.REFERENCE_MASS_BALANCE,
        ),
    )
    request = ExportRegulatoryHandoffPackageRequest(
        result=result,
        scenario=built_scenario,
        handoff_profile_id="exposure_scenario_mcp_v1",
        target_modules=["exposure_scenario_mcp_v1"],
    )
    return request.model_dump_json(indent=2)


@mcp.tool()
def fate_build_model_family_comparison_packet_skeleton() -> str:
    """Return a validated JSON skeleton for BuildModelFamilyComparisonPacketRequest."""
    from fate_mcp.runtime import FateRuntime
    runtime = FateRuntime(REPO_ROOT)
    base_scenario = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={"preferredName": "Example substance"},
            total_release_mass_kg=10.0,
            release_fractions=[ReleaseFraction(medium=Media.WATER, fraction=1.0)],
            duration_days=30.0,
        )
    )
    request = BuildModelFamilyComparisonPacketRequest(
        scenario=base_scenario,
        base_model_family=ModelFamily.REFERENCE_MASS_BALANCE,
        candidate_model_family=ModelFamily.ADVECTIVE_SCREENING_MASS_BALANCE,
    )
    return request.model_dump_json(indent=2)


@mcp.tool()
def fate_build_scientific_review_packet_skeleton() -> str:
    """Return a validated JSON skeleton for BuildScientificReviewPacketRequest."""
    from fate_mcp.runtime import FateRuntime
    runtime = FateRuntime(REPO_ROOT)
    scenario = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={"preferredName": "Example substance"},
            total_release_mass_kg=10.0,
            release_fractions=[ReleaseFraction(medium=Media.WATER, fraction=1.0)],
            duration_days=30.0,
        )
    )
    result = runtime.estimate(
        scenario,
        FateModelRunOptions(
            region_profile_id=scenario.geographic_scope.region_id,
            model_family=ModelFamily.REFERENCE_MASS_BALANCE,
        ),
    )
    request = BuildScientificReviewPacketRequest(
        scenario=scenario,
        result=result,
    )
    return request.model_dump_json(indent=2)


@mcp.tool()
def fate_build_run_scientific_trust_brief_skeleton() -> str:
    """Return a validated JSON skeleton for BuildRunScientificTrustBriefRequest."""
    from fate_mcp.runtime import FateRuntime
    runtime = FateRuntime(REPO_ROOT)
    scenario = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={"preferredName": "Example substance"},
            total_release_mass_kg=10.0,
            release_fractions=[ReleaseFraction(medium=Media.WATER, fraction=1.0)],
            duration_days=30.0,
        )
    )
    result = runtime.estimate(
        scenario,
        FateModelRunOptions(
            region_profile_id=scenario.geographic_scope.region_id,
            model_family=ModelFamily.REFERENCE_MASS_BALANCE,
        ),
    )
    request = BuildRunScientificTrustBriefRequest(
        scenario=scenario,
        result=result,
    )
    return request.model_dump_json(indent=2)


@mcp.tool()
def fate_build_model_family_challenge_scientific_dossier_skeleton() -> str:
    """Return a validated JSON skeleton for BuildModelFamilyChallengeScientificDossierRequest."""
    from fate_mcp.runtime import FateRuntime
    runtime = FateRuntime(REPO_ROOT)
    scenario = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={"preferredName": "Example substance"},
            total_release_mass_kg=10.0,
            release_fractions=[
                ReleaseFraction(medium=Media.WATER, fraction=0.6),
                ReleaseFraction(medium=Media.SOIL, fraction=0.4),
            ],
            duration_days=30.0,
        )
    )
    request = BuildModelFamilyChallengeScientificDossierRequest(
        scenario=scenario,
    )
    return request.model_dump_json(indent=2)


@mcp.tool()
def fate_build_concentration_surface_bundle(
    request: BuildConcentrationSurfaceBundleRequest,
) -> ConcentrationSurfaceBundle:
    """Package concentration surfaces and run metadata for downstream consumers."""
    return build_concentration_surface_bundle(request.result)


@mcp.tool()
def fate_compare_fate_scenarios(request: CompareFateScenariosRequest) -> FateScenarioComparisonRecord:
    """Compare two concentration-estimation results and surface the main drivers."""
    return compare_fate_scenarios(request, RUNTIME.provenance)


@mcp.tool()
def fate_apply_physchem_evidence(request: ApplyPhyschemEvidenceRequest) -> PhyschemEvidenceApplicationResult:
    """Attach supporting physicochemical evidence to scenario provenance."""
    return apply_physchem_evidence(request.scenario, request.evidence, RUNTIME.provenance)


@mcp.tool()
def fate_assess_release_scenario_fit(
    request: AssessReleaseScenarioFitRequest,
) -> ReleaseScenarioFitAssessment:
    """Assess whether the declared workflow is a good fit for the current scenario."""
    return assess_release_scenario_fit(request.scenario, request.run_options, RUNTIME.provenance)


@mcp.tool()
def fate_build_run_parameter_manifest(
    request: BuildRunParameterManifestRequest,
) -> RunParameterManifest:
    """Build a machine-readable run parameter manifest that preserves resolved provenance and runtime consumption state."""
    return build_run_parameter_manifest(request.scenario, request.result, RUNTIME.provenance)


@mcp.tool()
def fate_build_run_uncertainty_summary(
    request: BuildRunUncertaintySummaryRequest,
) -> RunUncertaintySummary:
    """Build a deterministic reviewer-facing uncertainty-driver summary without probabilistic inference."""
    return build_run_uncertainty_summary(request.scenario, request.result, RUNTIME.provenance)


@mcp.tool()
def fate_build_probabilistic_review_packet(
    request: BuildProbabilisticReviewPacketRequest,
) -> ProbabilisticReviewPacket:
    """Build an assessor-facing probabilistic review packet that preserves percentile surfaces, sampled drivers, and iteration health."""
    return build_probabilistic_review_packet(request, RUNTIME.provenance)


@mcp.tool()
def fate_build_probabilistic_review_brief(
    request: BuildProbabilisticReviewBriefRequest,
) -> ProbabilisticReviewBrief:
    """Render a compact assessor-facing brief from a probabilistic review packet."""
    return build_probabilistic_review_brief(request, RUNTIME.provenance)


@mcp.tool()
def fate_recommend_model_family_selection(
    request: RecommendModelFamilySelectionRequest,
) -> ModelFamilySelectionRecommendation:
    """Recommend whether to keep the default model-family baseline only or add a governed experimental challenge path."""
    return recommend_model_family_selection(request, RUNTIME.provenance)


@mcp.tool()
def fate_preview_model_family_selection_review(
    request: PreviewModelFamilySelectionReviewRequest,
) -> ModelFamilySelectionReviewPreview:
    """Preview the governed assessor-facing review status for a model-family selection recommendation."""
    return preview_model_family_selection_review(request, RUNTIME.provenance)


@mcp.tool()
def fate_build_model_family_selection_review_packet(
    request: BuildModelFamilySelectionReviewPacketRequest,
) -> ModelFamilySelectionReviewPacket:
    """Build a governed assessor-facing review packet from a model-family selection recommendation."""
    return build_model_family_selection_review_packet(request, RUNTIME.provenance)


@mcp.tool()
def fate_build_model_family_selection_review_brief(
    request: BuildModelFamilySelectionReviewBriefRequest,
) -> ModelFamilySelectionReviewBrief:
    """Render a compact assessor-facing review brief from a model-family selection review packet."""
    return build_model_family_selection_review_brief(request, RUNTIME.provenance)


@mcp.tool()
def fate_preview_model_family_challenge_review(
    request: PreviewModelFamilyChallengeReviewRequest,
) -> ModelFamilyChallengeReviewPreview:
    """Preview the governed assessor-facing review status for the composed baseline-versus-challenge model-family path."""
    return preview_model_family_challenge_review(request, RUNTIME, RUNTIME.provenance)


@mcp.tool()
def fate_build_model_family_challenge_review_packet(
    request: BuildModelFamilyChallengeReviewPacketRequest,
) -> ModelFamilyChallengeReviewPacket:
    """Build a composed assessor-facing packet that bundles governed model-family selection review and optional comparison review."""
    return build_model_family_challenge_review_packet(request, RUNTIME, RUNTIME.provenance)


@mcp.tool()
def fate_build_model_family_challenge_review_brief(
    request: BuildModelFamilyChallengeReviewBriefRequest,
) -> ModelFamilyChallengeReviewBrief:
    """Render a compact assessor-facing brief from a composed model-family challenge review packet."""
    return build_model_family_challenge_review_brief(request, RUNTIME.provenance)


@mcp.tool()
def fate_build_model_family_challenge_scientific_dossier(
    request: BuildModelFamilyChallengeScientificDossierRequest,
) -> ModelFamilyChallengeScientificDossier:
    """Build a composed scientific dossier for the governed baseline-versus-challenge model-family path."""
    return build_model_family_challenge_scientific_dossier(request, RUNTIME, RUNTIME.provenance)


@mcp.tool()
def fate_build_model_family_challenge_scientific_dossier_brief(
    request: BuildModelFamilyChallengeScientificDossierBriefRequest,
) -> ModelFamilyChallengeScientificDossierBrief:
    """Render a compact assessor-facing summary from a model-family challenge scientific dossier."""
    return build_model_family_challenge_scientific_dossier_brief(request, RUNTIME.provenance)


@mcp.tool()
def fate_build_model_family_comparison_packet(
    request: BuildModelFamilyComparisonPacketRequest,
) -> ModelFamilyComparisonPacket:
    """Build a deterministic comparison packet for two model families run against the same scenario."""
    return build_model_family_comparison_packet(request, RUNTIME, RUNTIME.provenance)


@mcp.tool()
def fate_build_model_family_comparison_brief(
    request: BuildModelFamilyComparisonBriefRequest,
) -> ModelFamilyComparisonBrief:
    """Render a compact comparison brief from a model-family comparison packet."""
    return build_model_family_comparison_brief(request)


@mcp.tool()
def fate_preview_model_family_comparison_review(
    request: PreviewModelFamilyComparisonReviewRequest,
) -> ModelFamilyComparisonReviewPreview:
    """Preview the governed assessor-facing review status for a model-family comparison packet."""
    return preview_model_family_comparison_review(request, RUNTIME.provenance)


@mcp.tool()
def fate_build_model_family_comparison_review_packet(
    request: BuildModelFamilyComparisonReviewPacketRequest,
) -> ModelFamilyComparisonReviewPacket:
    """Build a governed assessor-facing review packet from a model-family comparison packet."""
    return build_model_family_comparison_review_packet(request, RUNTIME.provenance)


@mcp.tool()
def fate_build_model_family_comparison_review_brief(
    request: BuildModelFamilyComparisonReviewBriefRequest,
) -> ModelFamilyComparisonReviewBrief:
    """Render a compact assessor-facing review brief from a model-family comparison review packet."""
    return build_model_family_comparison_review_brief(request, RUNTIME.provenance)


@mcp.tool()
def fate_preview_scientific_review_outcome(
    request: PreviewScientificReviewOutcomeRequest,
) -> ScientificReviewOutcomePreview:
    """Preview the governed scientific review outcome and review status before building a full scientific review packet."""
    return preview_scientific_review_outcome(request, RUNTIME.provenance)


@mcp.tool()
def fate_build_scientific_review_packet(
    request: BuildScientificReviewPacketRequest,
) -> ScientificReviewPacket:
    """Bundle fit assessment, parameter manifest, uncertainty summary, and sampled surfaces into one scientific review artifact."""
    return build_scientific_review_packet(request, RUNTIME.provenance)


@mcp.tool()
def fate_build_scientific_review_brief(
    request: BuildScientificReviewBriefRequest,
) -> ScientificReviewBrief:
    """Render a compact scientific review brief from a scientific review packet."""
    return build_scientific_review_brief(request, RUNTIME.provenance)


@mcp.tool()
def fate_build_run_scientific_trust_brief(
    request: BuildRunScientificTrustBriefRequest,
) -> RunScientificTrustBrief:
    """Render a compact run-level bounded-screening trust brief from a scenario/result pair."""
    return build_run_scientific_trust_brief_artifact(request, RUNTIME.provenance)


@mcp.tool()
def fate_build_scientific_methods_dossier(
    request: BuildScientificMethodsDossierRequest,
) -> ScientificMethodsDossier:
    """Build a model-family scientific methods dossier from governed claims, benchmark coverage, and applicability policy."""
    return build_scientific_methods_dossier(request, RUNTIME.provenance)


@mcp.tool()
def fate_build_scientific_methods_dossier_brief(
    request: BuildScientificMethodsDossierBriefRequest,
) -> ScientificMethodsDossierBrief:
    """Render a compact assessor-facing brief from a scientific methods dossier."""
    return build_scientific_methods_dossier_brief(request)


@mcp.tool()
def fate_reconcile_release_evidence(
    request: ReconcileReleaseEvidenceRequest,
) -> ReleaseEvidenceReconciliationResult:
    """Reconcile multiple release evidence records into a reviewable screening scenario."""
    return RUNTIME.reconcile_release_evidence(request)


@mcp.tool()
def fate_export_concentration_surface_bundle(
    request: ExportConcentrationSurfaceBundleRequest,
) -> ConcentrationSurfaceBundle:
    """Export a normalized concentration-surface bundle."""
    return request.bundle


@mcp.tool()
def fate_export_exposure_consumption_package(
    request: ExportExposureConsumptionPackageRequest,
) -> ExposureConsumptionPackage:
    """Build a concentration-only handoff package for downstream consumers."""
    return export_exposure_consumption_package(request, RUNTIME.provenance)


@mcp.tool()
def fate_export_regulatory_handoff_package(
    request: ExportRegulatoryHandoffPackageRequest,
) -> RegulatoryHandoffPackage:
    """Build a ToxMCP regulatory handoff crosswalk from concentration surfaces."""
    return export_regulatory_handoff_package(request, RUNTIME.provenance)


@mcp.tool()
def fate_summarize_regulatory_handoff_package(
    request: SummarizeRegulatoryHandoffPackageRequest,
) -> RegulatoryHandoffPackageSummary:
    """Build a deterministic, consumer-specific summary for a governed regulatory handoff package."""
    return summarize_regulatory_handoff_package(request, RUNTIME.provenance)


@mcp.tool()
def fate_build_regulatory_handoff_review_packet(
    request: BuildRegulatoryHandoffReviewPacketRequest,
) -> RegulatoryHandoffReviewPacket:
    """Build a governed assessor-facing packet that bundles resolution preview, handoff package, and summary."""
    return build_regulatory_handoff_review_packet(request, RUNTIME.provenance)


@mcp.tool()
def fate_build_regulatory_handoff_review_brief(
    request: BuildRegulatoryHandoffReviewBriefRequest,
) -> RegulatoryHandoffReviewBrief:
    """Build a deterministic assessor-facing review brief from a governed regulatory handoff review packet."""
    return build_regulatory_handoff_review_brief(request, RUNTIME.provenance)


@mcp.tool()
def fate_recommend_regulatory_handoff_profile(
    request: RecommendRegulatoryHandoffProfileRequest,
) -> RegulatoryHandoffProfileRecommendation:
    """Recommend a governed regulatory handoff profile for a downstream suite consumer."""
    return recommend_regulatory_handoff_profile(request, RUNTIME.provenance)


@mcp.tool()
def fate_preview_regulatory_handoff_resolution(
    request: PreviewRegulatoryHandoffResolutionRequest,
) -> RegulatoryHandoffResolutionPreview:
    """Preview how Environmental Fate MCP will resolve a regulatory handoff selector before export."""
    return preview_regulatory_handoff_resolution(request, RUNTIME.provenance)


@mcp.prompt(
    name="fate_request_model_family_selection_for_profile",
    title="Request Model Family Selection",
    description="Render orchestration guidance and a request skeleton for a governed model-family selection profile.",
)
def prompt_request_model_family_selection_for_profile(
    profile_id: str = "reference_baseline_advective_challenge_v1",
    selection_goal: str = "screening model-family selection",
) -> str:
    """Build an Environmental Fate MCP model-family selection request prompt for a governed selection profile."""
    profile = _model_family_selection_profile_or_error(profile_id)
    request_payload = {
        "scenario": "<EnvironmentalReleaseScenario>",
        "selection_profile_id": profile.profile_id,
        "run_mode": profile.supported_run_modes[0].value if profile.supported_run_modes else "steady_state",
        "fit_for_purpose": profile.fit_for_purpose[0].value if profile.fit_for_purpose else "screening",
    }
    return (
        f"Prepare an Environmental Fate MCP model-family selection recommendation for {selection_goal}.\n\n"
        f"Profile: {profile.display_name} ({profile.profile_id})\n"
        f"Default model family: {profile.default_model_family.value}\n"
        f"Challenge model family: {profile.challenge_model_family.value}\n"
        f"Guidance: {profile.default_recommendation_template or 'Use the governed selection profile as declared.'}\n\n"
        "Call `fate_recommend_model_family_selection` with a request shaped like:\n"
        f"```json\n{json.dumps(request_payload, indent=2)}\n```\n\n"
        "Replace the scenario placeholder with a matched Environmental Fate MCP release scenario."
    )


@mcp.prompt(
    name="fate_review_model_family_selection_for_profile",
    title="Review Model Family Selection",
    description="Render governed assessor-facing review guidance for a model-family selection profile.",
)
def prompt_review_model_family_selection_for_profile(
    profile_id: str = "reference_baseline_advective_challenge_v1",
) -> str:
    """Build a governed review prompt for assessors or orchestrators reviewing a model-family selection recommendation."""
    profile = _model_family_selection_profile_or_error(profile_id)
    checklist_lines = "\n".join(
        f"- {item.code}: {item.prompt}"
        for item in profile.review_checklist
    ) or "- No explicit selection review checklist items declared."
    return (
        f"Review the Environmental Fate MCP model-family selection recommendation for profile {profile.display_name} "
        f"({profile.profile_id}).\n\n"
        f"Default model family: {profile.default_model_family.value}\n"
        f"Challenge model family: {profile.challenge_model_family.value}\n"
        f"Review brief template: {profile.review_brief_template or 'Use the governed selection profile as the review anchor.'}\n\n"
        "Governed selection review checklist:\n"
        f"{checklist_lines}\n\n"
        "Use `fate_recommend_model_family_selection` first, then "
        "`fate_preview_model_family_selection_review`, `fate_build_model_family_selection_review_packet`, "
        "and `fate_build_model_family_selection_review_brief` to produce the assessor-facing review artifact."
    )


@mcp.prompt(
    name="fate_review_model_family_challenge_for_profile",
    title="Review Model Family Challenge",
    description="Render governed assessor-facing guidance for a composed model-family challenge review built from selection and optional comparison review.",
)
def prompt_review_model_family_challenge_for_profile(
    profile_id: str = "reference_baseline_advective_challenge_review_v1",
) -> str:
    """Build a governed review prompt for assessors or orchestrators reviewing the full baseline-versus-challenge model-family path."""
    profile = _model_family_challenge_review_profile_or_error(profile_id)
    checklist_lines = "\n".join(
        f"- {item.code}: {item.prompt}"
        for item in profile.review_checklist
    ) or "- No explicit challenge-review checklist items declared."
    return (
        f"Review the full Environmental Fate MCP model-family challenge path for profile {profile.display_name} "
        f"({profile.profile_id}).\n\n"
        f"Selection profile: {profile.selection_profile_id}\n"
        f"Comparison profile: {profile.comparison_profile_id or 'No governed comparison profile declared'}\n"
        f"Review brief template: {profile.review_brief_template or 'Use the governed challenge-review profile as the review anchor.'}\n\n"
        "Governed challenge review checklist:\n"
        f"{checklist_lines}\n\n"
        "Use `fate_preview_model_family_challenge_review` to inspect the governed composed review status first. "
        "Then use `fate_build_model_family_challenge_review_packet` to compose the governed selection review and, "
        "when triggered, the governed comparison review into one assessor-facing artifact. Then use "
        "`fate_build_model_family_challenge_review_brief` to render the compact review summary."
    )


@mcp.prompt(
    name="fate_review_model_family_challenge_scientifically",
    title="Review Model Family Challenge Scientifically",
    description="Render assessor-facing guidance for the composed model-family challenge scientific dossier.",
)
def prompt_review_model_family_challenge_scientifically(
    profile_id: str = "reference_baseline_advective_challenge_review_v1",
) -> str:
    """Build a prompt for assessors who want one composed scientific dossier for the governed challenge path."""
    profile = _model_family_challenge_review_profile_or_error(profile_id)
    return (
        f"Review the full Environmental Fate MCP model-family challenge path scientifically for profile "
        f"{profile.display_name} ({profile.profile_id}).\n\n"
        f"Selection profile: {profile.selection_profile_id}\n"
        f"Comparison profile: {profile.comparison_profile_id or 'No governed comparison profile declared'}\n\n"
        "Use `fate_build_model_family_challenge_scientific_dossier` to compose the governed challenge-review packet "
        "with the primary and optional challenge-family scientific review packets. Then use "
        "`fate_build_model_family_challenge_scientific_dossier_brief` to render the compact assessor-facing summary "
        "that preserves challenge-review status, scientific review outcomes, benchmark context, and equation traces."
    )


@mcp.prompt(
    name="fate_request_model_family_comparison_for_profile",
    title="Request Model Family Comparison",
    description="Render orchestration guidance and a request skeleton for a governed model-family comparison profile.",
)
def prompt_request_model_family_comparison_for_profile(
    profile_id: str = "reference_vs_advective_screening_v1",
    comparison_goal: str = "matched-scenario screening comparison",
) -> str:
    """Build an Environmental Fate MCP model-family comparison request prompt for a governed comparison profile."""
    profile = _model_family_comparison_profile_or_error(profile_id)
    request_payload = {
        "scenario": "<EnvironmentalReleaseScenario>",
        "comparison_profile_id": profile.profile_id,
        "run_mode": profile.supported_run_modes[0].value if profile.supported_run_modes else "steady_state",
        "fit_for_purpose": profile.fit_for_purpose[0].value if profile.fit_for_purpose else "screening",
        "base_model_family": profile.base_model_family.value,
        "candidate_model_family": profile.candidate_model_family.value,
    }
    return (
        f"Prepare an Environmental Fate MCP model-family comparison for {comparison_goal}.\n\n"
        f"Profile: {profile.display_name} ({profile.profile_id})\n"
        f"Base model family: {profile.base_model_family.value}\n"
        f"Candidate model family: {profile.candidate_model_family.value}\n"
        f"Guidance: {profile.packet_template or 'Use the governed comparison profile as declared.'}\n\n"
        "Call `fate_build_model_family_comparison_packet` with a request shaped like:\n"
        f"```json\n{json.dumps(request_payload, indent=2)}\n```\n\n"
        "Replace the scenario placeholder with a matched Environmental Fate MCP release scenario."
    )


@mcp.prompt(
    name="fate_summarize_model_family_comparison_for_profile",
    title="Summarize Model Family Comparison",
    description="Render assessor-facing summary guidance for a governed model-family comparison profile.",
)
def prompt_summarize_model_family_comparison_for_profile(
    profile_id: str = "reference_vs_advective_screening_v1",
) -> str:
    """Build a summary prompt for a governed model-family comparison profile."""
    profile = _model_family_comparison_profile_or_error(profile_id)
    return (
        f"Summarize the Environmental Fate MCP model-family comparison for profile {profile.display_name} "
        f"({profile.profile_id}).\n\n"
        f"Base model family: {profile.base_model_family.value}\n"
        f"Candidate model family: {profile.candidate_model_family.value}\n"
        f"Brief template: {profile.brief_template or 'Preserve the governed comparison profile as declared.'}\n\n"
        "Use `fate_build_model_family_comparison_packet` first, then `fate_build_model_family_comparison_brief` "
        "to produce the compact assessor-facing comparison artifact."
    )


@mcp.prompt(
    name="fate_review_model_family_comparison_for_profile",
    title="Review Model Family Comparison",
    description="Render governed assessor-facing review guidance for a model-family comparison profile.",
)
def prompt_review_model_family_comparison_for_profile(
    profile_id: str = "reference_vs_advective_screening_v1",
) -> str:
    """Build a governed review prompt for assessors or orchestrators reviewing a model-family comparison."""
    profile = _model_family_comparison_profile_or_error(profile_id)
    checklist_lines = "\n".join(
        f"- {item.code}: {item.prompt}"
        for item in profile.review_checklist
    ) or "- No explicit comparison review checklist items declared."
    return (
        f"Review the Environmental Fate MCP model-family comparison for profile {profile.display_name} "
        f"({profile.profile_id}).\n\n"
        f"Base model family: {profile.base_model_family.value}\n"
        f"Candidate model family: {profile.candidate_model_family.value}\n"
        f"Review brief template: {profile.review_brief_template or 'Use the governed comparison profile as the review anchor.'}\n\n"
        "Governed comparison review checklist:\n"
        f"{checklist_lines}\n\n"
        "Use `fate_build_model_family_comparison_packet` first, then "
        "`fate_preview_model_family_comparison_review`, `fate_build_model_family_comparison_review_packet`, "
        "and `fate_build_model_family_comparison_review_brief` to produce the assessor-facing review artifact."
    )


@mcp.prompt(
    name="fate_request_scientific_review_for_model_family",
    title="Request Scientific Review",
    description="Render orchestration guidance and a request skeleton for a governed scientific review profile.",
)
def prompt_request_scientific_review_for_model_family(
    model_family: str = "reference_mass_balance",
    review_goal: str = "scientific screening review",
) -> str:
    """Build an Environmental Fate MCP scientific review request prompt for a governed model-family profile."""
    profile = _scientific_review_profile_or_error(model_family)
    request_payload = {
        "scenario": "<EnvironmentalReleaseScenario>",
        "result": "<ConcentrationEstimationResult>",
    }
    return (
        f"Prepare an Environmental Fate MCP scientific review packet for {review_goal}.\n\n"
        f"Model family: {profile.model_family.value}\n"
        f"Profile: {profile.display_name}\n"
        f"Guidance: {profile.packet_template or 'Use the governed scientific review profile as declared.'}\n\n"
        "Call `fate_build_scientific_review_packet` with a request shaped like:\n"
        f"```json\n{json.dumps(request_payload, indent=2)}\n```\n\n"
        "Replace the placeholders with a matched scenario/result pair from Environmental Fate MCP."
    )


@mcp.prompt(
    name="fate_summarize_scientific_review_for_model_family",
    title="Summarize Scientific Review",
    description="Render assessor-facing summary guidance for a governed scientific review profile.",
)
def prompt_summarize_scientific_review_for_model_family(
    model_family: str = "reference_mass_balance",
) -> str:
    """Build a summary prompt for a governed scientific review profile."""
    profile = _scientific_review_profile_or_error(model_family)
    checklist_lines = "\n".join(
        f"- {item.code}: {item.prompt}"
        for item in profile.review_checklist
    ) or "- No explicit scientific review checklist items declared."
    return (
        f"Summarize the Environmental Fate MCP scientific review for model family {profile.model_family.value}.\n\n"
        f"Profile: {profile.display_name}\n"
        f"Brief template: {profile.brief_template or 'Preserve the declared scientific review boundary and review cues.'}\n\n"
        "Governed scientific review checklist:\n"
        f"{checklist_lines}\n\n"
        "Use `fate_build_scientific_review_packet` first, then `fate_build_scientific_review_brief` "
        "to produce the assessor-facing scientific review artifact."
    )


@mcp.prompt(
    name="fate_summarize_run_trust_for_model_family",
    title="Summarize Run Trust",
    description="Render reviewer-facing guidance for a compact run-level bounded-screening trust brief.",
)
def prompt_summarize_run_trust_for_model_family(
    model_family: str = "reference_mass_balance",
    review_goal: str = "run-level bounded-screening trust review",
) -> str:
    """Build a compact reviewer-facing prompt for a run-level trust brief."""
    profile = _scientific_review_profile_or_error(model_family)
    request_payload = {
        "scenario": "<EnvironmentalReleaseScenario>",
        "result": "<ConcentrationEstimationResult>",
    }
    return (
        f"Prepare an Environmental Fate MCP run trust brief for {review_goal}.\n\n"
        f"Model family: {profile.model_family.value}\n"
        f"Profile: {profile.display_name}\n\n"
        "Call `fate_build_run_scientific_trust_brief` with a request shaped like:\n"
        f"```json\n{json.dumps(request_payload, indent=2)}\n```\n\n"
        "Use this compact run brief when you need a one-shot answer on bounded-screening suitability, "
        "default-evidence posture, top uncertainty signals, and residual caveats. "
        "If you need equation traces or the full checklist path, follow up with "
        "`fate_build_scientific_review_packet` and `fate_build_scientific_review_brief`."
    )


@mcp.prompt(
    name="fate_review_scientific_methods_for_model_family",
    title="Review Scientific Methods",
    description="Render assessor-facing guidance for a model-family scientific methods dossier.",
)
def prompt_review_scientific_methods_for_model_family(
    model_family: str = "reference_mass_balance",
) -> str:
    """Build a summary prompt for a governed scientific methods dossier."""
    profile = _scientific_review_profile_or_error(model_family)
    applicability_profile = DEFAULTS.model_family_applicability_profile(model_family)
    applicability_note = (
        applicability_profile.applicability_note
        if applicability_profile is not None and applicability_profile.applicability_note
        else "Use the governed applicability profile as declared."
    )
    return (
        f"Review the governed Environmental Fate MCP scientific methods surface for model family {profile.model_family.value}.\n\n"
        f"Profile: {profile.display_name}\n"
        f"Applicability note: {applicability_note}\n\n"
        "Use `fate_build_scientific_methods_dossier` to build the model-family methods dossier from governed "
        "scientific validation claims, benchmark coverage, and applicability policy. Then use "
        "`fate_build_scientific_methods_dossier_brief` to render the compact assessor-facing summary."
    )


@mcp.prompt(
    name="fate_review_release_trust_for_screening",
    title="Review Release Trust",
    description="Render reviewer-facing guidance for the release trust surface, defaults evidence posture, corroboration posture, and blocker state.",
)
def prompt_review_release_trust_for_screening(
    review_goal: str = "skeptical scientific trust review",
) -> str:
    """Build a reviewer-facing prompt for the release trust surface and its governed trust artifacts."""
    return (
        f"Review the Environmental Fate MCP release trust surface for {review_goal}.\n\n"
        "Start with the governed reviewer-facing artifacts and keep the MCP boundary explicit.\n\n"
        "Read these resources first:\n"
        "- `docs://scientific-trust-brief`\n"
        "- `release://defaults-rebaseline-report`\n"
        "- `release://reference-corroboration-report`\n"
        "- `release://reference-worksheet-manifest`\n"
        "- `release://advective-promotion-bar-report`\n"
        "- `release://external-corroboration-report`\n"
        "- `release://erosion-sediment-validation-demo-report`\n"
        "- `docs://scientific-trust-pack`\n"
        "- `release://red-team-review-report`\n"
        "- `release://readiness-report`\n"
        "- `docs://release-readiness`\n"
        "- `docs://regulatory-quick-start`\n\n"
        "Use `release://resource-manifest` and `docs://manifest` if you need discovery context before drilling into the trust artifacts.\n\n"
        "Focus the review on:\n"
        "- whether the shipped default path is free of tier-3 internal screening assumptions and carries explicit rebaseline delta records\n"
        "- whether mandatory reference-family claims satisfy the reviewer-grade corroboration bar with official grounding, worksheet manifest links, and machine-readable expected-output artifacts\n"
        "- whether the advective family remains explicitly experimental and non-promotable in the release artifacts\n"
        "- whether mandatory claims show explicit corroboration status, official source counts, jurisdiction breadth, and next actions\n"
        "- whether the red-team artifact shows unresolved blocker findings or only accepted public limitations\n"
        "- whether the trust pack, release readiness doc, and quick-start exclusions all tell the same story about when not to use this MCP\n"
        "- whether the release still looks appropriate for bounded screening rather than regulator acceptance or source-engine equivalence\n\n"
        "Return a compact reviewer summary with:\n"
        "- release trust status\n"
        "- default-evidence posture\n"
        "- reference-family proof posture and corroboration posture for mandatory claims\n"
        "- advective-family promotion-bar posture\n"
        "- red-team blocker state\n"
        "- top residual caveats or strengthening actions\n"
        "- an explicit answer on whether the release remains appropriate for bounded screening use"
    )


@mcp.prompt(
    name="fate_review_reference_family_proof_for_screening",
    title="Review Reference Proof",
    description="Render reviewer-facing guidance for the reviewer-grade reference-family proof surface.",
)
def prompt_review_reference_family_proof_for_screening(
    review_goal: str = "reviewer-grade reference proof audit",
) -> str:
    """Build a reviewer-facing prompt for the mandatory reference-family proof surface."""
    return (
        f"Review the Environmental Fate MCP reference-family proof surface for {review_goal}.\n\n"
        "Treat `reference_mass_balance` as the reviewer-grade anchor and audit whether the released proof surface justifies that posture.\n\n"
        "Read these resources first:\n"
        "- `docs://reference-proof-brief`\n"
        "- `docs://scientific-trust-brief`\n"
        "- `release://reference-corroboration-report`\n"
        "- `release://reference-worksheet-manifest`\n"
        "- `release://defaults-rebaseline-report`\n"
        "- `docs://scientific-trust-pack`\n"
        "- `release://readiness-report`\n\n"
        "Use `fate_build_scientific_methods_dossier` and `fate_build_scientific_methods_dossier_brief` for `reference_mass_balance` if you need the governed claim-set narrative behind the release artifacts.\n\n"
        "Focus the review on:\n"
        "- whether every mandatory `reference_mass_balance` claim has at least two independent evidence families\n"
        "- whether every mandatory reference claim has official guidance, official modeling guidance, or official test-guideline grounding\n"
        "- whether every mandatory reference claim has explicit `officialSourceIds`, `worksheetArtifactPath`, `expectedOutputArtifactPath`, `worksheetStatus`, `lastReviewedDate`, and `toleranceBasis` metadata\n"
        "- whether every mandatory reference claim has machine-readable hand-worked worksheet support and expected-output artifacts linked through the worksheet manifest\n"
        "- whether the shipped defaults rebaseline is explicit, citation-backed, and free of tier-3 continuity assumptions\n"
        "- whether the public wording consistently treats `reference_mass_balance` as the reviewer-grade bounded-screening anchor rather than regulator acceptance\n\n"
        "Return a compact reviewer summary with:\n"
        "- reference-family proof status\n"
        "- defaults rebaseline posture\n"
        "- mandatory claim corroboration posture\n"
        "- any missing worksheet or guidance gaps\n"
        "- an explicit answer on whether the reference family remains reviewer-grade for bounded screening"
    )


@mcp.prompt(
    name="fate_review_advective_promotion_bar",
    title="Review Advective Promotion Bar",
    description="Render reviewer-facing guidance for the experimental advective-family promotion bar and non-promotable reasons.",
)
def prompt_review_advective_promotion_bar(
    review_goal: str = "experimental advective promotion-bar audit",
) -> str:
    """Build a reviewer-facing prompt for the advective-family promotion bar."""
    return (
        f"Review the Environmental Fate MCP advective-family promotion bar for {review_goal}.\n\n"
        "Treat `advective_screening_mass_balance` as an experimental challenge family and verify that the release artifacts keep it non-promotable unless a later explicit decision changes that policy.\n\n"
        "Read these resources first:\n"
        "- `docs://advective-promotion-brief`\n"
        "- `release://advective-promotion-bar-report`\n"
        "- `docs://scientific-trust-pack`\n"
        "- `release://reference-corroboration-report`\n"
        "- `release://readiness-report`\n"
        "- `docs://release-readiness`\n\n"
        "Use `fate_build_scientific_methods_dossier` and `fate_build_scientific_methods_dossier_brief` for `advective_screening_mass_balance` if you need the governed claim-level support and promotion-blocker detail.\n\n"
        "Focus the review on:\n"
        "- whether `advective_screening_mass_balance` remains explicitly experimental in every reviewer-facing surface\n"
        "- whether the non-promotable reasons are explicit and concrete, including missing official corroboration, insufficient independent evidence, sensitivity-only support, or missing reference-style anchors\n"
        "- whether no prompt, trust pack, or readiness artifact silently treats the advective family as a decision-facing baseline\n"
        "- whether the release still frames the advective family as baseline-versus-challenge interpretation rather than parity with the reference family\n\n"
        "Return a compact reviewer summary with:\n"
        "- advective promotion-bar status\n"
        "- explicit non-promotable reasons\n"
        "- any language drift or governance gaps\n"
        "- an explicit answer on whether the advective family remains correctly constrained to the experimental challenge lane"
    )


@mcp.prompt(
    name="fate_request_external_result_import",
    title="Request External Result Import",
    description="Render orchestration guidance and a request skeleton for the public normalized external payload import contract.",
)
def prompt_request_external_result_import(
    import_profile_id: str = "normalized_external_payload_json",
    import_goal: str = "external screening result normalization",
) -> str:
    """Build an Environmental Fate MCP prompt for importing a public normalized external payload."""
    profile = _public_adapter_import_profile_or_error(import_profile_id)
    request_payload = {
        "scenario": "<EnvironmentalReleaseScenario>",
        "run_options": {
            "model_family": "external_result_adapter",
            "run_mode": profile.accepted_modes[0].value if profile.accepted_modes else "steady_state",
            "region_profile_id": "eu_screening_default",
        },
        "payload_path": "path/to/payload"
        + profile.accepted_extensions[0],
        "import_profile_id": profile.profile_id,
    }
    return (
        f"Prepare an Environmental Fate MCP external payload import for {import_goal}.\n\n"
        f"Profile: {profile.display_name} ({profile.profile_id})\n"
        f"Accepted extensions: {', '.join(profile.accepted_extensions)}\n"
        f"Accepted run modes: {', '.join(mode.value for mode in profile.accepted_modes)}\n"
        f"Guidance: {profile.description}\n\n"
        "Call `fate_import_external_result_payload` with a request shaped like:\n"
        f"```json\n{json.dumps(request_payload, indent=2)}\n```\n\n"
        "Replace the scenario placeholder with a matched Environmental Fate MCP release scenario and "
        "point `payload_path` at a normalized external JSON or CSV payload file."
    )


@mcp.prompt(
    name="fate_request_erosion_sediment_transport_screening",
    title="Request Erosion Sediment Transport Screening",
    description="Render a bounded workflow for RUSLE/MUSLE erosion-mediated transport screening.",
)
def prompt_request_erosion_sediment_transport_screening(
    screening_goal: str = "erosion-mediated sediment transport screening",
) -> str:
    """Build an Environmental Fate MCP prompt for scalar erosion/sediment transport screening."""
    relevance_payload = {"scenario": "<EnvironmentalReleaseScenario>"}
    rusle_payload = {
        "rainfall_erosivity_r": 150.0,
        "soil_erodibility_k": 0.28,
        "slope_length_steepness_ls": 1.6,
        "cover_management_c": 0.12,
        "support_practice_p": 0.8,
        "area_ha": 2.5,
    }
    musle_payload = {
        "runoff_volume_m3": 1200.0,
        "peak_runoff_rate_m3_s": 2.4,
        "soil_erodibility_k": 0.28,
        "slope_length_steepness_ls": 1.6,
        "cover_management_c": 0.12,
        "support_practice_p": 0.8,
    }
    load_payload = {
        "soil_concentration_mg_kg": 2.5,
        "sediment_yield_t": "<sediment_yield_t_event>",
        "sediment_delivery_ratio": 0.35,
        "particle_bound_availability_fraction": 0.75,
    }
    return (
        f"Prepare Environmental Fate MCP erosion/sediment transport screening for {screening_goal}.\n\n"
        "Read `defaults://erosion-sediment-method-profiles` first to preserve the governed method boundary.\n\n"
        "Recommended workflow:\n"
        "1. Call `fate_screen_erosion_transport_relevance` with:\n"
        f"```json\n{json.dumps(relevance_payload, indent=2)}\n```\n"
        "2. Use `fate_estimate_soil_loss_rusle` for annual erosion potential when RUSLE factors are available:\n"
        f"```json\n{json.dumps(rusle_payload, indent=2)}\n```\n"
        "3. Use `fate_estimate_event_sediment_yield_musle` for event sediment yield when runoff volume and peak flow are available:\n"
        f"```json\n{json.dumps(musle_payload, indent=2)}\n```\n"
        "4. If a sediment-associated chemical handoff is needed, call `fate_estimate_sediment_associated_chemical_load` with:\n"
        f"```json\n{json.dumps(load_payload, indent=2)}\n```\n\n"
        "Keep the result framed as bounded scalar screening. Do not present it as a GIS routing, "
        "WEPP execution, receiving-water concentration, exposure, risk, or regulatory decision."
    )


@mcp.prompt(
    name="fate_request_erosion_sediment_validation_case",
    title="Request Erosion Sediment Validation Case",
    description="Render a bounded workflow for inline erosion/sediment screening validation QA.",
)
def prompt_request_erosion_sediment_validation_case(
    validation_goal: str = "erosion/sediment screening validation QA",
) -> str:
    """Build an Environmental Fate MCP prompt for scalar erosion/sediment validation QA."""
    observed_records = [
        {
            "record_id": "event-001",
            "quantity": "event_sediment_yield_t",
            "observed_value": 12.0,
            "unit": "t/event",
            "context_label": "illustrative monitored storm event",
        }
    ]
    predicted_records = [
        {
            "record_id": "event-001",
            "quantity": "event_sediment_yield_t",
            "predicted_value": 11.4,
            "unit": "t/event",
            "method_id": "musle",
        }
    ]
    case_payload = {
        "observed_records": observed_records,
        "predicted_records": predicted_records,
        "validation_profile_id": "erosion_sediment_screening_validation_v1",
    }
    fit_payload = {"validation_case": "<ErosionSedimentValidationCaseResult>"}
    return (
        f"Prepare Environmental Fate MCP erosion/sediment validation QA for {validation_goal}.\n\n"
        "Read `defaults://erosion-sediment-validation-profiles` before interpreting fit thresholds.\n\n"
        "Recommended workflow:\n"
        "1. Run the relevant scalar screening tool first: `fate_estimate_soil_loss_rusle`, "
        "`fate_estimate_event_sediment_yield_musle`, or "
        "`fate_estimate_sediment_associated_chemical_load`.\n"
        "2. Call `fate_build_erosion_sediment_validation_case` with observed and predicted "
        "records paired by `record_id`:\n"
        f"```json\n{json.dumps(case_payload, indent=2)}\n```\n"
        "3. Call `fate_assess_erosion_sediment_validation_fit` with:\n"
        f"```json\n{json.dumps(fit_payload, indent=2)}\n```\n\n"
        "Interpret classifications as screening QA only. Do not use them as calibration, "
        "parameter optimization, GIS routing, WEPP execution, regulatory acceptance, or final risk."
    )


@mcp.prompt(
    name="fate_request_regulatory_handoff_for_profile",
    title="Request Regulatory Handoff",
    description="Render orchestration guidance and a request skeleton for a governed Environmental Fate MCP handoff profile.",
)
def prompt_request_regulatory_handoff_for_profile(
    profile_id: str = "exposure_scenario_mcp_v1",
    downstream_goal: str = "downstream screening assessment",
) -> str:
    """Build an Environmental Fate MCP handoff request prompt for a governed downstream consumer profile."""
    profile = _regulatory_handoff_profile_or_error(profile_id)
    request_payload = {
        "result": "<ConcentrationEstimationResult>",
        "handoff_profile_id": profile.profile_id,
        "target_modules": [profile.target_module],
    }
    return (
        f"Prepare an Environmental Fate MCP regulatory handoff for {downstream_goal}.\n\n"
        f"Profile: {profile.display_name} ({profile.profile_id})\n"
        f"Target module: {profile.target_module}\n"
        f"Guidance: {profile.tool_request_template or 'Use the governed handoff profile as declared.'}\n\n"
        "Call `fate_export_regulatory_handoff_package` with a request shaped like:\n"
        f"```json\n{json.dumps(request_payload, indent=2)}\n```\n\n"
        "Replace `<ConcentrationEstimationResult>` with the upstream result from Environmental Fate MCP concentration estimation "
        "or the external adapter normalization path."
    )


@mcp.prompt(
    name="fate_request_regulatory_handoff_for_consumer",
    title="Request Regulatory Handoff For Consumer",
    description="Render orchestration guidance after recommending the right governed handoff profile for a named downstream consumer.",
)
def prompt_request_regulatory_handoff_for_consumer(
    consumer_name: str,
    downstream_goal: str = "downstream screening assessment",
) -> str:
    """Build an Environmental Fate MCP handoff request prompt for a named downstream suite consumer."""
    recommendation = DEFAULTS.recommend_regulatory_handoff_profile(consumer_name)
    if recommendation is None:
        raise ValueError(
            f"Unknown downstream consumer {consumer_name}. Use fate_recommend_regulatory_handoff_profile first."
        )
    request_payload = {
        "result": "<ConcentrationEstimationResult>",
        "consumer_name": consumer_name,
        "target_modules": [recommendation.target_module],
    }
    return (
        f"Prepare an Environmental Fate MCP regulatory handoff for {downstream_goal}.\n\n"
        f"Consumer: {consumer_name}\n"
        f"Recommended profile: {recommendation.resolved_profile_id}\n"
        f"Matched hint: {recommendation.matched_hint}\n"
        f"Confidence: {recommendation.confidence:.2f}\n"
        f"Guidance: {recommendation.tool_request_template or 'Use the governed recommended handoff profile.'}\n\n"
        "Call `fate_export_regulatory_handoff_package` with a request shaped like:\n"
        f"```json\n{json.dumps(request_payload, indent=2)}\n```\n"
    )


@mcp.prompt(
    name="fate_summarize_regulatory_handoff_for_profile",
    title="Summarize Regulatory Handoff",
    description="Render consumer-specific response guidance for a governed Environmental Fate MCP handoff profile.",
)
def prompt_summarize_regulatory_handoff_for_profile(
    profile_id: str = "exposure_scenario_mcp_v1",
) -> str:
    """Build a consumer-specific summary prompt for a governed regulatory handoff profile."""
    profile = _regulatory_handoff_profile_or_error(profile_id)
    return (
        f"Summarize the Environmental Fate MCP regulatory handoff for profile {profile.display_name} "
        f"({profile.profile_id}).\n\n"
        f"Target module: {profile.target_module}\n"
        f"Summary template: {profile.response_summary_template or 'Preserve the governed handoff fields unchanged.'}\n\n"
        "Keep the profile-specific downstream field, concentration units, time semantics, and limitation notes intact."
    )


@mcp.prompt(
    name="fate_review_regulatory_handoff_for_profile",
    title="Review Regulatory Handoff",
    description="Render governed assessor-facing review guidance for a regulatory handoff profile.",
)
def prompt_review_regulatory_handoff_for_profile(
    profile_id: str = "exposure_scenario_mcp_v1",
) -> str:
    """Build a governed review prompt for assessors or orchestrators reviewing a regulatory handoff."""
    profile = _regulatory_handoff_profile_or_error(profile_id)
    checklist_lines = "\n".join(
        f"- {item.code}: {item.prompt}"
        for item in profile.review_checklist
    ) or "- No explicit review checklist items declared."
    return (
        f"Review the Environmental Fate MCP regulatory handoff for profile {profile.display_name} "
        f"({profile.profile_id}).\n\n"
        f"Target module: {profile.target_module}\n"
        f"Review brief template: {profile.review_brief_template or 'Use the governed concentration-only boundary as the review anchor.'}\n\n"
        "Governed review checklist:\n"
        f"{checklist_lines}\n\n"
        "Use `fate_build_regulatory_handoff_review_packet` first, then `fate_build_regulatory_handoff_review_brief` "
        "to produce the assessor-facing review artifact."
    )


@mcp.resource("contracts://manifest")
def contracts_manifest() -> str:
    return json.dumps(build_contract_manifest(), indent=2)


@mcp.resource("schemas://{schema_name}")
def schema_resource(schema_name: str) -> str:
    _validate_resource_name(schema_name)
    path = REPO_ROOT / "docs" / "contracts" / "schemas" / f"{schema_name}.json"
    return path.read_text()


@mcp.resource("examples://{example_name}")
def example_resource(example_name: str) -> str:
    _validate_resource_name(example_name)
    path = REPO_ROOT / "schemas" / "examples" / f"{example_name}.json"
    return path.read_text()


@mcp.resource("defaults://manifest")
def defaults_manifest() -> str:
    return json.dumps(DEFAULTS.build_manifest(), indent=2)


@mcp.resource("defaults://adapter-unit-conversions")
def defaults_adapter_unit_conversions() -> str:
    return json.dumps(DEFAULTS.adapter_unit_conversion_manifest(), indent=2)


@mcp.resource("defaults://erosion-sediment-method-profiles")
def defaults_erosion_sediment_method_profiles() -> str:
    return DEFAULTS.erosion_sediment_method_profile_manifest().model_dump_json(indent=2)


@mcp.resource("defaults://erosion-sediment-validation-profiles")
def defaults_erosion_sediment_validation_profiles() -> str:
    return DEFAULTS.erosion_sediment_validation_profile_manifest().model_dump_json(indent=2)


@mcp.resource("defaults://erosion-sediment-validation-demo-pack")
def defaults_erosion_sediment_validation_demo_pack() -> str:
    return DEFAULTS.erosion_sediment_validation_demo_pack_manifest().model_dump_json(indent=2)


@mcp.resource("defaults://temperature-correction-policy")
def defaults_temperature_correction_policy() -> str:
    policy = DEFAULTS.temperature_correction_policy()
    return json.dumps(
        {
            "referenceTemperatureC": policy.reference_temperature_c,
            "minimumSupportedTemperatureC": policy.minimum_supported_temperature_c,
            "maximumSupportedTemperatureC": policy.maximum_supported_temperature_c,
            "correctionStrategy": policy.correction_strategy,
            "degradationQ10ByMedium": {
                medium.value: value for medium, value in policy.degradation_q10_by_medium.items()
            },
            "applicabilityNote": policy.applicability_note,
        },
        indent=2,
    )


@mcp.resource("defaults://model-family-selection-profiles")
def defaults_model_family_selection_profiles() -> str:
    return DEFAULTS.model_family_selection_profile_manifest().model_dump_json(indent=2)


@mcp.resource("defaults://model-family-selection-profile/{profile_id}")
def defaults_model_family_selection_profile(profile_id: str) -> str:
    profile = DEFAULTS.model_family_selection_profile(profile_id)
    if profile is None:
        raise KeyError(profile_id)
    return profile.model_dump_json(indent=2)


@mcp.resource("defaults://model-family-challenge-review-profiles")
def defaults_model_family_challenge_review_profiles() -> str:
    return DEFAULTS.model_family_challenge_review_profile_manifest().model_dump_json(indent=2)


@mcp.resource("defaults://model-family-challenge-review-profile/{profile_id}")
def defaults_model_family_challenge_review_profile(profile_id: str) -> str:
    profile = DEFAULTS.model_family_challenge_review_profile(profile_id)
    if profile is None:
        raise KeyError(profile_id)
    return profile.model_dump_json(indent=2)


@mcp.resource("defaults://model-family-comparison-profiles")
def defaults_model_family_comparison_profiles() -> str:
    return DEFAULTS.model_family_comparison_profile_manifest().model_dump_json(indent=2)


@mcp.resource("defaults://model-family-comparison-profile/{profile_id}")
def defaults_model_family_comparison_profile(profile_id: str) -> str:
    profile = DEFAULTS.model_family_comparison_profile(profile_id)
    if profile is None:
        raise KeyError(profile_id)
    return profile.model_dump_json(indent=2)


@mcp.resource("defaults://scientific-review-profiles")
def defaults_scientific_review_profiles() -> str:
    return DEFAULTS.scientific_review_profile_manifest().model_dump_json(indent=2)


@mcp.resource("defaults://scientific-review-profile/{model_family}")
def defaults_scientific_review_profile(model_family: str) -> str:
    profile = DEFAULTS.scientific_review_profile(model_family)
    if profile is None:
        raise KeyError(model_family)
    return profile.model_dump_json(indent=2)


@mcp.resource("defaults://model-family-applicability-profiles")
def defaults_model_family_applicability_profiles() -> str:
    return json.dumps(DEFAULTS.model_family_applicability_manifest(), indent=2)


@mcp.resource("defaults://model-family-applicability-profile/{model_family}")
def defaults_model_family_applicability_profile(model_family: str) -> str:
    profile = DEFAULTS.model_family_applicability_profile(model_family)
    if profile is None:
        raise KeyError(model_family)
    return profile.model_dump_json(indent=2)


@mcp.resource("defaults://scientific-validation-claims")
def defaults_scientific_validation_claims() -> str:
    return DEFAULTS.scientific_validation_claim_manifest().model_dump_json(indent=2)


@mcp.resource("defaults://scientific-reference-cases")
def defaults_scientific_reference_cases() -> str:
    return DEFAULTS.scientific_reference_case_manifest().model_dump_json(indent=2)


@mcp.resource("defaults://scientific-reference-case/{case_id}")
def defaults_scientific_reference_case(case_id: str) -> str:
    reference_case = DEFAULTS.scientific_reference_case(case_id)
    if reference_case is None:
        raise KeyError(case_id)
    return reference_case.model_dump_json(indent=2)


@mcp.resource("defaults://scientific-validation-claim/{claim_id}")
def defaults_scientific_validation_claim(claim_id: str) -> str:
    claim = DEFAULTS.scientific_validation_claim(claim_id)
    if claim is None:
        raise KeyError(claim_id)
    return claim.model_dump_json(indent=2)


@mcp.resource("defaults://adapter-unit-conversion/{compartment_code}")
def defaults_adapter_unit_conversion(compartment_code: str) -> str:
    rule = DEFAULTS.adapter_unit_conversion_rule(compartment_code)
    if rule is None:
        raise KeyError(compartment_code)
    return rule.model_dump_json(indent=2)


@mcp.resource("defaults://regulatory-handoff-profiles")
def defaults_regulatory_handoff_profiles() -> str:
    return json.dumps(DEFAULTS.regulatory_handoff_profile_manifest(), indent=2)


@mcp.resource("defaults://regulatory-handoff-consumer-aliases")
def defaults_regulatory_handoff_consumer_aliases() -> str:
    return DEFAULTS.regulatory_handoff_consumer_alias_manifest().model_dump_json(indent=2)


@mcp.resource("defaults://regulatory-handoff-target-matrix")
def defaults_regulatory_handoff_target_matrix() -> str:
    return DEFAULTS.regulatory_handoff_target_matrix_manifest().model_dump_json(indent=2)


@mcp.resource("defaults://regulatory-handoff-profile-recommendation/{consumer_name}")
def defaults_regulatory_handoff_profile_recommendation(consumer_name: str) -> str:
    recommendation = DEFAULTS.recommend_regulatory_handoff_profile(consumer_name)
    if recommendation is None:
        raise KeyError(consumer_name)
    return recommendation.model_dump_json(indent=2)


@mcp.resource("defaults://regulatory-handoff-profile/{profile_id}")
def defaults_regulatory_handoff_profile(profile_id: str) -> str:
    profile = DEFAULTS.regulatory_handoff_profile(profile_id)
    if profile is None:
        raise KeyError(profile_id)
    return profile.model_dump_json(indent=2)


@mcp.resource("adapters://import-manifest")
def adapters_import_manifest() -> str:
    return build_adapter_import_manifest(REPO_ROOT).model_dump_json(indent=2)


@mcp.resource("adapters://public-import-manifest")
def adapters_public_import_manifest() -> str:
    return build_public_adapter_import_manifest(REPO_ROOT).model_dump_json(indent=2)


@mcp.resource("adapters://fixture/{fixture_name}")
def adapters_fixture_descriptor(fixture_name: str) -> str:
    fixture = adapter_fixture_descriptor(REPO_ROOT, fixture_name)
    if fixture is None:
        raise KeyError(fixture_name)
    return fixture.model_dump_json(indent=2)


@mcp.resource("defaults://region-profiles")
def defaults_region_profiles() -> str:
    return json.dumps(DEFAULTS.region_profile_manifest(), indent=2)


@mcp.resource("defaults://region-profile/{region_id}")
def defaults_region_profile(region_id: str) -> str:
    for profile in DEFAULTS.list_region_profiles():
        if profile.region_id == region_id:
            return profile.model_dump_json(indent=2)
    raise KeyError(region_id)


@mcp.resource("defaults://physchem-parameter-policies")
def defaults_physchem_parameter_policies() -> str:
    return json.dumps(DEFAULTS.physchem_parameter_policy_manifest(), indent=2)


@mcp.resource("defaults://physchem-parameter-policy-families")
def defaults_physchem_parameter_policy_families() -> str:
    return json.dumps(DEFAULTS.physchem_parameter_policy_family_manifest(), indent=2)


@mcp.resource("defaults://physchem-parameter-policy-family/{family}")
def defaults_physchem_parameter_policy_family(family: str) -> str:
    policy_family = DEFAULTS.policy_family(family)
    if policy_family is None:
        raise KeyError(family)
    return policy_family.model_dump_json(indent=2)


@mcp.resource("defaults://physchem-parameter-policy/{parameter}")
def defaults_physchem_parameter_policy(parameter: str) -> str:
    policy = DEFAULTS.parameter_policy(parameter)
    if policy is None:
        raise KeyError(parameter)
    return policy.model_dump_json(indent=2)


@mcp.resource("fate-archetypes://manifest")
def fate_archetypes_manifest() -> str:
    return json.dumps(
        {
            "archetypes": [
                "regional_air_release_screening",
                "surface_water_discharge_screening",
                "agricultural_soil_loading_screening",
            ]
        },
        indent=2,
    )


@mcp.resource("docs://{doc_name}")
def docs_resource(doc_name: str) -> str:
    return read_doc(REPO_ROOT, doc_name)


@mcp.resource("docs://manifest")
def docs_manifest_resource() -> str:
    return json.dumps(build_doc_manifest(REPO_ROOT), indent=2)


@mcp.resource("benchmarks://manifest")
def benchmarks_resource() -> str:
    return json.dumps(benchmark_manifest(REPO_ROOT), indent=2)


@mcp.resource("benchmarks://scientific-validation-claim-coverage")
def benchmarks_scientific_validation_claim_coverage() -> str:
    return json.dumps(
        benchmark_manifest(REPO_ROOT)["scientificValidationClaimCoverage"],
        indent=2,
    )


_RELEASE_MARKDOWN_FILENAMES = {
    "scientific-trust-pack": "scientific-trust-pack.md",
    "scientific-trust-brief": "scientific-trust-brief.md",
    "reference-proof-brief": "reference-proof-brief.md",
    "advective-promotion-brief": "advective-promotion-brief.md",
}


def _prebuilt_release_report(report_name: str) -> dict | None:
    release_root = REPO_ROOT / "docs" / "releases" / f"v{VERSION}"
    for candidate_name, filename in REPORT_FILENAMES:
        if candidate_name == report_name:
            path = release_root / filename
            return json.loads(path.read_text()) if path.exists() else None
    markdown_filename = _RELEASE_MARKDOWN_FILENAMES.get(report_name)
    if markdown_filename is not None:
        path = release_root / markdown_filename
        return {"markdown": path.read_text()} if path.exists() else None
    return None


@mcp.resource("release://{report_name}")
def release_resource(report_name: str) -> str:
    prebuilt = _prebuilt_release_report(report_name)
    if prebuilt is not None:
        return json.dumps(prebuilt, indent=2)
    reports = build_release_reports(REPO_ROOT)
    return json.dumps(reports[report_name], indent=2)


@mcp.resource("release://resource-manifest")
def release_resource_manifest() -> str:
    resources = [
        {
            "name": report_name,
            "format": "json",
            "description": REPORT_DESCRIPTIONS[filename],
        }
        for report_name, filename in REPORT_FILENAMES
    ]
    resources.extend(
        [
            {
                "name": "scientific-trust-brief",
                "format": "json-wrapper",
                "description": "Compact reviewer-facing scientific trust brief exposed through release://scientific-trust-brief and directly as markdown via docs://scientific-trust-brief.",
            },
            {
                "name": "reference-proof-brief",
                "format": "json-wrapper",
                "description": "Compact reviewer-facing brief for the reviewer-grade reference-family proof surface exposed through release://reference-proof-brief and directly as markdown via docs://reference-proof-brief.",
            },
            {
                "name": "advective-promotion-brief",
                "format": "json-wrapper",
                "description": "Compact reviewer-facing brief for the experimental advective-family promotion bar exposed through release://advective-promotion-brief and directly as markdown via docs://advective-promotion-brief.",
            },
            {
                "name": "scientific-trust-pack",
                "format": "json-wrapper",
                "description": "Reviewer-facing scientific trust pack exposed through release://scientific-trust-pack and directly as markdown via docs://scientific-trust-pack.",
            },
            {
                "name": "docs://scientific-trust-brief",
                "format": "markdown",
                "description": REPORT_DESCRIPTIONS["scientific-trust-brief.md"],
            },
            {
                "name": "docs://scientific-trust-pack",
                "format": "markdown",
                "description": REPORT_DESCRIPTIONS["scientific-trust-pack.md"],
            },
            {
                "name": "docs://reference-proof-brief",
                "format": "markdown",
                "description": REPORT_DESCRIPTIONS["reference-proof-brief.md"],
            },
            {
                "name": "docs://advective-promotion-brief",
                "format": "markdown",
                "description": REPORT_DESCRIPTIONS["advective-promotion-brief.md"],
            },
        ]
    )
    return json.dumps({"resourceCount": len(resources), "resources": resources}, indent=2)


def create_server() -> FastMCP:
    ensure_supported_python_version()
    _configure_logging()
    ensure_contract_artifacts_current(REPO_ROOT)
    return mcp
