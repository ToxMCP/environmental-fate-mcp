from __future__ import annotations

import json
from pathlib import Path

from fate_mcp.examples import write_examples
from fate_mcp.models import (
    AdapterImportManifest,
    AdapterUnitConversionRule,
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
    BuildRunScientificTrustBriefRequest,
    BuildScientificReviewBriefRequest,
    BuildScientificReviewPacketRequest,
    BuildRunUncertaintySummaryRequest,
    BuildRegulatoryHandoffReviewBriefRequest,
    BuildRegulatoryHandoffReviewPacketRequest,
    BuildConcentrationSurfaceBundleRequest,
    BuildEnvironmentalReleaseScenarioRequest,
    CalculationTrace,
    CompareFateScenariosRequest,
    ConcentrationEstimationResult,
    ConcentrationSurface,
    ConcentrationSurfaceBundle,
    EnvironmentalReleaseScenario,
    EstimateProbabilisticMultimediaConcentrationsRequest,
    EstimateMultimediaConcentrationsRequest,
    ImportExternalResultPayloadRequest,
    ExportConcentrationSurfaceBundleRequest,
    ExportExposureConsumptionPackageRequest,
    ExportRegulatoryHandoffPackageRequest,
    ExposureConsumptionPackage,
    FateAssumptionRecord,
    FateModelRunOptions,
    FateParameterPolicy,
    FateParameterPolicyFamily,
    FateParameterRecord,
    FateRegionProfile,
    FateRunSummary,
    FateScenarioComparisonRecord,
    ModelFamilyComparisonBrief,
    ModelFamilyComparisonPacket,
    ModelFamilyComparisonProfile,
    ModelFamilyComparisonProfileManifest,
    ModelFamilyComparisonReviewBrief,
    ModelFamilyComparisonReviewPacket,
    ModelFamilyComparisonReviewPreview,
    ModelFamilyChallengeScientificDossier,
    ModelFamilyChallengeScientificDossierBrief,
    ModelFamilyChallengeReviewBrief,
    ModelFamilyChallengeReviewPacket,
    ModelFamilyChallengeReviewProfile,
    ModelFamilyChallengeReviewProfileManifest,
    ModelFamilyChallengeReviewPreview,
    ModelFamilySelectionProfile,
    ModelFamilySelectionProfileManifest,
    ModelFamilySelectionRecommendation,
    ModelFamilySelectionReviewBrief,
    ModelFamilySelectionReviewPacket,
    ModelFamilySelectionReviewPreview,
    ModelFamilyApplicabilityProfile,
    PhyschemEvidenceApplicationResult,
    ProbabilisticConcentrationResult,
    ProbabilisticReviewBrief,
    ProbabilisticReviewPacket,
    RecommendModelFamilySelectionRequest,
    PreviewModelFamilyComparisonReviewRequest,
    PreviewModelFamilyChallengeReviewRequest,
    PreviewModelFamilySelectionReviewRequest,
    PreviewScientificReviewOutcomeRequest,
    PreviewRegulatoryHandoffResolutionRequest,
    RegulatoryHandoffConsumerAliasManifest,
    RegulatoryHandoffReviewBrief,
    RegulatoryHandoffReviewPacket,
    RegulatoryHandoffPackageSummary,
    RegulatoryHandoffResolutionPreview,
    RecommendRegulatoryHandoffProfileRequest,
    RegulatoryHandoffProfile,
    RegulatoryHandoffProfileRecommendation,
    RegulatoryHandoffTargetMatrixManifest,
    RegulatoryHandoffPackage,
    ReconcileReleaseEvidenceRequest,
    ReleaseEvidenceReconciliationResult,
    ReleaseScenarioFitAssessment,
    RunParameterManifest,
    RunScientificTrustBrief,
    RunUncertaintySummary,
    ScientificValidationClaim,
    ScientificValidationClaimCoverageManifest,
    ScientificValidationClaimCoverageRecord,
    ScientificValidationClaimManifest,
    ScientificMethodsDossier,
    ScientificMethodsDossierBrief,
    ScientificMethodsDossierClaimSummary,
    ScientificReviewOutcomePreview,
    ScientificReviewProfile,
    ScientificReviewProfileManifest,
    ScientificReferenceCase,
    ScientificReferenceCaseManifest,
    ScientificReviewBrief,
    ScientificReviewPacket,
    SummarizeRegulatoryHandoffPackageRequest,
)
from fate_mcp.resources import refresh_packaged_resource_mirror
from fate_mcp.runtime import FateRuntime


SCHEMA_MODELS = {
    "adapterImportManifest.v1": AdapterImportManifest,
    "adapterUnitConversionRule.v1": AdapterUnitConversionRule,
    "buildEnvironmentalReleaseScenarioRequest.v1": BuildEnvironmentalReleaseScenarioRequest,
    "environmentalReleaseScenario.v1": EnvironmentalReleaseScenario,
    "modelFamilyApplicabilityProfile.v1": ModelFamilyApplicabilityProfile,
    "scientificValidationClaim.v1": ScientificValidationClaim,
    "scientificValidationClaimManifest.v1": ScientificValidationClaimManifest,
    "scientificReferenceCase.v1": ScientificReferenceCase,
    "scientificReferenceCaseManifest.v1": ScientificReferenceCaseManifest,
    "scientificValidationClaimCoverageRecord.v1": ScientificValidationClaimCoverageRecord,
    "scientificValidationClaimCoverageManifest.v1": ScientificValidationClaimCoverageManifest,
    "scientificMethodsDossierClaimSummary.v1": ScientificMethodsDossierClaimSummary,
    "buildScientificMethodsDossierRequest.v1": BuildScientificMethodsDossierRequest,
    "scientificMethodsDossier.v1": ScientificMethodsDossier,
    "buildScientificMethodsDossierBriefRequest.v1": BuildScientificMethodsDossierBriefRequest,
    "scientificMethodsDossierBrief.v1": ScientificMethodsDossierBrief,
    "modelFamilyComparisonProfile.v1": ModelFamilyComparisonProfile,
    "modelFamilyComparisonProfileManifest.v1": ModelFamilyComparisonProfileManifest,
    "modelFamilySelectionProfile.v1": ModelFamilySelectionProfile,
    "modelFamilySelectionProfileManifest.v1": ModelFamilySelectionProfileManifest,
    "modelFamilyChallengeReviewProfile.v1": ModelFamilyChallengeReviewProfile,
    "modelFamilyChallengeReviewProfileManifest.v1": ModelFamilyChallengeReviewProfileManifest,
    "scientificReviewProfile.v1": ScientificReviewProfile,
    "scientificReviewProfileManifest.v1": ScientificReviewProfileManifest,
    "fateParameterPolicy.v1": FateParameterPolicy,
    "fateParameterPolicyFamily.v1": FateParameterPolicyFamily,
    "fateParameterRecord.v1": FateParameterRecord,
    "fateRegionProfile.v1": FateRegionProfile,
    "fateModelRunOptions.v1": FateModelRunOptions,
    "estimateMultimediaConcentrationsRequest.v1": EstimateMultimediaConcentrationsRequest,
    "estimateProbabilisticMultimediaConcentrationsRequest.v1": EstimateProbabilisticMultimediaConcentrationsRequest,
    "importExternalResultPayloadRequest.v1": ImportExternalResultPayloadRequest,
    "calculationTrace.v1": CalculationTrace,
    "concentrationSurface.v1": ConcentrationSurface,
    "concentrationEstimationResult.v1": ConcentrationEstimationResult,
    "probabilisticConcentrationResult.v1": ProbabilisticConcentrationResult,
    "buildConcentrationSurfaceBundleRequest.v1": BuildConcentrationSurfaceBundleRequest,
    "concentrationSurfaceBundle.v1": ConcentrationSurfaceBundle,
    "fateRunSummary.v1": FateRunSummary,
    "fateAssumptionRecord.v1": FateAssumptionRecord,
    "compareFateScenariosRequest.v1": CompareFateScenariosRequest,
    "fateScenarioComparisonRecord.v1": FateScenarioComparisonRecord,
    "applyPhyschemEvidenceRequest.v1": ApplyPhyschemEvidenceRequest,
    "physchemEvidenceApplicationResult.v1": PhyschemEvidenceApplicationResult,
    "assessReleaseScenarioFitRequest.v1": AssessReleaseScenarioFitRequest,
    "releaseScenarioFitAssessment.v1": ReleaseScenarioFitAssessment,
    "buildModelFamilyComparisonPacketRequest.v1": BuildModelFamilyComparisonPacketRequest,
    "modelFamilyComparisonPacket.v1": ModelFamilyComparisonPacket,
    "buildModelFamilyComparisonBriefRequest.v1": BuildModelFamilyComparisonBriefRequest,
    "modelFamilyComparisonBrief.v1": ModelFamilyComparisonBrief,
    "previewModelFamilyComparisonReviewRequest.v1": PreviewModelFamilyComparisonReviewRequest,
    "modelFamilyComparisonReviewPreview.v1": ModelFamilyComparisonReviewPreview,
    "buildModelFamilyComparisonReviewPacketRequest.v1": BuildModelFamilyComparisonReviewPacketRequest,
    "modelFamilyComparisonReviewPacket.v1": ModelFamilyComparisonReviewPacket,
    "buildModelFamilyComparisonReviewBriefRequest.v1": BuildModelFamilyComparisonReviewBriefRequest,
    "modelFamilyComparisonReviewBrief.v1": ModelFamilyComparisonReviewBrief,
    "previewModelFamilyChallengeReviewRequest.v1": PreviewModelFamilyChallengeReviewRequest,
    "modelFamilyChallengeReviewPreview.v1": ModelFamilyChallengeReviewPreview,
    "buildModelFamilyChallengeReviewPacketRequest.v1": BuildModelFamilyChallengeReviewPacketRequest,
    "modelFamilyChallengeReviewPacket.v1": ModelFamilyChallengeReviewPacket,
    "buildModelFamilyChallengeReviewBriefRequest.v1": BuildModelFamilyChallengeReviewBriefRequest,
    "modelFamilyChallengeReviewBrief.v1": ModelFamilyChallengeReviewBrief,
    "buildModelFamilyChallengeScientificDossierRequest.v1": BuildModelFamilyChallengeScientificDossierRequest,
    "modelFamilyChallengeScientificDossier.v1": ModelFamilyChallengeScientificDossier,
    "buildModelFamilyChallengeScientificDossierBriefRequest.v1": BuildModelFamilyChallengeScientificDossierBriefRequest,
    "modelFamilyChallengeScientificDossierBrief.v1": ModelFamilyChallengeScientificDossierBrief,
    "recommendModelFamilySelectionRequest.v1": RecommendModelFamilySelectionRequest,
    "modelFamilySelectionRecommendation.v1": ModelFamilySelectionRecommendation,
    "previewModelFamilySelectionReviewRequest.v1": PreviewModelFamilySelectionReviewRequest,
    "modelFamilySelectionReviewPreview.v1": ModelFamilySelectionReviewPreview,
    "buildModelFamilySelectionReviewPacketRequest.v1": BuildModelFamilySelectionReviewPacketRequest,
    "modelFamilySelectionReviewPacket.v1": ModelFamilySelectionReviewPacket,
    "buildModelFamilySelectionReviewBriefRequest.v1": BuildModelFamilySelectionReviewBriefRequest,
    "modelFamilySelectionReviewBrief.v1": ModelFamilySelectionReviewBrief,
    "buildRunParameterManifestRequest.v1": BuildRunParameterManifestRequest,
    "runParameterManifest.v1": RunParameterManifest,
    "buildRunUncertaintySummaryRequest.v1": BuildRunUncertaintySummaryRequest,
    "runUncertaintySummary.v1": RunUncertaintySummary,
    "buildRunScientificTrustBriefRequest.v1": BuildRunScientificTrustBriefRequest,
    "runScientificTrustBrief.v1": RunScientificTrustBrief,
    "buildProbabilisticReviewPacketRequest.v1": BuildProbabilisticReviewPacketRequest,
    "probabilisticReviewPacket.v1": ProbabilisticReviewPacket,
    "buildProbabilisticReviewBriefRequest.v1": BuildProbabilisticReviewBriefRequest,
    "probabilisticReviewBrief.v1": ProbabilisticReviewBrief,
    "previewScientificReviewOutcomeRequest.v1": PreviewScientificReviewOutcomeRequest,
    "scientificReviewOutcomePreview.v1": ScientificReviewOutcomePreview,
    "buildScientificReviewPacketRequest.v1": BuildScientificReviewPacketRequest,
    "scientificReviewPacket.v1": ScientificReviewPacket,
    "buildScientificReviewBriefRequest.v1": BuildScientificReviewBriefRequest,
    "scientificReviewBrief.v1": ScientificReviewBrief,
    "reconcileReleaseEvidenceRequest.v1": ReconcileReleaseEvidenceRequest,
    "releaseEvidenceReconciliationResult.v1": ReleaseEvidenceReconciliationResult,
    "exportConcentrationSurfaceBundleRequest.v1": ExportConcentrationSurfaceBundleRequest,
    "exportExposureConsumptionPackageRequest.v1": ExportExposureConsumptionPackageRequest,
    "exposureConsumptionPackage.v1": ExposureConsumptionPackage,
    "previewRegulatoryHandoffResolutionRequest.v1": PreviewRegulatoryHandoffResolutionRequest,
    "regulatoryHandoffConsumerAliasManifest.v1": RegulatoryHandoffConsumerAliasManifest,
    "regulatoryHandoffProfile.v1": RegulatoryHandoffProfile,
    "summarizeRegulatoryHandoffPackageRequest.v1": SummarizeRegulatoryHandoffPackageRequest,
    "buildRegulatoryHandoffReviewBriefRequest.v1": BuildRegulatoryHandoffReviewBriefRequest,
    "buildRegulatoryHandoffReviewPacketRequest.v1": BuildRegulatoryHandoffReviewPacketRequest,
    "regulatoryHandoffResolutionPreview.v1": RegulatoryHandoffResolutionPreview,
    "recommendRegulatoryHandoffProfileRequest.v1": RecommendRegulatoryHandoffProfileRequest,
    "regulatoryHandoffProfileRecommendation.v1": RegulatoryHandoffProfileRecommendation,
    "regulatoryHandoffReviewBrief.v1": RegulatoryHandoffReviewBrief,
    "regulatoryHandoffPackageSummary.v1": RegulatoryHandoffPackageSummary,
    "regulatoryHandoffReviewPacket.v1": RegulatoryHandoffReviewPacket,
    "regulatoryHandoffTargetMatrixManifest.v1": RegulatoryHandoffTargetMatrixManifest,
    "exportRegulatoryHandoffPackageRequest.v1": ExportRegulatoryHandoffPackageRequest,
    "regulatoryHandoffPackage.v1": RegulatoryHandoffPackage,
}


def build_contract_manifest() -> dict:
    return {
        "schemas": [
            {
                "name": name,
                "path": f"docs/contracts/schemas/{name}.json",
            }
            for name in sorted(SCHEMA_MODELS.keys())
        ],
        "examples": {
            "path": "schemas/examples/manifest.json",
        },
    }


def generate_contract_artifacts(repo_root: Path) -> None:
    schema_dir = repo_root / "docs" / "contracts" / "schemas"
    schema_dir.mkdir(parents=True, exist_ok=True)
    for name, model in SCHEMA_MODELS.items():
        (schema_dir / f"{name}.json").write_text(json.dumps(model.model_json_schema(), indent=2) + "\n")
    (schema_dir / "manifest.json").write_text(json.dumps(build_contract_manifest(), indent=2) + "\n")

    runtime = FateRuntime(repo_root, verify_defaults_manifest=False)
    runtime.defaults.write_manifest()
    write_examples(repo_root, runtime)
    refresh_packaged_resource_mirror(repo_root)


def ensure_contract_artifacts_current(repo_root: Path) -> None:
    required_paths = (
        repo_root / "docs" / "contracts" / "schemas" / "manifest.json",
        repo_root / "schemas" / "examples" / "manifest.json",
        repo_root / "defaults" / "manifest.json",
    )
    missing_paths = [str(path.relative_to(repo_root)) for path in required_paths if not path.exists()]
    if missing_paths:
        missing_text = ", ".join(sorted(missing_paths))
        raise RuntimeError(
            "Missing generated release artifacts: "
            f"{missing_text}. Run `environmental-fate-mcp-generate-artifacts` before starting the server."
        )

    from fate_mcp.validation import validate_generated_artifacts

    results = validate_generated_artifacts(repo_root)
    invalid = sorted(
        item["name"]
        for section in ("schemas", "examples")
        for item in results[section]
        if item["status"] != "ok"
    )
    if invalid:
        invalid_text = ", ".join(invalid)
        raise RuntimeError(
            "Generated release artifacts are missing or invalid: "
            f"{invalid_text}. Run `environmental-fate-mcp-generate-artifacts` before starting the server."
        )


def main() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    generate_contract_artifacts(repo_root)


if __name__ == "__main__":
    main()
