"""Promote the 19 advective-family claims from worksheetStatus=missing to
worksheetStatus=ready by wiring them to the shipped advective worksheet pack.

The advective family stays governed as non-promotable experimental
(``promotable: False`` in release_artifacts._build_advective_promotion_bar_report),
so each claim's ``evidenceFamily`` remains ``public_method_description_plus_
internal_oracle``. This script only:

  * sets ``worksheetStatus`` to ``ready`` (because the pack is now shipped),
  * sets ``worksheetArtifactPath`` and ``expectedOutputArtifactPath`` to the
    pack-relative paths used by the release artifact pipeline,
  * refreshes ``toleranceBasis`` to reference the shipped pack rather than the
    pre-pack internal-oracle framing,
  * updates ``lastReviewedDate`` to the date of this metadata pass.

Idempotent: re-running it produces byte-identical output.
"""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CLAIMS_PATH = REPO_ROOT / "defaults" / "v1" / "scientific_validation_claims.json"

LAST_REVIEWED = "2026-05-14"
PACK_DIR = "advective-worksheet-pack"


# claim_class -> reviewer-facing tolerance-basis prose anchored on the
# shipped advective worksheet pack. Distinct per claim class so each
# downstream reviewer surface gets a precise rationale.
TOLERANCE_BY_CLASS: dict[str, str] = {
    "advective_single_medium_equation": (
        "Shipped advective worksheet pack requires the advective finite-duration "
        "screening surface to match the bundled hand-worked first-order "
        "degradation + first-order advective clearance fixtures within the "
        "fixture-declared tolerance. Internal-oracle posture remains because the "
        "advective family is non-promotable by governance."
    ),
    "advective_loss_dominance": (
        "Shipped advective worksheet pack requires the dominant-loss "
        "classification to match the hand-worked anchor + companion fixtures "
        "across degradation-dominant, clearance-dominant, and mixed-margin "
        "configurations within fixture-declared tolerance."
    ),
    "advective_mass_balance_accounting": (
        "Shipped advective worksheet pack requires |emitted_mass - retained_mass "
        "- cumulative_degraded_mass - cumulative_advected_mass| to remain below "
        "the screening closure threshold on every bundled fixture (typically "
        "< 1 microgram)."
    ),
    "advective_transport_regime": (
        "Shipped advective worksheet pack requires residence-time turnover "
        "counts, turnover-boundary offsets, and plateau-fraction reporting to "
        "match the bundled closed-form combined-loss expressions within fixture-"
        "declared tolerance."
    ),
    "advective_loss_transition_sensitivity": (
        "Shipped advective worksheet pack requires the dominant-loss "
        "interpretation to flip in the expected direction across the bundled "
        "near-parity sensitivity fixtures (half-life or residence-time crossing "
        "the loss-balance boundary)."
    ),
    "advective_time_bucket_semantics": (
        "Shipped advective worksheet pack requires each bucket-level surface to "
        "align with the elapsed-time first-order combined-loss expression on "
        "every bundled time-bucket fixture within fixture-declared tolerance."
    ),
    "advective_post_release_recovery": (
        "Shipped advective worksheet pack requires post-release retained-mass to "
        "follow the closed-form combined-loss decay anchored at release-stop, "
        "with release-stop fractions for retained, degraded, and advected mass "
        "summing to 1.0 on every bundled recovery fixture within fixture-"
        "declared tolerance."
    ),
    "advective_post_release_transition": (
        "Shipped advective worksheet pack requires post-release recovery windows "
        "to be classified consistently with the one-turnover flushing boundary "
        "across every bundled boundary-transition fixture."
    ),
    "advective_post_release_directionality": (
        "Shipped advective worksheet pack requires retained-mass to decline "
        "monotonically as recovery windows cross the one-turnover anchor in "
        "the expected direction on every bundled directionality fixture."
    ),
    "advective_post_release_pace": (
        "Shipped advective worksheet pack requires the reported combined-loss "
        "half-recovery time to match (ln 2) / (decay_constant + advective_"
        "constant) on every bundled pace fixture within fixture-declared "
        "tolerance."
    ),
    "advective_post_release_pace_directionality": (
        "Shipped advective worksheet pack requires retained-mass to remain "
        "monotonically below 50% on every bundled post-half-recovery fixture."
    ),
    "advective_late_recovery": (
        "Shipped advective worksheet pack requires the late-recovery regime "
        "classification to remain stable under the bounded combined-loss "
        "depletion authority layer on every bundled late-recovery fixture."
    ),
    "advective_edge_condition": (
        "Shipped advective worksheet pack requires effective-persistence "
        "(negligible degradation) screening surfaces to remain bounded by "
        "residence-time clearance alone on every bundled persistence-edge "
        "fixture within fixture-declared tolerance."
    ),
    "advective_clearance_edge_condition": (
        "Shipped advective worksheet pack requires retained-mass concentration "
        "to respond to residence-time overrides in the expected direction on "
        "every bundled clearance-edge fixture (shorter residence reduces, "
        "longer residence raises) within fixture-declared tolerance."
    ),
    "advective_duration_edge_condition": (
        "Shipped advective worksheet pack requires long-duration runs to "
        "approach the combined-loss plateau on every bundled duration-edge "
        "fixture within fixture-declared tolerance."
    ),
    "advective_parameter_override": (
        "Shipped advective worksheet pack requires a user-supplied surface-"
        "water residence-time override to be reflected in the assumption ledger "
        "and to drive the resulting concentration surface on every bundled "
        "parameter-override fixture within fixture-declared tolerance."
    ),
}


def main() -> None:
    doc = json.loads(CLAIMS_PATH.read_text())
    claims = doc["claims"]

    updated: list[str] = []
    skipped: list[str] = []

    for claim_id, claim in claims.items():
        if claim.get("modelFamily") != "advective_screening_mass_balance":
            continue

        claim_class = claim.get("claimClass", "")
        tolerance_basis = TOLERANCE_BY_CLASS.get(claim_class)
        if tolerance_basis is None:
            raise SystemExit(
                f"No reviewer-facing tolerance basis defined for claimClass="
                f"{claim_class!r} on claim {claim_id!r}."
            )

        # worksheetStatus -> ready
        claim["worksheetStatus"] = "ready"
        # Pack-relative paths matching what the release pipeline emits
        claim["worksheetArtifactPath"] = f"{PACK_DIR}/{claim_id}.worksheet.json"
        claim["expectedOutputArtifactPath"] = f"{PACK_DIR}/{claim_id}.expected-outputs.json"
        claim["toleranceBasis"] = tolerance_basis
        claim["lastReviewedDate"] = LAST_REVIEWED
        # NOTE: evidenceFamily remains public_method_description_plus_internal_oracle
        # because the advective family is non-promotable by governance.
        updated.append(claim_id)

    CLAIMS_PATH.write_text(json.dumps(doc, indent=2) + "\n")

    print(f"Promoted {len(updated)} advective claims to worksheetStatus=ready.")
    for cid in updated:
        print(f"  * {cid}")


if __name__ == "__main__":
    main()
