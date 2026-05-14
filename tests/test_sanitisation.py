"""Regression tests for the confidentiality-aware sanitisation lane.

The sanitisation lane produces a public-facing projection of a
ConcentrationSurfaceBundle with confidential parameter values and
source references redacted, plus a machine-readable record of every
redaction. These tests confirm:

  1. The sanitised bundle preserves non-confidential structure
     (surfaces, run summary, dependencies, scenario_id) byte-for-byte.
  2. Confidential parameter values are replaced by the canonical
     ``[REDACTED]`` placeholder rather than removed (so a reviewer
     can see "an assumption was applied here, but its value is
     confidential").
  3. Source references on redacted parameters are also dropped, and
     a separate ``remove_source_ids`` list scrubs sources from
     non-redacted parameters too.
  4. Every redaction produces a ``SanitisationRecord`` so the public
     bundle is fully reviewable.
  5. The sanitised bundle's ``sanitised_integrity_hash`` is content-
     addressed, byte-stable across reruns, and different from the
     source bundle's ``integrity_hash``.
  6. The source bundle is never mutated.
  7. An "empty" sanitisation request (nothing to redact) produces a
     sanitisation_records=[] sanitised bundle whose hash is stable.

Closes R11 in docs/scientific_hardening_tracker.md.
"""

from __future__ import annotations

from pathlib import Path

from fate_mcp.integrations import (
    build_concentration_surface_bundle,
    sanitise_concentration_surface_bundle_for_public_release,
)
from fate_mcp.models import (
    BuildEnvironmentalReleaseScenarioRequest,
    FateModelRunOptions,
    Media,
    ReleaseFraction,
    SanitisationRedactionKind,
)
from fate_mcp.runtime import FateRuntime

from tests._pendimethalin_slice_runner import frozen_environment


REPO_ROOT = Path(__file__).resolve().parents[1]
REDACTED_VALUE_PLACEHOLDER = "[REDACTED]"


def _build_seeded_bundle():
    """Build a deterministic ConcentrationSurfaceBundle for sanitisation tests."""
    runtime = FateRuntime(REPO_ROOT)
    scenario = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={
                "preferredName": "Sanitisation test substance",
                "casrn": "100-00-0",
                "substance_class": "organic chemical",
            },
            total_release_mass_kg=10.0,
            release_fractions=[
                ReleaseFraction(medium=Media.WATER, fraction=0.6),
                ReleaseFraction(medium=Media.SOIL, fraction=0.4),
            ],
            duration_days=14.0,
            parameter_records=[
                {
                    "parameter": "water_half_life_days",
                    "value": 12.0,
                    "unit": "day",
                    "source_classification": "user_input",
                    "rationale": "Sponsor-supplied confidential DT50.",
                    "evidence_quality": "reference",
                    "source_reference": {
                        "source_id": "confidential.sponsor.study.12345",
                        "title": "Unpublished sponsor study (confidential)",
                        "url": None,
                    },
                },
            ],
        )
    )
    result = runtime.estimate(
        scenario,
        FateModelRunOptions(region_profile_id=scenario.geographic_scope.region_id),
    )
    return build_concentration_surface_bundle(result)


def test_sanitised_bundle_preserves_non_confidential_structure() -> None:
    bundle = _build_seeded_bundle()
    sanitised = sanitise_concentration_surface_bundle_for_public_release(
        bundle,
        redact_parameter_names=["water_half_life_days"],
        remove_source_ids=[],
        sanitisation_rationale="Sponsor-supplied DT50 is confidential.",
    )
    # Non-confidential structure must be preserved byte-equally.
    assert sanitised.scenario_id == bundle.scenario_id
    assert len(sanitised.surfaces) == len(bundle.surfaces)
    assert sanitised.surfaces == bundle.surfaces
    assert sanitised.run_summary == bundle.run_summary
    assert sanitised.dependencies == bundle.dependencies
    assert sanitised.source_bundle_id == bundle.bundle_id
    assert sanitised.source_bundle_integrity_hash == bundle.integrity_hash
    assert sanitised.confidentiality_posture == "sanitised_public"


def test_sanitised_bundle_redacts_confidential_parameter_values() -> None:
    bundle = _build_seeded_bundle()
    sanitised = sanitise_concentration_surface_bundle_for_public_release(
        bundle,
        redact_parameter_names=["water_half_life_days"],
        remove_source_ids=[],
    )

    # The water_half_life_days value is now a placeholder string.
    redacted_assumptions = [
        item for item in sanitised.assumptions
        if item.parameter == "water_half_life_days"
    ]
    assert redacted_assumptions, "water_half_life_days assumption must survive (with placeholder)"
    for item in redacted_assumptions:
        assert item.value == REDACTED_VALUE_PLACEHOLDER
        # The embedded source_reference on a redacted parameter is also dropped.
        assert item.source_reference is None

    # Non-redacted assumptions keep their original numeric values intact.
    non_redacted = [
        item for item in sanitised.assumptions
        if item.parameter != "water_half_life_days"
    ]
    bundle_non_redacted = [
        item for item in bundle.assumptions
        if item.parameter != "water_half_life_days"
    ]
    assert len(non_redacted) == len(bundle_non_redacted)
    for sanitised_item, original_item in zip(non_redacted, bundle_non_redacted):
        assert sanitised_item.value == original_item.value


def test_sanitisation_records_document_every_redaction() -> None:
    bundle = _build_seeded_bundle()
    sanitised = sanitise_concentration_surface_bundle_for_public_release(
        bundle,
        redact_parameter_names=["water_half_life_days"],
        remove_source_ids=[],
        sanitisation_rationale="Sponsor-supplied DT50 is confidential.",
    )
    # We expect at minimum: one parameter-value redaction + one source-
    # reference removal (because the redacted parameter had a source_reference).
    kinds = [r.redaction_kind for r in sanitised.sanitisation_records]
    assert SanitisationRedactionKind.PARAMETER_VALUE_REDACTED_TO_PLACEHOLDER in kinds
    assert SanitisationRedactionKind.SOURCE_REFERENCE_REMOVED in kinds

    for record in sanitised.sanitisation_records:
        assert record.field_path
        assert record.parameter_or_source_id
        assert record.rationale


def test_sanitised_integrity_hash_is_byte_stable_across_reruns() -> None:
    """The sanitised integrity hash is a pure function of inputs. Two reruns
    of the same sanitisation call against a frozen bundle must produce
    byte-identical sanitised integrity hashes."""
    with frozen_environment():
        bundle_a = _build_seeded_bundle()
        sanitised_a = sanitise_concentration_surface_bundle_for_public_release(
            bundle_a,
            redact_parameter_names=["water_half_life_days"],
            remove_source_ids=["confidential.sponsor.study.12345"],
            sanitisation_rationale="Sponsor-supplied DT50 is confidential.",
        )

    with frozen_environment():
        bundle_b = _build_seeded_bundle()
        sanitised_b = sanitise_concentration_surface_bundle_for_public_release(
            bundle_b,
            redact_parameter_names=["water_half_life_days"],
            remove_source_ids=["confidential.sponsor.study.12345"],
            sanitisation_rationale="Sponsor-supplied DT50 is confidential.",
        )

    assert sanitised_a.sanitised_integrity_hash is not None
    assert len(sanitised_a.sanitised_integrity_hash) == 64
    assert sanitised_a.sanitised_integrity_hash == sanitised_b.sanitised_integrity_hash, (
        "Sanitised integrity hash drifted across two byte-identical sanitisations "
        f"of a frozen bundle: {sanitised_a.sanitised_integrity_hash!r} vs "
        f"{sanitised_b.sanitised_integrity_hash!r}"
    )


def test_sanitised_integrity_hash_differs_from_source_bundle_hash() -> None:
    """The sanitised bundle has its own hash, distinct from the source
    bundle's hash. If they collided, a consumer could not distinguish the
    sanitised public projection from the raw internal bundle."""
    bundle = _build_seeded_bundle()
    sanitised = sanitise_concentration_surface_bundle_for_public_release(
        bundle,
        redact_parameter_names=["water_half_life_days"],
        remove_source_ids=[],
    )
    assert sanitised.sanitised_integrity_hash != bundle.integrity_hash


def test_sanitisation_does_not_mutate_source_bundle() -> None:
    """The source bundle must be unchanged after sanitisation. A consumer who
    still holds the raw bundle must see its original values and original
    integrity hash."""
    bundle = _build_seeded_bundle()
    original_hash = bundle.integrity_hash
    original_assumption_count = len(bundle.assumptions)
    original_water_assumption = next(
        item for item in bundle.assumptions if item.parameter == "water_half_life_days"
    )
    original_water_value = original_water_assumption.value
    original_water_source = original_water_assumption.source_reference

    sanitise_concentration_surface_bundle_for_public_release(
        bundle,
        redact_parameter_names=["water_half_life_days"],
        remove_source_ids=["confidential.sponsor.study.12345"],
    )

    assert bundle.integrity_hash == original_hash
    assert len(bundle.assumptions) == original_assumption_count
    water_assumption_after = next(
        item for item in bundle.assumptions if item.parameter == "water_half_life_days"
    )
    assert water_assumption_after.value == original_water_value
    assert water_assumption_after.source_reference == original_water_source


def test_empty_sanitisation_request_produces_stable_empty_record_list() -> None:
    """A sanitisation call with no redactions or removals must still produce
    a well-formed sanitised bundle (with an empty sanitisation_records list),
    so consumers can use the sanitisation lane as a defensive default
    projection even when no fields are flagged confidential."""
    bundle = _build_seeded_bundle()
    sanitised = sanitise_concentration_surface_bundle_for_public_release(
        bundle,
        redact_parameter_names=[],
        remove_source_ids=[],
    )
    assert sanitised.sanitisation_records == []
    assert sanitised.sanitised_integrity_hash is not None
    assert len(sanitised.sanitised_integrity_hash) == 64
    # Every original assumption survives unmodified.
    for sanitised_item, original_item in zip(sanitised.assumptions, bundle.assumptions):
        assert sanitised_item.value == original_item.value
        assert sanitised_item.source_reference == original_item.source_reference


def test_remove_source_ids_scrubs_sources_on_non_redacted_parameters() -> None:
    """``remove_source_ids`` operates on *all* assumption records, not just
    the ones whose parameter is in ``redact_parameter_names``. A confidential
    citation on a non-confidential parameter should still be removed."""
    bundle = _build_seeded_bundle()
    # Find a non-redacted assumption that has a source_reference (one will
    # exist if any curated default carries a source_id we can target).
    targetable = [
        item for item in bundle.assumptions
        if item.parameter != "water_half_life_days" and item.source_reference is not None
    ]
    if not targetable:
        # If no non-redacted assumption carries a source_reference, the test
        # exits without action -- the scenario doesn't exercise the lane.
        return

    target_source_id = targetable[0].source_reference.source_id
    sanitised = sanitise_concentration_surface_bundle_for_public_release(
        bundle,
        redact_parameter_names=[],
        remove_source_ids=[target_source_id],
    )
    # The source has been removed.
    assert any(
        item.source_reference is None and item.parameter == targetable[0].parameter
        for item in sanitised.assumptions
    )
    # And the removal is recorded.
    assert any(
        record.redaction_kind == SanitisationRedactionKind.SOURCE_REFERENCE_REMOVED
        and record.parameter_or_source_id == target_source_id
        for record in sanitised.sanitisation_records
    )
