import re

with open("tests/test_external_adapter.py", "r") as f:
    content = f.read()

new_imports = """
from fate_mcp.plugins.headless import HeadlessEngineConfig, HeadlessEngineWrapper
"""

if "from fate_mcp.plugins.headless" not in content:
    content = content.replace("from fate_mcp.runtime import FateRuntime", "from fate_mcp.runtime import FateRuntime\n" + new_imports)

new_tests = """
def test_headless_engine_missing_executable() -> None:
    config = HeadlessEngineConfig(
        engine_id="nonexistent-engine",
        executable_name="missing-exe-path-12345",
        expected_version="1.0"
    )
    wrapper = HeadlessEngineWrapper(config)
    with pytest.raises(FateValidationError) as exc:
        wrapper.check_dependencies()
    assert exc.value.payload.code == "headless_engine_missing"
    assert "missing-exe-path-12345" in exc.value.payload.message


def test_headless_engine_execution_failed(tmp_path) -> None:
    config = HeadlessEngineConfig(
        engine_id="mock-engine",
        executable_name="python",  # a valid executable to pass dependency check
        expected_version="1.0"
    )
    wrapper = HeadlessEngineWrapper(config)
    
    runtime = FateRuntime(Path(__file__).resolve().parents[1])
    scenario = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={"preferredName": "Headless adapter example"},
            total_release_mass_kg=8.0,
            release_fractions=[ReleaseFraction(medium=Media.WATER, fraction=1.0)],
            duration_days=10.0,
        )
    )
    run_options = FateModelRunOptions(region_profile_id=scenario.geographic_scope.region_id)
    
    # Since we are mocking, we just let it run without creating the output file in tmp_path
    with pytest.raises(FateValidationError) as exc:
        wrapper.run(scenario, run_options, tmp_path)
    assert exc.value.payload.code == "headless_engine_execution_failed"


def test_headless_engine_bad_output(tmp_path) -> None:
    config = HeadlessEngineConfig(
        engine_id="mock-engine",
        executable_name="python",
        expected_version="1.0"
    )
    wrapper = HeadlessEngineWrapper(config)
    
    runtime = FateRuntime(Path(__file__).resolve().parents[1])
    scenario = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={"preferredName": "Headless adapter example"},
            total_release_mass_kg=8.0,
            release_fractions=[ReleaseFraction(medium=Media.WATER, fraction=1.0)],
            duration_days=10.0,
        )
    )
    run_options = FateModelRunOptions(region_profile_id=scenario.geographic_scope.region_id)
    
    # create a bad output file
    output_file = tmp_path / "output.csv"
    output_file.write_text("bad,csv,file\\n1,2,3\\n")
    
    with pytest.raises(FateValidationError) as exc:
        wrapper.run(scenario, run_options, tmp_path)
    assert exc.value.payload.code == "headless_engine_bad_output"
    assert "missing a header row" in exc.value.payload.message
"""

if "def test_headless_engine_missing_executable" not in content:
    content += new_tests

with open("tests/test_external_adapter.py", "w") as f:
    f.write(content)
