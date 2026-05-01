from __future__ import annotations

import importlib
import json
from pathlib import Path

from pydantic import ValidationError

from fate_mcp.benchmarks import (
    benchmark_manifest,
    run_benchmarks,
    scientific_validation_claim_coverage_manifest,
    supporting_benchmark_fixtures_for_claim,
)
from fate_mcp.contracts import SCHEMA_MODELS, generate_contract_artifacts
from fate_mcp.defaults import DefaultsRegistry
from fate_mcp.errors import FateValidationError
from fate_mcp.integrations import (
    assess_erosion_sediment_validation_fit,
    assess_release_scenario_fit,
    build_erosion_sediment_validation_case,
    build_run_parameter_manifest,
    build_run_uncertainty_summary,
    preview_regulatory_handoff_resolution,
)
from fate_mcp.models import (
    BuildEnvironmentalReleaseScenarioRequest,
    AssessErosionSedimentValidationFitRequest,
    BuildErosionSedimentValidationCaseRequest,
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
from fate_mcp.plugins.external_result_adapter import (
    build_public_adapter_import_manifest,
    load_external_payload,
    normalize_external_payload,
)
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

    example_manifest_path = example_dir / "manifest.json"
    if not example_manifest_path.exists():
        results["examples"].append({"name": "manifest.json", "status": "missing"})
    else:
        manifest_payload = json.loads(example_manifest_path.read_text())
        for item in manifest_payload.get("examples", []):
            expected_name = item["name"]
            expected_path = example_dir / f"{expected_name}.json"
            if not expected_path.exists():
                results["examples"].append({"name": f"{expected_name}.json", "status": "missing"})

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

    bundle_required = [
        "scenario_id",
        "surfaces",
        "run_summary",
        "assumptions",
        "dependencies",
        "integrity_hash",
        "regulatory_use_disclaimer",
    ]
    package_required = ["scenario_id", "surfaces", "geographic_scope", "time_semantics", "provenance"]
    regulatory_required = [
        "scenario_id",
        "source_module",
        "source_model_family",
        "target_modules",
        "crosswalk_entries",
        "provenance",
        "integrity_hash",
        "regulatory_use_disclaimer",
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
    bundle_has_integrity_hash = bool(bundle_payload.get("integrity_hash"))
    bundle_has_regulatory_use_disclaimer = bool(bundle_payload.get("regulatory_use_disclaimer"))
    regulatory_package_has_integrity_hash = bool(regulatory_package_payload.get("integrity_hash"))
    regulatory_package_has_regulatory_use_disclaimer = bool(
        regulatory_package_payload.get("regulatory_use_disclaimer")
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
        and bundle_has_integrity_hash
        and bundle_has_regulatory_use_disclaimer
        and regulatory_package_has_integrity_hash
        and regulatory_package_has_regulatory_use_disclaimer
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
        "bundleHasIntegrityHash": bundle_has_integrity_hash,
        "bundleHasRegulatoryUseDisclaimer": bundle_has_regulatory_use_disclaimer,
        "regulatoryPackageHasIntegrityHash": regulatory_package_has_integrity_hash,
        "regulatoryPackageHasRegulatoryUseDisclaimer": regulatory_package_has_regulatory_use_disclaimer,
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
    public_manifest = build_public_adapter_import_manifest(repo_root)
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
    public_profile_ids = sorted(profile.profile_id for profile in public_manifest.profiles)
    public_fixture_names = sorted(fixture.fixture_name for fixture in public_manifest.fixtures)
    time_bucket_bounds_preserved = all(
        surface.time_window.mode == RunMode.TIME_BUCKET
        and surface.time_window.start is not None
        and surface.time_window.end is not None
        for surface in legacy_time_bucket_result.surfaces
    )

    checks = [
        {
            "name": "normalized_json_csv_parity",
            "status": "ok" if json_csv_equivalent else "failed",
        },
        {
            "name": "adapter_unit_conversion_parity",
            "status": "ok" if alternate_unit_equivalent else "failed",
        },
        {
            "name": "adapter_basis_conversion_parity",
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
        {
            "name": "public_import_profiles_declared",
            "status": "ok"
            if public_profile_ids
            == ["normalized_external_payload_csv", "normalized_external_payload_json"]
            else "failed",
        },
        {
            "name": "public_import_fixtures_available",
            "status": "ok"
            if {
                "illustrative_external_engine_payload_csv",
                "illustrative_external_engine_payload_json",
            }.issubset(set(public_fixture_names))
            else "failed",
        },
    ]
    return {
        "passed": all(item["status"] == "ok" for item in checks),
        "checkCount": len(checks),
        "checks": checks,
        "contractScopeNote": (
            "These adapter checks verify canonical Fate MCP normalization parity across governed import "
            "paths. They do not certify source-engine scientific validity or scientific equivalence to "
            "native Environmental Fate MCP physics."
        ),
        "publicImportManifest": public_manifest.model_dump(mode="json"),
        "normalizedFixtureParity": {
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
        and bool(manifest.default_evidence_lines)
        and manifest.core_default_assumption_count >= 1
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
        "parameterManifestDefaultEvidenceStatus": manifest.default_evidence_status.value,
        "parameterManifestCoreDefaultAssumptionCount": manifest.core_default_assumption_count,
        "uncertaintySummaryConsistent": uncertainty_summary_consistent,
        "uncertaintyDriverCount": len(uncertainty_summary.top_drivers),
        "benchmarkMetadataComplete": benchmark_metadata_complete,
        "benchmarkMetadataFixtureCount": len(benchmark_fixtures),
        "surfacesHaveEquationTraces": surfaces_have_equation_traces,
    }


def validate_defaults_evidence_governance(repo_root: Path) -> dict:
    registry = DefaultsRegistry(repo_root)
    parameters = registry.core_defaults["parameters"]
    capacity_parameters = {
        "ambient_air_volume_m3",
        "surface_water_volume_m3",
        "agricultural_soil_mass_kg",
        "freshwater_sediment_mass_kg",
    }
    tier3_parameters = sorted(
        name
        for name, payload in parameters.items()
        if payload.get("evidenceTier") == "tier_3_internal_screening_assumption"
    )
    missing_effective_date_parameters = sorted(
        name for name, payload in parameters.items() if not payload.get("effectiveDate")
    )
    missing_source_reference_parameters = sorted(
        name for name in parameters if not registry.parameter_source_references(name)
    )
    missing_derivation_jurisdiction_parameters = sorted(
        name
        for name in parameters
        if not registry.parameter_derivation_metadata(name).get("jurisdiction")
    )
    missing_derivation_basis_parameters = sorted(
        name
        for name in parameters
        if not registry.parameter_derivation_metadata(name).get("basis")
    )
    missing_derivation_method_parameters = sorted(
        name
        for name in parameters
        if not registry.parameter_derivation_metadata(name).get("calculationMethod")
    )
    missing_derivation_validity_parameters = sorted(
        name
        for name in parameters
        if not registry.parameter_derivation_metadata(name).get("validityNote")
    )
    missing_previous_value_parameters = sorted(
        name for name, payload in parameters.items() if "previousValue" not in payload
    )
    missing_previous_effective_date_parameters = sorted(
        name for name, payload in parameters.items() if not payload.get("previousEffectiveDate")
    )
    missing_rebaseline_status_parameters = sorted(
        name for name, payload in parameters.items() if not payload.get("rebaselineStatus")
    )
    missing_scientific_change_note_parameters = sorted(
        name for name, payload in parameters.items() if not payload.get("scientificChangeNote")
    )
    missing_capacity_geometry_basis_parameters = sorted(
        name
        for name in capacity_parameters
        if not registry.parameter_derivation_metadata(name).get("assumedAreaM2")
        or not registry.parameter_derivation_metadata(name).get("depthM")
    )
    missing_capacity_mass_basis_parameters = sorted(
        name
        for name in {"agricultural_soil_mass_kg", "freshwater_sediment_mass_kg"}
        if not registry.parameter_derivation_metadata(name).get("bulkDensityKgPerM3")
    )
    legacy_continuity_parameters = sorted(
        name
        for name in parameters
        if registry.parameter_derivation_metadata(name).get("legacyContinuityOnly")
    )
    return {
        "passed": (
            not tier3_parameters
            and not missing_effective_date_parameters
            and not missing_source_reference_parameters
            and not missing_derivation_jurisdiction_parameters
            and not missing_derivation_basis_parameters
            and not missing_derivation_method_parameters
            and not missing_derivation_validity_parameters
            and not missing_previous_value_parameters
            and not missing_previous_effective_date_parameters
            and not missing_rebaseline_status_parameters
            and not missing_scientific_change_note_parameters
            and not missing_capacity_geometry_basis_parameters
            and not missing_capacity_mass_basis_parameters
            and not legacy_continuity_parameters
        ),
        "parameterCount": len(parameters),
        "tier3Parameters": tier3_parameters,
        "missingEffectiveDateParameters": missing_effective_date_parameters,
        "missingSourceReferenceParameters": missing_source_reference_parameters,
        "missingDerivationJurisdictionParameters": missing_derivation_jurisdiction_parameters,
        "missingDerivationBasisParameters": missing_derivation_basis_parameters,
        "missingDerivationMethodParameters": missing_derivation_method_parameters,
        "missingDerivationValidityParameters": missing_derivation_validity_parameters,
        "missingPreviousValueParameters": missing_previous_value_parameters,
        "missingPreviousEffectiveDateParameters": missing_previous_effective_date_parameters,
        "missingRebaselineStatusParameters": missing_rebaseline_status_parameters,
        "missingScientificChangeNoteParameters": missing_scientific_change_note_parameters,
        "missingCapacityGeometryBasisParameters": missing_capacity_geometry_basis_parameters,
        "missingCapacityMassBasisParameters": missing_capacity_mass_basis_parameters,
        "legacyContinuityParameters": legacy_continuity_parameters,
        "legacyContinuityImplicitSelectionBlocked": not legacy_continuity_parameters,
    }


def _has_required_guidance_source_type(
    source_types: set[str],
    required_prefixes: tuple[str, ...],
) -> bool:
    return any(
        any(source_type.startswith(prefix) for prefix in required_prefixes)
        for source_type in source_types
    )


def _claim_has_machine_readable_worksheet_support(claim_id: str) -> tuple[bool, list[str]]:
    worksheet_fixtures = [
        fixture["name"]
        for fixture in supporting_benchmark_fixtures_for_claim(claim_id)
        if fixture.get("reference_type", "").startswith("hand_worked_")
        and (fixture.get("expected_trace_terms") or fixture.get("expected_surfaces"))
    ]
    return bool(worksheet_fixtures), sorted(set(worksheet_fixtures))


def validate_external_corroboration_governance(repo_root: Path) -> dict:
    registry = DefaultsRegistry(repo_root)
    claim_manifest = registry.scientific_validation_claim_manifest()
    reference_required_source_type_prefixes = (
        "official_guidance",
        "official_modeling_guidance",
        "official_test_guideline",
    )
    advective_required_source_type_prefixes = (
        "official_guidance",
        "official_modeling_guidance",
    )
    missing_independent_evidence_family_claim_ids: list[str] = []
    missing_next_action_claim_ids: list[str] = []
    unresolved_independent_evidence_family_claim_ids: list[str] = []
    inconsistent_corroboration_status_claim_ids: list[str] = []
    reference_mandatory_insufficient_independent_evidence_claim_ids: list[str] = []
    reference_mandatory_missing_guidance_family_claim_ids: list[str] = []
    experimental_priority_insufficient_independent_evidence_claim_ids: list[str] = []
    experimental_priority_missing_guidance_family_claim_ids: list[str] = []

    for claim in claim_manifest.claims:
        requires_independent_evidence = (
            (claim.model_family.value == "reference_mass_balance" and claim.mandatory_for_release)
            or (
                claim.model_family.value in EXPERIMENTAL_MODEL_FAMILIES
                and claim.priority.value in {"high", "medium"}
            )
        )
        if requires_independent_evidence and not claim.independent_evidence_families:
            missing_independent_evidence_family_claim_ids.append(claim.claim_id)
        if not claim.next_corroboration_action:
            missing_next_action_claim_ids.append(claim.claim_id)
        resolved_cases = [
            registry.scientific_reference_case(case_id)
            for case_id in claim.independent_evidence_families
        ]
        if claim.independent_evidence_families and any(case is None for case in resolved_cases):
            unresolved_independent_evidence_family_claim_ids.append(claim.claim_id)
            resolved_cases = [case for case in resolved_cases if case is not None]
        source_type_set = {case.source_type for case in resolved_cases}
        jurisdiction_count = len(
            {
                jurisdiction
                for case in resolved_cases
                for jurisdiction in case.jurisdictions
            }
        )
        expected_status = "none"
        if claim.official_source_count == 1:
            expected_status = "single_official_source"
        elif claim.official_source_count >= 2 and jurisdiction_count >= 2:
            expected_status = "multi_official_multi_jurisdiction"
        elif claim.official_source_count >= 2:
            expected_status = "multi_official_single_jurisdiction"
        if claim.corroboration_status.value != expected_status:
            inconsistent_corroboration_status_claim_ids.append(claim.claim_id)

        if claim.model_family.value == "reference_mass_balance" and claim.mandatory_for_release:
            if len(claim.independent_evidence_families) < 2:
                reference_mandatory_insufficient_independent_evidence_claim_ids.append(claim.claim_id)
            if not _has_required_guidance_source_type(
                source_type_set,
                reference_required_source_type_prefixes,
            ):
                reference_mandatory_missing_guidance_family_claim_ids.append(claim.claim_id)
        if (
            claim.model_family.value in EXPERIMENTAL_MODEL_FAMILIES
            and claim.priority.value in {"high", "medium"}
        ):
            if len(claim.independent_evidence_families) < 2:
                experimental_priority_insufficient_independent_evidence_claim_ids.append(
                    claim.claim_id
                )
            if not _has_required_guidance_source_type(
                source_type_set,
                advective_required_source_type_prefixes,
            ):
                experimental_priority_missing_guidance_family_claim_ids.append(claim.claim_id)

    return {
        "passed": (
            not missing_independent_evidence_family_claim_ids
            and not missing_next_action_claim_ids
            and not unresolved_independent_evidence_family_claim_ids
            and not inconsistent_corroboration_status_claim_ids
            and not reference_mandatory_insufficient_independent_evidence_claim_ids
            and not reference_mandatory_missing_guidance_family_claim_ids
            and not experimental_priority_insufficient_independent_evidence_claim_ids
            and not experimental_priority_missing_guidance_family_claim_ids
        ),
        "claimCount": claim_manifest.claim_count,
        "missingIndependentEvidenceFamilyClaimIds": sorted(
            missing_independent_evidence_family_claim_ids
        ),
        "missingNextCorroborationActionClaimIds": sorted(missing_next_action_claim_ids),
        "unresolvedIndependentEvidenceFamilyClaimIds": sorted(
            unresolved_independent_evidence_family_claim_ids
        ),
        "inconsistentCorroborationStatusClaimIds": sorted(
            inconsistent_corroboration_status_claim_ids
        ),
        "referenceMandatoryInsufficientIndependentEvidenceClaimIds": sorted(
            reference_mandatory_insufficient_independent_evidence_claim_ids
        ),
        "referenceMandatoryMissingGuidanceFamilyClaimIds": sorted(
            reference_mandatory_missing_guidance_family_claim_ids
        ),
        "experimentalPriorityInsufficientIndependentEvidenceClaimIds": sorted(
            experimental_priority_insufficient_independent_evidence_claim_ids
        ),
        "experimentalPriorityMissingGuidanceFamilyClaimIds": sorted(
            experimental_priority_missing_guidance_family_claim_ids
        ),
    }


def validate_reference_corroboration_governance(repo_root: Path) -> dict:
    registry = DefaultsRegistry(repo_root)
    claim_manifest = registry.scientific_validation_claim_manifest()
    coverage_manifest = scientific_validation_claim_coverage_manifest(repo_root)
    coverage_by_id = {record.claim_id: record for record in coverage_manifest.coverage}
    required_source_type_prefixes = (
        "official_guidance",
        "official_modeling_guidance",
        "official_test_guideline",
    )
    missing_independent_evidence_claim_ids: list[str] = []
    missing_official_guidance_claim_ids: list[str] = []
    missing_worksheet_claim_ids: list[str] = []
    missing_evidence_family_claim_ids: list[str] = []
    missing_official_source_id_claim_ids: list[str] = []
    missing_worksheet_artifact_claim_ids: list[str] = []
    missing_expected_output_artifact_claim_ids: list[str] = []
    missing_worksheet_status_claim_ids: list[str] = []
    missing_last_reviewed_claim_ids: list[str] = []
    missing_tolerance_basis_claim_ids: list[str] = []
    worksheet_fixture_map: dict[str, list[str]] = {}
    insufficient_reference_anchor_claim_ids: list[str] = []
    unresolved_reference_case_claim_ids: list[str] = []

    reference_claims = [
        claim
        for claim in claim_manifest.claims
        if claim.model_family == ModelFamily.REFERENCE_MASS_BALANCE and claim.mandatory_for_release
    ]
    for claim in reference_claims:
        resolved_cases = [
            registry.scientific_reference_case(case_id)
            for case_id in claim.independent_evidence_families
        ]
        if any(case is None for case in resolved_cases):
            unresolved_reference_case_claim_ids.append(claim.claim_id)
            resolved_cases = [case for case in resolved_cases if case is not None]
        source_type_set = {case.source_type for case in resolved_cases}
        if len(claim.independent_evidence_families) < 2:
            missing_independent_evidence_claim_ids.append(claim.claim_id)
        if not claim.evidence_family:
            missing_evidence_family_claim_ids.append(claim.claim_id)
        if not claim.official_source_ids:
            missing_official_source_id_claim_ids.append(claim.claim_id)
        if not claim.worksheet_artifact_path:
            missing_worksheet_artifact_claim_ids.append(claim.claim_id)
        if not claim.expected_output_artifact_path:
            missing_expected_output_artifact_claim_ids.append(claim.claim_id)
        if claim.worksheet_status is None or claim.worksheet_status.value != "ready":
            missing_worksheet_status_claim_ids.append(claim.claim_id)
        if claim.last_reviewed_date is None:
            missing_last_reviewed_claim_ids.append(claim.claim_id)
        if not claim.tolerance_basis:
            missing_tolerance_basis_claim_ids.append(claim.claim_id)
        if not _has_required_guidance_source_type(source_type_set, required_source_type_prefixes):
            missing_official_guidance_claim_ids.append(claim.claim_id)
        has_worksheet, worksheet_fixtures = _claim_has_machine_readable_worksheet_support(
            claim.claim_id
        )
        worksheet_fixture_map[claim.claim_id] = worksheet_fixtures
        if not has_worksheet:
            missing_worksheet_claim_ids.append(claim.claim_id)
        coverage_record = coverage_by_id.get(claim.claim_id)
        if coverage_record is None or not coverage_record.covered:
            insufficient_reference_anchor_claim_ids.append(claim.claim_id)

    return {
        "passed": (
            not missing_independent_evidence_claim_ids
            and not missing_evidence_family_claim_ids
            and not missing_official_source_id_claim_ids
            and not missing_official_guidance_claim_ids
            and not missing_worksheet_claim_ids
            and not missing_worksheet_artifact_claim_ids
            and not missing_expected_output_artifact_claim_ids
            and not missing_worksheet_status_claim_ids
            and not missing_last_reviewed_claim_ids
            and not missing_tolerance_basis_claim_ids
            and not insufficient_reference_anchor_claim_ids
            and not unresolved_reference_case_claim_ids
        ),
        "claimCount": len(reference_claims),
        "missingIndependentEvidenceClaimIds": sorted(missing_independent_evidence_claim_ids),
        "missingEvidenceFamilyClaimIds": sorted(missing_evidence_family_claim_ids),
        "missingOfficialSourceIdClaimIds": sorted(missing_official_source_id_claim_ids),
        "missingOfficialGuidanceClaimIds": sorted(missing_official_guidance_claim_ids),
        "missingWorksheetClaimIds": sorted(missing_worksheet_claim_ids),
        "missingWorksheetArtifactClaimIds": sorted(missing_worksheet_artifact_claim_ids),
        "missingExpectedOutputArtifactClaimIds": sorted(
            missing_expected_output_artifact_claim_ids
        ),
        "missingWorksheetStatusClaimIds": sorted(missing_worksheet_status_claim_ids),
        "missingLastReviewedClaimIds": sorted(missing_last_reviewed_claim_ids),
        "missingToleranceBasisClaimIds": sorted(missing_tolerance_basis_claim_ids),
        "insufficientReferenceAnchorClaimIds": sorted(insufficient_reference_anchor_claim_ids),
        "unresolvedReferenceCaseClaimIds": sorted(unresolved_reference_case_claim_ids),
        "worksheetFixtureMap": worksheet_fixture_map,
    }


def validate_advective_promotion_bar_governance(repo_root: Path) -> dict:
    registry = DefaultsRegistry(repo_root)
    claim_manifest = registry.scientific_validation_claim_manifest()
    coverage_manifest = scientific_validation_claim_coverage_manifest(repo_root)
    coverage_by_id = {record.claim_id: record for record in coverage_manifest.coverage}
    advective_claims = [
        claim
        for claim in claim_manifest.claims
        if claim.model_family == ModelFamily.ADVECTIVE_SCREENING_MASS_BALANCE
        and claim.priority.value in {"high", "medium"}
    ]
    missing_independent_evidence_claim_ids: list[str] = []
    missing_official_guidance_claim_ids: list[str] = []
    sensitivity_only_support_claim_ids: list[str] = []
    non_reference_style_support_claim_ids: list[str] = []

    for claim in advective_claims:
        resolved_cases = [
            registry.scientific_reference_case(case_id)
            for case_id in claim.independent_evidence_families
        ]
        resolved_cases = [case for case in resolved_cases if case is not None]
        source_type_set = {case.source_type for case in resolved_cases}
        if len(claim.independent_evidence_families) < 2:
            missing_independent_evidence_claim_ids.append(claim.claim_id)
        if not _has_required_guidance_source_type(
            source_type_set,
            ("official_guidance", "official_modeling_guidance"),
        ):
            missing_official_guidance_claim_ids.append(claim.claim_id)
        coverage_record = coverage_by_id.get(claim.claim_id)
        supporting_tiers = set(coverage_record.supporting_validation_tiers if coverage_record else [])
        if supporting_tiers == {"sensitivity"}:
            sensitivity_only_support_claim_ids.append(claim.claim_id)
        if "reference_style" not in supporting_tiers:
            non_reference_style_support_claim_ids.append(claim.claim_id)

    remains_experimental = (
        ModelFamily.ADVECTIVE_SCREENING_MASS_BALANCE.value in EXPERIMENTAL_MODEL_FAMILIES
    )
    explicit_non_promotable_reasons = [
        reason
        for reason in [
            "governed_policy_retains_experimental_status"
            if remains_experimental
            else "",
            "missing_independent_evidence_families"
            if missing_independent_evidence_claim_ids
            else "",
            "missing_official_guidance_grounding"
            if missing_official_guidance_claim_ids
            else "",
            "sensitivity_only_support_present"
            if sensitivity_only_support_claim_ids
            else "",
            "reference_style_anchor_gap"
            if non_reference_style_support_claim_ids
            else "",
        ]
        if reason
    ]
    return {
        "passed": remains_experimental and bool(explicit_non_promotable_reasons),
        "claimCount": len(advective_claims),
        "remainsExperimental": remains_experimental,
        "policyHoldExperimental": True,
        "explicitNonPromotableReasons": explicit_non_promotable_reasons,
        "missingIndependentEvidenceClaimIds": sorted(missing_independent_evidence_claim_ids),
        "missingOfficialGuidanceClaimIds": sorted(missing_official_guidance_claim_ids),
        "sensitivityOnlySupportClaimIds": sorted(sensitivity_only_support_claim_ids),
        "nonReferenceStyleSupportClaimIds": sorted(non_reference_style_support_claim_ids),
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


def _resolve_plugin_code_reference(reference: str) -> tuple[bool, str]:
    """Resolve a plugin code reference like 'module.path:ClassName.method_name'.
    Returns (ok, error_message).
    """
    if ":" not in reference:
        return False, f"Invalid reference format (expected 'module:attr.attr'): {reference}"
    module_name, attr_path = reference.split(":", 1)
    try:
        module = importlib.import_module(module_name)
    except Exception as exc:
        return False, f"Could not import {module_name}: {exc}"
    obj = module
    for part in attr_path.split("."):
        if not hasattr(obj, part):
            return False, f"{attr_path} not found on {module_name} ({part} missing)"
        obj = getattr(obj, part)
    return True, ""


def validate_scientific_claim_freshness(repo_root: Path) -> dict:
    """Flag scientific validation claims that lack traceability to code or benchmarks."""
    registry = DefaultsRegistry(repo_root)
    claim_manifest = registry.scientific_validation_claim_manifest()
    benchmark_fixtures = benchmark_manifest(repo_root)["fixtures"]
    fixture_claim_ids = {
        claim_id
        for fixture in benchmark_fixtures
        for claim_id in fixture.get("scientific_claim_ids", [])
    }

    stale_claims: list[dict[str, str]] = []
    unresolvable_references: list[dict[str, str]] = []
    claims_missing_model_family_plugin: list[str] = []

    supported_families = set(SUPPORTED_MODEL_FAMILIES) | set(EXPERIMENTAL_MODEL_FAMILIES)

    for claim in claim_manifest.claims:
        if claim.model_family.value not in supported_families:
            claims_missing_model_family_plugin.append(claim.claim_id)
            continue

        has_benchmark_coverage = claim.claim_id in fixture_claim_ids
        has_code_references = bool(claim.plugin_code_references)

        if has_code_references:
            for ref in claim.plugin_code_references:
                ok, error = _resolve_plugin_code_reference(ref)
                if not ok:
                    unresolvable_references.append(
                        {"claimId": claim.claim_id, "reference": ref, "error": error}
                    )

        if not has_benchmark_coverage and not has_code_references:
            stale_claims.append(
                {
                    "claimId": claim.claim_id,
                    "modelFamily": claim.model_family.value,
                    "reason": "No benchmark fixture coverage and no plugin_code_references.",
                }
            )

    return {
        "passed": (
            not stale_claims
            and not unresolvable_references
            and not claims_missing_model_family_plugin
        ),
        "staleClaimCount": len(stale_claims),
        "staleClaims": stale_claims,
        "unresolvableReferenceCount": len(unresolvable_references),
        "unresolvableReferences": unresolvable_references,
        "claimsMissingModelFamilyPluginCount": len(claims_missing_model_family_plugin),
        "claimsMissingModelFamilyPlugin": claims_missing_model_family_plugin,
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
        and packet_payload.get("default_evidence_status")
        == manifest_payload.get("default_evidence_status")
        and packet_payload.get("default_proof_posture")
        == manifest_payload.get("default_proof_posture")
        and packet_payload.get("default_evidence_lines")
        == manifest_payload.get("default_evidence_lines")
        and all(
            line in packet_payload.get("proof_posture_lines", [])
            for line in manifest_payload.get("proof_posture_lines", [])
        )
        and bool(packet_payload.get("proof_posture_lines"))
        and packet_payload.get("scientific_change_lines")
        == manifest_payload.get("scientific_change_lines")
        and packet_payload.get("default_sensitivity_lines")
        == manifest_payload.get("default_sensitivity_lines")
        and packet_payload.get("rebaselined_default_parameters")
        == manifest_payload.get("rebaselined_default_parameters")
        and packet_payload.get("governed_override_parameters")
        == manifest_payload.get("governed_override_parameters")
        and packet_payload.get("material_default_sensitivity")
        == manifest_payload.get("material_default_sensitivity")
        and packet_payload.get("core_default_assumption_count")
        == manifest_payload.get("core_default_assumption_count")
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
        and packet_payload.get("post_release_pace_lines") is not None
        and packet_payload.get("post_release_pace_directionality_lines") is not None
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
        and bool(brief_payload.get("default_evidence_lines"))
        and brief_payload.get("default_evidence_status") == packet_payload.get("default_evidence_status")
        and brief_payload.get("default_proof_posture") == packet_payload.get("default_proof_posture")
        and brief_payload.get("claim_set_proof_posture")
        == packet_payload.get("claim_set_proof_posture")
        and brief_payload.get("proof_posture_lines") == packet_payload.get("proof_posture_lines")
        and brief_payload.get("scientific_change_lines")
        == packet_payload.get("scientific_change_lines")
        and brief_payload.get("default_sensitivity_lines")
        == packet_payload.get("default_sensitivity_lines")
        and brief_payload.get("rebaselined_default_parameters")
        == packet_payload.get("rebaselined_default_parameters")
        and brief_payload.get("governed_override_parameters")
        == packet_payload.get("governed_override_parameters")
        and brief_payload.get("material_default_sensitivity")
        == packet_payload.get("material_default_sensitivity")
        and brief_payload.get("core_default_assumption_count")
        == packet_payload.get("core_default_assumption_count")
        and bool(brief_payload.get("applicability_lines"))
        and bool(brief_payload.get("uncertainty_lines"))
        and bool(brief_payload.get("benchmark_reference_lines"))
        and bool(brief_payload.get("equation_lines"))
        and brief_payload.get("equation_component_lines") == packet_payload.get("equation_component_lines")
        and brief_payload.get("mass_balance_component_lines") == packet_payload.get("mass_balance_component_lines")
        and brief_payload.get("transport_regime_lines") == packet_payload.get("transport_regime_lines")
        and brief_payload.get("post_release_recovery_lines") == packet_payload.get("post_release_recovery_lines")
        and brief_payload.get("post_release_regime_lines") == packet_payload.get("post_release_regime_lines")
        and brief_payload.get("post_release_directionality_lines")
        == packet_payload.get("post_release_directionality_lines")
        and brief_payload.get("post_release_pace_lines") == packet_payload.get("post_release_pace_lines")
        and brief_payload.get("post_release_pace_directionality_lines")
        == packet_payload.get("post_release_pace_directionality_lines")
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
        and (
            not packet_payload.get("post_release_directionality_lines")
            or any(
                line.startswith("Post-release directionality: ")
                for line in brief_payload.get("summary_lines", [])
            )
        )
        and (
            not packet_payload.get("post_release_pace_lines")
            or any(
                line.startswith("Post-release pace: ")
                for line in brief_payload.get("summary_lines", [])
            )
        )
        and (
            not packet_payload.get("post_release_pace_directionality_lines")
            or any(
                line.startswith("Post-release pace directionality: ")
                for line in brief_payload.get("summary_lines", [])
            )
        )
        and any(
            line.startswith("Default evidence: ")
            for line in brief_payload.get("summary_lines", [])
        )
        and any(
            line.startswith("Proof posture: ")
            for line in brief_payload.get("summary_lines", [])
        )
        and any(
            line.startswith("Scientific change: ")
            for line in brief_payload.get("summary_lines", [])
        )
        and any(
            line.startswith("Default sensitivity: ")
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


def validate_run_scientific_trust_brief_workflow(repo_root: Path) -> dict:
    request_payload = json.loads(
        (repo_root / "schemas" / "examples" / "buildRunScientificTrustBriefRequest.v1.json").read_text()
    )
    brief_payload = json.loads(
        (repo_root / "schemas" / "examples" / "runScientificTrustBrief.v1.json").read_text()
    )
    packet_payload = json.loads((repo_root / "schemas" / "examples" / "scientificReviewPacket.v1.json").read_text())

    request_consistent = (
        request_payload.get("scenario", {}).get("scenario_id") == brief_payload.get("scenario_id")
        and request_payload.get("result", {}).get("run_summary", {}).get("run_id") == brief_payload.get("run_id")
        and request_payload.get("result", {}).get("run_summary", {}).get("model_family")
        == brief_payload.get("model_family")
    )
    brief_matches_packet = (
        bool(brief_payload.get("review_packet_id"))
        and brief_payload.get("scenario_id") == packet_payload.get("scenario_id")
        and brief_payload.get("run_id") == packet_payload.get("run_id")
        and brief_payload.get("model_family") == packet_payload.get("model_family")
        and brief_payload.get("fit_for_purpose") == packet_payload.get("fit_for_purpose")
        and brief_payload.get("review_status") == packet_payload.get("review_status")
        and brief_payload.get("review_outcome") == packet_payload.get("review_outcome")
        and brief_payload.get("default_evidence_status") == packet_payload.get("default_evidence_status")
        and brief_payload.get("default_proof_posture") == packet_payload.get("default_proof_posture")
        and brief_payload.get("claim_set_proof_posture")
        == packet_payload.get("claim_set_proof_posture")
        and brief_payload.get("default_evidence_lines") == packet_payload.get("default_evidence_lines")
        and brief_payload.get("proof_posture_lines") == packet_payload.get("proof_posture_lines")
        and brief_payload.get("scientific_change_lines")
        == packet_payload.get("scientific_change_lines")
        and brief_payload.get("default_sensitivity_lines")
        == packet_payload.get("default_sensitivity_lines")
        and brief_payload.get("rebaselined_default_parameters")
        == packet_payload.get("rebaselined_default_parameters")
        and brief_payload.get("governed_override_parameters")
        == packet_payload.get("governed_override_parameters")
        and brief_payload.get("material_default_sensitivity")
        == packet_payload.get("material_default_sensitivity")
        and brief_payload.get("core_default_assumption_count")
        == packet_payload.get("core_default_assumption_count")
        and brief_payload.get("applicability_lines")
        == packet_payload.get("fit_assessment", {}).get("applicability_lines")
        and brief_payload.get("scientific_unsuitability_lines")
        == packet_payload.get("fit_assessment", {}).get("scientific_unsuitability_lines")
        and brief_payload.get("uncertainty_lines")
        == packet_payload.get("uncertainty_summary", {}).get("summary_lines")
        and brief_payload.get("recommended_actions") == packet_payload.get("recommended_actions")
        and brief_payload.get("limitations") == packet_payload.get("limitations")
        and brief_payload.get("passed_check_count", 0) <= brief_payload.get("total_check_count", 0)
        and brief_payload.get("top_uncertainty_driver_types")
        == [
            driver.get("driver_type")
            for driver in packet_payload.get("uncertainty_summary", {}).get("top_drivers", [])[:4]
        ]
        and any(
            line.startswith("Screening recommendation: ")
            for line in brief_payload.get("summary_lines", [])
        )
        and any(
            line.startswith("Screening recommendation: ")
            for line in brief_payload.get("reviewer_signal_lines", [])
        )
        and any(
            line.startswith("Review outcome: ") for line in brief_payload.get("reviewer_signal_lines", [])
        )
        and any(
            line.startswith("Default evidence: ") for line in brief_payload.get("summary_lines", [])
        )
        and any(
            line.startswith("Proof posture: ") for line in brief_payload.get("summary_lines", [])
        )
        and any(
            line.startswith("Scientific change: ") for line in brief_payload.get("summary_lines", [])
        )
        and any(
            line.startswith("Default sensitivity: ") for line in brief_payload.get("summary_lines", [])
        )
        and bool(brief_payload.get("top_caveat_lines"))
    )
    return {
        "passed": request_consistent and brief_matches_packet,
        "runScientificTrustBriefRequestConsistent": request_consistent,
        "runScientificTrustBriefMatchesPacket": brief_matches_packet,
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
        and bool(dossier_payload.get("reviewer_grade_anchor_status"))
        and dossier_payload.get("mandatory_claim_pass_count", 0)
        <= dossier_payload.get("mandatory_claim_count", 0)
        and dossier_payload.get("worksheet_ready_mandatory_claim_count", 0)
        <= dossier_payload.get("mandatory_claim_count", 0)
        and bool(dossier_payload.get("proof_posture"))
        and bool(dossier_payload.get("proof_posture_lines"))
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
        and bool(dossier_payload.get("default_change_sensitivity_lines"))
        and bool(dossier_payload.get("benchmark_reference_lines"))
        and bool(dossier_payload.get("support_strength_lines"))
        and bool(dossier_payload.get("claim_summaries"))
        and any(
            line.startswith("Reviewer-grade anchor status: ")
            for line in dossier_payload.get("summary_lines", [])
        )
        and any(
            line.startswith("Mandatory claim pass count: ")
            for line in dossier_payload.get("summary_lines", [])
        )
        and any(
            line.startswith("Worksheet readiness: ")
            for line in dossier_payload.get("summary_lines", [])
        )
        and any(
            line.startswith("Default-change sensitivity: ")
            for line in dossier_payload.get("summary_lines", [])
        )
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
        and any(
            line.startswith("Default evidence posture: ")
            for line in dossier_payload.get("summary_lines", [])
        )
        and any(
            line.startswith("Proof posture: ")
            for line in dossier_payload.get("summary_lines", [])
        )
        and any(
            line.startswith("When not to use this MCP: ")
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
                item.get("claim_id") == "advective_post_release_flushing_directionality_v1"
                and item.get("covered")
                for item in dossier_payload.get("claim_summaries", [])
            )
            or any(
                line.startswith("Post-release directionality support: ")
                for line in dossier_payload.get("summary_lines", [])
            )
        )
        and (
            not any(
                item.get("claim_id") == "advective_post_release_half_recovery_pace_v1"
                and item.get("covered")
                for item in dossier_payload.get("claim_summaries", [])
            )
            or any(
                line.startswith("Post-release pace support: ")
                for line in dossier_payload.get("summary_lines", [])
            )
        )
        and (
            not any(
                item.get("claim_id") == "advective_post_release_half_recovery_directionality_v1"
                and item.get("covered")
                for item in dossier_payload.get("claim_summaries", [])
            )
            or any(
                line.startswith("Post-release pace directionality support: ")
                for line in dossier_payload.get("summary_lines", [])
            )
        )
        and (
            not any(
                item.get("claim_id") == "advective_post_release_late_recovery_regime_v1"
                and item.get("covered")
                for item in dossier_payload.get("claim_summaries", [])
            )
            or any(
                line.startswith("Late recovery regime support: ")
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
        and "evidence_family" in claim_summary_payload
        and "official_source_ids" in claim_summary_payload
        and "worksheet_artifact_path" in claim_summary_payload
        and "expected_output_artifact_path" in claim_summary_payload
        and "worksheet_status" in claim_summary_payload
        and "last_reviewed_date" in claim_summary_payload
        and "tolerance_basis" in claim_summary_payload
        and "reviewer_grade_passed" in claim_summary_payload
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
        and brief_payload.get("proof_posture") == dossier_payload.get("proof_posture")
        and brief_payload.get("proof_posture_lines") == dossier_payload.get("proof_posture_lines")
        and brief_payload.get("promotion_blocker_claim_ids")
        == dossier_payload.get("promotion_blocker_claim_ids")
        and brief_payload.get("promotion_blocker_summaries")
        == dossier_payload.get("promotion_blocker_summaries")
        and brief_payload.get("mandatory_claim_count") == dossier_payload.get("mandatory_claim_count")
        and brief_payload.get("covered_mandatory_claim_count")
        == dossier_payload.get("covered_mandatory_claim_count")
        and brief_payload.get("uncovered_mandatory_claim_count")
        == dossier_payload.get("uncovered_mandatory_claim_count")
        and brief_payload.get("reviewer_grade_anchor_status")
        == dossier_payload.get("reviewer_grade_anchor_status")
        and brief_payload.get("mandatory_claim_pass_count")
        == dossier_payload.get("mandatory_claim_pass_count")
        and brief_payload.get("worksheet_ready_mandatory_claim_count")
        == dossier_payload.get("worksheet_ready_mandatory_claim_count")
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
            line.startswith("Proof posture: ") for line in brief_payload.get("summary_lines", [])
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
        and any(
            line.startswith("When not to use this MCP: ")
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
        and brief_payload.get("default_change_sensitivity_lines")
        == dossier_payload.get("default_change_sensitivity_lines")
        and brief_payload.get("benchmark_reference_lines") == dossier_payload.get("benchmark_reference_lines")
        and brief_payload.get("support_strength_lines") == dossier_payload.get("support_strength_lines")
        and brief_payload.get("recommended_actions") == dossier_payload.get("recommended_actions")
        and any(
            line.startswith("Reviewer-grade anchor status: ")
            for line in brief_payload.get("summary_lines", [])
        )
        and any(
            line.startswith("Mandatory claim pass count: ")
            for line in brief_payload.get("summary_lines", [])
        )
        and any(
            line.startswith("Worksheet readiness: ")
            for line in brief_payload.get("summary_lines", [])
        )
        and any(
            line.startswith("Default-change sensitivity: ")
            for line in brief_payload.get("summary_lines", [])
        )
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
        and any(
            line.startswith("Primary applicability: When not to use this MCP: ")
            or line.startswith("Challenge applicability: When not to use this MCP: ")
            for line in brief_payload.get("brief_lines", [])
        )
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


def validate_trust_surface_consistency(repo_root: Path) -> dict:
    run_trust_payload = json.loads(
        (repo_root / "schemas" / "examples" / "runScientificTrustBrief.v1.json").read_text()
    )
    review_brief_payload = json.loads(
        (repo_root / "schemas" / "examples" / "scientificReviewBrief.v1.json").read_text()
    )
    methods_dossier_payload = json.loads(
        (repo_root / "schemas" / "examples" / "scientificMethodsDossier.v1.json").read_text()
    )
    methods_brief_payload = json.loads(
        (repo_root / "schemas" / "examples" / "scientificMethodsDossierBrief.v1.json").read_text()
    )
    quick_start_text = (repo_root / "docs" / "regulatory_quick_start.md").read_text()
    release_readiness_text = (repo_root / "docs" / "release_readiness.md").read_text()

    run_review_consistent = (
        run_trust_payload.get("default_proof_posture")
        == review_brief_payload.get("default_proof_posture")
        and run_trust_payload.get("claim_set_proof_posture")
        == review_brief_payload.get("claim_set_proof_posture")
        and run_trust_payload.get("proof_posture_lines")
        == review_brief_payload.get("proof_posture_lines")
        and run_trust_payload.get("scientific_change_lines")
        == review_brief_payload.get("scientific_change_lines")
        and run_trust_payload.get("default_sensitivity_lines")
        == review_brief_payload.get("default_sensitivity_lines")
    )
    methods_consistent = (
        methods_dossier_payload.get("proof_posture") == methods_brief_payload.get("proof_posture")
        and methods_dossier_payload.get("proof_posture_lines")
        == methods_brief_payload.get("proof_posture_lines")
        and methods_dossier_payload.get("reviewer_grade_anchor_status")
        == methods_brief_payload.get("reviewer_grade_anchor_status")
        and methods_dossier_payload.get("mandatory_claim_pass_count")
        == methods_brief_payload.get("mandatory_claim_pass_count")
        and methods_dossier_payload.get("worksheet_ready_mandatory_claim_count")
        == methods_brief_payload.get("worksheet_ready_mandatory_claim_count")
        and methods_dossier_payload.get("default_change_sensitivity_lines")
        == methods_brief_payload.get("default_change_sensitivity_lines")
        and any(
            line.startswith("Proof posture: ")
            for line in methods_brief_payload.get("summary_lines", [])
        )
        and any(
            line.startswith("Reviewer-grade anchor status: ")
            for line in methods_brief_payload.get("summary_lines", [])
        )
    )
    docs_consistent = (
        "When Not To Use This MCP" in quick_start_text
        and "bounded screening" in quick_start_text.lower()
        and (
            "bounded screening" in release_readiness_text.lower()
            or "bounded-screening" in release_readiness_text.lower()
        )
        and "advective_screening_mass_balance" in quick_start_text
        and "experimental" in quick_start_text.lower()
        and "reference_mass_balance" in release_readiness_text
    )
    return {
        "passed": run_review_consistent and methods_consistent and docs_consistent,
        "runTrustReviewConsistent": run_review_consistent,
        "scientificMethodsProofConsistent": methods_consistent,
        "docsScopeLanguageConsistent": docs_consistent,
    }


def validate_erosion_sediment_validation_demo_pack(repo_root: Path) -> dict:
    runtime = FateRuntime(repo_root)
    manifest = runtime.defaults.erosion_sediment_validation_demo_pack_manifest()
    case_results = []
    required_case_ids = {
        "perfect_fit",
        "screening_plausible",
        "weak_fit",
        "insufficient_evidence",
    }
    found_case_ids = {demo_case.demo_case_id for demo_case in manifest.demo_cases}
    for demo_case in manifest.demo_cases:
        validation_case = build_erosion_sediment_validation_case(
            BuildErosionSedimentValidationCaseRequest(
                observed_records=demo_case.observed_records,
                predicted_records=demo_case.predicted_records,
                validation_profile_id=demo_case.validation_profile_id,
            ),
            runtime.provenance,
        )
        fit = assess_erosion_sediment_validation_fit(
            AssessErosionSedimentValidationFitRequest(validation_case=validation_case),
            runtime.provenance,
        )
        case_results.append(
            {
                "demoCaseId": demo_case.demo_case_id,
                "expectedClassification": demo_case.expected_classification.value,
                "actualClassification": fit.classification.value,
                "matchedCount": fit.metrics.matched_count,
                "passed": fit.classification == demo_case.expected_classification,
            }
        )
    limitations_text = " ".join(manifest.limitations).lower()
    synthetic_boundary_clear = all(
        phrase in limitations_text
        for phrase in (
            "synthetic",
            "not field validation",
            "not field validation, calibration evidence",
            "not field validation, calibration evidence, regulator acceptance",
            "wepp validation",
        )
    )
    all_cases_present = required_case_ids.issubset(found_case_ids)
    return {
        "passed": (
            manifest.demo_case_count == len(manifest.demo_cases)
            and all_cases_present
            and all(item["passed"] for item in case_results)
            and synthetic_boundary_clear
        ),
        "demoCaseCount": manifest.demo_case_count,
        "requiredDemoCaseIds": sorted(required_case_ids),
        "missingDemoCaseIds": sorted(required_case_ids - found_case_ids),
        "syntheticBoundaryClear": synthetic_boundary_clear,
        "caseResults": case_results,
        "limitations": manifest.limitations,
    }


def validation_dossier(repo_root: Path) -> dict:
    generate_contract_artifacts(repo_root)
    return {
        "artifacts": validate_generated_artifacts(repo_root),
        "benchmarks": run_benchmarks(repo_root),
        "failureModes": validate_failure_modes(repo_root),
        "downstreamInteroperability": validate_downstream_interoperability(repo_root),
        "defaultsEvidenceGovernance": validate_defaults_evidence_governance(repo_root),
        "regulatoryHandoffGovernance": validate_regulatory_handoff_governance(repo_root),
        "adapterInteroperability": validate_adapter_interoperability(repo_root),
        "reconciliationTransparency": validate_reconciliation_transparency(repo_root),
        "scientificReviewArtifacts": validate_scientific_review_artifacts(repo_root),
        "scientificClaimCoverage": validate_scientific_claim_coverage(repo_root),
        "externalCorroborationGovernance": validate_external_corroboration_governance(repo_root),
        "referenceCorroborationGovernance": validate_reference_corroboration_governance(repo_root),
        "advectivePromotionBarGovernance": validate_advective_promotion_bar_governance(repo_root),
        "scientificClaimFreshness": validate_scientific_claim_freshness(repo_root),
        "scientificReviewWorkflow": validate_scientific_review_workflow(repo_root),
        "runScientificTrustBriefWorkflow": validate_run_scientific_trust_brief_workflow(repo_root),
        "scientificMethodsDossierWorkflow": validate_scientific_methods_dossier_workflow(repo_root),
        "trustSurfaceConsistency": validate_trust_surface_consistency(repo_root),
        "erosionSedimentValidationDemoPack": validate_erosion_sediment_validation_demo_pack(repo_root),
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
    dossier = validation_dossier(repo_root)
    if not dossier["erosionSedimentValidationDemoPack"]["passed"]:
        raise SystemExit("Erosion/sediment validation demo pack failed release validation.")


if __name__ == "__main__":
    main()
