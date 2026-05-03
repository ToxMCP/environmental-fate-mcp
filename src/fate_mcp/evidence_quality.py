from __future__ import annotations

from collections import Counter
from pathlib import Path

from fate_mcp.benchmarks import scientific_validation_claim_coverage_manifest
from fate_mcp.defaults import DefaultsRegistry
from fate_mcp.models import (
    ModelFamily,
    ScientificBenchmarkCaseClassification,
    ScientificClaimSupportStrength,
    ScientificEvidenceQualityMatrixClaimRow,
    ScientificEvidenceQualityMatrixModelFamilyRow,
    ScientificEvidenceQualityMatrixReport,
    ScientificEvidenceTrustTier,
    ScientificExternalCorroborationStatus,
    ScientificValidationClaim,
    ScientificValidationClaimCoverageRecord,
    ScientificValidationClaimPriority,
)
from fate_mcp.package_metadata import (
    DEFAULTS_VERSION,
    EXPERIMENTAL_MODEL_FAMILIES,
    SUPPORTED_MODEL_FAMILIES,
    VERSION,
)


def _benchmark_classifications_by_family(
    registry: DefaultsRegistry,
) -> dict[ModelFamily, set[ScientificBenchmarkCaseClassification]]:
    by_family: dict[ModelFamily, set[ScientificBenchmarkCaseClassification]] = {}
    for case in registry.scientific_external_benchmark_pack_manifest().cases:
        if case.model_family is None:
            continue
        by_family.setdefault(case.model_family, set()).add(case.classification)
    return by_family


def _fallback_action_for_tier(registry: DefaultsRegistry) -> dict[ScientificEvidenceTrustTier, str]:
    rubric = registry.scientific_evidence_quality_rubric_manifest()
    return {tier.tier: tier.next_action_template for tier in rubric.tiers}


def _claim_trust_tier(
    claim: ScientificValidationClaim,
    coverage: ScientificValidationClaimCoverageRecord,
) -> ScientificEvidenceTrustTier:
    if not coverage.covered:
        return ScientificEvidenceTrustTier.DEFERRED_OR_GAP
    if any("synthetic" in item for item in coverage.supporting_validation_tiers):
        return ScientificEvidenceTrustTier.SYNTHETIC_DEMO_ONLY
    if claim.model_family == ModelFamily.EXTERNAL_RESULT_ADAPTER:
        return ScientificEvidenceTrustTier.INTERNAL_ORACLE_SCREENING
    if (
        claim.model_family == ModelFamily.REFERENCE_MASS_BALANCE
        and claim.mandatory_for_release
        and coverage.support_strength == ScientificClaimSupportStrength.MULTI_ANCHOR_MULTI_TIER
        and claim.official_source_count >= 2
        and claim.corroboration_status
        == ScientificExternalCorroborationStatus.MULTI_OFFICIAL_MULTI_JURISDICTION
    ):
        return ScientificEvidenceTrustTier.REVIEWER_GRADE_SCREENING
    if claim.source_references or claim.official_source_count > 0:
        return ScientificEvidenceTrustTier.SOURCE_GROUNDED_SCREENING
    if coverage.supporting_fixture_count > 0:
        return ScientificEvidenceTrustTier.INTERNAL_ORACLE_SCREENING
    return ScientificEvidenceTrustTier.DEFERRED_OR_GAP


def _claim_limitations(
    claim: ScientificValidationClaim,
    coverage: ScientificValidationClaimCoverageRecord,
) -> list[str]:
    limitations = [
        "Evidence tier is for bounded screening release review only; it is not regulator acceptance, field validation, calibration evidence, or final risk assessment.",
    ]
    if claim.model_family == ModelFamily.ADVECTIVE_SCREENING_MASS_BALANCE:
        limitations.append(
            "Advective screening remains experimental and non-default; it is not routed hydrology, catchment validation, or calibrated transport."
        )
    elif claim.model_family == ModelFamily.FUGACITY_EQUILIBRIUM_SCREENING:
        limitations.append(
            "Fugacity equilibrium screening remains experimental Level I/II-style partitioning; it is not Level III intermedia-transfer, routing, calibration, or field validation."
        )
    elif claim.model_family == ModelFamily.EXTERNAL_RESULT_ADAPTER:
        limitations.append(
            "External-result adapter evidence covers normalization parity only; it does not validate the upstream source engine or claim scientific equivalence."
        )
    elif claim.model_family == ModelFamily.REFERENCE_MASS_BALANCE:
        limitations.append(
            "Reference mass-balance evidence supports the reviewer-grade bounded-screening anchor, not full multimedia fate realism or site-specific adequacy."
        )
    limitations.extend(coverage.gap_lines)
    return limitations


def _claim_row(
    claim: ScientificValidationClaim,
    coverage: ScientificValidationClaimCoverageRecord,
    classifications_by_family: dict[ModelFamily, set[ScientificBenchmarkCaseClassification]],
    fallback_actions: dict[ScientificEvidenceTrustTier, str],
) -> ScientificEvidenceQualityMatrixClaimRow:
    tier = _claim_trust_tier(claim, coverage)
    classifications = set(classifications_by_family.get(claim.model_family, set()))
    if coverage.supporting_fixture_count:
        classifications.add(ScientificBenchmarkCaseClassification.INTERNAL_ORACLE)
    return ScientificEvidenceQualityMatrixClaimRow(
        row_id=f"claim:{claim.claim_id}",
        claim_id=claim.claim_id,
        display_name=claim.display_name,
        model_family=claim.model_family,
        priority=claim.priority,
        mandatory_for_release=claim.mandatory_for_release,
        trust_tier=tier,
        covered=coverage.covered,
        support_strength=coverage.support_strength,
        supporting_validation_tiers=coverage.supporting_validation_tiers,
        supporting_reference_types=coverage.supporting_reference_types,
        supporting_fixture_names=coverage.supporting_fixture_names,
        benchmark_classifications=sorted(classifications, key=lambda item: item.value),
        official_source_count=claim.official_source_count,
        jurisdiction_breadth=claim.jurisdiction_breadth,
        corroboration_status=claim.corroboration_status,
        limitations=_claim_limitations(claim, coverage),
        next_corroboration_action=(
            claim.next_corroboration_action
            or fallback_actions.get(tier)
            or "Add governed evidence before increasing trust tier."
        ),
    )


def _model_family_trust_tier(
    family: ModelFamily,
    claim_rows: list[ScientificEvidenceQualityMatrixClaimRow],
    supported: bool,
    experimental: bool,
) -> ScientificEvidenceTrustTier:
    if not claim_rows:
        return ScientificEvidenceTrustTier.DEFERRED_OR_GAP
    row_tiers = {row.trust_tier for row in claim_rows}
    if family == ModelFamily.REFERENCE_MASS_BALANCE and row_tiers == {
        ScientificEvidenceTrustTier.REVIEWER_GRADE_SCREENING
    }:
        return ScientificEvidenceTrustTier.REVIEWER_GRADE_SCREENING
    if experimental and ScientificEvidenceTrustTier.SOURCE_GROUNDED_SCREENING in row_tiers:
        return ScientificEvidenceTrustTier.SOURCE_GROUNDED_SCREENING
    if supported and row_tiers == {ScientificEvidenceTrustTier.INTERNAL_ORACLE_SCREENING}:
        return ScientificEvidenceTrustTier.INTERNAL_ORACLE_SCREENING
    if ScientificEvidenceTrustTier.DEFERRED_OR_GAP in row_tiers:
        return ScientificEvidenceTrustTier.DEFERRED_OR_GAP
    if ScientificEvidenceTrustTier.SOURCE_GROUNDED_SCREENING in row_tiers:
        return ScientificEvidenceTrustTier.SOURCE_GROUNDED_SCREENING
    return sorted(row_tiers, key=lambda item: item.value)[0]


def _model_family_limitations(
    family: ModelFamily,
    claim_rows: list[ScientificEvidenceQualityMatrixClaimRow],
) -> list[str]:
    limitations = [
        "Family-level trust tier summarizes release evidence posture only; it is not field validation, calibration adequacy, regulator acceptance, source-engine equivalence, or final risk suitability."
    ]
    if family == ModelFamily.ADAPTER_STUB:
        limitations.append(
            "Adapter stub is a supported interface boundary with no native scientific claim row; use external_result_adapter for governed import normalization."
        )
    elif family == ModelFamily.EXTERNAL_RESULT_ADAPTER:
        limitations.append(
            "External-result adapter remains a normalization-parity lane and does not verify upstream engine calculations."
        )
    elif family == ModelFamily.ADVECTIVE_SCREENING_MASS_BALANCE:
        limitations.append(
            "Advective family remains experimental and non-default until independent review justifies promotion."
        )
    elif family == ModelFamily.FUGACITY_EQUILIBRIUM_SCREENING:
        limitations.append(
            "Fugacity family remains experimental Level I/II equilibrium screening and does not implement Level III transfer."
        )
    elif family == ModelFamily.REFERENCE_MASS_BALANCE:
        limitations.append(
            "Reference family is the reviewer-grade bounded-screening anchor but remains a simplified screening kernel."
        )
    for row in claim_rows:
        for limitation in row.limitations:
            if limitation not in limitations:
                limitations.append(limitation)
    return limitations


def _proof_posture(family: ModelFamily, supported: bool, experimental: bool) -> str:
    if family == ModelFamily.REFERENCE_MASS_BALANCE:
        return "reviewer_grade_reference_anchor"
    if family == ModelFamily.EXTERNAL_RESULT_ADAPTER:
        return "normalization_parity_lane"
    if family == ModelFamily.ADAPTER_STUB:
        return "deferred_adapter_stub_boundary"
    if experimental:
        return "experimental_challenge_path"
    if supported:
        return "supported_screening_lane"
    return "undocumented_family_gap"


def _model_family_row(
    family: ModelFamily,
    claim_rows: list[ScientificEvidenceQualityMatrixClaimRow],
    fallback_actions: dict[ScientificEvidenceTrustTier, str],
) -> ScientificEvidenceQualityMatrixModelFamilyRow:
    supported = family.value in SUPPORTED_MODEL_FAMILIES
    experimental = family.value in EXPERIMENTAL_MODEL_FAMILIES
    tier = _model_family_trust_tier(family, claim_rows, supported, experimental)
    high_or_medium_count = sum(
        1
        for row in claim_rows
        if row.priority
        in {ScientificValidationClaimPriority.HIGH, ScientificValidationClaimPriority.MEDIUM}
    )
    next_actions = [row.next_corroboration_action for row in claim_rows]
    return ScientificEvidenceQualityMatrixModelFamilyRow(
        row_id=f"model_family:{family.value}",
        model_family=family,
        proof_posture=_proof_posture(family, supported, experimental),
        trust_tier=tier,
        claim_count=len(claim_rows),
        high_or_medium_claim_count=high_or_medium_count,
        supported=supported,
        experimental=experimental,
        limitations=_model_family_limitations(family, claim_rows),
        next_corroboration_action=(
            next_actions[0]
            if next_actions
            else fallback_actions.get(tier, "Add governed claim evidence before use.")
        ),
    )


def build_scientific_evidence_quality_matrix_report(
    repo_root: Path,
) -> ScientificEvidenceQualityMatrixReport:
    registry = DefaultsRegistry(repo_root)
    rubric = registry.scientific_evidence_quality_rubric_manifest()
    claims = registry.list_scientific_validation_claims()
    coverage_by_claim_id = {
        record.claim_id: record
        for record in scientific_validation_claim_coverage_manifest(repo_root).coverage
    }
    fallback_actions = _fallback_action_for_tier(registry)
    classifications_by_family = _benchmark_classifications_by_family(registry)
    claim_rows = [
        _claim_row(
            claim,
            coverage_by_claim_id[claim.claim_id],
            classifications_by_family,
            fallback_actions,
        )
        for claim in claims
    ]
    families = sorted(
        {
            *(ModelFamily(family) for family in SUPPORTED_MODEL_FAMILIES),
            *(ModelFamily(family) for family in EXPERIMENTAL_MODEL_FAMILIES),
            *(row.model_family for row in claim_rows),
        },
        key=lambda item: item.value,
    )
    rows_by_family = {
        family: [row for row in claim_rows if row.model_family == family]
        for family in families
    }
    model_family_rows = [
        _model_family_row(family, rows_by_family[family], fallback_actions)
        for family in families
    ]
    all_rows = [*claim_rows, *model_family_rows]
    tier_counts = Counter(row.trust_tier for row in all_rows)
    unsupported_claims = [
        row.row_id
        for row in all_rows
        if row.field_validation_present
        or row.calibration_claim_present
        or row.regulatory_acceptance_claim_present
        or row.source_engine_equivalence_claim_present
    ]
    experimental_reviewer_rows = [
        row.row_id
        for row in all_rows
        if getattr(row, "experimental", False)
        and row.trust_tier == ScientificEvidenceTrustTier.REVIEWER_GRADE_SCREENING
    ]
    mandatory_uncovered_rows = [
        row.row_id for row in claim_rows if row.mandatory_for_release and not row.covered
    ]
    passed = (
        len(claim_rows) == len(claims)
        and not unsupported_claims
        and not experimental_reviewer_rows
        and not mandatory_uncovered_rows
        and all(row.limitations and row.next_corroboration_action for row in all_rows)
    )
    return ScientificEvidenceQualityMatrixReport(
        release_version=VERSION,
        defaults_version=DEFAULTS_VERSION,
        rubric_version=rubric.rubric_version,
        claim_row_count=len(claim_rows),
        model_family_row_count=len(model_family_rows),
        claim_rows=claim_rows,
        model_family_rows=model_family_rows,
        trust_tier_counts=dict(sorted(tier_counts.items(), key=lambda item: item[0].value)),
        passed=passed,
        limitations=[
            "Evidence-quality tiers summarize release-review confidence for bounded screening only.",
            "The matrix deliberately preserves unsupported/deferred rows instead of hiding them.",
            "No row is allowed to imply field validation, calibration adequacy, regulatory acceptance, or source-engine equivalence without a future governed evidence tranche.",
        ],
        summary_lines=[
            f"Matrix covers {len(claim_rows)} governed scientific validation claims.",
            f"Matrix covers {len(model_family_rows)} model-family posture rows, including supported and experimental families.",
            "Experimental families remain non-default and below reviewer-grade promotion in this report.",
            "Deferred rows are accepted only when boundary language and next actions are explicit.",
        ],
    )
