"""Generate the frozen public worked-case slice for pendimethalin.

Re-runs the canonical pipeline under the frozen environment (deterministic
UUIDs + frozen timestamps) and writes every input and output as a JSON file
under ``examples/pendimethalin_public_slice/``. Also writes ``output_summary.json``
which carries the expected SHA-256 integrity hashes and a small set of stable
numeric checkpoints that the regression test re-verifies.

This script is the single source of truth for the slice's frozen contents.
Running it again produces byte-identical files (modulo the slice metadata
``generatedAt`` timestamp, which is also frozen). If you need to regenerate
after a physics change, the regression test will fail until you re-run this.

Usage::

    .venv/bin/python scripts/generate_pendimethalin_slice.py

Exit code is 0 on success, non-zero on pipeline failure.
"""

from __future__ import annotations

import sys
from datetime import timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "tests"))  # noqa: E402

from _pendimethalin_slice_runner import (  # noqa: E402
    FROZEN_TIMESTAMP,
    run_pipeline,
    write_json,
)


SLICE_ROOT = REPO_ROOT / "examples" / "pendimethalin_public_slice"
CASE_PACK_ID = "pendimethalin_public_slice_v1"
LOCKED_ON = FROZEN_TIMESTAMP.date().isoformat()


def _build_output_summary(objects: dict) -> dict:
    """Numeric + identity checkpoints that the regression test re-verifies.

    The byte-equal SHA-256 hashes are the primary regression signal; the
    numeric checkpoints are a human-readable cross-check that also catches
    physics drift (e.g., a region-default capacity change that doesn't alter
    the bundle structure but shifts a concentration value).
    """
    scenario = objects["scenario"]
    det_result = objects["det_result"]
    bundle = objects["bundle"]
    prob_result = objects["prob_result"]
    review = objects["review"]
    handoff = objects["handoff"]
    relevance = objects["relevance"]
    rusle = objects["rusle"]
    musle = objects["musle"]
    chem_load = objects["chem_load"]

    soil_surface = next(s for s in det_result.surfaces if s.medium.value == "soil")
    air_surface = next(s for s in det_result.surfaces if s.medium.value == "air")

    soil_median = next(s for s in prob_result.median_surfaces if s.medium.value == "soil")
    soil_p90 = next(s for s in prob_result.p90_surfaces if s.medium.value == "soil")
    soil_p95 = next(s for s in prob_result.p95_surfaces if s.medium.value == "soil")

    return {
        "casePackId": CASE_PACK_ID,
        "generatedBy": "FateRuntime via tests/_pendimethalin_slice_runner.run_pipeline",
        "generatedAt": FROZEN_TIMESTAMP.astimezone(timezone.utc).isoformat(),
        "chemicalIdentity": {
            "preferredName": scenario.chemical_identity.get("preferredName"),
            "casrn": scenario.chemical_identity.get("casrn"),
        },
        "scenarioId": scenario.scenario_id,
        "integrityHashes": {
            "concentrationSurfaceBundle": bundle.integrity_hash,
            "regulatoryHandoffPackage": handoff.integrity_hash,
        },
        "runIdentifiers": {
            "deterministicRunId": det_result.run_summary.run_id,
            "probabilisticRunId": prob_result.run_summary.run_id,
            "bundleId": bundle.bundle_id,
            "regulatoryHandoffPackageId": handoff.package_id,
        },
        "deterministicConcentrations": {
            "soilAgriculturalSoil": {
                "value": soil_surface.concentration_value,
                "unit": soil_surface.concentration_unit,
                "modelFamily": soil_surface.model_family.value,
                "reportedTimeSemantics": soil_surface.reported_time_semantics,
            },
            "airAmbientAir": {
                "value": air_surface.concentration_value,
                "unit": air_surface.concentration_unit,
                "modelFamily": air_surface.model_family.value,
                "reportedTimeSemantics": air_surface.reported_time_semantics,
            },
        },
        "probabilisticSoil": {
            "p50": soil_median.concentration_value,
            "p90": soil_p90.concentration_value,
            "p95": soil_p95.concentration_value,
            "unit": soil_median.concentration_unit,
            "iterationCount": prob_result.iteration_count,
            "completedIterationCount": prob_result.completed_iteration_count,
            "failedIterationCount": prob_result.failed_iteration_count,
            "samplingSeed": prob_result.sampling_seed,
            "sampledParameterCount": prob_result.sampled_parameter_count,
        },
        "scientificReview": {
            "reviewOutcome": review.review_outcome.value
            if hasattr(review.review_outcome, "value")
            else str(review.review_outcome),
            "reviewStatus": review.review_status.value
            if hasattr(review.review_status, "value")
            else str(review.review_status),
            "modelFamily": review.model_family.value,
        },
        "regulatoryHandoff": {
            "handoffProfileId": handoff.handoff_profile_id,
            "targetModules": handoff.target_modules,
            "crosswalkEntryCount": len(handoff.crosswalk_entries),
        },
        "erosion": {
            "relevanceLevel": relevance.relevance_level.value
            if hasattr(relevance.relevance_level, "value")
            else str(relevance.relevance_level),
            "particleBoundTransportPlausible": relevance.particle_bound_transport_plausible,
            "rusleAnnualSoilLossTHaYr": rusle.annual_soil_loss_t_ha_yr,
            "rusleTotalSoilLossTYr": rusle.total_soil_loss_t_yr,
            "musleEventSedimentYieldT": musle.sediment_yield_t_event,
            "sedimentAssociatedLoadKg": chem_load.sediment_associated_load_kg,
        },
        "reviewPosture": {
            "screeningOnly": True,
            "regulatorAcceptance": False,
            "qualityFlags": [
                {
                    "code": "screening_only_demonstration",
                    "severity": "info",
                    "message": (
                        "This slice is a public-source pendimethalin screening "
                        "demonstration; it is not a regulatory submission, not a "
                        "calibrated site-specific assessment, and not a claim of "
                        "source-engine equivalence to EUSES, SimpleBox, or WEPP."
                    ),
                },
            ],
        },
    }


def _build_source_lock() -> dict:
    return {
        "casePackId": CASE_PACK_ID,
        "lockedOn": LOCKED_ON,
        "purpose": (
            "Public-source Environmental Fate MCP demonstration of UK arable "
            "pendimethalin screening through the deterministic, probabilistic, "
            "scientific review, and erosion / sediment lanes."
        ),
        "sourceAnchors": [
            {
                "sourceId": "footprint.ppdb.pendimethalin",
                "title": "FOOTPRINT Pesticide Properties DataBase - Pendimethalin",
                "url": "https://sitem.herts.ac.uk/aeru/ppdb/en/Reports/525.htm",
                "retrievedAt": "2026-05-14T00:00:00Z",
                "casePackReviewedAt": "2026-05-14T00:00:00Z",
                "publisherLastReviewed": "2024-06-01",
                "retrievalMethod": "manual_web_review",
                "observedUse": (
                    "Physchem evidence: water DT50, soil DT50, log Kow, Koc, Henry's "
                    "law constant, molecular weight."
                ),
                "lockedFacts": [
                    "Pendimethalin is a dinitroaniline herbicide widely used on UK arable crops.",
                    "Pendimethalin Koc is reported as approximately 17 491 L/kg, indicating strong sorption to soil.",
                    "Pendimethalin log Kow is reported as 5.18, consistent with high hydrophobicity.",
                    "Surface-water DT50 is reported as approximately 16 days under PPDB-cited conditions.",
                    "Field soil DT50 is reported as approximately 100 days.",
                ],
            },
            {
                "sourceId": "echa.guidance.ircsa",
                "title": (
                    "ECHA Guidance on Information Requirements and Chemical Safety Assessment"
                ),
                "url": (
                    "https://echa.europa.eu/guidance-documents/guidance-on-information-"
                    "requirements-and-chemical-safety-assessment"
                ),
                "retrievedAt": "2026-05-14T00:00:00Z",
                "casePackReviewedAt": "2026-05-14T00:00:00Z",
                "publisherLastReviewed": None,
                "retrievalMethod": "manual_web_review",
                "observedUse": (
                    "Governed regional-screening default capacities (soil mass, "
                    "freshwater volume, ambient air volume) and the half-life "
                    "scaling temperature-correction policy."
                ),
                "lockedFacts": [
                    "ECHA Guidance R.16 describes regional screening environmental compartment defaults.",
                    "Temperature correction is governed against a 25 degC reference temperature.",
                ],
            },
            {
                "sourceId": "oecd.test_guidelines.section3",
                "title": "OECD Test Guidelines for the Testing of Chemicals, Section 3",
                "url": "https://www.oecd.org/en/topics/sub-issues/testing-of-chemicals/test-guidelines.html",
                "retrievedAt": "2026-05-14T00:00:00Z",
                "casePackReviewedAt": "2026-05-14T00:00:00Z",
                "publisherLastReviewed": None,
                "retrievalMethod": "manual_web_review",
                "observedUse": (
                    "Reference case family for hand-worked single-medium first-order "
                    "screening equations."
                ),
                "lockedFacts": [
                    "OECD Section 3 covers degradation and accumulation test guidelines.",
                ],
            },
            {
                "sourceId": "usda.rusle.handbook703",
                "title": "USDA Agriculture Handbook 703 - Predicting Soil Erosion by Water (RUSLE)",
                "url": "https://www.ars.usda.gov/ARSUserFiles/64080530/RUSLE/AH_703.pdf",
                "retrievedAt": "2026-05-14T00:00:00Z",
                "casePackReviewedAt": "2026-05-14T00:00:00Z",
                "publisherLastReviewed": None,
                "retrievalMethod": "manual_web_review",
                "observedUse": (
                    "Source for the RUSLE A = R x K x LS x C x P screening formulation. "
                    "Slice values for R, K, LS, C, and P are illustrative UK lowland "
                    "arable inputs, not field-measured site values."
                ),
                "lockedFacts": [
                    "RUSLE predicts annual soil loss as A = R x K x LS x C x P.",
                    "The factors are dimensionless or have published units in Handbook 703.",
                ],
            },
            {
                "sourceId": "usda.musle.williams1975",
                "title": "Williams 1975 - Sediment-yield prediction with universal equation using runoff energy factor (MUSLE)",
                "url": "https://naldc.nal.usda.gov/download/CAT87208932/PDF",
                "retrievedAt": "2026-05-14T00:00:00Z",
                "casePackReviewedAt": "2026-05-14T00:00:00Z",
                "publisherLastReviewed": None,
                "retrievalMethod": "manual_web_review",
                "observedUse": (
                    "Source for the MUSLE Y = 11.8 x (Q x q_p)^0.56 x K x LS x C x P "
                    "event sediment-yield formulation."
                ),
                "lockedFacts": [
                    "MUSLE replaces the RUSLE rainfall erosivity factor R with a runoff energy factor 11.8 x (Q x q_p)^0.56.",
                ],
            },
        ],
        "nonClaims": [
            "This slice does not reproduce EUSES, SimpleBox, ChemFate, EUFRAM, or PRZM model outputs.",
            "This slice does not execute WEPP, hydrologic routing, or channel transport.",
            "This slice does not claim regulatory acceptance, submission readiness, or source-engine equivalence.",
            "This slice does not field-validate or calibrate against UK monitoring data.",
            "This slice's R/K/LS/C/P values are illustrative UK arable inputs, not site-measured factors.",
            "This slice's MUSLE Q and q_p values are illustrative design-storm inputs, not measured runoff.",
            "This slice's region defaults are EU regional-screening surrogates; the UK has post-Brexit divergence that is not modelled in this v1 slice.",
        ],
        "screeningInputPosture": {
            "physchemPosture": "public_source_anchored_screening_fixture",
            "physchemReviewStatus": "schema_reviewed_and_source_grounded",
            "scenarioPosture": "illustrative_uk_arable_screening_scenario",
            "scenarioReviewStatus": "schema_reviewed_not_site_calibrated",
            "regionPosture": "eu_regional_screening_default_used_as_uk_proxy",
        },
    }


def _build_readme() -> str:
    return (
        "# Pendimethalin Public Worked-Case Slice (UK arable screening)\n"
        "\n"
        "This example is the canonical public worked-case slice for the Environmental "
        "Fate MCP. It demonstrates the deterministic, probabilistic, scientific review, "
        "and erosion / sediment lanes on a single coherent UK-arable pendimethalin "
        "scenario, with every input, every output, and every SHA-256 integrity hash "
        "frozen on disk.\n"
        "\n"
        "Pendimethalin (CAS 40487-42-1) is a dinitroaniline herbicide widely used on UK "
        "arable crops. Its strong sorption to soil (Koc approximately 17 491 L/kg) and "
        "moderate persistence make it a useful screening anchor for the multimedia, "
        "probabilistic, and particle-bound transport lanes of the MCP at the same time.\n"
        "\n"
        "## What it shows\n"
        "\n"
        "- Single-day, 2.5 kg total release of pendimethalin to a 2.5 ha UK winter cereal field (95% to soil, 5% to air).\n"
        "- Deterministic multimedia concentration surface (soil + air).\n"
        "- Concentration surface bundle with a frozen SHA-256 `integrity_hash`.\n"
        "- Probabilistic percentile lane (P50/P90/P95 from a 200-iteration lognormal water DT50 distribution, seed 20260514).\n"
        "- Scientific review outcome preview.\n"
        "- Regulatory handoff package with a frozen SHA-256 `integrity_hash`, ready for downstream consumption by Direct-Use Exposure MCP.\n"
        "- Erosion relevance screen (high, as expected for Koc ~ 17 491 L/kg).\n"
        "- RUSLE annual soil-loss screen.\n"
        "- MUSLE event sediment-yield screen.\n"
        "- Sediment-associated chemical-load handoff for the receiving water step.\n"
        "\n"
        "## Files\n"
        "\n"
        "- `source_lock.json`: public source anchors (FOOTPRINT PPDB, ECHA, OECD, RUSLE/MUSLE) and explicit non-claims.\n"
        "- `inputs/01_release_scenario_request.json`: the canonical scenario build request.\n"
        "- `inputs/02_run_options_deterministic.json`: deterministic run options.\n"
        "- `inputs/03_run_options_probabilistic.json`: probabilistic run options.\n"
        "- `inputs/04_probabilistic_overlay.json`: iteration count, seed, and sample-manifest mode.\n"
        "- `inputs/05_rusle_request.json`: RUSLE factors for the 2.5 ha field.\n"
        "- `inputs/06_musle_request.json`: MUSLE event inputs (525 m^3 runoff, 0.18 m^3/s peak rate).\n"
        "- `inputs/07_chemical_load_request.json`: sediment-bound chemical-load handoff inputs.\n"
        "  The erosion-relevance screen is driven directly by the scenario built from `01_release_scenario_request.json`; no separate input file is needed.\n"
        "- `outputs/01_deterministic_result.json` through `outputs/09_sediment_chemical_load_result.json`: frozen Pydantic-dumped outputs.\n"
        "- `outputs/output_summary.json`: stable numeric checkpoints and expected SHA-256 integrity hashes.\n"
        "- `limitations.md`: reviewer-facing limitations and backlog.\n"
        "\n"
        "## How to rebuild\n"
        "\n"
        "The slice is regenerated and re-verified deterministically:\n"
        "\n"
        "```bash\n"
        ".venv/bin/python scripts/generate_pendimethalin_slice.py\n"
        ".venv/bin/pytest tests/test_pendimethalin_public_slice.py -v\n"
        "```\n"
        "\n"
        "The generator script and the regression test share the same pipeline runner "
        "at `tests/_pendimethalin_slice_runner.py`, executed inside the `frozen_environment` "
        "context manager that freezes UUID factories and `datetime.now()` so the outputs "
        "are byte-identical across runs. Any drift between the generator and the test "
        "implies a non-determinism regression in the runtime.\n"
        "\n"
        "## Boundary\n"
        "\n"
        "This slice is public-source screening evidence. It is **not** a regulatory "
        "submission, **not** a site-calibrated UK assessment, and **not** a claim of "
        "source-engine equivalence to EUSES / SimpleBox / WEPP. See `limitations.md` and "
        "`source_lock.json` non-claims.\n"
    )


def _build_limitations() -> str:
    return (
        "# Limitations\n"
        "\n"
        "This case pack is a public-source slice for demonstrating Environmental Fate "
        "MCP screening. It is not a regulatory submission, calibration corpus, or "
        "source-engine reproduction.\n"
        "\n"
        "## Explicit non-claims\n"
        "\n"
        "- Physchem values are drawn from FOOTPRINT PPDB and are screening-grade inputs, not GLP studies re-extracted at row level.\n"
        "- The scenario release fractions (95% soil, 5% air) are illustrative spring application allocations, not measured drift fractions for a specific application event.\n"
        "- The 12 degC scenario temperature is a UK spring soil-temperature anchor; per-day soil temperatures vary and are not modelled in this slice.\n"
        "- The region profile (`eu_screening_default`) is a regional-screening surrogate. Post-Brexit UK regulatory divergence is not modelled in v1 of this slice.\n"
        "- The probabilistic lane uses a single lognormal envelope on soil DT50 (range approximately 33-182 d, median 100 d). Real probabilistic assessment would correlate multiple physchem inputs.\n"
        "- The P95/P50 ratio in the probabilistic soil surface is small (~1.0005). This is correct physics for a single-day release with soil DT50 = 100 d: the loss term `exp(-k*t)` over 1 day is dominated by `t`, not by half-life uncertainty. The slice exercises the probabilistic machinery (200 iterations, seeded reproducibility, sample manifests, integrity hashing) even though the underlying physics says half-life uncertainty has little leverage at this duration; this is itself a useful reviewer-facing finding.\n"
        "- The RUSLE factors (R, K, LS, C, P) are illustrative UK lowland arable inputs; they are not site-measured.\n"
        "- The MUSLE design storm (525 m^3 runoff, 0.18 m^3/s peak rate, ~21 mm of runoff across 2.5 ha) is illustrative; real assessment requires basin-specific runoff modelling.\n"
        "- The sediment-associated chemical-load handoff is a load-only contract. It does not compute a receiving-water concentration. Receiving-water concentration is out of scope and would require a downstream hydrodynamic model.\n"
        "- The scientific review outcome and recommended actions are produced by the governed review-rubric layer; they are reviewer-facing rule-based outputs, not expert review.\n"
        "- The regulatory handoff package is a downstream-MCP handoff contract, not a regulatory submission.\n"
        "\n"
        "## Backlog\n"
        "\n"
        "- Add a UK-specific region profile when one is curated.\n"
        "- Add a correlated multi-parameter probabilistic distribution (Koc plus soil DT50 plus water DT50).\n"
        "- Add a site-specific erosion case pack once an independent UK arable runoff dataset is identified.\n"
        "- Add a Level III fugacity comparison once that lane reaches reviewer-grade evidence quality.\n"
        "- Add a paired Direct-Use Exposure MCP handoff demonstration that consumes the regulatory handoff package emitted here.\n"
    )


def main() -> int:
    # Ensure existing slice contents are removed so stale files don't linger.
    if SLICE_ROOT.exists():
        for stale in sorted(SLICE_ROOT.rglob("*"), reverse=True):
            if stale.is_file():
                stale.unlink()
            elif stale.is_dir():
                stale.rmdir()
        SLICE_ROOT.rmdir()

    result = run_pipeline(REPO_ROOT)

    for filename, payload in result["inputs"].items():
        write_json(SLICE_ROOT / "inputs" / filename, payload)

    for filename, payload in result["outputs"].items():
        write_json(SLICE_ROOT / "outputs" / filename, payload)

    write_json(SLICE_ROOT / "outputs" / "output_summary.json", _build_output_summary(result["objects"]))
    write_json(SLICE_ROOT / "source_lock.json", _build_source_lock())

    (SLICE_ROOT / "README.md").write_text(_build_readme())
    (SLICE_ROOT / "limitations.md").write_text(_build_limitations())

    print(f"Generated slice at: {SLICE_ROOT}")
    print(f"  bundle.integrity_hash   = {result['objects']['bundle'].integrity_hash}")
    print(f"  handoff.integrity_hash  = {result['objects']['handoff'].integrity_hash}")
    print(f"  scenario.scenario_id    = {result['objects']['scenario'].scenario_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
