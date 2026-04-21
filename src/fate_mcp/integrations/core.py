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
    DefaultEvidenceStatus,
    ReleaseScenarioFitAssessment,
    RunDefaultProofPosture,
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


from .common import CAPACITY_PARAMETERS, CONSERVATIVE_EVIDENCE_QUALITIES, DEFAULT_PHYSCHEM_RELATIVE_SPREAD_THRESHOLD, DEFAULT_WEIGHTING_STRATEGY, DRIVER_PRIORITY, SEVERITY_RANK, _applicability_lines, _collect_source_references, _conflict_metric_value, _ensure_scenario_matches_result, _fit_for_purpose_from_result, _inverse_reconciliation_value, _matching_scope_entries, _missing_required_inputs, _normalized_evidence_quality, _resolve_model_family_applicability, _resolve_substance_class, _scientific_unsuitability_lines, _transform_reconciliation_value

def build_concentration_surface_bundle(result: ConcentrationEstimationResult) -> ConcentrationSurfaceBundle:
    bundle = ConcentrationSurfaceBundle(
        scenario_id=result.run_summary.scenario_id,
        surfaces=result.surfaces,
        run_summary=result.run_summary,
        assumptions=result.assumptions,
        dependencies=[
            DependencyDescriptor(name="environmental-fate-mcp", version=VERSION, role="producer"),
            DependencyDescriptor(
                name=result.run_summary.model_family.value,
                version=VERSION,
                role="model_family",
            ),
        ],
    )
    # Compute a content-addressed tamper-evident hash over the bundle payload (excluding the hash itself).
    payload = bundle.model_dump(mode="json", exclude={"integrity_hash"})
    hash_input = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    bundle.integrity_hash = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()
    return bundle



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
    base_only_keys = sorted(set(base_by_key) - set(candidate_by_key))
    candidate_only_keys = sorted(set(candidate_by_key) - set(base_by_key))

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
    limitations = []
    blockers = []
    quality_flags = []
    if base_only_keys or candidate_only_keys:
        limitations.append(
            LimitationNote(
                code="unmatched_comparison_surfaces",
                message=(
                    "Comparison contains unmatched surface identities; matched deltas cover only the "
                    "intersection of base and candidate surface sets."
                ),
            )
        )
        quality_flags.append(
            QualityFlag(
                code="comparison_surface_set_mismatch",
                severity=Severity.WARNING,
                message="Base and candidate results do not expose the same compartment/time-bucket surface set.",
            )
        )
        dominant_drivers = [
            *dominant_drivers,
            *[
                f"base_only_surface={medium.value}/{compartment.value}/{bucket_label or 'steady_state'}"
                for medium, compartment, bucket_label in base_only_keys[:2]
            ],
            *[
                f"candidate_only_surface={medium.value}/{compartment.value}/{bucket_label or 'steady_state'}"
                for medium, compartment, bucket_label in candidate_only_keys[:2]
            ],
        ]

    return FateScenarioComparisonRecord(
        base_scenario_id=request.base_result.run_summary.scenario_id,
        candidate_scenario_id=request.candidate_result.run_summary.scenario_id,
        surface_deltas=deltas,
        base_only_surface_keys=[
            f"{medium.value}/{compartment.value}/{bucket_label or 'steady_state'}"
            for medium, compartment, bucket_label in base_only_keys
        ],
        candidate_only_surface_keys=[
            f"{medium.value}/{compartment.value}/{bucket_label or 'steady_state'}"
            for medium, compartment, bucket_label in candidate_only_keys
        ],
        changed_assumptions=changed_assumptions,
        dominant_drivers=dominant_drivers,
        provenance=provenance_builder.bundle(),
        limitations=limitations,
        blockers=blockers,
        quality_flags=quality_flags,
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
                suggestion="Provide evidence in the canonical Environmental Fate MCP unit for the parameter.",
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
    substance_class = _resolve_substance_class(scenario)
    supported_scope_matches = _matching_scope_entries(
        substance_class,
        applicability_profile.supported_substance_classes,
    )
    unsupported_scope_matches = _matching_scope_entries(
        substance_class,
        applicability_profile.unsupported_substance_classes,
    )
    missing_required_inputs = _missing_required_inputs(
        scenario,
        run_options,
        applicability_profile,
        provenance_builder.defaults_registry,
    )
    applicability_lines = _applicability_lines(
        applicability_profile,
        run_options.fit_for_purpose,
        substance_class=substance_class,
        supported_scope_matches=supported_scope_matches,
        unsupported_scope_matches=unsupported_scope_matches,
        missing_required_inputs=missing_required_inputs,
    )
    reasons = []
    scientific_unsuitability_lines = _scientific_unsuitability_lines(run_options.escalation_concerns)
    score = 1.0
    penalties = applicability_profile.fit_score_penalties
    runtime_supported_parameters = provenance_builder.defaults_registry.runtime_supported_parameter_units()
    if run_options.fit_for_purpose not in applicability_profile.fit_for_purpose:
        score -= penalties.unsupported_fit_for_purpose
        reasons.append(
            f"Requested fit_for_purpose {run_options.fit_for_purpose.value} is not declared for "
            f"model family {run_options.model_family.value}."
        )
    if run_options.run_mode == RunMode.TIME_BUCKET and run_options.bucket_count > 12:
        score -= penalties.excessive_time_bucket_count
        reasons.append("Large time-bucket count increases interpretive burden for a screening workflow.")
    if any(
        item.execution_mode != "pre_release_global"
        for item in scenario.treatment_assumptions
    ):
        score -= penalties.provenance_only_treatments
        reasons.append(
            "Some treatment assumptions remain provenance-only because they are not executable pre-release global removal."
        )
    if len(scenario.release_fractions) > 3:
        score -= penalties.multi_medium_release_complexity
        reasons.append("Many release media are being approximated with a simple screening kernel.")
    unsupported_parameters = sorted(
        {
            record.parameter
            for record in scenario.parameter_records
            if record.parameter not in runtime_supported_parameters
        }
    )
    if unsupported_parameters:
        score -= penalties.unsupported_runtime_parameters
        reasons.append(
            "Some parameter records are preserved for provenance but are not consumed by the reference runtime: "
            + ", ".join(sorted(unsupported_parameters))
        )
    if missing_required_inputs:
        score -= penalties.missing_required_inputs
        reasons.append(
            "Required applicability inputs could not be confirmed: "
            + ", ".join(missing_required_inputs)
        )
        scientific_unsuitability_lines.append(
            "Scientific applicability cannot be promoted to ready review until all governed required inputs are confirmed."
        )
    if substance_class is None:
        score -= penalties.missing_substance_class
        reasons.append(
            "chemical_identity is missing a canonical substance_class entry, so in-scope applicability cannot be confirmed."
        )
        scientific_unsuitability_lines.append(
            "Scientific applicability cannot be promoted to ready review until chemical_identity.substance_class is declared."
        )
    elif unsupported_scope_matches:
        score -= penalties.unsupported_substance_class
        reasons.append(
            "Resolved substance class matches declared unsupported scope for this model family: "
            + "; ".join(unsupported_scope_matches)
        )
        scientific_unsuitability_lines.append(
            "Scientific unsuitability trigger: resolved substance class is out of scope for the selected model family."
        )
    elif applicability_profile.supported_substance_classes and not supported_scope_matches:
        score -= penalties.missing_substance_class
        reasons.append(
            "Resolved substance class could not be confirmed against the declared supported scope examples."
        )
        scientific_unsuitability_lines.append(
            "Scientific applicability remains review-needed because the resolved substance class could not be mapped to declared supported scope."
        )
    if unsupported_scope_matches:
        verdict = "not_applicable"
    elif score >= applicability_profile.fit_score_threshold:
        verdict = "good_fit"
    else:
        verdict = "review_needed"
    return ReleaseScenarioFitAssessment(
        fit_score=max(score, 0.0),
        model_family=run_options.model_family,
        fit_for_purpose=run_options.fit_for_purpose,
        verdict=verdict,
        reasons=reasons,
        applicability_profile=applicability_profile,
        applicability_lines=applicability_lines,
        scientific_unsuitability_lines=sorted(set(scientific_unsuitability_lines)),
    )


def _default_rebaseline_delta(
    payload: dict[str, object],
) -> tuple[float | None, float | None, float | None]:
    current_value = payload.get("value")
    previous_value = payload.get("previousValue", current_value)
    if not isinstance(current_value, (int, float)) or not isinstance(previous_value, (int, float)):
        return None, None, None
    delta = float(current_value) - float(previous_value)
    relative_delta = None
    if abs(float(previous_value)) > 0.0:
        relative_delta = delta / float(previous_value)
    elif delta != 0.0:
        relative_delta = math.inf
    return float(previous_value), delta, relative_delta


def _default_evidence_summary(
    entries: list[RunParameterManifestEntry],
    defaults_registry: DefaultsRegistry,
) -> dict[str, object]:
    core_default_entries = [
        entry
        for entry in entries
        if (
            entry.runtime_consumed
            and entry.parameter in defaults_registry.core_defaults["parameters"]
            and entry.source_classification == SourceClassification.CURATED_DEFAULT
        )
    ]
    override_entries = [
        entry
        for entry in entries
        if entry.runtime_consumed and entry.source_classification == SourceClassification.USER_INPUT
    ]
    source_backed_defaults = sorted(
        entry.parameter
        for entry in core_default_entries
        if defaults_registry.parameter_evidence_tier(entry.parameter)
        != "tier_3_internal_screening_assumption"
    )
    legacy_continuity_defaults = sorted(
        entry.parameter
        for entry in core_default_entries
        if defaults_registry.parameter_evidence_tier(entry.parameter)
        == "tier_3_internal_screening_assumption"
    )
    governed_override_parameters = sorted({entry.parameter for entry in override_entries})
    if legacy_continuity_defaults:
        proof_posture = RunDefaultProofPosture.LEGACY_CONTINUITY_EXTENSION
    elif governed_override_parameters and source_backed_defaults:
        proof_posture = RunDefaultProofPosture.REBASELINED_DEFAULTS_WITH_GOVERNED_OVERRIDES
    elif governed_override_parameters:
        proof_posture = RunDefaultProofPosture.SCENARIO_SPECIFIC_NON_DEFAULT_VALUES
    else:
        proof_posture = RunDefaultProofPosture.REBASELINED_SHIPPED_DEFAULTS
    if legacy_continuity_defaults:
        status = DefaultEvidenceStatus.LEGACY_CONTINUITY_ASSUMPTIONS_PRESENT
    elif override_entries:
        status = DefaultEvidenceStatus.GOVERNED_OVERRIDES_PRESENT
    else:
        status = DefaultEvidenceStatus.SOURCE_BACKED_DEFAULTS
    lines = [
        f"Runtime consumed {len(core_default_entries)} governed core default parameter(s).",
    ]
    if source_backed_defaults:
        lines.append(
            "Source-backed defaults consumed: " + ", ".join(source_backed_defaults[:6]) + "."
        )
    if override_entries:
        lines.append(
            "Governed overrides consumed: "
            + ", ".join(sorted(entry.parameter for entry in override_entries)[:6])
            + "."
        )
    else:
        lines.append("No governed user overrides displaced the shipped core defaults in this run.")
    if legacy_continuity_defaults:
        lines.append(
            "Legacy continuity defaults remain active for: "
            + ", ".join(legacy_continuity_defaults[:6])
            + "."
        )
    else:
        lines.append("No legacy continuity defaults were consumed by runtime.")
    proof_lines = [f"Run default proof posture: {proof_posture.value}."]
    if source_backed_defaults:
        proof_lines.append(
            "Rebaselined shipped defaults remain active for: "
            + ", ".join(source_backed_defaults[:6])
            + "."
        )
    if governed_override_parameters:
        proof_lines.append(
            "Scenario-specific governed overrides displace the shipped default path for: "
            + ", ".join(governed_override_parameters[:6])
            + "."
        )
    if legacy_continuity_defaults:
        proof_lines.append(
            "Legacy continuity extensions remain active and block reviewer-grade default proof for: "
            + ", ".join(legacy_continuity_defaults[:6])
            + "."
        )

    scientific_change_lines: list[str] = []
    default_sensitivity_lines: list[str] = []
    material_default_sensitivity = False
    for parameter in source_backed_defaults:
        payload = defaults_registry.core_defaults["parameters"].get(parameter, {})
        previous_value, delta, relative_delta = _default_rebaseline_delta(payload)
        current_value = payload.get("value")
        unit = payload.get("unit")
        change_note = payload.get("scientificChangeNote")
        if change_note:
            scientific_change_lines.append(f"{parameter}: {change_note}")
        if delta is None or current_value is None or previous_value is None:
            continue
        if abs(delta) > 0.0:
            relative_text = (
                "n/a"
                if relative_delta is None or not math.isfinite(relative_delta)
                else f"{relative_delta:.3g}"
            )
            scientific_change_lines.append(
                f"{parameter}: shipped default rebaseline moved from {previous_value:g} to "
                f"{float(current_value):g} {unit or ''}".rstrip()
                + f" (delta={delta:g}, relative_delta={relative_text})."
            )
        if payload.get("materialOutputChange"):
            material_default_sensitivity = True
            default_sensitivity_lines.append(
                f"{parameter}: release metadata marks the shipped default rebaseline as materially output-affecting for reviewer attention."
            )
        elif abs(delta) > 0.0:
            default_sensitivity_lines.append(
                f"{parameter}: shipped default changed in this release but is not flagged as a material output delta."
            )
    if governed_override_parameters:
        default_sensitivity_lines.append(
            "Scenario-specific governed overrides limit direct dependence on the shipped default path for the overridden parameters."
        )
    if not scientific_change_lines:
        scientific_change_lines.append(
            "Runtime-consumed shipped defaults carry forward the source-backed rebaseline without numeric delta in this release."
        )
    if not default_sensitivity_lines:
        default_sensitivity_lines.append(
            "No material shipped-default delta is recorded for the runtime-consumed rebaselined defaults in this release."
        )
    return {
        "status": status,
        "proof_posture": proof_posture,
        "lines": lines,
        "proof_lines": proof_lines,
        "scientific_change_lines": scientific_change_lines,
        "default_sensitivity_lines": default_sensitivity_lines,
        "rebaselined_default_parameters": source_backed_defaults,
        "governed_override_parameters": governed_override_parameters,
        "material_default_sensitivity": material_default_sensitivity,
        "core_default_assumption_count": len(core_default_entries),
    }


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
    default_evidence_summary = _default_evidence_summary(
        entries,
        provenance_builder.defaults_registry,
    )
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
        (
            f"Default evidence posture: {default_evidence_summary['status'].value} with "
            f"{default_evidence_summary['core_default_assumption_count']} runtime-consumed core default assumption(s)."
        ),
        f"Run default proof posture: {default_evidence_summary['proof_posture'].value}.",
    ]
    if evidence_backed:
        summary_lines.append(
            "User or evidence-backed parameters: " + ", ".join(sorted(evidence_backed)) + "."
        )
    
    summary_lines.extend(_scientific_unsuitability_lines(result.run_summary.escalation_concerns))

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
        escalation_concerns=result.run_summary.escalation_concerns,
        entries=entries,
        default_evidence_status=default_evidence_summary["status"],
        default_proof_posture=default_evidence_summary["proof_posture"],
        default_evidence_lines=default_evidence_summary["lines"],
        proof_posture_lines=default_evidence_summary["proof_lines"],
        scientific_change_lines=default_evidence_summary["scientific_change_lines"],
        default_sensitivity_lines=default_evidence_summary["default_sensitivity_lines"],
        rebaselined_default_parameters=default_evidence_summary["rebaselined_default_parameters"],
        governed_override_parameters=default_evidence_summary["governed_override_parameters"],
        material_default_sensitivity=default_evidence_summary["material_default_sensitivity"],
        core_default_assumption_count=default_evidence_summary["core_default_assumption_count"],
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
    all_driver_types = sorted({driver.driver_type for driver in drivers})
    summary_lines = [
        (
            f"{len(drivers)} deterministic uncertainty drivers were ranked for "
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
        driver_count=len(drivers),
        all_driver_types=all_driver_types,
        summary_lines=summary_lines,
        limitations=limitations,
        provenance=provenance_builder.bundle(_collect_source_references(scenario, result)),
    )
