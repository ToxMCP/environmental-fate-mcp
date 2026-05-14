"""Shared pipeline + frozen-environment helpers for the pendimethalin
public worked-case slice.

Both `scripts/generate_pendimethalin_slice.py` and
`tests/test_pendimethalin_public_slice.py` import from this module so the
generator and the regression test execute the *same* pipeline against the
*same* frozen environment. This guarantees that the frozen outputs on disk
are reproducible bit-for-bit by the test.

The frozen-environment pattern is the same as in
`tests/test_integrity_hash_stability.py`: monkeypatched UUID factory and
datetime.now sources so the integrity hash payload is a pure function of
the inputs.

Leading underscore on the filename so pytest does not collect this as a
test module.
"""

from __future__ import annotations

import json
import sys
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import patch
from uuid import UUID

from fate_mcp.integrations import (
    build_concentration_surface_bundle,
    estimate_event_sediment_yield_musle,
    estimate_sediment_associated_chemical_load,
    estimate_soil_loss_rusle,
    export_regulatory_handoff_package,
    preview_scientific_review_outcome,
    screen_erosion_transport_relevance,
)
from fate_mcp.models import (
    BuildEnvironmentalReleaseScenarioRequest,
    EstimateEventSedimentYieldMusleRequest,
    EstimateProbabilisticMultimediaConcentrationsRequest,
    EstimateSedimentAssociatedChemicalLoadRequest,
    EstimateSoilLossRusleRequest,
    ExportRegulatoryHandoffPackageRequest,
    FateModelRunOptions,
    PreviewScientificReviewOutcomeRequest,
    ScreenErosionTransportRelevanceRequest,
)
from fate_mcp.runtime import FateRuntime


# Frozen datetime used inside the slice. Pinned to the slice's lockedOn date
# at 12:00 UTC so the provenance bundles have a stable timestamp.
FROZEN_TIMESTAMP = datetime(2026, 5, 14, 12, 0, 0, tzinfo=timezone.utc)


def _deterministic_uuid_factory():
    """Counter-based UUID factory whose hex prefix is unique per call.

    `models.py` slices ``uuid4().hex[:12]`` for short IDs, which reads the
    top 48 bits of the 128-bit UUID. To make those 48 bits vary per call,
    we left-shift the counter by 80 (= 128 - 48), placing it in bytes 0-5
    where ``hex[:12]`` will see it.
    """
    counter = {"n": 0}

    def _next() -> UUID:
        counter["n"] += 1
        return UUID(int=counter["n"] << 80)

    return _next


@contextmanager
def frozen_environment():
    """Freeze every source of non-determinism the runtime stamps onto outputs.

    Within the context, repeated runs of the same pipeline yield byte-identical
    JSON outputs (and therefore byte-identical SHA-256 integrity hashes).
    Outside the context, the runtime returns to its normal behavior.

    Uses ``unittest.mock.patch`` rather than pytest's monkeypatch so this helper
    is usable from non-test code (the generator script).
    """
    uuid_factory = _deterministic_uuid_factory()

    class _FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return FROZEN_TIMESTAMP if tz is None else FROZEN_TIMESTAMP.astimezone(tz)

    with (
        patch("fate_mcp.models.uuid4", side_effect=uuid_factory),
        patch("fate_mcp.provenance.datetime", _FrozenDatetime),
        patch("fate_mcp.result_meta.datetime", _FrozenDatetime),
    ):
        yield


# ----------------------------------------------------------------------------
# Frozen input payloads. These are the canonical scenario inputs for the slice.
# They are written verbatim to examples/.../inputs/ and re-read by the
# regression test, so changing any value here is a deliberate slice revision.
# ----------------------------------------------------------------------------

# Pendimethalin (CAS 40487-42-1), physchem evidence from FOOTPRINT PPDB.
# https://sitem.herts.ac.uk/aeru/ppdb/en/Reports/525.htm
PENDIMETHALIN_PARAMETERS: list[dict[str, Any]] = [
    {
        "parameter": "water_half_life_days",
        "value": 16.0,
        "unit": "day",
        "source_classification": "user_input",
        "evidence_quality": "reference",
        "rationale": "Pendimethalin surface-water DT50 (FOOTPRINT PPDB).",
    },
    {
        "parameter": "soil_half_life_days",
        "value": 100.0,
        "unit": "day",
        "source_classification": "user_input",
        "evidence_quality": "reference",
        "rationale": "Pendimethalin field soil DT50 (FOOTPRINT PPDB).",
        "distribution": {
            "distribution_type": "lognormal",
            "parameters": {"mu": 4.61, "sigma": 0.50},
            "bounds": [33.0, 182.0],
            "sampling_basis": (
                "PPDB-reported field soil DT50 range across temperate trials "
                "(approximately 33-182 days); lognormal screening envelope "
                "with median 100 d."
            ),
        },
    },
    {
        "parameter": "air_half_life_days",
        "value": 0.45,
        "unit": "day",
        "source_classification": "user_input",
        "evidence_quality": "reference",
        "rationale": "Tropospheric OH-radical photodegradation estimate.",
    },
    {
        "parameter": "log_kow",
        "value": 5.18,
        "unit": "log10",
        "source_classification": "user_input",
        "evidence_quality": "reference",
        "rationale": "Pendimethalin log Kow (FOOTPRINT PPDB).",
    },
    {
        "parameter": "organic_carbon_partition_coefficient_koc_l_kg",
        "value": 17491.0,
        "unit": "L/kg",
        "source_classification": "user_input",
        "evidence_quality": "reference",
        "rationale": "Pendimethalin Koc (FOOTPRINT PPDB).",
    },
    {
        "parameter": "molecular_weight_g_mol",
        "value": 281.31,
        "unit": "g/mol",
        "source_classification": "user_input",
        "evidence_quality": "reference",
        "rationale": "Pendimethalin molecular weight.",
    },
    {
        "parameter": "henry_law_constant_pa_m3_mol",
        "value": 2.728,
        "unit": "Pa*m3/mol",
        "source_classification": "user_input",
        "evidence_quality": "reference",
        "rationale": "Pendimethalin Henry's law constant (FOOTPRINT PPDB).",
    },
]

PENDIMETHALIN_EVIDENCE_SOURCES: list[dict[str, Any]] = [
    {
        "source_id": "footprint.ppdb.pendimethalin",
        "title": "FOOTPRINT Pesticide Properties DataBase - Pendimethalin",
        "effective_date": "2024-06-01",
        "url": "https://sitem.herts.ac.uk/aeru/ppdb/en/Reports/525.htm",
    },
]


def build_scenario_request_payload() -> dict[str, Any]:
    """The canonical pendimethalin release-scenario request as a plain dict.

    Single coherent UK arable scenario: 1.0 kg a.s./ha x 2.5 ha applied to a
    winter cereal field on a single day at 12 degC mean UK spring soil
    temperature. 95% to soil, 5% to air (modest drift loss). This single
    scenario feeds deterministic, probabilistic, review, and erosion lanes.
    """
    return {
        "chemical_identity": {
            "preferredName": "Pendimethalin",
            "casrn": "40487-42-1",
            "substance_class": "organic chemical",
        },
        "total_release_mass_kg": 2.5,
        "release_fractions": [
            {"medium": "soil", "fraction": 0.95},
            {"medium": "air", "fraction": 0.05},
        ],
        "duration_days": 1.0,
        "region_id": "eu_screening_default",
        "context_label": "uk_arable_screening",
        "timing_pattern": "continuous",
        "treatment_assumptions": [],
        "parameter_records": PENDIMETHALIN_PARAMETERS,
        "evidence_sources": PENDIMETHALIN_EVIDENCE_SOURCES,
        "temperature_c": 12.0,
    }


def deterministic_run_options_payload() -> dict[str, Any]:
    return {
        "schema_version": "v1",
        "run_mode": "steady_state",
        "model_family": "reference_mass_balance",
        "region_profile_id": "eu_screening_default",
        "fit_for_purpose": "screening",
        "fugacity_screening_level": "level_i_equilibrium",
        "bucket_count": 1,
        "bucket_duration_days": 1.0,
        "requested_media": [],
        "escalation_concerns": [],
    }


def probabilistic_run_options_payload() -> dict[str, Any]:
    return deterministic_run_options_payload()


def probabilistic_overlay_payload() -> dict[str, Any]:
    return {
        "iterations": 200,
        "seed": 20260514,
        "sample_manifest_mode": "none",
        "sample_manifest_max_records": 1000,
    }


def rusle_request_payload() -> dict[str, Any]:
    """UK lowland arable RUSLE inputs for the 2.5 ha winter cereal field."""
    return {
        "rainfall_erosivity_r": 85.0,
        "soil_erodibility_k": 0.30,
        "slope_length_steepness_ls": 1.2,
        "cover_management_c": 0.20,
        "support_practice_p": 1.0,
        "area_ha": 2.5,
    }


def musle_request_payload() -> dict[str, Any]:
    """Single design-storm event: ~21 mm runoff across 2.5 ha."""
    return {
        "runoff_volume_m3": 525.0,
        "peak_runoff_rate_m3_s": 0.18,
        "soil_erodibility_k": 0.30,
        "slope_length_steepness_ls": 1.2,
        "cover_management_c": 0.20,
        "support_practice_p": 1.0,
    }


def chemical_load_request_payload(sediment_yield_t: float) -> dict[str, Any]:
    """Convert MUSLE sediment yield + topsoil concentration -> sediment-associated load.

    `sediment_yield_t` is the output of the MUSLE step, threaded through here
    so the chemical-load request stays self-describing.
    """
    return {
        "soil_concentration_mg_kg": 1.0,
        "sediment_yield_t": sediment_yield_t,
        "sediment_delivery_ratio": 0.35,
        "particle_bound_availability_fraction": 0.95,
    }


# ----------------------------------------------------------------------------
# Pipeline runner
# ----------------------------------------------------------------------------


def _model_dump(obj: Any) -> dict[str, Any]:
    """Pydantic model_dump in JSON mode (handles datetime, Enum, UUID)."""
    return obj.model_dump(mode="json")


def run_pipeline(repo_root: Path) -> dict[str, Any]:
    """Run the full pendimethalin pipeline under the frozen environment.

    Returns a dict with both the inputs (plain dicts that round-trip via
    Pydantic ``model_validate``) and the outputs (Pydantic-dumped JSON dicts).

    The frozen environment guarantees that two calls of ``run_pipeline`` with
    the same code and defaults return byte-identical output JSON, and
    therefore byte-identical SHA-256 integrity hashes on the bundle and the
    regulatory handoff package.
    """
    runtime = FateRuntime(repo_root)

    scenario_payload = build_scenario_request_payload()
    det_opts_payload = deterministic_run_options_payload()
    prob_opts_payload = probabilistic_run_options_payload()
    prob_overlay_payload = probabilistic_overlay_payload()
    rusle_payload = rusle_request_payload()
    musle_payload = musle_request_payload()

    with frozen_environment():
        # Step 1 -- build the typed scenario object
        scenario = runtime.build_environmental_release_scenario(
            BuildEnvironmentalReleaseScenarioRequest.model_validate(scenario_payload)
        )

        # Step 2 -- deterministic multimedia concentration estimate
        det_result = runtime.estimate(
            scenario,
            FateModelRunOptions.model_validate(det_opts_payload),
        )

        # Step 3 -- concentration surface bundle (carries SHA-256 integrity_hash)
        bundle = build_concentration_surface_bundle(det_result)

        # Step 4 -- probabilistic percentile orchestration
        prob_request = EstimateProbabilisticMultimediaConcentrationsRequest(
            scenario=scenario,
            run_options=FateModelRunOptions.model_validate(prob_opts_payload),
            **prob_overlay_payload,
        )
        prob_result = runtime.estimate_probabilistic(
            prob_request.scenario,
            prob_request.run_options,
            iterations=prob_request.iterations,
            seed=prob_request.seed,
            sample_manifest_mode=prob_request.sample_manifest_mode,
            sample_manifest_max_records=prob_request.sample_manifest_max_records,
        )

        # Step 5 -- scientific review preview
        review = preview_scientific_review_outcome(
            PreviewScientificReviewOutcomeRequest(scenario=scenario, result=det_result),
            runtime.provenance,
        )

        # Step 6 -- regulatory handoff package (carries SHA-256 integrity_hash)
        handoff = export_regulatory_handoff_package(
            ExportRegulatoryHandoffPackageRequest(result=det_result),
            runtime.provenance,
        )

        # Step 7 -- erosion / particle-bound transport relevance screen
        relevance = screen_erosion_transport_relevance(
            ScreenErosionTransportRelevanceRequest(scenario=scenario),
            runtime.provenance,
        )

        # Step 8 -- RUSLE annual soil-loss screen
        rusle = estimate_soil_loss_rusle(
            EstimateSoilLossRusleRequest.model_validate(rusle_payload),
            runtime.provenance,
        )

        # Step 9 -- MUSLE event sediment yield
        musle = estimate_event_sediment_yield_musle(
            EstimateEventSedimentYieldMusleRequest.model_validate(musle_payload),
            runtime.provenance,
        )

        # Step 10 -- sediment-associated chemical-load handoff
        chem_load_payload = chemical_load_request_payload(musle.sediment_yield_t_event)
        chem_load = estimate_sediment_associated_chemical_load(
            EstimateSedimentAssociatedChemicalLoadRequest.model_validate(chem_load_payload),
            runtime.provenance,
        )

    return {
        "inputs": {
            "01_release_scenario_request.json": scenario_payload,
            "02_run_options_deterministic.json": det_opts_payload,
            "03_run_options_probabilistic.json": prob_opts_payload,
            "04_probabilistic_overlay.json": prob_overlay_payload,
            "05_rusle_request.json": rusle_payload,
            "06_musle_request.json": musle_payload,
            "07_chemical_load_request.json": chem_load_payload,
        },
        "outputs": {
            "01_deterministic_result.json": _model_dump(det_result),
            "02_concentration_bundle.json": _model_dump(bundle),
            "03_probabilistic_result.json": _model_dump(prob_result),
            "04_scientific_review_preview.json": _model_dump(review),
            "05_regulatory_handoff_package.json": _model_dump(handoff),
            "06_erosion_relevance_result.json": _model_dump(relevance),
            "07_rusle_soil_loss_result.json": _model_dump(rusle),
            "08_musle_sediment_yield_result.json": _model_dump(musle),
            "09_sediment_chemical_load_result.json": _model_dump(chem_load),
        },
        "objects": {
            "scenario": scenario,
            "det_result": det_result,
            "bundle": bundle,
            "prob_result": prob_result,
            "review": review,
            "handoff": handoff,
            "relevance": relevance,
            "rusle": rusle,
            "musle": musle,
            "chem_load": chem_load,
        },
    }


def write_json(path: Path, obj: dict[str, Any]) -> None:
    """Write canonical JSON: indent=2, sort_keys=True, trailing newline."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


if __name__ == "__main__":  # pragma: no cover - convenience smoke
    repo_root = Path(__file__).resolve().parents[1]
    result = run_pipeline(repo_root)
    print(
        f"OK: bundle.integrity_hash = {result['objects']['bundle'].integrity_hash}\n"
        f"OK: handoff.integrity_hash = {result['objects']['handoff'].integrity_hash}\n"
        f"OK: scenario.scenario_id = {result['objects']['scenario'].scenario_id}\n",
        file=sys.stderr,
    )
