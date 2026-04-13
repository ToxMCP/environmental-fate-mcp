from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from fate_mcp.package_metadata import DEFAULTS_VERSION, SCHEMA_VERSION
from fate_mcp.result_meta import ResultMetadata


class FateBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class Media(str, Enum):
    AIR = "air"
    WATER = "water"
    SOIL = "soil"
    SEDIMENT = "sediment"


class Compartment(str, Enum):
    AMBIENT_AIR = "ambient_air"
    SURFACE_WATER = "surface_water"
    AGRICULTURAL_SOIL = "agricultural_soil"
    FRESHWATER_SEDIMENT = "freshwater_sediment"


class RunMode(str, Enum):
    STEADY_STATE = "steady_state"
    TIME_BUCKET = "time_bucket"


class ModelFamily(str, Enum):
    REFERENCE_MASS_BALANCE = "reference_mass_balance"
    ADVECTIVE_SCREENING_MASS_BALANCE = "advective_screening_mass_balance"
    ADAPTER_STUB = "adapter_stub"
    EXTERNAL_RESULT_ADAPTER = "external_result_adapter"


class FitForPurpose(str, Enum):
    SCREENING = "screening"
    DOWNSTREAM_EXPORT = "downstream_export"
    BENCHMARK = "benchmark"


class SourceClassification(str, Enum):
    USER_INPUT = "user_input"
    CURATED_DEFAULT = "curated_default"
    DERIVED = "derived"
    HEURISTIC = "heuristic"


class TreatmentExecutionMode(str, Enum):
    PROVENANCE_ONLY = "provenance_only"
    PRE_RELEASE_GLOBAL = "pre_release_global"


class QualityFlag(FateBaseModel):
    code: str
    severity: Severity
    message: str


class LimitationNote(FateBaseModel):
    code: str
    message: str


class SourceReference(FateBaseModel):
    source_id: str
    title: str
    effective_date: date | None = None
    url: str | None = None


class ProvenanceBundle(FateBaseModel):
    schema_version: str = Field(default=SCHEMA_VERSION)
    defaults_version: str = Field(default=DEFAULTS_VERSION)
    algorithm_version: str
    generated_at: datetime
    source_references: list[SourceReference] = Field(default_factory=list)


class GeographicScope(FateBaseModel):
    region_id: str
    context_label: str
    notes: str | None = None


class FateRegionProfile(FateBaseModel):
    region_id: str
    display_name: str
    compartment_scalars: dict[Compartment, float]
    known_gaps: list[str] = Field(default_factory=list)
    source_pack: str
    applicability_note: str | None = None


class ModelFamilyApplicabilityProfile(FateBaseModel):
    model_family: ModelFamily
    fit_for_purpose: list[FitForPurpose] = Field(default_factory=list)
    supported_substance_classes: list[str] = Field(default_factory=list)
    unsupported_substance_classes: list[str] = Field(default_factory=list)
    required_inputs: list[str] = Field(default_factory=list)
    core_assumptions: list[str] = Field(default_factory=list)
    deferred_capabilities: list[str] = Field(default_factory=list)
    review_notes: list[str] = Field(default_factory=list)
    source_pack: str
    applicability_note: str | None = None


class ScientificValidationClaimPriority(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ScientificClaimSupportStrength(str, Enum):
    UNCOVERED = "uncovered"
    SINGLE_ANCHOR = "single_anchor"
    MULTI_ANCHOR_SINGLE_TIER = "multi_anchor_single_tier"
    MULTI_ANCHOR_MULTI_TIER = "multi_anchor_multi_tier"


class ScientificHighlightedClaimChallengeStatus(str, Enum):
    WELL_SUPPORTED = "well_supported"
    CHALLENGE = "challenge"
    ESCALATE = "escalate"


class ScientificExternalCorroborationStatus(str, Enum):
    NONE = "none"
    SINGLE_OFFICIAL_SOURCE = "single_official_source"
    MULTI_OFFICIAL_SINGLE_JURISDICTION = "multi_official_single_jurisdiction"
    MULTI_OFFICIAL_MULTI_JURISDICTION = "multi_official_multi_jurisdiction"


class ScientificValidationClaim(FateBaseModel):
    claim_id: str
    display_name: str
    model_family: ModelFamily
    supported_run_modes: list[RunMode] = Field(default_factory=list)
    fit_for_purpose: list[FitForPurpose] = Field(default_factory=list)
    statement: str
    claim_class: str
    priority: ScientificValidationClaimPriority = Field(default=ScientificValidationClaimPriority.HIGH)
    mandatory_for_release: bool = True
    required_validation_tiers: list[str] = Field(default_factory=list)
    required_reference_types: list[str] = Field(default_factory=list)
    source_references: list[SourceReference] = Field(default_factory=list)
    reference_case_ids: list[str] = Field(default_factory=list)
    methods_basis_lines: list[str] = Field(default_factory=list)
    reference_case_lines: list[str] = Field(default_factory=list)
    review_notes: list[str] = Field(default_factory=list)
    source_pack: str
    applicability_note: str | None = None


class ScientificValidationClaimManifest(FateBaseModel):
    schema_version: str = Field(default=SCHEMA_VERSION)
    claim_count: int
    mandatory_claim_count: int
    claims: list[ScientificValidationClaim]


class ScientificReferenceCase(FateBaseModel):
    case_id: str
    display_name: str
    model_families: list[ModelFamily] = Field(default_factory=list)
    jurisdictions: list[str] = Field(default_factory=list)
    source_type: str
    summary_lines: list[str] = Field(default_factory=list)
    applicability_lines: list[str] = Field(default_factory=list)
    source_references: list[SourceReference] = Field(default_factory=list)
    review_notes: list[str] = Field(default_factory=list)
    source_pack: str


class ScientificReferenceCaseManifest(FateBaseModel):
    schema_version: str = Field(default=SCHEMA_VERSION)
    case_count: int
    cases: list[ScientificReferenceCase]


class ScientificValidationClaimCoverageRecord(FateBaseModel):
    claim_id: str
    display_name: str
    model_family: ModelFamily
    supported_run_modes: list[RunMode] = Field(default_factory=list)
    priority: ScientificValidationClaimPriority
    mandatory_for_release: bool
    covered: bool
    support_strength: ScientificClaimSupportStrength = Field(
        default=ScientificClaimSupportStrength.UNCOVERED
    )
    supporting_fixture_count: int = 0
    supporting_validation_tier_count: int = 0
    supporting_fixture_names: list[str] = Field(default_factory=list)
    supporting_categories: list[str] = Field(default_factory=list)
    supporting_reference_types: list[str] = Field(default_factory=list)
    supporting_validation_tiers: list[str] = Field(default_factory=list)
    satisfies_required_reference_types: bool = True
    satisfies_required_validation_tiers: bool = True
    gap_lines: list[str] = Field(default_factory=list)


class ScientificValidationClaimCoverageManifest(FateBaseModel):
    schema_version: str = Field(default=SCHEMA_VERSION)
    claim_count: int
    covered_claim_count: int
    mandatory_claim_count: int
    uncovered_mandatory_claim_count: int
    coverage: list[ScientificValidationClaimCoverageRecord]


class ScientificMethodsDossierClaimSummary(FateBaseModel):
    claim_id: str
    display_name: str
    statement: str
    claim_class: str
    priority: ScientificValidationClaimPriority
    mandatory_for_release: bool
    supported_run_modes: list[RunMode] = Field(default_factory=list)
    fit_for_purpose: list[FitForPurpose] = Field(default_factory=list)
    required_validation_tiers: list[str] = Field(default_factory=list)
    required_reference_types: list[str] = Field(default_factory=list)
    covered: bool
    support_strength: ScientificClaimSupportStrength = Field(
        default=ScientificClaimSupportStrength.UNCOVERED
    )
    supporting_fixture_count: int = 0
    reference_case_ids: list[str] = Field(default_factory=list)
    supporting_fixture_names: list[str] = Field(default_factory=list)
    supporting_reference_types: list[str] = Field(default_factory=list)
    supporting_validation_tiers: list[str] = Field(default_factory=list)
    source_references: list[SourceReference] = Field(default_factory=list)
    external_corroboration_status: ScientificExternalCorroborationStatus = Field(
        default=ScientificExternalCorroborationStatus.NONE
    )
    external_corroboration_source_count: int = 0
    external_corroboration_jurisdictions: list[str] = Field(default_factory=list)
    external_corroboration_lines: list[str] = Field(default_factory=list)
    source_grounding_lines: list[str] = Field(default_factory=list)
    methods_basis_lines: list[str] = Field(default_factory=list)
    reference_case_lines: list[str] = Field(default_factory=list)
    reference_case_concept_lines: list[str] = Field(default_factory=list)
    review_notes: list[str] = Field(default_factory=list)
    gap_lines: list[str] = Field(default_factory=list)


class ScientificMethodsHighlightedClaimSummary(FateBaseModel):
    claim_id: str
    display_name: str
    priority: ScientificValidationClaimPriority
    mandatory_for_release: bool
    support_strength: ScientificClaimSupportStrength = Field(
        default=ScientificClaimSupportStrength.UNCOVERED
    )
    challenge_status: ScientificHighlightedClaimChallengeStatus = Field(
        default=ScientificHighlightedClaimChallengeStatus.CHALLENGE
    )
    external_corroboration_status: ScientificExternalCorroborationStatus = Field(
        default=ScientificExternalCorroborationStatus.NONE
    )
    external_corroboration_source_count: int = 0
    external_corroboration_jurisdictions: list[str] = Field(default_factory=list)
    external_corroboration_lines: list[str] = Field(default_factory=list)
    external_corroboration_actions: list[str] = Field(default_factory=list)
    source_grounding_lines: list[str] = Field(default_factory=list)
    reference_case_concept_lines: list[str] = Field(default_factory=list)
    benchmark_anchor_lines: list[str] = Field(default_factory=list)
    loss_regime_stability_status: str = "not_applicable"
    loss_regime_stability_lines: list[str] = Field(default_factory=list)
    transport_regime_stability_status: str = "not_applicable"
    transport_regime_stability_lines: list[str] = Field(default_factory=list)
    challenge_lines: list[str] = Field(default_factory=list)
    review_questions: list[str] = Field(default_factory=list)


class ScientificMethodsRecommendedActionPriority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"


class ScientificMethodsRecommendedActionPromotionImpact(str, Enum):
    BLOCKING = "blocking"
    STRENGTHENING = "strengthening"


class ScientificMethodsPromotionStatus(str, Enum):
    BLOCKED = "blocked"
    STRENGTHENING_ONLY = "strengthening_only"
    READY = "ready"


class ScientificMethodsRecommendedActionSummary(FateBaseModel):
    action: str
    priority: ScientificMethodsRecommendedActionPriority = Field(
        default=ScientificMethodsRecommendedActionPriority.MEDIUM
    )
    promotion_impact: ScientificMethodsRecommendedActionPromotionImpact = Field(
        default=ScientificMethodsRecommendedActionPromotionImpact.STRENGTHENING
    )
    action_class: str
    source_claim_id: str | None = None
    source_claim_display_name: str | None = None


class ScientificMethodsPromotionBlockerSummary(FateBaseModel):
    action: str
    action_class: str
    source_claim_id: str | None = None
    source_claim_display_name: str | None = None


class ScientificMethodsDossier(FateBaseModel):
    schema_version: str = Field(default=SCHEMA_VERSION)
    dossier_id: str = Field(default_factory=lambda: f"scimethods-{uuid4().hex[:12]}")
    model_family: ModelFamily
    run_mode_filter: RunMode | None = None
    promotion_status: ScientificMethodsPromotionStatus = Field(
        default=ScientificMethodsPromotionStatus.READY
    )
    blocking_action_count: int = 0
    strengthening_action_count: int = 0
    claim_count: int
    mandatory_claim_count: int
    covered_mandatory_claim_count: int
    uncovered_mandatory_claim_count: int
    claim_summaries: list[ScientificMethodsDossierClaimSummary]
    highlighted_claim_summaries: list[ScientificMethodsHighlightedClaimSummary] = Field(default_factory=list)
    summary_lines: list[str]
    applicability_lines: list[str] = Field(default_factory=list)
    source_grounding_lines: list[str] = Field(default_factory=list)
    highlighted_claim_grounding_lines: list[str] = Field(default_factory=list)
    reference_case_grounding_lines: list[str] = Field(default_factory=list)
    reference_case_concept_lines: list[str] = Field(default_factory=list)
    benchmark_reference_lines: list[str] = Field(default_factory=list)
    support_strength_lines: list[str] = Field(default_factory=list)
    edge_condition_lines: list[str] = Field(default_factory=list)
    promotion_blocker_claim_ids: list[str] = Field(default_factory=list)
    promotion_blocker_summaries: list[ScientificMethodsPromotionBlockerSummary] = Field(
        default_factory=list
    )
    recommended_action_summaries: list[ScientificMethodsRecommendedActionSummary] = Field(
        default_factory=list
    )
    recommended_actions: list[str] = Field(default_factory=list)
    provenance: ProvenanceBundle
    limitations: list[LimitationNote] = Field(default_factory=list)


class ScientificMethodsDossierBrief(FateBaseModel):
    schema_version: str = Field(default=SCHEMA_VERSION)
    dossier_id: str
    model_family: ModelFamily
    run_mode_filter: RunMode | None = None
    promotion_status: ScientificMethodsPromotionStatus = Field(
        default=ScientificMethodsPromotionStatus.READY
    )
    blocking_action_count: int = 0
    strengthening_action_count: int = 0
    claim_count: int
    mandatory_claim_count: int
    covered_mandatory_claim_count: int
    uncovered_mandatory_claim_count: int
    highlighted_claim_ids: list[str] = Field(default_factory=list)
    highlighted_claim_summaries: list[ScientificMethodsHighlightedClaimSummary] = Field(default_factory=list)
    summary_lines: list[str]
    applicability_lines: list[str] = Field(default_factory=list)
    source_grounding_lines: list[str] = Field(default_factory=list)
    highlighted_claim_grounding_lines: list[str] = Field(default_factory=list)
    reference_case_grounding_lines: list[str] = Field(default_factory=list)
    reference_case_concept_lines: list[str] = Field(default_factory=list)
    benchmark_reference_lines: list[str] = Field(default_factory=list)
    support_strength_lines: list[str] = Field(default_factory=list)
    promotion_blocker_claim_ids: list[str] = Field(default_factory=list)
    promotion_blocker_summaries: list[ScientificMethodsPromotionBlockerSummary] = Field(
        default_factory=list
    )
    recommended_action_summaries: list[ScientificMethodsRecommendedActionSummary] = Field(
        default_factory=list
    )
    recommended_actions: list[str] = Field(default_factory=list)
    limitations: list[LimitationNote] = Field(default_factory=list)


class ModelFamilyComparisonProfile(FateBaseModel):
    profile_id: str
    display_name: str
    base_model_family: ModelFamily
    candidate_model_family: ModelFamily
    fit_for_purpose: list[FitForPurpose] = Field(default_factory=list)
    supported_run_modes: list[RunMode] = Field(default_factory=list)
    material_relative_delta_threshold: float = Field(ge=0.0)
    material_absolute_delta_floor: float = Field(ge=0.0)
    packet_template: str | None = None
    brief_template: str | None = None
    comparable_outcome_template: str | None = None
    divergence_outcome_template: str | None = None
    review_needed_outcome_template: str | None = None
    review_checklist: list["ModelFamilyComparisonReviewChecklistTemplate"] = Field(default_factory=list)
    review_packet_template: str | None = None
    review_brief_template: str | None = None
    ready_comparison_outcomes: list["ModelFamilyComparisonOutcome"] = Field(default_factory=list)
    attention_outcomes: list["ModelFamilyComparisonOutcome"] = Field(default_factory=list)
    attention_if_any_checks_fail: bool = True
    attention_if_candidate_experimental: bool = True
    review_notes: list[str] = Field(default_factory=list)
    source_pack: str
    applicability_note: str | None = None


class ModelFamilyComparisonProfileManifest(FateBaseModel):
    schema_version: str = Field(default=SCHEMA_VERSION)
    profile_count: int
    profiles: list[ModelFamilyComparisonProfile]


class ModelFamilySelectionStatus(str, Enum):
    DEFAULT_BASELINE_ONLY = "default_baseline_only"
    DEFAULT_WITH_EXPERIMENTAL_CHALLENGE = "default_with_experimental_challenge"
    REVIEW_NEEDED = "review_needed"


class ModelFamilySelectionProfile(FateBaseModel):
    profile_id: str
    display_name: str
    fit_for_purpose: list[FitForPurpose] = Field(default_factory=list)
    supported_run_modes: list[RunMode] = Field(default_factory=list)
    default_model_family: ModelFamily
    challenge_model_family: ModelFamily
    comparison_profile_id: str
    minimum_duration_days_for_challenge: float = Field(ge=0.0, default=0.0)
    trigger_parameter_names: list[str] = Field(default_factory=list)
    default_recommendation_template: str | None = None
    challenge_recommendation_template: str | None = None
    review_needed_template: str | None = None
    review_checklist: list["ModelFamilySelectionReviewChecklistTemplate"] = Field(default_factory=list)
    review_packet_template: str | None = None
    review_brief_template: str | None = None
    ready_recommendation_statuses: list["ModelFamilySelectionStatus"] = Field(default_factory=list)
    attention_statuses: list["ModelFamilySelectionStatus"] = Field(default_factory=list)
    attention_if_any_checks_fail: bool = True
    attention_if_challenge_experimental: bool = True
    review_notes: list[str] = Field(default_factory=list)
    source_pack: str
    applicability_note: str | None = None


class ModelFamilySelectionProfileManifest(FateBaseModel):
    schema_version: str = Field(default=SCHEMA_VERSION)
    profile_count: int
    profiles: list[ModelFamilySelectionProfile]


class ModelFamilyChallengeReviewProfile(FateBaseModel):
    profile_id: str
    display_name: str
    selection_profile_id: str
    comparison_profile_id: str | None = None
    fit_for_purpose: list[FitForPurpose] = Field(default_factory=list)
    supported_run_modes: list[RunMode] = Field(default_factory=list)
    review_checklist: list["ModelFamilyChallengeReviewChecklistTemplate"] = Field(default_factory=list)
    review_packet_template: str | None = None
    review_brief_template: str | None = None
    ready_selection_review_statuses: list[str] = Field(default_factory=list)
    ready_comparison_review_statuses: list[str] = Field(default_factory=list)
    attention_if_any_checks_fail: bool = True
    attention_if_comparison_missing_when_challenge_recommended: bool = True
    ready_action_template: str | None = None
    attention_action_template: str | None = None
    review_notes: list[str] = Field(default_factory=list)
    source_pack: str
    applicability_note: str | None = None


class ModelFamilyChallengeReviewProfileManifest(FateBaseModel):
    schema_version: str = Field(default=SCHEMA_VERSION)
    profile_count: int
    profiles: list[ModelFamilyChallengeReviewProfile]


class TimeWindow(FateBaseModel):
    mode: RunMode
    start: datetime | None = None
    end: datetime | None = None
    bucket_label: str | None = None

    @model_validator(mode="after")
    def validate_time_window(self) -> "TimeWindow":
        if self.mode == RunMode.STEADY_STATE and (self.start or self.end):
            raise ValueError("steady_state time windows must not include start/end bounds")
        if self.mode == RunMode.TIME_BUCKET and not (self.start and self.end):
            raise ValueError("time_bucket windows require both start and end")
        if self.mode == RunMode.TIME_BUCKET and self.start and self.end and self.end <= self.start:
            raise ValueError("time_bucket end must be later than start")
        return self


class ReleaseFraction(FateBaseModel):
    medium: Media
    fraction: float = Field(ge=0.0, le=1.0)


class TreatmentAssumption(FateBaseModel):
    description: str
    removal_fraction: float = Field(ge=0.0, le=1.0, default=0.0)
    execution_mode: TreatmentExecutionMode = Field(default=TreatmentExecutionMode.PROVENANCE_ONLY)
    media_scope: list[Media] = Field(default_factory=list)


class FateAssumptionRecord(FateBaseModel):
    parameter: str
    value: float | str
    unit: str | None = None
    source_classification: SourceClassification
    rationale: str
    source_reference: SourceReference | None = None
    quality_flags: list[QualityFlag] = Field(default_factory=list)


class FateParameterRecord(FateBaseModel):
    parameter: str
    value: float
    unit: str
    source_classification: SourceClassification
    source_reference: SourceReference | None = None
    evidence_quality: str | None = None
    rationale: str | None = None
    quality_flags: list[QualityFlag] = Field(default_factory=list)


class FateParameterPolicy(FateBaseModel):
    parameter: str
    family: str | None = None
    expected_unit: str
    runtime_supported: bool
    conflict_relative_spread_threshold: float = Field(ge=0.0)
    weighting_strategy: str
    reconciliation_domain: str = Field(default="linear")
    conflict_metric: str = Field(default="relative_spread")
    disallow_conservative_empirical_blend: bool = False
    source_pack: str
    applicability_note: str | None = None


class FateParameterPolicyFamily(FateBaseModel):
    family: str
    expected_unit: str | None = None
    runtime_supported: bool
    conflict_relative_spread_threshold: float = Field(ge=0.0)
    weighting_strategy: str
    reconciliation_domain: str = Field(default="linear")
    conflict_metric: str = Field(default="relative_spread")
    disallow_conservative_empirical_blend: bool = False
    source_pack: str
    parameter_names: list[str] = Field(default_factory=list)
    applicability_note: str | None = None


class AdapterImportProfile(FateBaseModel):
    profile_id: str
    display_name: str
    accepted_extensions: list[str]
    accepted_modes: list[RunMode]
    internal_only: bool = True
    description: str


class AdapterFixtureDescriptor(FateBaseModel):
    fixture_name: str
    path: str
    import_profile: str
    format: str
    expected_engine_name: str
    supported_modes: list[RunMode]


class AdapterImportManifest(FateBaseModel):
    schema_version: str = Field(default=SCHEMA_VERSION)
    profiles: list[AdapterImportProfile]
    fixtures: list[AdapterFixtureDescriptor]


class AdapterUnitConversionRule(FateBaseModel):
    compartment_code: str
    canonical_unit: str
    canonical_basis: str | None = None
    supported_units: list[str]
    conversion_factors_to_canonical: dict[str, float]
    unit_basis_labels: dict[str, str] = Field(default_factory=dict)
    source_pack: str
    applicability_note: str | None = None


class RegulatoryHandoffReviewChecklistTemplate(FateBaseModel):
    code: str
    prompt: str
    rationale: str
    evidence_hint_fields: list[str] = Field(default_factory=list)


class RegulatoryHandoffProfile(FateBaseModel):
    profile_id: str
    display_name: str
    target_module: str
    downstream_field: str
    required_entry_fields: list[str] = Field(default_factory=list)
    consumer_hints: list[str] = Field(default_factory=list)
    review_checklist: list[RegulatoryHandoffReviewChecklistTemplate] = Field(default_factory=list)
    tool_request_template: str | None = None
    response_summary_template: str | None = None
    review_brief_template: str | None = None
    source_pack: str
    applicability_note: str | None = None


class RegulatoryHandoffProfileRecommendation(FateBaseModel):
    consumer_name: str
    resolved_profile_id: str
    target_module: str
    matched_hint: str
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str
    tool_request_template: str | None = None
    response_summary_template: str | None = None


class RegulatoryHandoffConsumerAlias(FateBaseModel):
    normalized_alias: str
    alias_variants: list[str] = Field(default_factory=list)
    profile_id: str
    target_module: str
    source_pack: str


class RegulatoryHandoffConsumerAliasConflict(FateBaseModel):
    normalized_alias: str
    alias_variants: list[str] = Field(default_factory=list)
    profile_ids: list[str] = Field(default_factory=list)


class RegulatoryHandoffConsumerAliasManifest(FateBaseModel):
    schema_version: str = Field(default=SCHEMA_VERSION)
    alias_count: int
    conflict_count: int
    aliases: list[RegulatoryHandoffConsumerAlias]
    conflicts: list[RegulatoryHandoffConsumerAliasConflict] = Field(default_factory=list)


class RegulatoryHandoffTargetMapping(FateBaseModel):
    profile_id: str
    target_module: str
    consumer_hints: list[str] = Field(default_factory=list)
    source_pack: str


class RegulatoryHandoffTargetMatrixManifest(FateBaseModel):
    schema_version: str = Field(default=SCHEMA_VERSION)
    mapping_count: int
    mappings: list[RegulatoryHandoffTargetMapping]


class RegulatoryHandoffResolutionPreview(FateBaseModel):
    requested_profile_id: str | None = None
    consumer_name: str | None = None
    recommended_profile_id: str | None = None
    resolved_profile_id: str | None = None
    resolution_method: str | None = None
    resolution_basis: str | None = None
    resolution_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    matched_hint: str | None = None
    target_module: str | None = None
    allowed_target_modules: list[str] = Field(default_factory=list)
    target_modules_preview: list[str] = Field(default_factory=list)
    downstream_field: str | None = None
    required_entry_fields: list[str] = Field(default_factory=list)
    status: str
    issues: list[str] = Field(default_factory=list)
    tool_request_template: str | None = None
    response_summary_template: str | None = None


class EnvironmentalReleaseScenario(FateBaseModel):
    schema_version: str = Field(default=SCHEMA_VERSION)
    scenario_id: str = Field(default_factory=lambda: f"scenario-{uuid4().hex[:12]}")
    chemical_identity: dict[str, str]
    total_release_mass_kg: float = Field(gt=0.0)
    release_fractions: list[ReleaseFraction]
    duration_days: float = Field(gt=0.0)
    timing_pattern: str = Field(default="continuous")
    geographic_scope: GeographicScope
    treatment_assumptions: list[TreatmentAssumption] = Field(default_factory=list)
    parameter_records: list[FateParameterRecord] = Field(default_factory=list)
    evidence_sources: list[SourceReference] = Field(default_factory=list)
    provenance: ProvenanceBundle
    quality_flags: list[QualityFlag] = Field(default_factory=list)
    limitations: list[LimitationNote] = Field(default_factory=list)

    @field_validator("release_fractions")
    @classmethod
    def validate_release_fractions(cls, value: list[ReleaseFraction]) -> list[ReleaseFraction]:
        total = round(sum(item.fraction for item in value), 8)
        if total > 1.0:
            raise ValueError("release fractions must sum to 1.0 or less")
        if not value:
            raise ValueError("at least one release fraction is required")
        return value

    @field_validator("parameter_records")
    @classmethod
    def validate_parameter_records(cls, value: list[FateParameterRecord]) -> list[FateParameterRecord]:
        seen = set()
        for record in value:
            if record.parameter in seen:
                raise ValueError("parameter records must be unique by parameter name")
            seen.add(record.parameter)
        return value


class FateModelRunOptions(FateBaseModel):
    schema_version: str = Field(default=SCHEMA_VERSION)
    run_mode: RunMode = Field(default=RunMode.STEADY_STATE)
    model_family: ModelFamily = Field(default=ModelFamily.REFERENCE_MASS_BALANCE)
    region_profile_id: str = Field(default="eu_screening_default")
    fit_for_purpose: FitForPurpose = Field(default=FitForPurpose.SCREENING)
    bucket_count: int = Field(default=1, ge=1, le=24)
    bucket_duration_days: float = Field(default=7.0, gt=0.0)
    requested_media: list[Media] = Field(default_factory=list)


class CalculationTraceTerm(FateBaseModel):
    name: str
    value: float | str
    unit: str | None = None


class CalculationTrace(FateBaseModel):
    equation_id: str
    equation_text: str
    resolved_terms: list[CalculationTraceTerm] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class ConcentrationSurface(FateBaseModel):
    schema_version: str = Field(default=SCHEMA_VERSION)
    surface_id: str = Field(default_factory=lambda: f"surface-{uuid4().hex[:12]}")
    scenario_id: str
    medium: Media
    compartment: Compartment
    geographic_scope: GeographicScope
    time_window: TimeWindow
    concentration_value: float = Field(ge=0.0)
    concentration_unit: str
    model_family: ModelFamily
    fit_for_purpose: FitForPurpose
    provenance: ProvenanceBundle
    calculation_trace: CalculationTrace | None = None
    quality_flags: list[QualityFlag] = Field(default_factory=list)
    limitations: list[LimitationNote] = Field(default_factory=list)


class FateRunSummary(FateBaseModel):
    schema_version: str = Field(default=SCHEMA_VERSION)
    run_id: str = Field(default_factory=lambda: f"run-{uuid4().hex[:12]}")
    scenario_id: str
    model_family: ModelFamily
    run_mode: RunMode
    surfaces_emitted: int
    assumptions_applied: list[FateAssumptionRecord]
    warnings: list[QualityFlag] = Field(default_factory=list)
    result_metadata: ResultMetadata


class ConcentrationEstimationResult(FateBaseModel):
    surfaces: list[ConcentrationSurface]
    run_summary: FateRunSummary
    assumptions: list[FateAssumptionRecord]


class DependencyDescriptor(FateBaseModel):
    name: str
    version: str
    role: str


class ConcentrationSurfaceBundle(FateBaseModel):
    schema_version: str = Field(default=SCHEMA_VERSION)
    bundle_id: str = Field(default_factory=lambda: f"bundle-{uuid4().hex[:12]}")
    scenario_id: str
    surfaces: list[ConcentrationSurface]
    run_summary: FateRunSummary
    assumptions: list[FateAssumptionRecord]
    dependencies: list[DependencyDescriptor]


class SurfaceDelta(FateBaseModel):
    medium: Media
    compartment: Compartment
    base_value: float
    candidate_value: float
    concentration_unit: str
    absolute_delta: float
    relative_delta: float | None = None


class FateScenarioComparisonRecord(FateBaseModel):
    schema_version: str = Field(default=SCHEMA_VERSION)
    comparison_id: str = Field(default_factory=lambda: f"comparison-{uuid4().hex[:12]}")
    base_scenario_id: str
    candidate_scenario_id: str
    surface_deltas: list[SurfaceDelta]
    changed_assumptions: list[str]
    dominant_drivers: list[str]
    provenance: ProvenanceBundle
    limitations: list[LimitationNote] = Field(default_factory=list)
    quality_flags: list[QualityFlag] = Field(default_factory=list)


class ExposureConsumptionPackage(FateBaseModel):
    schema_version: str = Field(default=SCHEMA_VERSION)
    package_id: str = Field(default_factory=lambda: f"package-{uuid4().hex[:12]}")
    scenario_id: str
    surfaces: list[ConcentrationSurface]
    geographic_scope: GeographicScope
    time_semantics: list[TimeWindow]
    provenance: ProvenanceBundle
    limitations: list[LimitationNote] = Field(default_factory=list)


class RegulatoryCrosswalkEntry(FateBaseModel):
    source_surface_id: str
    medium: Media
    compartment: Compartment
    concentration_value: float = Field(ge=0.0)
    concentration_unit: str
    time_window: TimeWindow
    semantic_label: str
    downstream_field: str
    route_hint: str
    equation_id: str | None = None
    equation_text: str | None = None
    requires_dose_translation: bool = True


class RegulatoryHandoffPackage(FateBaseModel):
    schema_version: str = Field(default=SCHEMA_VERSION)
    package_id: str = Field(default_factory=lambda: f"regpkg-{uuid4().hex[:12]}")
    scenario_id: str
    handoff_profile_id: str
    profile_resolution_method: str
    profile_resolution_basis: str | None = None
    profile_resolution_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    source_module: str
    source_model_family: ModelFamily
    target_modules: list[str]
    crosswalk_entries: list[RegulatoryCrosswalkEntry]
    parameter_manifest: RunParameterManifest | None = None
    uncertainty_summary: RunUncertaintySummary | None = None
    provenance: ProvenanceBundle
    limitations: list[LimitationNote] = Field(default_factory=list)


class RegulatoryHandoffEntrySummary(FateBaseModel):
    source_surface_id: str
    medium: Media
    compartment: Compartment
    concentration_value: float = Field(ge=0.0)
    concentration_unit: str
    downstream_field: str
    route_hint: str
    time_window_mode: RunMode
    equation_id: str | None = None
    equation_text: str | None = None


class RegulatoryHandoffPackageSummary(FateBaseModel):
    schema_version: str = Field(default=SCHEMA_VERSION)
    package_id: str
    scenario_id: str
    handoff_profile_id: str
    target_module: str
    entry_count: int
    downstream_field: str
    time_window_modes: list[RunMode]
    route_hints: list[str]
    mediums: list[Media]
    compartments: list[Compartment]
    requires_dose_translation: bool
    summary_template_used: str | None = None
    summary_lines: list[str]
    entry_samples: list[RegulatoryHandoffEntrySummary] = Field(default_factory=list)
    parameter_quality_lines: list[str] = Field(default_factory=list)
    applicability_lines: list[str] = Field(default_factory=list)
    equation_lines: list[str] = Field(default_factory=list)
    limitations: list[LimitationNote] = Field(default_factory=list)


class RegulatoryHandoffReviewCheck(FateBaseModel):
    code: str
    passed: bool
    message: str


class RegulatoryHandoffReviewChecklistItem(FateBaseModel):
    code: str
    prompt: str
    rationale: str
    status: str
    evidence_lines: list[str] = Field(default_factory=list)


class RegulatoryHandoffReviewPacket(FateBaseModel):
    schema_version: str = Field(default=SCHEMA_VERSION)
    review_packet_id: str = Field(default_factory=lambda: f"regreview-{uuid4().hex[:12]}")
    scenario_id: str
    handoff_profile_id: str
    target_module: str
    source_model_family: ModelFamily
    review_status: str
    resolution_preview: RegulatoryHandoffResolutionPreview
    package: RegulatoryHandoffPackage
    summary: RegulatoryHandoffPackageSummary
    checks: list[RegulatoryHandoffReviewCheck]
    review_checklist: list[RegulatoryHandoffReviewChecklistItem] = Field(default_factory=list)
    parameter_quality_lines: list[str] = Field(default_factory=list)
    applicability_lines: list[str] = Field(default_factory=list)
    uncertainty_lines: list[str] = Field(default_factory=list)
    equation_lines: list[str] = Field(default_factory=list)
    review_template_used: str | None = None
    provenance: ProvenanceBundle
    limitations: list[LimitationNote] = Field(default_factory=list)


class RegulatoryHandoffReviewBrief(FateBaseModel):
    schema_version: str = Field(default=SCHEMA_VERSION)
    review_packet_id: str
    scenario_id: str
    handoff_profile_id: str
    target_module: str
    review_status: str
    passed_check_count: int
    total_check_count: int
    review_template_used: str | None = None
    checklist_items: list[RegulatoryHandoffReviewChecklistItem] = Field(default_factory=list)
    brief_lines: list[str]
    parameter_quality_lines: list[str] = Field(default_factory=list)
    applicability_lines: list[str] = Field(default_factory=list)
    uncertainty_lines: list[str] = Field(default_factory=list)
    equation_lines: list[str] = Field(default_factory=list)
    limitations: list[LimitationNote] = Field(default_factory=list)


class ScientificReviewSurfaceSummary(FateBaseModel):
    medium: Media
    compartment: Compartment
    concentration_value: float = Field(ge=0.0)
    concentration_unit: str
    time_window_mode: RunMode
    bucket_label: str | None = None
    equation_id: str | None = None
    equation_text: str | None = None


class ScientificReviewCheck(FateBaseModel):
    code: str
    passed: bool
    message: str


class ScientificReviewChecklistTemplate(FateBaseModel):
    code: str
    prompt: str
    rationale: str
    evidence_hint_fields: list[str] = Field(default_factory=list)


class ScientificReviewChecklistItem(FateBaseModel):
    code: str
    prompt: str
    rationale: str
    status: str
    evidence_lines: list[str] = Field(default_factory=list)


class ScientificReviewOutcome(str, Enum):
    ACCEPTABLE_SCREENING_USE = "acceptable_screening_use"
    QUALIFIED_SCREENING_USE = "qualified_screening_use"
    ESCALATE_MODEL_REVIEW = "escalate_model_review"


class ScientificReviewProfile(FateBaseModel):
    model_family: ModelFamily
    display_name: str
    fit_for_purpose: list[FitForPurpose] = Field(default_factory=list)
    review_checklist: list[ScientificReviewChecklistTemplate] = Field(default_factory=list)
    packet_template: str | None = None
    brief_template: str | None = None
    ready_fit_verdicts: list[str] = Field(default_factory=list)
    attention_outcomes: list[ScientificReviewOutcome] = Field(default_factory=list)
    attention_if_any_checks_fail: bool = True
    escalation_fit_verdicts: list[str] = Field(default_factory=list)
    escalation_driver_types: list[str] = Field(default_factory=list)
    qualification_driver_types: list[str] = Field(default_factory=list)
    warning_severity_promotes_qualification: bool = True
    acceptable_outcome_template: str | None = None
    qualified_outcome_template: str | None = None
    escalation_outcome_template: str | None = None
    driver_action_templates: dict[str, str] = Field(default_factory=dict)
    source_pack: str
    applicability_note: str | None = None


class ScientificReviewProfileManifest(FateBaseModel):
    schema_version: str = Field(default=SCHEMA_VERSION)
    profile_count: int
    profiles: list[ScientificReviewProfile]


class ScientificReviewOutcomePreview(FateBaseModel):
    scenario_id: str
    run_id: str
    model_family: ModelFamily
    fit_for_purpose: FitForPurpose
    review_profile_model_family: ModelFamily
    review_outcome: ScientificReviewOutcome
    review_status: str
    triggered_fit_verdicts: list[str] = Field(default_factory=list)
    triggered_driver_types: list[str] = Field(default_factory=list)
    triggered_check_codes: list[str] = Field(default_factory=list)
    governing_rule_lines: list[str] = Field(default_factory=list)
    status_rule_lines: list[str] = Field(default_factory=list)
    outcome_lines: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)


class ScientificReviewPacket(FateBaseModel):
    schema_version: str = Field(default=SCHEMA_VERSION)
    review_packet_id: str = Field(default_factory=lambda: f"scireview-{uuid4().hex[:12]}")
    scenario_id: str
    run_id: str
    model_family: ModelFamily
    fit_for_purpose: FitForPurpose
    review_status: str
    review_outcome: ScientificReviewOutcome
    outcome_preview: ScientificReviewOutcomePreview
    fit_assessment: ReleaseScenarioFitAssessment
    parameter_manifest: RunParameterManifest
    uncertainty_summary: RunUncertaintySummary
    surface_samples: list[ScientificReviewSurfaceSummary] = Field(default_factory=list)
    summary_lines: list[str]
    outcome_lines: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    benchmark_reference_lines: list[str] = Field(default_factory=list)
    equation_lines: list[str] = Field(default_factory=list)
    equation_component_lines: list[str] = Field(default_factory=list)
    mass_balance_component_lines: list[str] = Field(default_factory=list)
    transport_regime_lines: list[str] = Field(default_factory=list)
    post_release_recovery_lines: list[str] = Field(default_factory=list)
    post_release_regime_lines: list[str] = Field(default_factory=list)
    post_release_directionality_lines: list[str] = Field(default_factory=list)
    loss_dominance_lines: list[str] = Field(default_factory=list)
    loss_transition_lines: list[str] = Field(default_factory=list)
    checks: list[ScientificReviewCheck]
    review_checklist: list[ScientificReviewChecklistItem] = Field(default_factory=list)
    review_template_used: str | None = None
    provenance: ProvenanceBundle
    limitations: list[LimitationNote] = Field(default_factory=list)


class ScientificReviewBrief(FateBaseModel):
    schema_version: str = Field(default=SCHEMA_VERSION)
    review_packet_id: str
    scenario_id: str
    run_id: str
    model_family: ModelFamily
    fit_for_purpose: FitForPurpose
    review_status: str
    review_outcome: ScientificReviewOutcome
    passed_check_count: int
    total_check_count: int
    review_template_used: str | None = None
    checklist_items: list[ScientificReviewChecklistItem] = Field(default_factory=list)
    summary_lines: list[str]
    outcome_lines: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    parameter_quality_lines: list[str] = Field(default_factory=list)
    applicability_lines: list[str] = Field(default_factory=list)
    uncertainty_lines: list[str] = Field(default_factory=list)
    benchmark_reference_lines: list[str] = Field(default_factory=list)
    equation_lines: list[str] = Field(default_factory=list)
    equation_component_lines: list[str] = Field(default_factory=list)
    mass_balance_component_lines: list[str] = Field(default_factory=list)
    transport_regime_lines: list[str] = Field(default_factory=list)
    post_release_recovery_lines: list[str] = Field(default_factory=list)
    post_release_regime_lines: list[str] = Field(default_factory=list)
    post_release_directionality_lines: list[str] = Field(default_factory=list)
    loss_dominance_lines: list[str] = Field(default_factory=list)
    loss_transition_lines: list[str] = Field(default_factory=list)
    limitations: list[LimitationNote] = Field(default_factory=list)


class ModelFamilyComparisonOutcome(str, Enum):
    COMPARABLE_SCREENING_OUTPUTS = "comparable_screening_outputs"
    MATERIAL_MODEL_FAMILY_DIVERGENCE = "material_model_family_divergence"
    REVIEW_NEEDED = "review_needed"


class ModelFamilyComparisonReviewCheck(FateBaseModel):
    code: str
    passed: bool
    message: str


class ModelFamilyComparisonReviewChecklistTemplate(FateBaseModel):
    code: str
    prompt: str
    rationale: str
    evidence_hint_fields: list[str] = Field(default_factory=list)


class ModelFamilyComparisonReviewChecklistItem(FateBaseModel):
    code: str
    prompt: str
    rationale: str
    status: str
    evidence_lines: list[str] = Field(default_factory=list)


class ModelFamilyComparisonReviewPreview(FateBaseModel):
    comparison_packet_id: str
    scenario_id: str
    comparison_profile_id: str
    comparison_outcome: ModelFamilyComparisonOutcome
    review_status: str
    triggered_check_codes: list[str] = Field(default_factory=list)
    governing_rule_lines: list[str] = Field(default_factory=list)
    status_rule_lines: list[str] = Field(default_factory=list)
    outcome_lines: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)


class ModelFamilyComparisonPacket(FateBaseModel):
    schema_version: str = Field(default=SCHEMA_VERSION)
    comparison_packet_id: str = Field(default_factory=lambda: f"familycmp-{uuid4().hex[:12]}")
    scenario_id: str
    run_mode: RunMode
    fit_for_purpose: FitForPurpose
    comparison_profile_id: str
    base_model_family: ModelFamily
    candidate_model_family: ModelFamily
    comparison_outcome: ModelFamilyComparisonOutcome
    base_fit_assessment: ReleaseScenarioFitAssessment
    candidate_fit_assessment: ReleaseScenarioFitAssessment
    comparison: FateScenarioComparisonRecord
    base_surface_samples: list[ScientificReviewSurfaceSummary] = Field(default_factory=list)
    candidate_surface_samples: list[ScientificReviewSurfaceSummary] = Field(default_factory=list)
    summary_lines: list[str]
    dominant_delta_lines: list[str] = Field(default_factory=list)
    outcome_lines: list[str] = Field(default_factory=list)
    base_benchmark_reference_lines: list[str] = Field(default_factory=list)
    candidate_benchmark_reference_lines: list[str] = Field(default_factory=list)
    base_equation_lines: list[str] = Field(default_factory=list)
    candidate_equation_lines: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    packet_template_used: str | None = None
    brief_template_used: str | None = None
    provenance: ProvenanceBundle
    limitations: list[LimitationNote] = Field(default_factory=list)


class ModelFamilyComparisonReviewPacket(FateBaseModel):
    schema_version: str = Field(default=SCHEMA_VERSION)
    review_packet_id: str = Field(default_factory=lambda: f"cmpreview-{uuid4().hex[:12]}")
    comparison_packet_id: str
    scenario_id: str
    comparison_profile_id: str
    base_model_family: ModelFamily
    candidate_model_family: ModelFamily
    comparison_outcome: ModelFamilyComparisonOutcome
    review_status: str
    review_preview: ModelFamilyComparisonReviewPreview
    comparison_packet: ModelFamilyComparisonPacket
    checks: list[ModelFamilyComparisonReviewCheck]
    review_checklist: list[ModelFamilyComparisonReviewChecklistItem] = Field(default_factory=list)
    summary_lines: list[str]
    dominant_delta_lines: list[str] = Field(default_factory=list)
    outcome_lines: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    base_applicability_lines: list[str] = Field(default_factory=list)
    candidate_applicability_lines: list[str] = Field(default_factory=list)
    base_benchmark_reference_lines: list[str] = Field(default_factory=list)
    candidate_benchmark_reference_lines: list[str] = Field(default_factory=list)
    base_equation_lines: list[str] = Field(default_factory=list)
    candidate_equation_lines: list[str] = Field(default_factory=list)
    review_template_used: str | None = None
    provenance: ProvenanceBundle
    limitations: list[LimitationNote] = Field(default_factory=list)


class ModelFamilyComparisonBrief(FateBaseModel):
    schema_version: str = Field(default=SCHEMA_VERSION)
    comparison_packet_id: str
    scenario_id: str
    run_mode: RunMode
    fit_for_purpose: FitForPurpose
    comparison_profile_id: str
    base_model_family: ModelFamily
    candidate_model_family: ModelFamily
    comparison_outcome: ModelFamilyComparisonOutcome
    summary_lines: list[str]
    dominant_delta_lines: list[str] = Field(default_factory=list)
    outcome_lines: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    base_equation_lines: list[str] = Field(default_factory=list)
    candidate_equation_lines: list[str] = Field(default_factory=list)
    brief_template_used: str | None = None
    limitations: list[LimitationNote] = Field(default_factory=list)


class ModelFamilyComparisonReviewBrief(FateBaseModel):
    schema_version: str = Field(default=SCHEMA_VERSION)
    review_packet_id: str
    comparison_packet_id: str
    scenario_id: str
    comparison_profile_id: str
    base_model_family: ModelFamily
    candidate_model_family: ModelFamily
    comparison_outcome: ModelFamilyComparisonOutcome
    review_status: str
    passed_check_count: int
    total_check_count: int
    review_template_used: str | None = None
    checklist_items: list[ModelFamilyComparisonReviewChecklistItem] = Field(default_factory=list)
    brief_lines: list[str]
    dominant_delta_lines: list[str] = Field(default_factory=list)
    outcome_lines: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    base_applicability_lines: list[str] = Field(default_factory=list)
    candidate_applicability_lines: list[str] = Field(default_factory=list)
    base_benchmark_reference_lines: list[str] = Field(default_factory=list)
    candidate_benchmark_reference_lines: list[str] = Field(default_factory=list)
    base_equation_lines: list[str] = Field(default_factory=list)
    candidate_equation_lines: list[str] = Field(default_factory=list)
    limitations: list[LimitationNote] = Field(default_factory=list)


class ModelFamilySelectionReviewCheck(FateBaseModel):
    code: str
    passed: bool
    message: str


class ModelFamilySelectionReviewChecklistTemplate(FateBaseModel):
    code: str
    prompt: str
    rationale: str
    evidence_hint_fields: list[str] = Field(default_factory=list)


class ModelFamilySelectionReviewChecklistItem(FateBaseModel):
    code: str
    prompt: str
    rationale: str
    status: str
    evidence_lines: list[str] = Field(default_factory=list)


class ModelFamilySelectionReviewPreview(FateBaseModel):
    scenario_id: str
    selection_profile_id: str
    recommendation_status: ModelFamilySelectionStatus
    primary_model_family: ModelFamily
    challenge_model_family: ModelFamily | None = None
    review_status: str
    triggered_check_codes: list[str] = Field(default_factory=list)
    governing_rule_lines: list[str] = Field(default_factory=list)
    status_rule_lines: list[str] = Field(default_factory=list)
    triggered_signal_lines: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)


class ModelFamilySelectionReviewPacket(FateBaseModel):
    schema_version: str = Field(default=SCHEMA_VERSION)
    review_packet_id: str = Field(default_factory=lambda: f"selreview-{uuid4().hex[:12]}")
    scenario_id: str
    run_mode: RunMode
    fit_for_purpose: FitForPurpose
    selection_profile_id: str
    recommendation_status: ModelFamilySelectionStatus
    primary_model_family: ModelFamily
    challenge_model_family: ModelFamily | None = None
    review_status: str
    review_preview: ModelFamilySelectionReviewPreview
    selection_recommendation: ModelFamilySelectionRecommendation
    checks: list[ModelFamilySelectionReviewCheck]
    review_checklist: list[ModelFamilySelectionReviewChecklistItem] = Field(default_factory=list)
    summary_lines: list[str]
    triggered_signal_lines: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    primary_applicability_lines: list[str] = Field(default_factory=list)
    challenge_applicability_lines: list[str] = Field(default_factory=list)
    comparison_guidance_lines: list[str] = Field(default_factory=list)
    review_template_used: str | None = None
    provenance: ProvenanceBundle
    limitations: list[LimitationNote] = Field(default_factory=list)


class ModelFamilySelectionReviewBrief(FateBaseModel):
    schema_version: str = Field(default=SCHEMA_VERSION)
    review_packet_id: str
    scenario_id: str
    run_mode: RunMode
    fit_for_purpose: FitForPurpose
    selection_profile_id: str
    recommendation_status: ModelFamilySelectionStatus
    primary_model_family: ModelFamily
    challenge_model_family: ModelFamily | None = None
    review_status: str
    passed_check_count: int
    total_check_count: int
    review_template_used: str | None = None
    checklist_items: list[ModelFamilySelectionReviewChecklistItem] = Field(default_factory=list)
    brief_lines: list[str]
    triggered_signal_lines: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    primary_applicability_lines: list[str] = Field(default_factory=list)
    challenge_applicability_lines: list[str] = Field(default_factory=list)
    comparison_guidance_lines: list[str] = Field(default_factory=list)
    limitations: list[LimitationNote] = Field(default_factory=list)


class ModelFamilyChallengeReviewPacket(FateBaseModel):
    schema_version: str = Field(default=SCHEMA_VERSION)
    review_packet_id: str = Field(default_factory=lambda: f"mfchallenge-{uuid4().hex[:12]}")
    scenario_id: str
    run_mode: RunMode
    fit_for_purpose: FitForPurpose
    selection_profile_id: str
    challenge_review_profile_id: str
    review_status: str
    selection_recommendation_status: ModelFamilySelectionStatus
    selection_review_status: str
    comparison_profile_id: str | None = None
    comparison_outcome: ModelFamilyComparisonOutcome | None = None
    comparison_review_status: str | None = None
    review_preview: ModelFamilyChallengeReviewPreview
    selection_recommendation: ModelFamilySelectionRecommendation
    selection_review_packet: ModelFamilySelectionReviewPacket
    comparison_packet: ModelFamilyComparisonPacket | None = None
    comparison_review_packet: ModelFamilyComparisonReviewPacket | None = None
    checks: list["ModelFamilyChallengeReviewCheck"]
    review_checklist: list["ModelFamilyChallengeReviewChecklistItem"] = Field(default_factory=list)
    summary_lines: list[str]
    governing_rule_lines: list[str] = Field(default_factory=list)
    triggered_signal_lines: list[str] = Field(default_factory=list)
    dominant_delta_lines: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    primary_applicability_lines: list[str] = Field(default_factory=list)
    challenge_applicability_lines: list[str] = Field(default_factory=list)
    comparison_guidance_lines: list[str] = Field(default_factory=list)
    review_template_used: str | None = None
    provenance: ProvenanceBundle
    limitations: list[LimitationNote] = Field(default_factory=list)


class ModelFamilyChallengeReviewBrief(FateBaseModel):
    schema_version: str = Field(default=SCHEMA_VERSION)
    review_packet_id: str
    scenario_id: str
    run_mode: RunMode
    fit_for_purpose: FitForPurpose
    selection_profile_id: str
    challenge_review_profile_id: str
    review_status: str
    selection_recommendation_status: ModelFamilySelectionStatus
    selection_review_status: str
    comparison_profile_id: str | None = None
    comparison_outcome: ModelFamilyComparisonOutcome | None = None
    comparison_review_status: str | None = None
    passed_check_count: int
    total_check_count: int
    review_template_used: str | None = None
    checklist_items: list["ModelFamilyChallengeReviewChecklistItem"] = Field(default_factory=list)
    brief_lines: list[str]
    triggered_signal_lines: list[str] = Field(default_factory=list)
    dominant_delta_lines: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    primary_applicability_lines: list[str] = Field(default_factory=list)
    challenge_applicability_lines: list[str] = Field(default_factory=list)
    comparison_guidance_lines: list[str] = Field(default_factory=list)
    limitations: list[LimitationNote] = Field(default_factory=list)


class ModelFamilyChallengeScientificDossier(FateBaseModel):
    schema_version: str = Field(default=SCHEMA_VERSION)
    dossier_id: str = Field(default_factory=lambda: f"mfscidossier-{uuid4().hex[:12]}")
    scenario_id: str
    run_mode: RunMode
    fit_for_purpose: FitForPurpose
    selection_profile_id: str
    challenge_review_profile_id: str
    primary_model_family: ModelFamily
    challenge_model_family: ModelFamily | None = None
    challenge_review_status: str
    selection_recommendation_status: ModelFamilySelectionStatus
    comparison_profile_id: str | None = None
    comparison_outcome: ModelFamilyComparisonOutcome | None = None
    challenge_review_packet_id: str
    primary_scientific_review_packet_id: str
    challenge_scientific_review_packet_id: str | None = None
    challenge_review_brief: ModelFamilyChallengeReviewBrief
    primary_scientific_review_brief: ScientificReviewBrief
    challenge_scientific_review_brief: ScientificReviewBrief | None = None
    summary_lines: list[str]
    recommended_actions: list[str] = Field(default_factory=list)
    triggered_signal_lines: list[str] = Field(default_factory=list)
    dominant_delta_lines: list[str] = Field(default_factory=list)
    primary_equation_lines: list[str] = Field(default_factory=list)
    challenge_equation_lines: list[str] = Field(default_factory=list)
    primary_benchmark_reference_lines: list[str] = Field(default_factory=list)
    challenge_benchmark_reference_lines: list[str] = Field(default_factory=list)
    provenance: ProvenanceBundle
    limitations: list[LimitationNote] = Field(default_factory=list)


class ModelFamilyChallengeScientificDossierBrief(FateBaseModel):
    schema_version: str = Field(default=SCHEMA_VERSION)
    dossier_id: str
    scenario_id: str
    run_mode: RunMode
    fit_for_purpose: FitForPurpose
    selection_profile_id: str
    challenge_review_profile_id: str
    primary_model_family: ModelFamily
    challenge_model_family: ModelFamily | None = None
    challenge_review_status: str
    selection_recommendation_status: ModelFamilySelectionStatus
    comparison_profile_id: str | None = None
    comparison_outcome: ModelFamilyComparisonOutcome | None = None
    primary_review_outcome: ScientificReviewOutcome
    challenge_review_outcome: ScientificReviewOutcome | None = None
    primary_passed_check_count: int
    primary_total_check_count: int
    challenge_passed_check_count: int | None = None
    challenge_total_check_count: int | None = None
    summary_lines: list[str]
    recommended_actions: list[str] = Field(default_factory=list)
    triggered_signal_lines: list[str] = Field(default_factory=list)
    dominant_delta_lines: list[str] = Field(default_factory=list)
    primary_equation_lines: list[str] = Field(default_factory=list)
    challenge_equation_lines: list[str] = Field(default_factory=list)
    primary_benchmark_reference_lines: list[str] = Field(default_factory=list)
    challenge_benchmark_reference_lines: list[str] = Field(default_factory=list)
    limitations: list[LimitationNote] = Field(default_factory=list)


class ModelFamilyChallengeReviewCheck(FateBaseModel):
    code: str
    passed: bool
    message: str


class ModelFamilyChallengeReviewChecklistTemplate(FateBaseModel):
    code: str
    prompt: str
    rationale: str
    evidence_hint_fields: list[str] = Field(default_factory=list)


class ModelFamilyChallengeReviewChecklistItem(FateBaseModel):
    code: str
    prompt: str
    rationale: str
    status: str
    evidence_lines: list[str] = Field(default_factory=list)


class ModelFamilyChallengeReviewPreview(FateBaseModel):
    scenario_id: str
    selection_profile_id: str
    challenge_review_profile_id: str
    selection_recommendation_status: ModelFamilySelectionStatus
    selection_review_status: str
    comparison_profile_id: str | None = None
    comparison_outcome: ModelFamilyComparisonOutcome | None = None
    comparison_review_status: str | None = None
    review_status: str
    triggered_check_codes: list[str] = Field(default_factory=list)
    triggered_component_statuses: list[str] = Field(default_factory=list)
    governing_rule_lines: list[str] = Field(default_factory=list)
    status_rule_lines: list[str] = Field(default_factory=list)
    triggered_signal_lines: list[str] = Field(default_factory=list)
    dominant_delta_lines: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)


class ModelFamilySelectionRecommendation(FateBaseModel):
    schema_version: str = Field(default=SCHEMA_VERSION)
    scenario_id: str
    run_mode: RunMode
    fit_for_purpose: FitForPurpose
    selection_profile_id: str
    recommendation_status: ModelFamilySelectionStatus
    primary_model_family: ModelFamily
    challenge_model_family: ModelFamily | None = None
    comparison_profile_id: str | None = None
    primary_fit_assessment: ReleaseScenarioFitAssessment
    challenge_fit_assessment: ReleaseScenarioFitAssessment | None = None
    triggered_parameters: list[str] = Field(default_factory=list)
    triggered_signal_lines: list[str] = Field(default_factory=list)
    summary_lines: list[str]
    recommended_actions: list[str] = Field(default_factory=list)
    recommendation_template_used: str | None = None
    provenance: ProvenanceBundle
    limitations: list[LimitationNote] = Field(default_factory=list)


class BuildEnvironmentalReleaseScenarioRequest(FateBaseModel):
    chemical_identity: dict[str, str] = Field(description="Identifiers such as CAS RN or preferred name.")
    total_release_mass_kg: float = Field(gt=0.0)
    release_fractions: list[ReleaseFraction]
    duration_days: float = Field(gt=0.0)
    region_id: str = Field(default="eu_screening_default")
    context_label: str = Field(default="regional_screening")
    timing_pattern: str = Field(default="continuous")
    treatment_assumptions: list[TreatmentAssumption] = Field(default_factory=list)
    parameter_records: list[FateParameterRecord] = Field(default_factory=list)
    evidence_sources: list[SourceReference] = Field(default_factory=list)


class EstimateMultimediaConcentrationsRequest(FateBaseModel):
    scenario: EnvironmentalReleaseScenario
    run_options: FateModelRunOptions


class BuildConcentrationSurfaceBundleRequest(FateBaseModel):
    result: ConcentrationEstimationResult


class CompareFateScenariosRequest(FateBaseModel):
    base_result: ConcentrationEstimationResult
    candidate_result: ConcentrationEstimationResult


class PhyschemEvidenceRecord(FateBaseModel):
    parameter: str
    value: float
    unit: str
    source_reference: SourceReference
    evidence_quality: str = Field(default="reference")


class PhyschemEvidenceObservation(FateBaseModel):
    parameter: str
    value: float
    unit: str
    source_reference: SourceReference
    evidence_quality: str
    evidence_weight: float


class ReconciledPhyschemParameter(FateBaseModel):
    parameter: str
    reconciled_value: float
    unit: str
    weighting_strategy: str
    reconciliation_domain: str = Field(default="linear")
    conflict_metric: str = Field(default="relative_spread")
    total_weight: float
    min_value: float
    max_value: float
    relative_spread: float
    status: str
    contributing_sources: list[str]


class PhyschemEvidenceConflict(FateBaseModel):
    parameter: str
    conflict_type: str
    description: str
    observed_values: list[str]
    contributing_sources: list[str]


class ApplyPhyschemEvidenceRequest(FateBaseModel):
    scenario: EnvironmentalReleaseScenario
    evidence: list[PhyschemEvidenceRecord]


class PhyschemEvidenceApplicationResult(FateBaseModel):
    scenario: EnvironmentalReleaseScenario
    evidence_observations: list[PhyschemEvidenceObservation]
    reconciled_parameters: list[ReconciledPhyschemParameter]
    conflicts: list[PhyschemEvidenceConflict]
    unresolved_conflict_count: int
    quality_flags: list[QualityFlag] = Field(default_factory=list)
    applied_assumptions: list[FateAssumptionRecord]
    notes: list[str]


class AssessReleaseScenarioFitRequest(FateBaseModel):
    scenario: EnvironmentalReleaseScenario
    run_options: FateModelRunOptions


class ReleaseScenarioFitAssessment(FateBaseModel):
    fit_score: float = Field(ge=0.0, le=1.0)
    model_family: ModelFamily
    fit_for_purpose: FitForPurpose
    verdict: str
    reasons: list[str]
    applicability_profile: ModelFamilyApplicabilityProfile
    applicability_lines: list[str] = Field(default_factory=list)


class RunParameterManifestEntry(FateBaseModel):
    parameter: str
    resolved_value: float | str
    unit: str | None = None
    source_classification: SourceClassification
    evidence_quality: str | None = None
    runtime_consumed: bool
    source_reference_ids: list[str] = Field(default_factory=list)
    quality_flag_codes: list[str] = Field(default_factory=list)
    rationale: str


class RunParameterManifest(FateBaseModel):
    schema_version: str = Field(default=SCHEMA_VERSION)
    scenario_id: str
    run_id: str
    model_family: ModelFamily
    fit_for_purpose: FitForPurpose
    entries: list[RunParameterManifestEntry]
    summary_lines: list[str]
    limitations: list[LimitationNote] = Field(default_factory=list)
    provenance: ProvenanceBundle


class UncertaintyDriver(FateBaseModel):
    parameter: str
    driver_type: str
    reason: str
    severity: Severity
    source_reference_ids: list[str] = Field(default_factory=list)
    quality_flag_codes: list[str] = Field(default_factory=list)


class RunUncertaintySummary(FateBaseModel):
    schema_version: str = Field(default=SCHEMA_VERSION)
    scenario_id: str
    run_id: str
    model_family: ModelFamily
    top_drivers: list[UncertaintyDriver]
    summary_lines: list[str]
    limitations: list[LimitationNote] = Field(default_factory=list)
    provenance: ProvenanceBundle


class ReleaseEvidenceInput(FateBaseModel):
    label: str
    total_release_mass_kg: float = Field(gt=0.0)
    release_fractions: list[ReleaseFraction]
    source_reference: SourceReference
    evidence_quality: str = Field(default="reference")

    @field_validator("release_fractions")
    @classmethod
    def validate_release_fractions(cls, value: list[ReleaseFraction]) -> list[ReleaseFraction]:
        total = round(sum(item.fraction for item in value), 8)
        if total > 1.0:
            raise ValueError("release fractions must sum to 1.0 or less")
        if not value:
            raise ValueError("at least one release fraction is required")
        return value


class ReleaseEvidenceObservation(FateBaseModel):
    label: str
    source_reference: SourceReference
    evidence_quality: str
    evidence_weight: float
    total_release_mass_kg: float
    release_fractions: list[ReleaseFraction]


class ReconciledScalarValue(FateBaseModel):
    field: str
    reconciled_value: float
    unit: str
    weighting_strategy: str
    total_weight: float
    min_value: float
    max_value: float
    relative_spread: float
    status: str
    contributing_labels: list[str]


class ReconciledReleaseFraction(FateBaseModel):
    medium: Media
    reconciled_fraction: float
    weighting_strategy: str
    total_weight: float
    min_fraction: float
    max_fraction: float
    absolute_spread: float
    status: str
    contributing_labels: list[str]


class ReleaseEvidenceConflict(FateBaseModel):
    field: str
    conflict_type: str
    description: str
    observed_values: list[str]
    contributing_labels: list[str]


class ReleaseVectorConflict(FateBaseModel):
    labels: list[str]
    cosine_similarity: float = Field(ge=-1.0, le=1.0)
    threshold: float = Field(ge=0.0, le=1.0)
    description: str
    observed_vectors: list[str]


class ReconcileReleaseEvidenceRequest(FateBaseModel):
    chemical_identity: dict[str, str]
    region_id: str = Field(default="eu_screening_default")
    context_label: str = Field(default="regional_screening")
    duration_days: float = Field(gt=0.0, default=30.0)
    evidence_inputs: list[ReleaseEvidenceInput]

    @field_validator("evidence_inputs")
    @classmethod
    def validate_evidence_inputs(cls, value: list[ReleaseEvidenceInput]) -> list[ReleaseEvidenceInput]:
        if not value:
            raise ValueError("at least one evidence input is required")
        return value


class ReleaseEvidenceReconciliationResult(FateBaseModel):
    schema_version: str = Field(default=SCHEMA_VERSION)
    reconciled_scenario: EnvironmentalReleaseScenario | None = None
    evidence_observations: list[ReleaseEvidenceObservation]
    reconciled_scalars: list[ReconciledScalarValue]
    reconciled_release_fractions: list[ReconciledReleaseFraction]
    agreed_values: dict[str, Any]
    conflicts: list[ReleaseEvidenceConflict]
    vector_conflicts: list[ReleaseVectorConflict] = Field(default_factory=list)
    unresolved_conflict_count: int
    recommended_next_actions: list[str]
    provenance: ProvenanceBundle
    quality_flags: list[QualityFlag] = Field(default_factory=list)
    limitations: list[LimitationNote] = Field(default_factory=list)


class ExportConcentrationSurfaceBundleRequest(FateBaseModel):
    bundle: ConcentrationSurfaceBundle


class ExportExposureConsumptionPackageRequest(FateBaseModel):
    result: ConcentrationEstimationResult


class ExportRegulatoryHandoffPackageRequest(FateBaseModel):
    result: ConcentrationEstimationResult
    scenario: EnvironmentalReleaseScenario | None = None
    handoff_profile_id: str | None = None
    consumer_name: str | None = None
    target_modules: list[str] = Field(default_factory=list)

    @field_validator("target_modules")
    @classmethod
    def validate_target_modules(cls, value: list[str]) -> list[str]:
        return value


class RecommendRegulatoryHandoffProfileRequest(FateBaseModel):
    consumer_name: str


class PreviewRegulatoryHandoffResolutionRequest(FateBaseModel):
    handoff_profile_id: str | None = None
    consumer_name: str | None = None
    target_modules: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_selection_inputs(self) -> "PreviewRegulatoryHandoffResolutionRequest":
        if not self.handoff_profile_id and not self.consumer_name:
            raise ValueError("at least one of handoff_profile_id or consumer_name is required")
        return self


class SummarizeRegulatoryHandoffPackageRequest(FateBaseModel):
    package: RegulatoryHandoffPackage
    max_entry_samples: int = Field(default=3, ge=1, le=10)


class BuildRunParameterManifestRequest(FateBaseModel):
    scenario: EnvironmentalReleaseScenario
    result: ConcentrationEstimationResult


class BuildRunUncertaintySummaryRequest(FateBaseModel):
    scenario: EnvironmentalReleaseScenario
    result: ConcentrationEstimationResult


class BuildScientificReviewPacketRequest(FateBaseModel):
    scenario: EnvironmentalReleaseScenario
    result: ConcentrationEstimationResult
    max_surface_samples: int = Field(default=4, ge=1, le=12)


class PreviewScientificReviewOutcomeRequest(FateBaseModel):
    scenario: EnvironmentalReleaseScenario
    result: ConcentrationEstimationResult


class BuildScientificReviewBriefRequest(FateBaseModel):
    review_packet: ScientificReviewPacket


class BuildScientificMethodsDossierRequest(FateBaseModel):
    model_family: ModelFamily
    run_mode_filter: RunMode | None = None


class BuildScientificMethodsDossierBriefRequest(FateBaseModel):
    dossier: ScientificMethodsDossier


class RecommendModelFamilySelectionRequest(FateBaseModel):
    scenario: EnvironmentalReleaseScenario
    run_mode: RunMode = Field(default=RunMode.STEADY_STATE)
    fit_for_purpose: FitForPurpose = Field(default=FitForPurpose.SCREENING)
    selection_profile_id: str | None = None


class BuildModelFamilyComparisonPacketRequest(FateBaseModel):
    scenario: EnvironmentalReleaseScenario
    run_mode: RunMode = Field(default=RunMode.STEADY_STATE)
    fit_for_purpose: FitForPurpose = Field(default=FitForPurpose.SCREENING)
    comparison_profile_id: str | None = None
    base_model_family: ModelFamily = Field(default=ModelFamily.REFERENCE_MASS_BALANCE)
    candidate_model_family: ModelFamily = Field(default=ModelFamily.ADVECTIVE_SCREENING_MASS_BALANCE)
    bucket_count: int = Field(default=1, ge=1, le=24)
    bucket_duration_days: float = Field(default=7.0, gt=0.0)
    requested_media: list[Media] = Field(default_factory=list)
    max_surface_samples: int = Field(default=4, ge=1, le=12)

    @model_validator(mode="after")
    def validate_model_family_pair(self) -> "BuildModelFamilyComparisonPacketRequest":
        if self.base_model_family == self.candidate_model_family:
            raise ValueError("base_model_family and candidate_model_family must differ")
        return self


class BuildModelFamilyComparisonBriefRequest(FateBaseModel):
    comparison_packet: ModelFamilyComparisonPacket


class PreviewModelFamilyComparisonReviewRequest(FateBaseModel):
    comparison_packet: ModelFamilyComparisonPacket


class BuildModelFamilyComparisonReviewPacketRequest(FateBaseModel):
    comparison_packet: ModelFamilyComparisonPacket


class BuildModelFamilyComparisonReviewBriefRequest(FateBaseModel):
    review_packet: ModelFamilyComparisonReviewPacket


class PreviewModelFamilySelectionReviewRequest(FateBaseModel):
    selection_recommendation: ModelFamilySelectionRecommendation


class BuildModelFamilySelectionReviewPacketRequest(FateBaseModel):
    selection_recommendation: ModelFamilySelectionRecommendation


class BuildModelFamilySelectionReviewBriefRequest(FateBaseModel):
    review_packet: ModelFamilySelectionReviewPacket


class PreviewModelFamilyChallengeReviewRequest(FateBaseModel):
    scenario: EnvironmentalReleaseScenario
    selection_profile_id: str | None = None
    run_mode: RunMode = RunMode.STEADY_STATE
    fit_for_purpose: FitForPurpose = FitForPurpose.SCREENING
    bucket_count: int = Field(default=4, ge=1, le=24)
    bucket_duration_days: float = Field(default=7.0, gt=0.0, le=365.0)
    requested_media: list[Media] = Field(default_factory=list)
    max_surface_samples: int = Field(default=3, ge=1, le=10)


class BuildModelFamilyChallengeReviewPacketRequest(FateBaseModel):
    scenario: EnvironmentalReleaseScenario
    selection_profile_id: str | None = None
    run_mode: RunMode = RunMode.STEADY_STATE
    fit_for_purpose: FitForPurpose = FitForPurpose.SCREENING
    bucket_count: int = Field(default=4, ge=1, le=24)
    bucket_duration_days: float = Field(default=7.0, gt=0.0, le=365.0)
    requested_media: list[Media] = Field(default_factory=list)
    max_surface_samples: int = Field(default=3, ge=1, le=10)


class BuildModelFamilyChallengeReviewBriefRequest(FateBaseModel):
    review_packet: ModelFamilyChallengeReviewPacket


class BuildModelFamilyChallengeScientificDossierRequest(FateBaseModel):
    scenario: EnvironmentalReleaseScenario
    selection_profile_id: str | None = None
    run_mode: RunMode = RunMode.STEADY_STATE
    fit_for_purpose: FitForPurpose = FitForPurpose.SCREENING
    bucket_count: int = Field(default=4, ge=1, le=24)
    bucket_duration_days: float = Field(default=7.0, gt=0.0, le=365.0)
    requested_media: list[Media] = Field(default_factory=list)
    max_surface_samples: int = Field(default=3, ge=1, le=10)


class BuildModelFamilyChallengeScientificDossierBriefRequest(FateBaseModel):
    dossier: ModelFamilyChallengeScientificDossier


class BuildRegulatoryHandoffReviewPacketRequest(FateBaseModel):
    result: ConcentrationEstimationResult
    scenario: EnvironmentalReleaseScenario | None = None
    handoff_profile_id: str | None = None
    consumer_name: str | None = None
    target_modules: list[str] = Field(default_factory=list)
    max_entry_samples: int = Field(default=3, ge=1, le=10)


class BuildRegulatoryHandoffReviewBriefRequest(FateBaseModel):
    review_packet: RegulatoryHandoffReviewPacket
