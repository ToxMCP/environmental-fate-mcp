"""Promote the external_adapter_canonical_equivalence_v1 claim from
worksheetStatus=missing to worksheetStatus=ready by wiring it to the
shipped adapter worksheet pack.

The adapter family is not promoted to reviewer-grade; the claim stays in
the public_method_description_plus_internal_oracle evidence family. The
shipped pack adds reviewability of the hand-worked canonical surface
signature for the JSON adapter fixture, paired with the existing
normalization-parity fixture that proves all governed adapter inputs
resolve to the same canonical shape.

Idempotent: re-running produces byte-identical output.
"""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CLAIMS_PATH = REPO_ROOT / "defaults" / "v1" / "scientific_validation_claims.json"

CLAIM_ID = "external_adapter_canonical_equivalence_v1"
PACK_DIR = "adapter-worksheet-pack"
LAST_REVIEWED = "2026-05-14"

TOLERANCE_BASIS = (
    "Shipped adapter worksheet pack requires governed JSON, CSV, and alternate-"
    "unit fixtures to normalize to the same canonical concentration-surface "
    "contract within floating-point screening tolerance, with no semantic-loss "
    "classification dropped during normalization. The hand-worked fixture pins "
    "the exact canonical surface signature (single surface_water concentration "
    "of 1.25e-02 mg/L) the JSON adapter fixture must reproduce."
)


def main() -> None:
    doc = json.loads(CLAIMS_PATH.read_text())
    claims = doc["claims"]
    claim = claims[CLAIM_ID]

    claim["worksheetStatus"] = "ready"
    claim["worksheetArtifactPath"] = f"{PACK_DIR}/{CLAIM_ID}.worksheet.json"
    claim["expectedOutputArtifactPath"] = f"{PACK_DIR}/{CLAIM_ID}.expected-outputs.json"
    claim["toleranceBasis"] = TOLERANCE_BASIS
    claim["lastReviewedDate"] = LAST_REVIEWED
    # Note: evidenceFamily intentionally remains
    # public_method_description_plus_internal_oracle; the adapter family is
    # not promoted to reviewer-grade by governance.

    CLAIMS_PATH.write_text(json.dumps(doc, indent=2) + "\n")
    print(f"Promoted {CLAIM_ID} to worksheetStatus=ready.")
    print(f"  worksheetArtifactPath: {claim['worksheetArtifactPath']}")
    print(f"  expectedOutputArtifactPath: {claim['expectedOutputArtifactPath']}")


if __name__ == "__main__":
    main()
