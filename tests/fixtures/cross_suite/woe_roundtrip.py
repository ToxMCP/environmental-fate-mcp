"""Deterministic Environmental Fate -> WoE round-trip fixture builder."""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from typing import Any

from fate_mcp.integrations import (
    build_concentration_surface_bundle,
    build_regulatory_handoff_review_packet,
)
from fate_mcp.models import (
    BuildEnvironmentalReleaseScenarioRequest,
    BuildRegulatoryHandoffReviewPacketRequest,
    FateModelRunOptions,
    Media,
    ReleaseFraction,
)
from fate_mcp.package_metadata import VERSION
from fate_mcp.runtime import FateRuntime

WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_PATH = (
    WORKSPACE_ROOT
    / "tests"
    / "fixtures"
    / "cross_suite"
    / "woe_ngra"
    / "fate_exposure_handoff.v1.1.0.json"
)
WOE_SYNC_TARGET_PATH = (
    WORKSPACE_ROOT.parent
    / "WoE_NGRA_Synthesis_MCP"
    / "src"
    / "integration"
    / "__fixtures__"
    / "fate-exposure-woe-roundtrip.bundle.json"
)

FIXTURE_CREATED_AT = "2026-04-21T12:00:00.000Z"
SOURCE_VERSION = "1.1.0"
SCHEMA_VERSION = "1.1.0"
BUNDLE_ID = "fate-exposure-woe-roundtrip-001"
CREATED_BY = "environmental-fate-cross-suite-fixture-builder"
PRODUCER_MODULE = "environmental_fate"
SCENARIO_ID = "fate-environmental-scenario-001"
CONCENTRATION_BUNDLE_ID = "fate-concentration-surface-bundle-001"
HANDOFF_PACKAGE_ID = "fate-regulatory-handoff-package-001"
HANDOFF_REVIEW_ID = "fate-regulatory-handoff-review-001"

ENTRY_CONFIGS = {
    "ambient_air": {
        "suffix": "air",
        "evidence_id": "fate-exp-air-001",
        "claim_id": "fate-exp-air-claim-001",
        "link_id": "fate-exp-air-link-001",
        "applicability_id": "fate-exp-air-app-001",
        "uncertainty_id": "fate-exp-air-unc-001",
        "line_of_evidence_id": "loe-fate-air",
        "surface_artifact_id": "fate-surface-air-001",
    },
    "surface_water": {
        "suffix": "water",
        "evidence_id": "fate-exp-water-001",
        "claim_id": "fate-exp-water-claim-001",
        "link_id": "fate-exp-water-link-001",
        "applicability_id": "fate-exp-water-app-001",
        "uncertainty_id": "fate-exp-water-unc-001",
        "line_of_evidence_id": "loe-fate-water",
        "surface_artifact_id": "fate-surface-water-001",
    },
    "agricultural_soil": {
        "suffix": "soil",
        "evidence_id": "fate-exp-soil-001",
        "claim_id": "fate-exp-soil-claim-001",
        "link_id": "fate-exp-soil-link-001",
        "applicability_id": "fate-exp-soil-app-001",
        "uncertainty_id": "fate-exp-soil-unc-001",
        "line_of_evidence_id": "loe-fate-soil",
        "surface_artifact_id": "fate-surface-soil-001",
    },
}


def _sorted_json(value: Any) -> Any:
    if isinstance(value, list):
        return [_sorted_json(item) for item in value]
    if isinstance(value, dict):
        return {key: _sorted_json(item) for key, item in sorted(value.items())}
    return value


def _stable_json_dumps(value: Any) -> str:
    return json.dumps(_sorted_json(value), indent=2)


def _hash_text(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def _hash_value(value: Any) -> str:
    return _hash_text(_stable_json_dumps(value))


def _provenance(tool_run_id: str, source_hash_value: Any) -> dict[str, Any]:
    return {
        "toolRunId": tool_run_id,
        "createdAt": FIXTURE_CREATED_AT,
        "createdBy": CREATED_BY,
        "sourceHashes": [
            {
                "algorithm": "sha256",
                "value": _hash_value(source_hash_value),
            }
        ],
    }


def _typed_ref(
    *,
    object_type_ref: str,
    artifact_id: str,
    retrieval_endpoint: str,
    cached_snapshot: dict[str, Any],
) -> dict[str, Any]:
    return {
        "objectType": "typedHandoffRef",
        "schemaVersion": "1.1.0",
        "objectTypeRef": object_type_ref,
        "retrievalEndpoint": retrieval_endpoint,
        "cachedSnapshot": cached_snapshot,
        "artifactId": artifact_id,
        "producerModule": PRODUCER_MODULE,
        "producerVersion": VERSION,
        "integrityHash": f"sha256:{_hash_value(cached_snapshot)}",
    }


def _build_review_artifacts() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    runtime = FateRuntime(WORKSPACE_ROOT)
    scenario = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={
                "preferredName": "Example Fate Compound",
                "substance_class": "organic chemical",
            },
            total_release_mass_kg=5.0,
            release_fractions=[
                ReleaseFraction(medium=Media.AIR, fraction=0.3),
                ReleaseFraction(medium=Media.WATER, fraction=0.4),
                ReleaseFraction(medium=Media.SOIL, fraction=0.3),
            ],
            duration_days=10.0,
        )
    )
    result = runtime.estimate(
        scenario,
        FateModelRunOptions(region_profile_id=scenario.geographic_scope.region_id),
    )
    concentration_bundle = build_concentration_surface_bundle(result)
    review_packet = build_regulatory_handoff_review_packet(
        BuildRegulatoryHandoffReviewPacketRequest(result=result, scenario=scenario),
        runtime.provenance,
    )
    return (
        scenario.model_dump(mode="json"),
        concentration_bundle.model_dump(mode="json"),
        review_packet.package.model_dump(mode="json"),
        review_packet.model_dump(mode="json"),
    )


def _entry_snapshots(
    *,
    scenario: dict[str, Any],
    concentration_bundle: dict[str, Any],
    handoff_package: dict[str, Any],
    review_packet: dict[str, Any],
    entry: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    summary = review_packet["summary"]
    surface_snapshot = {
        "objectType": "ConcentrationSurface",
        "scenarioId": SCENARIO_ID,
        "medium": entry["medium"],
        "compartment": entry["compartment"],
        "concentrationValue": entry["concentration_value"],
        "concentrationUnit": entry["concentration_unit"],
        "timeWindowMode": entry["time_window"]["mode"],
    }
    bundle_snapshot = {
        "objectType": "ConcentrationSurfaceBundle",
        "bundleId": CONCENTRATION_BUNDLE_ID,
        "scenarioId": SCENARIO_ID,
        "surfaceCount": len(concentration_bundle["surfaces"]),
        "modelFamily": concentration_bundle["run_summary"]["model_family"],
        "runMode": concentration_bundle["run_summary"]["run_mode"],
        "mediums": sorted({surface["medium"] for surface in concentration_bundle["surfaces"]}),
        "compartments": sorted(
            {surface["compartment"] for surface in concentration_bundle["surfaces"]}
        ),
        "regulatoryUseDisclaimer": concentration_bundle["regulatory_use_disclaimer"],
    }
    package_snapshot = {
        "objectType": "RegulatoryHandoffPackage",
        "packageId": HANDOFF_PACKAGE_ID,
        "scenarioId": SCENARIO_ID,
        "handoffProfileId": handoff_package["handoff_profile_id"],
        "sourceModelFamily": handoff_package["source_model_family"],
        "targetModules": handoff_package["target_modules"],
        "routeHints": summary["route_hints"],
        "requiresDoseTranslation": summary["requires_dose_translation"],
        "blockers": handoff_package["blockers"],
        "limitations": handoff_package["limitations"],
    }
    review_snapshot = {
        "objectType": "RegulatoryHandoffReviewPacket",
        "reviewPacketId": HANDOFF_REVIEW_ID,
        "scenarioId": SCENARIO_ID,
        "reviewStatus": review_packet["review_status"],
        "targetModule": review_packet["target_module"],
        "handoffProfileId": review_packet["handoff_profile_id"],
        "parameterQualityLines": review_packet["parameter_quality_lines"],
        "applicabilityLines": review_packet["applicability_lines"],
        "uncertaintyLines": review_packet["uncertainty_lines"],
        "equationLines": review_packet["equation_lines"],
    }
    summary_snapshot = {
        "objectType": "RegulatoryHandoffPackageSummary",
        "packageId": HANDOFF_PACKAGE_ID,
        "scenarioId": SCENARIO_ID,
        "targetModule": summary["target_module"],
        "downstreamField": summary["downstream_field"],
        "entryCount": summary["entry_count"],
        "timeWindowModes": summary["time_window_modes"],
        "routeHints": summary["route_hints"],
        "mediums": summary["mediums"],
        "compartments": summary["compartments"],
        "requiresDoseTranslation": summary["requires_dose_translation"],
        "summaryLines": summary["summary_lines"],
    }
    scenario_snapshot = {
        "objectType": "EnvironmentalReleaseScenario",
        "scenarioId": SCENARIO_ID,
        "preferredName": scenario["chemical_identity"]["preferredName"],
        "substanceClass": scenario["chemical_identity"].get("substance_class"),
        "durationDays": scenario["duration_days"],
        "releaseFractions": scenario["release_fractions"],
        "regionId": scenario["geographic_scope"]["region_id"],
    }
    return {
        "surface": surface_snapshot,
        "bundle": bundle_snapshot,
        "package": package_snapshot,
        "review": review_snapshot,
        "summary": summary_snapshot,
        "scenario": scenario_snapshot,
    }


def _entry_config(compartment: str) -> dict[str, str]:
    try:
        return ENTRY_CONFIGS[compartment]
    except KeyError as exc:
        raise KeyError(f"Unhandled Fate compartment: {compartment}") from exc


def _stable_entry_signature(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "medium": entry["medium"],
        "compartment": entry["compartment"],
        "concentration_value": entry["concentration_value"],
        "concentration_unit": entry["concentration_unit"],
        "time_window": entry["time_window"],
        "semantic_label": entry["semantic_label"],
        "downstream_field": entry["downstream_field"],
        "route_hint": entry["route_hint"],
        "equation_id": entry["equation_id"],
        "equation_text": entry["equation_text"],
        "requires_dose_translation": entry["requires_dose_translation"],
    }


def build_fate_woe_roundtrip_bundle() -> dict[str, Any]:
    scenario, concentration_bundle, handoff_package, review_packet = _build_review_artifacts()
    summary = review_packet["summary"]
    limitations = handoff_package["limitations"]
    concentration_only_note = next(
        item["message"] for item in limitations if item["code"] == "concentration_only"
    )
    suite_semantics_note = next(
        item["message"] for item in limitations if item["code"] == "suite_handoff_semantics"
    )
    uncertainty_lead = review_packet["uncertainty_lines"][0]
    evidence_items: list[dict[str, Any]] = []
    claim_items: list[dict[str, Any]] = []
    link_items: list[dict[str, Any]] = []
    applicability_items: list[dict[str, Any]] = []
    uncertainty_items: list[dict[str, Any]] = []

    for entry in sorted(
        handoff_package["crosswalk_entries"], key=lambda item: item["compartment"]
    ):
        config = _entry_config(entry["compartment"])
        snapshots = _entry_snapshots(
            scenario=scenario,
            concentration_bundle=concentration_bundle,
            handoff_package=handoff_package,
            review_packet=review_packet,
            entry=entry,
        )
        evidence_items.append(
            {
                "originalId": config["evidence_id"],
                "evidenceClass": "exposure",
                "sourceModule": PRODUCER_MODULE,
                "provenance": _provenance(
                    f"{config['evidence_id']}-run",
                    {
                        "entry": _stable_entry_signature(entry),
                        "summary": summary["summary_lines"],
                    },
                ),
                "endpointFamily": "environmental_media_concentration",
                "biologicalLevel": "environment",
                "methodMaturity": "governed_concentration_handoff",
                "methodDescription": (
                    f"{entry['compartment']} concentration precursor exported from "
                    f"Fate governed handoff profile {handoff_package['handoff_profile_id']}."
                ),
                "studyIdentifiers": [
                    {
                        "identifierType": "scenario_id",
                        "identifierValue": SCENARIO_ID,
                    },
                    {
                        "identifierType": "handoff_profile_id",
                        "identifierValue": handoff_package["handoff_profile_id"],
                    },
                    {
                        "identifierType": "medium",
                        "identifierValue": entry["medium"],
                    },
                    {
                        "identifierType": "compartment",
                        "identifierValue": entry["compartment"],
                    },
                    {
                        "identifierType": "time_window_mode",
                        "identifierValue": entry["time_window"]["mode"],
                    },
                    {
                        "identifierType": "route_hint",
                        "identifierValue": entry["route_hint"],
                    },
                    {
                        "identifierType": "requires_dose_translation",
                        "identifierValue": str(entry["requires_dose_translation"]).lower(),
                    },
                ],
                "schemaVersion": SCHEMA_VERSION,
                "exposureMetric": entry["semantic_label"],
                "exposureScenario": "environmental_media_precursor",
                "aggregateExposure": False,
                "sourceScenarioId": SCENARIO_ID,
                "route": entry["route_hint"],
                "region": scenario["geographic_scope"]["region_id"],
                "intendedUseFamily": "environmental",
                "doseValue": entry["concentration_value"],
                "doseUnit": entry["concentration_unit"],
                "routeMetricKeys": [
                    "concentration_value",
                    "concentration_unit",
                    "route_hint",
                    "requires_dose_translation",
                ],
                "upstreamArtifactRefs": [
                    _typed_ref(
                        object_type_ref="EnvironmentalReleaseScenario",
                        artifact_id=SCENARIO_ID,
                        retrieval_endpoint="fate://cross-suite/environmental-release-scenario",
                        cached_snapshot=snapshots["scenario"],
                    ),
                    _typed_ref(
                        object_type_ref="ConcentrationSurface",
                        artifact_id=config["surface_artifact_id"],
                        retrieval_endpoint=(
                            "fate://cross-suite/concentration-surface/"
                            f"{config['suffix']}"
                        ),
                        cached_snapshot=snapshots["surface"],
                    ),
                    _typed_ref(
                        object_type_ref="ConcentrationSurfaceBundle",
                        artifact_id=CONCENTRATION_BUNDLE_ID,
                        retrieval_endpoint="fate://cross-suite/concentration-surface-bundle",
                        cached_snapshot=snapshots["bundle"],
                    ),
                    _typed_ref(
                        object_type_ref="RegulatoryHandoffPackage",
                        artifact_id=HANDOFF_PACKAGE_ID,
                        retrieval_endpoint="fate://cross-suite/regulatory-handoff-package",
                        cached_snapshot=snapshots["package"],
                    ),
                    _typed_ref(
                        object_type_ref="RegulatoryHandoffPackageSummary",
                        artifact_id=f"{HANDOFF_PACKAGE_ID}:summary",
                        retrieval_endpoint=(
                            "fate://cross-suite/regulatory-handoff-package-summary"
                        ),
                        cached_snapshot=snapshots["summary"],
                    ),
                    _typed_ref(
                        object_type_ref="RegulatoryHandoffReviewPacket",
                        artifact_id=HANDOFF_REVIEW_ID,
                        retrieval_endpoint="fate://cross-suite/regulatory-handoff-review",
                        cached_snapshot=snapshots["review"],
                    ),
                ],
            }
        )
        claim_items.append(
            {
                "originalId": config["claim_id"],
                "claimText": (
                    f"{entry['compartment']} concentration precursor remains concentration-only "
                    f"at {entry['concentration_value']:.12g} {entry['concentration_unit']} and "
                    "still requires downstream route and dose translation."
                ),
                "claimType": "qualitative",
                "supportStatus": "supports",
                "confidence": "moderate",
                "evidenceObjectIds": [config["evidence_id"]],
                "lineOfEvidenceId": config["line_of_evidence_id"],
                "rationale": (
                    f"{concentration_only_note} {suite_semantics_note}"
                ),
                "applicabilityRecordId": config["applicability_id"],
                "provenance": _provenance(
                    f"{config['claim_id']}-run",
                    {
                        "entry": _stable_entry_signature(entry),
                        "notes": [concentration_only_note, suite_semantics_note],
                    },
                ),
            }
        )
        link_items.append(
            {
                "originalId": config["link_id"],
                "sourceId": config["evidence_id"],
                "sourceType": "evidence",
                "targetId": config["claim_id"],
                "targetType": "claim",
                "relationType": "supports",
                "rationale": (
                    "The claim restates the Fate crosswalk entry as bounded contextual "
                    "concentration evidence only."
                ),
                "strength": "strong",
                "bidirectional": False,
                "provenance": _provenance(
                    f"{config['link_id']}-run",
                    {"source": config["evidence_id"], "target": config["claim_id"]},
                ),
            }
        )
        applicability_items.append(
            {
                "originalId": config["applicability_id"],
                "evidenceClass": "exposure",
                "intendedUse": "bounded_environmental_context",
                "dimensionAssessments": [
                    {
                        "dimension": "exposure_metric",
                        "status": "direct",
                        "rationale": (
                            "The governed handoff preserves medium, compartment, "
                            "concentration value, concentration unit, and steady-state "
                            "time semantics."
                        ),
                    },
                    {
                        "dimension": "internal_dose_metric",
                        "status": "not_comparable",
                        "rationale": concentration_only_note,
                        "bridgingRationale": (
                            f"Route hint {entry['route_hint']} is precursor context only."
                        ),
                    },
                    {
                        "dimension": "route",
                        "status": "indirect",
                        "rationale": (
                            f"Route hint {entry['route_hint']} remains bounded guidance "
                            "and must not be treated as a final human route estimate."
                        ),
                    },
                ],
                "overallStatus": "partial",
                "materiality": "material",
                "affectedObjectIds": [config["evidence_id"]],
                "provenance": _provenance(
                    f"{config['applicability_id']}-run",
                    {
                        "entry": _stable_entry_signature(entry),
                        "applicability": review_packet["applicability_lines"],
                    },
                ),
            }
        )
        uncertainty_items.append(
            {
                "originalId": config["uncertainty_id"],
                "uncertaintyClass": "comparability_indirectness",
                "burdenLevel": "major",
                "affectedObjectIds": [config["evidence_id"]],
                "rationale": (
                    f"{uncertainty_lead} {concentration_only_note}"
                ),
                "reducibility": "partially_reducible",
                "directionality": "unknown",
                "mitigationPath": (
                    "Route the concentration surface into a concentration-to-dose or "
                    "scenario module before quantitative downstream comparison."
                ),
                "provenance": _provenance(
                    f"{config['uncertainty_id']}-run",
                    {
                        "entry": _stable_entry_signature(entry),
                        "uncertainty": review_packet["uncertainty_lines"],
                    },
                ),
            }
        )

    return {
        "sourceFormat": "structured_json_bundle",
        "sourceVersion": SOURCE_VERSION,
        "bundleId": BUNDLE_ID,
        "schemaVersion": SCHEMA_VERSION,
        "createdAt": FIXTURE_CREATED_AT,
        "createdBy": CREATED_BY,
        "targetConsumer": "woe_ngra",
        "evidenceItems": evidence_items,
        "claimItems": claim_items,
        "linkItems": link_items,
        "applicabilityItems": applicability_items,
        "uncertaintyItems": uncertainty_items,
    }


def write_fate_woe_roundtrip_bundle(path: Path = FIXTURE_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"{json.dumps(build_fate_woe_roundtrip_bundle(), indent=2, sort_keys=True)}\n",
        encoding="utf-8",
    )
