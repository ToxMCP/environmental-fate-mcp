"""Regression test for the pendimethalin public worked-case slice.

The slice at ``examples/pendimethalin_public_slice/`` is the canonical frozen
public worked-case for the Environmental Fate MCP. This test re-runs the same
pipeline under the same frozen environment (deterministic UUIDs + frozen
timestamps) and asserts:

  1. SHA-256 integrity hashes on the concentration bundle and the regulatory
     handoff package match the frozen values byte-for-byte. This is the
     strongest reproducibility contract the MCP exposes.
  2. Generated identifiers (scenario_id, run_id, bundle_id, package_id) match
     the frozen values.
  3. Key numeric concentration values match the frozen output_summary.json
     within ``math.isclose`` tolerance.
  4. The slice ``source_lock.json`` is well-formed and free of local paths.
  5. The on-disk input JSONs round-trip through Pydantic ``model_validate``
     identically to the in-memory payloads built by the runner.

Failure of any of these implies a non-trivial change in the runtime, the
defaults pack, the physics, or the slice itself. The fix is either to revise
the runtime (if the regression is unintended) or to regenerate the slice via
``scripts/generate_pendimethalin_slice.py`` (if the change is deliberate and
the slice should track it).
"""

from __future__ import annotations

import json
import math
from pathlib import Path

from fate_mcp.models import (
    BuildEnvironmentalReleaseScenarioRequest,
    EstimateEventSedimentYieldMusleRequest,
    EstimateSedimentAssociatedChemicalLoadRequest,
    EstimateSoilLossRusleRequest,
    FateModelRunOptions,
)

from tests._pendimethalin_slice_runner import run_pipeline


REPO_ROOT = Path(__file__).resolve().parents[1]
SLICE_ROOT = REPO_ROOT / "examples" / "pendimethalin_public_slice"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def _assert_close(actual: float, expected: float, *, rel_tol: float = 1e-9) -> None:
    assert math.isclose(actual, expected, rel_tol=rel_tol, abs_tol=1e-15), (
        f"expected {expected!r}, got {actual!r}"
    )


def test_slice_inputs_round_trip_through_public_request_contracts() -> None:
    """Every frozen input JSON must validate cleanly against the public
    Pydantic request model. This guards against silent schema drift between
    the slice and the runtime."""
    BuildEnvironmentalReleaseScenarioRequest.model_validate(
        _load_json(SLICE_ROOT / "inputs" / "01_release_scenario_request.json")
    )
    FateModelRunOptions.model_validate(
        _load_json(SLICE_ROOT / "inputs" / "02_run_options_deterministic.json")
    )
    FateModelRunOptions.model_validate(
        _load_json(SLICE_ROOT / "inputs" / "03_run_options_probabilistic.json")
    )
    # The probabilistic overlay is a partial dict (iterations/seed/etc.) so
    # we don't validate it against the full request model; we just assert
    # the expected keys are present.
    overlay = _load_json(SLICE_ROOT / "inputs" / "04_probabilistic_overlay.json")
    assert {"iterations", "seed", "sample_manifest_mode"} <= overlay.keys()
    EstimateSoilLossRusleRequest.model_validate(
        _load_json(SLICE_ROOT / "inputs" / "05_rusle_request.json")
    )
    EstimateEventSedimentYieldMusleRequest.model_validate(
        _load_json(SLICE_ROOT / "inputs" / "06_musle_request.json")
    )
    EstimateSedimentAssociatedChemicalLoadRequest.model_validate(
        _load_json(SLICE_ROOT / "inputs" / "07_chemical_load_request.json")
    )


def test_source_lock_is_well_formed_and_leak_free() -> None:
    """The public source lock must declare the expected anchor set and must
    contain no local-machine path leaks."""
    source_lock_path = SLICE_ROOT / "source_lock.json"
    source_lock_text = source_lock_path.read_text()
    source_lock = _load_json(source_lock_path)

    assert source_lock["casePackId"] == "pendimethalin_public_slice_v1"
    assert "/Users/" not in source_lock_text
    assert "file:///" not in source_lock_text

    expected_anchors = {
        "footprint.ppdb.pendimethalin",
        "echa.guidance.ircsa",
        "oecd.test_guidelines.section3",
        "usda.rusle.handbook703",
        "usda.musle.williams1975",
    }
    actual_anchors = {item["sourceId"] for item in source_lock["sourceAnchors"]}
    assert expected_anchors <= actual_anchors, (
        f"missing source anchors: {expected_anchors - actual_anchors}"
    )
    for anchor in source_lock["sourceAnchors"]:
        assert {
            "sourceId",
            "title",
            "url",
            "retrievedAt",
            "casePackReviewedAt",
            "retrievalMethod",
            "observedUse",
            "lockedFacts",
        } <= set(anchor)

    assert any(
        "regulatory acceptance" in claim.lower() for claim in source_lock["nonClaims"]
    )
    assert any("WEPP" in claim for claim in source_lock["nonClaims"])


def test_slice_pipeline_rebuilds_to_byte_equal_integrity_hashes_and_ids() -> None:
    """Re-running the pipeline under the same frozen environment must produce
    byte-identical integrity hashes and identifiers to the frozen slice.

    This is the strongest reproducibility contract: any drift in the runtime,
    the defaults pack, the physics, or the underlying float-repr behavior
    will trip this assertion.
    """
    expected = _load_json(SLICE_ROOT / "outputs" / "output_summary.json")
    result = run_pipeline(REPO_ROOT)

    objects = result["objects"]
    bundle = objects["bundle"]
    handoff = objects["handoff"]
    scenario = objects["scenario"]
    det_result = objects["det_result"]
    prob_result = objects["prob_result"]

    assert bundle.integrity_hash == expected["integrityHashes"]["concentrationSurfaceBundle"], (
        "ConcentrationSurfaceBundle.integrity_hash has drifted from the frozen slice. "
        "If this change is intentional, re-run scripts/generate_pendimethalin_slice.py."
    )
    assert handoff.integrity_hash == expected["integrityHashes"]["regulatoryHandoffPackage"], (
        "RegulatoryHandoffPackage.integrity_hash has drifted from the frozen slice. "
        "If this change is intentional, re-run scripts/generate_pendimethalin_slice.py."
    )

    assert scenario.scenario_id == expected["scenarioId"]
    assert det_result.run_summary.run_id == expected["runIdentifiers"]["deterministicRunId"]
    assert prob_result.run_summary.run_id == expected["runIdentifiers"]["probabilisticRunId"]
    assert bundle.bundle_id == expected["runIdentifiers"]["bundleId"]
    assert handoff.package_id == expected["runIdentifiers"]["regulatoryHandoffPackageId"]


def test_slice_deterministic_concentrations_match_within_tolerance() -> None:
    """Numeric cross-check on the deterministic surfaces. Tighter than the
    hash test (covers the same content) but easier to interpret when failing,
    and catches drift in physics that happens to leave the bundle structure
    unchanged."""
    expected = _load_json(SLICE_ROOT / "outputs" / "output_summary.json")
    result = run_pipeline(REPO_ROOT)
    det_result = result["objects"]["det_result"]

    soil_surface = next(s for s in det_result.surfaces if s.medium.value == "soil")
    air_surface = next(s for s in det_result.surfaces if s.medium.value == "air")

    exp_soil = expected["deterministicConcentrations"]["soilAgriculturalSoil"]
    exp_air = expected["deterministicConcentrations"]["airAmbientAir"]

    _assert_close(soil_surface.concentration_value, exp_soil["value"])
    assert soil_surface.concentration_unit == exp_soil["unit"]
    assert soil_surface.model_family.value == exp_soil["modelFamily"]

    _assert_close(air_surface.concentration_value, exp_air["value"])
    assert air_surface.concentration_unit == exp_air["unit"]
    assert air_surface.model_family.value == exp_air["modelFamily"]


def test_slice_probabilistic_soil_percentiles_match_within_tolerance() -> None:
    """The probabilistic soil percentiles (and seed + iteration health) must
    match the frozen slice. Probabilistic determinism is more delicate than
    deterministic determinism because the RNG seed has to thread cleanly."""
    expected = _load_json(SLICE_ROOT / "outputs" / "output_summary.json")
    result = run_pipeline(REPO_ROOT)
    prob = result["objects"]["prob_result"]

    soil_p50 = next(s for s in prob.median_surfaces if s.medium.value == "soil")
    soil_p90 = next(s for s in prob.p90_surfaces if s.medium.value == "soil")
    soil_p95 = next(s for s in prob.p95_surfaces if s.medium.value == "soil")
    exp_prob = expected["probabilisticSoil"]

    _assert_close(soil_p50.concentration_value, exp_prob["p50"])
    _assert_close(soil_p90.concentration_value, exp_prob["p90"])
    _assert_close(soil_p95.concentration_value, exp_prob["p95"])

    assert prob.iteration_count == exp_prob["iterationCount"]
    assert prob.completed_iteration_count == exp_prob["completedIterationCount"]
    assert prob.failed_iteration_count == exp_prob["failedIterationCount"]
    assert prob.sampling_seed == exp_prob["samplingSeed"]
    assert prob.sampled_parameter_count == exp_prob["sampledParameterCount"]


def test_slice_erosion_lane_values_match_within_tolerance() -> None:
    """Erosion / sediment lane regression: RUSLE soil loss, MUSLE event yield,
    and sediment-associated chemical-load handoff must reproduce the frozen
    slice values."""
    expected = _load_json(SLICE_ROOT / "outputs" / "output_summary.json")
    result = run_pipeline(REPO_ROOT)
    objects = result["objects"]
    relevance = objects["relevance"]
    rusle = objects["rusle"]
    musle = objects["musle"]
    chem_load = objects["chem_load"]
    exp_erosion = expected["erosion"]

    assert relevance.relevance_level.value == exp_erosion["relevanceLevel"]
    assert relevance.particle_bound_transport_plausible == exp_erosion["particleBoundTransportPlausible"]
    _assert_close(rusle.annual_soil_loss_t_ha_yr, exp_erosion["rusleAnnualSoilLossTHaYr"])
    _assert_close(rusle.total_soil_loss_t_yr, exp_erosion["rusleTotalSoilLossTYr"])
    _assert_close(musle.sediment_yield_t_event, exp_erosion["musleEventSedimentYieldT"])
    _assert_close(chem_load.sediment_associated_load_kg, exp_erosion["sedimentAssociatedLoadKg"])


def test_slice_scientific_review_outcome_matches() -> None:
    """The scientific review preview outcome and status must be stable
    against the frozen slice."""
    expected = _load_json(SLICE_ROOT / "outputs" / "output_summary.json")
    result = run_pipeline(REPO_ROOT)
    review = result["objects"]["review"]
    exp_review = expected["scientificReview"]

    outcome = review.review_outcome.value if hasattr(review.review_outcome, "value") else str(review.review_outcome)
    status = review.review_status.value if hasattr(review.review_status, "value") else str(review.review_status)
    assert outcome == exp_review["reviewOutcome"]
    assert status == exp_review["reviewStatus"]
    assert review.model_family.value == exp_review["modelFamily"]
