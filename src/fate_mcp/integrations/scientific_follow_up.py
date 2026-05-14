"""Governed scientific follow-up pipeline (R12).

This module implements a linear five-stage follow-up workflow analogous to
the Dietary MCP owner pipeline:

    QUEUED -> UNDER_REVIEW_BOARD -> OWNER_HANDOFF -> OWNER_REMEDIATION
    -> OWNER_SIGNOFF

The pipeline is deliberately linear in v1: each transition advances by
exactly one stage. Skipping a stage, going backward, or re-entering a
completed stage fires a FateValidationError. The OWNER_SIGNOFF stage is
terminal: no further transitions are permitted.

Every transition carries at least one ``ScientificFollowUpAcceptanceEvidence``
entry pointing at a concrete artifact (test path, PR URL, docs link) so the
bundle is fully auditable end-to-end. The bundle itself carries a content-
addressed SHA-256 ``integrity_hash`` over the entire transition log so
downstream consumers can verify the trail has not been altered.

v1 scope is deliberately minimal:

* The helpers are public integration functions but are **not** yet wrapped
  as MCP tools. Operators consume them directly from
  ``fate_mcp.integrations.scientific_follow_up``.
* Stage-specific payloads are caller-supplied via the ``rationale`` and
  ``acceptance_evidence`` fields; the pipeline does not yet enforce
  stage-specific schemas (e.g., "owner signoff must include a digest of the
  remediation actions"). Future work tracked under R12 follow-ups.
* The pipeline operates on bundles created by ``enqueue_scientific_follow_up``;
  there is no automatic ingest from ``preview_scientific_review_outcome``
  outputs yet (the caller supplies the optional preview ID at enqueue time).

This is enough to close R12: the linear state machine is enforced, every
transition is auditable, and the integrity hash is byte-stable.
"""

from __future__ import annotations

import hashlib
import json

from fate_mcp.compat import UTC, datetime
from fate_mcp.errors import FateValidationError
from fate_mcp.models import (
    ScientificFollowUpAcceptanceEvidence,
    ScientificFollowUpBundle,
    ScientificFollowUpStage,
    ScientificFollowUpStageTransition,
)


# Linear stage order. The state machine permits exactly the transitions
# (stage_order[i], stage_order[i+1]).
_STAGE_ORDER: tuple[ScientificFollowUpStage, ...] = (
    ScientificFollowUpStage.QUEUED,
    ScientificFollowUpStage.UNDER_REVIEW_BOARD,
    ScientificFollowUpStage.OWNER_HANDOFF,
    ScientificFollowUpStage.OWNER_REMEDIATION,
    ScientificFollowUpStage.OWNER_SIGNOFF,
)


def _next_stage(stage: ScientificFollowUpStage) -> ScientificFollowUpStage | None:
    """Return the next-permitted stage after ``stage``, or ``None`` if
    ``stage`` is terminal."""
    try:
        index = _STAGE_ORDER.index(stage)
    except ValueError as exc:  # pragma: no cover - defensive
        raise FateValidationError(
            code="unknown_scientific_follow_up_stage",
            message=f"Stage {stage!r} is not part of the governed pipeline.",
            suggestion="Use one of the ScientificFollowUpStage enum values.",
        ) from exc
    if index == len(_STAGE_ORDER) - 1:
        return None
    return _STAGE_ORDER[index + 1]


def _compute_integrity_hash(bundle: ScientificFollowUpBundle) -> str:
    payload = bundle.model_dump(mode="json", exclude={"integrity_hash"})
    hash_input = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(hash_input.encode("utf-8")).hexdigest()


def enqueue_scientific_follow_up(
    *,
    scenario_id: str,
    rationale: str,
    acceptance_evidence: list[ScientificFollowUpAcceptanceEvidence],
    review_outcome_preview_id: str | None = None,
    transitioned_at: datetime | None = None,
) -> ScientificFollowUpBundle:
    """Create a new follow-up bundle in the QUEUED stage.

    The initial enqueue is recorded as a transition with ``from_stage=None``
    and ``to_stage=QUEUED``. At least one acceptance-evidence entry must be
    supplied so the enqueue itself is auditable.
    """
    if not scenario_id:
        raise FateValidationError(
            code="scientific_follow_up_missing_scenario_id",
            message="scenario_id is required when enqueueing a scientific follow-up bundle.",
            suggestion="Pass a non-empty scenario_id (typically from a ConcentrationEstimationResult).",
        )
    if not rationale:
        raise FateValidationError(
            code="scientific_follow_up_missing_rationale",
            message="Enqueueing a scientific follow-up bundle requires a non-empty rationale.",
            suggestion="Provide a free-text rationale explaining why follow-up is being initiated.",
        )
    if not acceptance_evidence:
        raise FateValidationError(
            code="scientific_follow_up_missing_acceptance_evidence",
            message=(
                "At least one acceptance-evidence entry is required at enqueue time so "
                "the initial QUEUED state is traceable to a concrete artifact."
            ),
            suggestion=(
                "Supply a ScientificFollowUpAcceptanceEvidence pointing at the originating "
                "review preview, the related PR, or the docs page."
            ),
        )

    transition_time = transitioned_at or datetime.now(UTC)
    initial_transition = ScientificFollowUpStageTransition(
        from_stage=None,
        to_stage=ScientificFollowUpStage.QUEUED,
        transitioned_at=transition_time,
        rationale=rationale,
        acceptance_evidence=acceptance_evidence,
    )
    bundle = ScientificFollowUpBundle(
        scenario_id=scenario_id,
        review_outcome_preview_id=review_outcome_preview_id,
        current_stage=ScientificFollowUpStage.QUEUED,
        transitions=[initial_transition],
    )
    bundle.integrity_hash = _compute_integrity_hash(bundle)
    return bundle


def advance_scientific_follow_up(
    bundle: ScientificFollowUpBundle,
    *,
    to_stage: ScientificFollowUpStage,
    rationale: str,
    acceptance_evidence: list[ScientificFollowUpAcceptanceEvidence],
    transitioned_at: datetime | None = None,
) -> ScientificFollowUpBundle:
    """Advance the bundle by exactly one stage in the linear pipeline.

    Returns a new bundle (the source bundle is never mutated) with the
    transition appended and ``integrity_hash`` recomputed over the full new
    transition log. Raises ``FateValidationError`` if the transition is not
    the next-permitted linear step, if the bundle is already in a terminal
    stage, or if the rationale / acceptance-evidence preconditions are not
    met.
    """
    if bundle.current_stage == ScientificFollowUpStage.OWNER_SIGNOFF:
        raise FateValidationError(
            code="scientific_follow_up_terminal_stage_cannot_advance",
            message=(
                "Bundle is already in the terminal OWNER_SIGNOFF stage; no further "
                "transitions are permitted."
            ),
            suggestion=(
                "Open a new follow-up bundle (enqueue_scientific_follow_up) if the "
                "scenario needs another review cycle."
            ),
            details={"follow_up_id": bundle.follow_up_id},
        )

    expected_next = _next_stage(bundle.current_stage)
    if to_stage != expected_next:
        raise FateValidationError(
            code="scientific_follow_up_non_linear_transition",
            message=(
                f"Transition {bundle.current_stage.value} -> {to_stage.value} is not the "
                f"next-permitted linear step. Expected {bundle.current_stage.value} -> "
                f"{expected_next.value if expected_next else 'terminal'}."
            ),
            suggestion=(
                "Advance the bundle through every intervening stage with its own "
                "transition record so the audit trail remains complete."
            ),
            details={
                "follow_up_id": bundle.follow_up_id,
                "current_stage": bundle.current_stage.value,
                "requested_stage": to_stage.value,
                "expected_stage": expected_next.value if expected_next else None,
            },
        )

    if not rationale:
        raise FateValidationError(
            code="scientific_follow_up_missing_rationale",
            message=(
                f"Advancing to {to_stage.value} requires a non-empty rationale so the "
                "transition is auditable."
            ),
            suggestion="Provide a free-text rationale for this stage advance.",
        )
    if not acceptance_evidence:
        raise FateValidationError(
            code="scientific_follow_up_missing_acceptance_evidence",
            message=(
                f"Advancing to {to_stage.value} requires at least one acceptance-"
                "evidence entry so the transition is traceable to a concrete artifact."
            ),
            suggestion=(
                "Supply a ScientificFollowUpAcceptanceEvidence pointing at the "
                "review-board minutes, the owner-handoff document, the remediation "
                "PR, or the signoff dossier as appropriate for this stage."
            ),
        )

    transition_time = transitioned_at or datetime.now(UTC)
    new_transition = ScientificFollowUpStageTransition(
        from_stage=bundle.current_stage,
        to_stage=to_stage,
        transitioned_at=transition_time,
        rationale=rationale,
        acceptance_evidence=acceptance_evidence,
    )
    advanced = bundle.model_copy(
        update={
            "current_stage": to_stage,
            "transitions": [*bundle.transitions, new_transition],
            "integrity_hash": None,
        },
        deep=True,
    )
    advanced.integrity_hash = _compute_integrity_hash(advanced)
    return advanced
