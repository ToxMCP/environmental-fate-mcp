from pathlib import Path

import pytest

from fate_mcp.models import (
    BuildEnvironmentalReleaseScenarioRequest,
    FateModelRunOptions,
    FateParameterRecord,
    Media,
    ModelFamily,
    ReleaseFraction,
)
from fate_mcp.runtime import FateRuntime

REPO_ROOT = Path(__file__).resolve().parents[1]


def _run_reference(scenario, options=None):
    runtime = FateRuntime(REPO_ROOT)
    opts = options or FateModelRunOptions(
        region_profile_id=scenario.geographic_scope.region_id,
        model_family=ModelFamily.REFERENCE_MASS_BALANCE,
    )
    return runtime.estimate(scenario, opts)


def _run_advective(scenario, options=None):
    runtime = FateRuntime(REPO_ROOT)
    opts = options or FateModelRunOptions(
        region_profile_id=scenario.geographic_scope.region_id,
        model_family=ModelFamily.ADVECTIVE_SCREENING_MASS_BALANCE,
    )
    return runtime.estimate(scenario, opts)


def _surface_key(surface):
    return (surface.medium.value, surface.compartment.value, surface.time_window.mode.value)


def _concentration_map(result):
    return {_surface_key(s): s.concentration_value for s in result.surfaces}


def _trace_term(surface, name):
    if surface.calculation_trace is None:
        return None
    for term in surface.calculation_trace.resolved_terms:
        if term.name == name:
            return term.value
    return None


def test_all_concentrations_are_non_negative() -> None:
    runtime = FateRuntime(REPO_ROOT)
    scenario = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={"preferredName": "Non-negative invariant", "substance_class": "organic chemical"},
            total_release_mass_kg=10.0,
            release_fractions=[ReleaseFraction(medium=Media.WATER, fraction=1.0)],
            duration_days=30.0,
        )
    )
    for model_family in [
        ModelFamily.REFERENCE_MASS_BALANCE,
        ModelFamily.ADVECTIVE_SCREENING_MASS_BALANCE,
    ]:
        result = runtime.estimate(
            scenario,
            FateModelRunOptions(
                region_profile_id=scenario.geographic_scope.region_id,
                model_family=model_family,
            ),
        )
        for surface in result.surfaces:
            assert surface.concentration_value >= 0.0, (
                f"Negative concentration for {model_family.value} "
                f"at {surface.medium.value}/{surface.compartment.value}"
            )


def test_advective_mass_balance_closes() -> None:
    runtime = FateRuntime(REPO_ROOT)
    scenario = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={"preferredName": "Mass balance invariant", "substance_class": "organic chemical"},
            total_release_mass_kg=15.0,
            release_fractions=[
                ReleaseFraction(medium=Media.WATER, fraction=0.5),
                ReleaseFraction(medium=Media.SOIL, fraction=0.5),
            ],
            duration_days=20.0,
        )
    )
    result = runtime.estimate(
        scenario,
        FateModelRunOptions(
            region_profile_id=scenario.geographic_scope.region_id,
            model_family=ModelFamily.ADVECTIVE_SCREENING_MASS_BALANCE,
        ),
    )
    for surface in result.surfaces:
        closure_error = _trace_term(surface, "mass_balance_closure_error_mg")
        if closure_error is not None:
            assert abs(float(closure_error)) < 1e-6, (
                f"Mass balance closure error too large for {surface.medium.value}/"
                f"{surface.compartment.value}: {closure_error}"
            )


def test_advection_does_not_increase_concentration() -> None:
    runtime = FateRuntime(REPO_ROOT)
    scenario = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={"preferredName": "Advection invariant", "substance_class": "organic chemical"},
            total_release_mass_kg=12.0,
            release_fractions=[
                ReleaseFraction(medium=Media.WATER, fraction=0.6),
                ReleaseFraction(medium=Media.AIR, fraction=0.4),
            ],
            duration_days=10.0,
        )
    )
    ref_result = runtime.estimate(
        scenario,
        FateModelRunOptions(
            region_profile_id=scenario.geographic_scope.region_id,
            model_family=ModelFamily.REFERENCE_MASS_BALANCE,
        ),
    )
    adv_result = runtime.estimate(
        scenario,
        FateModelRunOptions(
            region_profile_id=scenario.geographic_scope.region_id,
            model_family=ModelFamily.ADVECTIVE_SCREENING_MASS_BALANCE,
        ),
    )
    ref_map = _concentration_map(ref_result)
    adv_map = _concentration_map(adv_result)
    for key, adv_conc in adv_map.items():
        ref_conc = ref_map.get(key)
        if ref_conc is not None:
            assert adv_conc <= ref_conc * (1 + 1e-12), (
                f"Advection increased concentration at {key}: "
                f"advective={adv_conc}, reference={ref_conc}"
            )


def test_concentration_scales_linearly_with_mass() -> None:
    runtime = FateRuntime(REPO_ROOT)
    base_scenario = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={"preferredName": "Linearity invariant", "substance_class": "organic chemical"},
            total_release_mass_kg=5.0,
            release_fractions=[ReleaseFraction(medium=Media.WATER, fraction=1.0)],
            duration_days=7.0,
        )
    )
    double_scenario = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={"preferredName": "Linearity invariant", "substance_class": "organic chemical"},
            total_release_mass_kg=10.0,
            release_fractions=[ReleaseFraction(medium=Media.WATER, fraction=1.0)],
            duration_days=7.0,
        )
    )
    base_result = runtime.estimate(
        base_scenario,
        FateModelRunOptions(
            region_profile_id=base_scenario.geographic_scope.region_id,
            model_family=ModelFamily.REFERENCE_MASS_BALANCE,
        ),
    )
    double_result = runtime.estimate(
        double_scenario,
        FateModelRunOptions(
            region_profile_id=double_scenario.geographic_scope.region_id,
            model_family=ModelFamily.REFERENCE_MASS_BALANCE,
        ),
    )
    base_map = _concentration_map(base_result)
    double_map = _concentration_map(double_result)
    for key, base_conc in base_map.items():
        double_conc = double_map.get(key)
        if double_conc is not None:
            ratio = double_conc / base_conc if base_conc > 0 else 1.0
            assert ratio == pytest.approx(2.0, abs=1e-9), (
                f"Concentration did not scale linearly with mass at {key}: "
                f"ratio={ratio}, base={base_conc}, double={double_conc}"
            )


def test_shorter_half_life_yields_lower_concentration() -> None:
    runtime = FateRuntime(REPO_ROOT)
    long_scenario = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={"preferredName": "Half-life monotonicity", "substance_class": "organic chemical"},
            total_release_mass_kg=8.0,
            release_fractions=[ReleaseFraction(medium=Media.WATER, fraction=1.0)],
            duration_days=10.0,
            parameter_records=[
                FateParameterRecord(
                    parameter="water_half_life_days",
                    value=10.0,
                    unit="day",
                    source_classification="user_input",
                )
            ],
        )
    )
    short_scenario = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={"preferredName": "Half-life monotonicity", "substance_class": "organic chemical"},
            total_release_mass_kg=8.0,
            release_fractions=[ReleaseFraction(medium=Media.WATER, fraction=1.0)],
            duration_days=10.0,
            parameter_records=[
                FateParameterRecord(
                    parameter="water_half_life_days",
                    value=1.0,
                    unit="day",
                    source_classification="user_input",
                )
            ],
        )
    )
    long_result = runtime.estimate(
        long_scenario,
        FateModelRunOptions(
            region_profile_id=long_scenario.geographic_scope.region_id,
            model_family=ModelFamily.REFERENCE_MASS_BALANCE,
        ),
    )
    short_result = runtime.estimate(
        short_scenario,
        FateModelRunOptions(
            region_profile_id=short_scenario.geographic_scope.region_id,
            model_family=ModelFamily.REFERENCE_MASS_BALANCE,
        ),
    )
    long_map = _concentration_map(long_result)
    short_map = _concentration_map(short_result)
    for key, long_conc in long_map.items():
        short_conc = short_map.get(key)
        if short_conc is not None:
            assert short_conc <= long_conc * (1 + 1e-12), (
                f"Shorter half-life increased concentration at {key}: "
                f"short={short_conc}, long={long_conc}"
            )
