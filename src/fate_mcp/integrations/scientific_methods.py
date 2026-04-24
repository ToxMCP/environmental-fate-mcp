from __future__ import annotations


from fate_mcp.models import (
    BuildScientificMethodsDossierBriefRequest,
    BuildScientificMethodsDossierRequest,
    LimitationNote,
    ScientificMethodsDossier,
    ScientificMethodsDossierBrief,
    ScientificExternalCorroborationStatus,
)
from fate_mcp.package_metadata import EXPERIMENTAL_MODEL_FAMILIES
from fate_mcp.provenance import ProvenanceBuilder

from .common import _advective_post_release_directionality_support_ready, _advective_post_release_late_recovery_support_ready, _advective_post_release_pace_directionality_support_ready, _advective_post_release_pace_support_ready, _advective_post_release_recovery_support_ready, _advective_post_release_regime_support_ready, _advective_transition_reference_support_ready, _advective_transport_authority_support_ready, _merge_source_references, _model_family_proof_posture, _model_family_proof_posture_lines, _scientific_methods_applicability_lines, _scientific_methods_benchmark_lines, _scientific_methods_claim_summaries, _scientific_methods_highlighted_claim_grounding_lines, _scientific_methods_highlighted_claim_summaries, _scientific_methods_promotion_blockers, _scientific_methods_promotion_status, _scientific_methods_recommended_action_summaries, _scientific_methods_reference_case_concept_summary_lines, _scientific_methods_reference_case_grounding_lines, _scientific_methods_source_grounding_lines, _scientific_methods_support_strength_lines

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
    boundary_sensitive_post_release_count = sum(
        1
        for item in highlighted_claim_summaries
        if item.transport_regime_stability_status
        == "boundary_sensitive_post_release_recovery_regime"
    )
    boundary_sensitive_post_release_pace_count = sum(
        1
        for item in highlighted_claim_summaries
        if item.transport_regime_stability_status
        == "boundary_sensitive_post_release_recovery_pace"
    )
    stable_post_release_count = sum(
        1
        for item in highlighted_claim_summaries
        if item.transport_regime_stability_status == "post_release_flushing_recovery_regime"
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
    mandatory_claim_pass_count = sum(
        1 for item in claim_summaries if item.mandatory_for_release and item.reviewer_grade_passed
    )
    worksheet_ready_mandatory_claim_count = sum(
        1
        for item in claim_summaries
        if (
            item.mandatory_for_release
            and item.worksheet_status is not None
            and item.worksheet_status.value == "ready"
        )
    )
    if request.model_family.value == "reference_mass_balance":
        reviewer_grade_anchor_status = (
            "ready"
            if mandatory_claim_pass_count == mandatory_claim_count
            else "review_needed"
        )
    elif request.model_family.value in EXPERIMENTAL_MODEL_FAMILIES:
        reviewer_grade_anchor_status = "experimental_non_promotable"
    else:
        reviewer_grade_anchor_status = "normalization_parity_only"
    tier3_default_count = sum(
        1
        for payload in defaults_registry.core_defaults["parameters"].values()
        if payload.get("evidenceTier") == "tier_3_internal_screening_assumption"
    )
    materially_changed_parameters = sorted(
        parameter
        for parameter, payload in defaults_registry.core_defaults["parameters"].items()
        if bool(payload.get("materialOutputChange", False))
    )
    changed_parameters = sorted(
        parameter
        for parameter, payload in defaults_registry.core_defaults["parameters"].items()
        if payload.get("previousValue", payload.get("value")) != payload.get("value")
    )
    if materially_changed_parameters:
        default_change_sensitivity_lines = [
            "Material shipped-default rebaseline changes are recorded for: "
            + ", ".join(materially_changed_parameters[:5])
            + ". Review the defaults-rebaseline report before treating this proof surface as unchanged."
        ]
    elif changed_parameters:
        default_change_sensitivity_lines = [
            "Shipped-default numeric changes are recorded, but none are flagged as materially output-affecting for the current governed release."
        ]
    else:
        default_change_sensitivity_lines = [
            "No shipped-default numeric changes are recorded in the current governed release, so no proof drift is declared from defaults rebaseline."
        ]
    source_references = _merge_source_references(
        *[claim_summary.source_references for claim_summary in claim_summaries]
    )
    filtered_run_mode = (
        f"/{request.run_mode_filter.value}" if request.run_mode_filter is not None else ""
    )
    proof_posture = _model_family_proof_posture(request.model_family)
    proof_posture_lines = _model_family_proof_posture_lines(request.model_family)
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
        (
            "Default evidence posture: shipped core defaults are source-backed and free of "
            "tier_3 internal screening assumptions."
            if tier3_default_count == 0
            else (
                "Default evidence posture: shipped core defaults still include "
                f"{tier3_default_count} tier_3 internal screening assumption(s)."
            )
        ),
    ]
    summary_lines.append(
        "Reviewer-grade anchor status: " + reviewer_grade_anchor_status + "."
    )
    summary_lines.append(
        f"Mandatory claim pass count: {mandatory_claim_pass_count}/{mandatory_claim_count}."
    )
    summary_lines.append(
        "Worksheet readiness: "
        + f"{worksheet_ready_mandatory_claim_count}/{mandatory_claim_count} mandatory claims expose ready machine-readable worksheet artifacts."
    )
    summary_lines.extend(
        "Default-change sensitivity: " + line
        for line in default_change_sensitivity_lines
    )
    summary_lines.extend("Proof posture: " + line for line in proof_posture_lines)
    summary_lines.extend(
        "Applicability: " + line for line in applicability_lines[:2]
    )
    summary_lines.extend(
        "When not to use this MCP: " + line.removeprefix("When not to use this MCP: ").strip()
        for line in applicability_lines
        if line.startswith("When not to use this MCP:")
    )
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
            "Post-release regime stability: "
            + f"{boundary_sensitive_post_release_count} boundary-sensitive recovery claim(s), "
            + f"{boundary_sensitive_post_release_pace_count} half-recovery pace claim(s), "
            + f"{stable_post_release_count} stable post-release recovery claim(s)."
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
    if (
        request.model_family.value == "advective_screening_mass_balance"
        and _advective_post_release_regime_support_ready(claim_summaries_by_id)
    ):
        summary_lines.append(
            "Post-release regime support: stable sub-boundary, boundary-sensitive, and flushing-dominant recovery windows are anchored around the one-turnover flushing threshold after release stop."
        )
    if (
        request.model_family.value == "advective_screening_mass_balance"
        and _advective_post_release_directionality_support_ready(claim_summaries_by_id)
    ):
        summary_lines.append(
            "Post-release directionality support: same-chemistry sub-boundary, boundary, and beyond-boundary anchors show retained release-stop mass crossing the one-turnover anchor in the governed direction as the recovery window extends."
        )
    if (
        request.model_family.value == "advective_screening_mass_balance"
        and _advective_post_release_pace_support_ready(claim_summaries_by_id)
    ):
        summary_lines.append(
            "Post-release pace support: same-chemistry pre-half, half-recovery, and beyond-half anchors show the governed combined-loss half-recovery timescale directly rather than inferring recovery pace from the one-turnover boundary alone."
        )
    if (
        request.model_family.value == "advective_screening_mass_balance"
        and _advective_post_release_pace_directionality_support_ready(claim_summaries_by_id)
    ):
        summary_lines.append(
            "Post-release pace directionality support: same-chemistry pre-half, half-boundary, beyond-half, and extended-beyond-half anchors show retained release-stop mass crossing and moving materially below the 50% half-recovery anchor in the governed direction as the recovery window extends."
        )
    if (
        request.model_family.value == "advective_screening_mass_balance"
        and _advective_post_release_late_recovery_support_ready(claim_summaries_by_id)
    ):
        summary_lines.append(
            "Late recovery regime support: exceptional beyond-half anchors show the deep depletion authority layer actively distinguishing stable late-recovery from mere sub-half-recovery windows."
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
        reviewer_grade_anchor_status=reviewer_grade_anchor_status,
        mandatory_claim_pass_count=mandatory_claim_pass_count,
        worksheet_ready_mandatory_claim_count=worksheet_ready_mandatory_claim_count,
        proof_posture=proof_posture,
        proof_posture_lines=proof_posture_lines,
        claim_summaries=claim_summaries,
        highlighted_claim_summaries=highlighted_claim_summaries,
        summary_lines=summary_lines,
        applicability_lines=applicability_lines,
        source_grounding_lines=source_grounding_lines,
        highlighted_claim_grounding_lines=highlighted_claim_grounding_lines,
        reference_case_grounding_lines=reference_case_grounding_lines,
        reference_case_concept_lines=reference_case_concept_lines,
        default_change_sensitivity_lines=default_change_sensitivity_lines,
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
    summary_lines.extend("Proof posture: " + line for line in dossier.proof_posture_lines)
    summary_lines.extend("Applicability: " + line for line in dossier.applicability_lines[:2])
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
        reviewer_grade_anchor_status=dossier.reviewer_grade_anchor_status,
        mandatory_claim_pass_count=dossier.mandatory_claim_pass_count,
        worksheet_ready_mandatory_claim_count=dossier.worksheet_ready_mandatory_claim_count,
        proof_posture=dossier.proof_posture,
        proof_posture_lines=dossier.proof_posture_lines,
        highlighted_claim_ids=highlighted_claim_ids,
        highlighted_claim_summaries=dossier.highlighted_claim_summaries,
        summary_lines=summary_lines,
        applicability_lines=dossier.applicability_lines,
        source_grounding_lines=dossier.source_grounding_lines,
        highlighted_claim_grounding_lines=dossier.highlighted_claim_grounding_lines,
        reference_case_grounding_lines=dossier.reference_case_grounding_lines,
        reference_case_concept_lines=dossier.reference_case_concept_lines,
        default_change_sensitivity_lines=dossier.default_change_sensitivity_lines,
        benchmark_reference_lines=dossier.benchmark_reference_lines,
        support_strength_lines=dossier.support_strength_lines,
        promotion_blocker_claim_ids=dossier.promotion_blocker_claim_ids,
        promotion_blocker_summaries=dossier.promotion_blocker_summaries,
        recommended_action_summaries=dossier.recommended_action_summaries,
        recommended_actions=dossier.recommended_actions,
        limitations=dossier.limitations,
    )
