from pathlib import Path

import pytest

from fate_mcp.errors import FateValidationError
from fate_mcp.models import (
    BuildEnvironmentalReleaseScenarioRequest,
    FateModelRunOptions,
    Media,
    ModelFamily,
    ReleaseFraction,
)
from fate_mcp.plugins.external_result_adapter import (
    ExternalEngineResultPayload,
    ExternalEngineSurfacePayload,
    build_adapter_import_manifest,
    build_public_adapter_import_manifest,
    load_external_payload,
    normalize_external_payload,
    write_external_payload,
)
from fate_mcp.runtime import FateRuntime

from fate_mcp.plugins.headless import HeadlessEngineConfig, HeadlessEngineWrapper



def test_external_result_adapter_harness_plugin_returns_normalized_outputs() -> None:
    runtime = FateRuntime(Path(__file__).resolve().parents[1])
    scenario = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={"preferredName": "External adapter example", "substance_class": "organic chemical"},
            total_release_mass_kg=8.0,
            release_fractions=[ReleaseFraction(medium=Media.WATER, fraction=1.0)],
            duration_days=10.0,
        )
    )
    result = runtime.estimate(
        scenario,
        FateModelRunOptions(
            region_profile_id=scenario.geographic_scope.region_id,
            model_family=ModelFamily.EXTERNAL_RESULT_ADAPTER,
        ),
    )
    assert result.run_summary.model_family == ModelFamily.EXTERNAL_RESULT_ADAPTER
    assert all(surface.model_family == ModelFamily.EXTERNAL_RESULT_ADAPTER for surface in result.surfaces)
    assert any(item.parameter == "external_engine_name" for item in result.assumptions)


def test_external_result_adapter_rejects_unit_mismatch() -> None:
    runtime = FateRuntime(Path(__file__).resolve().parents[1])
    scenario = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={"preferredName": "External adapter example", "substance_class": "organic chemical"},
            total_release_mass_kg=8.0,
            release_fractions=[ReleaseFraction(medium=Media.WATER, fraction=1.0)],
            duration_days=10.0,
        )
    )
    payload = ExternalEngineResultPayload(
        engine_name="unit-mismatch-engine",
        engine_version="1.0",
        surfaces=[
            ExternalEngineSurfacePayload(
                compartment_code="WATER_SURFACE",
                concentration=0.5,
                unit="ppm",
                context_scope=scenario.geographic_scope.region_id,
                mode="steady_state",
                interval_start=None,
                interval_end=None,
                notes=[],
            )
        ],
    )

    with pytest.raises(FateValidationError):
        normalize_external_payload(
            payload,
            scenario,
            FateModelRunOptions(region_profile_id=scenario.geographic_scope.region_id),
            runtime.provenance,
        )


def test_external_result_adapter_fixture_can_be_loaded_and_round_tripped(tmp_path) -> None:
    runtime = FateRuntime(Path(__file__).resolve().parents[1])
    scenario = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={"preferredName": "External adapter example", "substance_class": "organic chemical"},
            total_release_mass_kg=8.0,
            release_fractions=[ReleaseFraction(medium=Media.WATER, fraction=1.0)],
            duration_days=10.0,
        )
    )
    fixture_path = Path(__file__).resolve().parents[1] / "config" / "adapter-fixtures" / "illustrative_external_engine_payload.json"
    payload = load_external_payload(fixture_path)
    result = normalize_external_payload(
        payload,
        scenario,
        FateModelRunOptions(region_profile_id=scenario.geographic_scope.region_id),
        runtime.provenance,
    )
    assert result.surfaces[0].concentration_value == pytest.approx(0.0125)

    out_path = tmp_path / "roundtrip.json"
    write_external_payload(out_path, payload)
    loaded_again = load_external_payload(out_path)
    assert loaded_again.engine_name == payload.engine_name


def test_external_result_adapter_csv_fixture_can_be_loaded_and_round_tripped(tmp_path) -> None:
    runtime = FateRuntime(Path(__file__).resolve().parents[1])
    scenario = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={"preferredName": "External adapter example", "substance_class": "organic chemical"},
            total_release_mass_kg=8.0,
            release_fractions=[ReleaseFraction(medium=Media.WATER, fraction=1.0)],
            duration_days=10.0,
        )
    )
    fixture_path = Path(__file__).resolve().parents[1] / "config" / "adapter-fixtures" / "illustrative_external_engine_payload.csv"
    payload = load_external_payload(fixture_path)
    result = normalize_external_payload(
        payload,
        scenario,
        FateModelRunOptions(region_profile_id=scenario.geographic_scope.region_id),
        runtime.provenance,
    )
    assert result.surfaces[0].concentration_value == pytest.approx(0.0125)

    out_path = tmp_path / "roundtrip.csv"
    write_external_payload(out_path, payload)
    loaded_again = load_external_payload(out_path)
    assert loaded_again.engine_version == payload.engine_version
    assert loaded_again.surfaces[0].compartment_code == "WATER_SURFACE"


def test_external_result_adapter_csv_rejects_inconsistent_engine_metadata(tmp_path) -> None:
    bad_csv = tmp_path / "bad.csv"
    bad_csv.write_text(
        "engine_name,engine_version,compartment_code,concentration,unit,context_scope,mode,interval_start,interval_end,notes\n"
        "engine-a,1.0,WATER_SURFACE,0.5,mg/L,eu_screening_default,steady_state,,,\n"
        "engine-b,1.0,SOIL_TOP,0.2,mg/kg,eu_screening_default,steady_state,,,\n"
    )

    with pytest.raises(FateValidationError):
        load_external_payload(bad_csv)


def test_external_result_adapter_legacy_desktop_export_fixture_can_be_loaded() -> None:
    runtime = FateRuntime(Path(__file__).resolve().parents[1])
    scenario = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={"preferredName": "External adapter example", "substance_class": "organic chemical"},
            total_release_mass_kg=8.0,
            release_fractions=[
                ReleaseFraction(medium=Media.AIR, fraction=0.5),
                ReleaseFraction(medium=Media.WATER, fraction=0.5),
            ],
            duration_days=10.0,
        )
    )
    fixture_path = (
        Path(__file__).resolve().parents[1]
        / "config"
        / "adapter-fixtures"
        / "legacy_screening_desktop_export.csv"
    )
    payload = load_external_payload(fixture_path)
    result = normalize_external_payload(
        payload,
        scenario,
        FateModelRunOptions(region_profile_id=scenario.geographic_scope.region_id),
        runtime.provenance,
    )
    assert payload.engine_name == "legacy-screening-desktop"
    assert {surface.compartment.value for surface in result.surfaces} == {
        "ambient_air",
        "surface_water",
    }


def test_external_result_adapter_legacy_desktop_export_rejects_unknown_compartment(tmp_path) -> None:
    bad_csv = tmp_path / "legacy_bad.csv"
    bad_csv.write_text(
        "export_type,legacy_screening_desktop_export_v1\n"
        "engine_name,legacy-screening-desktop\n"
        "engine_version,2026.04\n"
        "region_id,eu_screening_default\n"
        "\n"
        "compartment_label,bulk_concentration,bulk_unit,notes\n"
        "Unknown box,0.5,mg/L,\n"
    )

    with pytest.raises(FateValidationError):
        load_external_payload(bad_csv)


def test_external_result_adapter_legacy_time_bucket_export_fixture_can_be_loaded() -> None:
    runtime = FateRuntime(Path(__file__).resolve().parents[1])
    scenario = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={"preferredName": "External adapter time bucket example", "substance_class": "organic chemical"},
            total_release_mass_kg=8.0,
            release_fractions=[ReleaseFraction(medium=Media.WATER, fraction=1.0)],
            duration_days=14.0,
        )
    )
    fixture_path = (
        Path(__file__).resolve().parents[1]
        / "config"
        / "adapter-fixtures"
        / "legacy_screening_desktop_export_time_bucket.csv"
    )
    payload = load_external_payload(fixture_path)
    result = normalize_external_payload(
        payload,
        scenario,
        FateModelRunOptions(
            run_mode="time_bucket",
            region_profile_id=scenario.geographic_scope.region_id,
        ),
        runtime.provenance,
    )
    assert len(result.surfaces) == 2
    assert all(surface.time_window.mode.value == "time_bucket" for surface in result.surfaces)
    assert result.surfaces[0].time_window.start is not None
    assert result.surfaces[0].time_window.end is not None


def test_external_result_adapter_rejects_run_mode_mismatch() -> None:
    runtime = FateRuntime(Path(__file__).resolve().parents[1])
    scenario = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={"preferredName": "External adapter mismatch example", "substance_class": "organic chemical"},
            total_release_mass_kg=8.0,
            release_fractions=[ReleaseFraction(medium=Media.WATER, fraction=1.0)],
            duration_days=14.0,
        )
    )
    fixture_path = (
        Path(__file__).resolve().parents[1]
        / "config"
        / "adapter-fixtures"
        / "legacy_screening_desktop_export_time_bucket.csv"
    )
    payload = load_external_payload(fixture_path)

    with pytest.raises(FateValidationError):
        normalize_external_payload(
            payload,
            scenario,
            FateModelRunOptions(region_profile_id=scenario.geographic_scope.region_id),
            runtime.provenance,
        )


def test_adapter_import_manifest_lists_profiles_and_fixtures() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    manifest = build_adapter_import_manifest(repo_root)
    assert len(manifest.profiles) >= 3
    fixtures = {fixture.fixture_name: fixture for fixture in manifest.fixtures}
    assert "legacy_screening_desktop_export_weight_basis" in fixtures
    assert "legacy_screening_desktop_export_time_bucket" in fixtures
    assert fixtures["legacy_screening_desktop_export_time_bucket"].supported_modes == ["time_bucket"]
    assert "illustrative_external_engine_payload_alt_units" in fixtures


def test_public_adapter_import_manifest_exposes_only_normalized_contracts() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    manifest = build_public_adapter_import_manifest(repo_root)
    profile_ids = {profile.profile_id for profile in manifest.profiles}
    assert profile_ids == {
        "normalized_external_payload_json",
        "normalized_external_payload_csv",
    }
    assert all(profile.internal_only is False for profile in manifest.profiles)
    fixture_names = {fixture.fixture_name for fixture in manifest.fixtures}
    assert "illustrative_external_engine_payload_json" in fixture_names
    assert "illustrative_external_engine_payload_csv" in fixture_names


def test_external_result_adapter_converts_supported_units_to_canonical() -> None:
    runtime = FateRuntime(Path(__file__).resolve().parents[1])
    scenario = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={"preferredName": "External adapter conversion example", "substance_class": "organic chemical"},
            total_release_mass_kg=8.0,
            release_fractions=[ReleaseFraction(medium=Media.WATER, fraction=1.0)],
            duration_days=10.0,
        )
    )
    payload = ExternalEngineResultPayload(
        engine_name="converted-engine",
        engine_version="1.0",
        surfaces=[
            ExternalEngineSurfacePayload(
                compartment_code="WATER_SURFACE",
                concentration=12500.0,
                unit="ug/L",
                context_scope=scenario.geographic_scope.region_id,
                mode="steady_state",
                interval_start=None,
                interval_end=None,
                notes=[],
            )
        ],
    )
    result = normalize_external_payload(
        payload,
        scenario,
        FateModelRunOptions(region_profile_id=scenario.geographic_scope.region_id),
        runtime.provenance,
    )
    assert result.surfaces[0].concentration_unit == "mg/L"
    assert result.surfaces[0].concentration_value == pytest.approx(12.5)
    assert any(flag.code == "adapter_unit_conversion_applied" for flag in result.run_summary.warnings)


def test_external_result_adapter_converts_weight_basis_to_canonical_dry_weight() -> None:
    runtime = FateRuntime(Path(__file__).resolve().parents[1])
    scenario = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={"preferredName": "External adapter weight basis example", "substance_class": "organic chemical"},
            total_release_mass_kg=8.0,
            release_fractions=[
                ReleaseFraction(medium=Media.SOIL, fraction=0.5),
                ReleaseFraction(medium=Media.SEDIMENT, fraction=0.5),
            ],
            duration_days=10.0,
        )
    )
    fixture_path = (
        Path(__file__).resolve().parents[1]
        / "config"
        / "adapter-fixtures"
        / "legacy_screening_desktop_export_weight_basis.csv"
    )
    payload = load_external_payload(fixture_path)
    result = normalize_external_payload(
        payload,
        scenario,
        FateModelRunOptions(region_profile_id=scenario.geographic_scope.region_id),
        runtime.provenance,
    )

    surfaces = {surface.compartment.value: surface for surface in result.surfaces}
    assert surfaces["agricultural_soil"].concentration_unit == "mg/kg"
    assert surfaces["agricultural_soil"].concentration_value == pytest.approx(10.0)
    assert surfaces["freshwater_sediment"].concentration_unit == "mg/kg"
    assert surfaces["freshwater_sediment"].concentration_value == pytest.approx(10.0)
    assert any(flag.code == "adapter_basis_conversion_applied" for flag in result.run_summary.warnings)
    assert any(
        note.code == "adapter_basis_normalization"
        for surface in result.surfaces
        for note in surface.limitations
    )

def test_external_result_adapter_euses_export_fixture_can_be_loaded() -> None:
    runtime = FateRuntime(Path(__file__).resolve().parents[1])
    scenario = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={"preferredName": "External adapter EUSES example", "substance_class": "organic chemical"},
            total_release_mass_kg=8.0,
            release_fractions=[
                ReleaseFraction(medium=Media.AIR, fraction=0.5),
                ReleaseFraction(medium=Media.WATER, fraction=0.5),
            ],
            duration_days=10.0,
        )
    )
    fixture_path = (
        Path(__file__).resolve().parents[1]
        / "config"
        / "adapter-fixtures"
        / "euses_screening_export.csv"
    )
    payload = load_external_payload(fixture_path)
    result = normalize_external_payload(
        payload,
        scenario,
        FateModelRunOptions(region_profile_id=scenario.geographic_scope.region_id),
        runtime.provenance,
    )
    assert payload.engine_name == "euses-screening-desktop"
    assert {surface.compartment.value for surface in result.surfaces} == {
        "ambient_air",
        "surface_water",
    }


def test_external_result_adapter_epi_suite_export_fixture_is_rejected_as_non_equivalent() -> None:
    runtime = FateRuntime(Path(__file__).resolve().parents[1])
    scenario = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={"preferredName": "External adapter EPI Suite example", "substance_class": "organic chemical"},
            total_release_mass_kg=8.0,
            release_fractions=[
                ReleaseFraction(medium=Media.AIR, fraction=0.5),
                ReleaseFraction(medium=Media.WATER, fraction=0.5),
            ],
            duration_days=10.0,
        )
    )
    fixture_path = (
        Path(__file__).resolve().parents[1]
        / "config"
        / "adapter-fixtures"
        / "epi_suite_screening_export.csv"
    )
    with pytest.raises(FateValidationError) as exc_info:
        load_external_payload(fixture_path)

    assert exc_info.value.payload.code == "adapter_semantic_loss_non_equivalent"


def test_external_result_adapter_adds_limitation_for_unsupported_time_bounds() -> None:
    runtime = FateRuntime(Path(__file__).resolve().parents[1])
    scenario = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={"preferredName": "External adapter unsupported time example", "substance_class": "organic chemical"},
            total_release_mass_kg=8.0,
            release_fractions=[ReleaseFraction(medium=Media.WATER, fraction=1.0)],
            duration_days=10.0,
        )
    )
    payload = ExternalEngineResultPayload(
        engine_name="test-engine",
        engine_version="1.0",
        surfaces=[
            ExternalEngineSurfacePayload(
                compartment_code="WATER_SURFACE",
                concentration=0.5,
                unit="mg/L",
                context_scope=scenario.geographic_scope.region_id,
                mode="steady_state",
                interval_start="2026-04-01T00:00:00Z",  # unsupported bounds for steady_state
                interval_end="2026-04-02T00:00:00Z",
                notes=[],
            )
        ],
    )
    result = normalize_external_payload(
        payload,
        scenario,
        FateModelRunOptions(region_profile_id=scenario.geographic_scope.region_id),
        runtime.provenance,
    )
    
    assert len(result.surfaces) == 1
    limitations = result.surfaces[0].limitations
    assert any(note.code == "adapter_unsupported_time_bounds" for note in limitations)

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
            chemical_identity={"preferredName": "Headless adapter example", "substance_class": "organic chemical"},
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
            chemical_identity={"preferredName": "Headless adapter example", "substance_class": "organic chemical"},
            total_release_mass_kg=8.0,
            release_fractions=[ReleaseFraction(medium=Media.WATER, fraction=1.0)],
            duration_days=10.0,
        )
    )
    run_options = FateModelRunOptions(region_profile_id=scenario.geographic_scope.region_id)
    
    # create a bad output file
    output_file = tmp_path / "output.csv"
    output_file.write_text("bad,csv,file\n1,2,3\n")
    
    with pytest.raises(FateValidationError) as exc:
        wrapper.run(scenario, run_options, tmp_path)
    assert exc.value.payload.code == "headless_engine_bad_output"
    assert "metadata line is malformed" in exc.value.payload.message

def test_external_result_adapter_blocks_non_equivalent_semantic_loss(tmp_path, monkeypatch) -> None:
    from fate_mcp.models import SemanticLossClassification, AdapterSemanticMapping
    from fate_mcp.plugins.external_result_adapter import ADAPTER_IMPORT_PROFILES
    
    profile = next(p for p in ADAPTER_IMPORT_PROFILES if p.profile_id == "euses_screening_export_v1")
    monkeypatch.setattr(
        profile.semantic_mapping,
        "semantic_loss",
        SemanticLossClassification.NON_EQUIVALENT,
    )

    fixture_path = (
        Path(__file__).resolve().parents[1]
        / "config"
        / "adapter-fixtures"
        / "euses_screening_export.csv"
    )
    with pytest.raises(FateValidationError) as exc:
        load_external_payload(fixture_path)
    assert exc.value.payload.code == "adapter_semantic_loss_non_equivalent"


def test_external_result_adapter_includes_trace_disclaimer() -> None:
    runtime = FateRuntime(Path(__file__).resolve().parents[1])
    scenario = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={"preferredName": "Trace disclaimer test", "substance_class": "organic chemical"},
            total_release_mass_kg=8.0,
            release_fractions=[ReleaseFraction(medium=Media.WATER, fraction=1.0)],
            duration_days=10.0,
        )
    )
    result = runtime.estimate(
        scenario,
        FateModelRunOptions(
            region_profile_id=scenario.geographic_scope.region_id,
            model_family=ModelFamily.EXTERNAL_RESULT_ADAPTER,
        ),
    )
    for surface in result.surfaces:
        codes = [lim.code for lim in surface.limitations]
        assert "adapter_trace_disclaimer" in codes
