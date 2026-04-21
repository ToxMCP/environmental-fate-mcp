from __future__ import annotations

import json

from tests.fixtures.cross_suite.woe_roundtrip import (
    FIXTURE_PATH,
    build_fate_woe_roundtrip_bundle,
)


def test_fate_woe_roundtrip_bundle_matches_fixture() -> None:
    generated = build_fate_woe_roundtrip_bundle()
    checked_in = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    assert generated == checked_in


def test_fate_woe_roundtrip_bundle_preserves_concentration_only_context() -> None:
    bundle = build_fate_woe_roundtrip_bundle()

    evidence_items = bundle["evidenceItems"]
    assert len(evidence_items) == 3
    assert {item["intendedUseFamily"] for item in evidence_items} == {"environmental"}
    assert {item["exposureScenario"] for item in evidence_items} == {
        "environmental_media_precursor"
    }
    assert {item["doseUnit"] for item in evidence_items} == {"mg/L", "mg/kg", "mg/m3"}
    assert {item["route"] for item in evidence_items} == {
        "inhalation_precursor",
        "soil_contact_or_crop_uptake_precursor",
        "water_contact_or_drinking_water_precursor",
    }
    assert all(
        any(
            identifier["identifierType"] == "requires_dose_translation"
            and identifier["identifierValue"] == "true"
            for identifier in item["studyIdentifiers"]
        )
        for item in evidence_items
    )
    assert all(
        {
            ref["objectTypeRef"]
            for ref in item["upstreamArtifactRefs"]
        }
        == {
            "EnvironmentalReleaseScenario",
            "ConcentrationSurface",
            "ConcentrationSurfaceBundle",
            "RegulatoryHandoffPackage",
            "RegulatoryHandoffPackageSummary",
            "RegulatoryHandoffReviewPacket",
        }
        for item in evidence_items
    )
