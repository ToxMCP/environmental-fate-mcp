"""Regression tests for the governed adapter worksheet pack (closes R7).

The adapter family does not run kernel physics; it normalizes governed
external-engine payloads into the canonical Fate MCP concentration-surface
contract. The worksheet pack ships a hand-worked canonical surface
signature so a reviewer can independently verify the adapter reproduces
the exact value the published method describes.

These tests confirm:

  1. The adapter worksheet manifest is well-formed and surfaces exactly
     one adapter claim (``external_adapter_canonical_equivalence_v1``).
  2. The claim remains in the
     ``public_method_description_plus_internal_oracle`` evidence family
     (no false promotion to reviewer-grade).
  3. The pack files are emitted to disk in the release bundle.
  4. The shipped worksheet content matches the live fixtures byte-for-
     byte (the pack is a deterministic projection of BENCHMARK_FIXTURES).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from fate_mcp.release_artifacts import (
    ADAPTER_WORKSHEET_PACK_DIR,
    _machine_readable_worksheet_fixtures,
    build_release_reports,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
ADAPTER_CLAIM_ID = "external_adapter_canonical_equivalence_v1"
EXPECTED_ADAPTER_CLAIM_COUNT = 1


@pytest.fixture(scope="module")
def reports() -> dict:
    return build_release_reports(REPO_ROOT)


def test_adapter_worksheet_manifest_is_present_and_well_formed(reports: dict) -> None:
    """The adapter manifest is structurally well-formed and ships one
    paired worksheet + expected-output artifact for the adapter claim.

    Note: ``manifest["passed"]`` (the reviewer-grade promotion gate) is
    intentionally NOT asserted true here. The adapter family is a
    normalization-parity lane, not a reviewer-grade kernel-physics family,
    so the reviewer-grade gate criteria (>= 2 independent evidence families,
    official_guidance_ready, multiple official_source_ids) are deliberately
    not met. The manifest still surfaces the gate's pass/fail signal for
    transparency, but the pack's value is reviewability of the canonical
    surface signature, not reviewer-grade promotion."""
    manifest = reports["adapter-worksheet-manifest"]
    assert manifest["modelFamily"] == "external_result_adapter"
    assert manifest["worksheetPackDirectory"] == ADAPTER_WORKSHEET_PACK_DIR
    assert manifest["claimCount"] == EXPECTED_ADAPTER_CLAIM_COUNT
    assert manifest["worksheetArtifactCount"] == EXPECTED_ADAPTER_CLAIM_COUNT
    assert manifest["expectedOutputArtifactCount"] == EXPECTED_ADAPTER_CLAIM_COUNT
    assert len(manifest["generatedArtifactPaths"]) == 2 * EXPECTED_ADAPTER_CLAIM_COUNT
    assert manifest["evidencePosture"] == "normalization_parity_lane"
    assert manifest["scientificEquivalenceClaim"] is False
    # The reviewer-grade gate is honestly False for the adapter claim
    # because the claim does not meet the >= 2 evidence-families bar.
    # The pack ships anyway as a reviewability artifact, not as a
    # promotion artifact.
    assert manifest["passed"] is False


def test_adapter_claim_remains_internal_oracle_evidence_family(reports: dict) -> None:
    """The adapter family is not reviewer-grade. The shipped worksheet pack
    adds reviewability; it does not upgrade the evidence posture."""
    manifest = reports["adapter-worksheet-manifest"]
    for claim in manifest["claims"]:
        assert claim["claimId"] == ADAPTER_CLAIM_ID
        assert claim["evidenceFamily"] == "public_method_description_plus_internal_oracle", (
            f"Adapter claim {claim['claimId']} unexpectedly promoted to "
            f"{claim['evidenceFamily']}"
        )
        assert claim["worksheetStatus"] == "ready"
        assert claim["worksheetArtifactPath"]
        assert claim["expectedOutputArtifactPath"]


def test_every_adapter_claim_has_a_paired_pack_file(reports: dict) -> None:
    manifest = reports["adapter-worksheet-manifest"]
    pack_files: dict[str, str] = reports["_adapter-worksheet-pack-files"]
    for claim in manifest["claims"]:
        assert claim["worksheetArtifactPath"] in pack_files
        assert claim["expectedOutputArtifactPath"] in pack_files


def test_shipped_worksheet_matches_live_fixtures_byte_for_byte(reports: dict) -> None:
    """The shipped adapter worksheet's bundled fixture content must match
    the live in-tree benchmark fixtures byte-for-byte."""
    manifest = reports["adapter-worksheet-manifest"]
    pack_files: dict[str, str] = reports["_adapter-worksheet-pack-files"]

    for claim_entry in manifest["claims"]:
        claim_id = claim_entry["claimId"]
        live_fixtures = _machine_readable_worksheet_fixtures(claim_id)
        assert live_fixtures, f"Adapter claim {claim_id} has no live fixtures"

        worksheet_text = pack_files[claim_entry["worksheetArtifactPath"]]
        worksheet_payload = json.loads(worksheet_text)
        shipped_fixture_names = [item["fixtureName"] for item in worksheet_payload["worksheets"]]
        live_fixture_names = [fixture["name"] for fixture in live_fixtures]
        assert shipped_fixture_names == live_fixture_names

        expected_text = pack_files[claim_entry["expectedOutputArtifactPath"]]
        expected_payload = json.loads(expected_text)
        for fixture, shipped in zip(live_fixtures, expected_payload["expectedOutputs"]):
            assert shipped["fixtureName"] == fixture["name"]
            assert shipped["expectedSurfaces"] == fixture.get("expected_surfaces", [])
            assert shipped["expectedTraceTerms"] == fixture.get("expected_trace_terms", [])


def test_adapter_pack_files_are_emitted_to_disk_in_release_bundle() -> None:
    """End-to-end check that the manifest and pack files reach the
    filesystem in the v0.5.0 release bundle."""
    bundle_dir = REPO_ROOT / "docs" / "releases" / "v0.5.0"
    manifest_path = bundle_dir / "adapter-worksheet-manifest.json"
    assert manifest_path.exists()
    pack_path = bundle_dir / ADAPTER_WORKSHEET_PACK_DIR
    assert pack_path.is_dir()
    artifact_paths = sorted(p.name for p in pack_path.iterdir() if p.is_file())
    assert len(artifact_paths) == 2 * EXPECTED_ADAPTER_CLAIM_COUNT
    worksheets = [p for p in artifact_paths if p.endswith(".worksheet.json")]
    expected_outputs = [p for p in artifact_paths if p.endswith(".expected-outputs.json")]
    assert len(worksheets) == EXPECTED_ADAPTER_CLAIM_COUNT
    assert len(expected_outputs) == EXPECTED_ADAPTER_CLAIM_COUNT
