from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from fate_mcp.benchmarks import benchmark_manifest, run_benchmarks, scientific_validation_claim_coverage_manifest
from fate_mcp.contracts import SCHEMA_MODELS, generate_contract_artifacts
from fate_mcp.defaults import DefaultsRegistry
from fate_mcp.errors import FateValidationError
from fate_mcp.integrations import (
    assess_release_scenario_fit,
    build_run_parameter_manifest,
    build_run_uncertainty_summary,
    preview_regulatory_handoff_resolution,
)
from fate_mcp.models import (
    BuildEnvironmentalReleaseScenarioRequest,
    FateModelRunOptions,
    FateParameterRecord,
    ModelFamily,
    PreviewRegulatoryHandoffResolutionRequest,
    ReleaseFraction,
    RunMode,
    TimeWindow,
    Media,
    SourceClassification,
)
from fate_mcp.package_metadata import EXPERIMENTAL_MODEL_FAMILIES, SUPPORTED_MODEL_FAMILIES
from fate_mcp.plugins.external_result_adapter import load_external_payload, normalize_external_payload
from fate_mcp.runtime import FateRuntime


def validate_generated_artifacts(repo_root: Path) -> dict:
    schema_dir = repo_root / "docs" / "contracts" / "schemas"
    example_dir = repo_root / "schemas" / "examples"
    results = {"schemas": [], "examples": []}

    for name, model in SCHEMA_MODELS.items():
        schema_path = schema_dir / f"{name}.json"
        if not schema_path.exists():
            results["schemas"].append({"name": name, "status": "missing"})
            continue
        results["schemas"].append({"name": name, "status": "ok"})

    for example_path in sorted(example_dir.glob("*.json")):
        if example_path.name == "manifest.json":
            continue
        name = example_path.stem
        model_name = name
        if model_name == "concentrationEstimation.timeBucket.v1":
            model_name = "concentrationEstimationResult.v1"
        payload = json.loads(example_path.read_text())
        SCHEMA_MODELS[model_name].model_validate(payload)
        results["examples"].append({"name": example_path.name, "status": "ok"})

    return results


def validate_failure_modes(repo_root: Path) -> dict:
    runtime = FateRuntime(repo_root)
    checks = []

    try:
        runtime.build_environmental_release_scenario(
            BuildEnvironmentalReleaseScenarioRequest(
                chemical_identity={"preferredName": "Invalid"},
                total_release_mass_kg=1.0,
                release_fractions=[
                    ReleaseFraction(medium=Media.AIR, fraction=0.8),
                    ReleaseFraction(medium=Media.WATER, fraction=0.5),
                ],
                duration_days=1.0,
            )
        )
    except ValidationError:
        checks.append({"name": "invalid_release_fraction_sum", "status": "ok"})
    else:
        checks.append({"name": "invalid_release_fraction_sum", "status": "failed"})

    try:
        TimeWindow(mode=RunMode.STEADY_STATE, start="2026-04-08T00:00:00Z")
    except ValidationError:
        checks.append({"name": "invalid_steady_state_time_window", "status": "ok"})
    else:
        checks.append({"name": "invalid_steady_state_time_window", "status": "failed"})

    scenario = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={"preferredName": "Mismatch"},
            total_release_mass_kg=1.0,
            release_fractions=[ReleaseFraction(medium=Media.AIR, fraction=1.0)],
            duration_days=1.0,
        )
    )
    try:
        runtime.estimate(
            scenario=scenario,
            run_options=FateModelRunOptions(region_profile_id="temperate_river_basin"),
        )
    except FateValidationError:
        checks.append({"name": "region_profile_mismatch", "status": "ok"})
    else:
        checks.append({"name": "region_profile_mismatch", "status": "failed"})

    return {
        "checkCount": len(checks),
        "passed": all(item["status"] == "ok" for item in checks),
        "checks": checks,
    }


def validate_downstream_interoperability(repo_root: Path) -> dict:
    bundle_path = repo_root / "schemas" / "examples" / "concentrationSurfaceBundle.v1.json"
    package_path = repo_root / "schemas" / "examples" / "exposureConsumptionPackage.v1.json"
    preview_path = repo_root / "schemas" / "examples" / "regulatoryHandoffResolutionPreview.v1.json"
    regulatory_package_path = repo_root / "schemas" / "examples" / "regulatoryHandoffPackage.v1.json"
    regulatory_summary_path = repo_root / "schemas" / "examples" / "regulatoryHandoffPackageSummary.v1.json"
    regulatory_review_packet_path = repo_root / "schemas" / "examples" / "regulatoryHandoffReviewPacket.v1.json"
    regulatory_review_brief_path = repo_root / "schemas" / "examples" / "regulatoryHandoffReviewBrief.v1.json"
    regulatory_profile_path = repo_root / "schemas" / "examples" / "regulatoryHandoffProfile.v1.json"
    parameter_manifest_path = repo_root / "schemas" / "examples" / "runParameterManifest.v1.json"
    uncertainty_summary_path = repo_root / "schemas" / "examples" / "runUncertaintySummary.v1.json"
    regulatory_recommendation_path = (
        repo_root / "schemas" / "examples" / "regulatoryHandoffProfileRecommendation.v1.json"
    )
    bundle_payload = json.loads(bundle_path.read_text())
    package_payload = json.loads(package_path.read_text())
    preview_payload = json.loads(preview_path.read_text())
    regulatory_package_payload = json.loads(regulatory_package_path.read_text())
    regulatory_summary_payload = json.loads(regulatory_summary_path.read_text())
    regulatory_review_packet_payload = json.loads(regulatory_review_packet_path.read_text())
    regulatory_review_brief_payload = json.loads(regulatory_review_brief_path.read_text())
    regulatory_profile_payload = json.loads(regulatory_profile_path.read_text())
    parameter_manifest_payload = json.loads(parameter_manifest_path.read_text())
    uncertainty_summary_payload = json.loads(uncertainty_summary_path.read_text())
    regulatory_recommendation_payload = json.loads(regulatory_recommendation_path.read_text())

    bundle_required = ["scenario_id", "surfaces", "run_summary", "assumptions", "dependencies"]
    package_required = ["scenario_id", "surfaces", "geographic_scope", "time_semantics", "provenance"]
    regulatory_required = [
        "scenario_id",
        "source_module",
        "source_model_family",
        "target_modules",
        "crosswalk_entries",
        "provenance",
    ]

    bundle_missing = [field for field in bundle_required if field not in bundle_payload]
    package_missing = [field for field in package_required if field not in package_payload]
    regulatory_missing = [field for field in regulatory_required if field not in regulatory_package_payload]

    surfaces_have_provenance = all("provenance" in surface for surface in bundle_payload["surfaces"])
    surfaces_have_calculation_traces = all(
        surface.get("calculation_trace", {}).get("equation_id")
        and surface.get("calculation_trace", {}).get("equation_text")
        for surface in bundle_payload["surfaces"]
    )
    package_time_windows_have_mode = all("mode" in item for item in package_payload["time_semantics"])
    crosswalk_entries_have_route_hints = all(
        entry.get("route_hint") and entry.get("downstream_field")
        for entry in regulatory_package_payload["crosswalk_entries"]
    )
    crosswalk_entry_count_matches_surfaces = (
        len(regulatory_package_payload["crosswalk_entries"]) == len(package_payload["surfaces"])
    )
    regulatory_profile_declared = (
        regulatory_package_payload.get("handoff_profile_id") == "exposure_scenario_mcp_v1"
    )
    regulatory_profile_resolution_declared = bool(
        regulatory_package_payload.get("profile_resolution_method")
        and regulatory_package_payload.get("profile_resolution_confidence") is not None
    )
    regulatory_profile_has_templates = bool(
        regulatory_profile_payload.get("tool_request_template")
        and regulatory_profile_payload.get("response_summary_template")
    )
    regulatory_profile_has_review_guidance = bool(
        regulatory_profile_payload.get("review_brief_template")
        and regulatory_profile_payload.get("review_checklist")
    )
    regulatory_recommendation_resolves_profile = bool(
        regulatory_recommendation_payload.get("resolved_profile_id")
        and regulatory_recommendation_payload.get("confidence") is not None
        and regulatory_recommendation_payload.get("matched_hint")
    )
    regulatory_preview_resolves_profile = (
        preview_payload.get("status") == "resolved"
        and bool(preview_payload.get("resolved_profile_id"))
        and bool(preview_payload.get("resolution_method"))
    )
    regulatory_summary_matches_package = (
        regulatory_summary_payload.get("package_id") == regulatory_package_payload.get("package_id")
        and regulatory_summary_payload.get("handoff_profile_id") == regulatory_package_payload.get("handoff_profile_id")
        and regulatory_summary_payload.get("target_module") == "Direct-Use Exposure MCP"
        and bool(regulatory_summary_payload.get("summary_lines"))
        and bool(regulatory_summary_payload.get("parameter_quality_lines"))
        and bool(regulatory_summary_payload.get("applicability_lines"))
        and bool(regulatory_summary_payload.get("equation_lines"))
    )
    regulatory_review_packet_matches_package = (
        regulatory_review_packet_payload.get("package", {}).get("package_id")
        == regulatory_package_payload.get("package_id")
        and regulatory_review_packet_payload.get("summary", {}).get("package_id")
        == regulatory_summary_payload.get("package_id")
        and regulatory_review_packet_payload.get("resolution_preview", {}).get("resolved_profile_id")
        == regulatory_package_payload.get("handoff_profile_id")
        and regulatory_review_packet_payload.get("review_status") == "ready_for_assessor_review"
        and regulatory_review_packet_payload.get("target_module") == regulatory_summary_payload.get("target_module")
        and bool(regulatory_review_packet_payload.get("checks"))
        and bool(regulatory_review_packet_payload.get("parameter_quality_lines"))
        and bool(regulatory_review_packet_payload.get("applicability_lines"))
        and bool(regulatory_review_packet_payload.get("uncertainty_lines"))
        and bool(regulatory_review_packet_payload.get("equation_lines"))
        and all(item.get("passed") for item in regulatory_review_packet_payload.get("checks", []))
    )
    regulatory_review_brief_matches_packet = (
        regulatory_review_brief_payload.get("review_packet_id")
        == regulatory_review_packet_payload.get("review_packet_id")
        and regulatory_review_brief_payload.get("handoff_profile_id")
        == regulatory_review_packet_payload.get("handoff_profile_id")
        and regulatory_review_brief_payload.get("target_module")
        == regulatory_review_packet_payload.get("target_module")
        and regulatory_review_brief_payload.get("review_status")
        == regulatory_review_packet_payload.get("review_status")
        and bool(regulatory_review_brief_payload.get("checklist_items"))
        and bool(regulatory_review_brief_payload.get("brief_lines"))
        and bool(regulatory_review_brief_payload.get("parameter_quality_lines"))
        and bool(regulatory_review_brief_payload.get("applicability_lines"))
        and bool(regulatory_review_brief_payload.get("uncertainty_lines"))
        and bool(regulatory_review_brief_payload.get("equation_lines"))
    )
    regulatory_package_carries_scientific_review_artifacts = (
        regulatory_package_payload.get("parameter_manifest", {}).get("run_id")
        == parameter_manifest_payload.get("run_id")
        and regulatory_package_payload.get("uncertainty_summary", {}).get("run_id")
        == uncertainty_summary_payload.get("run_id")
    )

    passed = (
        not bundle_missing
        and not package_missing
        and not regulatory_missing
        and surfaces_have_provenance
        and surfaces_have_calculation_traces
        and package_time_windows_have_mode
        and crosswalk_entries_have_route_hints
        and crosswalk_entry_count_matches_surfaces
        and regulatory_profile_declared
        and regulatory_profile_resolution_declared
        and regulatory_profile_has_templates
        and regulatory_profile_has_review_guidance
        and regulatory_recommendation_resolves_profile
        and regulatory_preview_resolves_profile
        and regulatory_summary_matches_package
        and regulatory_review_packet_matches_package
        and regulatory_review_brief_matches_packet
        and regulatory_package_carries_scientific_review_artifacts
    )
    return {
        "passed": passed,
        "bundleMissing": bundle_missing,
        "packageMissing": package_missing,
        "regulatoryPackageMissing": regulatory_missing,
        "surfacesHaveProvenance": surfaces_have_provenance,
        "surfacesHaveCalculationTraces": surfaces_have_calculation_traces,
        "packageTimeWindowsHaveMode": package_time_windows_have_mode,
        "crosswalkEntriesHaveRouteHints": crosswalk_entries_have_route_hints,
        "crosswalkEntryCountMatchesSurfaces": crosswalk_entry_count_matches_surfaces,
        "regulatoryProfileDeclared": regulatory_profile_declared,
        "regulatoryProfileResolutionDeclared": regulatory_profile_resolution_declared,
        "regulatoryProfileHasTemplates": regulatory_profile_has_templates,
        "regulatoryProfileHasReviewGuidance": regulatory_profile_has_review_guidance,
        "regulatoryRecommendationResolvesProfile": regulatory_recommendation_resolves_profile,
        "regulatoryPreviewResolvesProfile": regulatory_preview_resolves_profile,
        "regulatorySummaryMatchesPackage": regulatory_summary_matches_package,
        "regulatoryReviewPacketMatchesPackage": regulatory_review_packet_matches_package,
        "regulatoryReviewBriefMatchesPacket": regulatory_review_brief_matches_packet,
        "regulatoryPackageCarriesScientificReviewArtifacts": regulatory_package_carries_scientific_review_artifacts,
    }


def validate_reconciliation_transparency(repo_root: Path) -> dict:
    path = repo_root / "schemas" / "examples" / "releaseEvidenceReconciliationResult.v1.json"
    payload = json.loads(path.read_text())

    required_fields = [
        "reconciled_scenario",
        "evidence_observations",
        "reconciled_scalars",
        "reconciled_release_fractions",
        "conflicts",
        "vector_conflicts",
        "unresolved_conflict_count",
        "recommended_next_actions",
        "provenance",
    ]
    missing = [field for field in required_fields if field not in payload]
    scalar_fields = {item["field"] for item in payload["reconciled_scalars"]}
    fraction_fields = {item["medium"] for item in payload["reconciled_release_fractions"]}
    conflict_fields = {item["field"] for item in payload["conflicts"]}

    vector_conflicts = payload.get("vector_conflicts", [])
    passed = (
        not missing
        and "total_release_mass_kg" in scalar_fields
        and "water" in fraction_fields
        and payload["unresolved_conflict_count"] == len(payload["conflicts"]) + len(vector_conflicts)
        and bool(conflict_fields)
    )
    return {
        "passed": passed,
        "missing": missing,
        "scalarFields": sorted(scalar_fields),
        "fractionFields": sorted(fraction_fields),
        "conflictFields": sorted(conflict_fields),
        "vectorConflictCount": len(vector_conflicts),
    }


def validate_regulatory_handoff_governance(repo_root: Path) -> dict:
    registry = DefaultsRegistry(repo_root)
    runtime = FateRuntime(repo_root)
    alias_manifest = registry.regulatory_handoff_consumer_alias_manifest()
    recommendation = registry.recommend_regulatory_handoff_profile("ToxClaw")
    resolved_preview = preview_regulatory_handoff_resolution(
        PreviewRegulatoryHandoffResolutionRequest(consumer_name="ToxClaw"),
        runtime.provenance,
    )
    mismatch_preview = preview_regulatory_handoff_resolution(
        PreviewRegulatoryHandoffResolutionRequest(
            handoff_profile_id="exposure_scenario_mcp_v1",
            consumer_name="ToxClaw",
        ),
        runtime.provenance,
    )
    target_mismatch_preview = preview_regulatory_handoff_resolution(
        PreviewRegulatoryHandoffResolutionRequest(
            consumer_name="ToxClaw",
            target_modules=["Direct-Use Exposure MCP"],
        ),
        runtime.provenance,
    )
    passed = (
        alias_manifest.conflict_count == 0
        and recommendation is not None
        and recommendation.resolved_profile_id == "toxclaw_orchestration_v1"
        and recommendation.confidence >= 0.8
        and resolved_preview.status == "resolved"
        and mismatch_preview.status == "mismatch"
        and target_mismatch_preview.status == "mismatch"
    )
    return {
        "passed": passed,
        "aliasCount": alias_manifest.alias_count,
        "conflictCount": alias_manifest.conflict_count,
        "conflicts": [conflict.model_dump(mode="json") for conflict in alias_manifest.conflicts],
        "recommendationResolved": recommendation is not None,
        "resolvedPreviewStatus": resolved_preview.status,
        "mismatchPreviewStatus": mismatch_preview.status,
        "targetMismatchPreviewStatus": target_mismatch_preview.status,
    }


def _surface_signature(result) -> list[dict[str, object]]:
    return sorted(
        [
            {
                "compartment": surface.compartment.value,
                "unit": surface.concentration_unit,
                "mode": surface.time_window.mode.value,
                "start": surface.time_window.start.isoformat() if surface.time_window.start else None,
                "end": surface.time_window.end.isoformat() if surface.time_window.end else None,
                "value": round(surface.concentration_value, 8),
            }
            for surface in result.surfaces
        ],
        key=lambda item: (
            str(item["compartment"]),
            str(item["start"]),
            str(item["end"]),
            str(item["value"]),
        ),
    )


def validate_adapter_interoperability(repo_root: Path) -> dict:
    runtime = FateRuntime(repo_root)
    steady_scenario = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={"preferredName": "Adapter validation steady"},
            total_release_mass_kg=8.0,
            release_fractions=[ReleaseFraction(medium=Media.WATER, fraction=1.0)],
            duration_days=10.0,
        )
    )
    steady_run_options = FateModelRunOptions(
        region_profile_id=steady_scenario.geographic_scope.region_id,
        model_family=ModelFamily.EXTERNAL_RESULT_ADAPTER,
    )
    json_payload = load_external_payload(
        repo_root / "config" / "adapter-fixtures" / "illustrative_external_engine_payload.json"
    )
    csv_payload = load_external_payload(
        repo_root / "config" / "adapter-fixtures" / "illustrative_external_engine_payload.csv"
    )
    json_result = normalize_external_payload(
        json_payload,
        steady_scenario,
        steady_run_options,
        runtime.provenance,
    )
    csv_result = normalize_external_payload(
        csv_payload,
        steady_scenario,
        steady_run_options,
        runtime.provenance,
    )
    alternate_unit_payload = load_external_payload(
        repo_root / "config" / "adapter-fixtures" / "illustrative_external_engine_payload_alt_units.csv"
    )
    alternate_unit_result = normalize_external_payload(
        alternate_unit_payload,
        steady_scenario,
        steady_run_options,
        runtime.provenance,
    )
    weight_basis_scenario = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={"preferredName": "Adapter validation weight basis"},
            total_release_mass_kg=8.0,
            release_fractions=[
                ReleaseFraction(medium=Media.SOIL, fraction=0.5),
                ReleaseFraction(medium=Media.SEDIMENT, fraction=0.5),
            ],
            duration_days=10.0,
        )
    )
    weight_basis_payload = load_external_payload(
        repo_root / "config" / "adapter-fixtures" / "legacy_screening_desktop_export_weight_basis.csv"
    )
    weight_basis_result = normalize_external_payload(
        weight_basis_payload,
        weight_basis_scenario,
        FateModelRunOptions(
            region_profile_id=weight_basis_scenario.geographic_scope.region_id,
            model_family=ModelFamily.EXTERNAL_RESULT_ADAPTER,
        ),
        runtime.provenance,
    )

    legacy_steady_scenario = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={"preferredName": "Adapter validation legacy steady"},
            total_release_mass_kg=8.0,
            release_fractions=[
                ReleaseFraction(medium=Media.AIR, fraction=0.5),
                ReleaseFraction(medium=Media.WATER, fraction=0.5),
            ],
            duration_days=10.0,
        )
    )
    legacy_steady_payload = load_external_payload(
        repo_root / "config" / "adapter-fixtures" / "legacy_screening_desktop_export.csv"
    )
    legacy_steady_result = normalize_external_payload(
        legacy_steady_payload,
        legacy_steady_scenario,
        FateModelRunOptions(
            region_profile_id=legacy_steady_scenario.geographic_scope.region_id,
            model_family=ModelFamily.EXTERNAL_RESULT_ADAPTER,
        ),
        runtime.provenance,
    )

    legacy_time_bucket_scenario = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={"preferredName": "Adapter validation legacy time bucket"},
            total_release_mass_kg=8.0,
            release_fractions=[ReleaseFraction(medium=Media.WATER, fraction=1.0)],
            duration_days=14.0,
        )
    )
    legacy_time_bucket_payload = load_external_payload(
        repo_root / "config" / "adapter-fixtures" / "legacy_screening_desktop_export_time_bucket.csv"
    )
    legacy_time_bucket_result = normalize_external_payload(
        legacy_time_bucket_payload,
        legacy_time_bucket_scenario,
        FateModelRunOptions(
            run_mode=RunMode.TIME_BUCKET,
            region_profile_id=legacy_time_bucket_scenario.geographic_scope.region_id,
            model_family=ModelFamily.EXTERNAL_RESULT_ADAPTER,
            bucket_count=2,
            bucket_duration_days=7.0,
        ),
        runtime.provenance,
    )

    json_csv_equivalent = _surface_signature(json_result) == _surface_signature(csv_result)
    alternate_unit_equivalent = _surface_signature(json_result) == _surface_signature(alternate_unit_result)
    weight_basis_values = sorted(
        round(surface.concentration_value, 8) for surface in weight_basis_result.surfaces
    )
    weight_basis_units = {surface.concentration_unit for surface in weight_basis_result.surfaces}
    legacy_steady_compartments = sorted(
        {surface.compartment.value for surface in legacy_steady_result.surfaces}
    )
    time_bucket_bounds_preserved = all(
        surface.time_window.mode == RunMode.TIME_BUCKET
        and surface.time_window.start is not None
        and surface.time_window.end is not None
        for surface in legacy_time_bucket_result.surfaces
    )

    checks = [
        {
            "name": "normalized_json_csv_equivalence",
            "status": "ok" if json_csv_equivalent else "failed",
        },
        {
            "name": "adapter_unit_conversion_equivalence",
            "status": "ok" if alternate_unit_equivalent else "failed",
        },
        {
            "name": "adapter_basis_conversion_equivalence",
            "status": "ok"
            if weight_basis_values == [10.0, 10.0] and weight_basis_units == {"mg/kg"}
            else "failed",
        },
        {
            "name": "legacy_steady_compartments_preserved",
            "status": "ok" if legacy_steady_compartments == ["ambient_air", "surface_water"] else "failed",
        },
        {
            "name": "legacy_time_bucket_bounds_preserved",
            "status": "ok" if time_bucket_bounds_preserved else "failed",
        },
    ]
    return {
        "passed": all(item["status"] == "ok" for item in checks),
        "checkCount": len(checks),
        "checks": checks,
        "normalizedFixtureEquivalence": {
            "jsonSignature": _surface_signature(json_result),
            "csvSignature": _surface_signature(csv_result),
            "alternateUnitSignature": _surface_signature(alternate_unit_result),
            "weightBasisSignature": _surface_signature(weight_basis_result),
        },
        "legacySteadyImport": {
            "engineName": legacy_steady_payload.engine_name,
            "surfaceCount": len(legacy_steady_result.surfaces),
            "compartments": legacy_steady_compartments,
        },
        "legacyTimeBucketImport": {
            "engineName": legacy_time_bucket_payload.engine_name,
            "surfaceCount": len(legacy_time_bucket_result.surfaces),
            "timeWindowModes": [surface.time_window.mode.value for surface in legacy_time_bucket_result.surfaces],
            "bounds": [
                {
                    "start": surface.time_window.start.isoformat() if surface.time_window.start else None,
                    "end": surface.time_window.end.isoformat() if surface.time_window.end else None,
                }
                for surface in legacy_time_bucket_result.surfaces
            ],
        },
    }


def validate_scientific_review_artifacts(repo_root: Path) -> dict:
    runtime = FateRuntime(repo_root)
    registry = DefaultsRegistry(repo_root)
    scenario = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={"preferredName": "Scientific review validation"},
            total_release_mass_kg=12.0,
            release_fractions=[
                ReleaseFraction(medium=Media.WATER, fraction=0.7),
                ReleaseFraction(medium=Media.SOIL, fraction=0.3),
            ],
            duration_days=20.0,
            parameter_records=[
                FateParameterRecord(
                    parameter="water_half_life_days",
                    value=8.0,
                    unit="day",
                    source_classification=SourceClassification.USER_INPUT,
                    rationale="Validation override for water half-life.",
                    evidence_quality="reference",
                ),
                FateParameterRecord(
                    parameter="log_kow",
                    value=4.6,
                    unit="log10",
                    source_classification=SourceClassification.HEURISTIC,
                    rationale="Validation preserved-only parameter.",
                    evidence_quality="heuristic",
                ),
            ],
        )
    )
    run_options = FateModelRunOptions(
        region_profile_id=scenario.geographic_scope.region_id,
    )
    result = runtime.estimate(scenario, run_options)
    manifest = build_run_parameter_manifest(scenario, result, runtime.provenance)
    uncertainty_summary = build_run_uncertainty_summary(scenario, result, runtime.provenance)
    fit_assessment = assess_release_scenario_fit(scenario, run_options, runtime.provenance)

    declared_profiles = {profile.model_family.value for profile in registry.list_model_family_applicability_profiles()}
    declared_review_profiles = {profile.model_family.value for profile in registry.list_scientific_review_profiles()}
    missing_profiles = sorted(set(SUPPORTED_MODEL_FAMILIES) - declared_profiles)
    missing_experimental_applicability_profiles = sorted(
        set(EXPERIMENTAL_MODEL_FAMILIES) - declared_profiles
    )
    missing_experimental_review_profiles = sorted(
        set(EXPERIMENTAL_MODEL_FAMILIES) - declared_review_profiles
    )
    consumed_parameters = {entry.parameter for entry in manifest.entries if entry.runtime_consumed}
    preserved_only_parameters = {
        entry.parameter for entry in manifest.entries if not entry.runtime_consumed
    }
    benchmark_required_fields = {
        "category",
        "validation_tier",
        "scientific_basis",
        "reference_type",
        "expected_behavior",
        "tolerance_rationale",
        "scientific_claim_ids",
    }
    benchmark_fixtures = benchmark_manifest()["fixtures"]
    benchmark_metadata_complete = all(
        benchmark_required_fields.issubset(fixture.keys()) for fixture in benchmark_fixtures
    )
    surfaces_have_equation_traces = all(
        surface.calculation_trace is not None
        and bool(surface.calculation_trace.equation_id)
        and bool(surface.calculation_trace.equation_text)
        for surface in result.surfaces
    )
    manifest_consistent = (
        manifest.scenario_id == scenario.scenario_id
        and manifest.run_id == result.run_summary.run_id
        and "water_half_life_days" in consumed_parameters
        and "log_kow" in preserved_only_parameters
        and bool(manifest.summary_lines)
        and fit_assessment.applicability_profile.model_family == result.run_summary.model_family
        and bool(fit_assessment.applicability_lines)
    )
    uncertainty_summary_consistent = (
        uncertainty_summary.scenario_id == scenario.scenario_id
        and uncertainty_summary.run_id == result.run_summary.run_id
        and bool(uncertainty_summary.top_drivers)
        and bool(uncertainty_summary.summary_lines)
    )
    return {
        "passed": (
            not missing_profiles
            and not missing_experimental_applicability_profiles
            and not missing_experimental_review_profiles
            and manifest_consistent
            and uncertainty_summary_consistent
            and benchmark_metadata_complete
            and surfaces_have_equation_traces
        ),
        "modelFamilyApplicabilityProfileCount": len(declared_profiles),
        "missingApplicabilityProfiles": missing_profiles,
        "missingExperimentalApplicabilityProfiles": missing_experimental_applicability_profiles,
        "missingExperimentalScientificReviewProfiles": missing_experimental_review_profiles,
        "parameterManifestConsistent": manifest_consistent,
        "parameterManifestEntryCount": len(manifest.entries),
        "parameterManifestRuntimeConsumedCount": len(consumed_parameters),
        "parameterManifestPreservedOnlyCount": len(preserved_only_parameters),
        "uncertaintySummaryConsistent": uncertainty_summary_consistent,
        "uncertaintyDriverCount": len(uncertainty_summary.top_drivers),
        "benchmarkMetadataComplete": benchmark_metadata_complete,
        "benchmarkMetadataFixtureCount": len(benchmark_fixtures),
        "surfacesHaveEquationTraces": surfaces_have_equation_traces,
    }


def validate_scientific_claim_coverage(repo_root: Path) -> dict:
    registry = DefaultsRegistry(repo_root)
    claim_manifest = registry.scientific_validation_claim_manifest()
    coverage_manifest = scientific_validation_claim_coverage_manifest(repo_root)
    benchmark_fixtures = benchmark_manifest(repo_root)["fixtures"]

    declared_claim_ids = {claim.claim_id for claim in claim_manifest.claims}
    fixture_claim_ids = sorted(
        {
            claim_id
            for fixture in benchmark_fixtures
            for claim_id in fixture.get("scientific_claim_ids", [])
        }
    )
    unknown_fixture_claim_ids = sorted(set(fixture_claim_ids) - declared_claim_ids)
    unclaimed_fixture_names = sorted(
        fixture["name"] for fixture in benchmark_fixtures if not fixture.get("scientific_claim_ids")
    )
    uncovered_mandatory_claim_ids = sorted(
        record.claim_id
        for record in coverage_manifest.coverage
        if record.mandatory_for_release and not record.covered
    )
    unsatisfied_reference_claim_ids = sorted(
        record.claim_id
        for record in coverage_manifest.coverage
        if not record.satisfies_required_reference_types
    )
    unsatisfied_validation_tier_claim_ids = sorted(
        record.claim_id
        for record in coverage_manifest.coverage
        if not record.satisfies_required_validation_tiers
    )
    claims_missing_source_references = sorted(
        claim.claim_id for claim in claim_manifest.claims if not claim.source_references
    )
    claims_missing_methods_basis_lines = sorted(
        claim.claim_id for claim in claim_manifest.claims if not claim.methods_basis_lines
    )
    claims_missing_reference_case_lines = sorted(
        claim.claim_id for claim in claim_manifest.claims if not claim.reference_case_lines
    )
    claims_with_unresolved_reference_case_ids = sorted(
        claim.claim_id
        for claim in claim_manifest.claims
        if any(registry.scientific_reference_case(case_id) is None for case_id in claim.reference_case_ids)
    )
    experimental_priority_claims_missing_reference_case_ids = sorted(
        claim.claim_id
        for claim in claim_manifest.claims
        if (
            claim.model_family.value in EXPERIMENTAL_MODEL_FAMILIES
            and claim.priority.value in {"high", "medium"}
            and claim.mandatory_for_release
            and not claim.reference_case_ids
        )
    )
    reference_mandatory_claims_missing_reference_case_ids = sorted(
        claim.claim_id
        for claim in claim_manifest.claims
        if (
            claim.model_family.value == "reference_mass_balance"
            and claim.mandatory_for_release
            and not claim.reference_case_ids
        )
    )
    reference_mandatory_single_reference_case_claim_ids = sorted(
        claim.claim_id
        for claim in claim_manifest.claims
        if (
            claim.model_family.value == "reference_mass_balance"
            and claim.mandatory_for_release
            and len(claim.reference_case_ids) < 2
        )
    )
    reference_mandatory_single_anchor_claim_ids = sorted(
        record.claim_id
        for record in coverage_manifest.coverage
        if (
            record.model_family.value == "reference_mass_balance"
            and record.mandatory_for_release
            and record.support_strength.value == "single_anchor"
        )
    )
    reference_mandatory_single_tier_claim_ids = sorted(
        record.claim_id
        for record in coverage_manifest.coverage
        if (
            record.model_family.value == "reference_mass_balance"
            and record.mandatory_for_release
            and record.support_strength.value == "multi_anchor_single_tier"
        )
    )
    high_priority_experimental_single_reference_case_claim_ids = sorted(
        claim.claim_id
        for claim in claim_manifest.claims
        if (
            claim.model_family.value in EXPERIMENTAL_MODEL_FAMILIES
            and claim.priority.value == "high"
            and claim.mandatory_for_release
            and len(claim.reference_case_ids) < 2
        )
    )
    medium_priority_experimental_single_reference_case_claim_ids = sorted(
        claim.claim_id
        for claim in claim_manifest.claims
        if (
            claim.model_family.value in EXPERIMENTAL_MODEL_FAMILIES
            and claim.priority.value == "medium"
            and claim.mandatory_for_release
            and len(claim.reference_case_ids) < 2
        )
    )
    high_priority_experimental_single_anchor_claim_ids = sorted(
        record.claim_id
        for record in coverage_manifest.coverage
        if (
            record.model_family.value in EXPERIMENTAL_MODEL_FAMILIES
            and record.priority.value == "high"
            and record.mandatory_for_release
            and record.support_strength.value == "single_anchor"
        )
    )
    medium_priority_experimental_single_anchor_claim_ids = sorted(
        record.claim_id
        for record in coverage_manifest.coverage
        if (
            record.model_family.value in EXPERIMENTAL_MODEL_FAMILIES
            and record.priority.value == "medium"
            and record.mandatory_for_release
            and record.support_strength.value == "single_anchor"
        )
    )
    high_priority_experimental_single_tier_claim_ids = sorted(
        record.claim_id
        for record in coverage_manifest.coverage
        if (
            record.model_family.value in EXPERIMENTAL_MODEL_FAMILIES
            and record.priority.value == "high"
            and record.mandatory_for_release
            and record.support_strength.value == "multi_anchor_single_tier"
        )
    )
    medium_priority_experimental_single_tier_claim_ids = sorted(
        record.claim_id
        for record in coverage_manifest.coverage
        if (
            record.model_family.value in EXPERIMENTAL_MODEL_FAMILIES
            and record.priority.value == "medium"
            and record.mandatory_for_release
            and record.support_strength.value == "multi_anchor_single_tier"
        )
    )

    return {
        "passed": (
            not unknown_fixture_claim_ids
            and not unclaimed_fixture_names
            and not uncovered_mandatory_claim_ids
            and not unsatisfied_reference_claim_ids
            and not unsatisfied_validation_tier_claim_ids
            and not claims_missing_source_references
            and not claims_missing_methods_basis_lines
            and not claims_missing_reference_case_lines
            and not claims_with_unresolved_reference_case_ids
            and not experimental_priority_claims_missing_reference_case_ids
            and not reference_mandatory_claims_missing_reference_case_ids
            and not reference_mandatory_single_reference_case_claim_ids
            and not reference_mandatory_single_anchor_claim_ids
            and not reference_mandatory_single_tier_claim_ids
            and not high_priority_experimental_single_reference_case_claim_ids
            and not medium_priority_experimental_single_reference_case_claim_ids
            and not high_priority_experimental_single_anchor_claim_ids
            and not medium_priority_experimental_single_anchor_claim_ids
            and not high_priority_experimental_single_tier_claim_ids
            and not medium_priority_experimental_single_tier_claim_ids
        ),
        "claimCount": claim_manifest.claim_count,
        "coveredClaimCount": coverage_manifest.covered_claim_count,
        "mandatoryClaimCount": coverage_manifest.mandatory_claim_count,
        "uncoveredMandatoryClaimCount": coverage_manifest.uncovered_mandatory_claim_count,
        "unknownFixtureClaimIds": unknown_fixture_claim_ids,
        "unclaimedFixtureNames": unclaimed_fixture_names,
        "uncoveredMandatoryClaimIds": uncovered_mandatory_claim_ids,
        "unsatisfiedReferenceClaimIds": unsatisfied_reference_claim_ids,
        "unsatisfiedValidationTierClaimIds": unsatisfied_validation_tier_claim_ids,
        "claimsMissingSourceReferences": claims_missing_source_references,
        "claimsMissingMethodsBasisLines": claims_missing_methods_basis_lines,
        "claimsMissingReferenceCaseLines": claims_missing_reference_case_lines,
        "claimsWithUnresolvedReferenceCaseIds": claims_with_unresolved_reference_case_ids,
        "experimentalPriorityClaimsMissingReferenceCaseIds": experimental_priority_claims_missing_reference_case_ids,
        "referenceMandatoryClaimsMissingReferenceCaseIds": reference_mandatory_claims_missing_reference_case_ids,
        "referenceMandatorySingleReferenceCaseClaimIds": reference_mandatory_single_reference_case_claim_ids,
        "referenceMandatorySingleAnchorClaimIds": reference_mandatory_single_anchor_claim_ids,
        "referenceMandatorySingleTierClaimIds": reference_mandatory_single_tier_claim_ids,
        "highPriorityExperimentalSingleReferenceCaseClaimIds": high_priority_experimental_single_reference_case_claim_ids,
        "mediumPriorityExperimentalSingleReferenceCaseClaimIds": medium_priority_experimental_single_reference_case_claim_ids,
        "highPriorityExperimentalSingleAnchorClaimIds": high_priority_experimental_single_anchor_claim_ids,
        "mediumPriorityExperimentalSingleAnchorClaimIds": medium_priority_experimental_single_anchor_claim_ids,
        "highPriorityExperimentalSingleTierClaimIds": high_priority_experimental_single_tier_claim_ids,
        "mediumPriorityExperimentalSingleTierClaimIds": medium_priority_experimental_single_tier_claim_ids,
    }


def validate_scientific_review_workflow(repo_root: Path) -> dict:
    preview_payload = json.loads(
        (repo_root / "schemas" / "examples" / "scientificReviewOutcomePreview.v1.json").read_text()
    )
    packet_payload = json.loads((repo_root / "schemas" / "examples" / "scientificReviewPacket.v1.json").read_text())
    brief_payload = json.loads((repo_root / "schemas" / "examples" / "scientificReviewBrief.v1.json").read_text())
    manifest_payload = json.loads((repo_root / "schemas" / "examples" / "runParameterManifest.v1.json").read_text())
    uncertainty_payload = json.loads((repo_root / "schemas" / "examples" / "runUncertaintySummary.v1.json").read_text())
    review_profile_payload = json.loads((repo_root / "schemas" / "examples" / "scientificReviewProfile.v1.json").read_text())
    review_profile_manifest_payload = json.loads((repo_root / "schemas" / "examples" / "scientificReviewProfileManifest.v1.json").read_text())

    outcome_preview_matches_packet = (
        packet_payload.get("outcome_preview", {}).get("run_id") == preview_payload.get("run_id")
        and packet_payload.get("outcome_preview", {}).get("scenario_id") == preview_payload.get("scenario_id")
        and packet_payload.get("outcome_preview", {}).get("review_outcome") == preview_payload.get("review_outcome")
        and packet_payload.get("outcome_preview", {}).get("review_status") == preview_payload.get("review_status")
        and packet_payload.get("review_outcome") == preview_payload.get("review_outcome")
        and packet_payload.get("review_status") == preview_payload.get("review_status")
        and packet_payload.get("outcome_lines") == preview_payload.get("outcome_lines")
        and packet_payload.get("recommended_actions") == preview_payload.get("recommended_actions")
        and bool(preview_payload.get("governing_rule_lines"))
        and bool(preview_payload.get("status_rule_lines"))
    )
    packet_matches_components = (
        packet_payload.get("parameter_manifest", {}).get("run_id") == manifest_payload.get("run_id")
        and packet_payload.get("uncertainty_summary", {}).get("run_id") == uncertainty_payload.get("run_id")
        and packet_payload.get("fit_assessment", {}).get("applicability_profile", {}).get("model_family")
        == packet_payload.get("model_family")
        and packet_payload.get("outcome_preview", {}).get("review_profile_model_family")
        == packet_payload.get("model_family")
        and packet_payload.get("outcome_preview", {}).get("review_status")
        == packet_payload.get("review_status")
        and bool(packet_payload.get("surface_samples"))
        and bool(packet_payload.get("benchmark_reference_lines"))
        and bool(packet_payload.get("equation_lines"))
        and bool(packet_payload.get("equation_component_lines"))
        and bool(packet_payload.get("mass_balance_component_lines"))
        and bool(packet_payload.get("transport_regime_lines"))
        and bool(packet_payload.get("post_release_recovery_lines"))
        and bool(packet_payload.get("post_release_regime_lines"))
        and bool(packet_payload.get("loss_dominance_lines"))
        and bool(packet_payload.get("loss_transition_lines"))
        and bool(packet_payload.get("review_checklist"))
        and bool(packet_payload.get("review_template_used"))
        and bool(packet_payload.get("review_outcome"))
        and bool(packet_payload.get("outcome_lines"))
        and bool(packet_payload.get("recommended_actions"))
    )
    brief_matches_packet = (
        brief_payload.get("review_packet_id") == packet_payload.get("review_packet_id")
        and brief_payload.get("run_id") == packet_payload.get("run_id")
        and brief_payload.get("model_family") == packet_payload.get("model_family")
        and brief_payload.get("review_status") == packet_payload.get("review_status")
        and bool(brief_payload.get("review_template_used"))
        and bool(brief_payload.get("checklist_items"))
        and brief_payload.get("review_outcome") == packet_payload.get("review_outcome")
        and bool(brief_payload.get("outcome_lines"))
        and bool(brief_payload.get("recommended_actions"))
        and bool(brief_payload.get("parameter_quality_lines"))
        and bool(brief_payload.get("applicability_lines"))
        and bool(brief_payload.get("uncertainty_lines"))
        and bool(brief_payload.get("benchmark_reference_lines"))
        and bool(brief_payload.get("equation_lines"))
        and brief_payload.get("equation_component_lines") == packet_payload.get("equation_component_lines")
        and brief_payload.get("mass_balance_component_lines") == packet_payload.get("mass_balance_component_lines")
        and brief_payload.get("transport_regime_lines") == packet_payload.get("transport_regime_lines")
        and brief_payload.get("post_release_recovery_lines") == packet_payload.get("post_release_recovery_lines")
        and brief_payload.get("post_release_regime_lines") == packet_payload.get("post_release_regime_lines")
        and brief_payload.get("loss_dominance_lines") == packet_payload.get("loss_dominance_lines")
        and brief_payload.get("loss_transition_lines") == packet_payload.get("loss_transition_lines")
        and any(
            line.startswith("Equation components: ")
            for line in brief_payload.get("summary_lines", [])
        )
        and any(
            line.startswith("Mass balance: ")
            for line in brief_payload.get("summary_lines", [])
        )
        and any(
            line.startswith("Transport regime: ")
            for line in brief_payload.get("summary_lines", [])
        )
        and any(
            line.startswith("Post-release recovery: ")
            for line in brief_payload.get("summary_lines", [])
        )
        and any(
            line.startswith("Post-release regime: ")
            for line in brief_payload.get("summary_lines", [])
        )
        and any(
            line.startswith("Loss dominance: ")
            for line in brief_payload.get("summary_lines", [])
        )
        and any(
            line.startswith("Loss transition: ")
            for line in brief_payload.get("summary_lines", [])
        )
    )
    profile_manifest_consistent = (
        review_profile_manifest_payload.get("profile_count", 0) >= 3
        and bool(review_profile_payload.get("review_checklist"))
        and bool(review_profile_payload.get("packet_template"))
        and bool(review_profile_payload.get("brief_template"))
        and review_profile_payload.get("ready_fit_verdicts") is not None
        and review_profile_payload.get("attention_outcomes") is not None
        and review_profile_payload.get("attention_if_any_checks_fail") is not None
        and bool(review_profile_payload.get("acceptable_outcome_template"))
        and bool(review_profile_payload.get("qualified_outcome_template"))
        and bool(review_profile_payload.get("escalation_outcome_template"))
        and (
            bool(review_profile_payload.get("escalation_fit_verdicts"))
            or bool(review_profile_payload.get("escalation_driver_types"))
            or bool(review_profile_payload.get("qualification_driver_types"))
        )
        and review_profile_payload.get("warning_severity_promotes_qualification") is not None
        and bool(review_profile_payload.get("driver_action_templates"))
    )
    return {
        "passed": (
            outcome_preview_matches_packet
            and packet_matches_components
            and brief_matches_packet
            and profile_manifest_consistent
        ),
        "scientificReviewOutcomePreviewMatchesPacket": outcome_preview_matches_packet,
        "scientificReviewPacketMatchesComponents": packet_matches_components,
        "scientificReviewBriefMatchesPacket": brief_matches_packet,
        "scientificReviewProfileManifestConsistent": profile_manifest_consistent,
    }


def validate_scientific_methods_dossier_workflow(repo_root: Path) -> dict:
    request_payload = json.loads(
        (repo_root / "schemas" / "examples" / "buildScientificMethodsDossierRequest.v1.json").read_text()
    )
    dossier_payload = json.loads(
        (repo_root / "schemas" / "examples" / "scientificMethodsDossier.v1.json").read_text()
    )
    brief_request_payload = json.loads(
        (repo_root / "schemas" / "examples" / "buildScientificMethodsDossierBriefRequest.v1.json").read_text()
    )
    brief_payload = json.loads(
        (repo_root / "schemas" / "examples" / "scientificMethodsDossierBrief.v1.json").read_text()
    )
    claim_summary_payload = json.loads(
        (repo_root / "schemas" / "examples" / "scientificMethodsDossierClaimSummary.v1.json").read_text()
    )

    dossier_consistent = (
        request_payload.get("model_family") == dossier_payload.get("model_family")
        and request_payload.get("run_mode_filter") == dossier_payload.get("run_mode_filter")
        and dossier_payload.get("promotion_status")
        and "blocking_action_count" in dossier_payload
        and "strengthening_action_count" in dossier_payload
        and "promotion_blocker_claim_ids" in dossier_payload
        and "promotion_blocker_summaries" in dossier_payload
        and dossier_payload.get("claim_count") == len(dossier_payload.get("claim_summaries", []))
        and dossier_payload.get("mandatory_claim_count", 0)
        >= dossier_payload.get("covered_mandatory_claim_count", 0)
        and dossier_payload.get("uncovered_mandatory_claim_count", 0)
        == dossier_payload.get("mandatory_claim_count", 0)
        - dossier_payload.get("covered_mandatory_claim_count", 0)
        and bool(dossier_payload.get("highlighted_claim_summaries"))
        and all(
            item.get("challenge_status")
            and item.get("challenge_lines")
            and item.get("review_questions")
            and item.get("loss_regime_stability_status")
            and item.get("loss_regime_stability_lines")
            and item.get("transport_regime_stability_status")
            and item.get("transport_regime_stability_lines")
            and item.get("external_corroboration_status")
            and item.get("external_corroboration_lines")
            and item.get("external_corroboration_actions")
            and "external_corroboration_source_count" in item
            and "external_corroboration_jurisdictions" in item
            and not (
                item.get("external_corroboration_status") in {"none", "single_official_source"}
                and item.get("challenge_status") == "well_supported"
            )
            for item in dossier_payload.get("highlighted_claim_summaries", [])
        )
        and all(
            item.get("external_corroboration_status")
            and "external_corroboration_source_count" in item
            and "external_corroboration_jurisdictions" in item
            and item.get("external_corroboration_lines")
            for item in dossier_payload.get("claim_summaries", [])
        )
        and bool(dossier_payload.get("summary_lines"))
        and bool(dossier_payload.get("applicability_lines"))
        and bool(dossier_payload.get("source_grounding_lines"))
        and bool(dossier_payload.get("highlighted_claim_grounding_lines"))
        and bool(dossier_payload.get("reference_case_grounding_lines"))
        and bool(dossier_payload.get("reference_case_concept_lines"))
        and bool(dossier_payload.get("benchmark_reference_lines"))
        and bool(dossier_payload.get("support_strength_lines"))
        and bool(dossier_payload.get("claim_summaries"))
        and any(
            line.startswith("Promotion status: ") for line in dossier_payload.get("summary_lines", [])
        )
        and any(
            line.startswith("Highlighted regime stability: ")
            for line in dossier_payload.get("summary_lines", [])
        )
        and any(
            line.startswith("Highlighted transport stability: ")
            for line in dossier_payload.get("summary_lines", [])
        )
        and (
            dossier_payload.get("model_family") != "advective_screening_mass_balance"
            or any(
                line.startswith("Transport authority support: ")
                for line in dossier_payload.get("summary_lines", [])
            )
        )
        and (
            dossier_payload.get("model_family") != "advective_screening_mass_balance"
            or any(
                line.startswith("Transport transition support: ")
                for line in dossier_payload.get("summary_lines", [])
            )
        )
        and any(
            line.startswith("External corroboration breadth: ")
            for line in dossier_payload.get("summary_lines", [])
        )
        and (
            not any(
                item.get("claim_id") == "advective_loss_regime_flip_directionality_v1"
                and item.get("covered")
                for item in dossier_payload.get("claim_summaries", [])
            )
            or any(
                line.startswith("Transition sensitivity support: ")
                for line in dossier_payload.get("summary_lines", [])
            )
        )
        and (
            not any(
                item.get("claim_id") == "advective_post_release_flushing_recovery_v1"
                and item.get("covered")
                for item in dossier_payload.get("claim_summaries", [])
            )
            or any(
                line.startswith("Post-release recovery support: ")
                for line in dossier_payload.get("summary_lines", [])
            )
        )
        and (
            not any(
                item.get("claim_id") == "advective_post_release_flushing_regime_transition_v1"
                and item.get("covered")
                for item in dossier_payload.get("claim_summaries", [])
            )
            or any(
                line.startswith("Post-release regime support: ")
                for line in dossier_payload.get("summary_lines", [])
            )
        )
        and (
            not any(
                item.get("claim_id") == "advective_post_release_flushing_regime_transition_v1"
                and item.get("covered")
                for item in dossier_payload.get("claim_summaries", [])
            )
            or any(
                line.startswith("Post-release directionality support: ")
                for line in dossier_payload.get("summary_lines", [])
            )
        )
        and (
            not dossier_payload.get("promotion_blocker_summaries")
            or any(
                line.startswith("Promotion blocker: ")
                for line in dossier_payload.get("summary_lines", [])
            )
        )
        and (
            dossier_payload.get("promotion_status") != "blocked"
            or bool(dossier_payload.get("promotion_blocker_summaries"))
        )
    )
    claim_summary_consistent = (
        claim_summary_payload.get("claim_id")
        == dossier_payload.get("claim_summaries", [{}])[0].get("claim_id")
        and bool(claim_summary_payload.get("source_references"))
        and bool(claim_summary_payload.get("external_corroboration_status"))
        and "external_corroboration_source_count" in claim_summary_payload
        and "external_corroboration_jurisdictions" in claim_summary_payload
        and bool(claim_summary_payload.get("external_corroboration_lines"))
        and bool(claim_summary_payload.get("source_grounding_lines"))
        and bool(claim_summary_payload.get("methods_basis_lines"))
        and bool(claim_summary_payload.get("reference_case_lines"))
        and bool(claim_summary_payload.get("reference_case_concept_lines"))
    )
    brief_consistent = (
        brief_request_payload.get("dossier", {}).get("dossier_id") == brief_payload.get("dossier_id")
        and brief_payload.get("model_family") == dossier_payload.get("model_family")
        and brief_payload.get("run_mode_filter") == dossier_payload.get("run_mode_filter")
        and brief_payload.get("claim_count") == dossier_payload.get("claim_count")
        and brief_payload.get("promotion_status") == dossier_payload.get("promotion_status")
        and brief_payload.get("blocking_action_count")
        == dossier_payload.get("blocking_action_count")
        and brief_payload.get("strengthening_action_count")
        == dossier_payload.get("strengthening_action_count")
        and brief_payload.get("promotion_blocker_claim_ids")
        == dossier_payload.get("promotion_blocker_claim_ids")
        and brief_payload.get("promotion_blocker_summaries")
        == dossier_payload.get("promotion_blocker_summaries")
        and brief_payload.get("mandatory_claim_count") == dossier_payload.get("mandatory_claim_count")
        and brief_payload.get("covered_mandatory_claim_count")
        == dossier_payload.get("covered_mandatory_claim_count")
        and brief_payload.get("uncovered_mandatory_claim_count")
        == dossier_payload.get("uncovered_mandatory_claim_count")
        and bool(brief_payload.get("highlighted_claim_ids"))
        and bool(brief_payload.get("highlighted_claim_summaries"))
        and brief_payload.get("recommended_action_summaries")
        == dossier_payload.get("recommended_action_summaries")
        and bool(brief_payload.get("summary_lines"))
        and brief_payload.get("highlighted_claim_ids")
        == [item.get("claim_id") for item in dossier_payload.get("highlighted_claim_summaries", [])]
        and brief_payload.get("highlighted_claim_summaries")
        == dossier_payload.get("highlighted_claim_summaries")
        and any(
            line.startswith("Highlighted claim [") for line in brief_payload.get("summary_lines", [])
        )
        and any(
            line.startswith("Promotion status: ") for line in brief_payload.get("summary_lines", [])
        )
        and any(
            line.startswith("Claim regime stability: ")
            for line in brief_payload.get("summary_lines", [])
        )
        and any(
            line.startswith("Claim regime context: ")
            for line in brief_payload.get("summary_lines", [])
        )
        and any(
            line.startswith("Claim transport stability: ")
            for line in brief_payload.get("summary_lines", [])
        )
        and any(
            line.startswith("Claim transport context: ")
            for line in brief_payload.get("summary_lines", [])
        )
        and any(
            line.startswith("Highlighted regime stability: ")
            for line in brief_payload.get("summary_lines", [])
        )
        and any(
            line.startswith("Highlighted transport stability: ")
            for line in brief_payload.get("summary_lines", [])
        )
        and any(
            line.startswith("Post-release regime stability: ")
            for line in brief_payload.get("summary_lines", [])
        )
        and (
            not brief_payload.get("promotion_blocker_summaries")
            or any(
                line.startswith("Promotion blocker: ")
                for line in brief_payload.get("summary_lines", [])
            )
        )
        and any(
            line.startswith("Claim corroboration status: ")
            for line in brief_payload.get("summary_lines", [])
        )
        and any(
            line.startswith("Claim corroboration: ") for line in brief_payload.get("summary_lines", [])
        )
        and any(
            line.startswith("Claim corroboration action: ")
            for line in brief_payload.get("summary_lines", [])
        )
        and (
            not brief_payload.get("recommended_actions")
            or any(
                line.startswith("Recommended action: ")
                for line in brief_payload.get("summary_lines", [])
            )
        )
        and (
            not brief_payload.get("recommended_action_summaries")
            or all(
                item.get("priority")
                and item.get("promotion_impact")
                and item.get("action_class")
                and item.get("action")
                for item in brief_payload.get("recommended_action_summaries", [])
            )
        )
        and brief_payload.get("source_grounding_lines") == dossier_payload.get("source_grounding_lines")
        and brief_payload.get("highlighted_claim_grounding_lines")
        == dossier_payload.get("highlighted_claim_grounding_lines")
        and brief_payload.get("reference_case_grounding_lines")
        == dossier_payload.get("reference_case_grounding_lines")
        and brief_payload.get("reference_case_concept_lines")
        == dossier_payload.get("reference_case_concept_lines")
        and brief_payload.get("benchmark_reference_lines") == dossier_payload.get("benchmark_reference_lines")
        and brief_payload.get("support_strength_lines") == dossier_payload.get("support_strength_lines")
        and brief_payload.get("recommended_actions") == dossier_payload.get("recommended_actions")
    )
    return {
        "passed": dossier_consistent and claim_summary_consistent and brief_consistent,
        "scientificMethodsDossierConsistent": dossier_consistent,
        "scientificMethodsDossierClaimSummaryConsistent": claim_summary_consistent,
        "scientificMethodsDossierBriefConsistent": brief_consistent,
    }


def validate_model_family_comparison_workflow(repo_root: Path) -> dict:
    request_payload = json.loads(
        (repo_root / "schemas" / "examples" / "buildModelFamilyComparisonPacketRequest.v1.json").read_text()
    )
    profile_payload = json.loads(
        (repo_root / "schemas" / "examples" / "modelFamilyComparisonProfile.v1.json").read_text()
    )
    profile_manifest_payload = json.loads(
        (repo_root / "schemas" / "examples" / "modelFamilyComparisonProfileManifest.v1.json").read_text()
    )
    packet_payload = json.loads(
        (repo_root / "schemas" / "examples" / "modelFamilyComparisonPacket.v1.json").read_text()
    )
    brief_payload = json.loads(
        (repo_root / "schemas" / "examples" / "modelFamilyComparisonBrief.v1.json").read_text()
    )

    request_consistent = (
        request_payload.get("base_model_family") != request_payload.get("candidate_model_family")
        and request_payload.get("comparison_profile_id") == profile_payload.get("profile_id")
        and request_payload.get("candidate_model_family") == "advective_screening_mass_balance"
        and request_payload.get("run_mode") == packet_payload.get("run_mode")
        and request_payload.get("fit_for_purpose") == packet_payload.get("fit_for_purpose")
    )
    profile_manifest_consistent = (
        profile_manifest_payload.get("profile_count", 0) >= 1
        and profile_payload.get("base_model_family") == "reference_mass_balance"
        and profile_payload.get("candidate_model_family") == "advective_screening_mass_balance"
        and bool(profile_payload.get("supported_run_modes"))
        and bool(profile_payload.get("packet_template"))
        and bool(profile_payload.get("brief_template"))
        and bool(profile_payload.get("comparable_outcome_template"))
        and bool(profile_payload.get("divergence_outcome_template"))
        and bool(profile_payload.get("review_needed_outcome_template"))
    )
    packet_consistent = (
        packet_payload.get("scenario_id") == request_payload.get("scenario", {}).get("scenario_id")
        and packet_payload.get("comparison_profile_id") == profile_payload.get("profile_id")
        and packet_payload.get("base_model_family") == request_payload.get("base_model_family")
        and packet_payload.get("candidate_model_family") == request_payload.get("candidate_model_family")
        and packet_payload.get("base_fit_assessment", {}).get("model_family")
        == packet_payload.get("base_model_family")
        and packet_payload.get("candidate_fit_assessment", {}).get("model_family")
        == packet_payload.get("candidate_model_family")
        and packet_payload.get("comparison", {}).get("base_scenario_id") == packet_payload.get("scenario_id")
        and packet_payload.get("comparison", {}).get("candidate_scenario_id") == packet_payload.get("scenario_id")
        and bool(packet_payload.get("comparison", {}).get("surface_deltas"))
        and bool(packet_payload.get("base_surface_samples"))
        and bool(packet_payload.get("candidate_surface_samples"))
        and bool(packet_payload.get("dominant_delta_lines"))
        and bool(packet_payload.get("base_benchmark_reference_lines"))
        and bool(packet_payload.get("candidate_benchmark_reference_lines"))
        and bool(packet_payload.get("base_equation_lines"))
        and bool(packet_payload.get("candidate_equation_lines"))
        and bool(packet_payload.get("outcome_lines"))
        and bool(packet_payload.get("packet_template_used"))
        and bool(packet_payload.get("brief_template_used"))
        and bool(packet_payload.get("recommended_actions"))
    )
    experimental_candidate_flagged = any(
        note.get("code") == "experimental_candidate_model_family"
        for note in packet_payload.get("limitations", [])
    )
    brief_consistent = (
        brief_payload.get("comparison_packet_id") == packet_payload.get("comparison_packet_id")
        and brief_payload.get("scenario_id") == packet_payload.get("scenario_id")
        and brief_payload.get("base_model_family") == packet_payload.get("base_model_family")
        and brief_payload.get("candidate_model_family") == packet_payload.get("candidate_model_family")
        and brief_payload.get("comparison_outcome") == packet_payload.get("comparison_outcome")
        and brief_payload.get("dominant_delta_lines") == packet_payload.get("dominant_delta_lines")
        and brief_payload.get("comparison_profile_id") == packet_payload.get("comparison_profile_id")
        and brief_payload.get("outcome_lines") == packet_payload.get("outcome_lines")
        and brief_payload.get("brief_template_used") == packet_payload.get("brief_template_used")
        and brief_payload.get("recommended_actions") == packet_payload.get("recommended_actions")
        and bool(brief_payload.get("base_equation_lines"))
        and bool(brief_payload.get("candidate_equation_lines"))
    )
    return {
        "passed": (
            request_consistent
            and profile_manifest_consistent
            and packet_consistent
            and experimental_candidate_flagged
            and brief_consistent
        ),
        "modelFamilyComparisonRequestConsistent": request_consistent,
        "modelFamilyComparisonProfileManifestConsistent": profile_manifest_consistent,
        "modelFamilyComparisonPacketConsistent": packet_consistent,
        "experimentalCandidateFlagged": experimental_candidate_flagged,
        "modelFamilyComparisonBriefConsistent": brief_consistent,
    }


def validate_model_family_selection_workflow(repo_root: Path) -> dict:
    request_payload = json.loads(
        (repo_root / "schemas" / "examples" / "recommendModelFamilySelectionRequest.v1.json").read_text()
    )
    profile_payload = json.loads(
        (repo_root / "schemas" / "examples" / "modelFamilySelectionProfile.v1.json").read_text()
    )
    manifest_payload = json.loads(
        (repo_root / "schemas" / "examples" / "modelFamilySelectionProfileManifest.v1.json").read_text()
    )
    recommendation_payload = json.loads(
        (repo_root / "schemas" / "examples" / "modelFamilySelectionRecommendation.v1.json").read_text()
    )

    request_consistent = (
        request_payload.get("scenario", {}).get("scenario_id") == recommendation_payload.get("scenario_id")
        and request_payload.get("selection_profile_id") == profile_payload.get("profile_id")
        and request_payload.get("run_mode") == recommendation_payload.get("run_mode")
        and request_payload.get("fit_for_purpose") == recommendation_payload.get("fit_for_purpose")
    )
    profile_manifest_consistent = (
        manifest_payload.get("profile_count", 0) >= 1
        and profile_payload.get("default_model_family") == "reference_mass_balance"
        and profile_payload.get("challenge_model_family") == "advective_screening_mass_balance"
        and bool(profile_payload.get("comparison_profile_id"))
        and bool(profile_payload.get("trigger_parameter_names"))
        and bool(profile_payload.get("default_recommendation_template"))
        and bool(profile_payload.get("challenge_recommendation_template"))
        and bool(profile_payload.get("review_needed_template"))
    )
    recommendation_consistent = (
        recommendation_payload.get("selection_profile_id") == profile_payload.get("profile_id")
        and recommendation_payload.get("primary_model_family") == profile_payload.get("default_model_family")
        and recommendation_payload.get("challenge_model_family") == profile_payload.get("challenge_model_family")
        and recommendation_payload.get("comparison_profile_id") == profile_payload.get("comparison_profile_id")
        and recommendation_payload.get("recommendation_status") == "default_with_experimental_challenge"
        and bool(recommendation_payload.get("triggered_signal_lines"))
        and bool(recommendation_payload.get("summary_lines"))
        and bool(recommendation_payload.get("recommended_actions"))
        and bool(recommendation_payload.get("recommendation_template_used"))
        and recommendation_payload.get("primary_fit_assessment", {}).get("model_family")
        == profile_payload.get("default_model_family")
        and recommendation_payload.get("challenge_fit_assessment", {}).get("model_family")
        == profile_payload.get("challenge_model_family")
    )
    return {
        "passed": request_consistent and profile_manifest_consistent and recommendation_consistent,
        "modelFamilySelectionRequestConsistent": request_consistent,
        "modelFamilySelectionProfileManifestConsistent": profile_manifest_consistent,
        "modelFamilySelectionRecommendationConsistent": recommendation_consistent,
    }


def validate_model_family_selection_review_workflow(repo_root: Path) -> dict:
    preview_request_payload = json.loads(
        (repo_root / "schemas" / "examples" / "previewModelFamilySelectionReviewRequest.v1.json").read_text()
    )
    packet_request_payload = json.loads(
        (repo_root / "schemas" / "examples" / "buildModelFamilySelectionReviewPacketRequest.v1.json").read_text()
    )
    brief_request_payload = json.loads(
        (repo_root / "schemas" / "examples" / "buildModelFamilySelectionReviewBriefRequest.v1.json").read_text()
    )
    profile_payload = json.loads(
        (repo_root / "schemas" / "examples" / "modelFamilySelectionProfile.v1.json").read_text()
    )
    recommendation_payload = json.loads(
        (repo_root / "schemas" / "examples" / "modelFamilySelectionRecommendation.v1.json").read_text()
    )
    preview_payload = json.loads(
        (repo_root / "schemas" / "examples" / "modelFamilySelectionReviewPreview.v1.json").read_text()
    )
    review_packet_payload = json.loads(
        (repo_root / "schemas" / "examples" / "modelFamilySelectionReviewPacket.v1.json").read_text()
    )
    review_brief_payload = json.loads(
        (repo_root / "schemas" / "examples" / "modelFamilySelectionReviewBrief.v1.json").read_text()
    )

    preview_consistent = (
        preview_request_payload.get("selection_recommendation", {}).get("scenario_id")
        == preview_payload.get("scenario_id")
        and preview_payload.get("selection_profile_id") == profile_payload.get("profile_id")
        and preview_payload.get("recommendation_status") == recommendation_payload.get("recommendation_status")
        and bool(preview_payload.get("governing_rule_lines"))
        and bool(preview_payload.get("status_rule_lines"))
        and bool(preview_payload.get("recommended_actions"))
    )
    review_packet_consistent = (
        packet_request_payload.get("selection_recommendation", {}).get("scenario_id")
        == review_packet_payload.get("scenario_id")
        and review_packet_payload.get("selection_profile_id") == profile_payload.get("profile_id")
        and review_packet_payload.get("review_preview", {}).get("scenario_id")
        == review_packet_payload.get("scenario_id")
        and review_packet_payload.get("review_status")
        == review_packet_payload.get("review_preview", {}).get("review_status")
        and bool(review_packet_payload.get("checks"))
        and bool(review_packet_payload.get("review_checklist"))
        and bool(review_packet_payload.get("summary_lines"))
        and bool(review_packet_payload.get("triggered_signal_lines"))
        and bool(review_packet_payload.get("primary_applicability_lines"))
        and bool(review_packet_payload.get("comparison_guidance_lines"))
        and bool(review_packet_payload.get("review_template_used"))
    )
    review_brief_consistent = (
        brief_request_payload.get("review_packet", {}).get("review_packet_id")
        == review_brief_payload.get("review_packet_id")
        and review_brief_payload.get("scenario_id") == review_packet_payload.get("scenario_id")
        and review_brief_payload.get("selection_profile_id") == review_packet_payload.get("selection_profile_id")
        and review_brief_payload.get("recommendation_status")
        == review_packet_payload.get("recommendation_status")
        and review_brief_payload.get("review_status") == review_packet_payload.get("review_status")
        and bool(review_brief_payload.get("checklist_items"))
        and bool(review_brief_payload.get("brief_lines"))
        and bool(review_brief_payload.get("comparison_guidance_lines"))
    )
    return {
        "passed": preview_consistent and review_packet_consistent and review_brief_consistent,
        "modelFamilySelectionReviewPreviewConsistent": preview_consistent,
        "modelFamilySelectionReviewPacketConsistent": review_packet_consistent,
        "modelFamilySelectionReviewBriefConsistent": review_brief_consistent,
    }


def validate_model_family_comparison_review_workflow(repo_root: Path) -> dict:
    preview_request_payload = json.loads(
        (repo_root / "schemas" / "examples" / "previewModelFamilyComparisonReviewRequest.v1.json").read_text()
    )
    packet_request_payload = json.loads(
        (repo_root / "schemas" / "examples" / "buildModelFamilyComparisonReviewPacketRequest.v1.json").read_text()
    )
    brief_request_payload = json.loads(
        (repo_root / "schemas" / "examples" / "buildModelFamilyComparisonReviewBriefRequest.v1.json").read_text()
    )
    profile_payload = json.loads(
        (repo_root / "schemas" / "examples" / "modelFamilyComparisonProfile.v1.json").read_text()
    )
    preview_payload = json.loads(
        (repo_root / "schemas" / "examples" / "modelFamilyComparisonReviewPreview.v1.json").read_text()
    )
    review_packet_payload = json.loads(
        (repo_root / "schemas" / "examples" / "modelFamilyComparisonReviewPacket.v1.json").read_text()
    )
    review_brief_payload = json.loads(
        (repo_root / "schemas" / "examples" / "modelFamilyComparisonReviewBrief.v1.json").read_text()
    )

    preview_consistent = (
        preview_request_payload.get("comparison_packet", {}).get("comparison_packet_id")
        == preview_payload.get("comparison_packet_id")
        and preview_payload.get("comparison_profile_id") == profile_payload.get("profile_id")
        and bool(preview_payload.get("outcome_lines"))
        and bool(preview_payload.get("recommended_actions"))
        and bool(preview_payload.get("status_rule_lines"))
    )
    review_packet_consistent = (
        packet_request_payload.get("comparison_packet", {}).get("comparison_packet_id")
        == review_packet_payload.get("comparison_packet_id")
        and review_packet_payload.get("comparison_profile_id") == profile_payload.get("profile_id")
        and review_packet_payload.get("review_preview", {}).get("comparison_packet_id")
        == review_packet_payload.get("comparison_packet_id")
        and review_packet_payload.get("review_status")
        == review_packet_payload.get("review_preview", {}).get("review_status")
        and bool(review_packet_payload.get("checks"))
        and bool(review_packet_payload.get("review_checklist"))
        and bool(review_packet_payload.get("summary_lines"))
        and bool(review_packet_payload.get("dominant_delta_lines"))
        and bool(review_packet_payload.get("base_applicability_lines"))
        and bool(review_packet_payload.get("candidate_applicability_lines"))
        and bool(review_packet_payload.get("base_benchmark_reference_lines"))
        and bool(review_packet_payload.get("candidate_benchmark_reference_lines"))
        and bool(review_packet_payload.get("base_equation_lines"))
        and bool(review_packet_payload.get("candidate_equation_lines"))
        and bool(review_packet_payload.get("review_template_used"))
    )
    review_brief_consistent = (
        brief_request_payload.get("review_packet", {}).get("review_packet_id")
        == review_brief_payload.get("review_packet_id")
        and review_brief_payload.get("comparison_packet_id")
        == review_packet_payload.get("comparison_packet_id")
        and review_brief_payload.get("comparison_profile_id")
        == review_packet_payload.get("comparison_profile_id")
        and review_brief_payload.get("review_status")
        == review_packet_payload.get("review_status")
        and bool(review_brief_payload.get("checklist_items"))
        and bool(review_brief_payload.get("brief_lines"))
        and bool(review_brief_payload.get("base_applicability_lines"))
        and bool(review_brief_payload.get("candidate_applicability_lines"))
        and bool(review_brief_payload.get("base_equation_lines"))
        and bool(review_brief_payload.get("candidate_equation_lines"))
        and bool(review_brief_payload.get("review_template_used"))
    )
    profile_review_governance_consistent = (
        bool(profile_payload.get("review_checklist"))
        and bool(profile_payload.get("review_packet_template"))
        and bool(profile_payload.get("review_brief_template"))
        and bool(profile_payload.get("ready_comparison_outcomes"))
        and profile_payload.get("attention_outcomes") is not None
        and profile_payload.get("attention_if_any_checks_fail") is not None
        and profile_payload.get("attention_if_candidate_experimental") is not None
    )
    return {
        "passed": (
            preview_consistent
            and review_packet_consistent
            and review_brief_consistent
            and profile_review_governance_consistent
        ),
        "modelFamilyComparisonReviewPreviewConsistent": preview_consistent,
        "modelFamilyComparisonReviewPacketConsistent": review_packet_consistent,
        "modelFamilyComparisonReviewBriefConsistent": review_brief_consistent,
        "modelFamilyComparisonReviewGovernanceConsistent": profile_review_governance_consistent,
    }


def validate_model_family_challenge_review_workflow(repo_root: Path) -> dict:
    preview_request_payload = json.loads(
        (repo_root / "schemas" / "examples" / "previewModelFamilyChallengeReviewRequest.v1.json").read_text()
    )
    packet_request_payload = json.loads(
        (repo_root / "schemas" / "examples" / "buildModelFamilyChallengeReviewPacketRequest.v1.json").read_text()
    )
    profile_payload = json.loads(
        (repo_root / "schemas" / "examples" / "modelFamilyChallengeReviewProfile.v1.json").read_text()
    )
    manifest_payload = json.loads(
        (repo_root / "schemas" / "examples" / "modelFamilyChallengeReviewProfileManifest.v1.json").read_text()
    )
    preview_payload = json.loads(
        (repo_root / "schemas" / "examples" / "modelFamilyChallengeReviewPreview.v1.json").read_text()
    )
    brief_request_payload = json.loads(
        (repo_root / "schemas" / "examples" / "buildModelFamilyChallengeReviewBriefRequest.v1.json").read_text()
    )
    packet_payload = json.loads(
        (repo_root / "schemas" / "examples" / "modelFamilyChallengeReviewPacket.v1.json").read_text()
    )
    brief_payload = json.loads(
        (repo_root / "schemas" / "examples" / "modelFamilyChallengeReviewBrief.v1.json").read_text()
    )

    preview_consistent = (
        preview_request_payload.get("scenario", {}).get("scenario_id") == preview_payload.get("scenario_id")
        and preview_request_payload.get("selection_profile_id") == preview_payload.get("selection_profile_id")
        and preview_payload.get("challenge_review_profile_id") == profile_payload.get("profile_id")
        and preview_request_payload.get("run_mode") == packet_payload.get("run_mode")
        and preview_payload.get("review_status") == packet_payload.get("review_status")
        and preview_payload.get("selection_review_status") == packet_payload.get("selection_review_status")
        and preview_payload.get("comparison_review_status") == packet_payload.get("comparison_review_status")
        and bool(preview_payload.get("triggered_check_codes"))
        and bool(preview_payload.get("governing_rule_lines"))
        and bool(preview_payload.get("status_rule_lines"))
        and bool(preview_payload.get("recommended_actions"))
    )
    profile_manifest_consistent = (
        manifest_payload.get("profile_count", 0) >= 1
        and profile_payload.get("selection_profile_id") == "reference_baseline_advective_challenge_v1"
        and profile_payload.get("comparison_profile_id") == "reference_vs_advective_screening_v1"
        and bool(profile_payload.get("review_checklist"))
        and bool(profile_payload.get("review_packet_template"))
        and bool(profile_payload.get("review_brief_template"))
        and bool(profile_payload.get("ready_selection_review_statuses"))
        and bool(profile_payload.get("ready_comparison_review_statuses"))
    )
    request_consistent = (
        packet_request_payload.get("scenario", {}).get("scenario_id") == packet_payload.get("scenario_id")
        and packet_request_payload.get("selection_profile_id") == packet_payload.get("selection_profile_id")
        and packet_request_payload.get("run_mode") == packet_payload.get("run_mode")
        and packet_request_payload.get("fit_for_purpose") == packet_payload.get("fit_for_purpose")
    )
    packet_consistent = (
        packet_payload.get("selection_recommendation", {}).get("scenario_id") == packet_payload.get("scenario_id")
        and packet_payload.get("selection_review_packet", {}).get("scenario_id") == packet_payload.get("scenario_id")
        and packet_payload.get("challenge_review_profile_id") == profile_payload.get("profile_id")
        and packet_payload.get("selection_recommendation_status")
        == packet_payload.get("selection_recommendation", {}).get("recommendation_status")
        and packet_payload.get("selection_recommendation_status")
        == packet_payload.get("selection_review_packet", {}).get("recommendation_status")
        and packet_payload.get("selection_review_status")
        == packet_payload.get("selection_review_packet", {}).get("review_status")
        and packet_payload.get("review_preview", {}).get("scenario_id") == packet_payload.get("scenario_id")
        and packet_payload.get("review_status")
        == packet_payload.get("review_preview", {}).get("review_status")
        and packet_payload.get("review_preview", {}).get("challenge_review_profile_id")
        == packet_payload.get("challenge_review_profile_id")
        and bool(packet_payload.get("checks"))
        and bool(packet_payload.get("review_checklist"))
        and bool(packet_payload.get("summary_lines"))
        and bool(packet_payload.get("governing_rule_lines"))
        and bool(packet_payload.get("triggered_signal_lines"))
        and bool(packet_payload.get("primary_applicability_lines"))
        and bool(packet_payload.get("recommended_actions"))
        and packet_payload.get("review_template_used") == profile_payload.get("review_packet_template")
    )
    comparison_consistent = (
        packet_payload.get("comparison_profile_id") is not None
        and packet_payload.get("comparison_packet", {}).get("scenario_id") == packet_payload.get("scenario_id")
        and packet_payload.get("comparison_review_packet", {}).get("scenario_id") == packet_payload.get("scenario_id")
        and packet_payload.get("comparison_profile_id")
        == packet_payload.get("comparison_packet", {}).get("comparison_profile_id")
        and packet_payload.get("comparison_profile_id")
        == packet_payload.get("comparison_review_packet", {}).get("comparison_profile_id")
        and packet_payload.get("comparison_outcome")
        == packet_payload.get("comparison_review_packet", {}).get("comparison_outcome")
        and packet_payload.get("comparison_review_status")
        == packet_payload.get("comparison_review_packet", {}).get("review_status")
        and bool(packet_payload.get("dominant_delta_lines"))
        and bool(packet_payload.get("comparison_guidance_lines"))
    )
    brief_consistent = (
        brief_request_payload.get("review_packet", {}).get("review_packet_id")
        == brief_payload.get("review_packet_id")
        and brief_payload.get("scenario_id") == packet_payload.get("scenario_id")
        and brief_payload.get("selection_profile_id") == packet_payload.get("selection_profile_id")
        and brief_payload.get("challenge_review_profile_id") == packet_payload.get("challenge_review_profile_id")
        and brief_payload.get("review_status") == packet_payload.get("review_status")
        and brief_payload.get("selection_recommendation_status")
        == packet_payload.get("selection_recommendation_status")
        and brief_payload.get("selection_review_status") == packet_payload.get("selection_review_status")
        and brief_payload.get("comparison_profile_id") == packet_payload.get("comparison_profile_id")
        and brief_payload.get("comparison_outcome") == packet_payload.get("comparison_outcome")
        and brief_payload.get("comparison_review_status") == packet_payload.get("comparison_review_status")
        and brief_payload.get("passed_check_count", 0) <= brief_payload.get("total_check_count", 0)
        and bool(brief_payload.get("checklist_items"))
        and brief_payload.get("review_template_used") == profile_payload.get("review_brief_template")
        and brief_payload.get("dominant_delta_lines") == packet_payload.get("dominant_delta_lines")
        and brief_payload.get("comparison_guidance_lines") == packet_payload.get("comparison_guidance_lines")
        and bool(brief_payload.get("brief_lines"))
    )
    return {
        "passed": (
            preview_consistent
            and profile_manifest_consistent
            and request_consistent
            and packet_consistent
            and comparison_consistent
            and brief_consistent
        ),
        "modelFamilyChallengeReviewPreviewConsistent": preview_consistent,
        "modelFamilyChallengeReviewProfileManifestConsistent": profile_manifest_consistent,
        "modelFamilyChallengeReviewRequestConsistent": request_consistent,
        "modelFamilyChallengeReviewPacketConsistent": packet_consistent,
        "modelFamilyChallengeReviewComparisonConsistent": comparison_consistent,
        "modelFamilyChallengeReviewBriefConsistent": brief_consistent,
    }


def validate_model_family_challenge_scientific_dossier_workflow(repo_root: Path) -> dict:
    dossier_request_payload = json.loads(
        (repo_root / "schemas" / "examples" / "buildModelFamilyChallengeScientificDossierRequest.v1.json").read_text()
    )
    dossier_payload = json.loads(
        (repo_root / "schemas" / "examples" / "modelFamilyChallengeScientificDossier.v1.json").read_text()
    )
    brief_request_payload = json.loads(
        (repo_root / "schemas" / "examples" / "buildModelFamilyChallengeScientificDossierBriefRequest.v1.json").read_text()
    )
    brief_payload = json.loads(
        (repo_root / "schemas" / "examples" / "modelFamilyChallengeScientificDossierBrief.v1.json").read_text()
    )

    dossier_consistent = (
        dossier_request_payload.get("scenario", {}).get("scenario_id") == dossier_payload.get("scenario_id")
        and dossier_request_payload.get("selection_profile_id") == dossier_payload.get("selection_profile_id")
        and dossier_request_payload.get("run_mode") == dossier_payload.get("run_mode")
        and dossier_request_payload.get("fit_for_purpose") == dossier_payload.get("fit_for_purpose")
        and dossier_payload.get("challenge_review_brief", {}).get("scenario_id") == dossier_payload.get("scenario_id")
        and dossier_payload.get("challenge_review_profile_id")
        == dossier_payload.get("challenge_review_brief", {}).get("challenge_review_profile_id")
        and dossier_payload.get("challenge_review_status")
        == dossier_payload.get("challenge_review_brief", {}).get("review_status")
        and dossier_payload.get("selection_recommendation_status")
        == dossier_payload.get("challenge_review_brief", {}).get("selection_recommendation_status")
        and dossier_payload.get("primary_model_family")
        == dossier_payload.get("primary_scientific_review_brief", {}).get("model_family")
    )
    dossier_consistent = dossier_consistent and (
        dossier_payload.get("primary_scientific_review_brief", {}).get("scenario_id")
        == dossier_payload.get("scenario_id")
        and dossier_payload.get("primary_equation_lines")
        == dossier_payload.get("primary_scientific_review_brief", {}).get("equation_lines")
        and dossier_payload.get("primary_benchmark_reference_lines")
        == dossier_payload.get("primary_scientific_review_brief", {}).get("benchmark_reference_lines")
        and bool(dossier_payload.get("summary_lines"))
        and bool(dossier_payload.get("recommended_actions"))
    )
    challenge_brief = dossier_payload.get("challenge_scientific_review_brief")
    challenge_consistent = (
        challenge_brief is None
        or (
            dossier_payload.get("challenge_model_family") == challenge_brief.get("model_family")
            and challenge_brief.get("scenario_id") == dossier_payload.get("scenario_id")
            and dossier_payload.get("challenge_equation_lines") == challenge_brief.get("equation_lines")
            and dossier_payload.get("challenge_benchmark_reference_lines")
            == challenge_brief.get("benchmark_reference_lines")
        )
    )
    brief_consistent = (
        brief_request_payload.get("dossier", {}).get("dossier_id") == brief_payload.get("dossier_id")
        and brief_payload.get("scenario_id") == dossier_payload.get("scenario_id")
        and brief_payload.get("selection_profile_id") == dossier_payload.get("selection_profile_id")
        and brief_payload.get("challenge_review_profile_id") == dossier_payload.get("challenge_review_profile_id")
        and brief_payload.get("primary_model_family") == dossier_payload.get("primary_model_family")
        and brief_payload.get("challenge_model_family") == dossier_payload.get("challenge_model_family")
        and brief_payload.get("challenge_review_status") == dossier_payload.get("challenge_review_status")
        and brief_payload.get("selection_recommendation_status")
        == dossier_payload.get("selection_recommendation_status")
        and brief_payload.get("comparison_profile_id") == dossier_payload.get("comparison_profile_id")
        and brief_payload.get("comparison_outcome") == dossier_payload.get("comparison_outcome")
        and brief_payload.get("primary_review_outcome")
        == dossier_payload.get("primary_scientific_review_brief", {}).get("review_outcome")
        and brief_payload.get("primary_passed_check_count", 0)
        <= brief_payload.get("primary_total_check_count", 0)
        and brief_payload.get("primary_equation_lines") == dossier_payload.get("primary_equation_lines")
        and brief_payload.get("primary_benchmark_reference_lines")
        == dossier_payload.get("primary_benchmark_reference_lines")
        and bool(brief_payload.get("summary_lines"))
    )
    if challenge_brief is not None:
        brief_consistent = brief_consistent and (
            brief_payload.get("challenge_review_outcome") == challenge_brief.get("review_outcome")
            and brief_payload.get("challenge_passed_check_count", 0)
            <= brief_payload.get("challenge_total_check_count", 0)
            and brief_payload.get("challenge_equation_lines") == dossier_payload.get("challenge_equation_lines")
            and brief_payload.get("challenge_benchmark_reference_lines")
            == dossier_payload.get("challenge_benchmark_reference_lines")
        )
    return {
        "passed": dossier_consistent and challenge_consistent and brief_consistent,
        "modelFamilyChallengeScientificDossierConsistent": dossier_consistent,
        "modelFamilyChallengeScientificDossierChallengeConsistent": challenge_consistent,
        "modelFamilyChallengeScientificDossierBriefConsistent": brief_consistent,
    }


def validation_dossier(repo_root: Path) -> dict:
    generate_contract_artifacts(repo_root)
    return {
        "artifacts": validate_generated_artifacts(repo_root),
        "benchmarks": run_benchmarks(repo_root),
        "failureModes": validate_failure_modes(repo_root),
        "downstreamInteroperability": validate_downstream_interoperability(repo_root),
        "regulatoryHandoffGovernance": validate_regulatory_handoff_governance(repo_root),
        "adapterInteroperability": validate_adapter_interoperability(repo_root),
        "reconciliationTransparency": validate_reconciliation_transparency(repo_root),
        "scientificReviewArtifacts": validate_scientific_review_artifacts(repo_root),
        "scientificClaimCoverage": validate_scientific_claim_coverage(repo_root),
        "scientificReviewWorkflow": validate_scientific_review_workflow(repo_root),
        "scientificMethodsDossierWorkflow": validate_scientific_methods_dossier_workflow(repo_root),
        "modelFamilySelectionWorkflow": validate_model_family_selection_workflow(repo_root),
        "modelFamilySelectionReviewWorkflow": validate_model_family_selection_review_workflow(repo_root),
        "modelFamilyChallengeReviewWorkflow": validate_model_family_challenge_review_workflow(repo_root),
        "modelFamilyChallengeScientificDossierWorkflow": validate_model_family_challenge_scientific_dossier_workflow(repo_root),
        "modelFamilyComparisonWorkflow": validate_model_family_comparison_workflow(repo_root),
        "modelFamilyComparisonReviewWorkflow": validate_model_family_comparison_review_workflow(repo_root),
    }


def main() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    generate_contract_artifacts(repo_root)
    validation_dossier(repo_root)


if __name__ == "__main__":
    main()
