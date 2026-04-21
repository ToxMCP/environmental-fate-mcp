from __future__ import annotations

import math
from pathlib import Path

import pytest

from fate_mcp.defaults import DefaultsRegistry
from fate_mcp.models import (
    BuildEnvironmentalReleaseScenarioRequest,
    FateModelRunOptions,
    FateParameterRecord,
    Media,
    ModelFamily,
    ReleaseFraction,
    RunMode,
)
from fate_mcp.runtime import FateRuntime

REPO_ROOT = Path(__file__).resolve().parents[1]

TRACE_ABSOLUTE_TOLERANCES = {
    "emitted_mass_to_elapsed_mg": 1e-6,
    "compartment_mass_at_elapsed_mg": 1e-6,
    "cumulative_removed_mass_mg": 1e-6,
    "cumulative_degraded_mass_mg": 1e-6,
    "cumulative_advected_mass_mg": 1e-6,
    "release_stop_compartment_mass_mg": 1e-6,
    "mass_balance_closure_error_mg": 1e-9,
}

REFERENCE_ORACLE_CASES = (
    {
        "name": "reference_air_baseline",
        "medium": Media.AIR,
        "duration_days": 10.0,
        "expected_concentration": 0.0027952216417223663,
    },
    {
        "name": "reference_water_baseline",
        "medium": Media.WATER,
        "duration_days": 15.0,
        "expected_concentration": 1.4426950408889635e-05,
    },
    {
        "name": "reference_soil_baseline",
        "medium": Media.SOIL,
        "duration_days": 30.0,
        "expected_concentration": 0.0028853900817779267,
    },
    {
        "name": "reference_sediment_baseline",
        "medium": Media.SEDIMENT,
        "duration_days": 45.0,
        "expected_concentration": 0.009016844005556022,
    },
    {
        "name": "reference_water_no_decay_limit",
        "medium": Media.WATER,
        "duration_days": 1.0,
        "expected_concentration": 2e-05,
        "expected_equation_id": "finite_duration_release_no_decay_limit",
        "parameter_records": (
            {
                "parameter": "water_half_life_days",
                "value": 1e13,
                "unit": "day",
                "source_classification": "user_input",
            },
        ),
        "expected_terms": {
            "decay_constant_per_day": 6.931471805599453e-14,
            "emitted_mass_to_elapsed_mg": 10000000.0,
            "cumulative_degraded_mass_mg": 3.465735902799726e-07,
        },
    },
    {
        "name": "reference_water_temperature_correction",
        "medium": Media.WATER,
        "duration_days": 15.0,
        "temperature_c": 15.0,
        "expected_concentration": 1.6902223771686956e-05,
        "expected_terms": {
            "temperature_correction_factor": 0.5,
            "temperature_corrected_half_life_days": 30.0,
            "decay_constant_per_day": 0.023104906018664842,
            "cumulative_degraded_mass_mg": 1548888.114156522,
        },
    },
)

ADVECTIVE_ORACLE_CASES = (
    {
        "name": "advective_air_transport",
        "medium": Media.AIR,
        "duration_days": 10.0,
        "expected_concentration": 0.0014691498983410997,
        "expected_terms": {
            "degradation_loss_share_fraction": 0.5097368157955173,
            "advective_clearance_share_fraction": 0.4902631842044826,
            "elapsed_turnover_count": 3.333333333333333,
            "active_emission_turnover_count": 3.333333333333333,
            "retained_mass_fraction_of_finite_plateau": 0.9988851877078984,
            "cumulative_degraded_mass_mg": 4348488.366848473,
            "cumulative_advected_mass_mg": 4182361.734810427,
        },
    },
    {
        "name": "advective_soil_transport",
        "medium": Media.SOIL,
        "duration_days": 60.0,
        "expected_concentration": 0.0019094067279895887,
        "expected_terms": {
            "degradation_loss_share_fraction": 0.8061595923300592,
            "advective_clearance_share_fraction": 0.19384040766994082,
            "elapsed_turnover_count": 0.33333333333333337,
            "active_emission_turnover_count": 0.33333333333333337,
            "retained_mass_fraction_of_finite_plateau": 0.8208671723565526,
            "cumulative_degraded_mass_mg": 4213379.549729694,
            "cumulative_advected_mass_mg": 1013103.630296334,
        },
    },
    {
        "name": "advective_water_post_release",
        "medium": Media.WATER,
        "duration_days": 12.0,
        "elapsed_days": 20.0,
        "run_mode": RunMode.TIME_BUCKET,
        "expected_equation_id": "advective_screening_post_release_first_order_decay",
        "expected_concentration": 8.256826719727065e-07,
        "parameter_records": (
            {
                "parameter": "water_half_life_days",
                "value": 8.0,
                "unit": "day",
                "source_classification": "user_input",
            },
            {
                "parameter": "water_residence_time_days",
                "value": 6.0,
                "unit": "day",
                "source_classification": "user_input",
            },
        ),
        "expected_terms": {
            "cumulative_degraded_mass_mg": 3279238.0444729393,
            "cumulative_advected_mass_mg": 6307920.619540708,
            "post_release_elapsed_turnover_count": 1.3333333333333333,
            "post_release_retained_fraction_of_release_stop_mass": 0.1317985690578634,
            "post_release_boundary_retained_fraction_of_release_stop_mass": 0.2187424244521521,
            "post_release_half_recovery_days": 2.7363586308689225,
            "post_release_half_recovery_turnovers": 0.45605977181148705,
        },
    },
)


def _trace_term_map(surface) -> dict[str, float | str]:
    if surface.calculation_trace is None:
        return {}
    return {term.name: term.value for term in surface.calculation_trace.resolved_terms}


def _trace_absolute_tolerance(term_name: str) -> float:
    return TRACE_ABSOLUTE_TOLERANCES.get(term_name, 1e-12)


def _parameter_override_value(scenario, parameter_name: str) -> float | None:
    for record in scenario.parameter_records:
        if record.parameter == parameter_name:
            return record.value
    return None


def _temperature_adjusted_half_life(
    defaults: DefaultsRegistry,
    medium: Media,
    declared_half_life_days: float,
    scenario_temperature_c: float,
) -> tuple[float, float, float]:
    policy = defaults.temperature_correction_policy()
    effective_temperature_c = policy.clamp_temperature(scenario_temperature_c)
    temperature_correction_factor = policy.degradation_q10_by_medium[medium] ** (
        (effective_temperature_c - policy.reference_temperature_c) / 10.0
    )
    corrected_half_life_days = declared_half_life_days / temperature_correction_factor
    return corrected_half_life_days, temperature_correction_factor, effective_temperature_c


# These helpers intentionally re-derive the closed-form screening equations locally rather
# than calling plugin code, so the tests act as independent scientific oracles.
def _concentration_at_elapsed(
    release_rate_mg_per_day: float,
    capacity_value: float,
    total_loss_constant_per_day: float,
    emission_duration_days: float,
    elapsed_days: float,
) -> tuple[float, float]:
    if elapsed_days <= 0.0:
        return 0.0, 0.0
    active_emission_duration_days = min(elapsed_days, emission_duration_days)
    if total_loss_constant_per_day <= 1e-12:
        concentration = (release_rate_mg_per_day * active_emission_duration_days) / capacity_value
        return concentration, active_emission_duration_days
    concentration = (
        release_rate_mg_per_day
        / (capacity_value * total_loss_constant_per_day)
        * (1.0 - math.exp(-total_loss_constant_per_day * active_emission_duration_days))
    )
    if elapsed_days > emission_duration_days:
        concentration *= math.exp(-total_loss_constant_per_day * (elapsed_days - emission_duration_days))
    return concentration, active_emission_duration_days


def _cumulative_mass_time_integral(
    release_rate_mg_per_day: float,
    total_loss_constant_per_day: float,
    emission_duration_days: float,
    elapsed_days: float,
) -> float:
    if elapsed_days <= 0.0:
        return 0.0
    active_emission_duration_days = min(elapsed_days, emission_duration_days)
    if total_loss_constant_per_day <= 1e-12:
        during_emission_integral = 0.5 * release_rate_mg_per_day * active_emission_duration_days**2
        if elapsed_days <= emission_duration_days:
            return during_emission_integral
        release_stop_mass_mg = release_rate_mg_per_day * emission_duration_days
        return during_emission_integral + (
            release_stop_mass_mg * (elapsed_days - emission_duration_days)
        )

    during_emission_integral = (
        release_rate_mg_per_day
        / total_loss_constant_per_day
        * (
            active_emission_duration_days
            - (1.0 - math.exp(-total_loss_constant_per_day * active_emission_duration_days))
            / total_loss_constant_per_day
        )
    )
    if elapsed_days <= emission_duration_days:
        return during_emission_integral

    release_stop_mass_mg = (
        release_rate_mg_per_day
        / total_loss_constant_per_day
        * (1.0 - math.exp(-total_loss_constant_per_day * emission_duration_days))
    )
    post_release_integral = (
        release_stop_mass_mg
        * (1.0 - math.exp(-total_loss_constant_per_day * (elapsed_days - emission_duration_days)))
        / total_loss_constant_per_day
    )
    return during_emission_integral + post_release_integral


def _build_single_medium_scenario(runtime: FateRuntime, case: dict) -> object:
    parameter_records = [
        FateParameterRecord(**record) for record in case.get("parameter_records", ())
    ]
    return runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={
                "preferredName": f"Scientific oracle {case['name']}",
                "substance_class": "organic chemical",
            },
            total_release_mass_kg=case.get("total_release_mass_kg", 10.0),
            release_fractions=[ReleaseFraction(medium=case["medium"], fraction=1.0)],
            duration_days=case["duration_days"],
            temperature_c=case.get("temperature_c", 25.0),
            parameter_records=parameter_records,
        )
    )


def _estimate_single_surface(
    runtime: FateRuntime,
    scenario,
    model_family: ModelFamily,
    *,
    run_mode: RunMode = RunMode.STEADY_STATE,
    elapsed_days: float | None = None,
):
    result = runtime.estimate(
        scenario,
        FateModelRunOptions(
            region_profile_id=scenario.geographic_scope.region_id,
            model_family=model_family,
            run_mode=run_mode,
            bucket_count=1,
            bucket_duration_days=elapsed_days or 7.0,
        ),
    )
    assert len(result.surfaces) == 1
    return result.surfaces[0]


def _reference_oracle(defaults: DefaultsRegistry, scenario, medium: Media, elapsed_days: float) -> dict[str, float]:
    media_defaults = defaults.media_defaults(medium)
    region_scalar = defaults.region_scalar(
        scenario.geographic_scope.region_id,
        media_defaults.compartment,
    )
    capacity_override = _parameter_override_value(scenario, media_defaults.capacity_parameter)
    half_life_override = _parameter_override_value(
        scenario, media_defaults.degradation_half_life_parameter
    )
    capacity_value = (
        capacity_override
        if capacity_override is not None
        else defaults.parameter_value(media_defaults.capacity_parameter)
    ) * region_scalar
    declared_half_life_days = (
        half_life_override
        if half_life_override is not None
        else defaults.parameter_value(media_defaults.degradation_half_life_parameter)
    )
    corrected_half_life_days, temperature_correction_factor, effective_temperature_c = (
        _temperature_adjusted_half_life(
            defaults,
            medium,
            declared_half_life_days,
            scenario.temperature_c,
        )
    )
    decay_constant_per_day = math.log(2.0) / corrected_half_life_days
    release_rate_mg_per_day = scenario.total_release_mass_kg * 1_000_000.0 / scenario.duration_days
    raw_concentration, active_emission_duration_days = _concentration_at_elapsed(
        release_rate_mg_per_day,
        capacity_value,
        decay_constant_per_day,
        scenario.duration_days,
        elapsed_days,
    )
    emitted_mass_to_elapsed_mg = release_rate_mg_per_day * active_emission_duration_days
    compartment_mass_at_elapsed_mg = raw_concentration * capacity_value
    cumulative_degraded_mass_mg = decay_constant_per_day * _cumulative_mass_time_integral(
        release_rate_mg_per_day,
        decay_constant_per_day,
        scenario.duration_days,
        elapsed_days,
    )
    return {
        "temperature_correction_factor": temperature_correction_factor,
        "temperature_corrected_half_life_days": corrected_half_life_days,
        "effective_temperature_c": effective_temperature_c,
        "decay_constant_per_day": decay_constant_per_day,
        "emitted_mass_to_elapsed_mg": emitted_mass_to_elapsed_mg,
        "compartment_mass_at_elapsed_mg": compartment_mass_at_elapsed_mg,
        "cumulative_degraded_mass_mg": cumulative_degraded_mass_mg,
        "mass_balance_closure_error_mg": (
            emitted_mass_to_elapsed_mg
            - compartment_mass_at_elapsed_mg
            - cumulative_degraded_mass_mg
        ),
        "concentration_value": raw_concentration / 1000.0 if medium == Media.WATER else raw_concentration,
    }


def _advective_oracle(defaults: DefaultsRegistry, scenario, medium: Media, elapsed_days: float) -> dict[str, float]:
    media_defaults = defaults.media_defaults(medium)
    region_scalar = defaults.region_scalar(
        scenario.geographic_scope.region_id,
        media_defaults.compartment,
    )
    capacity_override = _parameter_override_value(scenario, media_defaults.capacity_parameter)
    half_life_override = _parameter_override_value(
        scenario, media_defaults.degradation_half_life_parameter
    )
    residence_time_override = _parameter_override_value(
        scenario, media_defaults.advective_residence_time_parameter
    )
    capacity_value = (
        capacity_override
        if capacity_override is not None
        else defaults.parameter_value(media_defaults.capacity_parameter)
    ) * region_scalar
    declared_half_life_days = (
        half_life_override
        if half_life_override is not None
        else defaults.parameter_value(media_defaults.degradation_half_life_parameter)
    )
    residence_time_days = (
        residence_time_override
        if residence_time_override is not None
        else defaults.parameter_value(media_defaults.advective_residence_time_parameter)
    )
    corrected_half_life_days, temperature_correction_factor, effective_temperature_c = (
        _temperature_adjusted_half_life(
            defaults,
            medium,
            declared_half_life_days,
            scenario.temperature_c,
        )
    )
    decay_constant_per_day = math.log(2.0) / corrected_half_life_days
    advective_constant_per_day = 1.0 / residence_time_days
    total_loss_constant_per_day = decay_constant_per_day + advective_constant_per_day
    release_rate_mg_per_day = scenario.total_release_mass_kg * 1_000_000.0 / scenario.duration_days
    raw_concentration, active_emission_duration_days = _concentration_at_elapsed(
        release_rate_mg_per_day,
        capacity_value,
        total_loss_constant_per_day,
        scenario.duration_days,
        elapsed_days,
    )
    emitted_mass_to_elapsed_mg = release_rate_mg_per_day * active_emission_duration_days
    compartment_mass_at_elapsed_mg = raw_concentration * capacity_value
    mass_time_integral = _cumulative_mass_time_integral(
        release_rate_mg_per_day,
        total_loss_constant_per_day,
        scenario.duration_days,
        elapsed_days,
    )
    cumulative_degraded_mass_mg = decay_constant_per_day * mass_time_integral
    cumulative_advected_mass_mg = advective_constant_per_day * mass_time_integral
    finite_plateau_mass_mg = release_rate_mg_per_day / total_loss_constant_per_day
    release_stop_concentration, _ = _concentration_at_elapsed(
        release_rate_mg_per_day,
        capacity_value,
        total_loss_constant_per_day,
        scenario.duration_days,
        scenario.duration_days,
    )
    release_stop_compartment_mass_mg = release_stop_concentration * capacity_value
    post_release_elapsed_days = max(elapsed_days - scenario.duration_days, 0.0)
    post_release_retained_fraction_of_release_stop_mass = (
        compartment_mass_at_elapsed_mg / release_stop_compartment_mass_mg
        if post_release_elapsed_days > 0.0 and release_stop_compartment_mass_mg > 1e-12
        else "not_applicable"
    )
    post_release_removed_fraction_of_release_stop_mass = (
        1.0 - post_release_retained_fraction_of_release_stop_mass
        if isinstance(post_release_retained_fraction_of_release_stop_mass, float)
        else "not_applicable"
    )
    degradation_loss_share_fraction = decay_constant_per_day / total_loss_constant_per_day
    advective_clearance_share_fraction = advective_constant_per_day / total_loss_constant_per_day
    return {
        "temperature_correction_factor": temperature_correction_factor,
        "temperature_corrected_half_life_days": corrected_half_life_days,
        "effective_temperature_c": effective_temperature_c,
        "decay_constant_per_day": decay_constant_per_day,
        "advective_clearance_constant_per_day": advective_constant_per_day,
        "total_loss_constant_per_day": total_loss_constant_per_day,
        "degradation_loss_share_fraction": degradation_loss_share_fraction,
        "advective_clearance_share_fraction": advective_clearance_share_fraction,
        "elapsed_turnover_count": elapsed_days * advective_constant_per_day,
        "active_emission_turnover_count": active_emission_duration_days * advective_constant_per_day,
        "retained_mass_fraction_of_finite_plateau": compartment_mass_at_elapsed_mg / finite_plateau_mass_mg,
        "emitted_mass_to_elapsed_mg": emitted_mass_to_elapsed_mg,
        "compartment_mass_at_elapsed_mg": compartment_mass_at_elapsed_mg,
        "cumulative_removed_mass_mg": cumulative_degraded_mass_mg + cumulative_advected_mass_mg,
        "cumulative_degraded_mass_mg": cumulative_degraded_mass_mg,
        "cumulative_advected_mass_mg": cumulative_advected_mass_mg,
        "release_stop_compartment_mass_mg": release_stop_compartment_mass_mg,
        "post_release_elapsed_turnover_count": (
            post_release_elapsed_days * advective_constant_per_day
            if post_release_elapsed_days > 0.0
            else "not_applicable"
        ),
        "post_release_retained_fraction_of_release_stop_mass": post_release_retained_fraction_of_release_stop_mass,
        "post_release_boundary_retained_fraction_of_release_stop_mass": (
            math.exp(-total_loss_constant_per_day * residence_time_days)
            if post_release_elapsed_days > 0.0
            else "not_applicable"
        ),
        "post_release_half_recovery_days": (
            math.log(2.0) / total_loss_constant_per_day
            if post_release_elapsed_days > 0.0
            else "not_applicable"
        ),
        "post_release_half_recovery_turnovers": (
            math.log(2.0) / total_loss_constant_per_day * advective_constant_per_day
            if post_release_elapsed_days > 0.0
            else "not_applicable"
        ),
        "post_release_removed_fraction_of_release_stop_mass": post_release_removed_fraction_of_release_stop_mass,
        "post_release_degraded_fraction_of_release_stop_mass": (
            post_release_removed_fraction_of_release_stop_mass * degradation_loss_share_fraction
            if isinstance(post_release_removed_fraction_of_release_stop_mass, float)
            else "not_applicable"
        ),
        "post_release_advected_fraction_of_release_stop_mass": (
            post_release_removed_fraction_of_release_stop_mass * advective_clearance_share_fraction
            if isinstance(post_release_removed_fraction_of_release_stop_mass, float)
            else "not_applicable"
        ),
        "mass_balance_closure_error_mg": (
            emitted_mass_to_elapsed_mg
            - compartment_mass_at_elapsed_mg
            - cumulative_degraded_mass_mg
            - cumulative_advected_mass_mg
        ),
        "concentration_value": raw_concentration / 1000.0 if medium == Media.WATER else raw_concentration,
    }


def _assert_term_matches(term_map: dict[str, float | str], oracle: dict[str, float | str], term_name: str) -> None:
    assert term_name in term_map
    assert term_name in oracle
    expected_value = oracle[term_name]
    actual_value = term_map[term_name]
    if isinstance(expected_value, str):
        assert actual_value == expected_value
        return
    assert float(actual_value) == pytest.approx(expected_value, abs=_trace_absolute_tolerance(term_name))


@pytest.mark.parametrize("case", REFERENCE_ORACLE_CASES, ids=lambda case: case["name"])
def test_reference_scientific_oracles_match_runtime(case: dict) -> None:
    runtime = FateRuntime(REPO_ROOT)
    defaults = DefaultsRegistry(REPO_ROOT)
    scenario = _build_single_medium_scenario(runtime, case)
    surface = _estimate_single_surface(
        runtime,
        scenario,
        ModelFamily.REFERENCE_MASS_BALANCE,
        run_mode=case.get("run_mode", RunMode.STEADY_STATE),
        elapsed_days=case.get("elapsed_days"),
    )
    oracle = _reference_oracle(
        defaults,
        scenario,
        case["medium"],
        case.get("elapsed_days", scenario.duration_days),
    )
    term_map = _trace_term_map(surface)

    assert surface.concentration_value == pytest.approx(case["expected_concentration"], abs=1e-12)
    assert oracle["concentration_value"] == pytest.approx(case["expected_concentration"], abs=1e-12)
    assert surface.concentration_value == pytest.approx(oracle["concentration_value"], abs=1e-12)
    _assert_term_matches(term_map, oracle, "decay_constant_per_day")
    _assert_term_matches(term_map, oracle, "emitted_mass_to_elapsed_mg")
    _assert_term_matches(term_map, oracle, "cumulative_degraded_mass_mg")
    _assert_term_matches(term_map, oracle, "mass_balance_closure_error_mg")

    for term_name, expected_value in case.get("expected_terms", {}).items():
        _assert_term_matches(term_map, oracle, term_name)
        assert float(term_map[term_name]) == pytest.approx(
            expected_value,
            abs=_trace_absolute_tolerance(term_name),
        )

    if "expected_equation_id" in case:
        assert surface.calculation_trace is not None
        assert surface.calculation_trace.equation_id == case["expected_equation_id"]


@pytest.mark.parametrize("case", ADVECTIVE_ORACLE_CASES, ids=lambda case: case["name"])
def test_advective_scientific_oracles_match_runtime(case: dict) -> None:
    runtime = FateRuntime(REPO_ROOT)
    defaults = DefaultsRegistry(REPO_ROOT)
    scenario = _build_single_medium_scenario(runtime, case)
    surface = _estimate_single_surface(
        runtime,
        scenario,
        ModelFamily.ADVECTIVE_SCREENING_MASS_BALANCE,
        run_mode=case.get("run_mode", RunMode.STEADY_STATE),
        elapsed_days=case.get("elapsed_days"),
    )
    oracle = _advective_oracle(
        defaults,
        scenario,
        case["medium"],
        case.get("elapsed_days", scenario.duration_days),
    )
    term_map = _trace_term_map(surface)

    assert surface.concentration_value == pytest.approx(case["expected_concentration"], abs=1e-12)
    assert oracle["concentration_value"] == pytest.approx(case["expected_concentration"], abs=1e-12)
    assert surface.concentration_value == pytest.approx(oracle["concentration_value"], abs=1e-12)
    _assert_term_matches(term_map, oracle, "degradation_loss_share_fraction")
    _assert_term_matches(term_map, oracle, "advective_clearance_share_fraction")
    _assert_term_matches(term_map, oracle, "cumulative_degraded_mass_mg")
    _assert_term_matches(term_map, oracle, "cumulative_advected_mass_mg")
    _assert_term_matches(term_map, oracle, "mass_balance_closure_error_mg")

    for term_name, expected_value in case.get("expected_terms", {}).items():
        _assert_term_matches(term_map, oracle, term_name)
        assert float(term_map[term_name]) == pytest.approx(
            expected_value,
            abs=_trace_absolute_tolerance(term_name),
        )

    if "expected_equation_id" in case:
        assert surface.calculation_trace is not None
        assert surface.calculation_trace.equation_id == case["expected_equation_id"]
