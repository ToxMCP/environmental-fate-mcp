"""Regression tests for the governed scientific follow-up pipeline (R12).

The pipeline is a linear five-stage state machine:

    QUEUED -> UNDER_REVIEW_BOARD -> OWNER_HANDOFF -> OWNER_REMEDIATION
    -> OWNER_SIGNOFF

These tests confirm:

  1. Enqueueing produces a bundle in the QUEUED stage with one transition
     entry, a hash, and the right scenario_id / preview_id wiring.
  2. The pipeline advances cleanly through every stage in order.
  3. Skipping a stage fires a non-linear-transition error.
  4. Going backward fires a non-linear-transition error.
  5. Advancing past OWNER_SIGNOFF fires a terminal-stage error.
  6. Enqueueing without rationale or evidence fails closed.
  7. Advancing without rationale or evidence fails closed.
  8. The integrity hash is content-addressed, byte-stable across reruns
     for the same inputs, and changes when a transition is appended.
  9. The source bundle is never mutated by `advance_scientific_follow_up`
     (the function returns a new bundle).

Closes R12 in docs/scientific_hardening_tracker.md.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from fate_mcp.errors import FateValidationError
from fate_mcp.integrations import (
    advance_scientific_follow_up,
    enqueue_scientific_follow_up,
)
from fate_mcp.models import (
    ScientificFollowUpAcceptanceEvidence,
    ScientificFollowUpStage,
)


FROZEN_T0 = datetime(2026, 5, 14, 12, 0, 0, tzinfo=timezone.utc)


def _evidence(uri: str = "tests/test_scientific_follow_up.py") -> ScientificFollowUpAcceptanceEvidence:
    return ScientificFollowUpAcceptanceEvidence(
        evidence_uri=uri,
        description="Regression-test fixture evidence",
        recorded_at=FROZEN_T0,
        recorded_by="test-harness",
    )


def _enqueue() -> object:
    return enqueue_scientific_follow_up(
        scenario_id="scenario-test-0001",
        rationale="Initial enqueue under the regression test fixture.",
        acceptance_evidence=[_evidence()],
        review_outcome_preview_id="scireview-test-0001",
        transitioned_at=FROZEN_T0,
    )


def test_enqueue_creates_queued_bundle_with_one_transition() -> None:
    bundle = _enqueue()
    assert bundle.scenario_id == "scenario-test-0001"
    assert bundle.review_outcome_preview_id == "scireview-test-0001"
    assert bundle.current_stage == ScientificFollowUpStage.QUEUED
    assert len(bundle.transitions) == 1
    first = bundle.transitions[0]
    assert first.from_stage is None
    assert first.to_stage == ScientificFollowUpStage.QUEUED
    assert first.acceptance_evidence
    assert bundle.integrity_hash is not None
    assert len(bundle.integrity_hash) == 64


def test_pipeline_advances_cleanly_through_every_stage_in_order() -> None:
    bundle = _enqueue()
    expected_order = [
        ScientificFollowUpStage.UNDER_REVIEW_BOARD,
        ScientificFollowUpStage.OWNER_HANDOFF,
        ScientificFollowUpStage.OWNER_REMEDIATION,
        ScientificFollowUpStage.OWNER_SIGNOFF,
    ]
    for next_stage in expected_order:
        bundle = advance_scientific_follow_up(
            bundle,
            to_stage=next_stage,
            rationale=f"Advancing to {next_stage.value}",
            acceptance_evidence=[_evidence(f"docs/{next_stage.value}.md")],
            transitioned_at=FROZEN_T0,
        )
        assert bundle.current_stage == next_stage
    # Final state: 5 transitions (initial enqueue + 4 advances)
    assert len(bundle.transitions) == 5
    assert bundle.transitions[0].to_stage == ScientificFollowUpStage.QUEUED
    assert bundle.transitions[-1].to_stage == ScientificFollowUpStage.OWNER_SIGNOFF
    # All from/to pairs match the linear order
    pairs = [(t.from_stage, t.to_stage) for t in bundle.transitions[1:]]
    expected_pairs = [
        (ScientificFollowUpStage.QUEUED, ScientificFollowUpStage.UNDER_REVIEW_BOARD),
        (ScientificFollowUpStage.UNDER_REVIEW_BOARD, ScientificFollowUpStage.OWNER_HANDOFF),
        (ScientificFollowUpStage.OWNER_HANDOFF, ScientificFollowUpStage.OWNER_REMEDIATION),
        (ScientificFollowUpStage.OWNER_REMEDIATION, ScientificFollowUpStage.OWNER_SIGNOFF),
    ]
    assert pairs == expected_pairs


def test_skipping_a_stage_fires_non_linear_transition_error() -> None:
    bundle = _enqueue()
    with pytest.raises(FateValidationError) as exc:
        advance_scientific_follow_up(
            bundle,
            to_stage=ScientificFollowUpStage.OWNER_HANDOFF,  # skipping UNDER_REVIEW_BOARD
            rationale="Trying to skip",
            acceptance_evidence=[_evidence()],
            transitioned_at=FROZEN_T0,
        )
    assert exc.value.payload.code == "scientific_follow_up_non_linear_transition"


def test_going_backward_fires_non_linear_transition_error() -> None:
    bundle = _enqueue()
    bundle = advance_scientific_follow_up(
        bundle,
        to_stage=ScientificFollowUpStage.UNDER_REVIEW_BOARD,
        rationale="Forward step",
        acceptance_evidence=[_evidence()],
        transitioned_at=FROZEN_T0,
    )
    with pytest.raises(FateValidationError) as exc:
        advance_scientific_follow_up(
            bundle,
            to_stage=ScientificFollowUpStage.QUEUED,  # going backward
            rationale="Trying to go back",
            acceptance_evidence=[_evidence()],
            transitioned_at=FROZEN_T0,
        )
    assert exc.value.payload.code == "scientific_follow_up_non_linear_transition"


def test_advancing_past_signoff_fires_terminal_stage_error() -> None:
    bundle = _enqueue()
    for next_stage in [
        ScientificFollowUpStage.UNDER_REVIEW_BOARD,
        ScientificFollowUpStage.OWNER_HANDOFF,
        ScientificFollowUpStage.OWNER_REMEDIATION,
        ScientificFollowUpStage.OWNER_SIGNOFF,
    ]:
        bundle = advance_scientific_follow_up(
            bundle,
            to_stage=next_stage,
            rationale="advance",
            acceptance_evidence=[_evidence()],
            transitioned_at=FROZEN_T0,
        )
    with pytest.raises(FateValidationError) as exc:
        advance_scientific_follow_up(
            bundle,
            to_stage=ScientificFollowUpStage.OWNER_SIGNOFF,  # already terminal
            rationale="cannot advance",
            acceptance_evidence=[_evidence()],
            transitioned_at=FROZEN_T0,
        )
    assert exc.value.payload.code == "scientific_follow_up_terminal_stage_cannot_advance"


def test_enqueue_without_rationale_fails_closed() -> None:
    with pytest.raises(FateValidationError) as exc:
        enqueue_scientific_follow_up(
            scenario_id="scenario-test",
            rationale="",
            acceptance_evidence=[_evidence()],
            transitioned_at=FROZEN_T0,
        )
    assert exc.value.payload.code == "scientific_follow_up_missing_rationale"


def test_enqueue_without_acceptance_evidence_fails_closed() -> None:
    with pytest.raises(FateValidationError) as exc:
        enqueue_scientific_follow_up(
            scenario_id="scenario-test",
            rationale="ok",
            acceptance_evidence=[],
            transitioned_at=FROZEN_T0,
        )
    assert exc.value.payload.code == "scientific_follow_up_missing_acceptance_evidence"


def test_enqueue_without_scenario_id_fails_closed() -> None:
    with pytest.raises(FateValidationError) as exc:
        enqueue_scientific_follow_up(
            scenario_id="",
            rationale="ok",
            acceptance_evidence=[_evidence()],
            transitioned_at=FROZEN_T0,
        )
    assert exc.value.payload.code == "scientific_follow_up_missing_scenario_id"


def test_advance_without_rationale_fails_closed() -> None:
    bundle = _enqueue()
    with pytest.raises(FateValidationError) as exc:
        advance_scientific_follow_up(
            bundle,
            to_stage=ScientificFollowUpStage.UNDER_REVIEW_BOARD,
            rationale="",
            acceptance_evidence=[_evidence()],
            transitioned_at=FROZEN_T0,
        )
    assert exc.value.payload.code == "scientific_follow_up_missing_rationale"


def test_advance_without_acceptance_evidence_fails_closed() -> None:
    bundle = _enqueue()
    with pytest.raises(FateValidationError) as exc:
        advance_scientific_follow_up(
            bundle,
            to_stage=ScientificFollowUpStage.UNDER_REVIEW_BOARD,
            rationale="ok",
            acceptance_evidence=[],
            transitioned_at=FROZEN_T0,
        )
    assert exc.value.payload.code == "scientific_follow_up_missing_acceptance_evidence"


def test_integrity_hash_is_byte_stable_for_equal_inputs_and_changes_per_transition() -> None:
    """Two enqueues with byte-identical inputs (frozen timestamp, fixed
    follow_up_id via monkeypatch on the uuid factory) produce the same hash.
    Advancing the bundle by one stage changes the hash."""
    from tests._pendimethalin_slice_runner import frozen_environment

    with frozen_environment():
        bundle_a = _enqueue()
    with frozen_environment():
        bundle_b = _enqueue()
    assert bundle_a.integrity_hash == bundle_b.integrity_hash

    advanced_a = advance_scientific_follow_up(
        bundle_a,
        to_stage=ScientificFollowUpStage.UNDER_REVIEW_BOARD,
        rationale="advance",
        acceptance_evidence=[_evidence()],
        transitioned_at=FROZEN_T0,
    )
    assert advanced_a.integrity_hash != bundle_a.integrity_hash


def test_advance_does_not_mutate_source_bundle() -> None:
    """``advance_scientific_follow_up`` must return a new bundle; the source
    bundle's stage, transition log, and integrity hash must be unchanged."""
    bundle = _enqueue()
    original_stage = bundle.current_stage
    original_hash = bundle.integrity_hash
    original_transition_count = len(bundle.transitions)

    advance_scientific_follow_up(
        bundle,
        to_stage=ScientificFollowUpStage.UNDER_REVIEW_BOARD,
        rationale="advance",
        acceptance_evidence=[_evidence()],
        transitioned_at=FROZEN_T0,
    )

    assert bundle.current_stage == original_stage
    assert bundle.integrity_hash == original_hash
    assert len(bundle.transitions) == original_transition_count
