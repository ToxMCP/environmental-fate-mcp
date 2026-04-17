with open("tests/test_runtime.py", "r") as f:
    content = f.read()

new_tests = """
def test_estimate_probabilistic_runs_iterations_and_aggregates() -> None:
    from fate_mcp.models import ParameterDistribution
    runtime = FateRuntime(Path(__file__).resolve().parents[1])
    scenario = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={"preferredName": "Probabilistic example"},
            total_release_mass_kg=10.0,
            release_fractions=[ReleaseFraction(medium=Media.WATER, fraction=1.0)],
            duration_days=30.0,
        )
    )
    # Give the first parameter a distribution
    p = scenario.parameter_records[0]
    p.distribution = ParameterDistribution(
        distribution_type="uniform",
        parameters={"low": p.value * 0.5, "high": p.value * 1.5}
    )
    
    result = runtime.estimate_probabilistic(
        scenario,
        FateModelRunOptions(region_profile_id=scenario.geographic_scope.region_id),
        iterations=5,
        seed=42
    )
    
    assert result.iteration_count == 5
    assert result.completed_iteration_count == 5
    assert result.sampled_parameter_count == 1
    assert len(result.median_surfaces) == 1
    assert result.median_surfaces[0].concentration_value > 0

def test_estimate_probabilistic_fails_without_distributions() -> None:
    runtime = FateRuntime(Path(__file__).resolve().parents[1])
    scenario = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={"preferredName": "Deterministic example"},
            total_release_mass_kg=10.0,
            release_fractions=[ReleaseFraction(medium=Media.WATER, fraction=1.0)],
            duration_days=30.0,
        )
    )
    from fate_mcp.errors import FateValidationError
    import pytest
    with pytest.raises(FateValidationError) as exc:
        runtime.estimate_probabilistic(
            scenario,
            FateModelRunOptions(region_profile_id=scenario.geographic_scope.region_id),
            iterations=5
        )
    assert exc.value.payload.code == "probabilistic_orchestration_missing_distributions"
"""

if "def test_estimate_probabilistic_runs_iterations_and_aggregates" not in content:
    with open("tests/test_runtime.py", "a") as f:
        f.write(new_tests)

print("done")
