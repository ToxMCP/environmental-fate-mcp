from __future__ import annotations

from collections import defaultdict
import hashlib
import json
import math

from fate_mcp.benchmarks import benchmark_manifest, supporting_benchmark_fixtures_for_claim
from fate_mcp.defaults import DefaultsRegistry
from fate_mcp.evidence import (
    evidence_weight,
    is_low_confidence_evidence,
    source_classification_for_evidence,
)
from fate_mcp.errors import FateValidationError
from fate_mcp.models import (
    BuildModelFamilyChallengeScientificDossierBriefRequest,
    BuildModelFamilyChallengeScientificDossierRequest,
    BuildModelFamilyChallengeReviewBriefRequest,
    BuildModelFamilyChallengeReviewPacketRequest,
    BuildScientificMethodsDossierBriefRequest,
    BuildScientificMethodsDossierRequest,
    BuildModelFamilySelectionReviewBriefRequest,
    BuildModelFamilySelectionReviewPacketRequest,
    BuildProbabilisticReviewBriefRequest,
    BuildProbabilisticReviewPacketRequest,
    BuildRunParameterManifestRequest,
    BuildModelFamilyComparisonBriefRequest,
    BuildModelFamilyComparisonPacketRequest,
    BuildModelFamilyComparisonReviewBriefRequest,
    BuildModelFamilyComparisonReviewPacketRequest,
    RecommendModelFamilySelectionRequest,
    BuildScientificReviewBriefRequest,
    BuildScientificReviewPacketRequest,
    PreviewModelFamilyChallengeReviewRequest,
    PreviewModelFamilyComparisonReviewRequest,
    PreviewModelFamilySelectionReviewRequest,
    PreviewScientificReviewOutcomeRequest,
    BuildRunUncertaintySummaryRequest,
    BuildRegulatoryHandoffReviewBriefRequest,
    BuildRegulatoryHandoffReviewPacketRequest,
    CompareFateScenariosRequest,
    ConcentrationEstimationResult,
    ConcentrationSurfaceBundle,
    DependencyDescriptor,
    ExportExposureConsumptionPackageRequest,
    ExportRegulatoryHandoffPackageRequest,
    ExposureConsumptionPackage,
    FateAssumptionRecord,
    FateModelRunOptions,
    FateParameterRecord,
    FateScenarioComparisonRecord,
    FitForPurpose,
    LimitationNote,
    ModelFamilyApplicabilityProfile,
    ModelFamilyComparisonBrief,
    ModelFamilyComparisonOutcome,
    ModelFamilyComparisonPacket,
    ModelFamilyComparisonProfile,
    ModelFamilyComparisonReviewBrief,
    ModelFamilyComparisonReviewCheck,
    ModelFamilyComparisonReviewChecklistItem,
    ModelFamilyComparisonReviewPacket,
    ModelFamilyComparisonReviewPreview,
    ModelFamilyChallengeReviewCheck,
    ModelFamilyChallengeScientificDossier,
    ModelFamilyChallengeScientificDossierBrief,
    ModelFamilyChallengeReviewChecklistItem,
    ModelFamilyChallengeReviewBrief,
    ModelFamilyChallengeReviewPacket,
    ModelFamilyChallengeReviewProfile,
    ModelFamilyChallengeReviewPreview,
    ModelFamilySelectionProfile,
    ModelFamilySelectionRecommendation,
    ModelFamilySelectionReviewBrief,
    ModelFamilySelectionReviewCheck,
    ModelFamilySelectionReviewChecklistItem,
    ModelFamilySelectionReviewPacket,
    ModelFamilySelectionReviewPreview,
    ModelFamilySelectionStatus,
    PhyschemEvidenceApplicationResult,
    PhyschemEvidenceConflict,
    PhyschemEvidenceObservation,
    PhyschemEvidenceRecord,
    ProbabilisticConcentrationResult,
    ProbabilisticReviewBrief,
    ProbabilisticReviewCheck,
    ProbabilisticReviewPacket,
    PreviewRegulatoryHandoffResolutionRequest,
    QualityFlag,
    RegulatoryCrosswalkEntry,
    RegulatoryHandoffEntrySummary,
    RegulatoryHandoffReviewBrief,
    RegulatoryHandoffReviewCheck,
    RegulatoryHandoffReviewChecklistItem,
    RegulatoryHandoffReviewPacket,
    RegulatoryHandoffResolutionPreview,
    RegulatoryHandoffPackage,
    RegulatoryHandoffPackageSummary,
    RegulatoryHandoffProfile,
    RegulatoryHandoffProfileRecommendation,
    RecommendRegulatoryHandoffProfileRequest,
    ReconciledPhyschemParameter,
    ReleaseScenarioFitAssessment,
    RunParameterManifest,
    RunParameterManifestEntry,
    RunMode,
    Severity,
    ScientificMethodsDossier,
    ScientificMethodsDossierBrief,
    ScientificMethodsDossierClaimSummary,
    ScientificMethodsPromotionBlockerSummary,
    ScientificMethodsPromotionStatus,
    ScientificMethodsRecommendedActionPromotionImpact,
    ScientificMethodsRecommendedActionPriority,
    ScientificMethodsRecommendedActionSummary,
    ScientificExternalCorroborationStatus,
    ScientificHighlightedClaimChallengeStatus,
    ScientificMethodsHighlightedClaimSummary,
    ScientificClaimSupportStrength,
    ScientificValidationClaim,
    ScientificValidationClaimCoverageRecord,
    ScientificReviewBrief,
    ScientificReviewCheck,
    ScientificReviewChecklistItem,
    ScientificReviewOutcome,
    ScientificReviewOutcomePreview,
    ScientificReviewPacket,
    ScientificReviewProfile,
    ScientificReviewSurfaceSummary,
    SummarizeRegulatoryHandoffPackageRequest,
    SurfaceDelta,
    SourceClassification,
    RunUncertaintySummary,
    UncertaintyDriver,
)
from fate_mcp.package_metadata import EXPERIMENTAL_MODEL_FAMILIES, VERSION
from fate_mcp.provenance import ProvenanceBuilder

DEFAULT_PHYSCHEM_RELATIVE_SPREAD_THRESHOLD = 0.5
DEFAULT_WEIGHTING_STRATEGY = "evidence_quality_weighted_mean"
CLAIM_PRIORITY_RANK = {
    "high": 0,
    "medium": 1,
    "low": 2,
}
REGULATORY_ROUTE_HINTS = {
    "ambient_air": "inhalation_precursor",
    "surface_water": "water_contact_or_drinking_water_precursor",
    "agricultural_soil": "soil_contact_or_crop_uptake_precursor",
    "freshwater_sediment": "sediment_contact_or_benthic_precursor",
}
REGULATORY_HANDOFF_ENTRY_FIELDS = {
    "source_surface_id",
    "medium",
    "compartment",
    "concentration_value",
    "concentration_unit",
    "time_window",
    "semantic_label",
    "downstream_field",
    "route_hint",
    "requires_dose_translation",
}
REGULATORY_REVIEW_EVIDENCE_FIELDS = {
    "target_module",
    "downstream_field",
    "entry_count",
    "route_hints",
    "time_window_modes",
    "mediums",
    "compartments",
    "equation_lines",
    "limitations",
    "profile_resolution_method",
}
SCIENTIFIC_REVIEW_EVIDENCE_FIELDS = {
    "fit_verdict",
    "applicability_lines",
    "parameter_quality_lines",
    "uncertainty_lines",
    "benchmark_reference_lines",
    "equation_lines",
    "surface_samples",
    "limitations",
    "model_family",
    "fit_for_purpose",
}
MODEL_FAMILY_COMPARISON_REVIEW_EVIDENCE_FIELDS = {
    "comparison_outcome",
    "comparison_profile_id",
    "dominant_delta_lines",
    "base_fit_verdict",
    "candidate_fit_verdict",
    "base_applicability_lines",
    "candidate_applicability_lines",
    "base_benchmark_reference_lines",
    "candidate_benchmark_reference_lines",
    "base_equation_lines",
    "candidate_equation_lines",
    "limitations",
    "run_mode",
    "fit_for_purpose",
}
MODEL_FAMILY_SELECTION_REVIEW_EVIDENCE_FIELDS = {
    "recommendation_status",
    "comparison_profile_id",
    "triggered_signal_lines",
    "primary_fit_verdict",
    "challenge_fit_verdict",
    "primary_applicability_lines",
    "challenge_applicability_lines",
    "limitations",
    "run_mode",
    "fit_for_purpose",
}
MODEL_FAMILY_CHALLENGE_REVIEW_EVIDENCE_FIELDS = {
    "selection_recommendation_status",
    "selection_review_status",
    "comparison_profile_id",
    "comparison_outcome",
    "comparison_review_status",
    "triggered_signal_lines",
    "dominant_delta_lines",
    "primary_applicability_lines",
    "challenge_applicability_lines",
    "comparison_guidance_lines",
    "governing_rule_lines",
    "limitations",
}
SEVERITY_RANK = {
    Severity.ERROR: 0,
    Severity.WARNING: 1,
    Severity.INFO: 2,
}
DRIVER_PRIORITY = {
    "evidence_conflict": 0,
    "unexecuted_treatment_assumption": 1,
    "default_screening_capacity": 2,
    "heuristic_parameter": 1,
    "unsupported_runtime_parameter": 3,
    "time_bucket_interpretive_burden": 4,
    "multi_medium_simplification_burden": 5,
    "default_heavy_parameter": 6,
}
MATERIAL_MODEL_FAMILY_RELATIVE_DELTA_THRESHOLD = 0.2
MATERIAL_MODEL_FAMILY_ABSOLUTE_DELTA_FLOOR = 1e-12
CONSERVATIVE_EVIDENCE_QUALITIES = {"regulatory"}
CAPACITY_PARAMETERS = {
    "ambient_air_volume_m3",
    "surface_water_volume_m3",
    "agricultural_soil_mass_kg",
    "freshwater_sediment_mass_kg",
}


from .common import REGULATORY_HANDOFF_ENTRY_FIELDS, REGULATORY_ROUTE_HINTS, TARGET_MODULE_ACKNOWLEDGEMENT_SCHEMA_URLS, _applicability_lines, _build_regulatory_review_checklist, _default_regulatory_handoff_resolution_preview, _ensure_scenario_matches_result, _parameter_quality_lines, _resolve_model_family_applicability, _resolve_regulatory_handoff_profile, _scientific_unsuitability_lines, _uncertainty_lines, _validated_target_modules
from .core import build_run_parameter_manifest, build_run_uncertainty_summary

def export_exposure_consumption_package(
    request: ExportExposureConsumptionPackageRequest,
    provenance_builder: ProvenanceBuilder,
) -> ExposureConsumptionPackage:
    result = request.result
    return ExposureConsumptionPackage(
        scenario_id=result.run_summary.scenario_id,
        surfaces=result.surfaces,
        geographic_scope=result.surfaces[0].geographic_scope,
        time_semantics=[surface.time_window for surface in result.surfaces],
        provenance=provenance_builder.bundle(),
        blockers=[],
        limitations=[
            LimitationNote(
                code="concentration_only",
                message="Package exports concentrations only; downstream consumers must perform concentration-to-dose translation.",
            )
        ],
    )



def recommend_regulatory_handoff_profile(
    request: RecommendRegulatoryHandoffProfileRequest,
    provenance_builder: ProvenanceBuilder,
) -> RegulatoryHandoffProfileRecommendation:
    recommendation = provenance_builder.defaults_registry.recommend_regulatory_handoff_profile(
        request.consumer_name
    )
    if recommendation is None:
        raise FateValidationError(
            code="unknown_regulatory_handoff_consumer",
            message=f"Could not resolve a governed regulatory handoff profile for consumer {request.consumer_name}.",
            suggestion="Inspect defaults://regulatory-handoff-profiles and choose a declared profile.",
        )
    return recommendation



def preview_regulatory_handoff_resolution(
    request: PreviewRegulatoryHandoffResolutionRequest,
    provenance_builder: ProvenanceBuilder,
) -> RegulatoryHandoffResolutionPreview:
    defaults_registry = provenance_builder.defaults_registry
    explicit_profile = (
        defaults_registry.regulatory_handoff_profile(request.handoff_profile_id)
        if request.handoff_profile_id
        else None
    )
    recommendation = (
        defaults_registry.recommend_regulatory_handoff_profile(request.consumer_name)
        if request.consumer_name
        else None
    )

    issues: list[str] = []
    if request.handoff_profile_id and explicit_profile is None:
        issues.append(f"Unknown profile id: {request.handoff_profile_id}")
    if request.consumer_name and recommendation is None:
        issues.append(f"Unknown or ambiguous consumer name: {request.consumer_name}")

    resolved_profile = explicit_profile
    status = "resolved"
    resolution_method = None
    resolution_basis = None
    resolution_confidence = None
    matched_hint = recommendation.matched_hint if recommendation else None

    if explicit_profile and recommendation:
        if recommendation.resolved_profile_id != explicit_profile.profile_id:
            status = "mismatch"
            issues.append(
                f"Consumer {request.consumer_name} resolves to {recommendation.resolved_profile_id}, "
                f"which conflicts with explicit profile {explicit_profile.profile_id}."
            )
            resolved_profile = None
        else:
            resolution_method = "explicit_profile_id_consumer_match"
            resolution_basis = recommendation.matched_hint
            resolution_confidence = recommendation.confidence
    elif explicit_profile:
        resolution_method = "explicit_profile_id"
        resolution_basis = explicit_profile.profile_id
        resolution_confidence = 1.0
    elif recommendation:
        resolved_profile = defaults_registry.regulatory_handoff_profile(recommendation.resolved_profile_id)
        resolution_method = "consumer_name_match"
        resolution_basis = recommendation.matched_hint
        resolution_confidence = recommendation.confidence

    if resolved_profile is None and status == "resolved":
        status = "unresolved"

    allowed_target_modules = [resolved_profile.target_module] if resolved_profile is not None else []
    target_modules_preview = request.target_modules or allowed_target_modules
    if resolved_profile is not None and request.target_modules:
        try:
            target_modules_preview = _validated_target_modules(request.target_modules, resolved_profile)
        except FateValidationError as exc:
            status = "mismatch"
            issues.append(exc.payload.message)
    return RegulatoryHandoffResolutionPreview(
        requested_profile_id=request.handoff_profile_id,
        consumer_name=request.consumer_name,
        recommended_profile_id=recommendation.resolved_profile_id if recommendation else None,
        resolved_profile_id=resolved_profile.profile_id if resolved_profile else None,
        resolution_method=resolution_method,
        resolution_basis=resolution_basis,
        resolution_confidence=resolution_confidence,
        matched_hint=matched_hint,
        target_module=resolved_profile.target_module if resolved_profile else None,
        allowed_target_modules=allowed_target_modules,
        target_modules_preview=target_modules_preview,
        downstream_field=resolved_profile.downstream_field if resolved_profile else None,
        required_entry_fields=resolved_profile.required_entry_fields if resolved_profile else [],
        status=status,
        issues=issues,
        tool_request_template=resolved_profile.tool_request_template if resolved_profile else None,
        response_summary_template=(
            resolved_profile.response_summary_template if resolved_profile else None
        ),
    )



def export_regulatory_handoff_package(
    request: ExportRegulatoryHandoffPackageRequest,
    provenance_builder: ProvenanceBuilder,
) -> RegulatoryHandoffPackage:
    result = request.result
    parameter_manifest = None
    uncertainty_summary = None
    if request.scenario is not None:
        _ensure_scenario_matches_result(request.scenario, result)
        parameter_manifest = build_run_parameter_manifest(
            request.scenario,
            result,
            provenance_builder,
        )
        uncertainty_summary = build_run_uncertainty_summary(
            request.scenario,
            result,
            provenance_builder,
        )
    handoff_profile, resolution_method, resolution_basis, resolution_confidence = (
        _resolve_regulatory_handoff_profile(
            request,
            provenance_builder.defaults_registry,
        )
    )
    unknown_required_fields = sorted(
        field
        for field in handoff_profile.required_entry_fields
        if field not in REGULATORY_HANDOFF_ENTRY_FIELDS
    )
    if unknown_required_fields:
        raise FateValidationError(
            code="invalid_regulatory_handoff_profile_field",
            message=(
                f"Regulatory handoff profile {handoff_profile.profile_id} declares unknown required fields: "
                f"{unknown_required_fields}."
            ),
            suggestion="Limit required_entry_fields to fields exposed by RegulatoryCrosswalkEntry.",
            details={"unknownRequiredFields": unknown_required_fields},
        )
    target_modules = _validated_target_modules(request.target_modules, handoff_profile)
    crosswalk_entries = [
        RegulatoryCrosswalkEntry(
            source_surface_id=surface.surface_id,
            medium=surface.medium,
            compartment=surface.compartment,
            concentration_value=surface.concentration_value,
            concentration_unit=surface.concentration_unit,
            time_window=surface.time_window,
            semantic_label="environmental_media_concentration",
            downstream_field=handoff_profile.downstream_field,
            route_hint=REGULATORY_ROUTE_HINTS[surface.compartment.value],
            equation_id=surface.calculation_trace.equation_id if surface.calculation_trace else None,
            equation_text=surface.calculation_trace.equation_text if surface.calculation_trace else None,
        )
        for surface in result.surfaces
    ]
    missing_required_fields = set()
    for entry in crosswalk_entries:
        payload = entry.model_dump(mode="json")
        for field in handoff_profile.required_entry_fields:
            if field not in payload or payload[field] is None:
                missing_required_fields.add(field)
                continue
            if isinstance(payload[field], str) and payload[field] == "":
                missing_required_fields.add(field)
    missing_required_fields = sorted(missing_required_fields)
    blockers = _scientific_unsuitability_lines(result.run_summary.escalation_concerns)
    if missing_required_fields:
        blockers.append(
            f"Regulatory handoff profile {handoff_profile.profile_id} requires fields that were not populated: {missing_required_fields}."
        )

    if handoff_profile.profile_id == "echa_csr_v1":
        compartments = {entry.compartment.value for entry in crosswalk_entries}
        required_compartments = {"ambient_air", "surface_water", "agricultural_soil", "freshwater_sediment"}
        if not required_compartments.issubset(compartments):
            missing_compartments = sorted(required_compartments - compartments)
            blockers.append(f"ECHA CSR requires concentration surfaces for {missing_compartments}.")

    if handoff_profile.profile_id == "epa_pmn_v1":
        modes = {entry.time_window.mode.value for entry in crosswalk_entries}
        if "time_bucket" not in modes:
            blockers.append("EPA PMN submission requires time-bucket semantics, but steady-state surfaces were provided.")

    target_module_acknowledgement_schema_url = TARGET_MODULE_ACKNOWLEDGEMENT_SCHEMA_URLS.get(
        handoff_profile.profile_id
    )

    return RegulatoryHandoffPackage(
        scenario_id=result.run_summary.scenario_id,
        handoff_profile_id=handoff_profile.profile_id,
        profile_resolution_method=resolution_method,
        profile_resolution_basis=resolution_basis,
        profile_resolution_confidence=resolution_confidence,
        source_module="fate_mcp",
        source_model_family=result.run_summary.model_family,
        target_modules=target_modules,
        crosswalk_entries=crosswalk_entries,
        parameter_manifest=parameter_manifest,
        uncertainty_summary=uncertainty_summary,
        provenance=provenance_builder.bundle(),
        target_module_acknowledgement_schema_url=target_module_acknowledgement_schema_url,
        blockers=blockers,
        limitations=[
            LimitationNote(
                code="concentration_only",
                message="Crosswalk exports concentrations only; downstream modules must perform route translation and dose calculation.",
            ),
            LimitationNote(
                code="suite_handoff_semantics",
                message="Crosswalk fields express ToxMCP handoff semantics, not final regulatory conclusions.",
            ),
            LimitationNote(
                code="handoff_profile",
                message=f"Crosswalk exported using governed handoff profile {handoff_profile.profile_id}.",
            ),
            LimitationNote(
                code="handoff_profile_resolution",
                message=(
                    f"Handoff profile was resolved via {resolution_method}"
                    + (f" using {resolution_basis}." if resolution_basis else ".")
                ),
            ),
        ],
    )



def summarize_regulatory_handoff_package(
    request: SummarizeRegulatoryHandoffPackageRequest,
    provenance_builder: ProvenanceBuilder,
) -> RegulatoryHandoffPackageSummary:
    package = request.package
    handoff_profile = provenance_builder.defaults_registry.regulatory_handoff_profile(
        package.handoff_profile_id
    )
    if handoff_profile is None:
        raise FateValidationError(
            code="unknown_regulatory_handoff_profile",
            message=f"Unknown regulatory handoff profile: {package.handoff_profile_id}.",
            suggestion="Use a handoff package generated from a declared governed profile.",
        )
    expected_targets = [handoff_profile.target_module]
    if package.target_modules != expected_targets:
        raise FateValidationError(
            code="regulatory_handoff_package_target_mismatch",
            message=(
                f"Regulatory handoff package target_modules {package.target_modules} do not match governed "
                f"target module {handoff_profile.target_module} for profile {handoff_profile.profile_id}."
            ),
            suggestion="Rebuild the handoff package with the governed target module mapping.",
            details={
                "packageTargetModules": package.target_modules,
                "governedTargetModule": handoff_profile.target_module,
                "profileId": handoff_profile.profile_id,
            },
        )

    route_hints = sorted({entry.route_hint for entry in package.crosswalk_entries})
    time_window_modes = sorted(
        {entry.time_window.mode for entry in package.crosswalk_entries},
        key=lambda item: item.value,
    )
    mediums = sorted({entry.medium for entry in package.crosswalk_entries}, key=lambda item: item.value)
    compartments = sorted(
        {entry.compartment for entry in package.crosswalk_entries},
        key=lambda item: item.value,
    )
    downstream_fields = sorted({entry.downstream_field for entry in package.crosswalk_entries})
    if len(downstream_fields) != 1:
        raise FateValidationError(
            code="regulatory_handoff_package_downstream_field_mismatch",
            message=(
                f"Regulatory handoff package contains multiple downstream fields {downstream_fields} "
                f"for profile {handoff_profile.profile_id}."
            ),
            suggestion="Rebuild the package so all crosswalk entries use one governed downstream field.",
            details={"downstreamFields": downstream_fields},
        )
    downstream_field = downstream_fields[0]
    parameter_quality_lines = _parameter_quality_lines(package.parameter_manifest)
    applicability_lines = []
    if package.parameter_manifest is not None:
        applicability_profile = _resolve_model_family_applicability(
            package.source_model_family,
            provenance_builder.defaults_registry,
        )
        applicability_lines = _applicability_lines(
            applicability_profile,
            package.parameter_manifest.fit_for_purpose,
        )

    entry_samples = [
        RegulatoryHandoffEntrySummary(
            source_surface_id=entry.source_surface_id,
            medium=entry.medium,
            compartment=entry.compartment,
            concentration_value=entry.concentration_value,
            concentration_unit=entry.concentration_unit,
            downstream_field=entry.downstream_field,
            route_hint=entry.route_hint,
            time_window_mode=entry.time_window.mode,
            equation_id=entry.equation_id,
            equation_text=entry.equation_text,
        )
        for entry in package.crosswalk_entries[: request.max_entry_samples]
    ]
    equation_lines = sorted(
        {
            f"{entry.compartment.value}: {entry.equation_id} -> {entry.equation_text}"
            for entry in package.crosswalk_entries
            if entry.equation_id and entry.equation_text
        }
    )
    summary_lines = [
        handoff_profile.response_summary_template
        or "Preserve the governed handoff fields unchanged for downstream consumers.",
        (
            f"Target module {handoff_profile.target_module} receives {len(package.crosswalk_entries)} "
            f"crosswalk entries via governed profile {handoff_profile.profile_id}."
        ),
        (
            f"Downstream field {downstream_field} carries media concentrations for "
            f"{', '.join(item.value for item in compartments)}."
        ),
        f"Route hints present: {', '.join(route_hints)}.",
        "Time semantics present: " + ", ".join(item.value for item in time_window_modes) + ".",
    ]
    if package.limitations:
        summary_lines.append(
            "Limitations: " + "; ".join(note.message for note in package.limitations)
        )

    return RegulatoryHandoffPackageSummary(
        package_id=package.package_id,
        scenario_id=package.scenario_id,
        handoff_profile_id=package.handoff_profile_id,
        target_module=handoff_profile.target_module,
        entry_count=len(package.crosswalk_entries),
        downstream_field=downstream_field,
        time_window_modes=time_window_modes,
        route_hints=route_hints,
        mediums=mediums,
        compartments=compartments,
        requires_dose_translation=all(
            entry.requires_dose_translation for entry in package.crosswalk_entries
        ),
        summary_template_used=handoff_profile.response_summary_template,
        summary_lines=summary_lines,
        entry_samples=entry_samples,
        parameter_quality_lines=parameter_quality_lines,
        applicability_lines=applicability_lines,
        equation_lines=equation_lines,
        limitations=package.limitations,
        blockers=package.blockers,
    )



def build_regulatory_handoff_review_packet(
    request: BuildRegulatoryHandoffReviewPacketRequest,
    provenance_builder: ProvenanceBuilder,
) -> RegulatoryHandoffReviewPacket:
    if request.handoff_profile_id or request.consumer_name:
        resolution_preview = preview_regulatory_handoff_resolution(
            PreviewRegulatoryHandoffResolutionRequest(
                handoff_profile_id=request.handoff_profile_id,
                consumer_name=request.consumer_name,
                target_modules=request.target_modules,
            ),
            provenance_builder,
        )
    else:
        resolution_preview = _default_regulatory_handoff_resolution_preview(
            provenance_builder.defaults_registry,
            request.target_modules,
        )

    if resolution_preview.status != "resolved" or resolution_preview.resolved_profile_id is None:
        raise FateValidationError(
            code="regulatory_handoff_review_resolution_unresolved",
            message="Regulatory handoff review packet could not be built because selector resolution did not resolve cleanly.",
            suggestion="Use fate_preview_regulatory_handoff_resolution to fix selector or target-module mismatches before building the review packet.",
            details={
                "previewStatus": resolution_preview.status,
                "issues": resolution_preview.issues,
            },
        )

    package = export_regulatory_handoff_package(
        ExportRegulatoryHandoffPackageRequest(
            result=request.result,
            scenario=request.scenario,
            handoff_profile_id=request.handoff_profile_id,
            consumer_name=request.consumer_name,
            target_modules=request.target_modules,
        ),
        provenance_builder,
    )
    summary = summarize_regulatory_handoff_package(
        SummarizeRegulatoryHandoffPackageRequest(
            package=package,
            max_entry_samples=request.max_entry_samples,
        ),
        provenance_builder,
    )
    handoff_profile = provenance_builder.defaults_registry.regulatory_handoff_profile(
        package.handoff_profile_id
    )
    if handoff_profile is None:
        raise FateValidationError(
            code="unknown_regulatory_handoff_profile",
            message=f"Unknown regulatory handoff profile: {package.handoff_profile_id}.",
            suggestion="Use a review packet generated from a declared governed handoff profile.",
        )

    concentration_only_declared = any(
        note.code == "concentration_only" for note in package.limitations
    )
    checks = [
        RegulatoryHandoffReviewCheck(
            code="resolution_preview_resolved",
            passed=True,
            message=(
                f"Selector set resolved to governed profile {resolution_preview.resolved_profile_id} "
                f"for target module {resolution_preview.target_module}."
            ),
        ),
        RegulatoryHandoffReviewCheck(
            code="package_profile_matches_preview",
            passed=resolution_preview.resolved_profile_id == package.handoff_profile_id,
            message=(
                f"Exported package profile {package.handoff_profile_id} matches preview resolution "
                f"{resolution_preview.resolved_profile_id}."
            ),
        ),
        RegulatoryHandoffReviewCheck(
            code="target_module_consistent",
            passed=(
                resolution_preview.target_module == summary.target_module
                and package.target_modules == [summary.target_module]
            ),
            message=(
                f"Governed target module {summary.target_module} is consistent across preview, "
                "package, and summary."
            ),
        ),
        RegulatoryHandoffReviewCheck(
            code="summary_matches_package",
            passed=(
                summary.package_id == package.package_id
                and summary.entry_count == len(package.crosswalk_entries)
                and summary.downstream_field == resolution_preview.downstream_field
            ),
            message=(
                f"Summary covers {summary.entry_count} crosswalk entries for downstream field "
                f"{summary.downstream_field} from package {package.package_id}."
            ),
        ),
        RegulatoryHandoffReviewCheck(
            code="concentration_boundary_preserved",
            passed=summary.requires_dose_translation and concentration_only_declared,
            message=(
                "Review packet preserves the concentration-only boundary and keeps dose translation "
                "explicitly downstream."
            ),
        ),
        RegulatoryHandoffReviewCheck(
            code="no_handoff_blockers",
            passed=not bool(package.blockers),
            message=(
                "No blockers were identified during handoff package export."
                if not package.blockers
                else "Handoff package export reported blockers: " + "; ".join(package.blockers)
            ),
        ),
    ]
    review_checklist = _build_regulatory_review_checklist(
        handoff_profile,
        resolution_preview,
        package,
        summary,
    )
    review_status = (
        "ready_for_assessor_review"
        if all(item.passed for item in checks)
        else "review_blocked"
    )
    return RegulatoryHandoffReviewPacket(
        scenario_id=package.scenario_id,
        handoff_profile_id=package.handoff_profile_id,
        target_module=summary.target_module,
        source_model_family=package.source_model_family,
        review_status=review_status,
        resolution_preview=resolution_preview,
        package=package,
        summary=summary,
        checks=checks,
        review_checklist=review_checklist,
        parameter_quality_lines=summary.parameter_quality_lines,
        applicability_lines=summary.applicability_lines,
        uncertainty_lines=_uncertainty_lines(package.uncertainty_summary),
        equation_lines=summary.equation_lines,
        review_template_used=handoff_profile.review_brief_template,
        provenance=provenance_builder.bundle(),
        limitations=package.limitations,
        blockers=package.blockers,
    )



def build_regulatory_handoff_review_brief(
    request: BuildRegulatoryHandoffReviewBriefRequest,
    provenance_builder: ProvenanceBuilder,
) -> RegulatoryHandoffReviewBrief:
    review_packet = request.review_packet
    handoff_profile = provenance_builder.defaults_registry.regulatory_handoff_profile(
        review_packet.handoff_profile_id
    )
    if handoff_profile is None:
        raise FateValidationError(
            code="unknown_regulatory_handoff_profile",
            message=f"Unknown regulatory handoff profile: {review_packet.handoff_profile_id}.",
            suggestion="Build the review brief from a review packet tied to a declared governed profile.",
        )
    if review_packet.target_module != handoff_profile.target_module:
        raise FateValidationError(
            code="regulatory_handoff_review_packet_target_mismatch",
            message=(
                f"Review packet target module {review_packet.target_module} does not match governed "
                f"target module {handoff_profile.target_module} for profile {handoff_profile.profile_id}."
            ),
            suggestion="Rebuild the review packet from the governed handoff profile before rendering a brief.",
        )
    passed_check_count = sum(1 for item in review_packet.checks if item.passed)
    brief_lines = [
        handoff_profile.review_brief_template
        or "Build a concise review brief that preserves the governed concentration-only handoff boundary.",
        (
            f"Review status {review_packet.review_status} for target module {review_packet.target_module} "
            f"under profile {review_packet.handoff_profile_id}."
        ),
        f"Technical checks: {passed_check_count}/{len(review_packet.checks)} passed.",
    ]
    for item in review_packet.review_checklist:
        brief_lines.append(f"[{item.status}] {item.prompt}")
        if item.evidence_lines:
            brief_lines.append("Evidence: " + " | ".join(item.evidence_lines))
    for line in review_packet.parameter_quality_lines:
        brief_lines.append("Parameter quality: " + line)
    for line in review_packet.applicability_lines:
        brief_lines.append("Applicability: " + line)
    for line in review_packet.uncertainty_lines:
        brief_lines.append("Uncertainty: " + line)
    for line in review_packet.equation_lines:
        brief_lines.append("Equation trace: " + line)
    if review_packet.limitations:
        brief_lines.append(
            "Limitations: " + "; ".join(note.message for note in review_packet.limitations)
        )
    return RegulatoryHandoffReviewBrief(
        review_packet_id=review_packet.review_packet_id,
        scenario_id=review_packet.scenario_id,
        handoff_profile_id=review_packet.handoff_profile_id,
        target_module=review_packet.target_module,
        review_status=review_packet.review_status,
        passed_check_count=passed_check_count,
        total_check_count=len(review_packet.checks),
        review_template_used=handoff_profile.review_brief_template,
        checklist_items=review_packet.review_checklist,
        brief_lines=brief_lines,
        parameter_quality_lines=review_packet.parameter_quality_lines,
        applicability_lines=review_packet.applicability_lines,
        uncertainty_lines=review_packet.uncertainty_lines,
        equation_lines=review_packet.equation_lines,
        limitations=review_packet.limitations,
    )
