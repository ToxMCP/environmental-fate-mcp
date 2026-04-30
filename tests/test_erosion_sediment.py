from pathlib import Path

import pytest

from fate_mcp.integrations import (
    estimate_event_sediment_yield_musle,
    estimate_sediment_associated_chemical_load,
    estimate_soil_loss_rusle,
    screen_erosion_transport_relevance,
)
from fate_mcp.models import (
    BuildEnvironmentalReleaseScenarioRequest,
    EstimateEventSedimentYieldMusleRequest,
    EstimateSedimentAssociatedChemicalLoadRequest,
    EstimateSoilLossRusleRequest,
    FateParameterRecord,
    Media,
    ReleaseFraction,
    ScreenErosionTransportRelevanceRequest,
    SourceClassification,
)
from fate_mcp.runtime import FateRuntime


REPO_ROOT = Path(__file__).resolve().parents[1]


def _runtime() -> FateRuntime:
    return FateRuntime(REPO_ROOT)


def _scenario_with_parameter(parameter: str | None = None, value: float | None = None):
    parameter_records = []
    if parameter is not None and value is not None:
        parameter_records.append(
            FateParameterRecord(
                parameter=parameter,
                value=value,
                unit="L/kg" if parameter.lower().startswith(("koc", "kd")) else "log10",
                source_classification=SourceClassification.USER_INPUT,
                rationale="Test particle-bound transport descriptor.",
            )
        )
    return _runtime().build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={
                "preferredName": "Example substance",
                "substance_class": "organic chemical",
            },
            total_release_mass_kg=1.0,
            release_fractions=[ReleaseFraction(medium=Media.SOIL, fraction=1.0)],
            duration_days=1.0,
            parameter_records=parameter_records,
        )
    )


def test_rusle_calculation_returns_rate_and_area_total() -> None:
    runtime = _runtime()
    request = EstimateSoilLossRusleRequest(
        rainfall_erosivity_r=150.0,
        soil_erodibility_k=0.28,
        slope_length_steepness_ls=1.6,
        cover_management_c=0.12,
        support_practice_p=0.8,
        area_ha=2.5,
    )
    result = estimate_soil_loss_rusle(request, runtime.provenance)

    assert result.annual_soil_loss_t_ha_yr == pytest.approx(6.4512)
    assert result.total_soil_loss_t_yr == pytest.approx(16.128)
    assert result.calculation_trace.equation_id == "rusle_v1"
    assert result.provenance.source_references[0].source_id == "usda.nrcs.rusle.efotg"


def test_musle_calculation_uses_caller_supplied_hydrology() -> None:
    runtime = _runtime()
    request = EstimateEventSedimentYieldMusleRequest(
        runoff_volume_m3=1200.0,
        peak_runoff_rate_m3_s=2.4,
        soil_erodibility_k=0.28,
        slope_length_steepness_ls=1.6,
        cover_management_c=0.12,
        support_practice_p=0.8,
    )
    result = estimate_event_sediment_yield_musle(request, runtime.provenance)
    expected = 11.8 * (1200.0 * 2.4) ** 0.56 * 0.28 * 1.6 * 0.12 * 0.8

    assert result.sediment_yield_t_event == pytest.approx(expected)
    assert result.calculation_trace.equation_id == "musle_metric_v1"
    assert any("does not compute rainfall-runoff" in note for note in result.calculation_trace.notes)


def test_sediment_associated_chemical_load_conversion() -> None:
    runtime = _runtime()
    request = EstimateSedimentAssociatedChemicalLoadRequest(
        soil_concentration_mg_kg=2.5,
        sediment_yield_t=40.0,
        sediment_delivery_ratio=0.35,
        particle_bound_availability_fraction=0.75,
    )
    result = estimate_sediment_associated_chemical_load(request, runtime.provenance)

    assert result.sediment_associated_load_kg == pytest.approx(0.02625)
    assert result.calculation_trace.equation_id == "sediment_associated_chemical_load_screening_v1"
    assert any("not a receiving-water concentration" in note for note in result.handoff_notes)


def test_zero_inputs_return_zero_with_quality_flag() -> None:
    runtime = _runtime()
    rusle = estimate_soil_loss_rusle(
        EstimateSoilLossRusleRequest(
            rainfall_erosivity_r=0.0,
            soil_erodibility_k=0.28,
            slope_length_steepness_ls=1.6,
            cover_management_c=0.12,
            support_practice_p=0.8,
        ),
        runtime.provenance,
    )
    musle = estimate_event_sediment_yield_musle(
        EstimateEventSedimentYieldMusleRequest(
            runoff_volume_m3=0.0,
            peak_runoff_rate_m3_s=2.4,
            soil_erodibility_k=0.28,
            slope_length_steepness_ls=1.6,
            cover_management_c=0.12,
            support_practice_p=0.8,
        ),
        runtime.provenance,
    )

    assert rusle.annual_soil_loss_t_ha_yr == 0.0
    assert musle.sediment_yield_t_event == 0.0
    assert rusle.quality_flags[0].code == "zero_erosion_transport_factor"
    assert musle.quality_flags[0].code == "zero_erosion_transport_factor"


def test_input_validation_rejects_nonfinite_and_out_of_range_values() -> None:
    with pytest.raises(ValueError, match="must be finite"):
        EstimateSoilLossRusleRequest(
            rainfall_erosivity_r=float("inf"),
            soil_erodibility_k=0.28,
            slope_length_steepness_ls=1.6,
            cover_management_c=0.12,
            support_practice_p=0.8,
        )
    with pytest.raises(ValueError):
        EstimateSedimentAssociatedChemicalLoadRequest(
            soil_concentration_mg_kg=2.5,
            sediment_yield_t=40.0,
            sediment_delivery_ratio=1.1,
            particle_bound_availability_fraction=0.75,
        )


def test_erosion_transport_relevance_thresholds() -> None:
    runtime = _runtime()
    high = screen_erosion_transport_relevance(
        ScreenErosionTransportRelevanceRequest(scenario=_scenario_with_parameter("koc", 1200.0)),
        runtime.provenance,
    )
    medium = screen_erosion_transport_relevance(
        ScreenErosionTransportRelevanceRequest(scenario=_scenario_with_parameter("log_kow", 3.4)),
        runtime.provenance,
    )
    low = screen_erosion_transport_relevance(
        ScreenErosionTransportRelevanceRequest(scenario=_scenario_with_parameter("log_kow", 2.2)),
        runtime.provenance,
    )
    unknown = screen_erosion_transport_relevance(
        ScreenErosionTransportRelevanceRequest(scenario=_scenario_with_parameter()),
        runtime.provenance,
    )

    assert high.relevance_level.value == "high"
    assert medium.relevance_level.value == "medium"
    assert low.relevance_level.value == "low"
    assert unknown.relevance_level.value == "unknown"
    assert unknown.particle_bound_transport_plausible is None
    assert unknown.quality_flags[0].code == "missing_particle_transport_evidence"
