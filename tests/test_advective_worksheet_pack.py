"""Regression tests for the governed advective worksheet pack.

The advective family remains non-promotable experimental, so the pack ships
the hand-worked machine-readable fixtures that back the family's internal-
oracle claims without falsely upgrading evidence-family posture. These tests
confirm:

  1. The manifest is well-formed and surfaces 19 advective claims, each
     with paired worksheet + expected-output artifacts and ``worksheetStatus =
     ready``.
  2. The manifest declares the family non-promotable so downstream readers
     cannot misinterpret it as a reviewer-grade evidence upgrade.
  3. Every shipped worksheet file matches the live in-tree benchmark fixture
     content byte-for-byte: the pack is a deterministic projection of the
     fixtures, not a hand-curated snapshot.
  4. Every claim's stated worksheet/expected-output artifact path matches its
     actually-shipped pack file.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from fate_mcp.release_artifacts import (
    ADVECTIVE_WORKSHEET_PACK_DIR,
    _machine_readable_worksheet_fixtures,
    build_release_reports,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
PACK_DIR_NAME = ADVECTIVE_WORKSHEET_PACK_DIR
EXPECTED_ADVECTIVE_CLAIM_COUNT = 19


@pytest.fixture(scope="module")
def reports() -> dict:
    return build_release_reports(REPO_ROOT)


def test_advective_worksheet_manifest_is_present_and_well_formed(reports: dict) -> None:
    manifest = reports["advective-worksheet-manifest"]
    assert manifest["modelFamily"] == "advective_screening_mass_balance"
    assert manifest["worksheetPackDirectory"] == PACK_DIR_NAME
    assert manifest["claimCount"] == EXPECTED_ADVECTIVE_CLAIM_COUNT
    assert manifest["worksheetArtifactCount"] == EXPECTED_ADVECTIVE_CLAIM_COUNT
    assert manifest["expectedOutputArtifactCount"] == EXPECTED_ADVECTIVE_CLAIM_COUNT
    # 19 claims x 2 artifacts each
    assert len(manifest["generatedArtifactPaths"]) == 2 * EXPECTED_ADVECTIVE_CLAIM_COUNT
    assert manifest["passed"] is True


def test_advective_worksheet_manifest_declares_non_promotable_governance(
    reports: dict,
) -> None:
    """The manifest must surface the advective family's non-promotable status
    explicitly so downstream readers cannot read the shipped pack as evidence
    of reviewer-grade promotion."""
    manifest = reports["advective-worksheet-manifest"]
    assert manifest["remainsExperimental"] is True
    assert manifest["promotable"] is False
    assert manifest["promotionStatus"] == "non_promotable_experimental"


def test_advective_claims_remain_internal_oracle_evidence_family(reports: dict) -> None:
    """Honest evidence posture: the shipped pack adds reviewability, not
    promotion. Every advective claim's evidenceFamily must stay
    ``public_method_description_plus_internal_oracle``."""
    manifest = reports["advective-worksheet-manifest"]
    for claim in manifest["claims"]:
        assert claim["evidenceFamily"] == "public_method_description_plus_internal_oracle", (
            f"Advective claim {claim['claimId']} unexpectedly promoted to "
            f"{claim['evidenceFamily']}. The family is non-promotable by governance."
        )
        assert claim["worksheetStatus"] == "ready"
        assert claim["worksheetArtifactPath"]
        assert claim["expectedOutputArtifactPath"]


def test_every_advective_claim_has_a_paired_pack_file(reports: dict) -> None:
    """For each claim row, both the worksheet and expected-output text must
    be present in the generated pack files dict."""
    manifest = reports["advective-worksheet-manifest"]
    pack_files: dict[str, str] = reports["_advective-worksheet-pack-files"]
    for claim in manifest["claims"]:
        worksheet_path = claim["worksheetArtifactPath"]
        expected_output_path = claim["expectedOutputArtifactPath"]
        assert worksheet_path in pack_files, (
            f"Missing worksheet text for {claim['claimId']} at {worksheet_path}"
        )
        assert expected_output_path in pack_files, (
            f"Missing expected-output text for {claim['claimId']} at {expected_output_path}"
        )


def test_shipped_worksheet_content_matches_live_fixtures_byte_for_byte(
    reports: dict,
) -> None:
    """Each shipped worksheet's bundled fixture content must match the live
    in-tree benchmark fixtures byte-for-byte. The pack is a deterministic
    projection of the fixtures; any drift here means the generator is
    inconsistent with its source."""
    manifest = reports["advective-worksheet-manifest"]
    pack_files: dict[str, str] = reports["_advective-worksheet-pack-files"]

    for claim_entry in manifest["claims"]:
        claim_id = claim_entry["claimId"]
        live_fixtures = _machine_readable_worksheet_fixtures(claim_id)
        assert live_fixtures, f"Advective claim {claim_id} has no live fixtures"

        worksheet_text = pack_files[claim_entry["worksheetArtifactPath"]]
        worksheet_payload = json.loads(worksheet_text)
        shipped_fixture_names = [item["fixtureName"] for item in worksheet_payload["worksheets"]]
        live_fixture_names = [fixture["name"] for fixture in live_fixtures]
        assert shipped_fixture_names == live_fixture_names, (
            f"Shipped worksheet for {claim_id} drifts from live fixtures: "
            f"shipped={shipped_fixture_names}, live={live_fixture_names}"
        )

        expected_text = pack_files[claim_entry["expectedOutputArtifactPath"]]
        expected_payload = json.loads(expected_text)
        for fixture, shipped in zip(live_fixtures, expected_payload["expectedOutputs"]):
            assert shipped["fixtureName"] == fixture["name"]
            assert shipped["expectedSurfaces"] == fixture.get("expected_surfaces", [])
            assert shipped["expectedTraceTerms"] == fixture.get("expected_trace_terms", [])


def test_advective_pack_files_are_actually_emitted_to_disk_in_release_bundle() -> None:
    """The release bundle directory must contain the manifest JSON and a
    pack subdirectory with all 38 paired artifact files. This is the
    end-to-end check that the pipeline reaches the filesystem."""
    bundle_dir = REPO_ROOT / "docs" / "releases" / "v0.5.0"
    manifest_path = bundle_dir / "advective-worksheet-manifest.json"
    assert manifest_path.exists(), (
        "advective-worksheet-manifest.json is not present in the v0.5.0 release "
        "bundle. Run `environmental-fate-mcp-build-release-bundle` after touching "
        "advective claims or the release artifact pipeline."
    )
    pack_path = bundle_dir / PACK_DIR_NAME
    assert pack_path.is_dir(), f"Expected pack directory at {pack_path}"
    artifact_paths = sorted(p.name for p in pack_path.iterdir() if p.is_file())
    # 19 worksheets + 19 expected-outputs = 38 files
    assert len(artifact_paths) == 2 * EXPECTED_ADVECTIVE_CLAIM_COUNT, (
        f"Expected 38 files in {pack_path}; found {len(artifact_paths)}"
    )
    worksheets = [p for p in artifact_paths if p.endswith(".worksheet.json")]
    expected_outputs = [p for p in artifact_paths if p.endswith(".expected-outputs.json")]
    assert len(worksheets) == EXPECTED_ADVECTIVE_CLAIM_COUNT
    assert len(expected_outputs) == EXPECTED_ADVECTIVE_CLAIM_COUNT
