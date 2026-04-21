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


from .common import _collect_source_references, _merge_limitations, _scientific_unsuitability_lines

def _probabilistic_review_checks(
    result: ProbabilisticConcentrationResult,
    defaults_registry: DefaultsRegistry,
) -> list[ProbabilisticReviewCheck]:
    policy = defaults_registry.probabilistic_review_policy()
    expected_surface_count = len(result.surface_summaries)
    seeded = result.sampling_seed is not None
    percentiles_should_be_present = (
        result.completed_iteration_count
        >= policy.minimum_completed_iterations_for_percentiles
    )
    percentile_surface_parity = (
        len(result.median_surfaces) == expected_surface_count
        and (
            (
                len(result.p90_surfaces) == expected_surface_count
                and len(result.p95_surfaces) == expected_surface_count
                and all(summary.p90_value is not None for summary in result.surface_summaries)
                and all(summary.p95_value is not None for summary in result.surface_summaries)
            )
            if percentiles_should_be_present
            else (
                len(result.p90_surfaces) == 0
                and len(result.p95_surfaces) == 0
                and all(summary.p90_value is None for summary in result.surface_summaries)
                and all(summary.p95_value is None for summary in result.surface_summaries)
            )
        )
    )
    failed_iteration_fraction = (
        result.failed_iteration_count / result.iteration_count if result.iteration_count else 0.0
    )
    checks = [
        ProbabilisticReviewCheck(
            code="probabilistic_iterations_completed",
            passed=result.completed_iteration_count > 0,
            message=(
                f"Completed {result.completed_iteration_count} probabilistic iterations out of "
                f"{result.iteration_count} requested."
            ),
        ),
        ProbabilisticReviewCheck(
            code="probabilistic_percentile_surface_parity",
            passed=percentile_surface_parity,
            message=(
                "Percentile surfaces are either aligned with the probabilistic surface summary inventory "
                "or explicitly suppressed under the governed minimum-iterations policy."
            ),
        ),
        ProbabilisticReviewCheck(
            code="probabilistic_sampling_seed_recorded",
            passed=seeded,
            message=(
                f"Sampling seed {'recorded' if seeded else 'not recorded'} for probabilistic execution."
            ),
        ),
        ProbabilisticReviewCheck(
            code="probabilistic_failed_iteration_fraction_within_ready_threshold",
            passed=failed_iteration_fraction <= policy.max_failed_iteration_fraction_for_ready_review,
            message=(
                f"Probabilistic execution recorded {result.failed_iteration_count} failed iterations "
                f"({failed_iteration_fraction:.1%} of requested runs)."
            ),
        ),
    ]
    return checks



def build_probabilistic_review_packet(
    request: BuildProbabilisticReviewPacketRequest,
    provenance_builder: ProvenanceBuilder,
) -> ProbabilisticReviewPacket:
    result = request.result
    policy = provenance_builder.defaults_registry.probabilistic_review_policy()
    checks = _probabilistic_review_checks(result, provenance_builder.defaults_registry)
    blockers = []
    if result.completed_iteration_count == 0:
        blockers.append("Probabilistic execution produced no completed iterations.")
    failed_iteration_fraction = (
        result.failed_iteration_count / result.iteration_count if result.iteration_count else 0.0
    )
    review_status = (
        "ready_for_assessor_review"
        if (
            not blockers
            and all(check.passed for check in checks)
            and failed_iteration_fraction <= policy.max_failed_iteration_fraction_for_ready_review
        )
        else "probabilistic_review_attention_needed"
    )
    percentile_surface_lines = [
        (
            f"{summary.medium.value}/{summary.compartment.value}: median={summary.median_value:.6g} "
            + (
                f"{summary.concentration_unit}, p90={summary.p90_value:.6g}, p95={summary.p95_value:.6g}, "
                f"p95-minus-median={summary.absolute_p95_minus_median:.6g}."
                if summary.p90_value is not None
                and summary.p95_value is not None
                and summary.absolute_p95_minus_median is not None
                else (
                    f"{summary.concentration_unit}, p90/p95 suppressed because completed iterations "
                    f"remained below the governed minimum of "
                    f"{policy.minimum_completed_iterations_for_percentiles}."
                )
            )
        )
        for summary in result.surface_summaries[:6]
    ]
    sensitivity_lines = [
        "Sampled uncertainty drivers: "
        + ", ".join(result.dominant_uncertainty_drivers)
        + "."
        if result.dominant_uncertainty_drivers
        else "Sampled uncertainty drivers were not recorded."
    ]
    failed_iteration_lines = [
        f"{reason}: {count} failed iterations."
        for reason, count in sorted(result.run_summary.failed_iteration_reasons.items())
    ]
    scientific_unsuitability_lines = _scientific_unsuitability_lines(
        result.run_summary.escalation_concerns
    )
    recommended_actions = []
    if result.failed_iteration_count > 0:
        recommended_actions.append(
            "Review failed iteration reasons before reusing percentile surfaces in decision-facing workflows."
        )
        recommended_actions.append(
            "Carry the failed-iteration truncation note forward so reviewers know percentile summaries were computed from successful runs only."
        )
    if result.sampling_seed is None:
        recommended_actions.append(
            "Record an explicit sampling seed for strict reproducibility when assessor replay is required."
        )
    if result.completed_iteration_count < policy.minimum_completed_iterations_for_percentiles:
        recommended_actions.append(
            "Increase successful probabilistic iterations to at least the governed minimum before claiming P90/P95 screening percentiles."
        )
    if failed_iteration_fraction > policy.max_failed_iteration_fraction_for_ready_review:
        recommended_actions.append(
            "Reduce failed-iteration fraction below the governed ready-review threshold before treating this run as assessor-ready."
        )
    if result.dominant_uncertainty_drivers:
        recommended_actions.append(
            "Treat sampled drivers as screening sensitivity indicators only until a formal sensitivity summary is implemented."
        )
    summary_lines = [
        "Build a probabilistic review packet that preserves percentile surfaces, sampled drivers, iteration health, and reproducibility context.",
        (
            f"Probabilistic review packet covers run {result.run_summary.run_id} for model family "
            f"{result.run_summary.model_family.value}."
        ),
        (
            f"Completed {result.completed_iteration_count}/{result.iteration_count} iterations with "
            f"{result.sampled_parameter_count} sampled parameters."
        ),
        (
            f"Failed iteration fraction: {failed_iteration_fraction:.1%}; governed ready-review threshold: "
            f"{policy.max_failed_iteration_fraction_for_ready_review:.0%}."
        ),
    ]
    if result.sampling_seed is not None:
        summary_lines.append(f"Sampling seed: {result.sampling_seed}.")
    limitations = _merge_limitations(
        *[surface.limitations for surface in result.median_surfaces],
        *[surface.limitations for surface in result.p90_surfaces],
        *[surface.limitations for surface in result.p95_surfaces],
        [
            LimitationNote(
                code="probabilistic_driver_summary_screening_only",
                message=(
                    "Probabilistic review lines expose sampled drivers and percentile spread, but they do not "
                    "replace a formal global sensitivity analysis."
                ),
            ),
            LimitationNote(
                code="probabilistic_review_screening_only",
                message=(
                    "Probabilistic review packet summarizes screening-oriented percentile behavior only and "
                    "is not a statement of regulator acceptance or submission approval."
                ),
            ),
        ],
    )
    return ProbabilisticReviewPacket(
        scenario_id=request.scenario.scenario_id,
        run_id=result.run_summary.run_id,
        model_family=result.run_summary.model_family,
        run_mode=result.run_summary.run_mode,
        review_status=review_status,
        probabilistic_result=result,
        summary_lines=summary_lines,
        recommended_actions=recommended_actions,
        sensitivity_lines=sensitivity_lines,
        percentile_surface_lines=percentile_surface_lines,
        failed_iteration_lines=failed_iteration_lines,
        scientific_unsuitability_lines=scientific_unsuitability_lines,
        uncertainty_limitation_lines=result.uncertainty_limitation_lines,
        checks=checks,
        review_template_used=(
            "Summarize whether the probabilistic percentile surfaces are reviewable within the declared Environmental Fate MCP boundary."
        ),
        provenance=provenance_builder.bundle(_collect_source_references(request.scenario)),
        limitations=limitations,
        blockers=blockers,
    )



def build_probabilistic_review_brief(
    request: BuildProbabilisticReviewBriefRequest,
    provenance_builder: ProvenanceBuilder,
) -> ProbabilisticReviewBrief:
    del provenance_builder
    review_packet = request.review_packet
    passed_check_count = sum(1 for check in review_packet.checks if check.passed)
    brief_lines = [review_packet.review_template_used or "Summarize the probabilistic review packet."]
    brief_lines.extend(review_packet.summary_lines)
    brief_lines.extend("Percentile surface: " + line for line in review_packet.percentile_surface_lines)
    brief_lines.extend("Sensitivity: " + line for line in review_packet.sensitivity_lines)
    brief_lines.extend("Failed iterations: " + line for line in review_packet.failed_iteration_lines)
    brief_lines.extend(
        "Scientific unsuitability: " + line for line in review_packet.scientific_unsuitability_lines
    )
    for check in review_packet.checks:
        brief_lines.append(f"[{'pass' if check.passed else 'attention'}] {check.message}")
    return ProbabilisticReviewBrief(
        review_packet_id=review_packet.review_packet_id,
        scenario_id=review_packet.scenario_id,
        run_id=review_packet.run_id,
        model_family=review_packet.model_family,
        run_mode=review_packet.run_mode,
        review_status=review_packet.review_status,
        passed_check_count=passed_check_count,
        total_check_count=len(review_packet.checks),
        review_template_used=review_packet.review_template_used,
        brief_lines=brief_lines,
        recommended_actions=review_packet.recommended_actions,
        sensitivity_lines=review_packet.sensitivity_lines,
        percentile_surface_lines=review_packet.percentile_surface_lines,
        failed_iteration_lines=review_packet.failed_iteration_lines,
        scientific_unsuitability_lines=review_packet.scientific_unsuitability_lines,
        uncertainty_limitation_lines=review_packet.uncertainty_limitation_lines,
        limitations=review_packet.limitations,
    )

