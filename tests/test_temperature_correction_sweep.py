"""Parametric tests for the governed temperature-correction policy.

Existing tests at `tests/test_runtime.py:740` and `tests/test_strict_mode.py`
cover point cases (15 degC, 25 degC, out-of-range -5 degC). This module adds
a parametric sweep across the full governed 0-40 degC range and a
quantitative cross-check that the medium-specific correction factor matches
the closed-form `Q10**((T - 25) / 10)` policy, anchored on the per-medium
Q10 values published in defaults/v1/core_defaults.json.

These tests defend the temperature-correction policy against three failure
modes the point tests cannot catch:

  1. A drift in any per-medium Q10 value (the values 1.8/2.0/2.2/2.4 for
     air/water/soil/sediment are governed and cited in the applicability
     note; a silent change would shift every non-reference run).
  2. A non-monotonic temperature response across the supported range
     (higher T should always increase degradation rate within 0-40 degC).
  3. A regression at the policy boundaries (exactly 0 degC and exactly
     40 degC must apply the correction, not clamp it).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from fate_mcp.errors import FateValidationError
from fate_mcp.models import (
    BuildEnvironmentalReleaseScenarioRequest,
    FateModelRunOptions,
    Media,
    ReleaseFraction,
    RunMode,
)
from fate_mcp.runtime import FateRuntime


REPO_ROOT = Path(__file__).resolve().parents[1]


# ----------------------------------------------------------------------------
# Closed-form policy anchor: read the published Q10 values and assert they
# match what the runtime serves. This catches silent governance drift.
# ----------------------------------------------------------------------------

EXPECTED_Q10_BY_MEDIUM: dict[Media, float] = {
    Media.AIR: 1.8,
    Media.WATER: 2.0,
    Media.SOIL: 2.2,
    Media.SEDIMENT: 2.4,
}


def test_governed_q10_values_match_published_policy() -> None:
    """The Q10 values published in core_defaults.json must be served by the
    runtime exactly as written. Catches silent drift in the governance layer."""
    runtime = FateRuntime(REPO_ROOT)
    policy = runtime.defaults.temperature_correction_policy()

    assert policy.reference_temperature_c == 25.0
    assert policy.minimum_supported_temperature_c == 0.0
    assert policy.maximum_supported_temperature_c == 40.0

    for medium, expected_q10 in EXPECTED_Q10_BY_MEDIUM.items():
        actual = policy.degradation_q10_by_medium[medium]
        assert actual == expected_q10, (
            f"Governed Q10 drift for {medium.value}: published value is {expected_q10}, "
            f"runtime served {actual}. The applicability note in core_defaults.json "
            f"and any downstream review document must move together."
        )


def _build_water_scenario(runtime: FateRuntime, *, temperature_c: float):
    return runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={
                "preferredName": "Temperature sweep substance",
                "substance_class": "organic chemical",
            },
            total_release_mass_kg=10.0,
            release_fractions=[ReleaseFraction(medium=Media.WATER, fraction=1.0)],
            duration_days=30.0,
            temperature_c=temperature_c,
            parameter_records=[
                {
                    "parameter": "water_half_life_days",
                    "value": 10.0,
                    "unit": "day",
                    "source_classification": "user_input",
                    "rationale": "Round-number DT50 pinned for temperature sweep.",
                },
            ],
        )
    )


def _water_surface_terms(runtime: FateRuntime, scenario) -> dict[str, float]:
    result = runtime.estimate(
        scenario,
        FateModelRunOptions(
            region_profile_id=scenario.geographic_scope.region_id,
            run_mode=RunMode.STEADY_STATE,
        ),
    )
    water_surface = next(s for s in result.surfaces if s.medium == Media.WATER)
    return {t.name: float(t.value) for t in water_surface.calculation_trace.resolved_terms
            if isinstance(t.value, (int, float))}, water_surface


# ----------------------------------------------------------------------------
# Quantitative formula anchor: at each temperature in the sweep, the runtime
# must compute `correction_factor == Q10**((T - 25) / 10)` exactly.
# ----------------------------------------------------------------------------

# Full sweep across the governed 0-40 degC range plus exact boundaries and
# the reference temperature.
SWEEP_TEMPERATURES_C = [0.0, 5.0, 10.0, 15.0, 20.0, 25.0, 30.0, 35.0, 40.0]


@pytest.mark.parametrize("temperature_c", SWEEP_TEMPERATURES_C)
def test_water_correction_factor_matches_q10_formula(temperature_c: float) -> None:
    """At every temperature in the governed range, the water correction factor
    must match the closed-form `Q10_water**((T - 25)/10)` exactly.

    Q10_water = 2.0 is the published value. The math is closed-form, so the
    runtime must reproduce it to within floating-point tolerance.
    """
    runtime = FateRuntime(REPO_ROOT)
    scenario = _build_water_scenario(runtime, temperature_c=temperature_c)
    terms, _ = _water_surface_terms(runtime, scenario)

    expected_factor = EXPECTED_Q10_BY_MEDIUM[Media.WATER] ** ((temperature_c - 25.0) / 10.0)
    actual_factor = terms["temperature_correction_factor"]

    assert actual_factor == pytest.approx(expected_factor, rel=1e-12, abs=0.0), (
        f"At T = {temperature_c} degC, water correction factor expected "
        f"{expected_factor!r} (= Q10_water**((T-25)/10) with Q10_water = 2.0); "
        f"got {actual_factor!r}."
    )


@pytest.mark.parametrize("temperature_c", SWEEP_TEMPERATURES_C)
def test_corrected_half_life_is_declared_half_life_divided_by_correction_factor(
    temperature_c: float,
) -> None:
    """For every supported temperature, the corrected half-life must equal
    `declared_half_life / correction_factor`. This is the policy's definition
    of how temperature correction applies, and it must hold byte-stably."""
    runtime = FateRuntime(REPO_ROOT)
    scenario = _build_water_scenario(runtime, temperature_c=temperature_c)
    terms, _ = _water_surface_terms(runtime, scenario)

    declared = terms["declared_half_life_days"]
    factor = terms["temperature_correction_factor"]
    corrected = terms["temperature_corrected_half_life_days"]

    assert corrected == pytest.approx(declared / factor, rel=1e-12, abs=0.0), (
        f"At T = {temperature_c} degC, corrected DT50 should be declared/factor "
        f"= {declared}/{factor} = {declared / factor!r}; got {corrected!r}."
    )


def test_reference_temperature_yields_unity_correction_factor() -> None:
    """At exactly 25 degC, no correction is applied and no governed limitation
    note is emitted. (The `correction_factor` term is still surfaced as 1.0 for
    auditability.)"""
    runtime = FateRuntime(REPO_ROOT)
    scenario = _build_water_scenario(runtime, temperature_c=25.0)
    terms, water_surface = _water_surface_terms(runtime, scenario)

    assert terms["temperature_correction_factor"] == pytest.approx(1.0, abs=1e-15)
    assert terms["temperature_corrected_half_life_days"] == terms["declared_half_life_days"]

    codes = {lim.code for lim in water_surface.limitations}
    assert "temperature_correction_governed" not in codes
    assert "temperature_correction_clamped_to_governed_range" not in codes


# ----------------------------------------------------------------------------
# Boundary tests: exactly 0 degC and exactly 40 degC must APPLY the correction
# (with a `temperature_correction_governed` note), not CLAMP it (which would
# emit `temperature_correction_clamped_to_governed_range`).
# ----------------------------------------------------------------------------


@pytest.mark.parametrize("temperature_c", [0.0, 40.0])
def test_boundary_temperatures_apply_correction_without_clamping(temperature_c: float) -> None:
    """At exactly the governed minimum (0 degC) and maximum (40 degC), the
    correction is applied to the declared half-life and the limitation note
    is `temperature_correction_governed`, not the clamp code."""
    runtime = FateRuntime(REPO_ROOT)
    scenario = _build_water_scenario(runtime, temperature_c=temperature_c)
    _, water_surface = _water_surface_terms(runtime, scenario)

    scenario_codes = {lim.code for lim in scenario.limitations}
    surface_codes = {lim.code for lim in water_surface.limitations}
    all_codes = scenario_codes | surface_codes

    assert "temperature_correction_governed" in all_codes, (
        f"At T = {temperature_c} degC (governed boundary), expected "
        f"'temperature_correction_governed' in limitation codes; got {sorted(all_codes)}."
    )
    assert "temperature_correction_clamped_to_governed_range" not in all_codes, (
        f"At T = {temperature_c} degC (governed boundary), the correction should be "
        f"applied, not clamped. Found 'temperature_correction_clamped_to_governed_range' "
        f"in limitation codes."
    )


@pytest.mark.parametrize("temperature_c", [-10.0, -5.0, 45.0, 50.0])
def test_out_of_range_temperatures_clamp_in_non_strict_mode(temperature_c: float) -> None:
    """Outside the governed range, non-strict mode must clamp to the nearest
    boundary and emit `temperature_correction_clamped_to_governed_range`."""
    runtime = FateRuntime(REPO_ROOT)
    scenario = _build_water_scenario(runtime, temperature_c=temperature_c)
    _, water_surface = _water_surface_terms(runtime, scenario)

    all_codes = (
        {lim.code for lim in scenario.limitations}
        | {lim.code for lim in water_surface.limitations}
    )
    assert "temperature_correction_clamped_to_governed_range" in all_codes, (
        f"At T = {temperature_c} degC (outside 0-40), expected the clamp "
        f"limitation note; got {sorted(all_codes)}."
    )

    # Effective temperature must be inside the governed range
    effective = next(
        float(t.value)
        for t in water_surface.calculation_trace.resolved_terms
        if t.name == "effective_temperature_c"
    )
    assert 0.0 <= effective <= 40.0, (
        f"Effective temperature must be clamped to [0, 40]; got {effective}."
    )


# ----------------------------------------------------------------------------
# Strict-mode rejection at the boundaries: exactly 0 / 40 must NOT be
# rejected, but anything outside must be.
# ----------------------------------------------------------------------------


@pytest.mark.parametrize("temperature_c", [0.0, 25.0, 40.0])
def test_strict_mode_accepts_governed_boundary_and_reference_temperatures(
    temperature_c: float,
) -> None:
    """Strict mode allows any temperature inside the closed [0, 40] interval."""
    runtime = FateRuntime(REPO_ROOT, strict_mode=True)
    scenario = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={"preferredName": "Boundary test", "substance_class": "organic chemical"},
            total_release_mass_kg=10.0,
            release_fractions=[ReleaseFraction(medium=Media.WATER, fraction=1.0)],
            duration_days=30.0,
            temperature_c=temperature_c,
        )
    )
    assert scenario.temperature_c == temperature_c


@pytest.mark.parametrize("temperature_c", [-0.01, 40.01, -10.0, 50.0])
def test_strict_mode_rejects_temperatures_outside_governed_range(
    temperature_c: float,
) -> None:
    """Strict mode rejects any temperature outside the closed [0, 40] interval."""
    runtime = FateRuntime(REPO_ROOT, strict_mode=True)
    with pytest.raises(FateValidationError) as exc_info:
        runtime.build_environmental_release_scenario(
            BuildEnvironmentalReleaseScenarioRequest(
                chemical_identity={"preferredName": "Out-of-range", "substance_class": "organic chemical"},
                total_release_mass_kg=10.0,
                release_fractions=[ReleaseFraction(medium=Media.WATER, fraction=1.0)],
                duration_days=30.0,
                temperature_c=temperature_c,
            )
        )
    assert exc_info.value.payload.code == "temperature_correction_clamped_to_governed_range"


# ----------------------------------------------------------------------------
# Monotonicity sweep: higher temperature must always increase the degradation
# decay constant within the governed range, so the steady-state concentration
# must decrease monotonically with temperature.
# ----------------------------------------------------------------------------


def test_water_concentration_decreases_monotonically_across_governed_range() -> None:
    """For a fixed water-release scenario with no other changes, sweeping
    temperature from 0 -> 40 degC must produce a strictly decreasing water
    concentration: warmer water -> faster first-order degradation -> lower
    end-of-duration screening concentration.

    This is the policy's primary physics claim and the closest thing to a
    closed-form anchor we have on the temperature-correction layer.
    """
    runtime = FateRuntime(REPO_ROOT)
    concentrations: list[tuple[float, float]] = []
    for temperature_c in SWEEP_TEMPERATURES_C:
        scenario = _build_water_scenario(runtime, temperature_c=temperature_c)
        _, water_surface = _water_surface_terms(runtime, scenario)
        concentrations.append((temperature_c, float(water_surface.concentration_value)))

    for (t_lo, c_lo), (t_hi, c_hi) in zip(concentrations, concentrations[1:]):
        assert c_hi < c_lo, (
            f"Water concentration is not strictly decreasing with temperature: "
            f"C({t_lo} degC) = {c_lo!r} is not greater than C({t_hi} degC) = {c_hi!r}. "
            f"The temperature-correction policy must make warmer water degrade faster."
        )


# ----------------------------------------------------------------------------
# Per-medium Q10 cross-check: confirm that the different Q10 values produce
# proportionally different correction factors. At T = 35 degC (10 above
# reference), correction_factor must equal the medium-specific Q10 exactly.
# ----------------------------------------------------------------------------


@pytest.mark.parametrize("medium", [Media.AIR, Media.WATER, Media.SOIL])
def test_per_medium_correction_factor_at_ten_degrees_above_reference_equals_q10(
    medium: Media,
) -> None:
    """At T = 35 degC (exactly 10 degC above the 25 degC reference), the
    medium-specific correction factor must equal the medium's published Q10.

    This is the cleanest scalar anchor: `Q10**((35 - 25)/10) == Q10`."""
    runtime = FateRuntime(REPO_ROOT)
    scenario = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={"preferredName": "Per-medium Q10 test", "substance_class": "organic chemical"},
            total_release_mass_kg=10.0,
            release_fractions=[ReleaseFraction(medium=medium, fraction=1.0)],
            duration_days=30.0,
            temperature_c=35.0,
            parameter_records=[
                {
                    "parameter": f"{medium.value}_half_life_days"
                    if medium != Media.AIR
                    else "air_half_life_days",
                    "value": 10.0,
                    "unit": "day",
                    "source_classification": "user_input",
                    "rationale": "Per-medium Q10 anchor.",
                },
            ],
        )
    )
    result = runtime.estimate(
        scenario,
        FateModelRunOptions(
            region_profile_id=scenario.geographic_scope.region_id,
            run_mode=RunMode.STEADY_STATE,
        ),
    )
    surface = next(s for s in result.surfaces if s.medium == medium)
    terms = {t.name: float(t.value) for t in surface.calculation_trace.resolved_terms
             if isinstance(t.value, (int, float))}

    expected_q10 = EXPECTED_Q10_BY_MEDIUM[medium]
    actual_factor = terms["temperature_correction_factor"]
    assert actual_factor == pytest.approx(expected_q10, rel=1e-12, abs=0.0), (
        f"At T = 35 degC, {medium.value} correction factor must equal Q10_{medium.value} "
        f"= {expected_q10}; got {actual_factor}."
    )
