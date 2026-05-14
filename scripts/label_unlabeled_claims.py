"""Fill missing evidence-quality metadata on the 20 unlabeled scientific
validation claims for the advective challenge family and the external-result
adapter, mirroring the existing fugacity internal-oracle precedent.

Idempotent: only writes fields that are missing or null. Run from repo root.
"""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CLAIMS_PATH = REPO_ROOT / "defaults" / "v1" / "scientific_validation_claims.json"
REFCASES_PATH = REPO_ROOT / "defaults" / "v1" / "scientific_reference_cases.json"

LAST_REVIEWED = "2026-05-14"
EVIDENCE_FAMILY = "public_method_description_plus_internal_oracle"
WORKSHEET_STATUS = "missing"

ADVECTIVE_PLUGIN_REF = (
    "fate_mcp.plugins.advective_screening_mass_balance:"
    "AdvectiveScreeningMassBalancePlugin._build_surface"
)
ADVECTIVE_TIME_BUCKET_PLUGIN_REF = (
    "fate_mcp.plugins.advective_screening_mass_balance:"
    "AdvectiveTimeBucketMassBalancePlugin._build_surface"
)
ADAPTER_PLUGIN_REF = (
    "fate_mcp.plugins.external_result_adapter:"
    "ExternalResultAdapterHarnessPlugin.run"
)

REVIEW_NOTE_ADVECTIVE = (
    "This claim is verified against the experimental advective challenge family "
    "via deterministic internal-oracle fixtures; reviewer-grade promotion remains "
    "gated on shipping an independent hand-worked advective worksheet pack."
)
REVIEW_NOTE_ADAPTER = (
    "This claim is verified by normalization-parity self-checks against governed "
    "JSON, CSV, and alternate-unit fixtures; it does not validate the upstream "
    "source-engine calculation."
)

# claim_class -> tolerance basis prose
TOLERANCE_BY_CLASS: dict[str, str] = {
    "advective_single_medium_equation": (
        "Internal-oracle tolerance requires the advective finite-duration screening "
        "surface to match the hand-worked first-order degradation + first-order "
        "advective clearance equation within floating-point screening tolerance."
    ),
    "advective_loss_dominance": (
        "Internal-oracle tolerance requires the dominant-loss classification (degradation-"
        "dominant, clearance-dominant, or mixed-margin) to match the expected category "
        "given the half-life vs. residence-time configuration in every supporting fixture."
    ),
    "advective_mass_balance_accounting": (
        "Internal-oracle tolerance requires |emitted_mass - retained_compartment_mass - "
        "cumulative_degraded_mass - cumulative_advected_mass| to remain below the "
        "screening closure threshold (1 microgram) on every fixture."
    ),
    "advective_transport_regime": (
        "Internal-oracle tolerance requires residence-time turnover counts, turnover-boundary "
        "offsets, and plateau-fraction reporting to match the closed-form combined-loss "
        "expressions within floating-point screening tolerance."
    ),
    "advective_loss_transition_sensitivity": (
        "Internal-oracle tolerance requires the dominant-loss interpretation to flip in the "
        "expected direction when half-life or residence time crosses the near-parity boundary "
        "in the supporting sensitivity fixtures."
    ),
    "advective_time_bucket_semantics": (
        "Internal-oracle tolerance requires each time-bucket surface to align with the elapsed-"
        "time first-order combined-loss expression within floating-point screening tolerance."
    ),
    "advective_post_release_recovery": (
        "Internal-oracle tolerance requires post-release retained-mass to follow the closed-"
        "form combined-loss decay anchored at the release-stop point, and release-stop "
        "fractions for retained, degraded, and advected mass to sum to 1.0 within floating-"
        "point screening tolerance."
    ),
    "advective_post_release_transition": (
        "Internal-oracle tolerance requires post-release recovery windows to be classified "
        "consistently with the one-turnover flushing boundary across the supporting fixtures."
    ),
    "advective_post_release_directionality": (
        "Internal-oracle tolerance requires retained-mass to decline monotonically as recovery "
        "windows cross the one-turnover anchor in the expected direction."
    ),
    "advective_post_release_pace": (
        "Internal-oracle tolerance requires the reported combined-loss half-recovery time to "
        "match the closed-form (ln 2) / (decay_constant + advective_constant) expression within "
        "floating-point screening tolerance."
    ),
    "advective_post_release_pace_directionality": (
        "Internal-oracle tolerance requires retained-mass to remain monotonically below 50% as "
        "post-release windows cross the half-recovery anchor in the supporting fixtures."
    ),
    "advective_late_recovery": (
        "Internal-oracle tolerance requires the late-recovery regime classification to remain "
        "stable under the bounded combined-loss depletion authority layer across the supporting "
        "fixtures."
    ),
    "advective_edge_condition": (
        "Internal-oracle tolerance requires effective-persistence (negligible degradation) "
        "screening surfaces to remain bounded by residence-time clearance alone within floating-"
        "point screening tolerance."
    ),
    "advective_clearance_edge_condition": (
        "Internal-oracle tolerance requires retained-mass concentration to respond to "
        "residence-time overrides in the expected direction (shorter residence reduces, longer "
        "residence raises) within floating-point screening tolerance."
    ),
    "advective_duration_edge_condition": (
        "Internal-oracle tolerance requires long-duration runs to approach the combined-loss "
        "plateau concentration within floating-point screening tolerance."
    ),
    "advective_parameter_override": (
        "Internal-oracle tolerance requires a user-supplied surface-water residence-time "
        "override to be reflected in the assumption ledger and to drive the resulting "
        "concentration surface within floating-point screening tolerance."
    ),
    "adapter_contract_normalization": (
        "Internal-oracle tolerance requires governed JSON, CSV, and alternate-unit fixtures to "
        "normalize to the same canonical concentration-surface contract within floating-point "
        "screening tolerance, with no semantic-loss classification dropped during normalization."
    ),
}


def _union_official_source_ids(
    reference_case_ids: list[str], reference_cases: dict
) -> list[str]:
    """Return the deduplicated, order-preserving union of officialSourceIds
    across the supplied reference-case families."""
    seen: list[str] = []
    for cid in reference_case_ids:
        case = reference_cases.get(cid)
        if not case:
            continue
        for sid in case.get("officialSourceIds", []) or []:
            if sid not in seen:
                seen.append(sid)
    return seen


def _plugin_refs_for(claim_id: str, model_family: str) -> list[str]:
    if model_family == "external_result_adapter":
        return [ADAPTER_PLUGIN_REF]
    if "time_bucket" in claim_id:
        return [ADVECTIVE_TIME_BUCKET_PLUGIN_REF, ADVECTIVE_PLUGIN_REF]
    return [ADVECTIVE_PLUGIN_REF]


def _review_note_for(model_family: str) -> str:
    if model_family == "external_result_adapter":
        return REVIEW_NOTE_ADAPTER
    return REVIEW_NOTE_ADVECTIVE


def main() -> None:
    claims_doc = json.loads(CLAIMS_PATH.read_text())
    refcases_doc = json.loads(REFCASES_PATH.read_text())
    claims = claims_doc["claims"]
    reference_cases = refcases_doc["cases"]

    updated: list[str] = []
    skipped: list[str] = []

    for claim_id, claim in claims.items():
        if claim.get("evidenceFamily"):
            skipped.append(claim_id)
            continue

        model_family = claim.get("modelFamily", "")
        claim_class = claim.get("claimClass", "")

        if claim_class not in TOLERANCE_BY_CLASS:
            raise SystemExit(
                f"No tolerance basis defined for claimClass={claim_class!r} "
                f"on claim {claim_id!r}; refusing to silently mislabel."
            )

        ref_ids = claim.get("referenceCaseIds", []) or []
        official_source_ids = _union_official_source_ids(ref_ids, reference_cases)

        # Add metadata, preserving existing populated fields if any
        claim.setdefault("evidenceFamily", EVIDENCE_FAMILY)
        claim.setdefault("worksheetStatus", WORKSHEET_STATUS)
        claim.setdefault("lastReviewedDate", LAST_REVIEWED)
        claim.setdefault("toleranceBasis", TOLERANCE_BY_CLASS[claim_class])
        if not claim.get("officialSourceIds"):
            claim["officialSourceIds"] = official_source_ids
        if not claim.get("pluginCodeReferences"):
            claim["pluginCodeReferences"] = _plugin_refs_for(claim_id, model_family)
        if not claim.get("reviewNotes"):
            claim["reviewNotes"] = [_review_note_for(model_family)]

        updated.append(claim_id)

    CLAIMS_PATH.write_text(json.dumps(claims_doc, indent=2) + "\n")

    print(f"Updated {len(updated)} claims; skipped {len(skipped)} already-labeled claims.")
    print()
    print("Updated:")
    for cid in updated:
        print(f"  • {cid}")
    print()
    print(f"Skipped (already labeled): {len(skipped)}")


if __name__ == "__main__":
    main()
