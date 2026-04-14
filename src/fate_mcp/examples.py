from __future__ import annotations

import json
from pathlib import Path

from fate_mcp.benchmarks import scientific_validation_claim_coverage_manifest
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
    build_probabilistic_review_brief,
    build_probabilistic_review_packet,
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
    export_exposure_consumption_package,
    export_regulatory_handoff_package,
    preview_model_family_comparison_review,
    preview_model_family_challenge_review,
    preview_model_family_selection_review,
    preview_scientific_review_outcome,
    preview_regulatory_handoff_resolution,
    recommend_model_family_selection,
    recommend_regulatory_handoff_profile,
)
from fate_mcp.models import (
    ApplyPhyschemEvidenceRequest,
    AssessReleaseScenarioFitRequest,
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
    BuildProbabilisticReviewBriefRequest,
    BuildProbabilisticReviewPacketRequest,
    BuildScientificMethodsDossierBriefRequest,
    BuildScientificMethodsDossierRequest,
    BuildRunParameterManifestRequest,
    BuildScientificReviewBriefRequest,
    BuildScientificReviewPacketRequest,
    BuildRunUncertaintySummaryRequest,
    BuildRegulatoryHandoffReviewBriefRequest,
    BuildRegulatoryHandoffReviewPacketRequest,
    BuildConcentrationSurfaceBundleRequest,
    BuildEnvironmentalReleaseScenarioRequest,
    CompareFateScenariosRequest,
    EstimateProbabilisticMultimediaConcentrationsRequest,
    ExportConcentrationSurfaceBundleRequest,
    ExportExposureConsumptionPackageRequest,
    ExportRegulatoryHandoffPackageRequest,
    FateModelRunOptions,
    FateParameterRecord,
    FitForPurpose,
    Media,
    ParameterDistribution,
    RecommendRegulatoryHandoffProfileRequest,
    RecommendModelFamilySelectionRequest,
    ReleaseFraction,
    ReconcileReleaseEvidenceRequest,
    ReleaseEvidenceInput,
    ScientificReferenceCase,
    SourceReference,
    SourceClassification,
    ModelFamily,
    SummarizeRegulatoryHandoffPackageRequest,
    PhyschemEvidenceRecord,
    PreviewModelFamilyComparisonReviewRequest,
    PreviewModelFamilyChallengeReviewRequest,
    PreviewModelFamilySelectionReviewRequest,
    PreviewScientificReviewOutcomeRequest,
    PreviewRegulatoryHandoffResolutionRequest,
)
from fate_mcp.plugins.external_result_adapter import build_adapter_import_manifest
from fate_mcp.runtime import FateRuntime


def build_examples(runtime: FateRuntime) -> dict[str, dict]:
    scenario_request = BuildEnvironmentalReleaseScenarioRequest(
        chemical_identity={"preferredName": "Example substance", "casrn": "100-00-0"},
        total_release_mass_kg=12.5,
        release_fractions=[
            ReleaseFraction(medium=Media.AIR, fraction=0.2),
            ReleaseFraction(medium=Media.WATER, fraction=0.5),
            ReleaseFraction(medium=Media.SOIL, fraction=0.3),
        ],
        duration_days=30,
        parameter_records=[
            FateParameterRecord(
                parameter="water_half_life_days",
                value=12.0,
                unit="day",
                source_classification=SourceClassification.USER_INPUT,
                rationale="Illustrative initial parameter override.",
                evidence_quality="reference",
            ),
            FateParameterRecord(
                parameter="log_kow",
                value=4.2,
                unit="log10",
                source_classification=SourceClassification.HEURISTIC,
                rationale="Illustrative preserved-only screening descriptor.",
                evidence_quality="heuristic",
            )
        ],
        evidence_sources=[
            SourceReference(
                source_id="example.release.note",
                title="Illustrative release scenario",
                effective_date="2026-04-08",
            )
        ],
    )
    scenario = runtime.build_environmental_release_scenario(scenario_request)

    steady_result = runtime.estimate(
        scenario=scenario,
        run_options=FateModelRunOptions(
            region_profile_id=scenario.geographic_scope.region_id,
            fit_for_purpose=FitForPurpose.SCREENING,
        ),
    )
    bucket_result = runtime.estimate(
        scenario=scenario,
        run_options=FateModelRunOptions(
            run_mode="time_bucket",
            region_profile_id=scenario.geographic_scope.region_id,
            bucket_count=3,
            bucket_duration_days=10,
            fit_for_purpose=FitForPurpose.DOWNSTREAM_EXPORT,
        ),
    )
    steady_run_options = FateModelRunOptions(
        region_profile_id=scenario.geographic_scope.region_id,
        fit_for_purpose=FitForPurpose.SCREENING,
    )
    bundle = build_concentration_surface_bundle(steady_result)

    comparison = runtime.estimate(
        scenario=runtime.build_environmental_release_scenario(
            scenario_request.model_copy(update={"total_release_mass_kg": 20.0})
        ),
        run_options=FateModelRunOptions(region_profile_id=scenario.geographic_scope.region_id),
    )
    evidence = [
        PhyschemEvidenceRecord(
            parameter="water_half_life_days",
            value=6.0,
            unit="day",
            source_reference=SourceReference(
                source_id="example.physchem.study",
                title="Illustrative half-life study",
                effective_date="2026-04-08",
            ),
            evidence_quality="reference",
        )
    ]
    physchem_request = ApplyPhyschemEvidenceRequest(
        scenario=scenario,
        evidence=evidence,
    )
    physchem_result = apply_physchem_evidence(
        scenario,
        evidence,
        runtime.provenance,
    )
    fit_request = AssessReleaseScenarioFitRequest(
        scenario=scenario,
        run_options=steady_run_options,
    )
    parameter_manifest = build_run_parameter_manifest(
        scenario,
        steady_result,
        runtime.provenance,
    )
    uncertainty_summary = build_run_uncertainty_summary(
        scenario,
        steady_result,
        runtime.provenance,
    )
    probabilistic_scenario = scenario.model_copy(deep=True)
    probabilistic_scenario.parameter_records = [
        record.model_copy(
            update={
                "distribution": ParameterDistribution(
                    distribution_type="uniform",
                    parameters={"low": 8.0, "high": 16.0},
                    sampling_basis="illustrative_screening_range",
                )
            }
        )
        if record.parameter == "water_half_life_days"
        else record
        for record in probabilistic_scenario.parameter_records
    ]
    probabilistic_result = runtime.estimate_probabilistic(
        probabilistic_scenario,
        steady_run_options,
        iterations=12,
        seed=17,
    )
    probabilistic_review_packet = build_probabilistic_review_packet(
        BuildProbabilisticReviewPacketRequest(
            scenario=probabilistic_scenario,
            result=probabilistic_result,
        ),
        runtime.provenance,
    )
    probabilistic_review_brief = build_probabilistic_review_brief(
        BuildProbabilisticReviewBriefRequest(
            review_packet=probabilistic_review_packet,
        ),
        runtime.provenance,
    )
    scientific_review_outcome_preview = preview_scientific_review_outcome(
        PreviewScientificReviewOutcomeRequest(
            scenario=scenario,
            result=steady_result,
        ),
        runtime.provenance,
    )
    scientific_review_packet = build_scientific_review_packet(
        BuildScientificReviewPacketRequest(
            scenario=scenario,
            result=steady_result,
        ),
        runtime.provenance,
    )
    scientific_review_brief = build_scientific_review_brief(
        BuildScientificReviewBriefRequest(review_packet=scientific_review_packet),
        runtime.provenance,
    )
    scientific_reference_case = runtime.defaults.scientific_reference_case(
        "echa_euses_water_screening_case_family_v1"
    )
    scientific_methods_dossier = build_scientific_methods_dossier(
        BuildScientificMethodsDossierRequest(
            model_family=ModelFamily.ADVECTIVE_SCREENING_MASS_BALANCE,
        ),
        runtime.provenance,
    )
    scientific_methods_dossier_brief = build_scientific_methods_dossier_brief(
        BuildScientificMethodsDossierBriefRequest(
            dossier=scientific_methods_dossier,
        )
    )
    model_family_comparison_request = BuildModelFamilyComparisonPacketRequest(
        scenario=scenario,
        comparison_profile_id="reference_vs_advective_screening_v1",
        candidate_model_family=ModelFamily.ADVECTIVE_SCREENING_MASS_BALANCE,
    )
    model_family_selection_request = RecommendModelFamilySelectionRequest(
        scenario=scenario,
        selection_profile_id="reference_baseline_advective_challenge_v1",
    )
    model_family_selection_recommendation = recommend_model_family_selection(
        model_family_selection_request,
        runtime.provenance,
    )
    model_family_selection_review_preview = preview_model_family_selection_review(
        PreviewModelFamilySelectionReviewRequest(
            selection_recommendation=model_family_selection_recommendation,
        ),
        runtime.provenance,
    )
    model_family_selection_review_packet = build_model_family_selection_review_packet(
        BuildModelFamilySelectionReviewPacketRequest(
            selection_recommendation=model_family_selection_recommendation,
        ),
        runtime.provenance,
    )
    model_family_selection_review_brief = build_model_family_selection_review_brief(
        BuildModelFamilySelectionReviewBriefRequest(
            review_packet=model_family_selection_review_packet,
        ),
        runtime.provenance,
    )
    model_family_comparison_packet = build_model_family_comparison_packet(
        model_family_comparison_request,
        runtime,
        runtime.provenance,
    )
    model_family_comparison_brief = build_model_family_comparison_brief(
        BuildModelFamilyComparisonBriefRequest(
            comparison_packet=model_family_comparison_packet,
        )
    )
    model_family_comparison_review_preview = preview_model_family_comparison_review(
        PreviewModelFamilyComparisonReviewRequest(
            comparison_packet=model_family_comparison_packet,
        ),
        runtime.provenance,
    )
    model_family_comparison_review_packet = build_model_family_comparison_review_packet(
        BuildModelFamilyComparisonReviewPacketRequest(
            comparison_packet=model_family_comparison_packet,
        ),
        runtime.provenance,
    )
    model_family_comparison_review_brief = build_model_family_comparison_review_brief(
        BuildModelFamilyComparisonReviewBriefRequest(
            review_packet=model_family_comparison_review_packet,
        ),
        runtime.provenance,
    )
    model_family_challenge_review_request = BuildModelFamilyChallengeReviewPacketRequest(
        scenario=scenario,
        selection_profile_id="reference_baseline_advective_challenge_v1",
    )
    model_family_challenge_review_preview = preview_model_family_challenge_review(
        PreviewModelFamilyChallengeReviewRequest(
            scenario=scenario,
            selection_profile_id="reference_baseline_advective_challenge_v1",
        ),
        runtime,
        runtime.provenance,
    )
    model_family_challenge_review_packet = build_model_family_challenge_review_packet(
        model_family_challenge_review_request,
        runtime,
        runtime.provenance,
    )
    model_family_challenge_review_brief = build_model_family_challenge_review_brief(
        BuildModelFamilyChallengeReviewBriefRequest(
            review_packet=model_family_challenge_review_packet,
        ),
        runtime.provenance,
    )
    model_family_challenge_scientific_dossier_request = BuildModelFamilyChallengeScientificDossierRequest(
        scenario=scenario,
        selection_profile_id="reference_baseline_advective_challenge_v1",
    )
    model_family_challenge_scientific_dossier = build_model_family_challenge_scientific_dossier(
        model_family_challenge_scientific_dossier_request,
        runtime,
        runtime.provenance,
    )
    model_family_challenge_scientific_dossier_brief = build_model_family_challenge_scientific_dossier_brief(
        BuildModelFamilyChallengeScientificDossierBriefRequest(
            dossier=model_family_challenge_scientific_dossier,
        ),
        runtime.provenance,
    )
    reconcile_request = ReconcileReleaseEvidenceRequest(
        chemical_identity={"preferredName": "Example substance", "casrn": "100-00-0"},
        region_id=scenario.geographic_scope.region_id,
        context_label=scenario.geographic_scope.context_label,
        duration_days=30,
        evidence_inputs=[
            ReleaseEvidenceInput(
                label="monitoring_record_a",
                total_release_mass_kg=10.0,
                evidence_quality="measured",
                release_fractions=[
                    ReleaseFraction(medium=Media.WATER, fraction=0.7),
                    ReleaseFraction(medium=Media.SOIL, fraction=0.3),
                ],
                source_reference=SourceReference(
                    source_id="example.release.a",
                    title="Illustrative monitoring record A",
                    effective_date="2026-04-08",
                ),
            ),
            ReleaseEvidenceInput(
                label="monitoring_record_b",
                total_release_mass_kg=16.0,
                evidence_quality="heuristic",
                release_fractions=[
                    ReleaseFraction(medium=Media.WATER, fraction=0.3),
                    ReleaseFraction(medium=Media.SOIL, fraction=0.7),
                ],
                source_reference=SourceReference(
                    source_id="example.release.b",
                    title="Illustrative monitoring record B",
                    effective_date="2026-04-08",
                ),
            ),
        ],
    )
    reconciliation_result = runtime.reconcile_release_evidence(reconcile_request)
    regulatory_handoff_review_packet = build_regulatory_handoff_review_packet(
        BuildRegulatoryHandoffReviewPacketRequest(
            result=steady_result,
            scenario=scenario,
        ),
        runtime.provenance,
    )
    regulatory_handoff_review_brief = build_regulatory_handoff_review_brief(
        BuildRegulatoryHandoffReviewBriefRequest(review_packet=regulatory_handoff_review_packet),
        runtime.provenance,
    )
    regulatory_handoff_package = regulatory_handoff_review_packet.package

    return {
        "adapterImportManifest.v1": build_adapter_import_manifest(runtime.repo_root).model_dump(mode="json"),
        "adapterUnitConversionRule.v1": runtime.defaults.list_adapter_unit_conversion_rules()[0].model_dump(mode="json"),
        "buildEnvironmentalReleaseScenarioRequest.v1": scenario_request.model_dump(mode="json"),
        "environmentalReleaseScenario.v1": scenario.model_dump(mode="json"),
        "modelFamilyApplicabilityProfile.v1": runtime.defaults.model_family_applicability_profile(
            ModelFamily.ADVECTIVE_SCREENING_MASS_BALANCE
        ).model_dump(mode="json"),
        "scientificValidationClaim.v1": runtime.defaults.list_scientific_validation_claims()[0].model_dump(mode="json"),
        "scientificValidationClaimManifest.v1": runtime.defaults.scientific_validation_claim_manifest().model_dump(mode="json"),
        "scientificReferenceCase.v1": scientific_reference_case.model_dump(mode="json"),
        "scientificReferenceCaseManifest.v1": runtime.defaults.scientific_reference_case_manifest().model_dump(mode="json"),
        "scientificValidationClaimCoverageManifest.v1": scientific_validation_claim_coverage_manifest(
            runtime.repo_root
        ).model_dump(mode="json"),
        "scientificMethodsDossierClaimSummary.v1": scientific_methods_dossier.claim_summaries[0].model_dump(mode="json"),
        "buildScientificMethodsDossierRequest.v1": BuildScientificMethodsDossierRequest(
            model_family=ModelFamily.ADVECTIVE_SCREENING_MASS_BALANCE
        ).model_dump(mode="json"),
        "scientificMethodsDossier.v1": scientific_methods_dossier.model_dump(mode="json"),
        "buildScientificMethodsDossierBriefRequest.v1": BuildScientificMethodsDossierBriefRequest(
            dossier=scientific_methods_dossier
        ).model_dump(mode="json"),
        "scientificMethodsDossierBrief.v1": scientific_methods_dossier_brief.model_dump(mode="json"),
        "modelFamilyComparisonProfile.v1": runtime.defaults.model_family_comparison_profile(
            "reference_vs_advective_screening_v1"
        ).model_dump(mode="json"),
        "modelFamilyComparisonProfileManifest.v1": runtime.defaults.model_family_comparison_profile_manifest().model_dump(mode="json"),
        "modelFamilySelectionProfile.v1": runtime.defaults.model_family_selection_profile(
            "reference_baseline_advective_challenge_v1"
        ).model_dump(mode="json"),
        "modelFamilySelectionProfileManifest.v1": runtime.defaults.model_family_selection_profile_manifest().model_dump(mode="json"),
        "modelFamilyChallengeReviewProfile.v1": runtime.defaults.model_family_challenge_review_profile(
            "reference_baseline_advective_challenge_review_v1"
        ).model_dump(mode="json"),
        "modelFamilyChallengeReviewProfileManifest.v1": runtime.defaults.model_family_challenge_review_profile_manifest().model_dump(mode="json"),
        "scientificReviewProfile.v1": runtime.defaults.scientific_review_profile(
            ModelFamily.ADVECTIVE_SCREENING_MASS_BALANCE
        ).model_dump(mode="json"),
        "scientificReviewProfileManifest.v1": runtime.defaults.scientific_review_profile_manifest().model_dump(mode="json"),
        "fateParameterPolicy.v1": runtime.defaults.list_physchem_parameter_policies()[0].model_dump(mode="json"),
        "fateParameterPolicyFamily.v1": runtime.defaults.list_physchem_parameter_policy_families()[0].model_dump(mode="json"),
        "regulatoryHandoffConsumerAliasManifest.v1": runtime.defaults.regulatory_handoff_consumer_alias_manifest().model_dump(mode="json"),
        "regulatoryHandoffProfile.v1": runtime.defaults.list_regulatory_handoff_profiles()[0].model_dump(mode="json"),
        "recommendRegulatoryHandoffProfileRequest.v1": RecommendRegulatoryHandoffProfileRequest(
            consumer_name="ToxClaw"
        ).model_dump(mode="json"),
        "regulatoryHandoffProfileRecommendation.v1": recommend_regulatory_handoff_profile(
            RecommendRegulatoryHandoffProfileRequest(consumer_name="ToxClaw"),
            runtime.provenance,
        ).model_dump(mode="json"),
        "regulatoryHandoffTargetMatrixManifest.v1": runtime.defaults.regulatory_handoff_target_matrix_manifest().model_dump(mode="json"),
        "fateParameterRecord.v1": scenario.parameter_records[0].model_dump(mode="json"),
        "fateRegionProfile.v1": runtime.defaults.list_region_profiles()[0].model_dump(mode="json"),
        "fateModelRunOptions.v1": steady_run_options.model_dump(mode="json"),
        "calculationTrace.v1": steady_result.surfaces[0].calculation_trace.model_dump(mode="json"),
        "estimateMultimediaConcentrationsRequest.v1": {
            "scenario": scenario.model_dump(mode="json"),
            "run_options": steady_run_options.model_dump(mode="json"),
        },
        "estimateProbabilisticMultimediaConcentrationsRequest.v1": EstimateProbabilisticMultimediaConcentrationsRequest(
            scenario=probabilistic_scenario,
            run_options=steady_run_options,
            iterations=12,
            seed=17,
        ).model_dump(mode="json"),
        "buildConcentrationSurfaceBundleRequest.v1": BuildConcentrationSurfaceBundleRequest(
            result=steady_result
        ).model_dump(mode="json"),
        "concentrationSurfaceBundle.v1": bundle.model_dump(mode="json"),
        "concentrationEstimation.timeBucket.v1": bucket_result.model_dump(mode="json"),
        "compareFateScenariosRequest.v1": CompareFateScenariosRequest(
            base_result=steady_result,
            candidate_result=comparison,
        ).model_dump(mode="json"),
        "fateScenarioComparisonRecord.v1": compare_fate_scenarios(
            CompareFateScenariosRequest(base_result=steady_result, candidate_result=comparison),
            runtime.provenance,
        ).model_dump(mode="json"),
        "applyPhyschemEvidenceRequest.v1": physchem_request.model_dump(mode="json"),
        "physchemEvidenceApplicationResult.v1": physchem_result.model_dump(mode="json"),
        "assessReleaseScenarioFitRequest.v1": fit_request.model_dump(mode="json"),
        "releaseScenarioFitAssessment.v1": assess_release_scenario_fit(
            scenario,
            steady_run_options,
            runtime.provenance,
        ).model_dump(mode="json"),
        "buildRunParameterManifestRequest.v1": BuildRunParameterManifestRequest(
            scenario=scenario,
            result=steady_result,
        ).model_dump(mode="json"),
        "runParameterManifest.v1": parameter_manifest.model_dump(mode="json"),
        "buildRunUncertaintySummaryRequest.v1": BuildRunUncertaintySummaryRequest(
            scenario=scenario,
            result=steady_result,
        ).model_dump(mode="json"),
        "runUncertaintySummary.v1": uncertainty_summary.model_dump(mode="json"),
        "probabilisticConcentrationResult.v1": probabilistic_result.model_dump(mode="json"),
        "buildProbabilisticReviewPacketRequest.v1": BuildProbabilisticReviewPacketRequest(
            scenario=probabilistic_scenario,
            result=probabilistic_result,
        ).model_dump(mode="json"),
        "probabilisticReviewPacket.v1": probabilistic_review_packet.model_dump(mode="json"),
        "buildProbabilisticReviewBriefRequest.v1": BuildProbabilisticReviewBriefRequest(
            review_packet=probabilistic_review_packet
        ).model_dump(mode="json"),
        "probabilisticReviewBrief.v1": probabilistic_review_brief.model_dump(mode="json"),
        "previewScientificReviewOutcomeRequest.v1": PreviewScientificReviewOutcomeRequest(
            scenario=scenario,
            result=steady_result,
        ).model_dump(mode="json"),
        "scientificReviewOutcomePreview.v1": scientific_review_outcome_preview.model_dump(mode="json"),
        "buildScientificReviewPacketRequest.v1": BuildScientificReviewPacketRequest(
            scenario=scenario,
            result=steady_result,
        ).model_dump(mode="json"),
        "scientificReviewPacket.v1": scientific_review_packet.model_dump(mode="json"),
        "buildScientificReviewBriefRequest.v1": BuildScientificReviewBriefRequest(
            review_packet=scientific_review_packet
        ).model_dump(mode="json"),
        "scientificReviewBrief.v1": scientific_review_brief.model_dump(mode="json"),
        "buildModelFamilyComparisonPacketRequest.v1": model_family_comparison_request.model_dump(mode="json"),
        "recommendModelFamilySelectionRequest.v1": model_family_selection_request.model_dump(mode="json"),
        "modelFamilySelectionRecommendation.v1": model_family_selection_recommendation.model_dump(mode="json"),
        "previewModelFamilySelectionReviewRequest.v1": PreviewModelFamilySelectionReviewRequest(
            selection_recommendation=model_family_selection_recommendation
        ).model_dump(mode="json"),
        "modelFamilySelectionReviewPreview.v1": model_family_selection_review_preview.model_dump(mode="json"),
        "buildModelFamilySelectionReviewPacketRequest.v1": BuildModelFamilySelectionReviewPacketRequest(
            selection_recommendation=model_family_selection_recommendation
        ).model_dump(mode="json"),
        "modelFamilySelectionReviewPacket.v1": model_family_selection_review_packet.model_dump(mode="json"),
        "buildModelFamilySelectionReviewBriefRequest.v1": BuildModelFamilySelectionReviewBriefRequest(
            review_packet=model_family_selection_review_packet
        ).model_dump(mode="json"),
        "modelFamilySelectionReviewBrief.v1": model_family_selection_review_brief.model_dump(mode="json"),
        "modelFamilyComparisonPacket.v1": model_family_comparison_packet.model_dump(mode="json"),
        "buildModelFamilyComparisonBriefRequest.v1": BuildModelFamilyComparisonBriefRequest(
            comparison_packet=model_family_comparison_packet
        ).model_dump(mode="json"),
        "modelFamilyComparisonBrief.v1": model_family_comparison_brief.model_dump(mode="json"),
        "previewModelFamilyComparisonReviewRequest.v1": PreviewModelFamilyComparisonReviewRequest(
            comparison_packet=model_family_comparison_packet
        ).model_dump(mode="json"),
        "modelFamilyComparisonReviewPreview.v1": model_family_comparison_review_preview.model_dump(mode="json"),
        "buildModelFamilyComparisonReviewPacketRequest.v1": BuildModelFamilyComparisonReviewPacketRequest(
            comparison_packet=model_family_comparison_packet
        ).model_dump(mode="json"),
        "modelFamilyComparisonReviewPacket.v1": model_family_comparison_review_packet.model_dump(mode="json"),
        "buildModelFamilyComparisonReviewBriefRequest.v1": BuildModelFamilyComparisonReviewBriefRequest(
            review_packet=model_family_comparison_review_packet
        ).model_dump(mode="json"),
        "modelFamilyComparisonReviewBrief.v1": model_family_comparison_review_brief.model_dump(mode="json"),
        "previewModelFamilyChallengeReviewRequest.v1": PreviewModelFamilyChallengeReviewRequest(
            scenario=scenario,
            selection_profile_id="reference_baseline_advective_challenge_v1",
        ).model_dump(mode="json"),
        "modelFamilyChallengeReviewPreview.v1": model_family_challenge_review_preview.model_dump(mode="json"),
        "buildModelFamilyChallengeReviewPacketRequest.v1": model_family_challenge_review_request.model_dump(
            mode="json"
        ),
        "modelFamilyChallengeReviewPacket.v1": model_family_challenge_review_packet.model_dump(mode="json"),
        "buildModelFamilyChallengeReviewBriefRequest.v1": BuildModelFamilyChallengeReviewBriefRequest(
            review_packet=model_family_challenge_review_packet
        ).model_dump(mode="json"),
        "modelFamilyChallengeReviewBrief.v1": model_family_challenge_review_brief.model_dump(mode="json"),
        "buildModelFamilyChallengeScientificDossierRequest.v1": model_family_challenge_scientific_dossier_request.model_dump(
            mode="json"
        ),
        "modelFamilyChallengeScientificDossier.v1": model_family_challenge_scientific_dossier.model_dump(mode="json"),
        "buildModelFamilyChallengeScientificDossierBriefRequest.v1": BuildModelFamilyChallengeScientificDossierBriefRequest(
            dossier=model_family_challenge_scientific_dossier
        ).model_dump(mode="json"),
        "modelFamilyChallengeScientificDossierBrief.v1": model_family_challenge_scientific_dossier_brief.model_dump(
            mode="json"
        ),
        "reconcileReleaseEvidenceRequest.v1": reconcile_request.model_dump(mode="json"),
        "releaseEvidenceReconciliationResult.v1": reconciliation_result.model_dump(mode="json"),
        "exportConcentrationSurfaceBundleRequest.v1": ExportConcentrationSurfaceBundleRequest(
            bundle=bundle
        ).model_dump(mode="json"),
        "exposureConsumptionPackage.v1": export_exposure_consumption_package(
            ExportExposureConsumptionPackageRequest(result=steady_result),
            runtime.provenance,
        ).model_dump(mode="json"),
        "exportExposureConsumptionPackageRequest.v1": ExportExposureConsumptionPackageRequest(
            result=steady_result
        ).model_dump(mode="json"),
        "previewRegulatoryHandoffResolutionRequest.v1": PreviewRegulatoryHandoffResolutionRequest(
            consumer_name="ToxClaw"
        ).model_dump(mode="json"),
        "regulatoryHandoffResolutionPreview.v1": preview_regulatory_handoff_resolution(
            PreviewRegulatoryHandoffResolutionRequest(consumer_name="ToxClaw"),
            runtime.provenance,
        ).model_dump(mode="json"),
        "buildRegulatoryHandoffReviewPacketRequest.v1": BuildRegulatoryHandoffReviewPacketRequest(
            result=steady_result,
            scenario=scenario,
        ).model_dump(mode="json"),
        "buildRegulatoryHandoffReviewBriefRequest.v1": BuildRegulatoryHandoffReviewBriefRequest(
            review_packet=regulatory_handoff_review_packet
        ).model_dump(mode="json"),
        "regulatoryHandoffPackage.v1": regulatory_handoff_package.model_dump(mode="json"),
        "summarizeRegulatoryHandoffPackageRequest.v1": SummarizeRegulatoryHandoffPackageRequest(
            package=regulatory_handoff_package
        ).model_dump(mode="json"),
        "regulatoryHandoffPackageSummary.v1": regulatory_handoff_review_packet.summary.model_dump(mode="json"),
        "regulatoryHandoffReviewPacket.v1": regulatory_handoff_review_packet.model_dump(mode="json"),
        "regulatoryHandoffReviewBrief.v1": regulatory_handoff_review_brief.model_dump(mode="json"),
        "exportRegulatoryHandoffPackageRequest.v1": ExportRegulatoryHandoffPackageRequest(
            result=steady_result,
            scenario=scenario,
            consumer_name="Direct-Use Exposure MCP",
        ).model_dump(mode="json"),
    }


def write_examples(repo_root: Path, runtime: FateRuntime) -> dict[str, dict]:
    examples = build_examples(runtime)
    target_dir = repo_root / "schemas" / "examples"
    target_dir.mkdir(parents=True, exist_ok=True)
    for name, payload in examples.items():
        (target_dir / f"{name}.json").write_text(json.dumps(payload, indent=2) + "\n")
    manifest = {
        "examples": [
            {"name": name, "path": f"schemas/examples/{name}.json"} for name in sorted(examples.keys())
        ]
    }
    (target_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return examples
