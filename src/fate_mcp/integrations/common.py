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

# Mock acknowledgement schema URLs by target consumer profile.
# In production, these should be served by the downstream MCPs themselves.
TARGET_MODULE_ACKNOWLEDGEMENT_SCHEMA_URLS = {
    "exposure_scenario_mcp_v1": "https://toxmcp.example/contracts/schemas/exposureScenarioAcknowledgement.v1.json",
    "toxclaw_orchestration_v1": "https://toxmcp.example/contracts/schemas/toxclawHandoffAcknowledgement.v1.json",
    "echa_csr_v1": "https://toxmcp.example/contracts/schemas/echaCsrConcentrationAnnex.v1.json",
    "epa_pmn_v1": "https://toxmcp.example/contracts/schemas/epaPmnEnvironmentalFateSection.v1.json",
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



def _scientific_unsuitability_lines(escalation_concerns: list[str]) -> list[str]:
    lines = []
    for concern in escalation_concerns:
        val = getattr(concern, 'value', concern)
        if val == "extreme_persistence":
            lines.append("Scientific unsuitability trigger: extreme persistence requires higher-tier modeling or prolonged clearance anchors.")
        elif val == "strong_spatial_heterogeneity":
            lines.append("Scientific unsuitability trigger: strong spatial heterogeneity requires GIS/routed spatial dispersion.")
        elif val == "point_source_plume_dependence":
            lines.append("Scientific unsuitability trigger: point-source plume dependence requires explicit near-field dispersion models.")
        elif val == "pfas_like_transport":
            lines.append("Scientific unsuitability trigger: PFAS-like transport concerns require specialized multimedia distribution logic.")
        elif val == "jurisdictional_probabilistic_requirement":
            lines.append("Scientific unsuitability trigger: jurisdictional requirement for probabilistic output cannot be satisfied by deterministic screening.")
        else:
            lines.append(f"Scientific unsuitability trigger: flagged for {val}.")
    return sorted(lines)



def _selection_recommendation_unsuitability_lines(
    recommendation: ModelFamilySelectionRecommendation,
) -> list[str]:
    lines: list[str] = []
    for note in recommendation.limitations:
        if note.message.startswith("Scientific unsuitability trigger:"):
            lines.append(note.message)
    return sorted(set(lines))


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
    if transport_regime_stability_status == "boundary_sensitive_post_release_recovery_regime":
        return ScientificHighlightedClaimChallengeStatus.CHALLENGE
    if transport_regime_stability_status == "boundary_sensitive_post_release_recovery_pace":
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
    elif transport_regime_stability_status == "boundary_sensitive_post_release_recovery_regime":
        lines.append(
            "Challenge because this claim is anchored close to the one-turnover post-release flushing boundary, where modest recovery-window or residence-time shifts can change the reviewer-facing recovery interpretation."
        )
    elif transport_regime_stability_status == "post_release_flushing_recovery_regime":
        lines.append(
            "Challenge because this claim depends on a post-release recovery window, so reviewer confidence depends on whether the elapsed post-release interval is long enough to support the claimed flushing or retention interpretation."
        )
    elif transport_regime_stability_status == "boundary_sensitive_post_release_recovery_pace":
        lines.append(
            "Challenge because this claim is anchored close to the combined-loss half-recovery pace boundary, where modest recovery-window or loss-constant shifts can change whether retained release-stop mass is still above or already below the 50% anchor."
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
    if any("post_release_boundary_transition" in name for name in fixture_names):
        return (
            "boundary_sensitive_post_release_recovery_regime",
            [
                "This claim is anchored near the one-turnover post-release flushing boundary, where retained release-stop mass can still be interpreted as either recovery-limited or flushing-dominant.",
                "The supporting anchors are intended to show how small recovery-window or residence-time shifts move the run across the post-release flushing transition rather than merely changing the magnitude of retained mass.",
            ],
        )
    if any("post_release_half_recovery" in name for name in fixture_names):
        return (
            "boundary_sensitive_post_release_recovery_pace",
            [
                "This claim is anchored around the combined-loss half-recovery pace, where retained release-stop mass sits near the 50% recovery anchor under the resolved degradation-plus-clearance constants.",
                "The supporting anchors are intended to show how modest post-release window shifts move the run from pre-half-recovery to beyond-half-recovery interpretation under the same chemistry and residence-time assumptions.",
            ],
        )
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
    if transport_regime_stability_status == "boundary_sensitive_post_release_recovery_regime":
        questions.append(
            "Could a modest residence-time or post-release recovery-window change move this scenario across the one-turnover flushing boundary after release stop?"
        )
    if transport_regime_stability_status == "boundary_sensitive_post_release_recovery_pace":
        questions.append(
            "Could a modest post-release recovery-window or loss-constant change move this scenario across the combined-loss half-recovery boundary for retained release-stop mass?"
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



def _advective_post_release_regime_support_ready(
    claim_summaries_by_id: dict[str, ScientificMethodsDossierClaimSummary],
) -> bool:
    regime_claim = claim_summaries_by_id.get("advective_post_release_flushing_regime_transition_v1")
    if not regime_claim or not regime_claim.covered:
        return False
    if regime_claim.support_strength != ScientificClaimSupportStrength.MULTI_ANCHOR_MULTI_TIER:
        return False
    if "reference_style" not in regime_claim.supporting_validation_tiers:
        return False
    return {
        "hand_worked_advective_post_release_bucket_anchor",
        "hand_worked_advective_post_release_boundary_transition_reference_fixture",
        "hand_worked_advective_post_release_recovery_reference_fixture",
        "hand_worked_advective_post_release_recovery_sensitivity_fixture",
        "hand_worked_advective_post_release_extended_flushing_sensitivity_fixture",
    }.issubset(set(regime_claim.supporting_reference_types))



def _advective_post_release_directionality_support_ready(
    claim_summaries_by_id: dict[str, ScientificMethodsDossierClaimSummary],
) -> bool:
    directionality_claim = claim_summaries_by_id.get("advective_post_release_flushing_directionality_v1")
    if not directionality_claim or not directionality_claim.covered:
        return False
    if (
        directionality_claim.support_strength
        != ScientificClaimSupportStrength.MULTI_ANCHOR_MULTI_TIER
    ):
        return False
    if "reference_style" not in directionality_claim.supporting_validation_tiers:
        return False
    return {
        "hand_worked_advective_post_release_bucket_anchor",
        "hand_worked_advective_post_release_subboundary_sensitivity_fixture",
        "hand_worked_advective_post_release_boundary_transition_reference_fixture",
        "hand_worked_advective_post_release_recovery_reference_fixture",
        "hand_worked_advective_post_release_extended_flushing_sensitivity_fixture",
    }.issubset(set(directionality_claim.supporting_reference_types))



def _advective_post_release_pace_support_ready(
    claim_summaries_by_id: dict[str, ScientificMethodsDossierClaimSummary],
) -> bool:
    pace_claim = claim_summaries_by_id.get("advective_post_release_half_recovery_pace_v1")
    if not pace_claim or not pace_claim.covered:
        return False
    if pace_claim.support_strength != ScientificClaimSupportStrength.MULTI_ANCHOR_MULTI_TIER:
        return False
    if "reference_style" not in pace_claim.supporting_validation_tiers:
        return False
    return {
        "hand_worked_advective_post_release_bucket_anchor",
        "hand_worked_advective_post_release_pre_half_recovery_sensitivity_fixture",
        "hand_worked_advective_post_release_half_recovery_reference_fixture",
        "hand_worked_advective_post_release_recovery_reference_fixture",
    }.issubset(set(pace_claim.supporting_reference_types))



def _advective_post_release_pace_directionality_support_ready(
    claim_summaries_by_id: dict[str, ScientificMethodsDossierClaimSummary],
) -> bool:
    directionality_claim = claim_summaries_by_id.get(
        "advective_post_release_half_recovery_directionality_v1"
    )
    if not directionality_claim or not directionality_claim.covered:
        return False
    if (
        directionality_claim.support_strength
        != ScientificClaimSupportStrength.MULTI_ANCHOR_MULTI_TIER
    ):
        return False
    if "reference_style" not in directionality_claim.supporting_validation_tiers:
        return False
    return {
        "hand_worked_advective_post_release_bucket_anchor",
        "hand_worked_advective_post_release_pre_half_recovery_sensitivity_fixture",
        "hand_worked_advective_post_release_half_recovery_reference_fixture",
        "hand_worked_advective_post_release_recovery_reference_fixture",
        "hand_worked_advective_post_release_extended_flushing_sensitivity_fixture",
    }.issubset(set(directionality_claim.supporting_reference_types))



def _advective_post_release_late_recovery_support_ready(
    claim_summaries_by_id: dict[str, ScientificMethodsDossierClaimSummary],
) -> bool:
    late_recovery_claim = claim_summaries_by_id.get(
        "advective_post_release_late_recovery_regime_v1"
    )
    if not late_recovery_claim or not late_recovery_claim.covered:
        return False
    if "sensitivity" not in late_recovery_claim.supporting_validation_tiers:
        return False
    return {
        "hand_worked_advective_post_release_extended_flushing_sensitivity_fixture",
    }.issubset(set(late_recovery_claim.supporting_reference_types))



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
    post_release_regime_support_ready = _advective_post_release_regime_support_ready(
        claim_summaries_by_id
    )
    post_release_directionality_support_ready = _advective_post_release_directionality_support_ready(
        claim_summaries_by_id
    )
    post_release_pace_support_ready = _advective_post_release_pace_support_ready(
        claim_summaries_by_id
    )
    post_release_pace_directionality_support_ready = (
        _advective_post_release_pace_directionality_support_ready(claim_summaries_by_id)
    )
    post_release_late_recovery_support_ready = (
        _advective_post_release_late_recovery_support_ready(claim_summaries_by_id)
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
            if (
                item.loss_regime_stability_status != "near_parity_transition"
                and item.transport_regime_stability_status
                != "boundary_sensitive_post_release_recovery_regime"
            ):
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
        if (
            item.transport_regime_stability_status == "boundary_sensitive_post_release_recovery_regime"
            and not post_release_regime_support_ready
        ):
            summaries.append(
                ScientificMethodsRecommendedActionSummary(
                    action=(
                        f"{item.display_name}: add a boundary-style post-release recovery anchor around the one-turnover flushing threshold so reviewers can see how easily the retained-mass interpretation changes after release stop."
                    ),
                    priority=ScientificMethodsRecommendedActionPriority.HIGH,
                    promotion_impact=ScientificMethodsRecommendedActionPromotionImpact.STRENGTHENING,
                    action_class="regime_transition",
                    source_claim_id=item.claim_id,
                    source_claim_display_name=item.display_name,
                )
            )
        if (
            item.transport_regime_stability_status
            == "boundary_sensitive_post_release_recovery_pace"
            and not post_release_pace_directionality_support_ready
        ):
            summaries.append(
                ScientificMethodsRecommendedActionSummary(
                    action=(
                        f"{item.display_name}: add a farther-beyond-half-recovery anchor so reviewers can see retained release-stop mass moving materially below the 50% anchor rather than only crossing it."
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
                transport_authority_support_ready
                and transition_reference_support_ready
                and post_release_regime_support_ready
                and post_release_directionality_support_ready
                and post_release_pace_support_ready
                and post_release_pace_directionality_support_ready
                and post_release_late_recovery_support_ready
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
    # Let us intercept unsuitability in the caller because unsuitability comes from the run parameter manifest, not recommended actions.
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
    selected_claim_limit = 8 if model_family.value == "advective_screening_mass_balance" else 5
    selected_claims = list(ranked_claims[:selected_claim_limit])
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
        post_release_transition_claim = next(
            (
                item
                for item in ranked_claims
                if item.claim_id == "advective_post_release_flushing_regime_transition_v1"
            ),
            None,
        )
        if post_release_transition_claim and all(
            item.claim_id != post_release_transition_claim.claim_id for item in selected_claims
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
            selected_claims[replace_index] = post_release_transition_claim
        post_release_directionality_claim = next(
            (
                item
                for item in ranked_claims
                if item.claim_id == "advective_post_release_flushing_directionality_v1"
            ),
            None,
        )
        if post_release_directionality_claim and all(
            item.claim_id != post_release_directionality_claim.claim_id
            for item in selected_claims
        ):
            protected_ids = {
                "advective_mixed_loss_transition_margin_v1",
                "advective_residence_time_turnover_regime_v1",
                "advective_post_release_flushing_recovery_v1",
                "advective_post_release_flushing_regime_transition_v1",
                "advective_post_release_half_recovery_pace_v1",
            }
            replace_index = next(
                (
                    idx
                    for idx in range(len(selected_claims) - 1, -1, -1)
                    if selected_claims[idx].claim_id not in protected_ids
                ),
                len(selected_claims) - 1,
            )
            selected_claims[replace_index] = post_release_directionality_claim
        post_release_pace_claim = next(
            (
                item
                for item in ranked_claims
                if item.claim_id == "advective_post_release_half_recovery_pace_v1"
            ),
            None,
        )
        if post_release_pace_claim and all(
            item.claim_id != post_release_pace_claim.claim_id for item in selected_claims
        ):
            protected_ids = {
                "advective_mixed_loss_transition_margin_v1",
                "advective_residence_time_turnover_regime_v1",
                "advective_post_release_flushing_recovery_v1",
                "advective_post_release_flushing_regime_transition_v1",
                "advective_post_release_flushing_directionality_v1",
            }
            replace_index = next(
                (
                    idx
                    for idx in range(len(selected_claims) - 1, -1, -1)
                    if selected_claims[idx].claim_id not in protected_ids
                ),
                len(selected_claims) - 1,
            )
            selected_claims[replace_index] = post_release_pace_claim
        post_release_pace_directionality_claim = next(
            (
                item
                for item in ranked_claims
                if item.claim_id == "advective_post_release_half_recovery_directionality_v1"
            ),
            None,
        )
        if post_release_pace_directionality_claim and all(
            item.claim_id != post_release_pace_directionality_claim.claim_id
            for item in selected_claims
        ):
            protected_ids = {
                "advective_mixed_loss_transition_margin_v1",
                "advective_residence_time_turnover_regime_v1",
                "advective_post_release_flushing_recovery_v1",
                "advective_post_release_flushing_regime_transition_v1",
                "advective_post_release_flushing_directionality_v1",
                "advective_post_release_half_recovery_pace_v1",
            }
            replace_index = next(
                (
                    idx
                    for idx in range(len(selected_claims) - 1, -1, -1)
                    if selected_claims[idx].claim_id not in protected_ids
                ),
                len(selected_claims) - 1,
            )
            selected_claims[replace_index] = post_release_pace_directionality_claim
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
                "advective_post_release_flushing_regime_transition_v1",
                "advective_post_release_flushing_directionality_v1",
                "advective_post_release_half_recovery_pace_v1",
                "advective_post_release_half_recovery_directionality_v1",
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


