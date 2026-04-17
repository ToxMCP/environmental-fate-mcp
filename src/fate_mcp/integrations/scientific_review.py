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


from .common import SCIENTIFIC_REVIEW_EVIDENCE_FIELDS, _benchmark_reference_lines, _collect_source_references, _ensure_scenario_matches_result, _fit_for_purpose_from_result, _resolve_scientific_review_profile
from .core import assess_release_scenario_fit, build_run_parameter_manifest, build_run_uncertainty_summary
from .surface_analysis import _equation_component_lines_from_surfaces, _equation_lines_from_surfaces, _loss_dominance_lines_from_surfaces, _loss_transition_lines_from_surfaces, _mass_balance_component_lines_from_surfaces, _post_release_directionality_lines_from_surfaces, _post_release_pace_directionality_lines_from_surfaces, _post_release_pace_lines_from_surfaces, _post_release_recovery_lines_from_surfaces, _post_release_regime_lines_from_surfaces, _transport_regime_lines_from_surfaces

def _scientific_review_evidence_line(
    field_name: str,
    review_packet: ScientificReviewPacket,
) -> str | None:
    if field_name == "fit_verdict":
        return (
            f"Fit verdict: {review_packet.fit_assessment.verdict} "
            f"(score={review_packet.fit_assessment.fit_score:.2f})."
        )
    if field_name == "applicability_lines" and review_packet.fit_assessment.applicability_lines:
        return "Applicability: " + " | ".join(review_packet.fit_assessment.applicability_lines)
    if field_name == "parameter_quality_lines" and review_packet.parameter_manifest.summary_lines:
        return "Parameter quality: " + " | ".join(review_packet.parameter_manifest.summary_lines)
    if field_name == "uncertainty_lines" and review_packet.uncertainty_summary.summary_lines:
        return "Uncertainty: " + " | ".join(review_packet.uncertainty_summary.summary_lines)
    if field_name == "benchmark_reference_lines" and review_packet.benchmark_reference_lines:
        return "Benchmark context: " + " | ".join(review_packet.benchmark_reference_lines)
    if field_name == "equation_lines" and review_packet.equation_lines:
        return "Equation trace: " + " | ".join(review_packet.equation_lines)
    if field_name == "surface_samples" and review_packet.surface_samples:
        first_surface = review_packet.surface_samples[0]
        return (
            f"Surface sample: {first_surface.medium.value}/{first_surface.compartment.value} "
            f"{first_surface.concentration_value:.6g} {first_surface.concentration_unit}."
        )
    if field_name == "limitations" and review_packet.limitations:
        return "Limitations: " + "; ".join(note.message for note in review_packet.limitations)
    if field_name == "model_family":
        return f"Model family: {review_packet.model_family.value}."
    if field_name == "fit_for_purpose":
        return f"Fit-for-purpose: {review_packet.fit_for_purpose.value}."
    return None



def _build_scientific_review_checklist(
    review_profile: ScientificReviewProfile,
    review_packet: ScientificReviewPacket,
) -> list[ScientificReviewChecklistItem]:
    checklist_items: list[ScientificReviewChecklistItem] = []
    for template in review_profile.review_checklist:
        unknown_fields = sorted(
            field for field in template.evidence_hint_fields if field not in SCIENTIFIC_REVIEW_EVIDENCE_FIELDS
        )
        if unknown_fields:
            raise FateValidationError(
                code="invalid_scientific_review_checklist_field",
                message=(
                    f"Scientific review profile {review_profile.model_family.value} declares unknown "
                    f"checklist evidence fields: {unknown_fields}."
                ),
                suggestion="Limit review checklist evidence_hint_fields to fields exposed by the scientific review packet builder.",
                details={"unknownEvidenceHintFields": unknown_fields},
            )
        evidence_lines = []
        for field_name in template.evidence_hint_fields:
            line = _scientific_review_evidence_line(field_name, review_packet)
            if line and line not in evidence_lines:
                evidence_lines.append(line)
        checklist_items.append(
            ScientificReviewChecklistItem(
                code=template.code,
                prompt=template.prompt,
                rationale=template.rationale,
                status="ready_for_assessor_confirmation" if evidence_lines else "attention_required",
                evidence_lines=evidence_lines,
            )
        )
    return checklist_items



def _build_scientific_review_context(
    scenario,
    result: ConcentrationEstimationResult,
    provenance_builder: ProvenanceBuilder,
) -> tuple[
    ScientificReviewProfile,
    ReleaseScenarioFitAssessment,
    RunParameterManifest,
    RunUncertaintySummary,
]:
    _ensure_scenario_matches_result(scenario, result)
    review_profile = _resolve_scientific_review_profile(
        result.run_summary.model_family,
        provenance_builder.defaults_registry,
    )
    fit_assessment = assess_release_scenario_fit(
        scenario,
        FateModelRunOptions(
            run_mode=result.run_summary.run_mode,
            model_family=result.run_summary.model_family,
            region_profile_id=scenario.geographic_scope.region_id,
            fit_for_purpose=_fit_for_purpose_from_result(result),
        ),
        provenance_builder,
    )
    parameter_manifest = build_run_parameter_manifest(
        scenario,
        result,
        provenance_builder,
    )
    uncertainty_summary = build_run_uncertainty_summary(
        scenario,
        result,
        provenance_builder,
    )
    return review_profile, fit_assessment, parameter_manifest, uncertainty_summary



def _scientific_review_checks(
    scenario,
    result: ConcentrationEstimationResult,
    fit_assessment: ReleaseScenarioFitAssessment,
    parameter_manifest: RunParameterManifest,
    uncertainty_summary: RunUncertaintySummary,
    surface_sample_count: int,
) -> list[ScientificReviewCheck]:
    return [
        ScientificReviewCheck(
            code="scenario_result_match",
            passed=scenario.scenario_id == result.run_summary.scenario_id,
            message=(
                f"Scenario {scenario.scenario_id} matches result "
                f"{result.run_summary.scenario_id}."
            ),
        ),
        ScientificReviewCheck(
            code="applicability_profile_declared",
            passed=bool(fit_assessment.applicability_profile.required_inputs),
            message=(
                f"Governed applicability profile is declared for model family "
                f"{fit_assessment.model_family.value}."
            ),
        ),
        ScientificReviewCheck(
            code="parameter_manifest_populated",
            passed=bool(parameter_manifest.entries),
            message=(
                f"Run parameter manifest records {len(parameter_manifest.entries)} resolved parameters."
            ),
        ),
        ScientificReviewCheck(
            code="uncertainty_summary_populated",
            passed=bool(uncertainty_summary.summary_lines),
            message=(
                f"Deterministic uncertainty summary records {len(uncertainty_summary.top_drivers)} top drivers."
            ),
        ),
        ScientificReviewCheck(
            code="surface_samples_available",
            passed=surface_sample_count > 0,
            message=f"Scientific review packet includes {surface_sample_count} sampled concentration surfaces.",
        ),
    ]



def _scientific_review_outcome(
    review_profile: ScientificReviewProfile,
    fit_assessment: ReleaseScenarioFitAssessment,
    uncertainty_summary: RunUncertaintySummary,
    quality_flags: list[QualityFlag] | None = None,
) -> ScientificReviewOutcome:
    quality_flags = quality_flags or []
    if any(flag.severity == Severity.ERROR for flag in quality_flags):
        return ScientificReviewOutcome.ESCALATE_MODEL_REVIEW
    driver_types = {driver.driver_type for driver in uncertainty_summary.top_drivers}
    if fit_assessment.verdict in review_profile.escalation_fit_verdicts:
        return ScientificReviewOutcome.ESCALATE_MODEL_REVIEW
    if any(driver_type in review_profile.escalation_driver_types for driver_type in driver_types):
        return ScientificReviewOutcome.ESCALATE_MODEL_REVIEW
    if any(driver_type in review_profile.qualification_driver_types for driver_type in driver_types):
        return ScientificReviewOutcome.QUALIFIED_SCREENING_USE
    if (
        review_profile.warning_severity_promotes_qualification
        and any(driver.severity == Severity.WARNING for driver in uncertainty_summary.top_drivers)
    ):
        return ScientificReviewOutcome.QUALIFIED_SCREENING_USE
    return ScientificReviewOutcome.ACCEPTABLE_SCREENING_USE



def _scientific_review_outcome_lines(
    review_profile: ScientificReviewProfile,
    outcome: ScientificReviewOutcome,
    fit_assessment: ReleaseScenarioFitAssessment,
    uncertainty_summary: RunUncertaintySummary,
    quality_flags: list[QualityFlag] | None = None,
) -> tuple[list[str], list[str], list[str]]:
    if outcome == ScientificReviewOutcome.ACCEPTABLE_SCREENING_USE:
        template = review_profile.acceptable_outcome_template
    elif outcome == ScientificReviewOutcome.QUALIFIED_SCREENING_USE:
        template = review_profile.qualified_outcome_template
    else:
        template = review_profile.escalation_outcome_template

    outcome_lines = [
        template
        or "Scientific review outcome should be interpreted within the declared model-family scope."
    ]
    outcome_lines.append(
        f"Fit verdict {fit_assessment.verdict} with score {fit_assessment.fit_score:.2f} informed the outcome."
    )
    governing_rule_lines = []
    quality_flags = quality_flags or []
    error_flags = [flag for flag in quality_flags if flag.severity == Severity.ERROR]
    if error_flags:
        governing_rule_lines.append(
            "Escalation triggered because ERROR-quality flags are present: "
            + ", ".join(sorted(set(flag.code for flag in error_flags))) + "."
        )
    if fit_assessment.verdict in review_profile.escalation_fit_verdicts:
        governing_rule_lines.append(
            f"Escalation triggered because fit verdict {fit_assessment.verdict} is governed for escalation."
        )
    triggered_escalation_drivers = [
        driver.driver_type
        for driver in uncertainty_summary.top_drivers
        if driver.driver_type in review_profile.escalation_driver_types
    ]
    if triggered_escalation_drivers:
        governing_rule_lines.append(
            "Escalation driver types present: " + ", ".join(sorted(set(triggered_escalation_drivers))) + "."
        )
    triggered_qualification_drivers = [
        driver.driver_type
        for driver in uncertainty_summary.top_drivers
        if driver.driver_type in review_profile.qualification_driver_types
    ]
    if triggered_qualification_drivers:
        governing_rule_lines.append(
            "Qualification driver types present: " + ", ".join(sorted(set(triggered_qualification_drivers))) + "."
        )
    if (
        review_profile.warning_severity_promotes_qualification
        and any(driver.severity == Severity.WARNING for driver in uncertainty_summary.top_drivers)
    ):
        governing_rule_lines.append(
            "Warning-severity drivers promote qualification under the governed review profile."
        )
    recommended_actions: list[str] = []
    if outcome == ScientificReviewOutcome.ESCALATE_MODEL_REVIEW:
        recommended_actions.append(
            "Escalate the run for deeper model review or additional evidence before decision-facing reuse."
        )
    elif outcome == ScientificReviewOutcome.QUALIFIED_SCREENING_USE:
        recommended_actions.append(
            "Carry the qualification notes and limitation lines forward in assessor-facing summaries."
        )
    else:
        recommended_actions.append(
            "Use inside the declared screening scope and keep the limitation notes attached."
        )

    seen_actions = set(recommended_actions)
    for driver in uncertainty_summary.top_drivers:
        template = review_profile.driver_action_templates.get(driver.driver_type)
        if template and template not in seen_actions:
            recommended_actions.append(template)
            seen_actions.add(template)
    if fit_assessment.verdict != "good_fit":
        fallback = "Revisit model-family applicability and fit-for-purpose alignment before reuse."
        if fallback not in seen_actions:
            recommended_actions.append(fallback)
    return outcome_lines, recommended_actions, governing_rule_lines



def _scientific_review_status(
    review_profile: ScientificReviewProfile,
    fit_assessment: ReleaseScenarioFitAssessment,
    outcome: ScientificReviewOutcome,
    checks: list[ScientificReviewCheck],
) -> tuple[str, list[str], list[str]]:
    triggered_check_codes = [check.code for check in checks if not check.passed]
    status_rule_lines: list[str] = []
    requires_attention = False

    if review_profile.attention_if_any_checks_fail and triggered_check_codes:
        requires_attention = True
        status_rule_lines.append(
            "Attention required because governed packet checks failed: "
            + ", ".join(triggered_check_codes)
            + "."
        )
    if review_profile.ready_fit_verdicts and fit_assessment.verdict not in review_profile.ready_fit_verdicts:
        requires_attention = True
        status_rule_lines.append(
            f"Attention required because fit verdict {fit_assessment.verdict} is outside the governed ready set."
        )
    if outcome in review_profile.attention_outcomes:
        requires_attention = True
        status_rule_lines.append(
            f"Attention required because outcome {outcome.value} is governed as attention-worthy."
        )
    if not status_rule_lines:
        status_rule_lines.append(
            f"Ready because fit verdict {fit_assessment.verdict}, packet checks, and outcome {outcome.value} satisfy the governed status policy."
        )
    return (
        "scientific_review_attention_needed" if requires_attention else "ready_for_scientific_review",
        triggered_check_codes,
        status_rule_lines,
    )



def preview_scientific_review_outcome(
    request: PreviewScientificReviewOutcomeRequest,
    provenance_builder: ProvenanceBuilder,
) -> ScientificReviewOutcomePreview:
    review_profile, fit_assessment, parameter_manifest, uncertainty_summary = _build_scientific_review_context(
        request.scenario,
        request.result,
        provenance_builder,
    )
    all_quality_flags = list(request.scenario.quality_flags)
    for surface in request.result.surfaces:
        all_quality_flags.extend(surface.quality_flags)
    outcome = _scientific_review_outcome(
        review_profile,
        fit_assessment,
        uncertainty_summary,
        quality_flags=all_quality_flags,
    )
    outcome_lines, recommended_actions, governing_rule_lines = _scientific_review_outcome_lines(
        review_profile,
        outcome,
        fit_assessment,
        uncertainty_summary,
        quality_flags=all_quality_flags,
    )
    checks = _scientific_review_checks(
        request.scenario,
        request.result,
        fit_assessment,
        parameter_manifest,
        uncertainty_summary,
        len(request.result.surfaces),
    )
    review_status, triggered_check_codes, status_rule_lines = _scientific_review_status(
        review_profile,
        fit_assessment,
        outcome,
        checks,
    )
    return ScientificReviewOutcomePreview(
        scenario_id=request.scenario.scenario_id,
        run_id=request.result.run_summary.run_id,
        model_family=request.result.run_summary.model_family,
        fit_for_purpose=parameter_manifest.fit_for_purpose,
        review_profile_model_family=review_profile.model_family,
        review_outcome=outcome,
        review_status=review_status,
        triggered_fit_verdicts=[fit_assessment.verdict] if fit_assessment.verdict in review_profile.escalation_fit_verdicts else [],
        triggered_driver_types=[
            driver.driver_type
            for driver in uncertainty_summary.top_drivers
            if driver.driver_type in review_profile.escalation_driver_types
            or driver.driver_type in review_profile.qualification_driver_types
            or (
                review_profile.warning_severity_promotes_qualification
                and driver.severity == Severity.WARNING
            )
        ],
        triggered_check_codes=triggered_check_codes,
        governing_rule_lines=governing_rule_lines,
        status_rule_lines=status_rule_lines,
        outcome_lines=outcome_lines,
        recommended_actions=recommended_actions,
    )



def build_scientific_review_packet(
    request: BuildScientificReviewPacketRequest,
    provenance_builder: ProvenanceBuilder,
) -> ScientificReviewPacket:
    review_profile, fit_assessment, parameter_manifest, uncertainty_summary = _build_scientific_review_context(
        request.scenario,
        request.result,
        provenance_builder,
    )
    outcome_preview = preview_scientific_review_outcome(
        PreviewScientificReviewOutcomeRequest(
            scenario=request.scenario,
            result=request.result,
        ),
        provenance_builder,
    )
    surface_samples = [
        ScientificReviewSurfaceSummary(
            medium=surface.medium,
            compartment=surface.compartment,
            concentration_value=surface.concentration_value,
            concentration_unit=surface.concentration_unit,
            time_window_mode=surface.time_window.mode,
            bucket_label=surface.time_window.bucket_label,
            equation_id=surface.calculation_trace.equation_id if surface.calculation_trace else None,
            equation_text=surface.calculation_trace.equation_text if surface.calculation_trace else None,
        )
        for surface in request.result.surfaces[: request.max_surface_samples]
    ]
    equation_lines = _equation_lines_from_surfaces(request.result.surfaces)
    equation_component_lines = _equation_component_lines_from_surfaces(request.result.surfaces)
    mass_balance_component_lines = _mass_balance_component_lines_from_surfaces(request.result.surfaces)
    transport_regime_lines = _transport_regime_lines_from_surfaces(request.result.surfaces)
    post_release_recovery_lines = _post_release_recovery_lines_from_surfaces(request.result.surfaces)
    post_release_regime_lines = _post_release_regime_lines_from_surfaces(request.result.surfaces)
    post_release_directionality_lines = _post_release_directionality_lines_from_surfaces(
        request.result.surfaces
    )
    post_release_pace_lines = _post_release_pace_lines_from_surfaces(request.result.surfaces)
    post_release_pace_directionality_lines = _post_release_pace_directionality_lines_from_surfaces(
        request.result.surfaces
    )
    loss_dominance_lines = _loss_dominance_lines_from_surfaces(request.result.surfaces)
    loss_transition_lines = _loss_transition_lines_from_surfaces(request.result.surfaces)
    benchmark_lines = _benchmark_reference_lines(
        request.result.run_summary.model_family,
        request.result.run_summary.run_mode,
    )
    checks = _scientific_review_checks(
        request.scenario,
        request.result,
        fit_assessment,
        parameter_manifest,
        uncertainty_summary,
        len(surface_samples),
    )
    review_outcome = outcome_preview.review_outcome
    review_status = outcome_preview.review_status
    summary_lines = [
        review_profile.packet_template
        or "Build a scientific review packet that preserves model-family scope, parameter provenance, benchmark context, and deterministic uncertainty drivers.",
        (
            f"Scientific review packet covers run {request.result.run_summary.run_id} for model family "
            f"{request.result.run_summary.model_family.value}."
        ),
        f"Fit verdict: {fit_assessment.verdict} (score={fit_assessment.fit_score:.2f}).",
        (
            f"Parameter manifest exposes {len(parameter_manifest.entries)} resolved parameters and "
            f"{len(uncertainty_summary.top_drivers)} ranked uncertainty drivers."
        ),
    ]
    review_packet = ScientificReviewPacket(
        scenario_id=request.scenario.scenario_id,
        run_id=request.result.run_summary.run_id,
        model_family=request.result.run_summary.model_family,
        fit_for_purpose=parameter_manifest.fit_for_purpose,
        review_status=review_status,
        review_outcome=review_outcome,
        outcome_preview=outcome_preview,
        fit_assessment=fit_assessment,
        parameter_manifest=parameter_manifest,
        uncertainty_summary=uncertainty_summary,
        surface_samples=surface_samples,
        summary_lines=summary_lines,
        outcome_lines=outcome_preview.outcome_lines,
        recommended_actions=outcome_preview.recommended_actions,
        benchmark_reference_lines=benchmark_lines,
        equation_lines=equation_lines,
        equation_component_lines=equation_component_lines,
        mass_balance_component_lines=mass_balance_component_lines,
        transport_regime_lines=transport_regime_lines,
        post_release_recovery_lines=post_release_recovery_lines,
        post_release_regime_lines=post_release_regime_lines,
        post_release_directionality_lines=post_release_directionality_lines,
        post_release_pace_lines=post_release_pace_lines,
        post_release_pace_directionality_lines=post_release_pace_directionality_lines,
        loss_dominance_lines=loss_dominance_lines,
        loss_transition_lines=loss_transition_lines,
        checks=checks,
        review_template_used=review_profile.packet_template,
        provenance=provenance_builder.bundle(_collect_source_references(request.scenario, request.result)),
        limitations=[
            *request.result.surfaces[0].limitations[:1],
            *parameter_manifest.limitations,
            *uncertainty_summary.limitations,
        ],
    )
    review_packet.review_checklist = _build_scientific_review_checklist(review_profile, review_packet)
    return review_packet



def build_scientific_review_brief(
    request: BuildScientificReviewBriefRequest,
    provenance_builder: ProvenanceBuilder,
) -> ScientificReviewBrief:
    review_packet = request.review_packet
    review_profile = _resolve_scientific_review_profile(
        review_packet.model_family,
        provenance_builder.defaults_registry,
    )
    passed_check_count = sum(1 for check in review_packet.checks if check.passed)
    summary_lines = [
        review_profile.brief_template
        or "Summarize whether the run is scientifically reviewable within the declared Environmental Fate MCP boundary."
    ]
    summary_lines.extend(review_packet.summary_lines)
    summary_lines.extend(
        "Benchmark reference: " + line for line in review_packet.benchmark_reference_lines
    )
    summary_lines.extend("Equation trace: " + line for line in review_packet.equation_lines)
    summary_lines.extend(
        "Equation components: " + line for line in review_packet.equation_component_lines
    )
    summary_lines.extend(
        "Mass balance: " + line for line in review_packet.mass_balance_component_lines
    )
    summary_lines.extend(
        "Transport regime: " + line for line in review_packet.transport_regime_lines
    )
    summary_lines.extend(
        "Post-release recovery: " + line for line in review_packet.post_release_recovery_lines
    )
    summary_lines.extend(
        "Post-release regime: " + line for line in review_packet.post_release_regime_lines
    )
    summary_lines.extend(
        "Post-release directionality: " + line
        for line in review_packet.post_release_directionality_lines
    )
    summary_lines.extend(
        "Post-release pace: " + line for line in review_packet.post_release_pace_lines
    )
    summary_lines.extend(
        "Post-release pace directionality: " + line
        for line in review_packet.post_release_pace_directionality_lines
    )
    summary_lines.extend(
        "Loss dominance: " + line for line in review_packet.loss_dominance_lines
    )
    summary_lines.extend(
        "Loss transition: " + line for line in review_packet.loss_transition_lines
    )
    for item in review_packet.review_checklist:
        summary_lines.append(f"[{item.status}] {item.prompt}")
        if item.evidence_lines:
            summary_lines.append("Evidence: " + " | ".join(item.evidence_lines))
    return ScientificReviewBrief(
        review_packet_id=review_packet.review_packet_id,
        scenario_id=review_packet.scenario_id,
        run_id=review_packet.run_id,
        model_family=review_packet.model_family,
        fit_for_purpose=review_packet.fit_for_purpose,
        review_status=review_packet.review_status,
        review_outcome=review_packet.review_outcome,
        passed_check_count=passed_check_count,
        total_check_count=len(review_packet.checks),
        review_template_used=review_profile.brief_template,
        checklist_items=review_packet.review_checklist,
        summary_lines=summary_lines,
        outcome_lines=review_packet.outcome_lines,
        recommended_actions=review_packet.recommended_actions,
        parameter_quality_lines=review_packet.parameter_manifest.summary_lines,
        applicability_lines=review_packet.fit_assessment.applicability_lines,
        uncertainty_lines=review_packet.uncertainty_summary.summary_lines,
        benchmark_reference_lines=review_packet.benchmark_reference_lines,
        equation_lines=review_packet.equation_lines,
        equation_component_lines=review_packet.equation_component_lines,
        mass_balance_component_lines=review_packet.mass_balance_component_lines,
        transport_regime_lines=review_packet.transport_regime_lines,
        post_release_recovery_lines=review_packet.post_release_recovery_lines,
        post_release_regime_lines=review_packet.post_release_regime_lines,
        post_release_directionality_lines=review_packet.post_release_directionality_lines,
        post_release_pace_lines=review_packet.post_release_pace_lines,
        post_release_pace_directionality_lines=review_packet.post_release_pace_directionality_lines,
        loss_dominance_lines=review_packet.loss_dominance_lines,
        loss_transition_lines=review_packet.loss_transition_lines,
        limitations=review_packet.limitations,
    )


