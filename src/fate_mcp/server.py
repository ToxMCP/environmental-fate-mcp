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

from fate_mcp.benchmarks import benchmark_manifest
from fate_mcp.contracts import build_contract_manifest, ensure_contract_artifacts_current
from fate_mcp.defaults import DefaultsRegistry
from fate_mcp.guidance import read_doc
from fate_mcp.integrations import (
    apply_physchem_evidence,
    assess_release_scenario_fit,
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
    export_exposure_consumption_package,
    export_regulatory_handoff_package,
    preview_model_family_comparison_review,
    preview_model_family_challenge_review,
    preview_model_family_selection_review,
    preview_scientific_review_outcome,
    preview_regulatory_handoff_resolution,
    recommend_model_family_selection,
    recommend_regulatory_handoff_profile,
    summarize_regulatory_handoff_package,
)
from fate_mcp.models import (
    ApplyPhyschemEvidenceRequest,
    AssessReleaseScenarioFitRequest,
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
    BuildScientificReviewBriefRequest,
    BuildScientificReviewPacketRequest,
    BuildRunUncertaintySummaryRequest,
    BuildRegulatoryHandoffReviewBriefRequest,
    BuildRegulatoryHandoffReviewPacketRequest,
    BuildConcentrationSurfaceBundleRequest,
    BuildEnvironmentalReleaseScenarioRequest,
    CompareFateScenariosRequest,
    EstimateProbabilisticMultimediaConcentrationsRequest,
    EstimateMultimediaConcentrationsRequest,
    FateModelRunOptions,
    Media,
    ModelFamily,
    ReleaseFraction,
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
    SummarizeRegulatoryHandoffPackageRequest,
)
from fate_mcp.plugins.external_result_adapter import (
    adapter_fixture_descriptor,
    build_adapter_import_manifest,
)
from fate_mcp.package_metadata import PACKAGE_NAME, VERSION
from fate_mcp.release_artifacts import build_release_reports
from fate_mcp.runtime import FateRuntime


REPO_ROOT = Path(__file__).resolve().parents[2]
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


def _logged_tool(*args, **kwargs):
    if len(args) == 1 and callable(args[0]) and not kwargs:
        fn = args[0]
        return _original_tool(_log_tool_call(fn))
    inner_decorator = _original_tool(*args, **kwargs)

    def decorator(fn):
        return inner_decorator(_log_tool_call(fn))

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


@mcp.tool()
def fate_build_environmental_release_scenario(
    request: BuildEnvironmentalReleaseScenarioRequest,
):
    """Validate and normalize an environmental release scenario."""
    return RUNTIME.build_environmental_release_scenario(request)


@mcp.tool()
def fate_estimate_multimedia_concentrations(
    request: EstimateMultimediaConcentrationsRequest,
):
    """Estimate deterministic or bounded concentration surfaces from a release scenario."""
    return RUNTIME.estimate(request.scenario, request.run_options)


@mcp.tool()
def fate_estimate_probabilistic_multimedia_concentrations(
    request: EstimateProbabilisticMultimediaConcentrationsRequest,
):
    """Estimate probabilistic percentile concentration surfaces by orchestrating governed distribution sampling over the deterministic kernels."""
    return RUNTIME.estimate_probabilistic(
        request.scenario,
        request.run_options,
        iterations=request.iterations,
        seed=request.seed,
    )


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
    base_result = runtime.estimate(
        base_scenario,
        FateModelRunOptions(
            region_profile_id=base_scenario.geographic_scope.region_id,
            model_family=ModelFamily.REFERENCE_MASS_BALANCE,
        ),
    )
    candidate_result = runtime.estimate(
        base_scenario,
        FateModelRunOptions(
            region_profile_id=base_scenario.geographic_scope.region_id,
            model_family=ModelFamily.ADVECTIVE_SCREENING_MASS_BALANCE,
        ),
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
    reference_result = runtime.estimate(
        scenario,
        FateModelRunOptions(
            region_profile_id=scenario.geographic_scope.region_id,
            model_family=ModelFamily.REFERENCE_MASS_BALANCE,
        ),
    )
    challenge_result = runtime.estimate(
        scenario,
        FateModelRunOptions(
            region_profile_id=scenario.geographic_scope.region_id,
            model_family=ModelFamily.ADVECTIVE_SCREENING_MASS_BALANCE,
        ),
    )
    request = BuildModelFamilyChallengeScientificDossierRequest(
        scenario=scenario,
    )
    return request.model_dump_json(indent=2)


@mcp.tool()
def fate_build_concentration_surface_bundle(request: BuildConcentrationSurfaceBundleRequest):
    """Package concentration surfaces and run metadata for downstream consumers."""
    return build_concentration_surface_bundle(request.result)


@mcp.tool()
def fate_compare_fate_scenarios(request: CompareFateScenariosRequest):
    """Compare two concentration-estimation results and surface the main drivers."""
    return compare_fate_scenarios(request, RUNTIME.provenance)


@mcp.tool()
def fate_apply_physchem_evidence(request: ApplyPhyschemEvidenceRequest) -> PhyschemEvidenceApplicationResult:
    """Attach supporting physicochemical evidence to scenario provenance."""
    return apply_physchem_evidence(request.scenario, request.evidence, RUNTIME.provenance)


@mcp.tool()
def fate_assess_release_scenario_fit(request: AssessReleaseScenarioFitRequest):
    """Assess whether the declared workflow is a good fit for the current scenario."""
    return assess_release_scenario_fit(request.scenario, request.run_options, RUNTIME.provenance)


@mcp.tool()
def fate_build_run_parameter_manifest(request: BuildRunParameterManifestRequest):
    """Build a machine-readable run parameter manifest that preserves resolved provenance and runtime consumption state."""
    return build_run_parameter_manifest(request.scenario, request.result, RUNTIME.provenance)


@mcp.tool()
def fate_build_run_uncertainty_summary(request: BuildRunUncertaintySummaryRequest):
    """Build a deterministic reviewer-facing uncertainty-driver summary without probabilistic inference."""
    return build_run_uncertainty_summary(request.scenario, request.result, RUNTIME.provenance)


@mcp.tool()
def fate_build_probabilistic_review_packet(request: BuildProbabilisticReviewPacketRequest):
    """Build an assessor-facing probabilistic review packet that preserves percentile surfaces, sampled drivers, and iteration health."""
    return build_probabilistic_review_packet(request, RUNTIME.provenance)


@mcp.tool()
def fate_build_probabilistic_review_brief(request: BuildProbabilisticReviewBriefRequest):
    """Render a compact assessor-facing brief from a probabilistic review packet."""
    return build_probabilistic_review_brief(request, RUNTIME.provenance)


@mcp.tool()
def fate_recommend_model_family_selection(request: RecommendModelFamilySelectionRequest):
    """Recommend whether to keep the default model-family baseline only or add a governed experimental challenge path."""
    return recommend_model_family_selection(request, RUNTIME.provenance)


@mcp.tool()
def fate_preview_model_family_selection_review(request: PreviewModelFamilySelectionReviewRequest):
    """Preview the governed assessor-facing review status for a model-family selection recommendation."""
    return preview_model_family_selection_review(request, RUNTIME.provenance)


@mcp.tool()
def fate_build_model_family_selection_review_packet(request: BuildModelFamilySelectionReviewPacketRequest):
    """Build a governed assessor-facing review packet from a model-family selection recommendation."""
    return build_model_family_selection_review_packet(request, RUNTIME.provenance)


@mcp.tool()
def fate_build_model_family_selection_review_brief(request: BuildModelFamilySelectionReviewBriefRequest):
    """Render a compact assessor-facing review brief from a model-family selection review packet."""
    return build_model_family_selection_review_brief(request, RUNTIME.provenance)


@mcp.tool()
def fate_preview_model_family_challenge_review(request: PreviewModelFamilyChallengeReviewRequest):
    """Preview the governed assessor-facing review status for the composed baseline-versus-challenge model-family path."""
    return preview_model_family_challenge_review(request, RUNTIME, RUNTIME.provenance)


@mcp.tool()
def fate_build_model_family_challenge_review_packet(request: BuildModelFamilyChallengeReviewPacketRequest):
    """Build a composed assessor-facing packet that bundles governed model-family selection review and optional comparison review."""
    return build_model_family_challenge_review_packet(request, RUNTIME, RUNTIME.provenance)


@mcp.tool()
def fate_build_model_family_challenge_review_brief(request: BuildModelFamilyChallengeReviewBriefRequest):
    """Render a compact assessor-facing brief from a composed model-family challenge review packet."""
    return build_model_family_challenge_review_brief(request, RUNTIME.provenance)


@mcp.tool()
def fate_build_model_family_challenge_scientific_dossier(
    request: BuildModelFamilyChallengeScientificDossierRequest,
):
    """Build a composed scientific dossier for the governed baseline-versus-challenge model-family path."""
    return build_model_family_challenge_scientific_dossier(request, RUNTIME, RUNTIME.provenance)


@mcp.tool()
def fate_build_model_family_challenge_scientific_dossier_brief(
    request: BuildModelFamilyChallengeScientificDossierBriefRequest,
):
    """Render a compact assessor-facing summary from a model-family challenge scientific dossier."""
    return build_model_family_challenge_scientific_dossier_brief(request, RUNTIME.provenance)


@mcp.tool()
def fate_build_model_family_comparison_packet(request: BuildModelFamilyComparisonPacketRequest):
    """Build a deterministic comparison packet for two model families run against the same scenario."""
    return build_model_family_comparison_packet(request, RUNTIME, RUNTIME.provenance)


@mcp.tool()
def fate_build_model_family_comparison_brief(request: BuildModelFamilyComparisonBriefRequest):
    """Render a compact comparison brief from a model-family comparison packet."""
    return build_model_family_comparison_brief(request)


@mcp.tool()
def fate_preview_model_family_comparison_review(request: PreviewModelFamilyComparisonReviewRequest):
    """Preview the governed assessor-facing review status for a model-family comparison packet."""
    return preview_model_family_comparison_review(request, RUNTIME.provenance)


@mcp.tool()
def fate_build_model_family_comparison_review_packet(request: BuildModelFamilyComparisonReviewPacketRequest):
    """Build a governed assessor-facing review packet from a model-family comparison packet."""
    return build_model_family_comparison_review_packet(request, RUNTIME.provenance)


@mcp.tool()
def fate_build_model_family_comparison_review_brief(request: BuildModelFamilyComparisonReviewBriefRequest):
    """Render a compact assessor-facing review brief from a model-family comparison review packet."""
    return build_model_family_comparison_review_brief(request, RUNTIME.provenance)


@mcp.tool()
def fate_preview_scientific_review_outcome(request: PreviewScientificReviewOutcomeRequest):
    """Preview the governed scientific review outcome and review status before building a full scientific review packet."""
    return preview_scientific_review_outcome(request, RUNTIME.provenance)


@mcp.tool()
def fate_build_scientific_review_packet(request: BuildScientificReviewPacketRequest):
    """Bundle fit assessment, parameter manifest, uncertainty summary, and sampled surfaces into one scientific review artifact."""
    return build_scientific_review_packet(request, RUNTIME.provenance)


@mcp.tool()
def fate_build_scientific_review_brief(request: BuildScientificReviewBriefRequest):
    """Render a compact scientific review brief from a scientific review packet."""
    return build_scientific_review_brief(request, RUNTIME.provenance)


@mcp.tool()
def fate_build_scientific_methods_dossier(request: BuildScientificMethodsDossierRequest):
    """Build a model-family scientific methods dossier from governed claims, benchmark coverage, and applicability policy."""
    return build_scientific_methods_dossier(request, RUNTIME.provenance)


@mcp.tool()
def fate_build_scientific_methods_dossier_brief(request: BuildScientificMethodsDossierBriefRequest):
    """Render a compact assessor-facing brief from a scientific methods dossier."""
    return build_scientific_methods_dossier_brief(request)


@mcp.tool()
def fate_reconcile_release_evidence(request: ReconcileReleaseEvidenceRequest):
    """Reconcile multiple release evidence records into a reviewable screening scenario."""
    return RUNTIME.reconcile_release_evidence(request)


@mcp.tool()
def fate_export_concentration_surface_bundle(request: ExportConcentrationSurfaceBundleRequest):
    """Export a normalized concentration-surface bundle."""
    return request.bundle


@mcp.tool()
def fate_export_exposure_consumption_package(request: ExportExposureConsumptionPackageRequest):
    """Build a concentration-only handoff package for downstream consumers."""
    return export_exposure_consumption_package(request, RUNTIME.provenance)


@mcp.tool()
def fate_export_regulatory_handoff_package(request: ExportRegulatoryHandoffPackageRequest):
    """Build a ToxMCP regulatory handoff crosswalk from concentration surfaces."""
    return export_regulatory_handoff_package(request, RUNTIME.provenance)


@mcp.tool()
def fate_summarize_regulatory_handoff_package(request: SummarizeRegulatoryHandoffPackageRequest):
    """Build a deterministic, consumer-specific summary for a governed regulatory handoff package."""
    return summarize_regulatory_handoff_package(request, RUNTIME.provenance)


@mcp.tool()
def fate_build_regulatory_handoff_review_packet(request: BuildRegulatoryHandoffReviewPacketRequest):
    """Build a governed assessor-facing packet that bundles resolution preview, handoff package, and summary."""
    return build_regulatory_handoff_review_packet(request, RUNTIME.provenance)


@mcp.tool()
def fate_build_regulatory_handoff_review_brief(request: BuildRegulatoryHandoffReviewBriefRequest):
    """Build a deterministic assessor-facing review brief from a governed regulatory handoff review packet."""
    return build_regulatory_handoff_review_brief(request, RUNTIME.provenance)


@mcp.tool()
def fate_recommend_regulatory_handoff_profile(request: RecommendRegulatoryHandoffProfileRequest):
    """Recommend a governed regulatory handoff profile for a downstream suite consumer."""
    return recommend_regulatory_handoff_profile(request, RUNTIME.provenance)


@mcp.tool()
def fate_preview_regulatory_handoff_resolution(request: PreviewRegulatoryHandoffResolutionRequest):
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


@mcp.resource("benchmarks://manifest")
def benchmarks_resource() -> str:
    return json.dumps(benchmark_manifest(REPO_ROOT), indent=2)


@mcp.resource("benchmarks://scientific-validation-claim-coverage")
def benchmarks_scientific_validation_claim_coverage() -> str:
    return json.dumps(
        benchmark_manifest(REPO_ROOT)["scientificValidationClaimCoverage"],
        indent=2,
    )


@mcp.resource("release://{report_name}")
def release_resource(report_name: str) -> str:
    reports = build_release_reports(REPO_ROOT)
    return json.dumps(reports[report_name], indent=2)


def create_server() -> FastMCP:
    _configure_logging()
    ensure_contract_artifacts_current(REPO_ROOT)
    return mcp
