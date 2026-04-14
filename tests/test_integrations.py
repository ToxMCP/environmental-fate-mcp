from pathlib import Path

import pytest

from fate_mcp.errors import FateValidationError
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
    build_run_parameter_manifest,
    build_scientific_methods_dossier,
    build_scientific_methods_dossier_brief,
    build_scientific_review_brief,
    build_scientific_review_packet,
    build_run_uncertainty_summary,
    build_regulatory_handoff_review_brief,
    build_regulatory_handoff_review_packet,
    build_concentration_surface_bundle,
    compare_fate_scenarios,
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
    BuildScientificMethodsDossierBriefRequest,
    BuildScientificMethodsDossierRequest,
    BuildScientificReviewBriefRequest,
    BuildScientificReviewPacketRequest,
    BuildRegulatoryHandoffReviewBriefRequest,
    BuildRegulatoryHandoffReviewPacketRequest,
    BuildEnvironmentalReleaseScenarioRequest,
    CompareFateScenariosRequest,
    ExportRegulatoryHandoffPackageRequest,
    FateModelRunOptions,
    FateParameterRecord,
    Media,
    ModelFamily,
    ModelFamilySelectionStatus,
    PhyschemEvidenceRecord,
    PreviewModelFamilyComparisonReviewRequest,
    PreviewModelFamilyChallengeReviewRequest,
    PreviewModelFamilySelectionReviewRequest,
    PreviewScientificReviewOutcomeRequest,
    PreviewRegulatoryHandoffResolutionRequest,
    RecommendModelFamilySelectionRequest,
    RegulatoryHandoffProfile,
    RecommendRegulatoryHandoffProfileRequest,
    ReleaseFraction,
    SourceClassification,
    SourceReference,
    SummarizeRegulatoryHandoffPackageRequest,
    TreatmentAssumption,
    TreatmentExecutionMode,
)
from fate_mcp.runtime import FateRuntime


def test_compare_fate_scenarios_exposes_delta() -> None:
    runtime = FateRuntime(Path(__file__).resolve().parents[1])
    base = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={"preferredName": "Example"},
            total_release_mass_kg=5.0,
            release_fractions=[ReleaseFraction(medium=Media.WATER, fraction=1.0)],
            duration_days=10.0,
        )
    )
    candidate = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={"preferredName": "Example"},
            total_release_mass_kg=10.0,
            release_fractions=[ReleaseFraction(medium=Media.WATER, fraction=1.0)],
            duration_days=10.0,
        )
    )
    run_options = FateModelRunOptions(region_profile_id=base.geographic_scope.region_id)
    base_result = runtime.estimate(base, run_options)
    candidate_result = runtime.estimate(candidate, run_options)
    comparison = compare_fate_scenarios(
        CompareFateScenariosRequest(base_result=base_result, candidate_result=candidate_result),
        runtime.provenance,
    )
    assert comparison.surface_deltas
    bundle = build_concentration_surface_bundle(base_result)
    assert bundle.dependencies


def test_apply_physchem_evidence_updates_parameter_records_and_changes_runtime() -> None:
    runtime = FateRuntime(Path(__file__).resolve().parents[1])
    scenario = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={"preferredName": "Example"},
            total_release_mass_kg=5.0,
            release_fractions=[ReleaseFraction(medium=Media.WATER, fraction=1.0)],
            duration_days=10.0,
        )
    )
    baseline = runtime.estimate(
        scenario,
        FateModelRunOptions(region_profile_id=scenario.geographic_scope.region_id),
    )

    evidence = [
        PhyschemEvidenceRecord(
            parameter="water_half_life_days",
            value=5.0,
            unit="day",
            source_reference=SourceReference(source_id="study-1", title="Measured study"),
            evidence_quality="reference",
        )
    ]
    applied = apply_physchem_evidence(scenario, evidence, runtime.provenance)
    updated = runtime.estimate(
        applied.scenario,
        FateModelRunOptions(region_profile_id=scenario.geographic_scope.region_id),
    )

    assert any(record.parameter == "water_half_life_days" for record in applied.scenario.parameter_records)
    assert updated.surfaces[0].concentration_value != baseline.surfaces[0].concentration_value


def test_apply_physchem_evidence_rejects_invalid_unit_for_supported_parameter() -> None:
    runtime = FateRuntime(Path(__file__).resolve().parents[1])
    scenario = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={"preferredName": "Example"},
            total_release_mass_kg=5.0,
            release_fractions=[ReleaseFraction(medium=Media.WATER, fraction=1.0)],
            duration_days=10.0,
        )
    )
    evidence = [
        PhyschemEvidenceRecord(
            parameter="water_half_life_days",
            value=5.0,
            unit="hour",
            source_reference=SourceReference(source_id="study-1", title="Measured study"),
        )
    ]

    with pytest.raises(FateValidationError):
        apply_physchem_evidence(scenario, evidence, runtime.provenance)


def test_apply_physchem_evidence_weights_higher_quality_inputs_more_heavily() -> None:
    runtime = FateRuntime(Path(__file__).resolve().parents[1])
    scenario = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={"preferredName": "Example"},
            total_release_mass_kg=5.0,
            release_fractions=[ReleaseFraction(medium=Media.WATER, fraction=1.0)],
            duration_days=10.0,
        )
    )
    evidence = [
        PhyschemEvidenceRecord(
            parameter="water_half_life_days",
            value=5.0,
            unit="day",
            source_reference=SourceReference(source_id="measured-study", title="Measured study"),
            evidence_quality="measured",
        ),
        PhyschemEvidenceRecord(
            parameter="water_half_life_days",
            value=25.0,
            unit="day",
            source_reference=SourceReference(source_id="heuristic-study", title="Heuristic study"),
            evidence_quality="heuristic",
        ),
    ]

    applied = apply_physchem_evidence(scenario, evidence, runtime.provenance)

    record = next(record for record in applied.scenario.parameter_records if record.parameter == "water_half_life_days")
    assert record.value == pytest.approx(5.76923076923077)
    assert applied.reconciled_parameters[0].weighting_strategy == "evidence_quality_weighted_mean"
    assert applied.reconciled_parameters[0].reconciliation_domain == "inverse_rate"
    assert applied.unresolved_conflict_count == 1
    assert any(flag.code == "heuristic_physchem_evidence" for flag in applied.quality_flags)


def test_apply_physchem_evidence_uses_policy_for_unsupported_parameter() -> None:
    runtime = FateRuntime(Path(__file__).resolve().parents[1])
    scenario = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={"preferredName": "Example"},
            total_release_mass_kg=5.0,
            release_fractions=[ReleaseFraction(medium=Media.WATER, fraction=1.0)],
            duration_days=10.0,
        )
    )
    evidence = [
        PhyschemEvidenceRecord(
            parameter="log_kow",
            value=4.5,
            unit="log10",
            source_reference=SourceReference(source_id="study-a", title="Study A"),
            evidence_quality="reference",
        ),
        PhyschemEvidenceRecord(
            parameter="log_kow",
            value=6.0,
            unit="log10",
            source_reference=SourceReference(source_id="study-b", title="Study B"),
            evidence_quality="reference",
        ),
    ]

    applied = apply_physchem_evidence(scenario, evidence, runtime.provenance)

    assert applied.reconciled_parameters[0].parameter == "log_kow"
    assert applied.reconciled_parameters[0].conflict_metric == "absolute_log_spread"
    assert applied.unresolved_conflict_count == 1
    assert any(flag.code == "unsupported_runtime_parameter" for flag in applied.quality_flags)


def test_apply_physchem_evidence_blocks_regulatory_empirical_blending_when_policy_forbids_it() -> None:
    runtime = FateRuntime(Path(__file__).resolve().parents[1])
    scenario = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={"preferredName": "Example"},
            total_release_mass_kg=5.0,
            release_fractions=[ReleaseFraction(medium=Media.WATER, fraction=1.0)],
            duration_days=10.0,
        )
    )
    evidence = [
        PhyschemEvidenceRecord(
            parameter="water_half_life_days",
            value=12.0,
            unit="day",
            source_reference=SourceReference(source_id="reg-default", title="Regulatory default"),
            evidence_quality="regulatory",
        ),
        PhyschemEvidenceRecord(
            parameter="water_half_life_days",
            value=4.0,
            unit="day",
            source_reference=SourceReference(source_id="measured-study", title="Measured study"),
            evidence_quality="measured",
        ),
    ]

    applied = apply_physchem_evidence(scenario, evidence, runtime.provenance)

    record = next(record for record in applied.scenario.parameter_records if record.parameter == "water_half_life_days")
    assert record.value == pytest.approx(12.0)
    assert applied.unresolved_conflict_count == 1
    assert any(flag.code == "physchem_evidence_lane_conflict" for flag in applied.quality_flags)


def test_assess_release_scenario_fit_includes_applicability_context() -> None:
    runtime = FateRuntime(Path(__file__).resolve().parents[1])
    scenario = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={"preferredName": "Applicability example"},
            total_release_mass_kg=5.0,
            release_fractions=[ReleaseFraction(medium=Media.WATER, fraction=1.0)],
            duration_days=10.0,
        )
    )
    run_options = FateModelRunOptions(region_profile_id=scenario.geographic_scope.region_id)
    assessment = assess_release_scenario_fit(scenario, run_options, runtime.provenance)
    assert assessment.model_family.value == "reference_mass_balance"
    assert assessment.fit_for_purpose.value == "screening"
    assert assessment.applicability_profile.model_family.value == "reference_mass_balance"
    assert assessment.applicability_profile.required_inputs
    assert assessment.applicability_lines


def test_assess_release_scenario_fit_supports_advective_family_context() -> None:
    runtime = FateRuntime(Path(__file__).resolve().parents[1])
    scenario = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={"preferredName": "Advective applicability example"},
            total_release_mass_kg=5.0,
            release_fractions=[ReleaseFraction(medium=Media.WATER, fraction=1.0)],
            duration_days=10.0,
        )
    )
    run_options = FateModelRunOptions(
        region_profile_id=scenario.geographic_scope.region_id,
        model_family=ModelFamily.ADVECTIVE_SCREENING_MASS_BALANCE,
    )
    assessment = assess_release_scenario_fit(scenario, run_options, runtime.provenance)
    assert assessment.model_family == ModelFamily.ADVECTIVE_SCREENING_MASS_BALANCE
    assert assessment.applicability_profile.model_family == ModelFamily.ADVECTIVE_SCREENING_MASS_BALANCE
    assert any("residence-time" in line.lower() for line in assessment.applicability_lines)


def test_build_run_parameter_manifest_distinguishes_runtime_consumed_from_preserved_only() -> None:
    runtime = FateRuntime(Path(__file__).resolve().parents[1])
    scenario = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={"preferredName": "Manifest example"},
            total_release_mass_kg=5.0,
            release_fractions=[ReleaseFraction(medium=Media.WATER, fraction=1.0)],
            duration_days=10.0,
            parameter_records=[
                FateParameterRecord(
                    parameter="water_half_life_days",
                    value=8.0,
                    unit="day",
                    source_classification=SourceClassification.USER_INPUT,
                    rationale="Consumed parameter override.",
                    evidence_quality="reference",
                ),
                FateParameterRecord(
                    parameter="log_kow",
                    value=4.8,
                    unit="log10",
                    source_classification=SourceClassification.HEURISTIC,
                    rationale="Preserved-only descriptor.",
                    evidence_quality="heuristic",
                ),
            ],
        )
    )
    result = runtime.estimate(
        scenario,
        FateModelRunOptions(region_profile_id=scenario.geographic_scope.region_id),
    )
    manifest = build_run_parameter_manifest(scenario, result, runtime.provenance)

    entries = {entry.parameter: entry for entry in manifest.entries}
    assert entries["water_half_life_days"].runtime_consumed is True
    assert entries["water_half_life_days"].source_classification.value == "user_input"
    assert entries["log_kow"].runtime_consumed is False
    assert entries["log_kow"].source_classification.value == "heuristic"
    assert manifest.summary_lines
    assert any(note.code == "preserved_only_parameters" for note in manifest.limitations)


def test_build_run_uncertainty_summary_reports_deterministic_review_drivers() -> None:
    runtime = FateRuntime(Path(__file__).resolve().parents[1])
    scenario = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={"preferredName": "Uncertainty example"},
            total_release_mass_kg=5.0,
            release_fractions=[
                ReleaseFraction(medium=Media.WATER, fraction=0.6),
                ReleaseFraction(medium=Media.SOIL, fraction=0.4),
            ],
            duration_days=10.0,
            parameter_records=[
                FateParameterRecord(
                    parameter="log_kow",
                    value=4.2,
                    unit="log10",
                    source_classification=SourceClassification.HEURISTIC,
                    rationale="Preserved-only heuristic descriptor.",
                    evidence_quality="heuristic",
                ),
            ],
        )
    )
    result = runtime.estimate(
        scenario,
        FateModelRunOptions(region_profile_id=scenario.geographic_scope.region_id),
    )
    summary = build_run_uncertainty_summary(scenario, result, runtime.provenance)
    driver_types = {driver.driver_type for driver in summary.top_drivers}
    assert "unsupported_runtime_parameter" in driver_types
    assert "multi_medium_simplification_burden" in driver_types
    assert summary.summary_lines


def test_build_run_uncertainty_summary_reports_unexecuted_treatment_assumptions() -> None:
    runtime = FateRuntime(Path(__file__).resolve().parents[1])
    scenario = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={"preferredName": "Treatment uncertainty example"},
            total_release_mass_kg=5.0,
            release_fractions=[ReleaseFraction(medium=Media.WATER, fraction=1.0)],
            duration_days=10.0,
            treatment_assumptions=[
                TreatmentAssumption(
                    description="Recorded but unexecuted treatment",
                    removal_fraction=0.5,
                    execution_mode=TreatmentExecutionMode.PROVENANCE_ONLY,
                )
            ],
        )
    )
    result = runtime.estimate(
        scenario,
        FateModelRunOptions(region_profile_id=scenario.geographic_scope.region_id),
    )
    summary = build_run_uncertainty_summary(scenario, result, runtime.provenance)
    driver_types = {driver.driver_type for driver in summary.top_drivers}
    assert "unexecuted_treatment_assumption" in driver_types


def test_build_model_family_comparison_packet_and_brief_compare_reference_and_advective() -> None:
    runtime = FateRuntime(Path(__file__).resolve().parents[1])
    scenario = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={"preferredName": "Model family comparison example"},
            total_release_mass_kg=5.0,
            release_fractions=[ReleaseFraction(medium=Media.WATER, fraction=1.0)],
            duration_days=10.0,
        )
    )
    packet = build_model_family_comparison_packet(
        BuildModelFamilyComparisonPacketRequest(
            scenario=scenario,
            comparison_profile_id="reference_vs_advective_screening_v1",
            candidate_model_family=ModelFamily.ADVECTIVE_SCREENING_MASS_BALANCE,
        ),
        runtime,
        runtime.provenance,
    )
    brief = build_model_family_comparison_brief(
        BuildModelFamilyComparisonBriefRequest(comparison_packet=packet)
    )

    assert packet.scenario_id == scenario.scenario_id
    assert packet.comparison_profile_id == "reference_vs_advective_screening_v1"
    assert packet.base_model_family == ModelFamily.REFERENCE_MASS_BALANCE
    assert packet.candidate_model_family == ModelFamily.ADVECTIVE_SCREENING_MASS_BALANCE
    assert packet.base_fit_assessment.model_family == ModelFamily.REFERENCE_MASS_BALANCE
    assert packet.candidate_fit_assessment.model_family == ModelFamily.ADVECTIVE_SCREENING_MASS_BALANCE
    assert packet.comparison.base_scenario_id == scenario.scenario_id
    assert packet.comparison.candidate_scenario_id == scenario.scenario_id
    assert packet.comparison.surface_deltas
    assert packet.base_surface_samples
    assert packet.candidate_surface_samples
    assert packet.dominant_delta_lines
    assert packet.outcome_lines
    assert packet.base_equation_lines
    assert packet.candidate_equation_lines
    assert packet.packet_template_used is not None
    assert packet.brief_template_used is not None
    assert any(note.code == "experimental_candidate_model_family" for note in packet.limitations)
    assert any("experimental" in action.lower() for action in packet.recommended_actions)
    assert brief.comparison_packet_id == packet.comparison_packet_id
    assert brief.comparison_profile_id == packet.comparison_profile_id
    assert brief.comparison_outcome == packet.comparison_outcome
    assert brief.dominant_delta_lines == packet.dominant_delta_lines
    assert brief.outcome_lines == packet.outcome_lines
    assert brief.base_equation_lines == packet.base_equation_lines
    assert brief.candidate_equation_lines == packet.candidate_equation_lines
    assert brief.brief_template_used == packet.brief_template_used
    assert brief.recommended_actions == packet.recommended_actions


def test_recommend_model_family_selection_prefers_baseline_plus_challenge_when_duration_triggers() -> None:
    runtime = FateRuntime(Path(__file__).resolve().parents[1])
    scenario = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={"preferredName": "Selection recommendation example"},
            total_release_mass_kg=5.0,
            release_fractions=[ReleaseFraction(medium=Media.WATER, fraction=1.0)],
            duration_days=30.0,
        )
    )
    recommendation = recommend_model_family_selection(
        RecommendModelFamilySelectionRequest(
            scenario=scenario,
            selection_profile_id="reference_baseline_advective_challenge_v1",
        ),
        runtime.provenance,
    )

    assert recommendation.selection_profile_id == "reference_baseline_advective_challenge_v1"
    assert recommendation.recommendation_status == ModelFamilySelectionStatus.DEFAULT_WITH_EXPERIMENTAL_CHALLENGE
    assert recommendation.primary_model_family == ModelFamily.REFERENCE_MASS_BALANCE
    assert recommendation.challenge_model_family == ModelFamily.ADVECTIVE_SCREENING_MASS_BALANCE
    assert recommendation.comparison_profile_id == "reference_vs_advective_screening_v1"
    assert recommendation.primary_fit_assessment.model_family == ModelFamily.REFERENCE_MASS_BALANCE
    assert recommendation.challenge_fit_assessment is not None
    assert recommendation.challenge_fit_assessment.model_family == ModelFamily.ADVECTIVE_SCREENING_MASS_BALANCE
    assert recommendation.triggered_signal_lines
    assert recommendation.summary_lines
    assert recommendation.recommended_actions


def test_recommend_model_family_selection_keeps_baseline_only_without_trigger() -> None:
    runtime = FateRuntime(Path(__file__).resolve().parents[1])
    scenario = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={"preferredName": "Selection baseline only example"},
            total_release_mass_kg=5.0,
            release_fractions=[ReleaseFraction(medium=Media.WATER, fraction=1.0)],
            duration_days=5.0,
        )
    )
    recommendation = recommend_model_family_selection(
        RecommendModelFamilySelectionRequest(
            scenario=scenario,
            selection_profile_id="reference_baseline_advective_challenge_v1",
        ),
        runtime.provenance,
    )

    assert recommendation.recommendation_status == ModelFamilySelectionStatus.DEFAULT_BASELINE_ONLY
    assert recommendation.primary_model_family == ModelFamily.REFERENCE_MASS_BALANCE
    assert recommendation.challenge_model_family is None
    assert recommendation.comparison_profile_id is None


def test_build_model_family_selection_review_packet_and_brief_are_governed() -> None:
    runtime = FateRuntime(Path(__file__).resolve().parents[1])
    scenario = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={"preferredName": "Selection review example"},
            total_release_mass_kg=5.0,
            release_fractions=[ReleaseFraction(medium=Media.WATER, fraction=1.0)],
            duration_days=30.0,
        )
    )
    recommendation = recommend_model_family_selection(
        RecommendModelFamilySelectionRequest(
            scenario=scenario,
            selection_profile_id="reference_baseline_advective_challenge_v1",
        ),
        runtime.provenance,
    )
    review_preview = preview_model_family_selection_review(
        PreviewModelFamilySelectionReviewRequest(
            selection_recommendation=recommendation,
        ),
        runtime.provenance,
    )
    review_packet = build_model_family_selection_review_packet(
        BuildModelFamilySelectionReviewPacketRequest(
            selection_recommendation=recommendation,
        ),
        runtime.provenance,
    )
    review_brief = build_model_family_selection_review_brief(
        BuildModelFamilySelectionReviewBriefRequest(review_packet=review_packet),
        runtime.provenance,
    )

    assert review_preview.scenario_id == recommendation.scenario_id
    assert review_preview.selection_profile_id == recommendation.selection_profile_id
    assert review_preview.review_status == "model_family_selection_review_attention_needed"
    assert review_preview.triggered_signal_lines == recommendation.triggered_signal_lines
    assert review_preview.status_rule_lines
    assert review_preview.governing_rule_lines
    assert review_packet.scenario_id == recommendation.scenario_id
    assert review_packet.review_status == review_preview.review_status
    assert review_packet.review_preview.review_status == review_preview.review_status
    assert review_packet.checks
    assert review_packet.review_checklist
    assert review_packet.primary_applicability_lines
    assert review_packet.challenge_applicability_lines
    assert review_packet.comparison_guidance_lines
    assert review_packet.review_template_used is not None
    assert any(
        note.code == "experimental_challenge_model_family"
        for note in review_packet.limitations
    )
    assert review_brief.review_packet_id == review_packet.review_packet_id
    assert review_brief.scenario_id == review_packet.scenario_id
    assert review_brief.review_status == review_packet.review_status
    assert review_brief.checklist_items == review_packet.review_checklist
    assert review_brief.primary_applicability_lines == review_packet.primary_applicability_lines
    assert review_brief.challenge_applicability_lines == review_packet.challenge_applicability_lines
    assert review_brief.comparison_guidance_lines == review_packet.comparison_guidance_lines
    assert review_brief.review_template_used is not None


def test_build_model_family_comparison_review_packet_and_brief_are_governed() -> None:
    runtime = FateRuntime(Path(__file__).resolve().parents[1])
    scenario = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={"preferredName": "Comparison review example"},
            total_release_mass_kg=5.0,
            release_fractions=[ReleaseFraction(medium=Media.WATER, fraction=1.0)],
            duration_days=10.0,
        )
    )
    comparison_packet = build_model_family_comparison_packet(
        BuildModelFamilyComparisonPacketRequest(
            scenario=scenario,
            comparison_profile_id="reference_vs_advective_screening_v1",
            candidate_model_family=ModelFamily.ADVECTIVE_SCREENING_MASS_BALANCE,
        ),
        runtime,
        runtime.provenance,
    )
    review_preview = preview_model_family_comparison_review(
        PreviewModelFamilyComparisonReviewRequest(comparison_packet=comparison_packet),
        runtime.provenance,
    )
    review_packet = build_model_family_comparison_review_packet(
        BuildModelFamilyComparisonReviewPacketRequest(comparison_packet=comparison_packet),
        runtime.provenance,
    )
    review_brief = build_model_family_comparison_review_brief(
        BuildModelFamilyComparisonReviewBriefRequest(review_packet=review_packet),
        runtime.provenance,
    )

    assert review_preview.comparison_packet_id == comparison_packet.comparison_packet_id
    assert review_preview.comparison_profile_id == comparison_packet.comparison_profile_id
    assert review_preview.review_status == "model_family_comparison_review_attention_needed"
    assert review_preview.outcome_lines == comparison_packet.outcome_lines
    assert review_preview.status_rule_lines
    assert review_preview.governing_rule_lines
    assert review_packet.comparison_packet_id == comparison_packet.comparison_packet_id
    assert review_packet.review_status == review_preview.review_status
    assert review_packet.review_preview.review_status == review_preview.review_status
    assert review_packet.checks
    assert review_packet.review_checklist
    assert review_packet.base_applicability_lines
    assert review_packet.candidate_applicability_lines
    assert review_packet.base_equation_lines == comparison_packet.base_equation_lines
    assert review_packet.candidate_equation_lines == comparison_packet.candidate_equation_lines
    assert review_packet.review_template_used is not None
    assert review_brief.review_packet_id == review_packet.review_packet_id
    assert review_brief.comparison_packet_id == review_packet.comparison_packet_id
    assert review_brief.review_status == review_packet.review_status
    assert review_brief.checklist_items == review_packet.review_checklist
    assert review_brief.base_applicability_lines == review_packet.base_applicability_lines
    assert review_brief.candidate_applicability_lines == review_packet.candidate_applicability_lines
    assert review_brief.base_equation_lines == review_packet.base_equation_lines
    assert review_brief.candidate_equation_lines == review_packet.candidate_equation_lines
    assert review_brief.review_template_used is not None


def test_build_model_family_challenge_review_packet_and_brief_compose_selection_and_comparison() -> None:
    runtime = FateRuntime(Path(__file__).resolve().parents[1])
    scenario = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={"preferredName": "Challenge review example"},
            total_release_mass_kg=5.0,
            release_fractions=[ReleaseFraction(medium=Media.WATER, fraction=1.0)],
            duration_days=30.0,
        )
    )
    review_preview = preview_model_family_challenge_review(
        PreviewModelFamilyChallengeReviewRequest(
            scenario=scenario,
            selection_profile_id="reference_baseline_advective_challenge_v1",
        ),
        runtime,
        runtime.provenance,
    )
    review_packet = build_model_family_challenge_review_packet(
        BuildModelFamilyChallengeReviewPacketRequest(
            scenario=scenario,
            selection_profile_id="reference_baseline_advective_challenge_v1",
        ),
        runtime,
        runtime.provenance,
    )
    review_brief = build_model_family_challenge_review_brief(
        BuildModelFamilyChallengeReviewBriefRequest(review_packet=review_packet),
        runtime.provenance,
    )

    assert review_preview.scenario_id == scenario.scenario_id
    assert review_preview.selection_profile_id == "reference_baseline_advective_challenge_v1"
    assert review_preview.challenge_review_profile_id == "reference_baseline_advective_challenge_review_v1"
    assert review_preview.review_status == "model_family_challenge_review_attention_needed"
    assert review_preview.selection_review_status == "model_family_selection_review_attention_needed"
    assert review_preview.comparison_review_status == "model_family_comparison_review_attention_needed"
    assert review_preview.triggered_check_codes
    assert review_preview.status_rule_lines
    assert review_preview.governing_rule_lines
    assert review_packet.scenario_id == scenario.scenario_id
    assert review_packet.selection_profile_id == "reference_baseline_advective_challenge_v1"
    assert review_packet.challenge_review_profile_id == review_preview.challenge_review_profile_id
    assert review_packet.review_status == review_preview.review_status
    assert review_packet.selection_recommendation_status == ModelFamilySelectionStatus.DEFAULT_WITH_EXPERIMENTAL_CHALLENGE
    assert review_packet.selection_review_status == review_preview.selection_review_status
    assert review_packet.review_preview.review_status == review_preview.review_status
    assert review_packet.review_preview.challenge_review_profile_id == review_preview.challenge_review_profile_id
    assert review_packet.selection_review_packet.scenario_id == scenario.scenario_id
    assert review_packet.comparison_profile_id == "reference_vs_advective_screening_v1"
    assert review_packet.comparison_packet is not None
    assert review_packet.comparison_review_packet is not None
    assert review_packet.comparison_outcome == review_packet.comparison_review_packet.comparison_outcome
    assert review_packet.comparison_review_status == review_packet.comparison_review_packet.review_status
    assert review_packet.checks
    assert review_packet.review_checklist
    assert review_packet.summary_lines
    assert review_packet.governing_rule_lines
    assert review_packet.triggered_signal_lines
    assert review_packet.primary_applicability_lines
    assert review_packet.challenge_applicability_lines
    assert review_packet.comparison_guidance_lines
    assert review_packet.dominant_delta_lines
    assert (
        review_packet.review_template_used
        == "Build a governed assessor-facing composed challenge review packet that bundles the selection review path and, when triggered, the reference-versus-advective comparison review path without losing baseline-versus-experimental framing."
    )
    assert review_brief.review_packet_id == review_packet.review_packet_id
    assert review_brief.challenge_review_profile_id == review_packet.challenge_review_profile_id
    assert review_brief.review_status == review_packet.review_status
    assert review_brief.selection_recommendation_status == review_packet.selection_recommendation_status
    assert review_brief.selection_review_status == review_packet.selection_review_status
    assert review_brief.comparison_profile_id == review_packet.comparison_profile_id
    assert review_brief.comparison_outcome == review_packet.comparison_outcome
    assert review_brief.comparison_review_status == review_packet.comparison_review_status
    assert review_brief.passed_check_count <= review_brief.total_check_count
    assert review_brief.checklist_items == review_packet.review_checklist
    assert review_brief.dominant_delta_lines == review_packet.dominant_delta_lines
    assert review_brief.comparison_guidance_lines == review_packet.comparison_guidance_lines
    assert (
        review_brief.review_template_used
        == "Summarize whether the governed model-family challenge review is ready for assessor-facing reuse, preserving selection status, comparison status, dominant deltas, and applicability context."
    )
    assert review_brief.brief_lines


def test_build_model_family_challenge_scientific_dossier_and_brief_compose_review_and_science() -> None:
    runtime = FateRuntime(Path(__file__).resolve().parents[1])
    scenario = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={"preferredName": "Challenge dossier example"},
            total_release_mass_kg=5.0,
            release_fractions=[ReleaseFraction(medium=Media.WATER, fraction=1.0)],
            duration_days=30.0,
        )
    )
    dossier = build_model_family_challenge_scientific_dossier(
        BuildModelFamilyChallengeScientificDossierRequest(
            scenario=scenario,
            selection_profile_id="reference_baseline_advective_challenge_v1",
        ),
        runtime,
        runtime.provenance,
    )
    brief = build_model_family_challenge_scientific_dossier_brief(
        BuildModelFamilyChallengeScientificDossierBriefRequest(dossier=dossier),
        runtime.provenance,
    )

    assert dossier.scenario_id == scenario.scenario_id
    assert dossier.selection_profile_id == "reference_baseline_advective_challenge_v1"
    assert dossier.challenge_review_profile_id == "reference_baseline_advective_challenge_review_v1"
    assert dossier.primary_model_family == ModelFamily.REFERENCE_MASS_BALANCE
    assert dossier.challenge_model_family == ModelFamily.ADVECTIVE_SCREENING_MASS_BALANCE
    assert dossier.challenge_review_brief.scenario_id == scenario.scenario_id
    assert dossier.primary_scientific_review_brief.scenario_id == scenario.scenario_id
    assert dossier.primary_scientific_review_brief.model_family == dossier.primary_model_family
    assert dossier.challenge_scientific_review_brief is not None
    assert dossier.challenge_scientific_review_brief.model_family == dossier.challenge_model_family
    assert dossier.challenge_review_status == dossier.challenge_review_brief.review_status
    assert dossier.selection_recommendation_status == dossier.challenge_review_brief.selection_recommendation_status
    assert dossier.primary_equation_lines == dossier.primary_scientific_review_brief.equation_lines
    assert dossier.challenge_equation_lines == dossier.challenge_scientific_review_brief.equation_lines
    assert dossier.primary_benchmark_reference_lines == dossier.primary_scientific_review_brief.benchmark_reference_lines
    assert dossier.challenge_benchmark_reference_lines == dossier.challenge_scientific_review_brief.benchmark_reference_lines
    assert dossier.summary_lines
    assert dossier.recommended_actions

    assert brief.dossier_id == dossier.dossier_id
    assert brief.scenario_id == dossier.scenario_id
    assert brief.selection_profile_id == dossier.selection_profile_id
    assert brief.challenge_review_profile_id == dossier.challenge_review_profile_id
    assert brief.primary_model_family == dossier.primary_model_family
    assert brief.challenge_model_family == dossier.challenge_model_family
    assert brief.challenge_review_status == dossier.challenge_review_status
    assert brief.selection_recommendation_status == dossier.selection_recommendation_status
    assert brief.comparison_profile_id == dossier.comparison_profile_id
    assert brief.comparison_outcome == dossier.comparison_outcome
    assert brief.primary_review_outcome == dossier.primary_scientific_review_brief.review_outcome
    assert brief.challenge_review_outcome == dossier.challenge_scientific_review_brief.review_outcome
    assert brief.primary_passed_check_count <= brief.primary_total_check_count
    assert brief.challenge_passed_check_count is not None
    assert brief.challenge_total_check_count is not None
    assert brief.challenge_passed_check_count <= brief.challenge_total_check_count
    assert brief.primary_equation_lines == dossier.primary_equation_lines
    assert brief.challenge_equation_lines == dossier.challenge_equation_lines
    assert brief.primary_benchmark_reference_lines == dossier.primary_benchmark_reference_lines
    assert brief.challenge_benchmark_reference_lines == dossier.challenge_benchmark_reference_lines
    assert brief.summary_lines


def test_build_scientific_review_packet_bundles_fit_manifest_and_uncertainty() -> None:
    runtime = FateRuntime(Path(__file__).resolve().parents[1])
    scenario = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={"preferredName": "Scientific packet example"},
            total_release_mass_kg=5.0,
            release_fractions=[ReleaseFraction(medium=Media.WATER, fraction=1.0)],
            duration_days=10.0,
            parameter_records=[
                FateParameterRecord(
                    parameter="log_kow",
                    value=4.0,
                    unit="log10",
                    source_classification=SourceClassification.HEURISTIC,
                    rationale="Preserved descriptor for review packet.",
                    evidence_quality="heuristic",
                ),
            ],
        )
    )
    result = runtime.estimate(
        scenario,
        FateModelRunOptions(region_profile_id=scenario.geographic_scope.region_id),
    )
    packet = build_scientific_review_packet(
        BuildScientificReviewPacketRequest(scenario=scenario, result=result),
        runtime.provenance,
    )
    preview = preview_scientific_review_outcome(
        PreviewScientificReviewOutcomeRequest(scenario=scenario, result=result),
        runtime.provenance,
    )
    assert packet.fit_assessment.applicability_lines
    assert packet.parameter_manifest.entries
    assert packet.uncertainty_summary.summary_lines
    assert packet.surface_samples
    assert packet.surface_samples[0].equation_id is not None
    assert packet.benchmark_reference_lines
    assert packet.equation_lines
    assert packet.equation_component_lines
    assert packet.mass_balance_component_lines
    assert packet.transport_regime_lines
    assert packet.post_release_recovery_lines
    assert packet.post_release_regime_lines
    assert packet.loss_dominance_lines
    assert packet.loss_transition_lines
    assert any("loss decomposition ->" in line for line in packet.equation_component_lines)
    assert any("closure_error=" in line for line in packet.mass_balance_component_lines)
    assert any("regime" in line for line in packet.transport_regime_lines)
    assert any("post_release" in line or "no_post_release" in line for line in packet.post_release_recovery_lines)
    assert any("post_release" in line or "no_post_release" in line for line in packet.post_release_regime_lines)
    assert any("dominant" in line or "degradation_only_loss" in line for line in packet.loss_dominance_lines)
    assert any("transition" in line or "single_loss_mechanism" in line for line in packet.loss_transition_lines)
    assert packet.review_checklist
    assert packet.review_template_used is not None
    assert packet.outcome_preview.review_outcome == preview.review_outcome
    assert packet.outcome_preview.review_status == preview.review_status
    assert packet.review_status == preview.review_status
    assert packet.outcome_preview.status_rule_lines == preview.status_rule_lines
    assert packet.outcome_preview.governing_rule_lines == preview.governing_rule_lines
    assert packet.review_outcome == packet.outcome_preview.review_outcome
    assert packet.review_outcome.value in {
        "acceptable_screening_use",
        "qualified_screening_use",
        "escalate_model_review",
    }
    assert packet.outcome_lines
    assert packet.recommended_actions
    assert all(check.passed for check in packet.checks)


def test_preview_scientific_review_outcome_returns_governed_resolution_context() -> None:
    runtime = FateRuntime(Path(__file__).resolve().parents[1])
    scenario = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={"preferredName": "Scientific preview example"},
            total_release_mass_kg=5.0,
            release_fractions=[
                ReleaseFraction(medium=Media.WATER, fraction=0.6),
                ReleaseFraction(medium=Media.SOIL, fraction=0.4),
            ],
            duration_days=10.0,
            parameter_records=[
                FateParameterRecord(
                    parameter="log_kow",
                    value=4.1,
                    unit="log10",
                    source_classification=SourceClassification.HEURISTIC,
                    rationale="Preserved-only heuristic descriptor for governed preview.",
                    evidence_quality="heuristic",
                ),
            ],
        )
    )
    result = runtime.estimate(
        scenario,
        FateModelRunOptions(region_profile_id=scenario.geographic_scope.region_id),
    )

    preview = preview_scientific_review_outcome(
        PreviewScientificReviewOutcomeRequest(scenario=scenario, result=result),
        runtime.provenance,
    )

    assert preview.model_family.value == "reference_mass_balance"
    assert preview.review_profile_model_family == result.run_summary.model_family
    assert preview.review_outcome.value == "qualified_screening_use"
    assert preview.review_status == "scientific_review_attention_needed"
    assert "unsupported_runtime_parameter" in preview.triggered_driver_types
    assert not preview.triggered_check_codes
    assert preview.governing_rule_lines
    assert preview.status_rule_lines
    assert preview.outcome_lines
    assert preview.recommended_actions


def test_build_scientific_review_brief_reflects_packet_context() -> None:
    runtime = FateRuntime(Path(__file__).resolve().parents[1])
    scenario = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={"preferredName": "Scientific brief example"},
            total_release_mass_kg=5.0,
            release_fractions=[ReleaseFraction(medium=Media.WATER, fraction=1.0)],
            duration_days=10.0,
        )
    )
    result = runtime.estimate(
        scenario,
        FateModelRunOptions(region_profile_id=scenario.geographic_scope.region_id),
    )
    packet = build_scientific_review_packet(
        BuildScientificReviewPacketRequest(scenario=scenario, result=result),
        runtime.provenance,
    )
    brief = build_scientific_review_brief(
        BuildScientificReviewBriefRequest(review_packet=packet),
        runtime.provenance,
    )
    assert brief.review_packet_id == packet.review_packet_id
    assert brief.run_id == packet.run_id
    assert brief.review_template_used is not None
    assert brief.checklist_items
    assert brief.review_outcome == packet.review_outcome
    assert brief.outcome_lines
    assert brief.recommended_actions
    assert brief.parameter_quality_lines
    assert brief.applicability_lines
    assert brief.uncertainty_lines
    assert brief.benchmark_reference_lines
    assert brief.equation_lines
    assert brief.equation_component_lines == packet.equation_component_lines
    assert brief.mass_balance_component_lines == packet.mass_balance_component_lines
    assert brief.transport_regime_lines == packet.transport_regime_lines
    assert brief.post_release_recovery_lines == packet.post_release_recovery_lines
    assert brief.post_release_regime_lines == packet.post_release_regime_lines
    assert brief.post_release_directionality_lines == packet.post_release_directionality_lines
    assert brief.post_release_pace_lines == packet.post_release_pace_lines
    assert brief.post_release_pace_directionality_lines == packet.post_release_pace_directionality_lines
    assert brief.loss_dominance_lines == packet.loss_dominance_lines
    assert brief.loss_transition_lines == packet.loss_transition_lines
    assert any(line.startswith("Equation components: ") for line in brief.summary_lines)
    assert any(line.startswith("Mass balance: ") for line in brief.summary_lines)
    assert any(line.startswith("Transport regime: ") for line in brief.summary_lines)
    assert any(line.startswith("Post-release recovery: ") for line in brief.summary_lines)
    assert any(line.startswith("Post-release regime: ") for line in brief.summary_lines)
    assert (
        not brief.post_release_directionality_lines
        or any(line.startswith("Post-release directionality: ") for line in brief.summary_lines)
    )
    assert (
        not brief.post_release_pace_lines
        or any(line.startswith("Post-release pace: ") for line in brief.summary_lines)
    )
    assert (
        not brief.post_release_pace_directionality_lines
        or any(
            line.startswith("Post-release pace directionality: ")
            for line in brief.summary_lines
        )
    )
    assert any(line.startswith("Loss dominance: ") for line in brief.summary_lines)
    assert any(line.startswith("Loss transition: ") for line in brief.summary_lines)


def test_build_scientific_methods_dossier_for_advective_family() -> None:
    runtime = FateRuntime(Path(__file__).resolve().parents[1])
    dossier = build_scientific_methods_dossier(
        BuildScientificMethodsDossierRequest(
            model_family=ModelFamily.ADVECTIVE_SCREENING_MASS_BALANCE,
        ),
        runtime.provenance,
    )
    assert dossier.model_family == ModelFamily.ADVECTIVE_SCREENING_MASS_BALANCE
    assert dossier.claim_count >= 7
    assert dossier.covered_mandatory_claim_count == dossier.mandatory_claim_count
    assert dossier.claim_summaries
    assert dossier.highlighted_claim_summaries
    assert dossier.applicability_lines
    assert dossier.source_grounding_lines
    assert dossier.highlighted_claim_grounding_lines
    assert dossier.reference_case_grounding_lines
    assert dossier.reference_case_concept_lines
    assert dossier.benchmark_reference_lines
    assert dossier.support_strength_lines
    assert dossier.edge_condition_lines
    assert not dossier.recommended_actions
    assert dossier.provenance.source_references
    assert any(
        item.claim_id == "advective_short_residence_time_clearance_anchor_v1"
        for item in dossier.claim_summaries
    )
    assert any(
        item.claim_id == "advective_long_duration_combined_loss_plateau_v1"
        for item in dossier.claim_summaries
    )
    assert any(
        item.claim_id == "advective_long_residence_time_accumulation_anchor_v1"
        for item in dossier.claim_summaries
    )
    assert any(
        item.claim_id == "advective_loss_regime_flip_directionality_v1"
        for item in dossier.claim_summaries
    )
    assert any(
        item.support_strength.value in {"multi_anchor_single_tier", "multi_anchor_multi_tier"}
        for item in dossier.claim_summaries
        if item.claim_id == "advective_water_finite_duration_first_order_v1"
    )
    assert all(
        item.support_strength.value in {"multi_anchor_single_tier", "multi_anchor_multi_tier"}
        for item in dossier.claim_summaries
        if item.claim_id in {
            "advective_short_residence_time_clearance_anchor_v1",
            "advective_long_duration_combined_loss_plateau_v1",
            "advective_long_residence_time_accumulation_anchor_v1",
        }
    )
    assert next(
        item.support_strength.value
        for item in dossier.claim_summaries
        if item.claim_id == "advective_long_duration_combined_loss_plateau_v1"
    ) == "multi_anchor_multi_tier"
    assert all(item.source_references for item in dossier.claim_summaries)
    assert all(item.external_corroboration_status.value for item in dossier.claim_summaries)
    assert all(item.external_corroboration_lines for item in dossier.claim_summaries)
    assert all(item.source_grounding_lines for item in dossier.claim_summaries if item.source_references)
    assert all(item.reference_case_ids for item in dossier.claim_summaries)
    assert all(item.reference_case_concept_lines for item in dossier.claim_summaries if item.reference_case_ids)
    assert all(item.source_grounding_lines for item in dossier.highlighted_claim_summaries)
    assert all(item.external_corroboration_status.value for item in dossier.highlighted_claim_summaries)
    assert all(item.external_corroboration_source_count >= 0 for item in dossier.highlighted_claim_summaries)
    assert any(
        item.external_corroboration_status.value == "multi_official_multi_jurisdiction"
        for item in dossier.highlighted_claim_summaries
    )
    assert all(
        item.external_corroboration_status.value == "multi_official_multi_jurisdiction"
        for item in dossier.highlighted_claim_summaries
    )
    assert any(
        "experimental model family" in line
        for item in dossier.highlighted_claim_summaries
        for line in item.challenge_lines
    )
    assert all(item.external_corroboration_lines for item in dossier.highlighted_claim_summaries)
    assert all(item.external_corroboration_actions for item in dossier.highlighted_claim_summaries)
    assert all(item.reference_case_concept_lines for item in dossier.highlighted_claim_summaries)
    assert all(item.benchmark_anchor_lines for item in dossier.highlighted_claim_summaries)
    assert all(item.loss_regime_stability_status for item in dossier.highlighted_claim_summaries)
    assert all(item.loss_regime_stability_lines for item in dossier.highlighted_claim_summaries)
    assert all(item.transport_regime_stability_status for item in dossier.highlighted_claim_summaries)
    assert all(item.transport_regime_stability_lines for item in dossier.highlighted_claim_summaries)
    assert all(item.challenge_status.value for item in dossier.highlighted_claim_summaries)
    assert all(item.challenge_lines for item in dossier.highlighted_claim_summaries)
    assert all(item.review_questions for item in dossier.highlighted_claim_summaries)
    assert any(
        item.loss_regime_stability_status == "near_parity_transition"
        for item in dossier.highlighted_claim_summaries
    )
    assert any(
        item.loss_regime_stability_status == "stable_loss_regime"
        for item in dossier.highlighted_claim_summaries
    )
    assert any(
        item.transport_regime_stability_status == "boundary_sensitive_transport_regime"
        for item in dossier.highlighted_claim_summaries
    )
    assert any(
        item.transport_regime_stability_status == "post_release_flushing_recovery_regime"
        for item in dossier.highlighted_claim_summaries
    )
    assert any(
        item.transport_regime_stability_status == "boundary_sensitive_post_release_recovery_regime"
        for item in dossier.highlighted_claim_summaries
    )
    assert any(
        item.transport_regime_stability_status == "boundary_sensitive_post_release_recovery_pace"
        for item in dossier.highlighted_claim_summaries
    )
    assert any(
        item.claim_id == "advective_residence_time_turnover_regime_v1"
        for item in dossier.highlighted_claim_summaries
    )
    assert any(
        item.claim_id == "advective_post_release_flushing_recovery_v1"
        for item in dossier.highlighted_claim_summaries
    )
    assert any(
        item.claim_id == "advective_post_release_flushing_regime_transition_v1"
        for item in dossier.highlighted_claim_summaries
    )
    assert any(
        item.claim_id == "advective_post_release_half_recovery_pace_v1"
        for item in dossier.highlighted_claim_summaries
    )
    assert any(
        item.claim_id == "advective_post_release_half_recovery_directionality_v1"
        for item in dossier.highlighted_claim_summaries
    )
    turnover_claim = next(
        item for item in dossier.claim_summaries if item.claim_id == "advective_residence_time_turnover_regime_v1"
    )
    assert turnover_claim.support_strength.value == "multi_anchor_multi_tier"
    assert "reference_style" in turnover_claim.supporting_validation_tiers
    assert {
        "hand_worked_advective_bounded_transport_reference_fixture",
        "hand_worked_advective_flow_through_transport_reference_fixture",
        "hand_worked_advective_storage_dominant_transport_reference_fixture",
        "hand_worked_advective_transition_boundary_reference_fixture",
    }.issubset(set(turnover_claim.supporting_reference_types))
    mixed_loss_claim = next(
        item for item in dossier.claim_summaries if item.claim_id == "advective_mixed_loss_transition_margin_v1"
    )
    assert "reference_style" in mixed_loss_claim.supporting_validation_tiers
    assert (
        "hand_worked_advective_transition_boundary_reference_fixture"
        in mixed_loss_claim.supporting_reference_types
    )
    post_release_claim = next(
        item for item in dossier.claim_summaries if item.claim_id == "advective_post_release_flushing_recovery_v1"
    )
    assert post_release_claim.support_strength.value == "multi_anchor_multi_tier"
    assert "reference_style" in post_release_claim.supporting_validation_tiers
    assert {
        "hand_worked_advective_post_release_bucket_anchor",
        "hand_worked_advective_post_release_recovery_reference_fixture",
        "hand_worked_advective_post_release_recovery_sensitivity_fixture",
    }.issubset(set(post_release_claim.supporting_reference_types))
    post_release_regime_claim = next(
        item
        for item in dossier.claim_summaries
        if item.claim_id == "advective_post_release_flushing_regime_transition_v1"
    )
    assert post_release_regime_claim.support_strength.value == "multi_anchor_multi_tier"
    assert "reference_style" in post_release_regime_claim.supporting_validation_tiers
    assert {
        "hand_worked_advective_post_release_bucket_anchor",
        "hand_worked_advective_post_release_boundary_transition_reference_fixture",
        "hand_worked_advective_post_release_recovery_reference_fixture",
        "hand_worked_advective_post_release_recovery_sensitivity_fixture",
        "hand_worked_advective_post_release_extended_flushing_sensitivity_fixture",
    }.issubset(set(post_release_regime_claim.supporting_reference_types))
    post_release_directionality_claim = next(
        item
        for item in dossier.claim_summaries
        if item.claim_id == "advective_post_release_flushing_directionality_v1"
    )
    assert post_release_directionality_claim.support_strength.value == "multi_anchor_multi_tier"
    assert "reference_style" in post_release_directionality_claim.supporting_validation_tiers
    assert {
        "hand_worked_advective_post_release_bucket_anchor",
        "hand_worked_advective_post_release_subboundary_sensitivity_fixture",
        "hand_worked_advective_post_release_boundary_transition_reference_fixture",
        "hand_worked_advective_post_release_recovery_reference_fixture",
        "hand_worked_advective_post_release_extended_flushing_sensitivity_fixture",
    }.issubset(set(post_release_directionality_claim.supporting_reference_types))
    post_release_pace_claim = next(
        item
        for item in dossier.claim_summaries
        if item.claim_id == "advective_post_release_half_recovery_pace_v1"
    )
    assert post_release_pace_claim.support_strength.value == "multi_anchor_multi_tier"
    assert "reference_style" in post_release_pace_claim.supporting_validation_tiers
    assert {
        "hand_worked_advective_post_release_bucket_anchor",
        "hand_worked_advective_post_release_pre_half_recovery_sensitivity_fixture",
        "hand_worked_advective_post_release_half_recovery_reference_fixture",
        "hand_worked_advective_post_release_recovery_reference_fixture",
    }.issubset(set(post_release_pace_claim.supporting_reference_types))
    post_release_pace_directionality_claim = next(
        item
        for item in dossier.claim_summaries
        if item.claim_id == "advective_post_release_half_recovery_directionality_v1"
    )
    assert (
        post_release_pace_directionality_claim.support_strength.value
        == "multi_anchor_multi_tier"
    )
    assert (
        "reference_style"
        in post_release_pace_directionality_claim.supporting_validation_tiers
    )
    assert {
        "hand_worked_advective_post_release_bucket_anchor",
        "hand_worked_advective_post_release_pre_half_recovery_sensitivity_fixture",
        "hand_worked_advective_post_release_half_recovery_reference_fixture",
        "hand_worked_advective_post_release_recovery_reference_fixture",
        "hand_worked_advective_post_release_extended_flushing_sensitivity_fixture",
    }.issubset(set(post_release_pace_directionality_claim.supporting_reference_types))
    assert any(line.startswith("Highlighted regime stability: ") for line in dossier.summary_lines)
    assert any(line.startswith("Highlighted transport stability: ") for line in dossier.summary_lines)
    assert any(line.startswith("Post-release regime stability: ") for line in dossier.summary_lines)
    assert any(line.startswith("External corroboration breadth: ") for line in dossier.summary_lines)
    assert any(line.startswith("Transport authority support: ") for line in dossier.summary_lines)
    assert any(line.startswith("Transport transition support: ") for line in dossier.summary_lines)
    assert any(line.startswith("Post-release recovery support: ") for line in dossier.summary_lines)
    assert any(line.startswith("Post-release regime support: ") for line in dossier.summary_lines)
    assert any(line.startswith("Post-release directionality support: ") for line in dossier.summary_lines)
    assert any(line.startswith("Post-release pace support: ") for line in dossier.summary_lines)
    assert any(line.startswith("Post-release pace directionality support: ") for line in dossier.summary_lines)
    assert any(line.startswith("Late recovery regime support: ") for line in dossier.summary_lines)
    assert any(line.startswith("Transition sensitivity support: ") for line in dossier.summary_lines)
    assert not any(item.action_class == "regime_transition" for item in dossier.recommended_action_summaries)
    assert dossier.promotion_status.value == "ready"


def test_build_scientific_methods_dossier_brief_reflects_dossier() -> None:
    runtime = FateRuntime(Path(__file__).resolve().parents[1])
    dossier = build_scientific_methods_dossier(
        BuildScientificMethodsDossierRequest(
            model_family=ModelFamily.REFERENCE_MASS_BALANCE,
        ),
        runtime.provenance,
    )
    brief = build_scientific_methods_dossier_brief(
        BuildScientificMethodsDossierBriefRequest(dossier=dossier),
    )
    assert brief.dossier_id == dossier.dossier_id
    assert brief.model_family == dossier.model_family
    assert brief.claim_count == dossier.claim_count
    assert brief.promotion_status == dossier.promotion_status
    assert brief.blocking_action_count == dossier.blocking_action_count
    assert brief.strengthening_action_count == dossier.strengthening_action_count
    assert brief.promotion_status.value == "ready"
    assert brief.blocking_action_count == 0
    assert brief.strengthening_action_count == 0
    assert brief.covered_mandatory_claim_count == dossier.covered_mandatory_claim_count
    assert dossier.reference_case_concept_lines
    assert brief.highlighted_claim_ids
    assert brief.highlighted_claim_summaries == dossier.highlighted_claim_summaries
    assert brief.highlighted_claim_ids == [item.claim_id for item in dossier.highlighted_claim_summaries]
    assert brief.promotion_blocker_claim_ids == dossier.promotion_blocker_claim_ids
    assert brief.promotion_blocker_summaries == dossier.promotion_blocker_summaries
    assert brief.summary_lines
    assert any(line.startswith("Promotion status: ") for line in dossier.summary_lines)
    assert any(line.startswith("Promotion status: ") for line in brief.summary_lines)
    assert not dossier.promotion_blocker_summaries
    assert not any(line.startswith("Promotion blocker: ") for line in dossier.summary_lines)
    assert not any(line.startswith("Promotion blocker: ") for line in brief.summary_lines)
    assert any(line.startswith("Highlighted claim [") for line in brief.summary_lines)
    assert any(line.startswith("Highlighted regime stability: ") for line in brief.summary_lines)
    assert any(line.startswith("Highlighted transport stability: ") for line in brief.summary_lines)
    assert any(line.startswith("Claim regime stability: ") for line in brief.summary_lines)
    assert any(line.startswith("Claim regime context: ") for line in brief.summary_lines)
    assert any(line.startswith("Claim transport stability: ") for line in brief.summary_lines)
    assert any(line.startswith("Claim transport context: ") for line in brief.summary_lines)
    assert any(line.startswith("Claim corroboration status: ") for line in brief.summary_lines)
    assert any(line.startswith("Claim corroboration: ") for line in brief.summary_lines)
    assert any(line.startswith("Claim corroboration action: ") for line in brief.summary_lines)
    assert any(line.startswith("Claim challenge: ") for line in brief.summary_lines)
    assert not brief.recommended_actions
    assert not any(line.startswith("Recommended action: ") for line in brief.summary_lines)
    assert brief.source_grounding_lines == dossier.source_grounding_lines
    assert brief.highlighted_claim_grounding_lines == dossier.highlighted_claim_grounding_lines
    assert brief.reference_case_grounding_lines == dossier.reference_case_grounding_lines
    assert brief.reference_case_concept_lines == dossier.reference_case_concept_lines
    assert brief.benchmark_reference_lines == dossier.benchmark_reference_lines
    assert brief.support_strength_lines == dossier.support_strength_lines
    assert brief.recommended_action_summaries == dossier.recommended_action_summaries
    assert brief.recommended_actions == dossier.recommended_actions
    assert all(item.priority.value for item in brief.recommended_action_summaries)
    assert all(item.promotion_impact.value for item in brief.recommended_action_summaries)
    assert all(item.action_class for item in brief.recommended_action_summaries)


def test_build_scientific_methods_dossier_lifts_claim_actions_into_recommended_actions() -> None:
    runtime = FateRuntime(Path(__file__).resolve().parents[1])
    dossier = build_scientific_methods_dossier(
        BuildScientificMethodsDossierRequest(
            model_family=ModelFamily.ADVECTIVE_SCREENING_MASS_BALANCE,
        ),
        runtime.provenance,
    )
    brief = build_scientific_methods_dossier_brief(
        BuildScientificMethodsDossierBriefRequest(dossier=dossier),
    )
    assert dossier.promotion_status.value == "ready"
    assert dossier.blocking_action_count == 0
    assert dossier.strengthening_action_count == 0
    assert not dossier.promotion_blocker_summaries
    assert not dossier.recommended_action_summaries
    assert not any(item.action_class == "regime_transition" for item in dossier.recommended_action_summaries)
    assert not any(line.startswith("Recommended action: ") for line in brief.summary_lines)


def test_export_regulatory_handoff_package_builds_crosswalk_entries() -> None:
    runtime = FateRuntime(Path(__file__).resolve().parents[1])
    scenario = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={"preferredName": "Example"},
            total_release_mass_kg=5.0,
            release_fractions=[ReleaseFraction(medium=Media.WATER, fraction=1.0)],
            duration_days=10.0,
        )
    )
    result = runtime.estimate(
        scenario,
        FateModelRunOptions(region_profile_id=scenario.geographic_scope.region_id),
    )
    handoff = export_regulatory_handoff_package(
        ExportRegulatoryHandoffPackageRequest(result=result),
        runtime.provenance,
    )
    assert handoff.source_module == "fate_mcp"
    assert handoff.handoff_profile_id == "exposure_scenario_mcp_v1"
    assert handoff.profile_resolution_method == "default_profile"
    assert handoff.profile_resolution_confidence == pytest.approx(1.0)
    assert handoff.target_modules == ["Direct-Use Exposure MCP"]
    assert len(handoff.crosswalk_entries) == len(result.surfaces)
    assert handoff.crosswalk_entries[0].route_hint == "water_contact_or_drinking_water_precursor"


def test_summarize_regulatory_handoff_package_builds_default_profile_summary() -> None:
    runtime = FateRuntime(Path(__file__).resolve().parents[1])
    scenario = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={"preferredName": "Example"},
            total_release_mass_kg=5.0,
            release_fractions=[ReleaseFraction(medium=Media.WATER, fraction=1.0)],
            duration_days=10.0,
        )
    )
    result = runtime.estimate(
        scenario,
        FateModelRunOptions(region_profile_id=scenario.geographic_scope.region_id),
    )
    package = export_regulatory_handoff_package(
        ExportRegulatoryHandoffPackageRequest(result=result),
        runtime.provenance,
    )
    summary = summarize_regulatory_handoff_package(
        SummarizeRegulatoryHandoffPackageRequest(package=package),
        runtime.provenance,
    )
    assert summary.handoff_profile_id == "exposure_scenario_mcp_v1"
    assert summary.target_module == "Direct-Use Exposure MCP"
    assert summary.entry_count == len(package.crosswalk_entries)
    assert summary.downstream_field == "environmental_media_concentration"
    assert summary.summary_template_used is not None
    assert any("Route hints present" in line for line in summary.summary_lines)
    assert summary.equation_lines


def test_build_regulatory_handoff_review_packet_builds_default_review_bundle() -> None:
    runtime = FateRuntime(Path(__file__).resolve().parents[1])
    scenario = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={"preferredName": "Example"},
            total_release_mass_kg=5.0,
            release_fractions=[ReleaseFraction(medium=Media.WATER, fraction=1.0)],
            duration_days=10.0,
        )
    )
    result = runtime.estimate(
        scenario,
        FateModelRunOptions(region_profile_id=scenario.geographic_scope.region_id),
    )
    review_packet = build_regulatory_handoff_review_packet(
        BuildRegulatoryHandoffReviewPacketRequest(result=result, scenario=scenario),
        runtime.provenance,
    )
    assert review_packet.review_status == "ready_for_assessor_review"
    assert review_packet.handoff_profile_id == "exposure_scenario_mcp_v1"
    assert review_packet.target_module == "Direct-Use Exposure MCP"
    assert review_packet.resolution_preview.resolution_method == "default_profile"
    assert review_packet.package.package_id == review_packet.summary.package_id
    assert review_packet.review_checklist
    assert review_packet.review_template_used is not None
    assert review_packet.parameter_quality_lines
    assert review_packet.applicability_lines
    assert review_packet.uncertainty_lines
    assert review_packet.equation_lines
    assert all(check.passed for check in review_packet.checks)


def test_export_regulatory_handoff_package_supports_alternate_profile() -> None:
    runtime = FateRuntime(Path(__file__).resolve().parents[1])
    scenario = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={"preferredName": "Example"},
            total_release_mass_kg=5.0,
            release_fractions=[ReleaseFraction(medium=Media.WATER, fraction=1.0)],
            duration_days=10.0,
        )
    )
    result = runtime.estimate(
        scenario,
        FateModelRunOptions(region_profile_id=scenario.geographic_scope.region_id),
    )
    handoff = export_regulatory_handoff_package(
        ExportRegulatoryHandoffPackageRequest(
            result=result,
            handoff_profile_id="toxclaw_orchestration_v1",
        ),
        runtime.provenance,
    )
    assert handoff.handoff_profile_id == "toxclaw_orchestration_v1"
    assert handoff.profile_resolution_method == "explicit_profile_id"
    assert handoff.profile_resolution_basis == "toxclaw_orchestration_v1"
    assert handoff.target_modules == ["ToxClaw"]
    assert handoff.crosswalk_entries[0].downstream_field == "upstream_concentration_surface"


def test_summarize_regulatory_handoff_package_builds_alternate_profile_summary() -> None:
    runtime = FateRuntime(Path(__file__).resolve().parents[1])
    scenario = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={"preferredName": "Example"},
            total_release_mass_kg=5.0,
            release_fractions=[ReleaseFraction(medium=Media.WATER, fraction=1.0)],
            duration_days=10.0,
        )
    )
    result = runtime.estimate(
        scenario,
        FateModelRunOptions(region_profile_id=scenario.geographic_scope.region_id),
    )
    package = export_regulatory_handoff_package(
        ExportRegulatoryHandoffPackageRequest(
            result=result,
            handoff_profile_id="toxclaw_orchestration_v1",
        ),
        runtime.provenance,
    )
    summary = summarize_regulatory_handoff_package(
        SummarizeRegulatoryHandoffPackageRequest(package=package),
        runtime.provenance,
    )
    assert summary.target_module == "ToxClaw"
    assert summary.downstream_field == "upstream_concentration_surface"
    assert summary.entry_samples[0].downstream_field == "upstream_concentration_surface"
    assert any("Target module ToxClaw" in line for line in summary.summary_lines)


def test_build_regulatory_handoff_review_packet_supports_consumer_resolved_profile() -> None:
    runtime = FateRuntime(Path(__file__).resolve().parents[1])
    scenario = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={"preferredName": "Example"},
            total_release_mass_kg=5.0,
            release_fractions=[ReleaseFraction(medium=Media.WATER, fraction=1.0)],
            duration_days=10.0,
        )
    )
    result = runtime.estimate(
        scenario,
        FateModelRunOptions(region_profile_id=scenario.geographic_scope.region_id),
    )
    review_packet = build_regulatory_handoff_review_packet(
        BuildRegulatoryHandoffReviewPacketRequest(
            result=result,
            consumer_name="ToxClaw",
        ),
        runtime.provenance,
    )
    assert review_packet.handoff_profile_id == "toxclaw_orchestration_v1"
    assert review_packet.target_module == "ToxClaw"
    assert review_packet.summary.downstream_field == "upstream_concentration_surface"
    assert review_packet.resolution_preview.resolved_profile_id == "toxclaw_orchestration_v1"
    assert any(item.code == "field_mapping_stable" for item in review_packet.review_checklist)
    assert all(check.passed for check in review_packet.checks)


def test_build_regulatory_handoff_review_brief_builds_default_profile_brief() -> None:
    runtime = FateRuntime(Path(__file__).resolve().parents[1])
    scenario = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={"preferredName": "Example"},
            total_release_mass_kg=5.0,
            release_fractions=[ReleaseFraction(medium=Media.WATER, fraction=1.0)],
            duration_days=10.0,
        )
    )
    result = runtime.estimate(
        scenario,
        FateModelRunOptions(region_profile_id=scenario.geographic_scope.region_id),
    )
    review_packet = build_regulatory_handoff_review_packet(
        BuildRegulatoryHandoffReviewPacketRequest(result=result, scenario=scenario),
        runtime.provenance,
    )
    review_brief = build_regulatory_handoff_review_brief(
        BuildRegulatoryHandoffReviewBriefRequest(review_packet=review_packet),
        runtime.provenance,
    )
    assert review_brief.handoff_profile_id == "exposure_scenario_mcp_v1"
    assert review_brief.target_module == "Direct-Use Exposure MCP"
    assert review_brief.review_status == "ready_for_assessor_review"
    assert review_brief.passed_check_count == review_brief.total_check_count
    assert review_brief.checklist_items
    assert review_brief.parameter_quality_lines
    assert review_brief.applicability_lines
    assert review_brief.uncertainty_lines
    assert review_brief.equation_lines
    assert any("Direct-Use Exposure MCP" in line for line in review_brief.brief_lines)


def test_build_regulatory_handoff_review_brief_builds_alternate_profile_brief() -> None:
    runtime = FateRuntime(Path(__file__).resolve().parents[1])
    scenario = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={"preferredName": "Example"},
            total_release_mass_kg=5.0,
            release_fractions=[ReleaseFraction(medium=Media.WATER, fraction=1.0)],
            duration_days=10.0,
        )
    )
    result = runtime.estimate(
        scenario,
        FateModelRunOptions(region_profile_id=scenario.geographic_scope.region_id),
    )
    review_packet = build_regulatory_handoff_review_packet(
        BuildRegulatoryHandoffReviewPacketRequest(
            result=result,
            consumer_name="ToxClaw",
        ),
        runtime.provenance,
    )
    review_brief = build_regulatory_handoff_review_brief(
        BuildRegulatoryHandoffReviewBriefRequest(review_packet=review_packet),
        runtime.provenance,
    )
    assert review_brief.handoff_profile_id == "toxclaw_orchestration_v1"
    assert review_brief.target_module == "ToxClaw"
    assert any(item.code == "field_mapping_stable" for item in review_brief.checklist_items)
    assert review_brief.equation_lines
    assert any("ToxClaw" in line for line in review_brief.brief_lines)


def test_recommend_regulatory_handoff_profile_matches_known_consumer() -> None:
    runtime = FateRuntime(Path(__file__).resolve().parents[1])
    recommendation = recommend_regulatory_handoff_profile(
        RecommendRegulatoryHandoffProfileRequest(consumer_name="workflow orchestrator"),
        runtime.provenance,
    )
    assert recommendation.resolved_profile_id == "toxclaw_orchestration_v1"
    assert recommendation.target_module == "ToxClaw"
    assert recommendation.confidence >= 0.8


def test_preview_regulatory_handoff_resolution_resolves_consumer_name() -> None:
    runtime = FateRuntime(Path(__file__).resolve().parents[1])
    preview = preview_regulatory_handoff_resolution(
        PreviewRegulatoryHandoffResolutionRequest(consumer_name="ToxClaw"),
        runtime.provenance,
    )
    assert preview.status == "resolved"
    assert preview.resolved_profile_id == "toxclaw_orchestration_v1"
    assert preview.resolution_method == "consumer_name_match"
    assert preview.matched_hint == "ToxClaw"
    assert preview.allowed_target_modules == ["ToxClaw"]


def test_preview_regulatory_handoff_resolution_flags_target_module_mismatch() -> None:
    runtime = FateRuntime(Path(__file__).resolve().parents[1])
    preview = preview_regulatory_handoff_resolution(
        PreviewRegulatoryHandoffResolutionRequest(
            consumer_name="ToxClaw",
            target_modules=["Direct-Use Exposure MCP"],
        ),
        runtime.provenance,
    )
    assert preview.status == "mismatch"
    assert preview.allowed_target_modules == ["ToxClaw"]
    assert any("governed target module ToxClaw" in issue for issue in preview.issues)


def test_export_regulatory_handoff_package_can_resolve_profile_from_consumer_name() -> None:
    runtime = FateRuntime(Path(__file__).resolve().parents[1])
    scenario = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={"preferredName": "Example"},
            total_release_mass_kg=5.0,
            release_fractions=[ReleaseFraction(medium=Media.WATER, fraction=1.0)],
            duration_days=10.0,
        )
    )
    result = runtime.estimate(
        scenario,
        FateModelRunOptions(region_profile_id=scenario.geographic_scope.region_id),
    )
    handoff = export_regulatory_handoff_package(
        ExportRegulatoryHandoffPackageRequest(
            result=result,
            consumer_name="ToxClaw",
        ),
        runtime.provenance,
    )
    assert handoff.handoff_profile_id == "toxclaw_orchestration_v1"
    assert handoff.profile_resolution_method == "consumer_name_match"
    assert handoff.profile_resolution_basis == "ToxClaw"
    assert handoff.profile_resolution_confidence >= 0.8
    assert handoff.target_modules == ["ToxClaw"]


def test_export_regulatory_handoff_package_rejects_profile_consumer_mismatch() -> None:
    runtime = FateRuntime(Path(__file__).resolve().parents[1])
    scenario = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={"preferredName": "Example"},
            total_release_mass_kg=5.0,
            release_fractions=[ReleaseFraction(medium=Media.WATER, fraction=1.0)],
            duration_days=10.0,
        )
    )
    result = runtime.estimate(
        scenario,
        FateModelRunOptions(region_profile_id=scenario.geographic_scope.region_id),
    )
    with pytest.raises(FateValidationError):
        export_regulatory_handoff_package(
            ExportRegulatoryHandoffPackageRequest(
                result=result,
                handoff_profile_id="exposure_scenario_mcp_v1",
                consumer_name="ToxClaw",
            ),
            runtime.provenance,
        )


def test_export_regulatory_handoff_package_rejects_target_module_mismatch() -> None:
    runtime = FateRuntime(Path(__file__).resolve().parents[1])
    scenario = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={"preferredName": "Example"},
            total_release_mass_kg=5.0,
            release_fractions=[ReleaseFraction(medium=Media.WATER, fraction=1.0)],
            duration_days=10.0,
        )
    )
    result = runtime.estimate(
        scenario,
        FateModelRunOptions(region_profile_id=scenario.geographic_scope.region_id),
    )
    with pytest.raises(FateValidationError):
        export_regulatory_handoff_package(
            ExportRegulatoryHandoffPackageRequest(
                result=result,
                consumer_name="ToxClaw",
                target_modules=["Direct-Use Exposure MCP"],
            ),
            runtime.provenance,
        )


def test_export_regulatory_handoff_package_rejects_unknown_profile() -> None:
    runtime = FateRuntime(Path(__file__).resolve().parents[1])
    scenario = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={"preferredName": "Example"},
            total_release_mass_kg=5.0,
            release_fractions=[ReleaseFraction(medium=Media.WATER, fraction=1.0)],
            duration_days=10.0,
        )
    )
    result = runtime.estimate(
        scenario,
        FateModelRunOptions(region_profile_id=scenario.geographic_scope.region_id),
    )
    with pytest.raises(FateValidationError):
        export_regulatory_handoff_package(
            ExportRegulatoryHandoffPackageRequest(
                result=result,
                handoff_profile_id="missing_profile",
            ),
            runtime.provenance,
        )


def test_export_regulatory_handoff_package_rejects_unknown_consumer() -> None:
    runtime = FateRuntime(Path(__file__).resolve().parents[1])
    scenario = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={"preferredName": "Example"},
            total_release_mass_kg=5.0,
            release_fractions=[ReleaseFraction(medium=Media.WATER, fraction=1.0)],
            duration_days=10.0,
        )
    )
    result = runtime.estimate(
        scenario,
        FateModelRunOptions(region_profile_id=scenario.geographic_scope.region_id),
    )
    with pytest.raises(FateValidationError):
        export_regulatory_handoff_package(
            ExportRegulatoryHandoffPackageRequest(
                result=result,
                consumer_name="unknown consumer",
            ),
            runtime.provenance,
        )


def test_export_regulatory_handoff_package_rejects_invalid_profile_requirements(monkeypatch) -> None:
    runtime = FateRuntime(Path(__file__).resolve().parents[1])
    scenario = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={"preferredName": "Example"},
            total_release_mass_kg=5.0,
            release_fractions=[ReleaseFraction(medium=Media.WATER, fraction=1.0)],
            duration_days=10.0,
        )
    )
    result = runtime.estimate(
        scenario,
        FateModelRunOptions(region_profile_id=scenario.geographic_scope.region_id),
    )
    monkeypatch.setattr(
        runtime.provenance.defaults_registry,
        "regulatory_handoff_profile",
        lambda profile_id: RegulatoryHandoffProfile(
            profile_id=profile_id,
            display_name="Bad profile",
            target_module="Direct-Use Exposure MCP",
            downstream_field="environmental_media_concentration",
            required_entry_fields=["not_a_real_field"],
            source_pack="test",
        ),
    )
    with pytest.raises(FateValidationError):
        export_regulatory_handoff_package(
            ExportRegulatoryHandoffPackageRequest(
                result=result,
                handoff_profile_id="bad_profile",
            ),
            runtime.provenance,
        )
