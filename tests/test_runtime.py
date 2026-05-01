from pathlib import Path

import pytest

from fate_mcp.errors import FateValidationError
from fate_mcp.models import (
    BuildEnvironmentalReleaseScenarioRequest,
    FateParameterRecord,
    FateModelRunOptions,
    Media,
    ModelFamily,
    ParameterDistribution,
    ReportedTimeSemantics,
    ReleaseFraction,
    SourceClassification,
    TreatmentAssumption,
    TreatmentExecutionMode,
)
from fate_mcp.runtime import FateRuntime


def test_reference_runtime_produces_surfaces() -> None:
    runtime = FateRuntime(Path(__file__).resolve().parents[1])
    scenario = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={"preferredName": "Example", "substance_class": "organic chemical"},
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
    assert all(
        surface.reported_time_semantics
        == ReportedTimeSemantics.END_OF_DURATION_SCREENING_NOT_INFINITE_EQUILIBRIUM
        for surface in result.surfaces
    )


def test_advective_runtime_adds_clearance_and_lowers_concentration() -> None:
    runtime = FateRuntime(Path(__file__).resolve().parents[1])
    scenario = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={"preferredName": "Advective example", "substance_class": "organic chemical"},
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
    assert (
        advective_result.surfaces[0].reported_time_semantics
        == ReportedTimeSemantics.END_OF_DURATION_SCREENING_NOT_INFINITE_EQUILIBRIUM
    )
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
            chemical_identity={"preferredName": "Example", "substance_class": "organic chemical"},
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
    assert all(
        surface.reported_time_semantics == ReportedTimeSemantics.BOUNDED_TIME_BUCKET
        for surface in two_bucket_result.surfaces + five_bucket_result.surfaces
    )


def test_advective_time_bucket_runtime_is_invariant_to_bucket_partitioning_for_same_horizon() -> None:
    runtime = FateRuntime(Path(__file__).resolve().parents[1])
    scenario = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={"preferredName": "Advective bucket example", "substance_class": "organic chemical"},
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
            chemical_identity={"preferredName": "Advective post-release example", "substance_class": "organic chemical"},
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
            chemical_identity={"preferredName": "Treatment example", "substance_class": "organic chemical"},
            total_release_mass_kg=10.0,
            release_fractions=[ReleaseFraction(medium=Media.WATER, fraction=1.0)],
            duration_days=10.0,
        )
    )
    treated_scenario = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={"preferredName": "Treatment example", "substance_class": "organic chemical"},
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
            chemical_identity={"preferredName": "Treatment example", "substance_class": "organic chemical"},
            total_release_mass_kg=10.0,
            release_fractions=[ReleaseFraction(medium=Media.WATER, fraction=1.0)],
            duration_days=10.0,
        )
    )
    provenance_only_scenario = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={"preferredName": "Treatment example", "substance_class": "organic chemical"},
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


def test_multiple_pre_release_global_treatments_disclose_additive_semantics() -> None:
    runtime = FateRuntime(Path(__file__).resolve().parents[1])
    scenario = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={"preferredName": "Treatment semantics example", "substance_class": "organic chemical"},
            total_release_mass_kg=10.0,
            release_fractions=[ReleaseFraction(medium=Media.WATER, fraction=1.0)],
            duration_days=10.0,
            treatment_assumptions=[
                TreatmentAssumption(
                    description="Stage 1",
                    removal_fraction=0.2,
                    execution_mode=TreatmentExecutionMode.PRE_RELEASE_GLOBAL,
                ),
                TreatmentAssumption(
                    description="Stage 2",
                    removal_fraction=0.3,
                    execution_mode=TreatmentExecutionMode.PRE_RELEASE_GLOBAL,
                ),
            ],
        )
    )
    result = runtime.estimate(
        scenario,
        FateModelRunOptions(region_profile_id=scenario.geographic_scope.region_id),
    )
    assert any(
        note.code == "pre_release_global_treatment_additive_semantics"
        for note in result.surfaces[0].limitations
    )


def test_adapter_stub_plugin_returns_normalized_outputs() -> None:
    runtime = FateRuntime(Path(__file__).resolve().parents[1])
    scenario = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={"preferredName": "Adapter example", "substance_class": "organic chemical"},
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

def test_estimate_probabilistic_runs_iterations_and_aggregates() -> None:
    from fate_mcp.models import ParameterDistribution
    runtime = FateRuntime(Path(__file__).resolve().parents[1])
    scenario = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={"preferredName": "Probabilistic example", "substance_class": "organic chemical"},
            total_release_mass_kg=10.0,
            release_fractions=[ReleaseFraction(medium=Media.WATER, fraction=1.0)],
            duration_days=30.0,
        )
    )
    # Give the first parameter a distribution
    from fate_mcp.models import FateParameterRecord, SourceClassification
    p = FateParameterRecord(
        parameter="water_half_life_days",
        value=10.0,
        unit="day",
        source_classification=SourceClassification.USER_INPUT,
        rationale="Test"
    )
    scenario.parameter_records.append(p)
    p.distribution = ParameterDistribution(
        distribution_type="uniform",
        parameters={"low": p.value * 0.5, "high": p.value * 1.5}
    )

    result = runtime.estimate_probabilistic(
        scenario,
        FateModelRunOptions(region_profile_id=scenario.geographic_scope.region_id),
        iterations=12,
        seed=42
    )

    assert result.iteration_count == 12
    assert result.completed_iteration_count == 12
    assert result.sampled_parameter_count == 1
    assert len(result.median_surfaces) == 1
    assert result.median_surfaces[0].concentration_value > 0
    assert result.median_surfaces[0].calculation_trace is None
    assert (
        result.median_surfaces[0].reported_time_semantics
        == ReportedTimeSemantics.END_OF_DURATION_SCREENING_NOT_INFINITE_EQUILIBRIUM
    )
    assert result.p90_surfaces[0].calculation_trace is None
    assert result.p95_surfaces[0].calculation_trace is None
    assert result.median_surfaces[0].surface_id.endswith("-median")
    assert any(
        note.code == "probabilistic_surface_aggregation"
        for note in result.p95_surfaces[0].limitations
    )

def test_estimate_probabilistic_fails_without_distributions() -> None:
    runtime = FateRuntime(Path(__file__).resolve().parents[1])
    scenario = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={"preferredName": "Deterministic example", "substance_class": "organic chemical"},
            total_release_mass_kg=10.0,
            release_fractions=[ReleaseFraction(medium=Media.WATER, fraction=1.0)],
            duration_days=30.0,
        )
    )
    with pytest.raises(FateValidationError) as exc:
        runtime.estimate_probabilistic(
            scenario,
            FateModelRunOptions(region_profile_id=scenario.geographic_scope.region_id),
            iterations=5
        )
    assert exc.value.payload.code == "probabilistic_orchestration_missing_distributions"


def test_parameter_distribution_rejects_unsupported_distribution_type() -> None:
    with pytest.raises(ValueError, match="unsupported distribution_type"):
        ParameterDistribution(
            distribution_type="weird",
            parameters={},
        )


def test_estimate_probabilistic_fails_when_distribution_bounds_are_unsampleable() -> None:
    runtime = FateRuntime(Path(__file__).resolve().parents[1])
    scenario = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={"preferredName": "Probabilistic bounds example", "substance_class": "organic chemical"},
            total_release_mass_kg=10.0,
            release_fractions=[ReleaseFraction(medium=Media.WATER, fraction=1.0)],
            duration_days=30.0,
        )
    )
    scenario.parameter_records.append(
        FateParameterRecord(
            parameter="water_half_life_days",
            value=10.0,
            unit="day",
            source_classification=SourceClassification.USER_INPUT,
            rationale="Test impossible bounds",
            distribution=ParameterDistribution(
                distribution_type="uniform",
                parameters={"low": 5.0, "high": 6.0},
                bounds=[0.0, 1.0],
            ),
        )
    )

    with pytest.raises(FateValidationError) as exc:
        runtime.estimate_probabilistic(
            scenario,
            FateModelRunOptions(region_profile_id=scenario.geographic_scope.region_id),
            iterations=2,
            seed=7,
        )

    assert exc.value.payload.code == "parameter_distribution_sampling_out_of_bounds"


def test_estimate_probabilistic_is_reproducible_for_same_seed() -> None:
    runtime = FateRuntime(Path(__file__).resolve().parents[1])
    scenario = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={"preferredName": "Probabilistic reproducibility example", "substance_class": "organic chemical"},
            total_release_mass_kg=10.0,
            release_fractions=[ReleaseFraction(medium=Media.WATER, fraction=1.0)],
            duration_days=30.0,
            treatment_assumptions=[
                TreatmentAssumption(
                    description="Executable pre-release treatment",
                    removal_fraction=0.2,
                    execution_mode=TreatmentExecutionMode.PRE_RELEASE_GLOBAL,
                )
            ],
        )
    )
    scenario.parameter_records.append(
        FateParameterRecord(
            parameter="water_half_life_days",
            value=10.0,
            unit="day",
            source_classification=SourceClassification.USER_INPUT,
            rationale="Reproducibility test",
            distribution=ParameterDistribution(
                distribution_type="uniform",
                parameters={"low": 8.0, "high": 12.0},
            ),
        )
    )

    options = FateModelRunOptions(region_profile_id=scenario.geographic_scope.region_id)
    first = runtime.estimate_probabilistic(scenario, options, iterations=6, seed=19)
    second = runtime.estimate_probabilistic(scenario, options, iterations=6, seed=19)

    assert [surface.concentration_value for surface in first.median_surfaces] == pytest.approx(
        [surface.concentration_value for surface in second.median_surfaces]
    )
    first_parameters = [assumption.parameter for assumption in first.run_summary.assumptions_applied]
    second_parameters = [assumption.parameter for assumption in second.run_summary.assumptions_applied]
    assert first_parameters == second_parameters
    assert "water_half_life_days" not in first_parameters
    assert len(first_parameters) == len(set(first_parameters))


def test_non_positive_half_life_raises_validation_error() -> None:
    runtime = FateRuntime(Path(__file__).resolve().parents[1])
    scenario = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={"preferredName": "Bad half-life", "substance_class": "organic chemical"},
            total_release_mass_kg=10.0,
            release_fractions=[ReleaseFraction(medium=Media.WATER, fraction=1.0)],
            duration_days=10.0,
            parameter_records=[
                FateParameterRecord(
                    parameter="water_half_life_days",
                    value=0.0,
                    unit="day",
                    source_classification=SourceClassification.USER_INPUT,
                    rationale="Invalid zero half-life",
                )
            ],
        )
    )
    with pytest.raises(FateValidationError) as exc:
        runtime.estimate(scenario, FateModelRunOptions(region_profile_id=scenario.geographic_scope.region_id))
    assert exc.value.payload.code == "non_positive_half_life"


def test_probabilistic_iterations_are_capped() -> None:
    from fate_mcp.models import EstimateProbabilisticMultimediaConcentrationsRequest
    with pytest.raises(ValueError):
        EstimateProbabilisticMultimediaConcentrationsRequest(
            scenario={
                "chemical_identity": {"preferredName": "Cap test"},
                "total_release_mass_kg": 1.0,
                "release_fractions": [{"medium": "water", "fraction": 1.0}],
                "duration_days": 1.0,
                "geographic_scope": {"region_id": "eu_screening_default", "context_label": "test"},
                "provenance": {
                    "schema_version": "v1",
                    "defaults_version": "v1",
                    "algorithm_version": "test",
                    "generated_at": "2026-01-01T00:00:00Z",
                },
            },
            run_options={"region_profile_id": "eu_screening_default"},
            iterations=20000,
        )


def test_runtime_probabilistic_iterations_are_defensively_capped() -> None:
    runtime = FateRuntime(Path(__file__).resolve().parents[1])
    scenario = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={
                "preferredName": "Runtime cap test",
                "substance_class": "organic chemical",
            },
            total_release_mass_kg=10.0,
            release_fractions=[ReleaseFraction(medium=Media.WATER, fraction=1.0)],
            duration_days=30.0,
            parameter_records=[
                FateParameterRecord(
                    parameter="water_half_life_days",
                    value=10.0,
                    unit="day",
                    source_classification=SourceClassification.USER_INPUT,
                    rationale="Runtime cap test",
                    distribution=ParameterDistribution(
                        distribution_type="uniform",
                        parameters={"low": 8.0, "high": 12.0},
                    ),
                )
            ],
        )
    )

    with pytest.raises(FateValidationError) as exc:
        runtime.estimate_probabilistic(
            scenario,
            FateModelRunOptions(region_profile_id=scenario.geographic_scope.region_id),
            iterations=10_001,
        )

    assert exc.value.payload.code == "probabilistic_orchestration_iteration_limit_exceeded"


def test_release_fraction_sum_invariant_and_unallocated_warning() -> None:
    runtime = FateRuntime(Path(__file__).resolve().parents[1])
    accepted = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={
                "preferredName": "Accepted fraction sum",
                "substance_class": "organic chemical",
            },
            total_release_mass_kg=1.0,
            release_fractions=[ReleaseFraction(medium=Media.WATER, fraction=1.0)],
            duration_days=1.0,
        )
    )
    assert sum(item.fraction for item in accepted.release_fractions) == pytest.approx(1.0)

    partial = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={
                "preferredName": "Partial fraction sum",
                "substance_class": "organic chemical",
            },
            total_release_mass_kg=1.0,
            release_fractions=[ReleaseFraction(medium=Media.WATER, fraction=0.8)],
            duration_days=1.0,
        )
    )
    assert any(flag.code == "unallocated_release_fraction" for flag in partial.quality_flags)

    with pytest.raises(ValueError, match="release fractions must sum to 1.0 or less"):
        runtime.build_environmental_release_scenario(
            BuildEnvironmentalReleaseScenarioRequest(
                chemical_identity={
                    "preferredName": "Invalid fraction sum",
                    "substance_class": "organic chemical",
                },
                total_release_mass_kg=1.0,
                release_fractions=[
                    ReleaseFraction(medium=Media.WATER, fraction=0.8),
                    ReleaseFraction(medium=Media.SOIL, fraction=0.3),
                ],
                duration_days=1.0,
            )
        )


def test_non_default_temperature_adds_governed_correction_note() -> None:
    runtime = FateRuntime(Path(__file__).resolve().parents[1])
    scenario = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={"preferredName": "Temperature test", "substance_class": "organic chemical"},
            total_release_mass_kg=1.0,
            release_fractions=[ReleaseFraction(medium=Media.WATER, fraction=1.0)],
            duration_days=1.0,
            temperature_c=15.0,
        )
    )
    assert scenario.temperature_c == 15.0
    codes = [lim.code for lim in scenario.limitations]
    assert "temperature_correction_governed" in codes


def test_default_temperature_has_no_limitation_note() -> None:
    runtime = FateRuntime(Path(__file__).resolve().parents[1])
    scenario = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={"preferredName": "Default temp test", "substance_class": "organic chemical"},
            total_release_mass_kg=1.0,
            release_fractions=[ReleaseFraction(medium=Media.WATER, fraction=1.0)],
            duration_days=1.0,
        )
    )
    assert scenario.temperature_c == 25.0
    codes = [lim.code for lim in scenario.limitations]
    assert "temperature_correction_governed" not in codes


def test_lower_temperature_increases_reference_concentration_due_to_governed_half_life_adjustment() -> None:
    runtime = FateRuntime(Path(__file__).resolve().parents[1])
    baseline = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={"preferredName": "Temperature baseline", "substance_class": "organic chemical"},
            total_release_mass_kg=1.0,
            release_fractions=[ReleaseFraction(medium=Media.WATER, fraction=1.0)],
            duration_days=10.0,
            temperature_c=25.0,
        )
    )
    cooler = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={"preferredName": "Temperature cooler", "substance_class": "organic chemical"},
            total_release_mass_kg=1.0,
            release_fractions=[ReleaseFraction(medium=Media.WATER, fraction=1.0)],
            duration_days=10.0,
            temperature_c=15.0,
        )
    )

    baseline_result = runtime.estimate(
        baseline,
        FateModelRunOptions(region_profile_id=baseline.geographic_scope.region_id),
    )
    cooler_result = runtime.estimate(
        cooler,
        FateModelRunOptions(region_profile_id=cooler.geographic_scope.region_id),
    )

    assert cooler_result.surfaces[0].concentration_value > baseline_result.surfaces[0].concentration_value
    term_map = {
        term.name: term.value for term in cooler_result.surfaces[0].calculation_trace.resolved_terms
    }
    assert float(term_map["temperature_correction_factor"]) < 1.0
    assert float(term_map["temperature_corrected_half_life_days"]) > float(term_map["declared_half_life_days"])


def test_temperature_outside_governed_range_adds_clamp_note_in_non_strict_mode() -> None:
    runtime = FateRuntime(Path(__file__).resolve().parents[1], strict_mode=False)
    scenario = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={"preferredName": "Temperature clamp test", "substance_class": "organic chemical"},
            total_release_mass_kg=1.0,
            release_fractions=[ReleaseFraction(medium=Media.WATER, fraction=1.0)],
            duration_days=10.0,
            temperature_c=-5.0,
        )
    )
    codes = [lim.code for lim in scenario.limitations]
    assert "temperature_correction_clamped_to_governed_range" in codes


def test_reconciliation_thresholds_loaded_from_defaults() -> None:
    runtime = FateRuntime(Path(__file__).resolve().parents[1])
    assert runtime.defaults.reconciliation_threshold("mass_relative_spread") == 0.25
    assert runtime.defaults.reconciliation_threshold("fraction_absolute_spread") == 0.15
    assert runtime.defaults.reconciliation_threshold("vector_cosine_similarity") == 0.9


def test_non_positive_residence_time_raises_validation_error() -> None:
    runtime = FateRuntime(Path(__file__).resolve().parents[1])
    scenario = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={"preferredName": "Advective residence time test", "substance_class": "organic chemical"},
            total_release_mass_kg=10.0,
            release_fractions=[ReleaseFraction(medium=Media.WATER, fraction=1.0)],
            duration_days=10.0,
            parameter_records=[
                FateParameterRecord(
                    parameter="water_residence_time_days",
                    value=0.0,
                    unit="day",
                    source_classification="user_input",
                )
            ],
        )
    )
    with pytest.raises(FateValidationError) as exc_info:
        runtime.estimate(
            scenario,
            FateModelRunOptions(
                region_profile_id=scenario.geographic_scope.region_id,
                model_family=ModelFamily.ADVECTIVE_SCREENING_MASS_BALANCE,
            ),
        )
    assert exc_info.value.payload.code == "non_positive_residence_time"
