from pathlib import Path

import pytest

from fate_mcp.models import (
    BuildEnvironmentalReleaseScenarioRequest,
    FateModelRunOptions,
    Media,
    ModelFamily,
    ReleaseFraction,
    TreatmentAssumption,
    TreatmentExecutionMode,
)
from fate_mcp.runtime import FateRuntime


def test_reference_runtime_produces_surfaces() -> None:
    runtime = FateRuntime(Path(__file__).resolve().parents[1])
    scenario = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={"preferredName": "Example"},
            total_release_mass_kg=10.0,
            release_fractions=[
                ReleaseFraction(medium=Media.AIR, fraction=0.5),
                ReleaseFraction(medium=Media.WATER, fraction=0.5),
            ],
            duration_days=30.0,
        )
    )
    result = runtime.estimate(
        scenario,
        FateModelRunOptions(region_profile_id=scenario.geographic_scope.region_id),
    )
    assert result.run_summary.surfaces_emitted == 2
    assert {surface.medium.value for surface in result.surfaces} == {"air", "water"}
    assert all(surface.calculation_trace is not None for surface in result.surfaces)


def test_advective_runtime_adds_clearance_and_lowers_concentration() -> None:
    runtime = FateRuntime(Path(__file__).resolve().parents[1])
    scenario = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={"preferredName": "Advective example"},
            total_release_mass_kg=10.0,
            release_fractions=[ReleaseFraction(medium=Media.WATER, fraction=1.0)],
            duration_days=15.0,
        )
    )
    reference_result = runtime.estimate(
        scenario,
        FateModelRunOptions(region_profile_id=scenario.geographic_scope.region_id),
    )
    advective_result = runtime.estimate(
        scenario,
        FateModelRunOptions(
            region_profile_id=scenario.geographic_scope.region_id,
            model_family=ModelFamily.ADVECTIVE_SCREENING_MASS_BALANCE,
        ),
    )
    assert advective_result.run_summary.model_family == ModelFamily.ADVECTIVE_SCREENING_MASS_BALANCE
    assert advective_result.surfaces[0].concentration_value < reference_result.surfaces[0].concentration_value
    assert advective_result.surfaces[0].calculation_trace is not None
    assert advective_result.surfaces[0].calculation_trace.equation_id.startswith("advective_screening_")
    resolved_term_names = {
        term.name for term in advective_result.surfaces[0].calculation_trace.resolved_terms
    }
    assert "advective_clearance_constant_per_day" in resolved_term_names
    assert "total_loss_constant_per_day" in resolved_term_names
    assert "degradation_loss_share_fraction" in resolved_term_names
    assert "advective_clearance_share_fraction" in resolved_term_names
    assert "loss_dominance_margin_fraction" in resolved_term_names
    assert "combined_loss_characteristic_time_days" in resolved_term_names
    assert "emitted_mass_to_elapsed_mg" in resolved_term_names
    assert "compartment_mass_at_elapsed_mg" in resolved_term_names
    assert "cumulative_degraded_mass_mg" in resolved_term_names
    assert "cumulative_advected_mass_mg" in resolved_term_names
    assert "mass_balance_closure_error_mg" in resolved_term_names
    assert "elapsed_turnover_count" in resolved_term_names
    assert "active_emission_turnover_count" in resolved_term_names
    assert "storage_boundary_offset_turnovers" in resolved_term_names
    assert "flow_through_boundary_offset_turnovers" in resolved_term_names
    assert "retained_mass_fraction_of_finite_plateau" in resolved_term_names
    term_map = {
        term.name: term.value for term in advective_result.surfaces[0].calculation_trace.resolved_terms
    }
    assert abs(float(term_map["mass_balance_closure_error_mg"])) <= 1e-6
    assert float(term_map["elapsed_turnover_count"]) > 0.0
    assert float(term_map["retained_mass_fraction_of_finite_plateau"]) >= 0.0


def test_time_bucket_runtime_is_invariant_to_bucket_partitioning_for_same_horizon() -> None:
    runtime = FateRuntime(Path(__file__).resolve().parents[1])
    scenario = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={"preferredName": "Example"},
            total_release_mass_kg=10.0,
            release_fractions=[ReleaseFraction(medium=Media.WATER, fraction=1.0)],
            duration_days=10.0,
        )
    )
    two_bucket_result = runtime.estimate(
        scenario,
        FateModelRunOptions(
            run_mode="time_bucket",
            region_profile_id=scenario.geographic_scope.region_id,
            bucket_count=2,
            bucket_duration_days=5.0,
        ),
    )
    five_bucket_result = runtime.estimate(
        scenario,
        FateModelRunOptions(
            run_mode="time_bucket",
            region_profile_id=scenario.geographic_scope.region_id,
            bucket_count=5,
            bucket_duration_days=2.0,
        ),
    )
    assert two_bucket_result.run_summary.surfaces_emitted == 2
    assert five_bucket_result.run_summary.surfaces_emitted == 5
    assert two_bucket_result.surfaces[-1].concentration_value == pytest.approx(
        five_bucket_result.surfaces[-1].concentration_value
    )
    assert two_bucket_result.surfaces[-1].calculation_trace is not None


def test_advective_time_bucket_runtime_is_invariant_to_bucket_partitioning_for_same_horizon() -> None:
    runtime = FateRuntime(Path(__file__).resolve().parents[1])
    scenario = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={"preferredName": "Advective bucket example"},
            total_release_mass_kg=10.0,
            release_fractions=[ReleaseFraction(medium=Media.WATER, fraction=1.0)],
            duration_days=10.0,
        )
    )
    two_bucket_result = runtime.estimate(
        scenario,
        FateModelRunOptions(
            run_mode="time_bucket",
            region_profile_id=scenario.geographic_scope.region_id,
            model_family=ModelFamily.ADVECTIVE_SCREENING_MASS_BALANCE,
            bucket_count=2,
            bucket_duration_days=5.0,
        ),
    )
    five_bucket_result = runtime.estimate(
        scenario,
        FateModelRunOptions(
            run_mode="time_bucket",
            region_profile_id=scenario.geographic_scope.region_id,
            model_family=ModelFamily.ADVECTIVE_SCREENING_MASS_BALANCE,
            bucket_count=5,
            bucket_duration_days=2.0,
        ),
    )
    assert two_bucket_result.surfaces[-1].concentration_value == pytest.approx(
        five_bucket_result.surfaces[-1].concentration_value
    )
    assert two_bucket_result.surfaces[-1].calculation_trace is not None


def test_advective_post_release_runtime_emits_recovery_trace_terms() -> None:
    runtime = FateRuntime(Path(__file__).resolve().parents[1])
    scenario = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={"preferredName": "Advective post-release example"},
            total_release_mass_kg=10.0,
            release_fractions=[ReleaseFraction(medium=Media.WATER, fraction=1.0)],
            duration_days=10.0,
        )
    )
    result = runtime.estimate(
        scenario,
        FateModelRunOptions(
            run_mode="time_bucket",
            region_profile_id=scenario.geographic_scope.region_id,
            model_family=ModelFamily.ADVECTIVE_SCREENING_MASS_BALANCE,
            bucket_count=4,
            bucket_duration_days=5.0,
        ),
    )
    surface = result.surfaces[-1]
    term_map = {
        term.name: term.value for term in surface.calculation_trace.resolved_terms
    }
    assert surface.time_window.bucket_label == "bucket_4"
    assert float(term_map["post_release_elapsed_days"]) == pytest.approx(10.0)
    assert float(term_map["post_release_elapsed_turnover_count"]) > 0.0
    assert float(term_map["post_release_transition_margin_turnovers"]) == pytest.approx(
        abs(float(term_map["post_release_flushing_boundary_offset_turnovers"]))
    )
    assert 0.0 <= float(term_map["post_release_boundary_retained_fraction_of_release_stop_mass"]) <= 1.0
    assert float(term_map["post_release_retained_fraction_offset_from_boundary"]) == pytest.approx(
        float(term_map["post_release_retained_fraction_of_release_stop_mass"])
        - float(term_map["post_release_boundary_retained_fraction_of_release_stop_mass"])
    )
    assert float(term_map["post_release_retained_fraction_ratio_to_boundary"]) == pytest.approx(
        float(term_map["post_release_retained_fraction_of_release_stop_mass"])
        / float(term_map["post_release_boundary_retained_fraction_of_release_stop_mass"])
    )
    assert float(term_map["post_release_half_recovery_days"]) > 0.0
    assert float(term_map["post_release_half_recovery_turnovers"]) > 0.0
    assert float(term_map["post_release_half_recovery_offset_turnovers"]) == pytest.approx(
        float(term_map["post_release_elapsed_turnover_count"])
        - float(term_map["post_release_half_recovery_turnovers"])
    )
    assert float(term_map["post_release_half_recovery_transition_margin_turnovers"]) == pytest.approx(
        abs(float(term_map["post_release_half_recovery_offset_turnovers"]))
    )
    assert float(term_map["post_release_recovery_window_multiple_of_half_recovery"]) == pytest.approx(
        float(term_map["post_release_elapsed_turnover_count"])
        / float(term_map["post_release_half_recovery_turnovers"])
    )
    assert float(term_map["post_release_retained_fraction_offset_from_half_recovery_anchor"]) == pytest.approx(
        float(term_map["post_release_retained_fraction_of_release_stop_mass"]) - 0.5
    )
    assert float(term_map["post_release_retained_fraction_ratio_to_half_recovery_anchor"]) == pytest.approx(
        float(term_map["post_release_retained_fraction_of_release_stop_mass"]) / 0.5
    )
    assert 0.0 <= float(term_map["post_release_retained_fraction_of_release_stop_mass"]) <= 1.0
    assert 0.0 <= float(term_map["post_release_removed_fraction_of_release_stop_mass"]) <= 1.0
    assert float(term_map["post_release_removed_fraction_of_release_stop_mass"]) == pytest.approx(
        float(term_map["post_release_degraded_fraction_of_release_stop_mass"])
        + float(term_map["post_release_advected_fraction_of_release_stop_mass"])
    )


def test_executable_pre_release_treatment_reduces_concentration() -> None:
    runtime = FateRuntime(Path(__file__).resolve().parents[1])
    baseline_scenario = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={"preferredName": "Treatment example"},
            total_release_mass_kg=10.0,
            release_fractions=[ReleaseFraction(medium=Media.WATER, fraction=1.0)],
            duration_days=10.0,
        )
    )
    treated_scenario = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={"preferredName": "Treatment example"},
            total_release_mass_kg=10.0,
            release_fractions=[ReleaseFraction(medium=Media.WATER, fraction=1.0)],
            duration_days=10.0,
            treatment_assumptions=[
                TreatmentAssumption(
                    description="Executable pre-release treatment",
                    removal_fraction=0.9,
                    execution_mode=TreatmentExecutionMode.PRE_RELEASE_GLOBAL,
                )
            ],
        )
    )
    run_options = FateModelRunOptions(region_profile_id=baseline_scenario.geographic_scope.region_id)
    baseline = runtime.estimate(baseline_scenario, run_options)
    treated = runtime.estimate(treated_scenario, run_options)

    assert treated.surfaces[0].concentration_value == pytest.approx(
        baseline.surfaces[0].concentration_value * 0.1
    )
    assert any(
        assumption.parameter == "global_treatment_removal_fraction"
        for assumption in treated.assumptions
    )


def test_provenance_only_treatment_is_warned_but_not_applied() -> None:
    runtime = FateRuntime(Path(__file__).resolve().parents[1])
    baseline_scenario = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={"preferredName": "Treatment example"},
            total_release_mass_kg=10.0,
            release_fractions=[ReleaseFraction(medium=Media.WATER, fraction=1.0)],
            duration_days=10.0,
        )
    )
    provenance_only_scenario = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={"preferredName": "Treatment example"},
            total_release_mass_kg=10.0,
            release_fractions=[ReleaseFraction(medium=Media.WATER, fraction=1.0)],
            duration_days=10.0,
            treatment_assumptions=[
                TreatmentAssumption(
                    description="Recorded but unexecuted treatment",
                    removal_fraction=0.9,
                )
            ],
        )
    )
    run_options = FateModelRunOptions(region_profile_id=baseline_scenario.geographic_scope.region_id)
    baseline = runtime.estimate(baseline_scenario, run_options)
    provenance_only = runtime.estimate(provenance_only_scenario, run_options)

    assert provenance_only.surfaces[0].concentration_value == pytest.approx(
        baseline.surfaces[0].concentration_value
    )
    assert any(flag.code == "unexecuted_treatment_assumption" for flag in provenance_only.run_summary.warnings)


def test_adapter_stub_plugin_returns_normalized_outputs() -> None:
    runtime = FateRuntime(Path(__file__).resolve().parents[1])
    scenario = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={"preferredName": "Adapter example"},
            total_release_mass_kg=5.0,
            release_fractions=[ReleaseFraction(medium=Media.AIR, fraction=1.0)],
            duration_days=5.0,
        )
    )
    result = runtime.estimate(
        scenario,
        FateModelRunOptions(
            region_profile_id=scenario.geographic_scope.region_id,
            model_family=ModelFamily.ADAPTER_STUB,
        ),
    )
    assert result.run_summary.model_family == ModelFamily.ADAPTER_STUB
    assert all(surface.model_family == ModelFamily.ADAPTER_STUB for surface in result.surfaces)
