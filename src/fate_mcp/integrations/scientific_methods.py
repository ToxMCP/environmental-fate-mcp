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


from .common import _advective_post_release_directionality_support_ready, _advective_post_release_late_recovery_support_ready, _advective_post_release_pace_directionality_support_ready, _advective_post_release_pace_support_ready, _advective_post_release_recovery_support_ready, _advective_post_release_regime_support_ready, _advective_transition_reference_support_ready, _advective_transport_authority_support_ready, _merge_source_references, _scientific_methods_applicability_lines, _scientific_methods_benchmark_lines, _scientific_methods_claim_summaries, _scientific_methods_highlighted_claim_grounding_lines, _scientific_methods_highlighted_claim_summaries, _scientific_methods_promotion_blockers, _scientific_methods_promotion_status, _scientific_methods_recommended_action_summaries, _scientific_methods_reference_case_concept_summary_lines, _scientific_methods_reference_case_grounding_lines, _scientific_methods_source_grounding_lines, _scientific_methods_support_strength_lines

def build_scientific_methods_dossier(
    request: BuildScientificMethodsDossierRequest,
    provenance_builder: ProvenanceBuilder,
) -> ScientificMethodsDossier:
    defaults_registry = provenance_builder.defaults_registry
    claim_summaries = _scientific_methods_claim_summaries(
        defaults_registry,
        request.model_family,
        request.run_mode_filter,
    )
    applicability_lines = _scientific_methods_applicability_lines(
        defaults_registry,
        request.model_family,
    )
    source_grounding_lines = _scientific_methods_source_grounding_lines(claim_summaries)
    highlighted_claim_grounding_lines = _scientific_methods_highlighted_claim_grounding_lines(
        claim_summaries
    )
    highlighted_claim_summaries = _scientific_methods_highlighted_claim_summaries(
        defaults_registry,
        claim_summaries,
        request.model_family,
    )
    near_parity_transition_count = sum(
        1
        for item in highlighted_claim_summaries
        if item.loss_regime_stability_status == "near_parity_transition"
    )
    stable_loss_regime_count = sum(
        1
        for item in highlighted_claim_summaries
        if item.loss_regime_stability_status == "stable_loss_regime"
    )
    boundary_sensitive_transport_count = sum(
        1
        for item in highlighted_claim_summaries
        if item.transport_regime_stability_status == "boundary_sensitive_transport_regime"
    )
    stable_transport_regime_count = sum(
        1
        for item in highlighted_claim_summaries
        if item.transport_regime_stability_status
        in {"storage_dominant_transport_regime", "flow_through_transport_regime"}
    )
    boundary_sensitive_post_release_count = sum(
        1
        for item in highlighted_claim_summaries
        if item.transport_regime_stability_status
        == "boundary_sensitive_post_release_recovery_regime"
    )
    boundary_sensitive_post_release_pace_count = sum(
        1
        for item in highlighted_claim_summaries
        if item.transport_regime_stability_status
        == "boundary_sensitive_post_release_recovery_pace"
    )
    stable_post_release_count = sum(
        1
        for item in highlighted_claim_summaries
        if item.transport_regime_stability_status == "post_release_flushing_recovery_regime"
    )
    multi_jurisdiction_claim_count = sum(
        1
        for item in claim_summaries
        if item.external_corroboration_status
        == ScientificExternalCorroborationStatus.MULTI_OFFICIAL_MULTI_JURISDICTION
    )
    reference_case_grounding_lines = _scientific_methods_reference_case_grounding_lines(
        defaults_registry,
        claim_summaries,
    )
    reference_case_concept_lines = _scientific_methods_reference_case_concept_summary_lines(
        claim_summaries
    )
    benchmark_reference_lines, edge_condition_lines = _scientific_methods_benchmark_lines(claim_summaries)
    support_strength_lines = _scientific_methods_support_strength_lines(
        claim_summaries,
        request.model_family,
    )
    mandatory_claim_count = sum(1 for item in claim_summaries if item.mandatory_for_release)
    covered_mandatory_claim_count = sum(
        1 for item in claim_summaries if item.mandatory_for_release and item.covered
    )
    uncovered_mandatory_claim_count = mandatory_claim_count - covered_mandatory_claim_count
    source_references = _merge_source_references(
        *[claim_summary.source_references for claim_summary in claim_summaries]
    )
    filtered_run_mode = (
        f"/{request.run_mode_filter.value}" if request.run_mode_filter is not None else ""
    )
    summary_lines = [
        f"Scientific methods dossier for {request.model_family.value}{filtered_run_mode}.",
        (
            f"Mandatory scientific validation claims covered: {covered_mandatory_claim_count}/"
            f"{mandatory_claim_count}."
        ),
        (
            f"Total governed claims in scope: {len(claim_summaries)} with "
            f"{sum(1 for item in claim_summaries if item.covered)} currently benchmark-covered."
        ),
    ]
    summary_lines.extend(
        "Highlighted claim grounding: " + line for line in highlighted_claim_grounding_lines[:2]
    )
    if highlighted_claim_summaries:
        summary_lines.append(
            "Highlighted regime stability: "
            + f"{near_parity_transition_count} near-parity transition claim(s), "
            + f"{stable_loss_regime_count} stable-regime claim(s)."
        )
        summary_lines.append(
            "Highlighted transport stability: "
            + f"{boundary_sensitive_transport_count} boundary-sensitive transport claim(s), "
            + f"{stable_transport_regime_count} stable transport-regime claim(s)."
        )
        summary_lines.append(
            "Post-release regime stability: "
            + f"{boundary_sensitive_post_release_count} boundary-sensitive recovery claim(s), "
            + f"{boundary_sensitive_post_release_pace_count} half-recovery pace claim(s), "
            + f"{stable_post_release_count} stable post-release recovery claim(s)."
        )
    summary_lines.append(
        "External corroboration breadth: "
        + f"{multi_jurisdiction_claim_count}/{len(claim_summaries)} claim(s) carry multi-official multi-jurisdiction grounding."
    )
    claim_summaries_by_id = {item.claim_id: item for item in claim_summaries}
    if (
        request.model_family.value == "advective_screening_mass_balance"
        and _advective_transport_authority_support_ready(claim_summaries_by_id)
    ):
        summary_lines.append(
            "Transport authority support: reference-style bounded-transport anchors now span stable flow-through, boundary-sensitive intermediate, and stable storage-dominant regimes."
        )
    if (
        request.model_family.value == "advective_screening_mass_balance"
        and _advective_transition_reference_support_ready(claim_summaries_by_id)
    ):
        summary_lines.append(
            "Transport transition support: reference-style transition anchors and flip-side sensitivity anchors are present around the near-parity degradation-versus-clearance boundary."
        )
    if (
        request.model_family.value == "advective_screening_mass_balance"
        and _advective_post_release_recovery_support_ready(claim_summaries_by_id)
    ):
        summary_lines.append(
            "Post-release recovery support: reference-style bucket anchors show release-stop mass draining with explicit degraded-versus-advected recovery accounting after active emission ends."
        )
    if (
        request.model_family.value == "advective_screening_mass_balance"
        and _advective_post_release_regime_support_ready(claim_summaries_by_id)
    ):
        summary_lines.append(
            "Post-release regime support: stable sub-boundary, boundary-sensitive, and flushing-dominant recovery windows are anchored around the one-turnover flushing threshold after release stop."
        )
    if (
        request.model_family.value == "advective_screening_mass_balance"
        and _advective_post_release_directionality_support_ready(claim_summaries_by_id)
    ):
        summary_lines.append(
            "Post-release directionality support: same-chemistry sub-boundary, boundary, and beyond-boundary anchors show retained release-stop mass crossing the one-turnover anchor in the governed direction as the recovery window extends."
        )
    if (
        request.model_family.value == "advective_screening_mass_balance"
        and _advective_post_release_pace_support_ready(claim_summaries_by_id)
    ):
        summary_lines.append(
            "Post-release pace support: same-chemistry pre-half, half-recovery, and beyond-half anchors show the governed combined-loss half-recovery timescale directly rather than inferring recovery pace from the one-turnover boundary alone."
        )
    if (
        request.model_family.value == "advective_screening_mass_balance"
        and _advective_post_release_pace_directionality_support_ready(claim_summaries_by_id)
    ):
        summary_lines.append(
            "Post-release pace directionality support: same-chemistry pre-half, half-boundary, beyond-half, and extended-beyond-half anchors show retained release-stop mass crossing and moving materially below the 50% half-recovery anchor in the governed direction as the recovery window extends."
        )
    if (
        request.model_family.value == "advective_screening_mass_balance"
        and _advective_post_release_late_recovery_support_ready(claim_summaries_by_id)
    ):
        summary_lines.append(
            "Late recovery regime support: exceptional beyond-half anchors show the deep depletion authority layer actively distinguishing stable late-recovery from mere sub-half-recovery windows."
        )
    flip_directionality_claim = next(
        (
            item
            for item in claim_summaries
            if item.claim_id == "advective_loss_regime_flip_directionality_v1"
        ),
        None,
    )
    if flip_directionality_claim is not None and flip_directionality_claim.covered:
        summary_lines.append(
            "Transition sensitivity support: explicit flip-side sensitivity anchors are present around the near-parity degradation-versus-clearance boundary."
        )
    if request.model_family.value in EXPERIMENTAL_MODEL_FAMILIES:
        summary_lines.append(
            "This model family remains experimental and should be challenged with extra reviewer scrutiny even when its mandatory claims are covered."
        )
    recommended_action_summaries = _scientific_methods_recommended_action_summaries(
        defaults_registry,
        claim_summaries,
        highlighted_claim_summaries,
        request.model_family,
        uncovered_mandatory_claim_count,
    )
    (
        promotion_status,
        blocking_action_count,
        strengthening_action_count,
    ) = _scientific_methods_promotion_status(recommended_action_summaries)
    (
        promotion_blocker_claim_ids,
        promotion_blocker_summaries,
    ) = _scientific_methods_promotion_blockers(recommended_action_summaries)
    recommended_actions = [item.action for item in recommended_action_summaries]
    summary_lines.append(
        "Promotion status: "
        + promotion_status.value
        + f" ({blocking_action_count} blocking actions, {strengthening_action_count} strengthening actions)."
    )
    summary_lines.extend(
        "Promotion blocker: " + item.action for item in promotion_blocker_summaries[:2]
    )

    limitations = [
        LimitationNote(
            code="claim_coverage_not_regulatory_acceptance",
            message=(
                "Scientific claim coverage documents governed benchmark and reference-case support only and is not a statement of regulator acceptance or submission approval."
            ),
        )
    ]
    if request.model_family.value in EXPERIMENTAL_MODEL_FAMILIES:
        limitations.append(
            LimitationNote(
                code="experimental_model_family",
                message=(
                    "This dossier covers an experimental model family that remains non-default pending broader validation."
                ),
            )
        )

    return ScientificMethodsDossier(
        model_family=request.model_family,
        run_mode_filter=request.run_mode_filter,
        promotion_status=promotion_status,
        blocking_action_count=blocking_action_count,
        strengthening_action_count=strengthening_action_count,
        claim_count=len(claim_summaries),
        mandatory_claim_count=mandatory_claim_count,
        covered_mandatory_claim_count=covered_mandatory_claim_count,
        uncovered_mandatory_claim_count=uncovered_mandatory_claim_count,
        claim_summaries=claim_summaries,
        highlighted_claim_summaries=highlighted_claim_summaries,
        summary_lines=summary_lines,
        applicability_lines=applicability_lines,
        source_grounding_lines=source_grounding_lines,
        highlighted_claim_grounding_lines=highlighted_claim_grounding_lines,
        reference_case_grounding_lines=reference_case_grounding_lines,
        reference_case_concept_lines=reference_case_concept_lines,
        benchmark_reference_lines=benchmark_reference_lines,
        support_strength_lines=support_strength_lines,
        edge_condition_lines=edge_condition_lines,
        promotion_blocker_claim_ids=promotion_blocker_claim_ids,
        promotion_blocker_summaries=promotion_blocker_summaries,
        recommended_action_summaries=recommended_action_summaries,
        recommended_actions=recommended_actions,
        provenance=provenance_builder.bundle(source_references),
        limitations=limitations,
    )



def build_scientific_methods_dossier_brief(
    request: BuildScientificMethodsDossierBriefRequest,
) -> ScientificMethodsDossierBrief:
    dossier = request.dossier
    highlighted_claim_ids = [item.claim_id for item in dossier.highlighted_claim_summaries]
    summary_lines = list(dossier.summary_lines)
    summary_lines.extend("Source grounding: " + line for line in dossier.source_grounding_lines[:2])
    summary_lines.extend(
        "Highlighted claim grounding: " + line
        for line in dossier.highlighted_claim_grounding_lines[:2]
    )
    for item in dossier.highlighted_claim_summaries[:2]:
        summary_lines.append(
            f"Highlighted claim [{item.challenge_status.value}]: {item.display_name} ({item.support_strength.value})."
        )
        summary_lines.append(
            "Claim regime stability: "
            + item.loss_regime_stability_status
            + "."
        )
        summary_lines.extend(
            "Claim regime context: " + line
            for line in item.loss_regime_stability_lines[:1]
        )
        summary_lines.append(
            "Claim transport stability: "
            + item.transport_regime_stability_status
            + "."
        )
        summary_lines.extend(
            "Claim transport context: " + line
            for line in item.transport_regime_stability_lines[:1]
        )
        summary_lines.append(
            "Claim corroboration status: "
            + item.external_corroboration_status.value
            + f" ({item.external_corroboration_source_count} official sources"
            + (
                f"; jurisdictions: {', '.join(item.external_corroboration_jurisdictions[:3])}"
                if item.external_corroboration_jurisdictions
                else ""
            )
            + ")."
        )
        summary_lines.extend(
            "Claim corroboration: " + line for line in item.external_corroboration_lines[:1]
        )
        summary_lines.extend(
            "Claim corroboration action: " + line
            for line in item.external_corroboration_actions[:1]
        )
        summary_lines.extend("Claim challenge: " + line for line in item.challenge_lines[:1])
    summary_lines.extend(
        "Reference-case grounding: " + line for line in dossier.reference_case_grounding_lines[:2]
    )
    summary_lines.extend(
        "Reference-case concept: " + line for line in dossier.reference_case_concept_lines[:2]
    )
    summary_lines.extend("Support strength: " + line for line in dossier.support_strength_lines[:2])
    summary_lines.extend("Benchmark context: " + line for line in dossier.benchmark_reference_lines)
    if dossier.edge_condition_lines:
        summary_lines.append("Edge anchors: " + " | ".join(dossier.edge_condition_lines[:3]))
    summary_lines.extend(
        "Recommended action: "
        + f"[{item.promotion_impact.value}/{item.priority.value}/{item.action_class}] "
        + item.action
        for item in dossier.recommended_action_summaries[:2]
    )
    summary_lines.extend(
        "Promotion blocker: " + item.action for item in dossier.promotion_blocker_summaries[:2]
    )
    return ScientificMethodsDossierBrief(
        dossier_id=dossier.dossier_id,
        model_family=dossier.model_family,
        run_mode_filter=dossier.run_mode_filter,
        promotion_status=dossier.promotion_status,
        blocking_action_count=dossier.blocking_action_count,
        strengthening_action_count=dossier.strengthening_action_count,
        claim_count=dossier.claim_count,
        mandatory_claim_count=dossier.mandatory_claim_count,
        covered_mandatory_claim_count=dossier.covered_mandatory_claim_count,
        uncovered_mandatory_claim_count=dossier.uncovered_mandatory_claim_count,
        highlighted_claim_ids=highlighted_claim_ids,
        highlighted_claim_summaries=dossier.highlighted_claim_summaries,
        summary_lines=summary_lines,
        applicability_lines=dossier.applicability_lines,
        source_grounding_lines=dossier.source_grounding_lines,
        highlighted_claim_grounding_lines=dossier.highlighted_claim_grounding_lines,
        reference_case_grounding_lines=dossier.reference_case_grounding_lines,
        reference_case_concept_lines=dossier.reference_case_concept_lines,
        benchmark_reference_lines=dossier.benchmark_reference_lines,
        support_strength_lines=dossier.support_strength_lines,
        promotion_blocker_claim_ids=dossier.promotion_blocker_claim_ids,
        promotion_blocker_summaries=dossier.promotion_blocker_summaries,
        recommended_action_summaries=dossier.recommended_action_summaries,
        recommended_actions=dossier.recommended_actions,
        limitations=dossier.limitations,
    )


