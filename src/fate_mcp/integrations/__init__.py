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

from .core import apply_physchem_evidence, assess_release_scenario_fit, build_concentration_surface_bundle, build_run_parameter_manifest, build_run_uncertainty_summary, compare_fate_scenarios
from .model_family import build_model_family_challenge_review_brief, build_model_family_challenge_review_packet, build_model_family_challenge_scientific_dossier, build_model_family_challenge_scientific_dossier_brief, build_model_family_comparison_brief, build_model_family_comparison_packet, build_model_family_comparison_review_brief, build_model_family_comparison_review_packet, build_model_family_selection_review_brief, build_model_family_selection_review_packet, preview_model_family_challenge_review, preview_model_family_comparison_review, preview_model_family_selection_review, recommend_model_family_selection
from .probabilistic import build_probabilistic_review_brief, build_probabilistic_review_packet
from .regulatory_handoff import build_regulatory_handoff_review_brief, build_regulatory_handoff_review_packet, export_exposure_consumption_package, export_regulatory_handoff_package, preview_regulatory_handoff_resolution, recommend_regulatory_handoff_profile, summarize_regulatory_handoff_package
from .scientific_methods import build_scientific_methods_dossier, build_scientific_methods_dossier_brief
from .scientific_review import build_scientific_review_brief, build_scientific_review_packet, preview_scientific_review_outcome

__all__ = ['apply_physchem_evidence', 'assess_release_scenario_fit', 'build_concentration_surface_bundle', 'build_model_family_challenge_review_brief', 'build_model_family_challenge_review_packet', 'build_model_family_challenge_scientific_dossier', 'build_model_family_challenge_scientific_dossier_brief', 'build_model_family_comparison_brief', 'build_model_family_comparison_packet', 'build_model_family_comparison_review_brief', 'build_model_family_comparison_review_packet', 'build_model_family_selection_review_brief', 'build_model_family_selection_review_packet', 'build_probabilistic_review_brief', 'build_probabilistic_review_packet', 'build_regulatory_handoff_review_brief', 'build_regulatory_handoff_review_packet', 'build_run_parameter_manifest', 'build_run_uncertainty_summary', 'build_scientific_methods_dossier', 'build_scientific_methods_dossier_brief', 'build_scientific_review_brief', 'build_scientific_review_packet', 'compare_fate_scenarios', 'export_exposure_consumption_package', 'export_regulatory_handoff_package', 'preview_model_family_challenge_review', 'preview_model_family_comparison_review', 'preview_model_family_selection_review', 'preview_regulatory_handoff_resolution', 'preview_scientific_review_outcome', 'recommend_model_family_selection', 'recommend_regulatory_handoff_profile', 'summarize_regulatory_handoff_package']
