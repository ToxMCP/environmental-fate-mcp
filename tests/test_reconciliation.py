from pathlib import Path

import pytest

from fate_mcp.models import (
    Media,
    ReconcileReleaseEvidenceRequest,
    ReleaseEvidenceInput,
    ReleaseFraction,
    SourceReference,
)
from fate_mcp.runtime import FateRuntime


def test_reconcile_release_evidence_consistent_inputs() -> None:
    runtime = FateRuntime(Path(__file__).resolve().parents[1])
    request = ReconcileReleaseEvidenceRequest(
        chemical_identity={"preferredName": "Example", "substance_class": "organic chemical"},
        duration_days=30.0,
        evidence_inputs=[
            ReleaseEvidenceInput(
                label="source_a",
                total_release_mass_kg=10.0,
                release_fractions=[
                    ReleaseFraction(medium=Media.WATER, fraction=0.6),
                    ReleaseFraction(medium=Media.SOIL, fraction=0.4),
                ],
                source_reference=SourceReference(source_id="src-a", title="Source A"),
            ),
            ReleaseEvidenceInput(
                label="source_b",
                total_release_mass_kg=11.0,
                release_fractions=[
                    ReleaseFraction(medium=Media.WATER, fraction=0.65),
                    ReleaseFraction(medium=Media.SOIL, fraction=0.35),
                ],
                source_reference=SourceReference(source_id="src-b", title="Source B"),
            ),
        ],
    )

    result = runtime.reconcile_release_evidence(request)

    assert result.unresolved_conflict_count == 0
    assert result.reconciled_scenario is not None
    assert not result.vector_conflicts
    assert result.agreed_values["total_release_mass_kg"] == pytest.approx(10.5)
    assert result.agreed_values["release_fraction_water"] == pytest.approx(0.625)
    assert len(result.evidence_observations) == 2
    assert len(result.provenance.source_references) == 2


def test_reconcile_release_evidence_surfaces_structured_conflicts() -> None:
    runtime = FateRuntime(Path(__file__).resolve().parents[1])
    request = ReconcileReleaseEvidenceRequest(
        chemical_identity={"preferredName": "Example", "substance_class": "organic chemical"},
        duration_days=30.0,
        evidence_inputs=[
            ReleaseEvidenceInput(
                label="source_a",
                total_release_mass_kg=10.0,
                release_fractions=[
                    ReleaseFraction(medium=Media.WATER, fraction=0.8),
                    ReleaseFraction(medium=Media.SOIL, fraction=0.2),
                ],
                source_reference=SourceReference(source_id="src-a", title="Source A"),
            ),
            ReleaseEvidenceInput(
                label="source_b",
                total_release_mass_kg=20.0,
                release_fractions=[
                    ReleaseFraction(medium=Media.WATER, fraction=0.2),
                    ReleaseFraction(medium=Media.SOIL, fraction=0.8),
                ],
                source_reference=SourceReference(source_id="src-b", title="Source B"),
            ),
        ],
    )

    result = runtime.reconcile_release_evidence(request)

    conflict_fields = {conflict.field for conflict in result.conflicts}
    assert result.unresolved_conflict_count == 4
    assert result.reconciled_scenario is None
    assert "total_release_mass_kg" in conflict_fields
    assert "release_fraction_water" in conflict_fields
    assert "release_fraction_soil" in conflict_fields
    assert any(flag.code == "release_evidence_conflict" for flag in result.quality_flags)
    assert any(flag.code == "release_vector_conflict" for flag in result.quality_flags)
    assert result.vector_conflicts
    assert any("Resolve competing release-mass estimates" in action for action in result.recommended_next_actions)
    assert any("Do not synthesize a blended screening scenario" in action for action in result.recommended_next_actions)


def test_reconcile_release_evidence_weights_higher_quality_inputs_more_heavily() -> None:
    runtime = FateRuntime(Path(__file__).resolve().parents[1])
    request = ReconcileReleaseEvidenceRequest(
        chemical_identity={"preferredName": "Example", "substance_class": "organic chemical"},
        duration_days=30.0,
        evidence_inputs=[
            ReleaseEvidenceInput(
                label="measured_source",
                total_release_mass_kg=10.0,
                evidence_quality="measured",
                release_fractions=[
                    ReleaseFraction(medium=Media.WATER, fraction=0.9),
                    ReleaseFraction(medium=Media.SOIL, fraction=0.1),
                ],
                source_reference=SourceReference(source_id="src-a", title="Measured Source"),
            ),
            ReleaseEvidenceInput(
                label="heuristic_source",
                total_release_mass_kg=30.0,
                evidence_quality="heuristic",
                release_fractions=[
                    ReleaseFraction(medium=Media.WATER, fraction=0.1),
                    ReleaseFraction(medium=Media.SOIL, fraction=0.9),
                ],
                source_reference=SourceReference(source_id="src-b", title="Heuristic Source"),
            ),
        ],
    )

    result = runtime.reconcile_release_evidence(request)

    assert result.reconciled_scalars[0].reconciled_value == pytest.approx((10.0 * 1.0 + 30.0 * 0.2) / 1.2)
    water_fraction = next(item for item in result.reconciled_release_fractions if item.medium == Media.WATER)
    assert water_fraction.reconciled_fraction == pytest.approx((0.9 * 1.0 + 0.1 * 0.2) / 1.2)
    assert any(flag.code == "low_confidence_release_evidence" for flag in result.quality_flags)
    assert any("heuristic_source" in action for action in result.recommended_next_actions)


def test_reconcile_release_evidence_blocks_orthogonal_release_vectors() -> None:
    runtime = FateRuntime(Path(__file__).resolve().parents[1])
    request = ReconcileReleaseEvidenceRequest(
        chemical_identity={"preferredName": "Example", "substance_class": "organic chemical"},
        duration_days=30.0,
        evidence_inputs=[
            ReleaseEvidenceInput(
                label="stack_source",
                total_release_mass_kg=10.0,
                release_fractions=[ReleaseFraction(medium=Media.AIR, fraction=1.0)],
                source_reference=SourceReference(source_id="src-air", title="Stack Source"),
            ),
            ReleaseEvidenceInput(
                label="drain_source",
                total_release_mass_kg=10.0,
                release_fractions=[ReleaseFraction(medium=Media.WATER, fraction=1.0)],
                source_reference=SourceReference(source_id="src-water", title="Drain Source"),
            ),
        ],
    )

    result = runtime.reconcile_release_evidence(request)

    assert result.reconciled_scenario is None
    assert result.vector_conflicts
    assert result.vector_conflicts[0].cosine_similarity == pytest.approx(0.0)
    assert any(flag.code == "release_vector_conflict" for flag in result.quality_flags)
