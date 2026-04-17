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


from .common import MODEL_FAMILY_CHALLENGE_REVIEW_EVIDENCE_FIELDS, MODEL_FAMILY_COMPARISON_REVIEW_EVIDENCE_FIELDS, MODEL_FAMILY_SELECTION_REVIEW_EVIDENCE_FIELDS, _benchmark_reference_lines, _collect_source_references, _merge_limitations, _merge_source_references, _selection_recommendation_unsuitability_lines
from .core import assess_release_scenario_fit, compare_fate_scenarios
from .scientific_review import build_scientific_review_brief, build_scientific_review_packet
from .surface_analysis import _equation_lines_from_surfaces, _surface_samples_from_result

def _resolve_model_family_comparison_profile(
    request: BuildModelFamilyComparisonPacketRequest,
    defaults_registry: DefaultsRegistry,
) -> ModelFamilyComparisonProfile:
    if request.comparison_profile_id:
        profile = defaults_registry.model_family_comparison_profile(request.comparison_profile_id)
        if profile is None:
            raise FateValidationError(
                code="unknown_model_family_comparison_profile",
                message=(
                    f"No governed model-family comparison profile is declared for "
                    f"{request.comparison_profile_id}."
                ),
                suggestion="Inspect defaults://model-family-comparison-profiles and use a declared profile id.",
            )
        if (
            profile.base_model_family != request.base_model_family
            or profile.candidate_model_family != request.candidate_model_family
        ):
            raise FateValidationError(
                code="model_family_comparison_profile_mismatch",
                message=(
                    f"Comparison profile {profile.profile_id} does not match the requested "
                    f"model-family pair {request.base_model_family.value} -> "
                    f"{request.candidate_model_family.value}."
                ),
                suggestion="Choose a comparison profile that matches the requested base/candidate family pair.",
                details={
                    "profileId": profile.profile_id,
                    "profileBaseModelFamily": profile.base_model_family.value,
                    "profileCandidateModelFamily": profile.candidate_model_family.value,
                    "requestedBaseModelFamily": request.base_model_family.value,
                    "requestedCandidateModelFamily": request.candidate_model_family.value,
                },
            )
    else:
        profile = defaults_registry.resolve_model_family_comparison_profile(
            request.base_model_family,
            request.candidate_model_family,
        )
        if profile is None:
            raise FateValidationError(
                code="missing_model_family_comparison_profile",
                message=(
                    f"No governed model-family comparison profile is declared for "
                    f"{request.base_model_family.value} -> {request.candidate_model_family.value}."
                ),
                suggestion="Declare the model-family pair in defaults/v1/model_family_comparison_profiles.json.",
            )
    if request.fit_for_purpose not in profile.fit_for_purpose:
        raise FateValidationError(
            code="model_family_comparison_fit_for_purpose_unsupported",
            message=(
                f"Comparison profile {profile.profile_id} does not support fit_for_purpose "
                f"{request.fit_for_purpose.value}."
            ),
            suggestion="Choose a compatible comparison profile or a supported fit-for-purpose value.",
        )
    if request.run_mode not in profile.supported_run_modes:
        raise FateValidationError(
            code="model_family_comparison_run_mode_unsupported",
            message=(
                f"Comparison profile {profile.profile_id} does not support run_mode "
                f"{request.run_mode.value}."
            ),
            suggestion="Choose a compatible comparison profile or a supported run mode.",
        )
    return profile



def _resolve_model_family_selection_profile(
    request: RecommendModelFamilySelectionRequest,
    defaults_registry: DefaultsRegistry,
) -> ModelFamilySelectionProfile:
    if request.selection_profile_id:
        profile = defaults_registry.model_family_selection_profile(request.selection_profile_id)
        if profile is None:
            raise FateValidationError(
                code="unknown_model_family_selection_profile",
                message=(
                    f"No governed model-family selection profile is declared for "
                    f"{request.selection_profile_id}."
                ),
                suggestion="Inspect defaults://model-family-selection-profiles and use a declared profile id.",
            )
    else:
        profiles = defaults_registry.list_model_family_selection_profiles()
        if len(profiles) != 1:
            raise FateValidationError(
                code="ambiguous_model_family_selection_profile",
                message="No model-family selection profile id was provided and the defaults registry is not singular.",
                suggestion="Specify selection_profile_id explicitly.",
            )
        profile = profiles[0]
    if request.fit_for_purpose not in profile.fit_for_purpose:
        raise FateValidationError(
            code="model_family_selection_fit_for_purpose_unsupported",
            message=(
                f"Selection profile {profile.profile_id} does not support fit_for_purpose "
                f"{request.fit_for_purpose.value}."
            ),
            suggestion="Choose a compatible selection profile or a supported fit-for-purpose value.",
        )
    if request.run_mode not in profile.supported_run_modes:
        raise FateValidationError(
            code="model_family_selection_run_mode_unsupported",
            message=(
                f"Selection profile {profile.profile_id} does not support run_mode "
                f"{request.run_mode.value}."
            ),
            suggestion="Choose a compatible selection profile or a supported run mode.",
        )
    comparison_profile = defaults_registry.model_family_comparison_profile(profile.comparison_profile_id)
    if comparison_profile is None:
        raise FateValidationError(
            code="model_family_selection_missing_comparison_profile",
            message=(
                f"Selection profile {profile.profile_id} references missing comparison profile "
                f"{profile.comparison_profile_id}."
            ),
            suggestion="Declare the referenced comparison profile or correct comparison_profile_id in the selection profile.",
        )
    return profile



def recommend_model_family_selection(
    request: RecommendModelFamilySelectionRequest,
    provenance_builder: ProvenanceBuilder,
) -> ModelFamilySelectionRecommendation:
    defaults_registry = provenance_builder.defaults_registry
    selection_profile = _resolve_model_family_selection_profile(request, defaults_registry)

    primary_run_options = FateModelRunOptions(
        run_mode=request.run_mode,
        model_family=selection_profile.default_model_family,
        region_profile_id=request.scenario.geographic_scope.region_id,
        fit_for_purpose=request.fit_for_purpose,
    )
    challenge_run_options = FateModelRunOptions(
        run_mode=request.run_mode,
        model_family=selection_profile.challenge_model_family,
        region_profile_id=request.scenario.geographic_scope.region_id,
        fit_for_purpose=request.fit_for_purpose,
    )
    primary_fit_assessment = assess_release_scenario_fit(
        request.scenario,
        primary_run_options,
        provenance_builder,
    )
    challenge_fit_assessment = assess_release_scenario_fit(
        request.scenario,
        challenge_run_options,
        provenance_builder,
    )

    triggered_parameters = sorted(
        {
            record.parameter
            for record in request.scenario.parameter_records
            if record.parameter in selection_profile.trigger_parameter_names
        }
    )
    triggered_signal_lines: list[str] = []
    if triggered_parameters:
        triggered_signal_lines.append(
            "Explicit residence-time-sensitive parameters supplied: " + ", ".join(triggered_parameters) + "."
        )
    if request.scenario.duration_days >= selection_profile.minimum_duration_days_for_challenge:
        triggered_signal_lines.append(
            f"Scenario duration {request.scenario.duration_days:.6g} day meets or exceeds the governed challenge threshold of "
            f"{selection_profile.minimum_duration_days_for_challenge:.6g} day."
        )

    summary_lines = [
        (
            f"Model-family selection profile {selection_profile.display_name} "
            f"({selection_profile.profile_id}) was evaluated for scenario {request.scenario.scenario_id}."
        ),
        f"Primary baseline family: {selection_profile.default_model_family.value}.",
        f"Challenge family: {selection_profile.challenge_model_family.value}.",
        f"Primary fit verdict: {primary_fit_assessment.verdict} (score={primary_fit_assessment.fit_score:.2f}).",
        f"Challenge fit verdict: {challenge_fit_assessment.verdict} (score={challenge_fit_assessment.fit_score:.2f}).",
    ]
    if selection_profile.applicability_note:
        summary_lines.append(selection_profile.applicability_note)

    recommended_actions: list[str] = []
    limitations = [
        LimitationNote(
            code="model_family_selection_guidance",
            message=(
                "Model-family selection recommendations are workflow-selection guidance inside the Environmental Fate MCP boundary "
                "and do not by themselves prove scientific superiority of one family."
            ),
        )
    ]

    if primary_fit_assessment.verdict != "good_fit":
        recommendation_status = ModelFamilySelectionStatus.REVIEW_NEEDED
        recommendation_template = (
            selection_profile.review_needed_template
            or "Do not recommend a model-family path until baseline fit issues are resolved."
        )
        recommended_actions.append(
            "Resolve baseline applicability or fit issues before using any model-family selection recommendation in assessor-facing workflows."
        )
        challenge_model_family = None
        comparison_profile_id = None
        challenge_fit_assessment_payload = challenge_fit_assessment
    elif challenge_fit_assessment.verdict == "good_fit" and triggered_signal_lines:
        recommendation_status = ModelFamilySelectionStatus.DEFAULT_WITH_EXPERIMENTAL_CHALLENGE
        recommendation_template = (
            selection_profile.challenge_recommendation_template
            or "Keep the default family as baseline and run the governed experimental challenge path."
        )
        recommended_actions.append(
            f"Use {selection_profile.default_model_family.value} as the baseline run and compare it against "
            f"{selection_profile.challenge_model_family.value} using comparison profile "
            f"{selection_profile.comparison_profile_id}."
        )
        challenge_model_family = selection_profile.challenge_model_family
        comparison_profile_id = selection_profile.comparison_profile_id
        challenge_fit_assessment_payload = challenge_fit_assessment
    else:
        recommendation_status = ModelFamilySelectionStatus.DEFAULT_BASELINE_ONLY
        recommendation_template = (
            selection_profile.default_recommendation_template
            or "Keep the default model family as the screening baseline for this scenario."
        )
        if challenge_fit_assessment.verdict != "good_fit":
            recommended_actions.append(
                f"Do not recommend the challenge family because its fit verdict is {challenge_fit_assessment.verdict}."
            )
        else:
            recommended_actions.append(
                "No governed duration or explicit residence-time trigger was present, so the experimental challenge path is optional rather than recommended."
            )
        challenge_model_family = None
        comparison_profile_id = None
        challenge_fit_assessment_payload = challenge_fit_assessment

    if not triggered_signal_lines:
        triggered_signal_lines.append(
            "No explicit residence-time override or governed duration trigger was present."
        )
    if (
        challenge_model_family is not None
        and challenge_model_family.value in EXPERIMENTAL_MODEL_FAMILIES
    ):
        limitations.append(
            LimitationNote(
                code="experimental_challenge_model_family",
                message=(
                    f"Challenge model family {challenge_model_family.value} is published as experimental "
                    "and should be treated as a governed challenge path rather than a default release baseline."
                ),
            )
        )
    recommended_actions.extend(
        note for note in selection_profile.review_notes if note not in recommended_actions
    )
    summary_lines.append(recommendation_template)
    summary_lines.extend(triggered_signal_lines)

    return ModelFamilySelectionRecommendation(
        scenario_id=request.scenario.scenario_id,
        run_mode=request.run_mode,
        fit_for_purpose=request.fit_for_purpose,
        selection_profile_id=selection_profile.profile_id,
        recommendation_status=recommendation_status,
        primary_model_family=selection_profile.default_model_family,
        challenge_model_family=challenge_model_family,
        comparison_profile_id=comparison_profile_id,
        primary_fit_assessment=primary_fit_assessment,
        challenge_fit_assessment=challenge_fit_assessment_payload,
        triggered_parameters=triggered_parameters,
        triggered_signal_lines=triggered_signal_lines,
        summary_lines=summary_lines,
        recommended_actions=recommended_actions,
        recommendation_template_used=recommendation_template,
        provenance=provenance_builder.bundle(_collect_source_references(request.scenario)),
        limitations=limitations,
    )



def _resolve_model_family_selection_profile_from_recommendation(
    recommendation: ModelFamilySelectionRecommendation,
    defaults_registry: DefaultsRegistry,
) -> ModelFamilySelectionProfile:
    profile = defaults_registry.model_family_selection_profile(recommendation.selection_profile_id)
    if profile is None:
        raise FateValidationError(
            code="unknown_model_family_selection_profile",
            message=(
                f"No governed model-family selection profile is declared for "
                f"{recommendation.selection_profile_id}."
            ),
            suggestion="Inspect defaults://model-family-selection-profiles and use a declared profile id.",
        )
    if profile.default_model_family != recommendation.primary_model_family:
        raise FateValidationError(
            code="model_family_selection_profile_primary_mismatch",
            message=(
                f"Selection recommendation for scenario {recommendation.scenario_id} does not match governed "
                f"primary model family {profile.default_model_family.value}."
            ),
            suggestion="Rebuild the selection recommendation with a profile that matches the primary model family.",
        )
    if recommendation.challenge_model_family and profile.challenge_model_family != recommendation.challenge_model_family:
        raise FateValidationError(
            code="model_family_selection_profile_challenge_mismatch",
            message=(
                f"Selection recommendation for scenario {recommendation.scenario_id} does not match governed "
                f"challenge model family {profile.challenge_model_family.value}."
            ),
            suggestion="Rebuild the selection recommendation with a profile that matches the challenge model family.",
        )
    if recommendation.comparison_profile_id and recommendation.comparison_profile_id != profile.comparison_profile_id:
        raise FateValidationError(
            code="model_family_selection_profile_comparison_mismatch",
            message=(
                f"Selection recommendation for scenario {recommendation.scenario_id} does not match governed "
                f"comparison profile {profile.comparison_profile_id}."
            ),
            suggestion="Rebuild the selection recommendation with a profile that matches the governed comparison profile.",
        )
    return profile



def _model_family_selection_review_evidence_line(
    field_name: str,
    review_packet: ModelFamilySelectionReviewPacket,
) -> str | None:
    recommendation = review_packet.selection_recommendation
    if field_name == "recommendation_status":
        return f"Recommendation status: {recommendation.recommendation_status.value}."
    if field_name == "comparison_profile_id":
        if recommendation.comparison_profile_id:
            return f"Governed comparison profile: {recommendation.comparison_profile_id}."
        return "No governed comparison profile is attached because the recommendation keeps the baseline only."
    if field_name == "triggered_signal_lines" and review_packet.triggered_signal_lines:
        return "Trigger signals: " + " | ".join(review_packet.triggered_signal_lines)
    if field_name == "primary_fit_verdict":
        return (
            f"Primary fit verdict: {recommendation.primary_fit_assessment.verdict} "
            f"(score={recommendation.primary_fit_assessment.fit_score:.2f})."
        )
    if field_name == "challenge_fit_verdict" and recommendation.challenge_fit_assessment is not None:
        return (
            f"Challenge fit verdict: {recommendation.challenge_fit_assessment.verdict} "
            f"(score={recommendation.challenge_fit_assessment.fit_score:.2f})."
        )
    if field_name == "primary_applicability_lines" and review_packet.primary_applicability_lines:
        return "Primary applicability: " + " | ".join(review_packet.primary_applicability_lines)
    if field_name == "challenge_applicability_lines" and review_packet.challenge_applicability_lines:
        return "Challenge applicability: " + " | ".join(review_packet.challenge_applicability_lines)
    if field_name == "limitations" and review_packet.limitations:
        return "Limitations: " + "; ".join(note.message for note in review_packet.limitations)
    if field_name == "run_mode":
        return f"Run mode: {recommendation.run_mode.value}."
    if field_name == "fit_for_purpose":
        return f"Fit-for-purpose: {recommendation.fit_for_purpose.value}."
    return None



def _build_model_family_selection_review_checklist(
    selection_profile: ModelFamilySelectionProfile,
    review_packet: ModelFamilySelectionReviewPacket,
) -> list[ModelFamilySelectionReviewChecklistItem]:
    checklist_items: list[ModelFamilySelectionReviewChecklistItem] = []
    for template in selection_profile.review_checklist:
        unknown_fields = sorted(
            field
            for field in template.evidence_hint_fields
            if field not in MODEL_FAMILY_SELECTION_REVIEW_EVIDENCE_FIELDS
        )
        if unknown_fields:
            raise FateValidationError(
                code="invalid_model_family_selection_review_checklist_field",
                message=(
                    f"Selection profile {selection_profile.profile_id} declares unknown "
                    f"review checklist evidence fields: {unknown_fields}."
                ),
                suggestion="Limit review checklist evidence_hint_fields to fields exposed by the selection review packet builder.",
                details={"unknownEvidenceHintFields": unknown_fields},
            )
        evidence_lines = []
        for field_name in template.evidence_hint_fields:
            line = _model_family_selection_review_evidence_line(field_name, review_packet)
            if line and line not in evidence_lines:
                evidence_lines.append(line)
        checklist_items.append(
            ModelFamilySelectionReviewChecklistItem(
                code=template.code,
                prompt=template.prompt,
                rationale=template.rationale,
                status="ready_for_assessor_confirmation" if evidence_lines else "attention_required",
                evidence_lines=evidence_lines,
            )
        )
    return checklist_items



def _model_family_selection_review_checks(
    recommendation: ModelFamilySelectionRecommendation,
) -> list[ModelFamilySelectionReviewCheck]:
    challenge_is_experimental = bool(
        recommendation.challenge_model_family
        and recommendation.challenge_model_family.value in EXPERIMENTAL_MODEL_FAMILIES
    )
    challenge_disclosed = any(
        note.code == "experimental_challenge_model_family" for note in recommendation.limitations
    )
    challenge_fit_matches = (
        recommendation.challenge_model_family is None
        or (
            recommendation.challenge_fit_assessment is not None
            and recommendation.challenge_fit_assessment.model_family == recommendation.challenge_model_family
        )
    )
    comparison_profile_declared = (
        recommendation.recommendation_status != ModelFamilySelectionStatus.DEFAULT_WITH_EXPERIMENTAL_CHALLENGE
        or bool(recommendation.comparison_profile_id)
    )
    return [
        ModelFamilySelectionReviewCheck(
            code="selection_profile_declared",
            passed=bool(recommendation.selection_profile_id),
            message=f"Governed selection profile {recommendation.selection_profile_id} is recorded on the recommendation.",
        ),
        ModelFamilySelectionReviewCheck(
            code="primary_fit_matches_primary_family",
            passed=recommendation.primary_fit_assessment.model_family == recommendation.primary_model_family,
            message="Primary fit assessment matches the declared baseline model family.",
        ),
        ModelFamilySelectionReviewCheck(
            code="challenge_fit_matches_challenge_family",
            passed=challenge_fit_matches,
            message=(
                "Challenge fit assessment matches the declared challenge model family."
                if recommendation.challenge_model_family is not None
                else "No challenge model family is attached to this recommendation."
            ),
        ),
        ModelFamilySelectionReviewCheck(
            code="trigger_signals_recorded",
            passed=bool(recommendation.triggered_signal_lines),
            message="Trigger-signal lines are recorded for assessor-facing selection review.",
        ),
        ModelFamilySelectionReviewCheck(
            code="comparison_profile_declared_when_challenge_recommended",
            passed=comparison_profile_declared,
            message=(
                "A governed comparison profile is recorded when the recommendation includes an experimental challenge path."
            ),
        ),
        ModelFamilySelectionReviewCheck(
            code="experimental_challenge_disclosed",
            passed=(not challenge_is_experimental) or challenge_disclosed,
            message=(
                "Experimental challenge-model-family status is explicitly disclosed."
                if challenge_is_experimental
                else "No experimental challenge model family is attached to this recommendation."
            ),
        ),
    ]



def _model_family_selection_review_status(
    selection_profile: ModelFamilySelectionProfile,
    recommendation: ModelFamilySelectionRecommendation,
    checks: list[ModelFamilySelectionReviewCheck],
) -> tuple[str, list[str], list[str], list[str], list[str]]:
    triggered_check_codes = [check.code for check in checks if not check.passed]
    governing_rule_lines: list[str] = []
    status_rule_lines: list[str] = []
    recommended_actions = list(recommendation.recommended_actions)
    requires_attention = False

    if recommendation.recommendation_status in selection_profile.ready_recommendation_statuses:
        governing_rule_lines.append(
            f"Recommendation status {recommendation.recommendation_status.value} is inside the governed ready set."
        )
    if recommendation.recommendation_status in selection_profile.attention_statuses:
        requires_attention = True
        governing_rule_lines.append(
            f"Attention is required because recommendation status {recommendation.recommendation_status.value} is governed as attention-worthy."
        )
    if (
        selection_profile.attention_if_challenge_experimental
        and recommendation.challenge_model_family is not None
        and recommendation.challenge_model_family.value in EXPERIMENTAL_MODEL_FAMILIES
    ):
        requires_attention = True
        governing_rule_lines.append(
            f"Attention is required because challenge model family {recommendation.challenge_model_family.value} is published as experimental."
        )
    if selection_profile.attention_if_any_checks_fail and triggered_check_codes:
        requires_attention = True
        status_rule_lines.append(
            "Attention required because governed selection-review checks failed: "
            + ", ".join(triggered_check_codes)
            + "."
        )
    if not status_rule_lines:
        status_rule_lines.append(
            "Ready because selection-review checks and governed status rules did not trigger additional attention."
            if not requires_attention
            else "Attention required because governed selection-review policy was triggered."
        )
    if requires_attention:
        attention_note = (
            "Keep the selection recommendation in assessor-facing attention status until the governed challenge-path, applicability, or packet-check concerns are resolved."
        )
        if attention_note not in recommended_actions:
            recommended_actions.append(attention_note)
    else:
        ready_note = "Selection recommendation is ready for assessor-facing review within the governed selection profile."
        if ready_note not in recommended_actions:
            recommended_actions.append(ready_note)
    return (
        "model_family_selection_review_attention_needed"
        if requires_attention
        else "ready_for_model_family_selection_review",
        triggered_check_codes,
        governing_rule_lines,
        status_rule_lines,
        recommended_actions,
    )



def preview_model_family_selection_review(
    request: PreviewModelFamilySelectionReviewRequest,
    provenance_builder: ProvenanceBuilder,
) -> ModelFamilySelectionReviewPreview:
    recommendation = request.selection_recommendation
    selection_profile = _resolve_model_family_selection_profile_from_recommendation(
        recommendation,
        provenance_builder.defaults_registry,
    )
    checks = _model_family_selection_review_checks(recommendation)
    review_status, triggered_check_codes, governing_rule_lines, status_rule_lines, recommended_actions = (
        _model_family_selection_review_status(
            selection_profile,
            recommendation,
            checks,
        )
    )
    return ModelFamilySelectionReviewPreview(
        scenario_id=recommendation.scenario_id,
        selection_profile_id=recommendation.selection_profile_id,
        recommendation_status=recommendation.recommendation_status,
        primary_model_family=recommendation.primary_model_family,
        challenge_model_family=recommendation.challenge_model_family,
        review_status=review_status,
        triggered_check_codes=triggered_check_codes,
        governing_rule_lines=governing_rule_lines,
        status_rule_lines=status_rule_lines,
        triggered_signal_lines=recommendation.triggered_signal_lines,
        recommended_actions=recommended_actions,
    )



def build_model_family_selection_review_packet(
    request: BuildModelFamilySelectionReviewPacketRequest,
    provenance_builder: ProvenanceBuilder,
) -> ModelFamilySelectionReviewPacket:
    recommendation = request.selection_recommendation
    selection_profile = _resolve_model_family_selection_profile_from_recommendation(
        recommendation,
        provenance_builder.defaults_registry,
    )
    review_preview = preview_model_family_selection_review(
        PreviewModelFamilySelectionReviewRequest(selection_recommendation=recommendation),
        provenance_builder,
    )
    checks = _model_family_selection_review_checks(recommendation)
    comparison_guidance_lines = []
    if recommendation.comparison_profile_id:
        comparison_guidance_lines.append(
            f"Governed comparison profile {recommendation.comparison_profile_id} should be used before carrying the challenge family into assessor-facing comparison review."
        )
    else:
        comparison_guidance_lines.append(
            "No governed comparison profile is attached because the selection recommendation keeps the baseline only."
        )
    summary_lines = [
        selection_profile.review_packet_template
        or "Build a governed assessor-facing review packet for an Environmental Fate MCP model-family selection recommendation.",
        (
            f"Selection review packet covers scenario {recommendation.scenario_id} with baseline "
            f"{recommendation.primary_model_family.value}."
        ),
        f"Recommendation status: {recommendation.recommendation_status.value}.",
        f"Review status: {review_preview.review_status}.",
    ]
    if selection_profile.applicability_note:
        summary_lines.append(selection_profile.applicability_note)
    review_packet = ModelFamilySelectionReviewPacket(
        scenario_id=recommendation.scenario_id,
        run_mode=recommendation.run_mode,
        fit_for_purpose=recommendation.fit_for_purpose,
        selection_profile_id=recommendation.selection_profile_id,
        recommendation_status=recommendation.recommendation_status,
        primary_model_family=recommendation.primary_model_family,
        challenge_model_family=recommendation.challenge_model_family,
        review_status=review_preview.review_status,
        review_preview=review_preview,
        selection_recommendation=recommendation,
        checks=checks,
        summary_lines=summary_lines,
        triggered_signal_lines=recommendation.triggered_signal_lines,
        recommended_actions=review_preview.recommended_actions,
        primary_applicability_lines=recommendation.primary_fit_assessment.applicability_lines,
        scientific_unsuitability_lines=_selection_recommendation_unsuitability_lines(
            recommendation
        ),
        challenge_applicability_lines=(
            recommendation.challenge_fit_assessment.applicability_lines
            if recommendation.challenge_fit_assessment is not None
            else []
        ),
        comparison_guidance_lines=comparison_guidance_lines,
        review_template_used=selection_profile.review_packet_template,
        provenance=provenance_builder.bundle(recommendation.provenance.source_references),
        limitations=recommendation.limitations,
    )
    review_packet.review_checklist = _build_model_family_selection_review_checklist(
        selection_profile,
        review_packet,
    )
    return review_packet



def build_model_family_selection_review_brief(
    request: BuildModelFamilySelectionReviewBriefRequest,
    provenance_builder: ProvenanceBuilder,
) -> ModelFamilySelectionReviewBrief:
    review_packet = request.review_packet
    selection_profile = _resolve_model_family_selection_profile_from_recommendation(
        review_packet.selection_recommendation,
        provenance_builder.defaults_registry,
    )
    passed_check_count = sum(1 for check in review_packet.checks if check.passed)
    brief_lines = [
        selection_profile.review_brief_template
        or "Summarize whether the model-family selection recommendation is ready for assessor-facing review."
    ]
    brief_lines.extend(review_packet.summary_lines)
    brief_lines.extend("Trigger signal: " + line for line in review_packet.triggered_signal_lines)
    brief_lines.extend("Primary applicability: " + line for line in review_packet.primary_applicability_lines)
    brief_lines.extend("Challenge applicability: " + line for line in review_packet.challenge_applicability_lines)
    brief_lines.extend("Comparison guidance: " + line for line in review_packet.comparison_guidance_lines)
    for item in review_packet.review_checklist:
        brief_lines.append(f"[{item.status}] {item.prompt}")
        if item.evidence_lines:
            brief_lines.append("Evidence: " + " | ".join(item.evidence_lines))
    return ModelFamilySelectionReviewBrief(
        review_packet_id=review_packet.review_packet_id,
        scenario_id=review_packet.scenario_id,
        run_mode=review_packet.run_mode,
        fit_for_purpose=review_packet.fit_for_purpose,
        selection_profile_id=review_packet.selection_profile_id,
        recommendation_status=review_packet.recommendation_status,
        primary_model_family=review_packet.primary_model_family,
        challenge_model_family=review_packet.challenge_model_family,
        review_status=review_packet.review_status,
        passed_check_count=passed_check_count,
        total_check_count=len(review_packet.checks),
        review_template_used=selection_profile.review_brief_template,
        checklist_items=review_packet.review_checklist,
        brief_lines=brief_lines,
        triggered_signal_lines=review_packet.triggered_signal_lines,
        recommended_actions=review_packet.recommended_actions,
        primary_applicability_lines=review_packet.primary_applicability_lines,
        challenge_applicability_lines=review_packet.challenge_applicability_lines,
        comparison_guidance_lines=review_packet.comparison_guidance_lines,
        limitations=review_packet.limitations,
    )



def _resolve_model_family_challenge_review_profile(
    selection_recommendation: ModelFamilySelectionRecommendation,
    defaults_registry: DefaultsRegistry,
) -> ModelFamilyChallengeReviewProfile:
    challenge_profile = defaults_registry.resolve_model_family_challenge_review_profile(
        selection_recommendation.selection_profile_id,
        selection_recommendation.comparison_profile_id,
    )
    if challenge_profile is None:
        raise FateValidationError(
            code="unknown_model_family_challenge_review_profile",
            message=(
                f"No governed challenge-review profile is declared for selection profile "
                f"{selection_recommendation.selection_profile_id}."
            ),
            suggestion="Declare the composed challenge-review policy in defaults/v1/model_family_challenge_review_profiles.json.",
        )
    if challenge_profile.selection_profile_id != selection_recommendation.selection_profile_id:
        raise FateValidationError(
            code="model_family_challenge_review_profile_selection_mismatch",
            message=(
                f"Challenge-review profile {challenge_profile.profile_id} does not match selection profile "
                f"{selection_recommendation.selection_profile_id}."
            ),
            suggestion="Use a challenge-review profile governed for the same selection profile.",
        )
    if (
        selection_recommendation.comparison_profile_id is not None
        and challenge_profile.comparison_profile_id not in {
            selection_recommendation.comparison_profile_id,
            None,
        }
    ):
        raise FateValidationError(
            code="model_family_challenge_review_profile_comparison_mismatch",
            message=(
                f"Challenge-review profile {challenge_profile.profile_id} does not match governed comparison profile "
                f"{selection_recommendation.comparison_profile_id}."
            ),
            suggestion="Use a challenge-review profile declared for the same comparison profile.",
        )
    return challenge_profile



def _model_family_challenge_review_checks(
    challenge_profile: ModelFamilyChallengeReviewProfile,
    selection_recommendation: ModelFamilySelectionRecommendation,
    selection_review_packet: ModelFamilySelectionReviewPacket,
    comparison_review_packet: ModelFamilyComparisonReviewPacket | None,
) -> list[ModelFamilyChallengeReviewCheck]:
    comparison_required = (
        selection_recommendation.recommendation_status
        == ModelFamilySelectionStatus.DEFAULT_WITH_EXPERIMENTAL_CHALLENGE
    )
    comparison_ready = comparison_review_packet is not None and (
        comparison_review_packet.review_status in challenge_profile.ready_comparison_review_statuses
    )
    comparison_profile_matches = (
        challenge_profile.comparison_profile_id is None
        or comparison_review_packet is None
        or comparison_review_packet.comparison_profile_id == challenge_profile.comparison_profile_id
    )
    return [
        ModelFamilyChallengeReviewCheck(
            code="selection_review_status_ready_under_profile",
            passed=selection_review_packet.review_status
            in challenge_profile.ready_selection_review_statuses,
            message=(
                f"Selection review status {selection_review_packet.review_status} is inside the governed ready set."
            ),
        ),
        ModelFamilyChallengeReviewCheck(
            code="comparison_review_present_when_challenge_recommended",
            passed=(not comparison_required) or comparison_review_packet is not None,
            message=(
                "A governed comparison review packet is present when the selection recommendation carries an experimental challenge path."
            ),
        ),
        ModelFamilyChallengeReviewCheck(
            code="comparison_review_status_ready_under_profile",
            passed=(not comparison_required) or comparison_ready,
            message=(
                "Comparison review status is inside the governed ready set when the challenge path requires comparison review."
            ),
        ),
        ModelFamilyChallengeReviewCheck(
            code="comparison_profile_matches_governed_challenge_profile",
            passed=comparison_profile_matches,
            message="Attached comparison review matches the comparison profile governed by the challenge-review profile.",
        ),
    ]



def _model_family_challenge_review_status(
    challenge_profile: ModelFamilyChallengeReviewProfile,
    selection_recommendation: ModelFamilySelectionRecommendation,
    selection_review_packet: ModelFamilySelectionReviewPacket,
    comparison_review_packet: ModelFamilyComparisonReviewPacket | None,
    checks: list[ModelFamilyChallengeReviewCheck],
) -> tuple[str, list[str], list[str], list[str], list[str], list[str]]:
    triggered_check_codes = [check.code for check in checks if not check.passed]
    governing_rule_lines: list[str] = []
    status_rule_lines: list[str] = []
    triggered_component_statuses: list[str] = []
    recommended_actions = list(selection_review_packet.recommended_actions)
    if comparison_review_packet is not None:
        for action in comparison_review_packet.recommended_actions:
            if action not in recommended_actions:
                recommended_actions.append(action)

    requires_attention = False
    selection_ready = (
        selection_review_packet.review_status in challenge_profile.ready_selection_review_statuses
    )
    if selection_ready:
        governing_rule_lines.append(
            f"Selection review status {selection_review_packet.review_status} is inside the governed ready set."
        )
    else:
        requires_attention = True
        triggered_component_statuses.append(selection_review_packet.review_status)
        governing_rule_lines.append(
            f"Attention is required because selection review status {selection_review_packet.review_status} is outside the governed ready set."
        )

    comparison_required = (
        selection_recommendation.recommendation_status
        == ModelFamilySelectionStatus.DEFAULT_WITH_EXPERIMENTAL_CHALLENGE
    )
    if comparison_review_packet is None:
        if comparison_required and challenge_profile.attention_if_comparison_missing_when_challenge_recommended:
            requires_attention = True
            governing_rule_lines.append(
                "Attention is required because the governed selection recommendation carries an experimental challenge path but no comparison review packet is attached."
            )
        else:
            governing_rule_lines.append(
                "No comparison review packet is attached because the governed selection path remains baseline-only."
            )
    else:
        comparison_ready = (
            comparison_review_packet.review_status in challenge_profile.ready_comparison_review_statuses
        )
        if comparison_ready:
            governing_rule_lines.append(
                f"Comparison review status {comparison_review_packet.review_status} is inside the governed ready set."
            )
        else:
            requires_attention = True
            triggered_component_statuses.append(comparison_review_packet.review_status)
            governing_rule_lines.append(
                f"Attention is required because comparison review status {comparison_review_packet.review_status} is outside the governed ready set."
            )

    if challenge_profile.attention_if_any_checks_fail and triggered_check_codes:
        requires_attention = True
        status_rule_lines.append(
            "Attention required because governed challenge-review checks failed: "
            + ", ".join(triggered_check_codes)
            + "."
        )
    if not status_rule_lines:
        status_rule_lines.append(
            "Ready because governed challenge-review component statuses and checks did not trigger additional attention."
            if not requires_attention
            else "Attention required because governed challenge-review policy was triggered."
        )

    action_template = (
        challenge_profile.attention_action_template if requires_attention else challenge_profile.ready_action_template
    )
    if action_template and action_template not in recommended_actions:
        recommended_actions.append(action_template)

    return (
        "model_family_challenge_review_attention_needed"
        if requires_attention
        else "ready_for_model_family_challenge_review",
        triggered_check_codes,
        triggered_component_statuses,
        governing_rule_lines,
        status_rule_lines,
        recommended_actions,
    )



def _model_family_challenge_review_evidence_line(
    field_name: str,
    review_packet: ModelFamilyChallengeReviewPacket,
) -> str | None:
    if field_name == "selection_recommendation_status":
        return (
            f"Selection recommendation status: {review_packet.selection_recommendation_status.value}."
        )
    if field_name == "selection_review_status":
        return f"Selection review status: {review_packet.selection_review_status}."
    if field_name == "comparison_profile_id":
        if review_packet.comparison_profile_id:
            return f"Governed comparison profile: {review_packet.comparison_profile_id}."
        return "No governed comparison profile is attached because the selection path stays on the baseline family only."
    if field_name == "comparison_outcome" and review_packet.comparison_outcome is not None:
        return f"Comparison outcome: {review_packet.comparison_outcome.value}."
    if field_name == "comparison_review_status":
        if review_packet.comparison_review_status:
            return f"Comparison review status: {review_packet.comparison_review_status}."
        return "No comparison review status is present because the optional comparison path was not built."
    if field_name == "triggered_signal_lines" and review_packet.triggered_signal_lines:
        return "Trigger signals: " + " | ".join(review_packet.triggered_signal_lines)
    if field_name == "dominant_delta_lines" and review_packet.dominant_delta_lines:
        return "Dominant deltas: " + " | ".join(review_packet.dominant_delta_lines)
    if field_name == "primary_applicability_lines" and review_packet.primary_applicability_lines:
        return "Primary applicability: " + " | ".join(review_packet.primary_applicability_lines)
    if field_name == "challenge_applicability_lines" and review_packet.challenge_applicability_lines:
        return "Challenge applicability: " + " | ".join(review_packet.challenge_applicability_lines)
    if field_name == "comparison_guidance_lines" and review_packet.comparison_guidance_lines:
        return "Comparison guidance: " + " | ".join(review_packet.comparison_guidance_lines)
    if field_name == "governing_rule_lines" and review_packet.governing_rule_lines:
        return "Governing rules: " + " | ".join(review_packet.governing_rule_lines)
    if field_name == "limitations" and review_packet.limitations:
        return "Limitations: " + "; ".join(note.message for note in review_packet.limitations)
    return None



def _build_model_family_challenge_review_checklist(
    challenge_profile: ModelFamilyChallengeReviewProfile,
    review_packet: ModelFamilyChallengeReviewPacket,
) -> list[ModelFamilyChallengeReviewChecklistItem]:
    checklist_items: list[ModelFamilyChallengeReviewChecklistItem] = []
    for template in challenge_profile.review_checklist:
        unknown_fields = sorted(
            field
            for field in template.evidence_hint_fields
            if field not in MODEL_FAMILY_CHALLENGE_REVIEW_EVIDENCE_FIELDS
        )
        if unknown_fields:
            raise FateValidationError(
                code="invalid_model_family_challenge_review_checklist_field",
                message=(
                    f"Challenge-review profile {challenge_profile.profile_id} declares unknown "
                    f"review checklist evidence fields: {unknown_fields}."
                ),
                suggestion="Limit review checklist evidence_hint_fields to fields exposed by the challenge review packet builder.",
                details={"unknownEvidenceHintFields": unknown_fields},
            )
        evidence_lines = []
        for field_name in template.evidence_hint_fields:
            line = _model_family_challenge_review_evidence_line(field_name, review_packet)
            if line and line not in evidence_lines:
                evidence_lines.append(line)
        checklist_items.append(
            ModelFamilyChallengeReviewChecklistItem(
                code=template.code,
                prompt=template.prompt,
                rationale=template.rationale,
                status="ready_for_assessor_confirmation" if evidence_lines else "attention_required",
                evidence_lines=evidence_lines,
            )
        )
    return checklist_items



def _build_model_family_challenge_review_components(
    request: PreviewModelFamilyChallengeReviewRequest | BuildModelFamilyChallengeReviewPacketRequest,
    runtime,
    provenance_builder: ProvenanceBuilder,
) -> tuple[
    ModelFamilySelectionRecommendation,
    ModelFamilySelectionReviewPacket,
    ModelFamilyComparisonPacket | None,
    ModelFamilyComparisonReviewPacket | None,
]:
    selection_recommendation = recommend_model_family_selection(
        RecommendModelFamilySelectionRequest(
            scenario=request.scenario,
            selection_profile_id=request.selection_profile_id,
            run_mode=request.run_mode,
            fit_for_purpose=request.fit_for_purpose,
        ),
        provenance_builder,
    )
    selection_review_packet = build_model_family_selection_review_packet(
        BuildModelFamilySelectionReviewPacketRequest(
            selection_recommendation=selection_recommendation,
        ),
        provenance_builder,
    )

    comparison_packet = None
    comparison_review_packet = None
    if (
        selection_recommendation.challenge_model_family is not None
        and selection_recommendation.comparison_profile_id is not None
    ):
        comparison_packet = build_model_family_comparison_packet(
            BuildModelFamilyComparisonPacketRequest(
                scenario=request.scenario,
                comparison_profile_id=selection_recommendation.comparison_profile_id,
                run_mode=request.run_mode,
                fit_for_purpose=request.fit_for_purpose,
                base_model_family=selection_recommendation.primary_model_family,
                candidate_model_family=selection_recommendation.challenge_model_family,
                bucket_count=request.bucket_count,
                bucket_duration_days=request.bucket_duration_days,
                requested_media=request.requested_media,
                max_surface_samples=request.max_surface_samples,
            ),
            runtime,
            provenance_builder,
        )
        comparison_review_packet = build_model_family_comparison_review_packet(
            BuildModelFamilyComparisonReviewPacketRequest(
                comparison_packet=comparison_packet,
            ),
            provenance_builder,
        )
    return (
        selection_recommendation,
        selection_review_packet,
        comparison_packet,
        comparison_review_packet,
    )



def _preview_model_family_challenge_review(
    challenge_profile: ModelFamilyChallengeReviewProfile,
    selection_recommendation: ModelFamilySelectionRecommendation,
    selection_review_packet: ModelFamilySelectionReviewPacket,
    comparison_packet: ModelFamilyComparisonPacket | None,
    comparison_review_packet: ModelFamilyComparisonReviewPacket | None,
) -> ModelFamilyChallengeReviewPreview:
    checks = _model_family_challenge_review_checks(
        challenge_profile,
        selection_recommendation,
        selection_review_packet,
        comparison_review_packet,
    )
    (
        review_status,
        triggered_check_codes,
        triggered_component_statuses,
        governing_rule_lines,
        status_rule_lines,
        recommended_actions,
    ) = _model_family_challenge_review_status(
        challenge_profile,
        selection_recommendation,
        selection_review_packet,
        comparison_review_packet,
        checks,
    )

    return ModelFamilyChallengeReviewPreview(
        scenario_id=selection_recommendation.scenario_id,
        selection_profile_id=selection_recommendation.selection_profile_id,
        challenge_review_profile_id=challenge_profile.profile_id,
        selection_recommendation_status=selection_recommendation.recommendation_status,
        selection_review_status=selection_review_packet.review_status,
        comparison_profile_id=selection_recommendation.comparison_profile_id,
        comparison_outcome=(
            comparison_review_packet.comparison_outcome if comparison_review_packet is not None else None
        ),
        comparison_review_status=(
            comparison_review_packet.review_status if comparison_review_packet is not None else None
        ),
        review_status=review_status,
        triggered_check_codes=triggered_check_codes,
        triggered_component_statuses=triggered_component_statuses,
        governing_rule_lines=governing_rule_lines,
        status_rule_lines=status_rule_lines,
        triggered_signal_lines=selection_review_packet.triggered_signal_lines,
        dominant_delta_lines=(
            comparison_review_packet.dominant_delta_lines if comparison_review_packet is not None else []
        ),
        recommended_actions=recommended_actions,
    )



def preview_model_family_challenge_review(
    request: PreviewModelFamilyChallengeReviewRequest,
    runtime,
    provenance_builder: ProvenanceBuilder,
) -> ModelFamilyChallengeReviewPreview:
    selection_recommendation, selection_review_packet, comparison_packet, comparison_review_packet = (
        _build_model_family_challenge_review_components(request, runtime, provenance_builder)
    )
    challenge_profile = _resolve_model_family_challenge_review_profile(
        selection_recommendation,
        provenance_builder.defaults_registry,
    )
    return _preview_model_family_challenge_review(
        challenge_profile,
        selection_recommendation,
        selection_review_packet,
        comparison_packet,
        comparison_review_packet,
    )



def build_model_family_challenge_review_packet(
    request: BuildModelFamilyChallengeReviewPacketRequest,
    runtime,
    provenance_builder: ProvenanceBuilder,
) -> ModelFamilyChallengeReviewPacket:
    selection_recommendation, selection_review_packet, comparison_packet, comparison_review_packet = (
        _build_model_family_challenge_review_components(request, runtime, provenance_builder)
    )
    challenge_profile = _resolve_model_family_challenge_review_profile(
        selection_recommendation,
        provenance_builder.defaults_registry,
    )
    review_preview = _preview_model_family_challenge_review(
        challenge_profile,
        selection_recommendation,
        selection_review_packet,
        comparison_packet,
        comparison_review_packet,
    )
    checks = _model_family_challenge_review_checks(
        challenge_profile,
        selection_recommendation,
        selection_review_packet,
        comparison_review_packet,
    )

    summary_lines = [
        challenge_profile.review_packet_template
        or "Build a governed assessor-facing model-family challenge review packet that bundles selection review and, when applicable, comparison review.",
        (
            f"Challenge review packet covers scenario {request.scenario.scenario_id} with baseline "
            f"{selection_recommendation.primary_model_family.value}."
        ),
        f"Selection recommendation status: {selection_recommendation.recommendation_status.value}.",
        f"Overall challenge review status: {review_preview.review_status}.",
    ]
    if challenge_profile.applicability_note:
        summary_lines.append(challenge_profile.applicability_note)
    if comparison_review_packet is not None:
        summary_lines.append(
            f"Comparison outcome {comparison_review_packet.comparison_outcome.value} is available through governed comparison profile {comparison_review_packet.comparison_profile_id}."
        )
    else:
        summary_lines.append(
            "No governed comparison packet is attached because the selection path stays on the baseline family only."
        )

    limitations: list[LimitationNote] = []
    seen_limitations: set[tuple[str, str]] = set()
    for note in selection_review_packet.limitations + (
        comparison_review_packet.limitations if comparison_review_packet is not None else []
    ):
        key = (note.code, note.message)
        if key not in seen_limitations:
            seen_limitations.add(key)
            limitations.append(note)

    source_references = list(selection_review_packet.provenance.source_references)
    if comparison_review_packet is not None:
        for item in comparison_review_packet.provenance.source_references:
            if item not in source_references:
                source_references.append(item)

    review_packet = ModelFamilyChallengeReviewPacket(
        scenario_id=request.scenario.scenario_id,
        run_mode=request.run_mode,
        fit_for_purpose=request.fit_for_purpose,
        selection_profile_id=selection_recommendation.selection_profile_id,
        challenge_review_profile_id=challenge_profile.profile_id,
        review_status=review_preview.review_status,
        selection_recommendation_status=selection_recommendation.recommendation_status,
        selection_review_status=review_preview.selection_review_status,
        comparison_profile_id=selection_recommendation.comparison_profile_id,
        comparison_outcome=(
            comparison_review_packet.comparison_outcome if comparison_review_packet is not None else None
        ),
        comparison_review_status=(
            comparison_review_packet.review_status if comparison_review_packet is not None else None
        ),
        review_preview=review_preview,
        selection_recommendation=selection_recommendation,
        selection_review_packet=selection_review_packet,
        comparison_packet=comparison_packet,
        comparison_review_packet=comparison_review_packet,
        checks=checks,
        summary_lines=summary_lines,
        governing_rule_lines=review_preview.governing_rule_lines,
        triggered_signal_lines=review_preview.triggered_signal_lines,
        dominant_delta_lines=review_preview.dominant_delta_lines,
        recommended_actions=review_preview.recommended_actions,
        primary_applicability_lines=selection_review_packet.primary_applicability_lines,
        challenge_applicability_lines=selection_review_packet.challenge_applicability_lines,
        comparison_guidance_lines=selection_review_packet.comparison_guidance_lines,
        review_template_used=challenge_profile.review_packet_template,
        provenance=provenance_builder.bundle(source_references),
        limitations=limitations,
    )
    review_packet.review_checklist = _build_model_family_challenge_review_checklist(
        challenge_profile,
        review_packet,
    )
    return review_packet



def build_model_family_challenge_review_brief(
    request: BuildModelFamilyChallengeReviewBriefRequest,
    provenance_builder: ProvenanceBuilder,
) -> ModelFamilyChallengeReviewBrief:
    review_packet = request.review_packet
    challenge_profile = provenance_builder.defaults_registry.model_family_challenge_review_profile(
        review_packet.challenge_review_profile_id
    )
    if challenge_profile is None:
        raise FateValidationError(
            code="unknown_model_family_challenge_review_profile",
            message=(
                f"Challenge-review packet {review_packet.review_packet_id} references unknown profile "
                f"{review_packet.challenge_review_profile_id}."
            ),
            suggestion="Rebuild the packet with a governed challenge-review profile that exists in defaults.",
        )
    passed_check_count = sum(1 for check in review_packet.checks if check.passed)
    brief_lines = [
        challenge_profile.review_brief_template
        or "Summarize whether the governed model-family challenge review is ready for assessor-facing reuse."
    ]
    brief_lines.extend(review_packet.summary_lines)
    brief_lines.extend("Governing rule: " + line for line in review_packet.governing_rule_lines)
    brief_lines.extend("Trigger signal: " + line for line in review_packet.triggered_signal_lines)
    brief_lines.extend("Primary applicability: " + line for line in review_packet.primary_applicability_lines)
    brief_lines.extend("Challenge applicability: " + line for line in review_packet.challenge_applicability_lines)
    brief_lines.extend("Comparison guidance: " + line for line in review_packet.comparison_guidance_lines)
    brief_lines.extend("Dominant delta: " + line for line in review_packet.dominant_delta_lines)
    for item in review_packet.review_checklist:
        brief_lines.append(f"[{item.status}] {item.prompt}")
        if item.evidence_lines:
            brief_lines.append("Evidence: " + " | ".join(item.evidence_lines))
    return ModelFamilyChallengeReviewBrief(
        review_packet_id=review_packet.review_packet_id,
        scenario_id=review_packet.scenario_id,
        run_mode=review_packet.run_mode,
        fit_for_purpose=review_packet.fit_for_purpose,
        selection_profile_id=review_packet.selection_profile_id,
        challenge_review_profile_id=review_packet.challenge_review_profile_id,
        review_status=review_packet.review_status,
        selection_recommendation_status=review_packet.selection_recommendation_status,
        selection_review_status=review_packet.selection_review_status,
        comparison_profile_id=review_packet.comparison_profile_id,
        comparison_outcome=review_packet.comparison_outcome,
        comparison_review_status=review_packet.comparison_review_status,
        passed_check_count=passed_check_count,
        total_check_count=len(review_packet.checks),
        review_template_used=challenge_profile.review_brief_template,
        checklist_items=review_packet.review_checklist,
        brief_lines=brief_lines,
        triggered_signal_lines=review_packet.triggered_signal_lines,
        dominant_delta_lines=review_packet.dominant_delta_lines,
        recommended_actions=review_packet.recommended_actions,
        primary_applicability_lines=review_packet.primary_applicability_lines,
        challenge_applicability_lines=review_packet.challenge_applicability_lines,
        comparison_guidance_lines=review_packet.comparison_guidance_lines,
        limitations=review_packet.limitations,
    )



def _estimate_model_family_result(
    scenario,
    model_family,
    run_mode: RunMode,
    fit_for_purpose: FitForPurpose,
    bucket_count: int,
    bucket_duration_days: float,
    requested_media: list,
    runtime,
) -> ConcentrationEstimationResult:
    return runtime.estimate(
        scenario,
        FateModelRunOptions(
            run_mode=run_mode,
            model_family=model_family,
            region_profile_id=scenario.geographic_scope.region_id,
            fit_for_purpose=fit_for_purpose,
            bucket_count=bucket_count,
            bucket_duration_days=bucket_duration_days,
            requested_media=requested_media,
        ),
    )



def build_model_family_challenge_scientific_dossier(
    request: BuildModelFamilyChallengeScientificDossierRequest,
    runtime,
    provenance_builder: ProvenanceBuilder,
) -> ModelFamilyChallengeScientificDossier:
    challenge_review_packet = build_model_family_challenge_review_packet(
        BuildModelFamilyChallengeReviewPacketRequest(
            scenario=request.scenario,
            selection_profile_id=request.selection_profile_id,
            run_mode=request.run_mode,
            fit_for_purpose=request.fit_for_purpose,
            bucket_count=request.bucket_count,
            bucket_duration_days=request.bucket_duration_days,
            requested_media=request.requested_media,
            max_surface_samples=request.max_surface_samples,
        ),
        runtime,
        provenance_builder,
    )
    challenge_review_brief = build_model_family_challenge_review_brief(
        BuildModelFamilyChallengeReviewBriefRequest(review_packet=challenge_review_packet),
        provenance_builder,
    )

    selection_recommendation = challenge_review_packet.selection_recommendation
    primary_result = _estimate_model_family_result(
        request.scenario,
        selection_recommendation.primary_model_family,
        request.run_mode,
        request.fit_for_purpose,
        request.bucket_count,
        request.bucket_duration_days,
        request.requested_media,
        runtime,
    )
    primary_scientific_review_packet = build_scientific_review_packet(
        BuildScientificReviewPacketRequest(
            scenario=request.scenario,
            result=primary_result,
            max_surface_samples=request.max_surface_samples,
        ),
        provenance_builder,
    )
    primary_scientific_review_brief = build_scientific_review_brief(
        BuildScientificReviewBriefRequest(review_packet=primary_scientific_review_packet),
        provenance_builder,
    )

    challenge_scientific_review_packet = None
    challenge_scientific_review_brief = None
    if selection_recommendation.challenge_model_family is not None:
        challenge_result = _estimate_model_family_result(
            request.scenario,
            selection_recommendation.challenge_model_family,
            request.run_mode,
            request.fit_for_purpose,
            request.bucket_count,
            request.bucket_duration_days,
            request.requested_media,
            runtime,
        )
        challenge_scientific_review_packet = build_scientific_review_packet(
            BuildScientificReviewPacketRequest(
                scenario=request.scenario,
                result=challenge_result,
                max_surface_samples=request.max_surface_samples,
            ),
            provenance_builder,
        )
        challenge_scientific_review_brief = build_scientific_review_brief(
            BuildScientificReviewBriefRequest(review_packet=challenge_scientific_review_packet),
            provenance_builder,
        )

    summary_lines = [
        (
            "Build a composed scientific dossier that couples the governed model-family challenge review "
            "path with model-family-specific scientific review packets."
        ),
        (
            f"Challenge review status {challenge_review_packet.review_status} governs scenario "
            f"{request.scenario.scenario_id}."
        ),
        (
            f"Primary family {selection_recommendation.primary_model_family.value} scientific review outcome: "
            f"{primary_scientific_review_brief.review_outcome.value}."
        ),
    ]
    if challenge_scientific_review_brief is not None:
        summary_lines.append(
            f"Challenge family {selection_recommendation.challenge_model_family.value} scientific review outcome: "
            f"{challenge_scientific_review_brief.review_outcome.value}."
        )
    else:
        summary_lines.append(
            "No challenge-family scientific review packet is attached because the governed selection path stays baseline-only."
        )

    recommended_actions = list(challenge_review_packet.recommended_actions)
    for brief in (challenge_review_brief, primary_scientific_review_brief, challenge_scientific_review_brief):
        if brief is None:
            continue
        for action in brief.recommended_actions:
            if action not in recommended_actions:
                recommended_actions.append(action)

    limitations = _merge_limitations(
        challenge_review_packet.limitations,
        primary_scientific_review_packet.limitations,
        challenge_scientific_review_packet.limitations if challenge_scientific_review_packet is not None else [],
    )
    provenance = provenance_builder.bundle(
        _merge_source_references(
            challenge_review_packet.provenance.source_references,
            primary_scientific_review_packet.provenance.source_references,
            (
                challenge_scientific_review_packet.provenance.source_references
                if challenge_scientific_review_packet is not None
                else []
            ),
        )
    )

    return ModelFamilyChallengeScientificDossier(
        scenario_id=request.scenario.scenario_id,
        run_mode=request.run_mode,
        fit_for_purpose=request.fit_for_purpose,
        selection_profile_id=challenge_review_packet.selection_profile_id,
        challenge_review_profile_id=challenge_review_packet.challenge_review_profile_id,
        primary_model_family=selection_recommendation.primary_model_family,
        challenge_model_family=selection_recommendation.challenge_model_family,
        challenge_review_status=challenge_review_packet.review_status,
        selection_recommendation_status=challenge_review_packet.selection_recommendation_status,
        comparison_profile_id=challenge_review_packet.comparison_profile_id,
        comparison_outcome=challenge_review_packet.comparison_outcome,
        challenge_review_packet_id=challenge_review_packet.review_packet_id,
        primary_scientific_review_packet_id=primary_scientific_review_packet.review_packet_id,
        challenge_scientific_review_packet_id=(
            challenge_scientific_review_packet.review_packet_id
            if challenge_scientific_review_packet is not None
            else None
        ),
        challenge_review_brief=challenge_review_brief,
        primary_scientific_review_brief=primary_scientific_review_brief,
        challenge_scientific_review_brief=challenge_scientific_review_brief,
        summary_lines=summary_lines,
        recommended_actions=recommended_actions,
        triggered_signal_lines=challenge_review_packet.triggered_signal_lines,
        dominant_delta_lines=challenge_review_packet.dominant_delta_lines,
        primary_equation_lines=primary_scientific_review_brief.equation_lines,
        challenge_equation_lines=(
            challenge_scientific_review_brief.equation_lines
            if challenge_scientific_review_brief is not None
            else []
        ),
        primary_benchmark_reference_lines=primary_scientific_review_brief.benchmark_reference_lines,
        challenge_benchmark_reference_lines=(
            challenge_scientific_review_brief.benchmark_reference_lines
            if challenge_scientific_review_brief is not None
            else []
        ),
        provenance=provenance,
        limitations=limitations,
    )



def build_model_family_challenge_scientific_dossier_brief(
    request: BuildModelFamilyChallengeScientificDossierBriefRequest,
    provenance_builder: ProvenanceBuilder,
) -> ModelFamilyChallengeScientificDossierBrief:
    dossier = request.dossier
    primary_scientific_review_brief = dossier.primary_scientific_review_brief
    challenge_scientific_review_brief = dossier.challenge_scientific_review_brief

    summary_lines = [
        (
            "Summarize the governed model-family challenge path together with the baseline and optional "
            "challenge-family scientific review outcomes."
        )
    ]
    summary_lines.extend(dossier.summary_lines)
    summary_lines.extend("Trigger signal: " + line for line in dossier.triggered_signal_lines)
    summary_lines.extend("Dominant delta: " + line for line in dossier.dominant_delta_lines)
    summary_lines.extend(
        "Primary scientific outcome: " + line for line in primary_scientific_review_brief.outcome_lines
    )
    summary_lines.extend(
        "Primary equation trace: " + line for line in primary_scientific_review_brief.equation_lines
    )
    if challenge_scientific_review_brief is not None:
        summary_lines.extend(
            "Challenge scientific outcome: " + line
            for line in challenge_scientific_review_brief.outcome_lines
        )
        summary_lines.extend(
            "Challenge equation trace: " + line
            for line in challenge_scientific_review_brief.equation_lines
        )

    return ModelFamilyChallengeScientificDossierBrief(
        dossier_id=dossier.dossier_id,
        scenario_id=dossier.scenario_id,
        run_mode=dossier.run_mode,
        fit_for_purpose=dossier.fit_for_purpose,
        selection_profile_id=dossier.selection_profile_id,
        challenge_review_profile_id=dossier.challenge_review_profile_id,
        primary_model_family=dossier.primary_model_family,
        challenge_model_family=dossier.challenge_model_family,
        challenge_review_status=dossier.challenge_review_status,
        selection_recommendation_status=dossier.selection_recommendation_status,
        comparison_profile_id=dossier.comparison_profile_id,
        comparison_outcome=dossier.comparison_outcome,
        primary_review_outcome=dossier.primary_scientific_review_brief.review_outcome,
        challenge_review_outcome=(
            dossier.challenge_scientific_review_brief.review_outcome
            if dossier.challenge_scientific_review_brief is not None
            else None
        ),
        primary_passed_check_count=primary_scientific_review_brief.passed_check_count,
        primary_total_check_count=primary_scientific_review_brief.total_check_count,
        challenge_passed_check_count=(
            challenge_scientific_review_brief.passed_check_count
            if challenge_scientific_review_brief is not None
            else None
        ),
        challenge_total_check_count=(
            challenge_scientific_review_brief.total_check_count
            if challenge_scientific_review_brief is not None
            else None
        ),
        summary_lines=summary_lines,
        recommended_actions=dossier.recommended_actions,
        triggered_signal_lines=dossier.triggered_signal_lines,
        dominant_delta_lines=dossier.dominant_delta_lines,
        primary_equation_lines=dossier.primary_equation_lines,
        challenge_equation_lines=dossier.challenge_equation_lines,
        primary_benchmark_reference_lines=dossier.primary_benchmark_reference_lines,
        challenge_benchmark_reference_lines=dossier.challenge_benchmark_reference_lines,
        limitations=dossier.limitations,
    )



def _model_family_comparison_outcome(
    base_fit_assessment: ReleaseScenarioFitAssessment,
    candidate_fit_assessment: ReleaseScenarioFitAssessment,
    comparison: FateScenarioComparisonRecord,
    profile: ModelFamilyComparisonProfile,
) -> ModelFamilyComparisonOutcome:
    if base_fit_assessment.verdict != "good_fit" or candidate_fit_assessment.verdict != "good_fit":
        return ModelFamilyComparisonOutcome.REVIEW_NEEDED
    for delta in comparison.surface_deltas:
        if delta.relative_delta is not None:
            if abs(delta.relative_delta) >= profile.material_relative_delta_threshold:
                return ModelFamilyComparisonOutcome.MATERIAL_MODEL_FAMILY_DIVERGENCE
        elif abs(delta.absolute_delta) > profile.material_absolute_delta_floor:
            return ModelFamilyComparisonOutcome.MATERIAL_MODEL_FAMILY_DIVERGENCE
    return ModelFamilyComparisonOutcome.COMPARABLE_SCREENING_OUTPUTS



def build_model_family_comparison_packet(
    request: BuildModelFamilyComparisonPacketRequest,
    runtime,
    provenance_builder: ProvenanceBuilder,
) -> ModelFamilyComparisonPacket:
    comparison_profile = _resolve_model_family_comparison_profile(
        request,
        runtime.defaults,
    )
    base_run_options = FateModelRunOptions(
        run_mode=request.run_mode,
        model_family=request.base_model_family,
        region_profile_id=request.scenario.geographic_scope.region_id,
        fit_for_purpose=request.fit_for_purpose,
        bucket_count=request.bucket_count,
        bucket_duration_days=request.bucket_duration_days,
        requested_media=request.requested_media,
    )
    candidate_run_options = FateModelRunOptions(
        run_mode=request.run_mode,
        model_family=request.candidate_model_family,
        region_profile_id=request.scenario.geographic_scope.region_id,
        fit_for_purpose=request.fit_for_purpose,
        bucket_count=request.bucket_count,
        bucket_duration_days=request.bucket_duration_days,
        requested_media=request.requested_media,
    )
    base_result = runtime.estimate(request.scenario, base_run_options)
    candidate_result = runtime.estimate(request.scenario, candidate_run_options)
    comparison = compare_fate_scenarios(
        CompareFateScenariosRequest(
            base_result=base_result,
            candidate_result=candidate_result,
        ),
        provenance_builder,
    )
    base_fit_assessment = assess_release_scenario_fit(request.scenario, base_run_options, provenance_builder)
    candidate_fit_assessment = assess_release_scenario_fit(
        request.scenario,
        candidate_run_options,
        provenance_builder,
    )
    comparison_outcome = _model_family_comparison_outcome(
        base_fit_assessment,
        candidate_fit_assessment,
        comparison,
        comparison_profile,
    )
    dominant_delta_lines = [
        f"{delta.medium.value}/{delta.compartment.value}: {delta.base_value:.6g} -> "
        f"{delta.candidate_value:.6g} {delta.concentration_unit}"
        + (
            f" ({delta.relative_delta:+.1%})"
            if delta.relative_delta is not None
            else f" (absolute delta {delta.absolute_delta:+.6g})"
        )
        for delta in sorted(comparison.surface_deltas, key=lambda item: abs(item.absolute_delta), reverse=True)[:5]
    ]
    base_equation_lines = _equation_lines_from_surfaces(base_result.surfaces)
    candidate_equation_lines = _equation_lines_from_surfaces(candidate_result.surfaces)
    base_benchmark_reference_lines = _benchmark_reference_lines(
        request.base_model_family,
        request.run_mode,
    )
    candidate_benchmark_reference_lines = _benchmark_reference_lines(
        request.candidate_model_family,
        request.run_mode,
    )
    summary_lines = [
        (
            f"Compared {request.base_model_family.value} against "
            f"{request.candidate_model_family.value} for scenario {request.scenario.scenario_id}."
        ),
        (
            f"Comparison profile: {comparison_profile.display_name} "
            f"({comparison_profile.profile_id})."
        ),
        (
            f"Run mode {request.run_mode.value} with fit-for-purpose {request.fit_for_purpose.value} "
            f"produced {len(comparison.surface_deltas)} comparable surface deltas."
        ),
        f"Base fit verdict: {base_fit_assessment.verdict} (score={base_fit_assessment.fit_score:.2f}).",
        f"Candidate fit verdict: {candidate_fit_assessment.verdict} (score={candidate_fit_assessment.fit_score:.2f}).",
    ]
    if comparison_profile.applicability_note:
        summary_lines.append(comparison_profile.applicability_note)
    outcome_lines: list[str] = []
    recommended_actions: list[str] = []
    if request.candidate_model_family.value in EXPERIMENTAL_MODEL_FAMILIES:
        recommended_actions.append(
            "Treat the candidate family as experimental and keep the default reference family as the screening baseline unless the transport question clearly requires the candidate assumptions."
        )
    if comparison_outcome == ModelFamilyComparisonOutcome.MATERIAL_MODEL_FAMILY_DIVERGENCE:
        if comparison_profile.divergence_outcome_template:
            outcome_lines.append(comparison_profile.divergence_outcome_template)
        recommended_actions.append(
            "Review the dominant surface deltas, residence-time assumptions, and equation traces before choosing which family better matches the decision context."
        )
    elif comparison_outcome == ModelFamilyComparisonOutcome.REVIEW_NEEDED:
        if comparison_profile.review_needed_outcome_template:
            outcome_lines.append(comparison_profile.review_needed_outcome_template)
        recommended_actions.append(
            "Resolve model-family applicability limitations before reusing this comparison in assessor-facing review."
        )
    else:
        if comparison_profile.comparable_outcome_template:
            outcome_lines.append(comparison_profile.comparable_outcome_template)
        recommended_actions.append(
            "Use the comparison as a sensitivity check showing that the candidate family does not materially diverge from the default screening baseline for this scenario."
        )
    recommended_actions.extend(
        note for note in comparison_profile.review_notes if note not in recommended_actions
    )
    limitations = [
        LimitationNote(
            code="model_family_comparison",
            message="Model-family comparison reflects deterministic Environmental Fate MCP outputs for one matched scenario and does not by itself endorse either family as the scientifically correct choice.",
        )
    ]
    for limit in comparison.limitations:
        if limit not in limitations:
            limitations.append(limit)
    if request.candidate_model_family.value in EXPERIMENTAL_MODEL_FAMILIES:
        limitations.append(
            LimitationNote(
                code="experimental_candidate_model_family",
                message=(
                    f"Candidate model family {request.candidate_model_family.value} is published as experimental "
                    "and should be treated as a challenge path rather than a default release baseline."
                ),
            )
        )
    return ModelFamilyComparisonPacket(
        scenario_id=request.scenario.scenario_id,
        run_mode=request.run_mode,
        fit_for_purpose=request.fit_for_purpose,
        comparison_profile_id=comparison_profile.profile_id,
        base_model_family=request.base_model_family,
        candidate_model_family=request.candidate_model_family,
        comparison_outcome=comparison_outcome,
        base_fit_assessment=base_fit_assessment,
        candidate_fit_assessment=candidate_fit_assessment,
        comparison=comparison,
        base_surface_samples=_surface_samples_from_result(base_result, request.max_surface_samples),
        candidate_surface_samples=_surface_samples_from_result(candidate_result, request.max_surface_samples),
        summary_lines=summary_lines,
        dominant_delta_lines=dominant_delta_lines,
        outcome_lines=outcome_lines,
        base_benchmark_reference_lines=base_benchmark_reference_lines,
        candidate_benchmark_reference_lines=candidate_benchmark_reference_lines,
        base_equation_lines=base_equation_lines,
        candidate_equation_lines=candidate_equation_lines,
        recommended_actions=recommended_actions,
        packet_template_used=comparison_profile.packet_template,
        brief_template_used=comparison_profile.brief_template,
        provenance=provenance_builder.bundle(_collect_source_references(request.scenario, candidate_result)),
        limitations=limitations,
    )



def build_model_family_comparison_brief(
    request: BuildModelFamilyComparisonBriefRequest,
) -> ModelFamilyComparisonBrief:
    packet = request.comparison_packet
    summary_lines = list(packet.summary_lines)
    summary_lines.extend("Dominant delta: " + line for line in packet.dominant_delta_lines)
    summary_lines.extend(
        "Base equation trace: " + line for line in packet.base_equation_lines
    )
    summary_lines.extend(
        "Candidate equation trace: " + line for line in packet.candidate_equation_lines
    )
    return ModelFamilyComparisonBrief(
        comparison_packet_id=packet.comparison_packet_id,
        scenario_id=packet.scenario_id,
        run_mode=packet.run_mode,
        fit_for_purpose=packet.fit_for_purpose,
        comparison_profile_id=packet.comparison_profile_id,
        base_model_family=packet.base_model_family,
        candidate_model_family=packet.candidate_model_family,
        comparison_outcome=packet.comparison_outcome,
        summary_lines=summary_lines,
        dominant_delta_lines=packet.dominant_delta_lines,
        outcome_lines=packet.outcome_lines,
        recommended_actions=packet.recommended_actions,
        base_equation_lines=packet.base_equation_lines,
        candidate_equation_lines=packet.candidate_equation_lines,
        brief_template_used=packet.brief_template_used,
        limitations=packet.limitations,
    )



def _resolve_model_family_comparison_profile_from_packet(
    packet: ModelFamilyComparisonPacket,
    defaults_registry: DefaultsRegistry,
) -> ModelFamilyComparisonProfile:
    profile = defaults_registry.model_family_comparison_profile(packet.comparison_profile_id)
    if profile is None:
        raise FateValidationError(
            code="unknown_model_family_comparison_profile",
            message=(
                f"No governed model-family comparison profile is declared for "
                f"{packet.comparison_profile_id}."
            ),
            suggestion="Inspect defaults://model-family-comparison-profiles and use a declared profile id.",
        )
    if (
        profile.base_model_family != packet.base_model_family
        or profile.candidate_model_family != packet.candidate_model_family
    ):
        raise FateValidationError(
            code="model_family_comparison_profile_packet_mismatch",
            message=(
                f"Comparison packet {packet.comparison_packet_id} does not match governed profile "
                f"{profile.profile_id}."
            ),
            suggestion="Rebuild the comparison packet with a profile that matches the model-family pair.",
        )
    return profile



def _model_family_comparison_review_evidence_line(
    field_name: str,
    review_packet: ModelFamilyComparisonReviewPacket,
) -> str | None:
    packet = review_packet.comparison_packet
    if field_name == "comparison_outcome":
        return f"Comparison outcome: {packet.comparison_outcome.value}."
    if field_name == "comparison_profile_id":
        return f"Comparison profile: {packet.comparison_profile_id}."
    if field_name == "dominant_delta_lines" and review_packet.dominant_delta_lines:
        return "Dominant deltas: " + " | ".join(review_packet.dominant_delta_lines)
    if field_name == "base_fit_verdict":
        return (
            f"Base fit verdict: {packet.base_fit_assessment.verdict} "
            f"(score={packet.base_fit_assessment.fit_score:.2f})."
        )
    if field_name == "candidate_fit_verdict":
        return (
            f"Candidate fit verdict: {packet.candidate_fit_assessment.verdict} "
            f"(score={packet.candidate_fit_assessment.fit_score:.2f})."
        )
    if field_name == "base_applicability_lines" and review_packet.base_applicability_lines:
        return "Base applicability: " + " | ".join(review_packet.base_applicability_lines)
    if field_name == "candidate_applicability_lines" and review_packet.candidate_applicability_lines:
        return "Candidate applicability: " + " | ".join(review_packet.candidate_applicability_lines)
    if field_name == "base_benchmark_reference_lines" and review_packet.base_benchmark_reference_lines:
        return "Base benchmark context: " + " | ".join(review_packet.base_benchmark_reference_lines)
    if field_name == "candidate_benchmark_reference_lines" and review_packet.candidate_benchmark_reference_lines:
        return "Candidate benchmark context: " + " | ".join(review_packet.candidate_benchmark_reference_lines)
    if field_name == "base_equation_lines" and review_packet.base_equation_lines:
        return "Base equation trace: " + " | ".join(review_packet.base_equation_lines)
    if field_name == "candidate_equation_lines" and review_packet.candidate_equation_lines:
        return "Candidate equation trace: " + " | ".join(review_packet.candidate_equation_lines)
    if field_name == "limitations" and review_packet.limitations:
        return "Limitations: " + "; ".join(note.message for note in review_packet.limitations)
    if field_name == "run_mode":
        return f"Run mode: {packet.run_mode.value}."
    if field_name == "fit_for_purpose":
        return f"Fit-for-purpose: {packet.fit_for_purpose.value}."
    return None



def _build_model_family_comparison_review_checklist(
    comparison_profile: ModelFamilyComparisonProfile,
    review_packet: ModelFamilyComparisonReviewPacket,
) -> list[ModelFamilyComparisonReviewChecklistItem]:
    checklist_items: list[ModelFamilyComparisonReviewChecklistItem] = []
    for template in comparison_profile.review_checklist:
        unknown_fields = sorted(
            field
            for field in template.evidence_hint_fields
            if field not in MODEL_FAMILY_COMPARISON_REVIEW_EVIDENCE_FIELDS
        )
        if unknown_fields:
            raise FateValidationError(
                code="invalid_model_family_comparison_review_checklist_field",
                message=(
                    f"Comparison profile {comparison_profile.profile_id} declares unknown "
                    f"review checklist evidence fields: {unknown_fields}."
                ),
                suggestion="Limit review checklist evidence_hint_fields to fields exposed by the comparison review packet builder.",
                details={"unknownEvidenceHintFields": unknown_fields},
            )
        evidence_lines = []
        for field_name in template.evidence_hint_fields:
            line = _model_family_comparison_review_evidence_line(field_name, review_packet)
            if line and line not in evidence_lines:
                evidence_lines.append(line)
        checklist_items.append(
            ModelFamilyComparisonReviewChecklistItem(
                code=template.code,
                prompt=template.prompt,
                rationale=template.rationale,
                status="ready_for_assessor_confirmation" if evidence_lines else "attention_required",
                evidence_lines=evidence_lines,
            )
        )
    return checklist_items



def _model_family_comparison_review_checks(
    packet: ModelFamilyComparisonPacket,
) -> list[ModelFamilyComparisonReviewCheck]:
    candidate_is_experimental = packet.candidate_model_family.value in EXPERIMENTAL_MODEL_FAMILIES
    candidate_experimental_disclosed = any(
        note.code == "experimental_candidate_model_family" for note in packet.limitations
    )
    return [
        ModelFamilyComparisonReviewCheck(
            code="comparison_profile_declared",
            passed=bool(packet.comparison_profile_id),
            message=f"Governed comparison profile {packet.comparison_profile_id} is recorded on the packet.",
        ),
        ModelFamilyComparisonReviewCheck(
            code="fit_assessments_match_packet",
            passed=(
                packet.base_fit_assessment.model_family == packet.base_model_family
                and packet.candidate_fit_assessment.model_family == packet.candidate_model_family
            ),
            message="Base and candidate fit assessments match the declared model-family pair.",
        ),
        ModelFamilyComparisonReviewCheck(
            code="surface_deltas_available",
            passed=bool(packet.comparison.surface_deltas),
            message=(
                f"Comparison packet records {len(packet.comparison.surface_deltas)} surface deltas for assessor review."
            ),
        ),
        ModelFamilyComparisonReviewCheck(
            code="benchmark_and_equation_context_available",
            passed=bool(
                packet.base_benchmark_reference_lines
                and packet.candidate_benchmark_reference_lines
                and packet.base_equation_lines
                and packet.candidate_equation_lines
            ),
            message="Benchmark context and equation traces are available for both model families.",
        ),
        ModelFamilyComparisonReviewCheck(
            code="experimental_candidate_disclosed",
            passed=(not candidate_is_experimental) or candidate_experimental_disclosed,
            message=(
                "Experimental candidate-model-family status is explicitly disclosed."
                if candidate_is_experimental
                else "Candidate model family is not published as experimental."
            ),
        ),
    ]



def _model_family_comparison_review_status(
    comparison_profile: ModelFamilyComparisonProfile,
    packet: ModelFamilyComparisonPacket,
    checks: list[ModelFamilyComparisonReviewCheck],
) -> tuple[str, list[str], list[str], list[str], list[str]]:
    triggered_check_codes = [check.code for check in checks if not check.passed]
    governing_rule_lines: list[str] = []
    status_rule_lines: list[str] = []
    recommended_actions = list(packet.recommended_actions)
    requires_attention = False

    if packet.comparison_outcome in comparison_profile.ready_comparison_outcomes:
        governing_rule_lines.append(
            f"Comparison outcome {packet.comparison_outcome.value} is inside the governed ready set."
        )
    if packet.comparison_outcome in comparison_profile.attention_outcomes:
        requires_attention = True
        governing_rule_lines.append(
            f"Attention is required because comparison outcome {packet.comparison_outcome.value} is governed as attention-worthy."
        )
    if (
        comparison_profile.attention_if_candidate_experimental
        and packet.candidate_model_family.value in EXPERIMENTAL_MODEL_FAMILIES
    ):
        requires_attention = True
        governing_rule_lines.append(
            f"Attention is required because candidate model family {packet.candidate_model_family.value} is published as experimental."
        )
    if comparison_profile.attention_if_any_checks_fail and triggered_check_codes:
        requires_attention = True
        status_rule_lines.append(
            "Attention required because governed comparison-review checks failed: "
            + ", ".join(triggered_check_codes)
            + "."
        )
    if not status_rule_lines:
        status_rule_lines.append(
            "Ready because comparison-review checks and governed status rules did not trigger additional attention."
            if not requires_attention
            else "Attention required because governed comparison-review policy was triggered."
        )
    if requires_attention:
        attention_note = (
            "Keep the comparison in assessor-facing attention status until the governed divergence, experimental-family, or packet-check concerns are resolved."
        )
        if attention_note not in recommended_actions:
            recommended_actions.append(attention_note)
    else:
        ready_note = "Comparison is ready for assessor-facing review within the governed comparison profile."
        if ready_note not in recommended_actions:
            recommended_actions.append(ready_note)
    return (
        "model_family_comparison_review_attention_needed"
        if requires_attention
        else "ready_for_model_family_comparison_review",
        triggered_check_codes,
        governing_rule_lines,
        status_rule_lines,
        recommended_actions,
    )



def preview_model_family_comparison_review(
    request: PreviewModelFamilyComparisonReviewRequest,
    provenance_builder: ProvenanceBuilder,
) -> ModelFamilyComparisonReviewPreview:
    packet = request.comparison_packet
    comparison_profile = _resolve_model_family_comparison_profile_from_packet(
        packet,
        provenance_builder.defaults_registry,
    )
    checks = _model_family_comparison_review_checks(packet)
    review_status, triggered_check_codes, governing_rule_lines, status_rule_lines, recommended_actions = (
        _model_family_comparison_review_status(
            comparison_profile,
            packet,
            checks,
        )
    )
    return ModelFamilyComparisonReviewPreview(
        comparison_packet_id=packet.comparison_packet_id,
        scenario_id=packet.scenario_id,
        comparison_profile_id=packet.comparison_profile_id,
        comparison_outcome=packet.comparison_outcome,
        review_status=review_status,
        triggered_check_codes=triggered_check_codes,
        governing_rule_lines=governing_rule_lines,
        status_rule_lines=status_rule_lines,
        outcome_lines=packet.outcome_lines,
        recommended_actions=recommended_actions,
    )



def build_model_family_comparison_review_packet(
    request: BuildModelFamilyComparisonReviewPacketRequest,
    provenance_builder: ProvenanceBuilder,
) -> ModelFamilyComparisonReviewPacket:
    packet = request.comparison_packet
    comparison_profile = _resolve_model_family_comparison_profile_from_packet(
        packet,
        provenance_builder.defaults_registry,
    )
    review_preview = preview_model_family_comparison_review(
        PreviewModelFamilyComparisonReviewRequest(comparison_packet=packet),
        provenance_builder,
    )
    checks = _model_family_comparison_review_checks(packet)
    summary_lines = [
        comparison_profile.review_packet_template
        or "Build a governed assessor-facing review packet for an Environmental Fate MCP model-family comparison.",
        (
            f"Comparison review packet covers {packet.base_model_family.value} -> "
            f"{packet.candidate_model_family.value} for scenario {packet.scenario_id}."
        ),
        f"Comparison outcome: {packet.comparison_outcome.value}.",
        f"Review status: {review_preview.review_status}.",
    ]
    if comparison_profile.applicability_note:
        summary_lines.append(comparison_profile.applicability_note)
    review_packet = ModelFamilyComparisonReviewPacket(
        comparison_packet_id=packet.comparison_packet_id,
        scenario_id=packet.scenario_id,
        comparison_profile_id=packet.comparison_profile_id,
        base_model_family=packet.base_model_family,
        candidate_model_family=packet.candidate_model_family,
        comparison_outcome=packet.comparison_outcome,
        review_status=review_preview.review_status,
        review_preview=review_preview,
        comparison_packet=packet,
        checks=checks,
        summary_lines=summary_lines,
        dominant_delta_lines=packet.dominant_delta_lines,
        outcome_lines=review_preview.outcome_lines,
        recommended_actions=review_preview.recommended_actions,
        base_applicability_lines=packet.base_fit_assessment.applicability_lines,
        candidate_applicability_lines=packet.candidate_fit_assessment.applicability_lines,
        base_benchmark_reference_lines=packet.base_benchmark_reference_lines,
        candidate_benchmark_reference_lines=packet.candidate_benchmark_reference_lines,
        base_equation_lines=packet.base_equation_lines,
        candidate_equation_lines=packet.candidate_equation_lines,
        review_template_used=comparison_profile.review_packet_template,
        provenance=provenance_builder.bundle(packet.provenance.source_references),
        limitations=packet.limitations,
    )
    review_packet.review_checklist = _build_model_family_comparison_review_checklist(
        comparison_profile,
        review_packet,
    )
    return review_packet



def build_model_family_comparison_review_brief(
    request: BuildModelFamilyComparisonReviewBriefRequest,
    provenance_builder: ProvenanceBuilder,
) -> ModelFamilyComparisonReviewBrief:
    review_packet = request.review_packet
    comparison_profile = _resolve_model_family_comparison_profile_from_packet(
        review_packet.comparison_packet,
        provenance_builder.defaults_registry,
    )
    passed_check_count = sum(1 for check in review_packet.checks if check.passed)
    brief_lines = [
        comparison_profile.review_brief_template
        or "Summarize whether the model-family comparison is ready for assessor-facing review."
    ]
    brief_lines.extend(review_packet.summary_lines)
    brief_lines.extend("Dominant delta: " + line for line in review_packet.dominant_delta_lines)
    brief_lines.extend("Base applicability: " + line for line in review_packet.base_applicability_lines)
    brief_lines.extend("Candidate applicability: " + line for line in review_packet.candidate_applicability_lines)
    brief_lines.extend(
        "Base benchmark context: " + line for line in review_packet.base_benchmark_reference_lines
    )
    brief_lines.extend(
        "Candidate benchmark context: " + line for line in review_packet.candidate_benchmark_reference_lines
    )
    brief_lines.extend("Base equation trace: " + line for line in review_packet.base_equation_lines)
    brief_lines.extend("Candidate equation trace: " + line for line in review_packet.candidate_equation_lines)
    for item in review_packet.review_checklist:
        brief_lines.append(f"[{item.status}] {item.prompt}")
        if item.evidence_lines:
            brief_lines.append("Evidence: " + " | ".join(item.evidence_lines))
    return ModelFamilyComparisonReviewBrief(
        review_packet_id=review_packet.review_packet_id,
        comparison_packet_id=review_packet.comparison_packet_id,
        scenario_id=review_packet.scenario_id,
        comparison_profile_id=review_packet.comparison_profile_id,
        base_model_family=review_packet.base_model_family,
        candidate_model_family=review_packet.candidate_model_family,
        comparison_outcome=review_packet.comparison_outcome,
        review_status=review_packet.review_status,
        passed_check_count=passed_check_count,
        total_check_count=len(review_packet.checks),
        review_template_used=comparison_profile.review_brief_template,
        checklist_items=review_packet.review_checklist,
        brief_lines=brief_lines,
        dominant_delta_lines=review_packet.dominant_delta_lines,
        outcome_lines=review_packet.outcome_lines,
        recommended_actions=review_packet.recommended_actions,
        base_applicability_lines=review_packet.base_applicability_lines,
        candidate_applicability_lines=review_packet.candidate_applicability_lines,
        base_benchmark_reference_lines=review_packet.base_benchmark_reference_lines,
        candidate_benchmark_reference_lines=review_packet.candidate_benchmark_reference_lines,
        base_equation_lines=review_packet.base_equation_lines,
        candidate_equation_lines=review_packet.candidate_equation_lines,
        limitations=review_packet.limitations,
    )


