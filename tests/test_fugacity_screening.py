from pathlib import Path

import pytest

from fate_mcp.errors import FateValidationError
from fate_mcp.models import (
    BuildEnvironmentalReleaseScenarioRequest,
    FateParameterRecord,
    FateModelRunOptions,
    FugacityScreeningLevel,
    Media,
    ModelFamily,
    ReleaseFraction,
    ReportedTimeSemantics,
    RunMode,
    SourceClassification,
)
from fate_mcp.runtime import FateRuntime


def _runtime() -> FateRuntime:
    return FateRuntime(Path(__file__).resolve().parents[1])


def _parameter_record(parameter: str, value: float, unit: str) -> FateParameterRecord:
    return FateParameterRecord(
        parameter=parameter,
        value=value,
        unit=unit,
        source_classification=SourceClassification.USER_INPUT,
        rationale=f"Fugacity screening test parameter {parameter}.",
    )


def _scenario_request(*, parameter_records: list[FateParameterRecord] | None = None) -> BuildEnvironmentalReleaseScenarioRequest:
    return BuildEnvironmentalReleaseScenarioRequest(
        chemical_identity={
            "preferredName": "Fugacity test substance",
            "substance_class": "neutral organic chemical",
        },
        total_release_mass_kg=10.0,
        release_fractions=[
            ReleaseFraction(medium=Media.AIR, fraction=0.25),
            ReleaseFraction(medium=Media.WATER, fraction=0.25),
            ReleaseFraction(medium=Media.SOIL, fraction=0.25),
            ReleaseFraction(medium=Media.SEDIMENT, fraction=0.25),
        ],
        duration_days=30.0,
        parameter_records=parameter_records
        or [
            _parameter_record("molecular_weight_g_mol", 200.0, "g/mol"),
            _parameter_record("henry_law_constant_pa_m3_mol", 1.0, "Pa m3/mol"),
            _parameter_record("organic_carbon_partition_coefficient_koc_l_kg", 1000.0, "L/kg"),
        ],
    )


def _run_fugacity(
    runtime: FateRuntime,
    *,
    level: FugacityScreeningLevel = FugacityScreeningLevel.LEVEL_I_EQUILIBRIUM,
    requested_media: list[Media] | None = None,
):
    scenario = runtime.build_environmental_release_scenario(_scenario_request())
    return runtime.estimate(
        scenario,
        FateModelRunOptions(
            region_profile_id=scenario.geographic_scope.region_id,
            model_family=ModelFamily.FUGACITY_EQUILIBRIUM_SCREENING,
            fugacity_screening_level=level,
            requested_media=requested_media or [],
        ),
    )


def _term_map(surface) -> dict[str, float | str]:
    assert surface.calculation_trace is not None
    return {term.name: term.value for term in surface.calculation_trace.resolved_terms}


def test_fugacity_level_i_conserves_scoped_mass() -> None:
    result = _run_fugacity(_runtime())
    assert len(result.surfaces) == 4
    assert all(
        surface.reported_time_semantics
        == ReportedTimeSemantics.FUGACITY_EQUILIBRIUM_PARTITIONING
        for surface in result.surfaces
    )
    total_mass_mg = sum(float(_term_map(surface)["medium_mass_mg"]) for surface in result.surfaces)
    assert total_mass_mg == pytest.approx(10_000_000.0)
    assert sum(float(_term_map(surface)["medium_partition_fraction"]) for surface in result.surfaces) == pytest.approx(1.0)


def test_fugacity_level_i_partitioning_fixture_values() -> None:
    result = _run_fugacity(_runtime())
    by_medium = {surface.medium: surface for surface in result.surfaces}
    assert by_medium[Media.AIR].concentration_value == pytest.approx(6.832539557802613e-06)
    assert by_medium[Media.AIR].concentration_unit == "mg/m3"
    assert by_medium[Media.WATER].concentration_value == pytest.approx(0.01693757196685118)
    assert by_medium[Media.WATER].concentration_unit == "mg/m3"
    assert by_medium[Media.SOIL].concentration_value == pytest.approx(0.0003387514393370236)
    assert by_medium[Media.SOIL].concentration_unit == "mg/kg"
    assert by_medium[Media.SEDIMENT].concentration_value == pytest.approx(0.000846878598342559)
    assert by_medium[Media.SEDIMENT].concentration_unit == "mg/kg"
    assert float(_term_map(by_medium[Media.SOIL])["medium_kd_capacity_term"]) == pytest.approx(0.02)
    assert float(_term_map(by_medium[Media.SEDIMENT])["medium_kd_capacity_term"]) == pytest.approx(0.05)


def test_fugacity_requested_media_filters_outputs_not_denominator() -> None:
    runtime = _runtime()
    all_media = _run_fugacity(runtime)
    water_only = _run_fugacity(runtime, requested_media=[Media.WATER])
    all_media_water = next(surface for surface in all_media.surfaces if surface.medium == Media.WATER)
    assert len(water_only.surfaces) == 1
    assert water_only.surfaces[0].medium == Media.WATER
    assert water_only.surfaces[0].concentration_value == pytest.approx(
        all_media_water.concentration_value
    )
    assert float(_term_map(water_only.surfaces[0])["total_capacity_denominator"]) == pytest.approx(
        float(_term_map(all_media_water)["total_capacity_denominator"])
    )


def test_fugacity_level_ii_balances_input_rate_with_degradation_losses() -> None:
    result = _run_fugacity(
        _runtime(),
        level=FugacityScreeningLevel.LEVEL_II_EQUILIBRIUM_PERSISTENCE,
    )
    input_rate = float(_term_map(result.surfaces[0])["total_scoped_moles_or_rate"])
    degradation_loss = sum(
        float(_term_map(surface)["medium_degradation_loss_rate"])
        for surface in result.surfaces
    )
    assert input_rate == pytest.approx(1.6666666666666667)
    assert degradation_loss == pytest.approx(input_rate)
    water = next(surface for surface in result.surfaces if surface.medium == Media.WATER)
    assert water.concentration_value == pytest.approx(0.01332475839396872)


def test_fugacity_rejects_time_bucket_mode() -> None:
    runtime = _runtime()
    scenario = runtime.build_environmental_release_scenario(_scenario_request())
    with pytest.raises(FateValidationError, match="steady_state mode only"):
        runtime.estimate(
            scenario,
            FateModelRunOptions(
                region_profile_id=scenario.geographic_scope.region_id,
                model_family=ModelFamily.FUGACITY_EQUILIBRIUM_SCREENING,
                run_mode=RunMode.TIME_BUCKET,
            ),
        )


def test_fugacity_requires_explicit_physchem_parameters() -> None:
    runtime = _runtime()
    request = _scenario_request(
        parameter_records=[
            _parameter_record("molecular_weight_g_mol", 200.0, "g/mol"),
            _parameter_record("henry_law_constant_pa_m3_mol", 1.0, "Pa m3/mol"),
        ]
    )
    scenario = runtime.build_environmental_release_scenario(request)
    with pytest.raises(FateValidationError, match="organic_carbon_partition_coefficient_koc_l_kg"):
        runtime.estimate(
            scenario,
            FateModelRunOptions(
                region_profile_id=scenario.geographic_scope.region_id,
                model_family=ModelFamily.FUGACITY_EQUILIBRIUM_SCREENING,
            ),
        )


def test_fugacity_rejects_nonpositive_or_wrong_unit_parameters() -> None:
    runtime = _runtime()
    zero_henry = runtime.build_environmental_release_scenario(
        _scenario_request(
            parameter_records=[
                _parameter_record("molecular_weight_g_mol", 200.0, "g/mol"),
                _parameter_record("henry_law_constant_pa_m3_mol", 0.0, "Pa m3/mol"),
                _parameter_record("organic_carbon_partition_coefficient_koc_l_kg", 1000.0, "L/kg"),
            ]
        )
    )
    with pytest.raises(FateValidationError, match="finite and positive"):
        runtime.estimate(
            zero_henry,
            FateModelRunOptions(
                region_profile_id=zero_henry.geographic_scope.region_id,
                model_family=ModelFamily.FUGACITY_EQUILIBRIUM_SCREENING,
            ),
        )

    wrong_unit = runtime.build_environmental_release_scenario(
        _scenario_request(
            parameter_records=[
                _parameter_record("molecular_weight_g_mol", 200.0, "kg/mol"),
                _parameter_record("henry_law_constant_pa_m3_mol", 1.0, "Pa m3/mol"),
                _parameter_record("organic_carbon_partition_coefficient_koc_l_kg", 1000.0, "L/kg"),
            ]
        )
    )
    with pytest.raises(FateValidationError, match="expected g/mol"):
        runtime.estimate(
            wrong_unit,
            FateModelRunOptions(
                region_profile_id=wrong_unit.geographic_scope.region_id,
                model_family=ModelFamily.FUGACITY_EQUILIBRIUM_SCREENING,
            ),
        )
