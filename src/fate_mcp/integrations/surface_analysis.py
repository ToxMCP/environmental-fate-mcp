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

def _equation_lines_from_surfaces(surfaces: list) -> list[str]:
    lines: list[str] = []
    seen: set[tuple[str, str]] = set()
    for surface in surfaces:
        if surface.calculation_trace is None:
            continue
        key = (surface.compartment.value, surface.calculation_trace.equation_id)
        if key in seen:
            continue
        seen.add(key)
        lines.append(
            f"{surface.compartment.value}: {surface.calculation_trace.equation_id} -> "
            f"{surface.calculation_trace.equation_text}"
        )
    return lines



def _format_trace_term_value(value: float | str, precision: int = 4) -> str:
    if isinstance(value, str):
        return value
    return f"{value:.{precision}g}"



def _equation_component_lines_from_surfaces(surfaces: list) -> list[str]:
    lines: list[str] = []
    seen: set[tuple[str, str]] = set()
    for surface in surfaces:
        if surface.calculation_trace is None:
            continue
        key = (surface.compartment.value, surface.calculation_trace.equation_id)
        if key in seen:
            continue
        seen.add(key)
        terms = {
            term.name: term.value
            for term in surface.calculation_trace.resolved_terms
        }
        if {
            "decay_constant_per_day",
            "advective_clearance_constant_per_day",
            "total_loss_constant_per_day",
            "degradation_loss_share_fraction",
            "advective_clearance_share_fraction",
        }.issubset(terms):
            line = (
                f"{surface.compartment.value}: loss decomposition -> "
                f"k_deg={_format_trace_term_value(terms['decay_constant_per_day'])}/day, "
                f"k_adv={_format_trace_term_value(terms['advective_clearance_constant_per_day'])}/day, "
                f"k_total={_format_trace_term_value(terms['total_loss_constant_per_day'])}/day, "
                f"deg_share={_format_trace_term_value(float(terms['degradation_loss_share_fraction']) * 100.0, 3)}%, "
                f"adv_share={_format_trace_term_value(float(terms['advective_clearance_share_fraction']) * 100.0, 3)}%"
            )
            if "combined_loss_characteristic_time_days" in terms:
                line += (
                    ", tau_total="
                    + _format_trace_term_value(terms["combined_loss_characteristic_time_days"])
                    + " day"
                )
            if "combined_loss_half_life_days" in terms:
                line += (
                    ", t1/2_total="
                    + _format_trace_term_value(terms["combined_loss_half_life_days"])
                    + " day"
                )
            lines.append(line)
            continue
        if "decay_constant_per_day" in terms:
            line = (
                f"{surface.compartment.value}: loss decomposition -> "
                f"k_deg={_format_trace_term_value(terms['decay_constant_per_day'])}/day"
            )
            if "effective_half_life_days" in terms:
                line += (
                    ", t1/2_eff="
                    + _format_trace_term_value(terms["effective_half_life_days"])
                    + " day"
                )
            if "loss_characteristic_time_days" in terms:
                line += (
                    ", tau_loss="
                    + _format_trace_term_value(terms["loss_characteristic_time_days"])
                    + " day"
                )
            lines.append(line)
    return lines



def _mass_balance_component_lines_from_surfaces(surfaces: list) -> list[str]:
    lines: list[str] = []
    seen: set[tuple[str, str]] = set()
    for surface in surfaces:
        if surface.calculation_trace is None:
            continue
        key = (surface.compartment.value, surface.calculation_trace.equation_id)
        if key in seen:
            continue
        seen.add(key)
        terms = {term.name: term.value for term in surface.calculation_trace.resolved_terms}
        if {
            "emitted_mass_to_elapsed_mg",
            "compartment_mass_at_elapsed_mg",
            "cumulative_degraded_mass_mg",
            "cumulative_advected_mass_mg",
            "mass_balance_closure_error_mg",
        }.issubset(terms):
            lines.append(
                f"{surface.compartment.value}: emitted={_format_trace_term_value(terms['emitted_mass_to_elapsed_mg'])} mg, "
                f"retained={_format_trace_term_value(terms['compartment_mass_at_elapsed_mg'])} mg, "
                f"degraded={_format_trace_term_value(terms['cumulative_degraded_mass_mg'])} mg, "
                f"advected={_format_trace_term_value(terms['cumulative_advected_mass_mg'])} mg, "
                f"closure_error={_format_trace_term_value(terms['mass_balance_closure_error_mg'], 3)} mg"
            )
    return lines



def _loss_dominance_lines_from_surfaces(surfaces: list) -> list[str]:
    lines: list[str] = []
    seen: set[tuple[str, str]] = set()
    for surface in surfaces:
        if surface.calculation_trace is None:
            continue
        key = (surface.compartment.value, surface.calculation_trace.equation_id)
        if key in seen:
            continue
        seen.add(key)
        terms = {term.name: term.value for term in surface.calculation_trace.resolved_terms}
        if {
            "degradation_loss_share_fraction",
            "advective_clearance_share_fraction",
            "total_loss_constant_per_day",
        }.issubset(terms):
            deg_share = float(terms["degradation_loss_share_fraction"])
            adv_share = float(terms["advective_clearance_share_fraction"])
            if deg_share >= 0.67:
                regime = "degradation_dominant"
            elif adv_share >= 0.67:
                regime = "advective_clearance_dominant"
            else:
                regime = "mixed_loss_regime"
            lines.append(
                f"{surface.compartment.value}: {regime} "
                f"(deg_share={_format_trace_term_value(deg_share * 100.0, 3)}%, "
                f"adv_share={_format_trace_term_value(adv_share * 100.0, 3)}%, "
                f"k_total={_format_trace_term_value(terms['total_loss_constant_per_day'])}/day)"
            )
        elif "decay_constant_per_day" in terms:
            lines.append(
                f"{surface.compartment.value}: degradation_only_loss "
                f"(k_deg={_format_trace_term_value(terms['decay_constant_per_day'])}/day)"
            )
    return lines



def _loss_transition_lines_from_surfaces(surfaces: list) -> list[str]:
    lines: list[str] = []
    seen: set[tuple[str, str]] = set()
    for surface in surfaces:
        if surface.calculation_trace is None:
            continue
        key = (surface.compartment.value, surface.calculation_trace.equation_id)
        if key in seen:
            continue
        seen.add(key)
        terms = {term.name: term.value for term in surface.calculation_trace.resolved_terms}
        if {
            "degradation_loss_share_fraction",
            "advective_clearance_share_fraction",
            "loss_dominance_margin_fraction",
        }.issubset(terms):
            deg_share = float(terms["degradation_loss_share_fraction"])
            adv_share = float(terms["advective_clearance_share_fraction"])
            margin = float(terms["loss_dominance_margin_fraction"])
            if margin <= 0.05:
                transition_status = "near_parity_transition"
            elif margin <= 0.2:
                transition_status = "moderate_transition_margin"
            else:
                transition_status = "stable_loss_regime"
            current_leader = (
                "degradation"
                if deg_share > adv_share
                else "advective_clearance"
                if adv_share > deg_share
                else "balanced"
            )
            lines.append(
                f"{surface.compartment.value}: {transition_status} "
                f"(margin={_format_trace_term_value(margin * 100.0, 3)} pct_points, "
                f"current_leader={current_leader})"
            )
        elif "decay_constant_per_day" in terms:
            lines.append(
                f"{surface.compartment.value}: single_loss_mechanism_reference_family "
                f"(k_deg={_format_trace_term_value(terms['decay_constant_per_day'])}/day)"
            )
    return lines



def _transport_regime_lines_from_surfaces(surfaces: list) -> list[str]:
    lines: list[str] = []
    seen: set[tuple[str, str]] = set()
    for surface in surfaces:
        if surface.calculation_trace is None:
            continue
        key = (surface.compartment.value, surface.calculation_trace.equation_id)
        if key in seen:
            continue
        seen.add(key)
        terms = {term.name: term.value for term in surface.calculation_trace.resolved_terms}
        if {
            "residence_time_days",
            "elapsed_turnover_count",
            "active_emission_turnover_count",
        }.issubset(terms):
            elapsed_turnover_count = float(terms["elapsed_turnover_count"])
            active_emission_turnover_count = float(terms["active_emission_turnover_count"])
            storage_boundary_offset = float(terms.get("storage_boundary_offset_turnovers", elapsed_turnover_count - 0.75))
            flow_boundary_offset = float(
                terms.get("flow_through_boundary_offset_turnovers", elapsed_turnover_count - 2.0)
            )
            plateau_fraction = terms.get("retained_mass_fraction_of_finite_plateau")
            if elapsed_turnover_count < 0.75:
                regime = "storage_dominant_transport_regime"
            elif elapsed_turnover_count > 2.0:
                regime = "flow_through_transport_regime"
            else:
                regime = "intermediate_turnover_transport_regime"
            lines.append(
                f"{surface.compartment.value}: {regime} "
                f"(turnovers_elapsed={_format_trace_term_value(elapsed_turnover_count, 3)}, "
                f"turnovers_emission={_format_trace_term_value(active_emission_turnover_count, 3)}, "
                f"residence_time={_format_trace_term_value(terms['residence_time_days'])} day)"
            )
            if regime == "storage_dominant_transport_regime":
                lines.append(
                    f"{surface.compartment.value}: turnover regime remains "
                    f"{_format_trace_term_value(abs(storage_boundary_offset), 3)} turnover(s) below the storage-to-intermediate boundary."
                )
            elif regime == "flow_through_transport_regime":
                lines.append(
                    f"{surface.compartment.value}: turnover regime remains "
                    f"{_format_trace_term_value(abs(flow_boundary_offset), 3)} turnover(s) beyond the intermediate-to-flow-through boundary."
                )
            else:
                lines.append(
                    f"{surface.compartment.value}: turnover regime is boundary-sensitive "
                    f"({_format_trace_term_value(storage_boundary_offset, 3)} turnover(s) above storage boundary, "
                    f"{_format_trace_term_value(abs(flow_boundary_offset), 3)} turnover(s) below flow-through boundary)."
                )
            if isinstance(plateau_fraction, (int, float)):
                lines.append(
                    f"{surface.compartment.value}: retained mass is at "
                    f"{_format_trace_term_value(float(plateau_fraction) * 100.0, 2)} pct of the finite active-emission plateau."
                )
        elif "decay_constant_per_day" in terms:
            lines.append(
                f"{surface.compartment.value}: nonadvective_reference_regime "
                f"(no residence-time turnover term)"
            )
    return lines



def _post_release_recovery_lines_from_surfaces(surfaces: list) -> list[str]:
    lines: list[str] = []
    seen: set[tuple[str, str]] = set()
    for surface in surfaces:
        if surface.calculation_trace is None:
            continue
        key = (surface.compartment.value, surface.calculation_trace.equation_id)
        if key in seen:
            continue
        seen.add(key)
        terms = {term.name: term.value for term in surface.calculation_trace.resolved_terms}
        if {"elapsed_days", "emission_duration_days"}.issubset(terms):
            post_release_elapsed_days = float(
                terms.get(
                    "post_release_elapsed_days",
                    max(float(terms["elapsed_days"]) - float(terms["emission_duration_days"]), 0.0),
                )
            )
            if post_release_elapsed_days <= 0.0:
                lines.append(
                    f"{surface.compartment.value}: no_post_release_recovery_window "
                    f"(elapsed time does not extend beyond the active emission duration)."
                )
                continue
            if {
                "post_release_retained_fraction_of_release_stop_mass",
                "post_release_removed_fraction_of_release_stop_mass",
            }.issubset(terms):
                lines.append(
                    f"{surface.compartment.value}: post_release_recovery_active "
                    f"(elapsed_since_release_stop={_format_trace_term_value(post_release_elapsed_days)} day, "
                    f"retained_from_release_stop={_format_trace_term_value(float(terms['post_release_retained_fraction_of_release_stop_mass']) * 100.0, 2)}%, "
                    f"removed_since_release_stop={_format_trace_term_value(float(terms['post_release_removed_fraction_of_release_stop_mass']) * 100.0, 2)}%)."
                )
            if {
                "post_release_degraded_fraction_of_release_stop_mass",
                "post_release_advected_fraction_of_release_stop_mass",
            }.issubset(terms):
                lines.append(
                    f"{surface.compartment.value}: post_release_loss_split "
                    f"(degraded={_format_trace_term_value(float(terms['post_release_degraded_fraction_of_release_stop_mass']) * 100.0, 2)}%, "
                    f"advected={_format_trace_term_value(float(terms['post_release_advected_fraction_of_release_stop_mass']) * 100.0, 2)}% of release-stop mass)."
                )
            if "post_release_elapsed_turnover_count" in terms:
                turnover_count = float(terms["post_release_elapsed_turnover_count"])
                boundary_offset = float(
                    terms.get(
                        "post_release_flushing_boundary_offset_turnovers",
                        turnover_count - 1.0,
                    )
                )
                if turnover_count >= 1.0:
                    lines.append(
                        f"{surface.compartment.value}: post_release_flushing_window "
                        f"spans {_format_trace_term_value(turnover_count, 3)} turnover(s), "
                        f"{_format_trace_term_value(abs(boundary_offset), 3)} beyond the one-turnover flushing boundary."
                    )
                else:
                    lines.append(
                        f"{surface.compartment.value}: post_release_flushing_window "
                        f"spans {_format_trace_term_value(turnover_count, 3)} turnover(s), "
                        f"{_format_trace_term_value(abs(boundary_offset), 3)} below the one-turnover flushing boundary."
                    )
            if {
                "post_release_boundary_retained_fraction_of_release_stop_mass",
                "post_release_retained_fraction_offset_from_boundary",
                "post_release_retained_fraction_of_release_stop_mass",
            }.issubset(terms):
                retained_fraction = float(
                    terms["post_release_retained_fraction_of_release_stop_mass"]
                )
                boundary_retained_fraction = float(
                    terms["post_release_boundary_retained_fraction_of_release_stop_mass"]
                )
                retained_offset = float(
                    terms["post_release_retained_fraction_offset_from_boundary"]
                )
                direction = "above"
                if retained_offset < -1e-12:
                    direction = "below"
                elif abs(retained_offset) <= 1e-12:
                    direction = "at"
                ratio_fragment = ""
                if "post_release_retained_fraction_ratio_to_boundary" in terms:
                    ratio_fragment = (
                        ", "
                        + f"ratio={_format_trace_term_value(float(terms['post_release_retained_fraction_ratio_to_boundary']), 3)}x anchor"
                    )
                lines.append(
                    f"{surface.compartment.value}: post_release_retained_mass_relative_to_boundary "
                    f"(retained={_format_trace_term_value(retained_fraction * 100.0, 2)}%, "
                    f"one_turnover_anchor={_format_trace_term_value(boundary_retained_fraction * 100.0, 2)}%, "
                    f"offset={_format_trace_term_value(retained_offset * 100.0, 2)} pct{ratio_fragment}, {direction} the one-turnover retained-mass anchor)."
                )
    return lines



def _post_release_regime_lines_from_surfaces(surfaces: list) -> list[str]:
    lines: list[str] = []
    seen: set[tuple[str, str]] = set()
    for surface in surfaces:
        if surface.calculation_trace is None:
            continue
        key = (surface.compartment.value, surface.calculation_trace.equation_id)
        if key in seen:
            continue
        seen.add(key)
        terms = {term.name: term.value for term in surface.calculation_trace.resolved_terms}
        if not {"elapsed_days", "emission_duration_days"}.issubset(terms):
            continue
        post_release_elapsed_days = float(
            terms.get(
                "post_release_elapsed_days",
                max(float(terms["elapsed_days"]) - float(terms["emission_duration_days"]), 0.0),
            )
        )
        if post_release_elapsed_days <= 0.0:
            lines.append(
                f"{surface.compartment.value}: no_post_release_regime_window "
                f"(elapsed time does not extend beyond the active emission duration)."
            )
            continue
        if "post_release_elapsed_turnover_count" not in terms:
            continue
        turnover_count = float(terms["post_release_elapsed_turnover_count"])
        boundary_offset = float(
            terms.get(
                "post_release_flushing_boundary_offset_turnovers",
                turnover_count - 1.0,
            )
        )
        transition_margin = float(
            terms.get(
                "post_release_transition_margin_turnovers",
                abs(boundary_offset),
            )
        )
        if transition_margin <= 0.25:
            lines.append(
                f"{surface.compartment.value}: boundary_sensitive_post_release_recovery_regime "
                f"(post-release window spans {_format_trace_term_value(turnover_count, 3)} turnover(s), "
                f"{_format_trace_term_value(transition_margin, 3)} from the one-turnover flushing boundary)."
            )
        elif boundary_offset < 0.0:
            lines.append(
                f"{surface.compartment.value}: sub_flushing_post_release_recovery_regime "
                f"(post-release window spans {_format_trace_term_value(turnover_count, 3)} turnover(s), "
                f"{_format_trace_term_value(abs(boundary_offset), 3)} below the one-turnover flushing boundary)."
            )
        else:
            lines.append(
                f"{surface.compartment.value}: flushing_dominant_post_release_recovery_regime "
                f"(post-release window spans {_format_trace_term_value(turnover_count, 3)} turnover(s), "
                f"{_format_trace_term_value(abs(boundary_offset), 3)} beyond the one-turnover flushing boundary)."
            )
    return lines



def _post_release_directionality_lines_from_surfaces(surfaces: list) -> list[str]:
    lines: list[str] = []
    seen: set[tuple[str, str]] = set()
    for surface in surfaces:
        if surface.calculation_trace is None:
            continue
        key = (surface.compartment.value, surface.calculation_trace.equation_id)
        if key in seen:
            continue
        seen.add(key)
        terms = {term.name: term.value for term in surface.calculation_trace.resolved_terms}
        required_terms = {
            "post_release_elapsed_days",
            "post_release_elapsed_turnover_count",
            "post_release_flushing_boundary_offset_turnovers",
            "post_release_retained_fraction_ratio_to_boundary",
        }
        if not required_terms.issubset(terms):
            continue
        post_release_elapsed_days = float(terms["post_release_elapsed_days"])
        if post_release_elapsed_days <= 0.0:
            lines.append(
                f"{surface.compartment.value}: no_post_release_directionality_window "
                f"(elapsed time does not extend beyond the active emission duration)."
            )
            continue
        turnover_count = float(terms["post_release_elapsed_turnover_count"])
        boundary_offset = float(terms["post_release_flushing_boundary_offset_turnovers"])
        retained_ratio = float(terms["post_release_retained_fraction_ratio_to_boundary"])
        if abs(retained_ratio - 1.0) <= 0.05:
            lines.append(
                f"{surface.compartment.value}: boundary_matched_post_release_directionality "
                f"(retained release-stop mass sits at {_format_trace_term_value(retained_ratio, 3)}x the one-turnover anchor "
                f"with {_format_trace_term_value(turnover_count, 3)} turnover(s) of post-release recovery)."
            )
        elif boundary_offset < 0.0:
            lines.append(
                f"{surface.compartment.value}: subboundary_post_release_directionality "
                f"(retained release-stop mass remains {_format_trace_term_value(retained_ratio, 3)}x the one-turnover anchor, "
                f"{_format_trace_term_value(abs(boundary_offset), 3)} turnover(s) before the flushing boundary)."
            )
        else:
            lines.append(
                f"{surface.compartment.value}: beyond_boundary_post_release_directionality "
                f"(retained release-stop mass has declined to {_format_trace_term_value(retained_ratio, 3)}x the one-turnover anchor, "
                f"{_format_trace_term_value(abs(boundary_offset), 3)} turnover(s) beyond the flushing boundary)."
            )
    return lines



def _post_release_pace_lines_from_surfaces(surfaces: list) -> list[str]:
    lines: list[str] = []
    seen: set[tuple[str, str]] = set()
    for surface in surfaces:
        if surface.calculation_trace is None:
            continue
        key = (surface.compartment.value, surface.calculation_trace.equation_id)
        if key in seen:
            continue
        seen.add(key)
        terms = {term.name: term.value for term in surface.calculation_trace.resolved_terms}
        required_terms = {
            "post_release_elapsed_days",
            "post_release_elapsed_turnover_count",
            "post_release_half_recovery_turnovers",
            "post_release_half_recovery_offset_turnovers",
            "post_release_recovery_window_multiple_of_half_recovery",
            "post_release_retained_fraction_ratio_to_half_recovery_anchor",
        }
        if not required_terms.issubset(terms):
            continue
        post_release_elapsed_days = float(terms["post_release_elapsed_days"])
        if post_release_elapsed_days <= 0.0:
            lines.append(
                f"{surface.compartment.value}: no_post_release_recovery_pace_window "
                f"(elapsed time does not extend beyond the active emission duration)."
            )
            continue
        half_recovery_turnovers = terms["post_release_half_recovery_turnovers"]
        if isinstance(half_recovery_turnovers, str):
            lines.append(
                f"{surface.compartment.value}: unbounded_post_release_recovery_pace "
                f"(combined-loss half-recovery pace is not finite under the resolved loss constants)."
            )
            continue
        offset = float(terms["post_release_half_recovery_offset_turnovers"])
        multiple = float(terms["post_release_recovery_window_multiple_of_half_recovery"])
        retained_ratio = float(terms["post_release_retained_fraction_ratio_to_half_recovery_anchor"])
        if abs(offset) <= 0.05:
            lines.append(
                f"{surface.compartment.value}: half_recovery_boundary_post_release_pace "
                f"(post-release window spans {_format_trace_term_value(multiple, 3)}x the combined-loss half-recovery pace, "
                f"retained release-stop mass is {_format_trace_term_value(retained_ratio, 3)}x the 50% anchor)."
            )
        elif offset < 0.0:
            lines.append(
                f"{surface.compartment.value}: pre_half_recovery_post_release_pace "
                f"(post-release window spans {_format_trace_term_value(multiple, 3)}x the combined-loss half-recovery pace, "
                f"{_format_trace_term_value(abs(offset), 3)} turnover(s) before the 50% retained-mass anchor)."
            )
        elif multiple >= 4.0:
            lines.append(
                f"{surface.compartment.value}: far_beyond_half_recovery_post_release_pace "
                f"(post-release window spans {_format_trace_term_value(multiple, 3)}x the combined-loss half-recovery pace, "
                f"entering a stable late-recovery regime under the same bounded combined-loss semantics)."
            )
        else:
            lines.append(
                f"{surface.compartment.value}: beyond_half_recovery_post_release_pace "
                f"(post-release window spans {_format_trace_term_value(multiple, 3)}x the combined-loss half-recovery pace, "
                f"{_format_trace_term_value(abs(offset), 3)} turnover(s) beyond the 50% retained-mass anchor)."
            )
    return lines



def _post_release_pace_directionality_lines_from_surfaces(surfaces: list) -> list[str]:
    lines: list[str] = []
    seen: set[tuple[str, str]] = set()
    for surface in surfaces:
        if surface.calculation_trace is None:
            continue
        key = (surface.compartment.value, surface.calculation_trace.equation_id)
        if key in seen:
            continue
        seen.add(key)
        terms = {term.name: term.value for term in surface.calculation_trace.resolved_terms}
        required_terms = {
            "post_release_elapsed_days",
            "post_release_retained_fraction_of_release_stop_mass",
            "post_release_retained_fraction_ratio_to_half_recovery_anchor",
        }
        if not required_terms.issubset(terms):
            continue
        post_release_elapsed_days = float(terms["post_release_elapsed_days"])
        if post_release_elapsed_days <= 0.0:
            lines.append(
                f"{surface.compartment.value}: no_post_release_pace_directionality_window "
                f"(elapsed time does not extend beyond the active emission duration)."
            )
            continue
        retained_fraction = float(terms["post_release_retained_fraction_of_release_stop_mass"])
        retained_offset = float(
            terms.get(
                "post_release_retained_fraction_offset_from_half_recovery_anchor",
                retained_fraction - 0.5,
            )
        )
        retained_ratio = float(terms["post_release_retained_fraction_ratio_to_half_recovery_anchor"])
        transition_margin = terms.get("post_release_half_recovery_transition_margin_turnovers")
        margin_fragment = ""
        if not isinstance(transition_margin, str):
            margin_fragment = (
                ", "
                + f"transition_margin={_format_trace_term_value(float(transition_margin), 3)} turnover(s)"
            )
        if abs(retained_offset) <= 0.01:
            lines.append(
                f"{surface.compartment.value}: half_recovery_anchor_retained_mass_directionality "
                f"(retained={_format_trace_term_value(retained_fraction * 100.0, 2)}%, "
                f"ratio={_format_trace_term_value(retained_ratio, 3)}x the 50% anchor{margin_fragment}, "
                f"effectively at the governed half-recovery retained-mass boundary)."
            )
        elif retained_offset > 0.0:
            lines.append(
                f"{surface.compartment.value}: above_half_recovery_anchor_retained_mass_directionality "
                f"(retained={_format_trace_term_value(retained_fraction * 100.0, 2)}%, "
                f"ratio={_format_trace_term_value(retained_ratio, 3)}x the 50% anchor{margin_fragment}, "
                f"{_format_trace_term_value(retained_offset * 100.0, 2)} pct above the governed half-recovery retained-mass boundary)."
            )
        elif retained_ratio <= 0.125:
            lines.append(
                f"{surface.compartment.value}: late_recovery_regime_retained_mass_directionality "
                f"(retained={_format_trace_term_value(retained_fraction * 100.0, 2)}%, "
                f"ratio={_format_trace_term_value(retained_ratio, 3)}x the 50% anchor{margin_fragment}, "
                f"depletion authority layer distinguishes this as a stable late-recovery regime)."
            )
        else:
            lines.append(
                f"{surface.compartment.value}: below_half_recovery_anchor_retained_mass_directionality "
                f"(retained={_format_trace_term_value(retained_fraction * 100.0, 2)}%, "
                f"ratio={_format_trace_term_value(retained_ratio, 3)}x the 50% anchor{margin_fragment}, "
                f"{_format_trace_term_value(abs(retained_offset) * 100.0, 2)} pct below the governed half-recovery retained-mass boundary)."
            )
    return lines



def _surface_samples_from_result(
    result: ConcentrationEstimationResult,
    max_surface_samples: int,
) -> list[ScientificReviewSurfaceSummary]:
    return [
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
        for surface in result.surfaces[:max_surface_samples]
    ]


