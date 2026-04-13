from __future__ import annotations

from collections import defaultdict
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


def _fit_for_purpose_from_result(result: ConcentrationEstimationResult) -> FitForPurpose:
    fit_for_purpose = {surface.fit_for_purpose for surface in result.surfaces}
    if not fit_for_purpose:
        raise FateValidationError(
            code="empty_concentration_result",
            message="Concentration result does not contain any surfaces to assess.",
            suggestion="Run concentration estimation before building scientific-review artifacts.",
        )
    if len(fit_for_purpose) != 1:
        raise FateValidationError(
            code="mixed_fit_for_purpose_result",
            message="Concentration result mixes multiple fit_for_purpose values across surfaces.",
            suggestion="Build scientific-review artifacts from a homogeneous concentration result.",
            details={"fitForPurposeValues": sorted(item.value for item in fit_for_purpose)},
        )
    return next(iter(fit_for_purpose))


def _ensure_scenario_matches_result(scenario, result: ConcentrationEstimationResult) -> None:
    if scenario.scenario_id != result.run_summary.scenario_id:
        raise FateValidationError(
            code="scenario_result_mismatch",
            message=(
                f"Scenario {scenario.scenario_id} does not match result scenario "
                f"{result.run_summary.scenario_id}."
            ),
            suggestion="Build manifests and review artifacts from a matched scenario/result pair.",
            details={
                "scenarioId": scenario.scenario_id,
                "resultScenarioId": result.run_summary.scenario_id,
            },
        )


def _resolve_model_family_applicability(
    model_family,
    defaults_registry: DefaultsRegistry,
) -> ModelFamilyApplicabilityProfile:
    profile = defaults_registry.model_family_applicability_profile(model_family)
    if profile is None:
        raise FateValidationError(
            code="unknown_model_family_applicability_profile",
            message=f"No governed applicability profile is declared for {model_family.value}.",
            suggestion="Declare the model family in defaults/v1/model_family_applicability_profiles.json.",
        )
    return profile


def _applicability_lines(
    profile: ModelFamilyApplicabilityProfile,
    fit_for_purpose: FitForPurpose,
) -> list[str]:
    supported_fits = ", ".join(item.value for item in profile.fit_for_purpose)
    lines = [
        (
            f"Model family {profile.model_family.value} is declared for fit-for-purpose values: "
            f"{supported_fits}."
        ),
        f"Requested fit-for-purpose: {fit_for_purpose.value}.",
    ]
    if profile.supported_substance_classes:
        lines.append("Supported scope: " + profile.supported_substance_classes[0] + ".")
    if profile.unsupported_substance_classes:
        lines.append("Escalate when scope resembles: " + profile.unsupported_substance_classes[0] + ".")
    if profile.applicability_note:
        lines.append(profile.applicability_note)
    return lines


def _collect_source_references(scenario, result: ConcentrationEstimationResult | None = None):
    references = {}
    for source_reference in scenario.evidence_sources:
        references[source_reference.source_id] = source_reference
    for record in scenario.parameter_records:
        if record.source_reference is not None:
            references[record.source_reference.source_id] = record.source_reference
    if result is not None:
        for assumption in result.assumptions:
            if assumption.source_reference is not None:
                references[assumption.source_reference.source_id] = assumption.source_reference
    return list(references.values())


def _merge_source_references(*reference_groups) -> list:
    merged = {}
    for group in reference_groups:
        for source_reference in group:
            merged[source_reference.source_id] = source_reference
    return list(merged.values())


def _merge_limitations(*limitation_groups: list[LimitationNote]) -> list[LimitationNote]:
    merged: list[LimitationNote] = []
    seen: set[tuple[str, str]] = set()
    for group in limitation_groups:
        for note in group:
            key = (note.code, note.message)
            if key in seen:
                continue
            seen.add(key)
            merged.append(note)
    return merged


def _parameter_quality_lines(manifest: RunParameterManifest | None) -> list[str]:
    return list(manifest.summary_lines) if manifest is not None else []


def _uncertainty_lines(summary: RunUncertaintySummary | None) -> list[str]:
    return list(summary.summary_lines) if summary is not None else []


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
    return lines


def _normalized_evidence_quality(evidence_quality: str | None) -> str:
    return (evidence_quality or "reference").strip().lower()


def _transform_reconciliation_value(value: float, reconciliation_domain: str) -> float:
    if reconciliation_domain == "inverse_rate":
        return math.log(2.0) / max(value, 1e-12)
    return value


def _inverse_reconciliation_value(value: float, reconciliation_domain: str) -> float:
    if reconciliation_domain == "inverse_rate":
        return math.log(2.0) / max(value, 1e-12)
    return value


def _conflict_metric_value(
    original_values: list[float],
    transformed_values: list[float],
    reconciled_value: float,
    conflict_metric: str,
) -> float:
    if conflict_metric == "absolute_log_spread":
        return max(original_values) - min(original_values)
    return (max(transformed_values) - min(transformed_values)) / reconciled_value if reconciled_value else 0.0


def _benchmark_reference_lines(
    model_family,
    run_mode: RunMode,
) -> list[str]:
    manifest = benchmark_manifest()
    coverage_records = manifest["scientificValidationClaimCoverage"]["coverage"]
    relevant_claims = [
        record
        for record in coverage_records
        if record["model_family"] == model_family.value
        and (not record["supported_run_modes"] or run_mode.value in record["supported_run_modes"])
    ]
    covered_claims = [record for record in relevant_claims if record["covered"]]
    if not relevant_claims:
        return ["No governed scientific validation claims are declared for this model family and run mode."]
    if not covered_claims:
        return ["Governed scientific validation claims are declared, but none are currently benchmark-covered."]

    lines = [
        f"Scientific validation claim coverage for {model_family.value}/{run_mode.value}: "
        f"{len(covered_claims)}/{len(relevant_claims)} governed claims covered."
    ]
    lines.append(
        "Representative covered claims: "
        + ", ".join(record["display_name"] for record in covered_claims[:3])
        + "."
    )
    representative_fixtures = []
    for record in covered_claims[:2]:
        representative_fixtures.extend(record["supporting_fixture_names"])
    representative_fixtures = list(dict.fromkeys(representative_fixtures))
    if representative_fixtures:
        lines.append(
            "Representative supporting fixtures: " + ", ".join(representative_fixtures[:3]) + "."
        )
    return lines


def _scientific_validation_claims_for_model_family(
    defaults_registry: DefaultsRegistry,
    model_family,
    run_mode_filter: RunMode | None = None,
) -> list[ScientificValidationClaim]:
    claims = defaults_registry.list_scientific_validation_claims(model_family)
    if run_mode_filter is not None:
        claims = [
            claim
            for claim in claims
            if not claim.supported_run_modes or run_mode_filter in claim.supported_run_modes
        ]
    return sorted(
        claims,
        key=lambda claim: (
            0 if claim.mandatory_for_release else 1,
            CLAIM_PRIORITY_RANK.get(claim.priority.value, 99),
            claim.claim_id,
        ),
    )


def _scientific_claim_coverage_by_id(
    model_family,
    run_mode_filter: RunMode | None = None,
) -> dict[str, ScientificValidationClaimCoverageRecord]:
    coverage_records = benchmark_manifest()["scientificValidationClaimCoverage"]["coverage"]
    filtered = {}
    for payload in coverage_records:
        record = ScientificValidationClaimCoverageRecord(**payload)
        if record.model_family != model_family:
            continue
        if run_mode_filter is not None and record.supported_run_modes and run_mode_filter not in record.supported_run_modes:
            continue
        filtered[record.claim_id] = record
    return filtered


def _scientific_methods_claim_summaries(
    defaults_registry: DefaultsRegistry,
    model_family,
    run_mode_filter: RunMode | None = None,
) -> list[ScientificMethodsDossierClaimSummary]:
    coverage_by_id = _scientific_claim_coverage_by_id(model_family, run_mode_filter)
    summaries: list[ScientificMethodsDossierClaimSummary] = []
    for claim in _scientific_validation_claims_for_model_family(
        defaults_registry,
        model_family,
        run_mode_filter,
    ):
        coverage = coverage_by_id.get(claim.claim_id)
        supporting_fixtures = supporting_benchmark_fixtures_for_claim(claim.claim_id)
        reference_case_lines = list(claim.reference_case_lines)
        reference_case_lines.extend(
            f"{fixture['name']}: {fixture['expected_behavior']}"
            for fixture in supporting_fixtures[:2]
        )
        reference_case_concept_lines = _scientific_methods_claim_reference_case_concept_lines(
            defaults_registry,
            claim.reference_case_ids,
        )
        summary = ScientificMethodsDossierClaimSummary(
            claim_id=claim.claim_id,
            display_name=claim.display_name,
            statement=claim.statement,
            claim_class=claim.claim_class,
            priority=claim.priority,
            mandatory_for_release=claim.mandatory_for_release,
            supported_run_modes=claim.supported_run_modes,
            fit_for_purpose=claim.fit_for_purpose,
            required_validation_tiers=claim.required_validation_tiers,
            required_reference_types=claim.required_reference_types,
            covered=coverage.covered if coverage is not None else False,
            support_strength=(
                coverage.support_strength if coverage is not None else "uncovered"
            ),
            supporting_fixture_count=(
                coverage.supporting_fixture_count if coverage is not None else 0
            ),
            reference_case_ids=claim.reference_case_ids,
            supporting_fixture_names=coverage.supporting_fixture_names if coverage is not None else [],
            supporting_reference_types=coverage.supporting_reference_types if coverage is not None else [],
            supporting_validation_tiers=coverage.supporting_validation_tiers if coverage is not None else [],
            source_references=claim.source_references,
            methods_basis_lines=claim.methods_basis_lines,
            reference_case_lines=list(dict.fromkeys(reference_case_lines)),
            reference_case_concept_lines=reference_case_concept_lines,
            review_notes=claim.review_notes,
            gap_lines=coverage.gap_lines if coverage is not None else ["No claim-coverage record is available."],
        )
        (
            external_corroboration_status,
            external_corroboration_source_count,
            external_corroboration_jurisdictions,
            external_reference_titles,
        ) = _scientific_methods_claim_external_corroboration(defaults_registry, summary)
        summary.external_corroboration_status = external_corroboration_status
        summary.external_corroboration_source_count = external_corroboration_source_count
        summary.external_corroboration_jurisdictions = external_corroboration_jurisdictions
        summary.external_corroboration_lines = _scientific_methods_claim_external_corroboration_lines(
            summary,
            external_corroboration_status,
            external_reference_titles,
            external_corroboration_jurisdictions,
        )
        summary.source_grounding_lines = _scientific_methods_claim_source_grounding_lines(claim)
        summaries.append(summary)
    return summaries


def _scientific_methods_source_grounding_lines(
    claim_summaries: list[ScientificMethodsDossierClaimSummary],
) -> list[str]:
    external_references: list[str] = []
    governed_references: list[str] = []
    for claim_summary in claim_summaries:
        for source_reference in claim_summary.source_references:
            label = source_reference.title
            if source_reference.url and source_reference.url.startswith(("http://", "https://")):
                if label not in external_references:
                    external_references.append(label)
            else:
                if label not in governed_references:
                    governed_references.append(label)
    lines = [
        (
            f"Source grounding cites {len(external_references)} external official references and "
            f"{len(governed_references)} governed internal references across the filtered claim set."
        )
    ]
    if external_references:
        lines.append(
            "Representative external references: " + ", ".join(external_references[:3]) + "."
        )
    if governed_references:
        lines.append(
            "Representative governed references: " + ", ".join(governed_references[:3]) + "."
        )
    return lines


def _scientific_methods_claim_source_grounding_lines(
    claim: ScientificValidationClaim,
) -> list[str]:
    external_references: list[str] = []
    governed_references: list[str] = []
    for source_reference in claim.source_references:
        label = source_reference.title
        if source_reference.url and source_reference.url.startswith(("http://", "https://")):
            if label not in external_references:
                external_references.append(label)
        else:
            if label not in governed_references:
                governed_references.append(label)
    lines: list[str] = []
    if external_references:
        lines.append(
            f"{claim.display_name}: externally grounded by "
            + ", ".join(external_references[:3])
            + "."
        )
    if governed_references:
        lines.append(
            f"{claim.display_name}: governed method anchors include "
            + ", ".join(governed_references[:3])
            + "."
        )
    return lines


def _scientific_methods_reference_case_grounding_lines(
    defaults_registry: DefaultsRegistry,
    claim_summaries: list[ScientificMethodsDossierClaimSummary],
) -> list[str]:
    case_ids: list[str] = []
    case_labels: list[str] = []
    jurisdictions: set[str] = set()
    for claim_summary in claim_summaries:
        for case_id in claim_summary.reference_case_ids:
            if case_id in case_ids:
                continue
            case = defaults_registry.scientific_reference_case(case_id)
            if case is None:
                continue
            case_ids.append(case_id)
            case_labels.append(case.display_name)
            jurisdictions.update(case.jurisdictions)
    lines = [
        (
            f"Scientific reference-case mapping resolves {len(case_ids)} governed case families "
            f"across jurisdictions: {', '.join(sorted(jurisdictions)) if jurisdictions else 'none'}."
        )
    ]
    if case_labels:
        lines.append("Representative reference-case families: " + ", ".join(case_labels[:3]) + ".")
    return lines


def _scientific_methods_claim_reference_case_concept_lines(
    defaults_registry: DefaultsRegistry,
    reference_case_ids: list[str],
) -> list[str]:
    lines: list[str] = []
    for case_id in reference_case_ids:
        case = defaults_registry.scientific_reference_case(case_id)
        if case is None:
            continue
        if case.summary_lines:
            lines.append(f"{case.display_name}: {case.summary_lines[0]}")
        elif case.applicability_lines:
            lines.append(f"{case.display_name}: {case.applicability_lines[0]}")
    return list(dict.fromkeys(lines))


def _scientific_methods_reference_case_concept_summary_lines(
    claim_summaries: list[ScientificMethodsDossierClaimSummary],
) -> list[str]:
    lines: list[str] = []
    for claim_summary in claim_summaries:
        for line in claim_summary.reference_case_concept_lines:
            if line not in lines:
                lines.append(line)
    return lines


def _scientific_methods_highlighted_claim_grounding_lines(
    claim_summaries: list[ScientificMethodsDossierClaimSummary],
) -> list[str]:
    ranked_claims = sorted(
        claim_summaries,
        key=lambda item: (
            0 if item.mandatory_for_release else 1,
            CLAIM_PRIORITY_RANK.get(item.priority.value, 99),
            item.claim_id,
        ),
    )
    lines: list[str] = []
    for claim_summary in ranked_claims:
        if not claim_summary.source_grounding_lines:
            continue
        line = claim_summary.source_grounding_lines[0]
        if line not in lines:
            lines.append(line)
        if len(lines) >= 6:
            break
    return lines


def _scientific_methods_claim_external_corroboration(
    defaults_registry: DefaultsRegistry,
    claim_summary: ScientificMethodsDossierClaimSummary,
) -> tuple[
    ScientificExternalCorroborationStatus,
    int,
    list[str],
    list[str],
]:
    external_references: list[str] = []
    for source_reference in claim_summary.source_references:
        if not (source_reference.url and source_reference.url.startswith(("http://", "https://"))):
            continue
        if source_reference.title not in external_references:
            external_references.append(source_reference.title)
    jurisdictions: list[str] = []
    for case_id in claim_summary.reference_case_ids:
        reference_case = defaults_registry.scientific_reference_case(case_id)
        if reference_case is None:
            continue
        for jurisdiction in reference_case.jurisdictions:
            if jurisdiction not in jurisdictions:
                jurisdictions.append(jurisdiction)
    if not external_references:
        status = ScientificExternalCorroborationStatus.NONE
    elif len(external_references) == 1:
        status = ScientificExternalCorroborationStatus.SINGLE_OFFICIAL_SOURCE
    elif len(jurisdictions) >= 2:
        status = ScientificExternalCorroborationStatus.MULTI_OFFICIAL_MULTI_JURISDICTION
    else:
        status = ScientificExternalCorroborationStatus.MULTI_OFFICIAL_SINGLE_JURISDICTION
    return status, len(external_references), jurisdictions, external_references


def _scientific_methods_claim_external_corroboration_lines(
    claim_summary: ScientificMethodsDossierClaimSummary,
    external_corroboration_status: ScientificExternalCorroborationStatus,
    external_reference_titles: list[str],
    jurisdictions: list[str],
) -> list[str]:
    lines: list[str] = []
    if external_reference_titles:
        lines.append(
            f"{claim_summary.display_name}: external corroboration status is "
            f"{external_corroboration_status.value} from {len(external_reference_titles)} official source(s)."
        )
        lines.append(
            f"{claim_summary.display_name}: independent external corroboration cites "
            + ", ".join(external_reference_titles[:3])
            + "."
        )
    else:
        lines.append(
            f"{claim_summary.display_name}: no independent external corroboration references are declared."
        )
    if jurisdictions:
        lines.append("Corroboration jurisdictions: " + ", ".join(jurisdictions[:3]) + ".")
    if claim_summary.methods_basis_lines:
        lines.append("Corroboration scope: " + claim_summary.methods_basis_lines[0])
    return lines


def _scientific_methods_highlighted_claim_challenge_status(
    claim_summary: ScientificMethodsDossierClaimSummary,
    model_family,
    external_corroboration_status: ScientificExternalCorroborationStatus,
    loss_regime_stability_status: str,
    transport_regime_stability_status: str,
) -> ScientificHighlightedClaimChallengeStatus:
    if not claim_summary.covered or claim_summary.support_strength.value == "uncovered":
        return ScientificHighlightedClaimChallengeStatus.ESCALATE
    if claim_summary.support_strength.value in {"single_anchor", "multi_anchor_single_tier"}:
        return ScientificHighlightedClaimChallengeStatus.CHALLENGE
    if external_corroboration_status == ScientificExternalCorroborationStatus.NONE:
        return ScientificHighlightedClaimChallengeStatus.CHALLENGE
    if (
        external_corroboration_status == ScientificExternalCorroborationStatus.SINGLE_OFFICIAL_SOURCE
        and claim_summary.mandatory_for_release
    ):
        return ScientificHighlightedClaimChallengeStatus.CHALLENGE
    if (
        model_family.value in EXPERIMENTAL_MODEL_FAMILIES
        and claim_summary.priority.value in {"high", "medium"}
    ):
        return ScientificHighlightedClaimChallengeStatus.CHALLENGE
    if loss_regime_stability_status == "near_parity_transition":
        return ScientificHighlightedClaimChallengeStatus.CHALLENGE
    if transport_regime_stability_status == "boundary_sensitive_transport_regime":
        return ScientificHighlightedClaimChallengeStatus.CHALLENGE
    return ScientificHighlightedClaimChallengeStatus.WELL_SUPPORTED


def _scientific_methods_highlighted_claim_external_corroboration(
    defaults_registry: DefaultsRegistry,
    claim_summary: ScientificMethodsDossierClaimSummary,
) -> tuple[
    ScientificExternalCorroborationStatus,
    int,
    list[str],
    list[str],
]:
    return _scientific_methods_claim_external_corroboration(defaults_registry, claim_summary)


def _scientific_methods_highlighted_claim_challenge_lines(
    claim_summary: ScientificMethodsDossierClaimSummary,
    model_family,
    challenge_status: ScientificHighlightedClaimChallengeStatus,
    external_corroboration_status: ScientificExternalCorroborationStatus,
    loss_regime_stability_status: str,
    transport_regime_stability_status: str,
) -> list[str]:
    lines: list[str] = []
    if challenge_status == ScientificHighlightedClaimChallengeStatus.ESCALATE:
        lines.append(
            "Escalate because this highlighted claim is not fully benchmark-covered for the current governed release bar."
        )
    elif challenge_status == ScientificHighlightedClaimChallengeStatus.CHALLENGE:
        if model_family.value in EXPERIMENTAL_MODEL_FAMILIES:
            lines.append(
                "Challenge because this claim belongs to an experimental model family and still requires active reviewer scrutiny even when release-gated."
            )
        else:
            lines.append(
                "Challenge because this claim should be checked against the specific scenario assumptions rather than accepted from aggregate support counts alone."
            )
        if external_corroboration_status == ScientificExternalCorroborationStatus.NONE:
            lines.append(
                "Challenge because this claim currently has no declared independent official external corroboration."
            )
        elif external_corroboration_status == ScientificExternalCorroborationStatus.SINGLE_OFFICIAL_SOURCE:
            lines.append(
                "Challenge because this claim is only grounded to a single independent official external source."
            )
    else:
        lines.append(
            "This claim is currently well supported under the governed benchmark bar, but it should still be interpreted within the declared screening boundary."
        )
    if loss_regime_stability_status == "near_parity_transition":
        lines.append(
            "Challenge because this claim is anchored at a near-parity degradation-versus-clearance transition, where modest input shifts can change the dominant loss interpretation."
        )
    elif loss_regime_stability_status == "stable_loss_regime":
        lines.append(
            "Current anchors place this claim inside a stable one-sided loss regime rather than at a regime boundary."
        )
    if transport_regime_stability_status == "boundary_sensitive_transport_regime":
        lines.append(
            "Challenge because this claim is anchored close to a turnover-regime boundary, where modest residence-time shifts can change the reviewer-facing transport interpretation."
        )
    elif transport_regime_stability_status == "post_release_flushing_recovery_regime":
        lines.append(
            "Challenge because this claim depends on a post-release recovery window, so reviewer confidence depends on whether the elapsed post-release interval is long enough to support the claimed flushing or retention interpretation."
        )
    elif transport_regime_stability_status in {
        "storage_dominant_transport_regime",
        "flow_through_transport_regime",
    }:
        lines.append(
            "Current anchors place this claim inside a stable transport-regime interpretation rather than at a turnover boundary."
        )
    lines.append(
        f"Support strength is {claim_summary.support_strength.value} with {claim_summary.supporting_fixture_count} supporting fixtures."
    )
    if claim_summary.reference_case_ids:
        lines.append(
            f"Governed reference-case mapping count for this claim: {len(claim_summary.reference_case_ids)}."
        )
    return lines


def _scientific_methods_highlighted_claim_external_corroboration_actions(
    claim_summary: ScientificMethodsDossierClaimSummary,
    external_corroboration_status: ScientificExternalCorroborationStatus,
) -> list[str]:
    if external_corroboration_status == ScientificExternalCorroborationStatus.NONE:
        return [
            "Add at least one independent official external source before treating this claim as externally corroborated.",
            "Add or confirm governed reference-case mappings so the claim is challengeable against a regulator-recognizable case family.",
        ]
    if external_corroboration_status == ScientificExternalCorroborationStatus.SINGLE_OFFICIAL_SOURCE:
        return [
            "Add a second independent official external source before treating this claim as broadly corroborated.",
        ]
    if external_corroboration_status == ScientificExternalCorroborationStatus.MULTI_OFFICIAL_SINGLE_JURISDICTION:
        return [
            "Add corroboration from a second jurisdiction when cross-jurisdiction reviewer trust matters for this claim.",
        ]
    return [
        "No immediate external corroboration expansion is required under the current governed release bar.",
    ]


def _scientific_methods_highlighted_claim_loss_regime_stability(
    claim_summary: ScientificMethodsDossierClaimSummary,
) -> tuple[str, list[str]]:
    fixture_names = claim_summary.supporting_fixture_names
    if any("mixed_loss_transition" in name for name in fixture_names):
        return (
            "near_parity_transition",
            [
                "This claim is anchored in a near-parity degradation-versus-clearance transition regime rather than a strongly one-sided loss regime.",
                "Small changes in half-life or residence-time assumptions can move this claim across the loss-dominance boundary.",
            ],
        )
    if any("dominant_loss_share" in name for name in fixture_names):
        return (
            "stable_loss_regime",
            [
                "This claim is anchored in a stable one-sided loss regime where one loss mechanism remains materially larger than the other.",
                "The supported benchmark anchors are intended to confirm regime stability rather than boundary sensitivity.",
            ],
        )
    if claim_summary.claim_class == "advective_loss_dominance":
        return (
            "loss_regime_relevant_but_indirect",
            [
                "This claim is relevant to advective loss behavior, but its current support is not framed as a direct regime-stability anchor.",
            ],
        )
    return (
        "not_applicable",
        [
            "This highlighted claim does not primarily govern a degradation-versus-clearance regime transition surface.",
        ],
    )


def _scientific_methods_highlighted_claim_transport_regime_stability(
    claim_summary: ScientificMethodsDossierClaimSummary,
) -> tuple[str, list[str]]:
    fixture_names = claim_summary.supporting_fixture_names
    if any("post_release" in name for name in fixture_names):
        return (
            "post_release_flushing_recovery_regime",
            [
                "This claim is anchored in an explicit post-release recovery window where retained compartment mass drains after active emission stops.",
                "The supporting anchors emphasize release-stop mass retention, removed-fraction accounting, and turnover-aware flushing interpretation rather than active-emission accumulation.",
            ],
        )
    if any("mixed_loss_transition" in name or "bounded_transport_reference" in name for name in fixture_names):
        return (
            "boundary_sensitive_transport_regime",
            [
                "This claim is anchored close to a transport-regime boundary where modest residence-time shifts can move the run between storage-dominant, intermediate-turnover, and flow-through interpretations.",
                "The bounded transport anchor is intended to show how close the retained mass is to its finite plateau while the turnover count remains boundary-sensitive.",
            ],
        )
    if any("short_residence_time_clearance" in name for name in fixture_names):
        return (
            "flow_through_transport_regime",
            [
                "This claim is anchored in a stable flow-through regime with elapsed turnover count comfortably beyond the flow-through boundary.",
                "The supporting anchors emphasize bounded clearance rather than storage accumulation.",
            ],
        )
    if any(
        "long_residence_time_accumulation" in name or "long_duration_plateau" in name
        for name in fixture_names
    ):
        return (
            "storage_dominant_transport_regime",
            [
                "This claim is anchored in a storage-dominant transport regime with turnover count below the storage-to-intermediate boundary.",
                "The supporting anchors emphasize bounded accumulation toward a finite plateau rather than flow-through clearance.",
            ],
        )
    if claim_summary.claim_class == "advective_transport_regime":
        return (
            "transport_regime_relevant_but_indirect",
            [
                "This claim is transport-regime relevant, but its current support is not yet framed as a direct turnover-boundary anchor.",
            ],
        )
    return (
        "not_applicable",
        [
            "This highlighted claim does not primarily govern residence-time transport-regime interpretation.",
        ],
    )


def _scientific_methods_highlighted_claim_review_questions(
    claim_summary: ScientificMethodsDossierClaimSummary,
    benchmark_anchor_lines: list[str],
    external_corroboration_status: ScientificExternalCorroborationStatus,
    loss_regime_stability_status: str,
    transport_regime_stability_status: str,
) -> list[str]:
    questions: list[str] = []
    if claim_summary.methods_basis_lines:
        questions.append(
            "Does the scenario stay inside the declared claim boundary: "
            + claim_summary.methods_basis_lines[0]
        )
    if claim_summary.reference_case_concept_lines:
        questions.append(
            "Does the cited reference-case concept actually match the reviewer question: "
            + claim_summary.reference_case_concept_lines[0]
        )
    if benchmark_anchor_lines:
        questions.append(
            "Is the leading benchmark anchor scientifically representative here: "
            + benchmark_anchor_lines[0]
        )
    if external_corroboration_status in {
        ScientificExternalCorroborationStatus.NONE,
        ScientificExternalCorroborationStatus.SINGLE_OFFICIAL_SOURCE,
    }:
        questions.append(
            "Is the external corroboration breadth strong enough for this reviewer question, or is additional independent official support needed?"
        )
    if loss_regime_stability_status == "near_parity_transition":
        questions.append(
            "Could modest changes in half-life or residence-time assumptions move this scenario across the degradation-versus-clearance dominance boundary?"
        )
    if transport_regime_stability_status == "boundary_sensitive_transport_regime":
        questions.append(
            "Could a modest residence-time change move this scenario across the storage/intermediate or intermediate/flow-through transport-regime boundary?"
        )
    if transport_regime_stability_status == "post_release_flushing_recovery_regime":
        questions.append(
            "Is the post-release recovery window long enough after release stop to support the claimed flushing or retention interpretation?"
        )
    return questions[:3]


_ADVECTIVE_TRANSPORT_REFERENCE_TYPES = {
    "hand_worked_advective_bounded_transport_reference_fixture",
    "hand_worked_advective_flow_through_transport_reference_fixture",
    "hand_worked_advective_storage_dominant_transport_reference_fixture",
    "hand_worked_advective_transition_boundary_reference_fixture",
}


def _advective_transport_authority_support_ready(
    claim_summaries_by_id: dict[str, ScientificMethodsDossierClaimSummary],
) -> bool:
    turnover_claim = claim_summaries_by_id.get("advective_residence_time_turnover_regime_v1")
    if not turnover_claim or not turnover_claim.covered:
        return False
    if turnover_claim.support_strength != ScientificClaimSupportStrength.MULTI_ANCHOR_MULTI_TIER:
        return False
    if "reference_style" not in turnover_claim.supporting_validation_tiers:
        return False
    return _ADVECTIVE_TRANSPORT_REFERENCE_TYPES.issubset(
        set(turnover_claim.supporting_reference_types)
    )


def _advective_transition_reference_support_ready(
    claim_summaries_by_id: dict[str, ScientificMethodsDossierClaimSummary],
) -> bool:
    mixed_claim = claim_summaries_by_id.get("advective_mixed_loss_transition_margin_v1")
    flip_claim = claim_summaries_by_id.get("advective_loss_regime_flip_directionality_v1")
    if not mixed_claim or not mixed_claim.covered:
        return False
    if mixed_claim.support_strength != ScientificClaimSupportStrength.MULTI_ANCHOR_MULTI_TIER:
        return False
    if "reference_style" not in mixed_claim.supporting_validation_tiers:
        return False
    if (
        "hand_worked_advective_transition_boundary_reference_fixture"
        not in mixed_claim.supporting_reference_types
    ):
        return False
    return bool(
        flip_claim
        and flip_claim.covered
        and flip_claim.support_strength == ScientificClaimSupportStrength.MULTI_ANCHOR_MULTI_TIER
    )


def _advective_post_release_recovery_support_ready(
    claim_summaries_by_id: dict[str, ScientificMethodsDossierClaimSummary],
) -> bool:
    recovery_claim = claim_summaries_by_id.get("advective_post_release_flushing_recovery_v1")
    if not recovery_claim or not recovery_claim.covered:
        return False
    if recovery_claim.support_strength != ScientificClaimSupportStrength.MULTI_ANCHOR_MULTI_TIER:
        return False
    if "reference_style" not in recovery_claim.supporting_validation_tiers:
        return False
    return {
        "hand_worked_advective_post_release_bucket_anchor",
        "hand_worked_advective_post_release_recovery_reference_fixture",
    }.issubset(set(recovery_claim.supporting_reference_types))


def _scientific_methods_recommended_action_summaries(
    defaults_registry: DefaultsRegistry,
    claim_summaries: list[ScientificMethodsDossierClaimSummary],
    highlighted_claim_summaries: list[ScientificMethodsHighlightedClaimSummary],
    model_family,
    uncovered_mandatory_claim_count: int,
) -> list[ScientificMethodsRecommendedActionSummary]:
    summaries: list[ScientificMethodsRecommendedActionSummary] = []
    claim_summaries_by_id = {item.claim_id: item for item in claim_summaries}
    transport_authority_support_ready = _advective_transport_authority_support_ready(
        claim_summaries_by_id
    )
    transition_reference_support_ready = _advective_transition_reference_support_ready(
        claim_summaries_by_id
    )
    if uncovered_mandatory_claim_count:
        summaries.append(
            ScientificMethodsRecommendedActionSummary(
                action=(
                    "Do not treat this model family as release-ready for the filtered claim set until all mandatory scientific validation claims are benchmark-covered."
                ),
                priority=ScientificMethodsRecommendedActionPriority.CRITICAL,
                promotion_impact=ScientificMethodsRecommendedActionPromotionImpact.BLOCKING,
                action_class="release_gate",
            )
        )
    for item in highlighted_claim_summaries:
        if item.external_corroboration_status == ScientificExternalCorroborationStatus.MULTI_OFFICIAL_MULTI_JURISDICTION:
            if item.loss_regime_stability_status != "near_parity_transition":
                continue
        if (
            item.external_corroboration_status
            != ScientificExternalCorroborationStatus.MULTI_OFFICIAL_MULTI_JURISDICTION
            and item.external_corroboration_actions
        ):
            priority = ScientificMethodsRecommendedActionPriority.HIGH
            if item.external_corroboration_status == ScientificExternalCorroborationStatus.MULTI_OFFICIAL_SINGLE_JURISDICTION:
                priority = ScientificMethodsRecommendedActionPriority.MEDIUM
            promotion_impact = ScientificMethodsRecommendedActionPromotionImpact.STRENGTHENING
            if item.mandatory_for_release and item.external_corroboration_status in {
                ScientificExternalCorroborationStatus.NONE,
                ScientificExternalCorroborationStatus.SINGLE_OFFICIAL_SOURCE,
            }:
                promotion_impact = ScientificMethodsRecommendedActionPromotionImpact.BLOCKING
            summaries.append(
                ScientificMethodsRecommendedActionSummary(
                    action=f"{item.display_name}: {item.external_corroboration_actions[0]}",
                    priority=priority,
                    promotion_impact=promotion_impact,
                    action_class="external_corroboration",
                    source_claim_id=item.claim_id,
                    source_claim_display_name=item.display_name,
                )
            )
        boundary_transition_support_ready = (
            transport_authority_support_ready and transition_reference_support_ready
        )
        if (
            item.loss_regime_stability_status == "near_parity_transition"
            and not boundary_transition_support_ready
        ):
            summaries.append(
                ScientificMethodsRecommendedActionSummary(
                    action=(
                        f"{item.display_name}: add a small boundary-sensitivity check around the governed half-life/residence-time transition so reviewers can see how easily this claim flips loss dominance."
                    ),
                    priority=ScientificMethodsRecommendedActionPriority.HIGH,
                    promotion_impact=ScientificMethodsRecommendedActionPromotionImpact.STRENGTHENING,
                    action_class="regime_transition",
                    source_claim_id=item.claim_id,
                    source_claim_display_name=item.display_name,
                )
            )
    thin_claims = [
        item.display_name
        for item in claim_summaries
        if item.covered and len(item.supporting_fixture_names) < 2 and item.priority.value in {"high", "medium"}
    ]
    if thin_claims:
        summaries.append(
            ScientificMethodsRecommendedActionSummary(
                action="Add secondary supporting fixtures for thinner covered claims: "
                + ", ".join(thin_claims[:3])
                + ".",
                priority=ScientificMethodsRecommendedActionPriority.HIGH,
                promotion_impact=ScientificMethodsRecommendedActionPromotionImpact.STRENGTHENING,
                action_class="benchmark_depth",
            )
        )
    if model_family.value in EXPERIMENTAL_MODEL_FAMILIES:
        priority_claims = [
            item
            for item in claim_summaries
            if item.mandatory_for_release and item.priority.value in {"high", "medium"}
        ]
        experimental_blocking = (
            uncovered_mandatory_claim_count > 0
            or any(
                item.support_strength.value != "multi_anchor_multi_tier"
                for item in priority_claims
            )
            or any(
                _scientific_methods_highlighted_claim_external_corroboration(
                    defaults_registry,
                    item,
                )[0]
                != ScientificExternalCorroborationStatus.MULTI_OFFICIAL_MULTI_JURISDICTION
                for item in priority_claims
            )
        )
        experimental_strengthening_needed = True
        if model_family.value == "advective_screening_mass_balance":
            experimental_strengthening_needed = not (
                transport_authority_support_ready and transition_reference_support_ready
            )
        if experimental_blocking or experimental_strengthening_needed:
            summaries.append(
                ScientificMethodsRecommendedActionSummary(
                    action=(
                        "Expand independent edge-condition and reference-style validation before promoting this experimental family beyond challenge use."
                        if experimental_blocking
                        else "Maintain independent edge-condition, reference-style, and transition-boundary validation as trust-strengthening support while this experimental family remains non-default."
                    ),
                    priority=ScientificMethodsRecommendedActionPriority.MEDIUM,
                    promotion_impact=(
                        ScientificMethodsRecommendedActionPromotionImpact.BLOCKING
                        if experimental_blocking
                        else ScientificMethodsRecommendedActionPromotionImpact.STRENGTHENING
                    ),
                    action_class="experimental_validation",
                )
            )
    summaries.sort(
        key=lambda item: (
            {"blocking": 0, "strengthening": 1}.get(item.promotion_impact.value, 99),
            {"critical": 0, "high": 1, "medium": 2}.get(item.priority.value, 99),
            {
                "release_gate": 0,
                "external_corroboration": 1,
                "regime_transition": 2,
                "benchmark_depth": 3,
                "experimental_validation": 4,
            }.get(item.action_class, 99),
            item.source_claim_display_name or "",
            item.action,
        )
    )
    return summaries


def _scientific_methods_promotion_status(
    recommended_action_summaries: list[ScientificMethodsRecommendedActionSummary],
) -> tuple[ScientificMethodsPromotionStatus, int, int]:
    blocking_action_count = sum(
        1
        for item in recommended_action_summaries
        if item.promotion_impact == ScientificMethodsRecommendedActionPromotionImpact.BLOCKING
    )
    strengthening_action_count = sum(
        1
        for item in recommended_action_summaries
        if item.promotion_impact == ScientificMethodsRecommendedActionPromotionImpact.STRENGTHENING
    )
    if blocking_action_count:
        return (
            ScientificMethodsPromotionStatus.BLOCKED,
            blocking_action_count,
            strengthening_action_count,
        )
    if strengthening_action_count:
        return (
            ScientificMethodsPromotionStatus.STRENGTHENING_ONLY,
            blocking_action_count,
            strengthening_action_count,
        )
    return (
        ScientificMethodsPromotionStatus.READY,
        blocking_action_count,
        strengthening_action_count,
    )


def _scientific_methods_promotion_blockers(
    recommended_action_summaries: list[ScientificMethodsRecommendedActionSummary],
) -> tuple[list[str], list[ScientificMethodsPromotionBlockerSummary]]:
    blocker_summaries = [
        ScientificMethodsPromotionBlockerSummary(
            action=item.action,
            action_class=item.action_class,
            source_claim_id=item.source_claim_id,
            source_claim_display_name=item.source_claim_display_name,
        )
        for item in recommended_action_summaries
        if item.promotion_impact == ScientificMethodsRecommendedActionPromotionImpact.BLOCKING
    ]
    blocker_claim_ids: list[str] = []
    for item in blocker_summaries:
        if item.source_claim_id and item.source_claim_id not in blocker_claim_ids:
            blocker_claim_ids.append(item.source_claim_id)
    return blocker_claim_ids, blocker_summaries


def _scientific_methods_highlighted_claim_summaries(
    defaults_registry: DefaultsRegistry,
    claim_summaries: list[ScientificMethodsDossierClaimSummary],
    model_family,
) -> list[ScientificMethodsHighlightedClaimSummary]:
    ranked_claims = sorted(
        claim_summaries,
        key=lambda item: (
            0 if item.mandatory_for_release and item.priority.value == "high" else 1,
            0 if item.mandatory_for_release else 1,
            0
            if model_family.value == "advective_screening_mass_balance"
            and item.claim_class == "advective_loss_dominance"
            else 1,
            CLAIM_PRIORITY_RANK.get(item.priority.value, 99),
            item.claim_id,
        ),
    )
    selected_claims = list(ranked_claims[:5])
    if model_family.value == "advective_screening_mass_balance":
        transition_claim = next(
            (
                item
                for item in ranked_claims
                if item.claim_id == "advective_mixed_loss_transition_margin_v1"
            ),
            None,
        )
        if transition_claim and all(
            item.claim_id != transition_claim.claim_id for item in selected_claims
        ):
            replace_index = next(
                (
                    idx
                    for idx in range(len(selected_claims) - 1, -1, -1)
                    if selected_claims[idx].claim_class != "advective_loss_dominance"
                ),
                len(selected_claims) - 1,
            )
            selected_claims[replace_index] = transition_claim
        transport_claim = next(
            (
                item
                for item in ranked_claims
                if item.claim_id == "advective_residence_time_turnover_regime_v1"
            ),
            None,
        )
        if transport_claim and all(
            item.claim_id != transport_claim.claim_id for item in selected_claims
        ):
            replace_index = next(
                (
                    idx
                    for idx in range(len(selected_claims) - 1, -1, -1)
                    if selected_claims[idx].claim_id not in {
                        "advective_mixed_loss_transition_margin_v1",
                    }
                ),
                len(selected_claims) - 1,
            )
            selected_claims[replace_index] = transport_claim
        post_release_claim = next(
            (
                item
                for item in ranked_claims
                if item.claim_id == "advective_post_release_flushing_recovery_v1"
            ),
            None,
        )
        if post_release_claim and all(
            item.claim_id != post_release_claim.claim_id for item in selected_claims
        ):
            protected_ids = {
                "advective_mixed_loss_transition_margin_v1",
                "advective_residence_time_turnover_regime_v1",
            }
            replace_index = next(
                (
                    idx
                    for idx in range(len(selected_claims) - 1, -1, -1)
                    if selected_claims[idx].claim_id not in protected_ids
                ),
                len(selected_claims) - 1,
            )
            selected_claims[replace_index] = post_release_claim
        stable_loss_claim = next(
            (
                item
                for item in ranked_claims
                if item.claim_id in {
                    "advective_degradation_dominant_loss_share_v1",
                    "advective_clearance_dominant_loss_share_v1",
                }
            ),
            None,
        )
        if stable_loss_claim and not any(
            item.claim_id in {
                "advective_degradation_dominant_loss_share_v1",
                "advective_clearance_dominant_loss_share_v1",
            }
            for item in selected_claims
        ):
            protected_ids = {
                "advective_mixed_loss_transition_margin_v1",
                "advective_residence_time_turnover_regime_v1",
                "advective_post_release_flushing_recovery_v1",
            }
            replace_index = next(
                (
                    idx
                    for idx in range(len(selected_claims) - 1, -1, -1)
                    if selected_claims[idx].claim_id not in protected_ids
                ),
                len(selected_claims) - 1,
            )
            selected_claims[replace_index] = stable_loss_claim
    summaries: list[ScientificMethodsHighlightedClaimSummary] = []
    for claim_summary in selected_claims:
        benchmark_anchor_lines = [
            f"{fixture_name} [{supporting_tier}]"
            for fixture_name, supporting_tier in zip(
                claim_summary.supporting_fixture_names[:3],
                claim_summary.supporting_validation_tiers[:3],
                strict=False,
            )
        ]
        (
            external_corroboration_status,
            external_corroboration_source_count,
            external_corroboration_jurisdictions,
            external_reference_titles,
        ) = _scientific_methods_highlighted_claim_external_corroboration(
            defaults_registry,
            claim_summary,
        )
        (
            loss_regime_stability_status,
            loss_regime_stability_lines,
        ) = _scientific_methods_highlighted_claim_loss_regime_stability(claim_summary)
        (
            transport_regime_stability_status,
            transport_regime_stability_lines,
        ) = _scientific_methods_highlighted_claim_transport_regime_stability(claim_summary)
        challenge_status = _scientific_methods_highlighted_claim_challenge_status(
            claim_summary,
            model_family,
            external_corroboration_status,
            loss_regime_stability_status,
            transport_regime_stability_status,
        )
        summaries.append(
            ScientificMethodsHighlightedClaimSummary(
                claim_id=claim_summary.claim_id,
                display_name=claim_summary.display_name,
                priority=claim_summary.priority,
                mandatory_for_release=claim_summary.mandatory_for_release,
                support_strength=claim_summary.support_strength,
                challenge_status=challenge_status,
                external_corroboration_status=external_corroboration_status,
                external_corroboration_source_count=external_corroboration_source_count,
                external_corroboration_jurisdictions=external_corroboration_jurisdictions,
                external_corroboration_lines=_scientific_methods_claim_external_corroboration_lines(
                    claim_summary,
                    external_corroboration_status,
                    external_reference_titles,
                    external_corroboration_jurisdictions,
                ),
                external_corroboration_actions=_scientific_methods_highlighted_claim_external_corroboration_actions(
                    claim_summary,
                    external_corroboration_status,
                ),
                source_grounding_lines=claim_summary.source_grounding_lines[:2],
                reference_case_concept_lines=claim_summary.reference_case_concept_lines[:2],
                benchmark_anchor_lines=benchmark_anchor_lines,
                loss_regime_stability_status=loss_regime_stability_status,
                loss_regime_stability_lines=loss_regime_stability_lines,
                transport_regime_stability_status=transport_regime_stability_status,
                transport_regime_stability_lines=transport_regime_stability_lines,
                challenge_lines=_scientific_methods_highlighted_claim_challenge_lines(
                    claim_summary,
                    model_family,
                    challenge_status,
                    external_corroboration_status,
                    loss_regime_stability_status,
                    transport_regime_stability_status,
                ),
                review_questions=_scientific_methods_highlighted_claim_review_questions(
                    claim_summary,
                    benchmark_anchor_lines,
                    external_corroboration_status,
                    loss_regime_stability_status,
                    transport_regime_stability_status,
                ),
            )
        )
    return summaries


def _scientific_methods_applicability_lines(
    defaults_registry: DefaultsRegistry,
    model_family,
) -> list[str]:
    applicability_profile = _resolve_model_family_applicability(model_family, defaults_registry)
    review_profile = _resolve_scientific_review_profile(model_family, defaults_registry)
    fit_for_purpose = (
        applicability_profile.fit_for_purpose[0]
        if applicability_profile.fit_for_purpose
        else FitForPurpose.SCREENING
    )
    lines = _applicability_lines(applicability_profile, fit_for_purpose)
    lines.append(
        f"Governed scientific review checklist count for {model_family.value}: "
        f"{len(review_profile.review_checklist)}."
    )
    if review_profile.applicability_note:
        lines.append("Scientific review note: " + review_profile.applicability_note)
    return lines


def _scientific_methods_benchmark_lines(
    claim_summaries: list[ScientificMethodsDossierClaimSummary],
) -> tuple[list[str], list[str]]:
    supporting_fixtures = []
    for claim_summary in claim_summaries:
        for fixture_name in claim_summary.supporting_fixture_names:
            if fixture_name not in supporting_fixtures:
                supporting_fixtures.append(fixture_name)

    benchmark_lines = [
        f"Benchmark-backed claim support cites {len(supporting_fixtures)} supporting fixtures across the filtered claim set."
    ]
    if supporting_fixtures:
        benchmark_lines.append(
            "Representative supporting fixtures: " + ", ".join(supporting_fixtures[:5]) + "."
        )

    edge_condition_lines: list[str] = []
    seen_fixtures: set[str] = set()
    for claim_summary in claim_summaries:
        for fixture in supporting_benchmark_fixtures_for_claim(claim_summary.claim_id):
            if fixture["name"] in seen_fixtures:
                continue
            seen_fixtures.add(fixture["name"])
            if fixture["validation_tier"] in {"edge_condition", "invariance", "sensitivity"}:
                edge_condition_lines.append(
                    f"{fixture['name']} [{fixture['validation_tier']}]: {fixture['expected_behavior']}"
                )
    return benchmark_lines, edge_condition_lines[:6]


def _scientific_methods_support_strength_lines(
    claim_summaries: list[ScientificMethodsDossierClaimSummary],
    model_family,
) -> list[str]:
    high_priority_claims = [
        item for item in claim_summaries if item.priority.value == "high" and item.mandatory_for_release
    ]
    multi_anchor_high_priority = [
        item
        for item in high_priority_claims
        if item.support_strength.value in {"multi_anchor_single_tier", "multi_anchor_multi_tier"}
    ]
    single_anchor_claims = [
        item.display_name for item in claim_summaries if item.support_strength.value == "single_anchor"
    ]
    lines = [
        (
            f"High-priority mandatory claims with multi-anchor support for {model_family.value}: "
            f"{len(multi_anchor_high_priority)}/{len(high_priority_claims)}."
        )
    ]
    if single_anchor_claims:
        lines.append(
            "Claims still backed by a single anchor: " + ", ".join(single_anchor_claims[:4]) + "."
        )
    else:
        lines.append("No in-scope claims are limited to a single benchmark anchor.")
    return lines


def _resolve_scientific_review_profile(
    model_family,
    defaults_registry: DefaultsRegistry,
) -> ScientificReviewProfile:
    profile = defaults_registry.scientific_review_profile(model_family)
    if profile is None:
        raise FateValidationError(
            code="unknown_scientific_review_profile",
            message=f"No governed scientific review profile is declared for {model_family.value}.",
            suggestion="Declare the model family in defaults/v1/scientific_review_profiles.json.",
        )
    return profile


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
) -> ScientificReviewOutcome:
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
    outcome = _scientific_review_outcome(
        review_profile,
        fit_assessment,
        uncertainty_summary,
    )
    outcome_lines, recommended_actions, governing_rule_lines = _scientific_review_outcome_lines(
        review_profile,
        outcome,
        fit_assessment,
        uncertainty_summary,
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


def _resolve_regulatory_handoff_profile(
    request: ExportRegulatoryHandoffPackageRequest,
    defaults_registry: DefaultsRegistry,
) -> tuple[RegulatoryHandoffProfile, str, str | None, float | None]:
    explicit_profile = None
    if request.handoff_profile_id:
        explicit_profile = defaults_registry.regulatory_handoff_profile(request.handoff_profile_id)
        if explicit_profile is None:
            raise FateValidationError(
                code="unknown_regulatory_handoff_profile",
                message=f"Unknown regulatory handoff profile: {request.handoff_profile_id}.",
                suggestion="Inspect defaults://regulatory-handoff-profiles and choose a declared profile.",
            )

    recommendation = None
    if request.consumer_name:
        recommendation = defaults_registry.recommend_regulatory_handoff_profile(request.consumer_name)
        if recommendation is None:
            raise FateValidationError(
                code="unknown_regulatory_handoff_consumer",
                message=f"Could not resolve a governed regulatory handoff profile for consumer {request.consumer_name}.",
                suggestion="Use fate_recommend_regulatory_handoff_profile or inspect defaults://regulatory-handoff-profiles.",
            )

    if explicit_profile and recommendation:
        if recommendation.resolved_profile_id != explicit_profile.profile_id:
            raise FateValidationError(
                code="regulatory_handoff_profile_consumer_mismatch",
                message=(
                    f"Requested profile {explicit_profile.profile_id} does not match consumer "
                    f"{request.consumer_name}, which resolves to {recommendation.resolved_profile_id}."
                ),
                suggestion="Use a matching consumer/profile pair or provide only one selector.",
                details={
                    "requestedProfileId": explicit_profile.profile_id,
                    "consumerName": request.consumer_name,
                    "recommendedProfileId": recommendation.resolved_profile_id,
                },
            )
        return (
            explicit_profile,
            "explicit_profile_id_consumer_match",
            recommendation.matched_hint,
            recommendation.confidence,
        )

    if explicit_profile:
        return explicit_profile, "explicit_profile_id", request.handoff_profile_id, 1.0

    if recommendation:
        profile = defaults_registry.regulatory_handoff_profile(recommendation.resolved_profile_id)
        if profile is None:
            raise FateValidationError(
                code="unknown_regulatory_handoff_profile",
                message=f"Resolved profile {recommendation.resolved_profile_id} is not declared.",
                suggestion="Check defaults/v1/regulatory_handoff_profiles.json for consistency.",
            )
        return profile, "consumer_name_match", recommendation.matched_hint, recommendation.confidence

    profile = defaults_registry.regulatory_handoff_profile("exposure_scenario_mcp_v1")
    if profile is None:
        raise FateValidationError(
            code="missing_default_regulatory_handoff_profile",
            message="Default regulatory handoff profile exposure_scenario_mcp_v1 is not declared.",
            suggestion="Restore the default governed handoff profile in defaults/v1/regulatory_handoff_profiles.json.",
        )
    return profile, "default_profile", profile.profile_id, 1.0


def build_concentration_surface_bundle(result: ConcentrationEstimationResult) -> ConcentrationSurfaceBundle:
    return ConcentrationSurfaceBundle(
        scenario_id=result.run_summary.scenario_id,
        surfaces=result.surfaces,
        run_summary=result.run_summary,
        assumptions=result.assumptions,
        dependencies=[
            DependencyDescriptor(name="fate-mcp", version=VERSION, role="producer"),
            DependencyDescriptor(
                name=result.run_summary.model_family.value,
                version=VERSION,
                role="model_family",
            ),
        ],
    )


def compare_fate_scenarios(
    request: CompareFateScenariosRequest,
    provenance_builder: ProvenanceBuilder,
) -> FateScenarioComparisonRecord:
    base_by_key = {
        (surface.medium, surface.compartment, surface.time_window.bucket_label): surface
        for surface in request.base_result.surfaces
    }
    candidate_by_key = {
        (surface.medium, surface.compartment, surface.time_window.bucket_label): surface
        for surface in request.candidate_result.surfaces
    }

    deltas = []
    for key, base_surface in base_by_key.items():
        candidate_surface = candidate_by_key.get(key)
        if not candidate_surface:
            continue
        absolute_delta = candidate_surface.concentration_value - base_surface.concentration_value
        relative_delta = None
        if base_surface.concentration_value:
            relative_delta = absolute_delta / base_surface.concentration_value
        deltas.append(
            SurfaceDelta(
                medium=base_surface.medium,
                compartment=base_surface.compartment,
                base_value=base_surface.concentration_value,
                candidate_value=candidate_surface.concentration_value,
                concentration_unit=base_surface.concentration_unit,
                absolute_delta=absolute_delta,
                relative_delta=relative_delta,
            )
        )

    base_params = {f"{item.parameter}:{item.value}" for item in request.base_result.assumptions}
    candidate_params = {f"{item.parameter}:{item.value}" for item in request.candidate_result.assumptions}
    changed_assumptions = sorted(candidate_params.symmetric_difference(base_params))
    dominant_drivers = [
        f"{delta.medium.value}/{delta.compartment.value} delta={delta.absolute_delta:.6g} {delta.concentration_unit}"
        for delta in sorted(deltas, key=lambda item: abs(item.absolute_delta), reverse=True)[:3]
    ]

    return FateScenarioComparisonRecord(
        base_scenario_id=request.base_result.run_summary.scenario_id,
        candidate_scenario_id=request.candidate_result.run_summary.scenario_id,
        surface_deltas=deltas,
        changed_assumptions=changed_assumptions,
        dominant_drivers=dominant_drivers,
        provenance=provenance_builder.bundle(),
    )


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
                "Model-family selection recommendations are workflow-selection guidance inside the Fate MCP boundary "
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
        or "Build a governed assessor-facing review packet for a Fate MCP model-family selection recommendation.",
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
            message="Model-family comparison reflects deterministic Fate MCP outputs for one matched scenario and does not by itself endorse either family as the scientifically correct choice.",
        )
    ]
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
        or "Build a governed assessor-facing review packet for a Fate MCP model-family comparison.",
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


def apply_physchem_evidence(
    scenario,
    evidence: list[PhyschemEvidenceRecord],
    provenance_builder: ProvenanceBuilder,
) -> PhyschemEvidenceApplicationResult:
    defaults_registry = provenance_builder.defaults_registry
    runtime_supported_parameters = defaults_registry.runtime_supported_parameter_units()
    parameter_map = {record.parameter: record for record in scenario.parameter_records}
    applied = []
    notes = []
    scenario_quality_flags = list(scenario.quality_flags)
    evidence_observations = []
    reconciled_parameters = []
    conflicts = []

    grouped: dict[str, list[PhyschemEvidenceRecord]] = defaultdict(list)
    for item in evidence:
        grouped[item.parameter].append(item)

    for parameter, items in sorted(grouped.items()):
        parameter_policy = defaults_registry.parameter_policy(parameter)
        expected_unit = parameter_policy.expected_unit if parameter_policy else None
        conflict_relative_spread_threshold = (
            parameter_policy.conflict_relative_spread_threshold
            if parameter_policy
            else DEFAULT_PHYSCHEM_RELATIVE_SPREAD_THRESHOLD
        )
        weighting_strategy = (
            parameter_policy.weighting_strategy
            if parameter_policy
            else DEFAULT_WEIGHTING_STRATEGY
        )
        reconciliation_domain = (
            parameter_policy.reconciliation_domain if parameter_policy else "linear"
        )
        conflict_metric = (
            parameter_policy.conflict_metric if parameter_policy else "relative_spread"
        )
        disallow_conservative_empirical_blend = (
            parameter_policy.disallow_conservative_empirical_blend if parameter_policy else False
        )
        runtime_supported = (
            parameter_policy.runtime_supported
            if parameter_policy
            else parameter in runtime_supported_parameters
        )
        units = {item.unit for item in items}
        if len(units) > 1:
            raise FateValidationError(
                code="physchem_evidence_inconsistent_units",
                message=f"Evidence for {parameter} contains inconsistent units: {sorted(units)}.",
                suggestion="Normalize all evidence for a parameter to a single canonical unit before reconciliation.",
                details={"parameter": parameter, "units": sorted(units)},
            )
        unit = next(iter(units))
        if expected_unit and unit != expected_unit:
            raise FateValidationError(
                code="physchem_evidence_unit_mismatch",
                message=f"Evidence unit {unit} is incompatible with expected unit {expected_unit} for {parameter}.",
                suggestion="Provide evidence in the canonical Fate MCP unit for the parameter.",
                details={"parameter": parameter, "expectedUnit": expected_unit, "providedUnit": unit},
            )

        weights = [evidence_weight(item.evidence_quality) for item in items]
        total_weight = sum(weights)
        values = [item.value for item in items]
        transformed_values = [
            _transform_reconciliation_value(value, reconciliation_domain) for value in values
        ]
        normalized_qualities = [_normalized_evidence_quality(item.evidence_quality) for item in items]
        conservative_empirical_blend_blocked = (
            disallow_conservative_empirical_blend
            and any(quality in CONSERVATIVE_EVIDENCE_QUALITIES for quality in normalized_qualities)
            and any(quality not in CONSERVATIVE_EVIDENCE_QUALITIES for quality in normalized_qualities)
        )
        if conservative_empirical_blend_blocked:
            selected_index = max(range(len(items)), key=lambda idx: (weights[idx], -idx))
            weighted_value = values[selected_index]
            transformed_weighted_value = transformed_values[selected_index]
            status = "conflict"
            selection_rationale = (
                "Policy forbids blending regulatory and empirical evidence, so the highest-weight input "
                "was preserved instead of arithmetic reconciliation."
            )
        else:
            transformed_weighted_value = sum(
                weight * value for weight, value in zip(weights, transformed_values, strict=True)
            ) / total_weight
            weighted_value = _inverse_reconciliation_value(
                transformed_weighted_value,
                reconciliation_domain,
            )
            selection_rationale = (
                f"Weighted reconciliation across physicochemical evidence inputs using policy {weighting_strategy} "
                f"in {reconciliation_domain} space."
            )
        min_value = min(values)
        max_value = max(values)
        relative_spread = _conflict_metric_value(
            values,
            transformed_values,
            transformed_weighted_value,
            conflict_metric,
        )
        if not conservative_empirical_blend_blocked:
            status = (
                "agreed"
                if relative_spread <= conflict_relative_spread_threshold
                else "conflict"
            )
        contributing_sources = [item.source_reference.source_id for item in items]

        reconciled_parameters.append(
            ReconciledPhyschemParameter(
                parameter=parameter,
                reconciled_value=weighted_value,
                unit=unit,
                weighting_strategy=weighting_strategy,
                reconciliation_domain=reconciliation_domain,
                conflict_metric=conflict_metric,
                total_weight=total_weight,
                min_value=min_value,
                max_value=max_value,
                relative_spread=relative_spread,
                status=status,
                contributing_sources=contributing_sources,
            )
        )

        low_confidence_inputs = [item for item in items if is_low_confidence_evidence(item.evidence_quality)]
        quality_flags = []
        if low_confidence_inputs:
            warning = QualityFlag(
                code="heuristic_physchem_evidence",
                severity=Severity.WARNING,
                message=f"Low-confidence evidence contributed to {parameter}: "
                + ", ".join(sorted(item.source_reference.source_id for item in low_confidence_inputs)),
            )
            quality_flags.append(warning)
            scenario_quality_flags.append(warning)
        if conservative_empirical_blend_blocked:
            conflict = PhyschemEvidenceConflict(
                parameter=parameter,
                conflict_type="conservative_empirical_blend_disallowed",
                description=(
                    f"Evidence for {parameter} mixes regulatory and empirical lanes, and policy forbids "
                    "blending them into a single reconciled value."
                ),
                observed_values=[
                    f"{item.source_reference.source_id}: {item.value} {item.unit} "
                    f"(quality={item.evidence_quality}, weight={evidence_weight(item.evidence_quality):.2f})"
                    for item in items
                ],
                contributing_sources=contributing_sources,
            )
            conflicts.append(conflict)
            conflict_flag = QualityFlag(
                code="physchem_evidence_lane_conflict",
                severity=Severity.WARNING,
                message=f"Regulatory and empirical evidence lanes remain unresolved for {parameter}.",
            )
            quality_flags.append(conflict_flag)
            scenario_quality_flags.append(conflict_flag)
        elif status == "conflict":
            conflict = PhyschemEvidenceConflict(
                parameter=parameter,
                conflict_type="spread_exceeds_threshold",
                description=(
                    f"Evidence for {parameter} differs by more than the allowed {conflict_metric} threshold "
                    f"({conflict_relative_spread_threshold}) after evidence-quality weighting."
                ),
                observed_values=[
                    f"{item.source_reference.source_id}: {item.value} {item.unit} "
                    f"(quality={item.evidence_quality}, weight={evidence_weight(item.evidence_quality):.2f})"
                    for item in items
                ],
                contributing_sources=contributing_sources,
            )
            conflicts.append(conflict)
            conflict_flag = QualityFlag(
                code="physchem_evidence_conflict",
                severity=Severity.WARNING,
                message=f"Conflicting physicochemical evidence remains for {parameter}.",
            )
            quality_flags.append(conflict_flag)
            scenario_quality_flags.append(conflict_flag)

        if not runtime_supported:
            note = f"Stored parameter {parameter} in scenario state, but the reference runtime does not consume it yet."
            notes.append(note)
            scenario_quality_flags.append(
                QualityFlag(
                    code="unsupported_runtime_parameter",
                    severity=Severity.INFO,
                    message=note,
                )
            )

        parameter_record = FateParameterRecord(
            parameter=parameter,
            value=weighted_value,
            unit=unit,
            source_classification=source_classification_for_evidence(
                (
                    items[max(range(len(items)), key=lambda idx: (weights[idx], -idx))].evidence_quality
                    if conservative_empirical_blend_blocked
                    else ("heuristic" if low_confidence_inputs else "reference")
                )
            ),
            source_reference=items[0].source_reference if len(items) == 1 else None,
            evidence_quality=(
                items[0].evidence_quality
                if len(items) == 1
                else (
                    items[max(range(len(items)), key=lambda idx: (weights[idx], -idx))].evidence_quality
                    if conservative_empirical_blend_blocked
                    else "weighted_mixed"
                )
            ),
            rationale=selection_rationale,
            quality_flags=quality_flags,
        )
        parameter_map[parameter] = parameter_record
        applied.append(
            provenance_builder.from_parameter_record(
                parameter_record,
                rationale=f"Resolved physicochemical evidence for {parameter} using policy-driven evidence-quality weighting.",
            )
        )
        for item, weight in zip(items, weights, strict=True):
            evidence_observations.append(
                PhyschemEvidenceObservation(
                    parameter=parameter,
                    value=item.value,
                    unit=item.unit,
                    source_reference=item.source_reference,
                    evidence_quality=item.evidence_quality,
                    evidence_weight=weight,
                )
            )

    updated_sources = scenario.evidence_sources + [item.source_reference for item in evidence]
    scenario = scenario.model_copy(
        update={
            "parameter_records": sorted(parameter_map.values(), key=lambda record: record.parameter),
            "evidence_sources": updated_sources,
            "provenance": provenance_builder.bundle(updated_sources),
            "quality_flags": scenario_quality_flags,
        }
    )
    return PhyschemEvidenceApplicationResult(
        scenario=scenario,
        evidence_observations=evidence_observations,
        reconciled_parameters=reconciled_parameters,
        conflicts=conflicts,
        unresolved_conflict_count=len(conflicts),
        quality_flags=[
            flag
            for flag in scenario_quality_flags
            if flag.code in {
                "heuristic_physchem_evidence",
                "physchem_evidence_conflict",
                "physchem_evidence_lane_conflict",
                "unsupported_runtime_parameter",
            }
        ],
        applied_assumptions=applied,
        notes=(
            notes
            or ["Evidence was attached to the scenario provenance and parameter ledger using evidence-quality weighting."]
        ),
    )


def assess_release_scenario_fit(
    scenario,
    run_options,
    provenance_builder: ProvenanceBuilder,
) -> ReleaseScenarioFitAssessment:
    applicability_profile = _resolve_model_family_applicability(
        run_options.model_family,
        provenance_builder.defaults_registry,
    )
    applicability_lines = _applicability_lines(applicability_profile, run_options.fit_for_purpose)
    reasons = []
    score = 1.0
    runtime_supported_parameters = provenance_builder.defaults_registry.runtime_supported_parameter_units()
    if run_options.fit_for_purpose not in applicability_profile.fit_for_purpose:
        score -= 0.25
        reasons.append(
            f"Requested fit_for_purpose {run_options.fit_for_purpose.value} is not declared for "
            f"model family {run_options.model_family.value}."
        )
    if run_options.run_mode == RunMode.TIME_BUCKET and run_options.bucket_count > 12:
        score -= 0.2
        reasons.append("Large time-bucket count increases interpretive burden for a screening workflow.")
    if any(
        item.execution_mode != "pre_release_global"
        for item in scenario.treatment_assumptions
    ):
        score -= 0.1
        reasons.append(
            "Some treatment assumptions remain provenance-only because they are not executable pre-release global removal."
        )
    if len(scenario.release_fractions) > 3:
        score -= 0.1
        reasons.append("Many release media are being approximated with a simple screening kernel.")
    unsupported_parameters = sorted(
        {
            record.parameter
            for record in scenario.parameter_records
            if record.parameter not in runtime_supported_parameters
        }
    )
    if unsupported_parameters:
        score -= 0.15
        reasons.append(
            "Some parameter records are preserved for provenance but are not consumed by the reference runtime: "
            + ", ".join(sorted(unsupported_parameters))
        )
    verdict = "good_fit" if score >= 0.75 else "review_needed"
    return ReleaseScenarioFitAssessment(
        fit_score=max(score, 0.0),
        model_family=run_options.model_family,
        fit_for_purpose=run_options.fit_for_purpose,
        verdict=verdict,
        reasons=reasons,
        applicability_profile=applicability_profile,
        applicability_lines=applicability_lines,
    )


def build_run_parameter_manifest(
    scenario,
    result: ConcentrationEstimationResult,
    provenance_builder: ProvenanceBuilder,
) -> RunParameterManifest:
    _ensure_scenario_matches_result(scenario, result)
    fit_for_purpose = _fit_for_purpose_from_result(result)
    applicability_profile = _resolve_model_family_applicability(
        result.run_summary.model_family,
        provenance_builder.defaults_registry,
    )
    assumption_groups: dict[str, list[FateAssumptionRecord]] = defaultdict(list)
    for assumption in result.assumptions:
        assumption_groups[assumption.parameter].append(assumption)
    scenario_parameters = {record.parameter: record for record in scenario.parameter_records}
    parameter_names = sorted(set(assumption_groups) | set(scenario_parameters))
    entries: list[RunParameterManifestEntry] = []

    for parameter in parameter_names:
        assumption_records = assumption_groups.get(parameter, [])
        scenario_record = scenario_parameters.get(parameter)
        representative = scenario_record or (assumption_records[0] if assumption_records else None)
        if representative is None:
            continue
        rationales = []
        source_reference_ids = []
        quality_flag_codes = []
        if scenario_record is not None:
            if scenario_record.rationale:
                rationales.append(scenario_record.rationale)
            if scenario_record.source_reference is not None:
                source_reference_ids.append(scenario_record.source_reference.source_id)
            quality_flag_codes.extend(flag.code for flag in scenario_record.quality_flags)
        for assumption in assumption_records:
            if assumption.rationale and assumption.rationale not in rationales:
                rationales.append(assumption.rationale)
            if assumption.source_reference is not None and assumption.source_reference.source_id not in source_reference_ids:
                source_reference_ids.append(assumption.source_reference.source_id)
            quality_flag_codes.extend(flag.code for flag in assumption.quality_flags)
        dedup_quality_flags = sorted({code for code in quality_flag_codes})
        runtime_consumed = bool(assumption_records)
        rationale = " ".join(rationales) or (
            "Parameter is preserved on the scenario state for review provenance but was not consumed by the current runtime."
            if not runtime_consumed
            else "Parameter was resolved from runtime assumptions."
        )
        source_classification = (
            scenario_record.source_classification
            if scenario_record is not None
            else assumption_records[0].source_classification
        )
        entries.append(
            RunParameterManifestEntry(
                parameter=parameter,
                resolved_value=(
                    scenario_record.value
                    if scenario_record is not None
                    else assumption_records[0].value
                ),
                unit=(
                    scenario_record.unit
                    if scenario_record is not None
                    else assumption_records[0].unit
                ),
                source_classification=source_classification,
                evidence_quality=(
                    scenario_record.evidence_quality
                    if scenario_record is not None
                    else None
                ),
                runtime_consumed=runtime_consumed,
                source_reference_ids=source_reference_ids,
                quality_flag_codes=dedup_quality_flags,
                rationale=rationale,
            )
        )

    entries = sorted(entries, key=lambda item: (not item.runtime_consumed, item.parameter))
    runtime_consumed_count = sum(1 for entry in entries if entry.runtime_consumed)
    preserved_only_count = len(entries) - runtime_consumed_count
    evidence_backed = [
        entry.parameter
        for entry in entries
        if entry.source_classification == SourceClassification.USER_INPUT or entry.evidence_quality is not None
    ]
    default_or_derived_count = sum(
        1
        for entry in entries
        if entry.source_classification in {SourceClassification.CURATED_DEFAULT, SourceClassification.DERIVED}
    )
    heuristic_count = sum(
        1 for entry in entries if entry.source_classification == SourceClassification.HEURISTIC
    )
    summary_lines = [
        (
            f"{runtime_consumed_count} parameters were consumed by runtime "
            f"{result.run_summary.model_family.value}; {preserved_only_count} remain provenance-only for review."
        ),
        (
            f"Applicability context follows {applicability_profile.model_family.value} "
            f"for fit-for-purpose {fit_for_purpose.value}."
        ),
        (
            f"{default_or_derived_count} entries rely on governed curated-default or derived assumptions; "
            f"{heuristic_count} entries remain heuristic."
        ),
    ]
    if evidence_backed:
        summary_lines.append(
            "User or evidence-backed parameters: " + ", ".join(sorted(evidence_backed)) + "."
        )

    limitations = []
    if preserved_only_count:
        limitations.append(
            LimitationNote(
                code="preserved_only_parameters",
                message=(
                    "Some scenario parameters are preserved for provenance and assessor review but are not "
                    "consumed by the current runtime."
                ),
            )
        )
    if heuristic_count:
        limitations.append(
            LimitationNote(
                code="heuristic_parameter_inputs",
                message="One or more manifest entries rely on heuristic source classification.",
            )
        )
    return RunParameterManifest(
        scenario_id=scenario.scenario_id,
        run_id=result.run_summary.run_id,
        model_family=result.run_summary.model_family,
        fit_for_purpose=fit_for_purpose,
        entries=entries,
        summary_lines=summary_lines,
        limitations=limitations,
        provenance=provenance_builder.bundle(_collect_source_references(scenario, result)),
    )


def build_run_uncertainty_summary(
    scenario,
    result: ConcentrationEstimationResult,
    provenance_builder: ProvenanceBuilder,
) -> RunUncertaintySummary:
    _ensure_scenario_matches_result(scenario, result)
    manifest = build_run_parameter_manifest(scenario, result, provenance_builder)
    drivers: list[UncertaintyDriver] = []

    for record in scenario.parameter_records:
        source_reference_ids = (
            [record.source_reference.source_id] if record.source_reference is not None else []
        )
        quality_flag_codes = [flag.code for flag in record.quality_flags]
        if {"physchem_evidence_conflict", "physchem_evidence_lane_conflict"} & set(quality_flag_codes):
            drivers.append(
                UncertaintyDriver(
                    parameter=record.parameter,
                    driver_type="evidence_conflict",
                    reason=(
                        "Conflicting physicochemical evidence remains attached to this parameter after reconciliation."
                    ),
                    severity=Severity.WARNING,
                    source_reference_ids=source_reference_ids,
                    quality_flag_codes=quality_flag_codes,
                )
            )

    for entry in manifest.entries:
        if not entry.runtime_consumed:
            drivers.append(
                UncertaintyDriver(
                    parameter=entry.parameter,
                    driver_type="unsupported_runtime_parameter",
                    reason=(
                        "Parameter is preserved on scenario state for traceability but is not consumed by the "
                        "current runtime."
                    ),
                    severity=Severity.INFO,
                    source_reference_ids=entry.source_reference_ids,
                    quality_flag_codes=entry.quality_flag_codes,
                )
            )
        elif (
            entry.parameter in CAPACITY_PARAMETERS
            and entry.source_classification == SourceClassification.CURATED_DEFAULT
        ):
            drivers.append(
                UncertaintyDriver(
                    parameter=entry.parameter,
                    driver_type="default_screening_capacity",
                    reason=(
                        "Runtime relied on a governed screening capacity default that strongly influences "
                        "compartment concentration scaling."
                    ),
                    severity=Severity.INFO,
                    source_reference_ids=entry.source_reference_ids,
                    quality_flag_codes=entry.quality_flag_codes,
                )
            )
        elif entry.source_classification == SourceClassification.HEURISTIC:
            drivers.append(
                UncertaintyDriver(
                    parameter=entry.parameter,
                    driver_type="heuristic_parameter",
                    reason="Runtime used a heuristic-classified parameter value.",
                    severity=Severity.WARNING,
                    source_reference_ids=entry.source_reference_ids,
                    quality_flag_codes=entry.quality_flag_codes,
                )
            )
        elif entry.source_classification == SourceClassification.CURATED_DEFAULT:
            drivers.append(
                UncertaintyDriver(
                    parameter=entry.parameter,
                    driver_type="default_heavy_parameter",
                    reason="Runtime relied on a governed curated default instead of a scenario-specific override.",
                    severity=Severity.INFO,
                    source_reference_ids=entry.source_reference_ids,
                    quality_flag_codes=entry.quality_flag_codes,
                )
            )

    if any(flag.code == "unexecuted_treatment_assumption" for flag in result.run_summary.warnings):
        drivers.append(
            UncertaintyDriver(
                parameter="treatment_assumptions",
                driver_type="unexecuted_treatment_assumption",
                reason=(
                    "One or more treatment assumptions were preserved for provenance but were not "
                    "executable within the current screening kernel."
                ),
                severity=Severity.WARNING,
                source_reference_ids=[],
                quality_flag_codes=["unexecuted_treatment_assumption"],
            )
        )

    if result.run_summary.run_mode == RunMode.TIME_BUCKET:
        bucket_count = len({surface.time_window.bucket_label for surface in result.surfaces})
        drivers.append(
            UncertaintyDriver(
                parameter="time_bucket_mode",
                driver_type="time_bucket_interpretive_burden",
                reason=(
                    f"Time-bucket execution emits {bucket_count} buckets that require explicit temporal interpretation."
                ),
                severity=Severity.WARNING if bucket_count > 12 else Severity.INFO,
                source_reference_ids=[],
                quality_flag_codes=[],
            )
        )

    scoped_media = sorted({release_fraction.medium.value for release_fraction in scenario.release_fractions})
    if len(scoped_media) > 1:
        drivers.append(
            UncertaintyDriver(
                parameter="release_fractions",
                driver_type="multi_medium_simplification_burden",
                reason=(
                    "Multiple release media are represented within a simplified screening kernel rather than "
                    "explicit transfer dynamics."
                ),
                severity=Severity.WARNING if len(scoped_media) > 2 else Severity.INFO,
                source_reference_ids=[],
                quality_flag_codes=[],
            )
        )

    drivers = sorted(
        drivers,
        key=lambda item: (
            SEVERITY_RANK[item.severity],
            DRIVER_PRIORITY.get(item.driver_type, 99),
            item.parameter,
        ),
    )
    top_drivers = drivers[:5]
    summary_lines = [
        (
            f"{len(top_drivers)} deterministic uncertainty drivers were ranked for "
            f"{result.run_summary.model_family.value}."
        ),
        "These drivers explain reviewer attention points only; they are not probabilistic confidence intervals.",
    ]
    if top_drivers:
        summary_lines.append(
            "Top drivers: "
            + ", ".join(f"{driver.parameter} ({driver.driver_type})" for driver in top_drivers)
            + "."
        )
    limitations = [
        LimitationNote(
            code="deterministic_uncertainty_only",
            message=(
                "Uncertainty summary ranks deterministic reviewer-facing drivers only and does not provide "
                "Monte Carlo outputs, confidence intervals, or probabilistic bounds."
            ),
        )
    ]
    if any(entry.source_classification == SourceClassification.CURATED_DEFAULT for entry in manifest.entries):
        limitations.append(
            LimitationNote(
                code="default_dependent_runtime",
                message="Some runtime outputs depend on curated defaults rather than scenario-specific measurements.",
            )
        )
    return RunUncertaintySummary(
        scenario_id=scenario.scenario_id,
        run_id=result.run_summary.run_id,
        model_family=result.run_summary.model_family,
        top_drivers=top_drivers,
        summary_lines=summary_lines,
        limitations=limitations,
        provenance=provenance_builder.bundle(_collect_source_references(scenario, result)),
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
        or "Summarize whether the run is scientifically reviewable within the declared Fate MCP boundary."
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
        loss_dominance_lines=review_packet.loss_dominance_lines,
        loss_transition_lines=review_packet.loss_transition_lines,
        limitations=review_packet.limitations,
    )


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


def _validated_target_modules(
    requested_target_modules: list[str],
    handoff_profile: RegulatoryHandoffProfile,
) -> list[str]:
    normalized = []
    for item in requested_target_modules:
        stripped = item.strip()
        if not stripped:
            continue
        if stripped not in normalized:
            normalized.append(stripped)
    if not normalized:
        return [handoff_profile.target_module]
    if normalized != [handoff_profile.target_module]:
        raise FateValidationError(
            code="regulatory_handoff_target_module_mismatch",
            message=(
                f"Requested target_modules {normalized} do not match the governed target module "
                f"{handoff_profile.target_module} for profile {handoff_profile.profile_id}."
            ),
            suggestion="Use the profile's governed target module or omit target_modules entirely.",
            details={
                "requestedTargetModules": normalized,
                "governedTargetModule": handoff_profile.target_module,
                "profileId": handoff_profile.profile_id,
            },
        )
    return [handoff_profile.target_module]


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
    if missing_required_fields:
        raise FateValidationError(
            code="regulatory_handoff_profile_requirement_unmet",
            message=(
                f"Regulatory handoff profile {handoff_profile.profile_id} requires fields that were not populated: "
                f"{missing_required_fields}."
            ),
            suggestion="Adjust the handoff profile or the crosswalk export logic so all required fields are populated.",
            details={"missingRequiredFields": missing_required_fields},
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


def _default_regulatory_handoff_resolution_preview(
    defaults_registry: DefaultsRegistry,
    requested_target_modules: list[str] | None = None,
) -> RegulatoryHandoffResolutionPreview:
    profile = defaults_registry.regulatory_handoff_profile("exposure_scenario_mcp_v1")
    if profile is None:
        raise FateValidationError(
            code="missing_default_regulatory_handoff_profile",
            message="Default regulatory handoff profile exposure_scenario_mcp_v1 is not declared.",
            suggestion="Restore the default governed handoff profile in defaults/v1/regulatory_handoff_profiles.json.",
        )
    status = "resolved"
    issues: list[str] = []
    allowed_target_modules = [profile.target_module]
    target_modules_preview = allowed_target_modules
    if requested_target_modules:
        try:
            target_modules_preview = _validated_target_modules(requested_target_modules, profile)
        except FateValidationError as exc:
            status = "mismatch"
            issues.append(exc.payload.message)
            target_modules_preview = requested_target_modules
    return RegulatoryHandoffResolutionPreview(
        resolved_profile_id=profile.profile_id,
        resolution_method="default_profile",
        resolution_basis=profile.profile_id,
        resolution_confidence=1.0,
        target_module=profile.target_module,
        allowed_target_modules=allowed_target_modules,
        target_modules_preview=target_modules_preview,
        downstream_field=profile.downstream_field,
        required_entry_fields=profile.required_entry_fields,
        status=status,
        issues=issues,
        tool_request_template=profile.tool_request_template,
        response_summary_template=profile.response_summary_template,
    )


def _review_evidence_line(
    field_name: str,
    resolution_preview: RegulatoryHandoffResolutionPreview,
    package: RegulatoryHandoffPackage,
    summary: RegulatoryHandoffPackageSummary,
) -> str | None:
    if field_name == "target_module":
        return f"Target module: {summary.target_module}."
    if field_name == "downstream_field":
        return f"Downstream field: {summary.downstream_field}."
    if field_name == "entry_count":
        return f"Crosswalk entry count: {summary.entry_count}."
    if field_name == "route_hints" and summary.route_hints:
        return "Route hints: " + ", ".join(summary.route_hints) + "."
    if field_name == "time_window_modes" and summary.time_window_modes:
        return "Time window modes: " + ", ".join(item.value for item in summary.time_window_modes) + "."
    if field_name == "mediums" and summary.mediums:
        return "Media: " + ", ".join(item.value for item in summary.mediums) + "."
    if field_name == "compartments" and summary.compartments:
        return "Compartments: " + ", ".join(item.value for item in summary.compartments) + "."
    if field_name == "equation_lines" and summary.equation_lines:
        return "Equation trace: " + " | ".join(summary.equation_lines)
    if field_name == "limitations" and package.limitations:
        return "Limitations: " + "; ".join(note.message for note in package.limitations)
    if field_name == "profile_resolution_method":
        line = f"Profile resolution: {package.profile_resolution_method}"
        if resolution_preview.resolution_basis:
            line += f" using {resolution_preview.resolution_basis}"
        return line + "."
    return None


def _build_regulatory_review_checklist(
    handoff_profile: RegulatoryHandoffProfile,
    resolution_preview: RegulatoryHandoffResolutionPreview,
    package: RegulatoryHandoffPackage,
    summary: RegulatoryHandoffPackageSummary,
) -> list[RegulatoryHandoffReviewChecklistItem]:
    checklist_items: list[RegulatoryHandoffReviewChecklistItem] = []
    for template in handoff_profile.review_checklist:
        unknown_fields = sorted(
            field for field in template.evidence_hint_fields if field not in REGULATORY_REVIEW_EVIDENCE_FIELDS
        )
        if unknown_fields:
            raise FateValidationError(
                code="invalid_regulatory_handoff_review_checklist_field",
                message=(
                    f"Regulatory handoff profile {handoff_profile.profile_id} declares unknown review checklist "
                    f"evidence fields: {unknown_fields}."
                ),
                suggestion="Limit review checklist evidence_hint_fields to fields exposed by the review packet builder.",
                details={"unknownEvidenceHintFields": unknown_fields},
            )
        evidence_lines = []
        for field_name in template.evidence_hint_fields:
            line = _review_evidence_line(field_name, resolution_preview, package, summary)
            if line and line not in evidence_lines:
                evidence_lines.append(line)
        checklist_items.append(
            RegulatoryHandoffReviewChecklistItem(
                code=template.code,
                prompt=template.prompt,
                rationale=template.rationale,
                status=(
                    "ready_for_assessor_confirmation"
                    if evidence_lines
                    else "attention_required"
                ),
                evidence_lines=evidence_lines,
            )
        )
    return checklist_items


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
