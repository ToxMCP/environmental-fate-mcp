# Scientific Follow-Up Pipeline

Environmental Fate MCP v0.5.x ships a governed multi-stage scientific
follow-up pipeline analogous to the Dietary MCP owner pipeline. It
closes row `R12` in
[`scientific_hardening_tracker.md`](scientific_hardening_tracker.md).

## Why the pipeline exists

The existing `fate_preview_scientific_review_outcome` tool returns a
single `ScientificReviewOutcomePreview` — a static snapshot of "what a
governed reviewer would say about this run." That snapshot is the
*entry point* of a review, not the entire review. For non-trivial
assessments — anything where a screening output is going to inform a
real decision — the review needs to traverse a linear, auditable
pipeline:

```
QUEUED  ->  UNDER_REVIEW_BOARD  ->  OWNER_HANDOFF
        ->  OWNER_REMEDIATION   ->  OWNER_SIGNOFF
```

Each stage has a different audience and a different acceptance
condition:

| Stage | Audience | Acceptance condition |
| --- | --- | --- |
| `QUEUED` | The follow-up author | A non-empty rationale + at least one acceptance-evidence pointer (preview, related PR, docs) |
| `UNDER_REVIEW_BOARD` | The review board | Board minutes or equivalent recorded decision |
| `OWNER_HANDOFF` | The remediation owner | A handoff document or PR description with the owner identified |
| `OWNER_REMEDIATION` | The remediation owner | A PR or evidence artifact showing the remediation work |
| `OWNER_SIGNOFF` | The signoff authority | A signoff dossier or equivalent terminal artifact |

The pipeline does not prescribe the *content* of each artifact in v1
— it only enforces that an artifact is *cited* at every transition.
This keeps the pipeline usable for any review style (formal review
board, lightweight peer review, single-author remediation) while
guaranteeing the audit trail is complete.

## Public contract

The pipeline is implemented in
`fate_mcp.integrations.scientific_follow_up` and surfaced through:

- `ScientificFollowUpStage` (enum: `queued`, `under_review_board`,
  `owner_handoff`, `owner_remediation`, `owner_signoff`)
- `ScientificFollowUpAcceptanceEvidence` (`evidence_uri`,
  `description`, `recorded_at`, `recorded_by`)
- `ScientificFollowUpStageTransition` (`from_stage`, `to_stage`,
  `transitioned_at`, `rationale`, `acceptance_evidence`)
- `ScientificFollowUpBundle` (`follow_up_id`, `scenario_id`,
  `review_outcome_preview_id`, `current_stage`, `transitions`,
  `integrity_hash`, `regulatory_use_disclaimer`)

Two helper functions:

```python
def enqueue_scientific_follow_up(
    *,
    scenario_id: str,
    rationale: str,
    acceptance_evidence: list[ScientificFollowUpAcceptanceEvidence],
    review_outcome_preview_id: str | None = None,
    transitioned_at: datetime | None = None,
) -> ScientificFollowUpBundle: ...


def advance_scientific_follow_up(
    bundle: ScientificFollowUpBundle,
    *,
    to_stage: ScientificFollowUpStage,
    rationale: str,
    acceptance_evidence: list[ScientificFollowUpAcceptanceEvidence],
    transitioned_at: datetime | None = None,
) -> ScientificFollowUpBundle: ...
```

`enqueue_scientific_follow_up` creates a fresh bundle in the `QUEUED`
state with a single transition entry (`from_stage=None`,
`to_stage=QUEUED`). At least one acceptance-evidence entry must be
supplied at enqueue time.

`advance_scientific_follow_up` returns a *new* bundle with the
requested transition appended. The source bundle is never mutated. The
function raises `FateValidationError` if:

- the bundle is already in the terminal `OWNER_SIGNOFF` stage
  (`scientific_follow_up_terminal_stage_cannot_advance`),
- the requested transition skips a stage or goes backward
  (`scientific_follow_up_non_linear_transition`),
- the rationale or acceptance-evidence list is empty
  (`scientific_follow_up_missing_rationale` /
  `scientific_follow_up_missing_acceptance_evidence`).

## Reviewer-grade properties

The regression test at
[`tests/test_scientific_follow_up.py`](../tests/test_scientific_follow_up.py)
asserts each of the following contract properties:

- **Enqueue produces a well-formed initial bundle.** One transition
  entry, `from_stage=None`, `to_stage=QUEUED`, hash present (64-char
  SHA-256).
- **Linear progression works.** The bundle advances cleanly through
  every stage in order; the final bundle has 5 transition entries
  (initial + 4 advances) and ends in `OWNER_SIGNOFF`.
- **Skipping a stage fails closed** with
  `scientific_follow_up_non_linear_transition`.
- **Going backward fails closed** with the same code.
- **Advancing past `OWNER_SIGNOFF` fails closed** with
  `scientific_follow_up_terminal_stage_cannot_advance`.
- **Enqueue and advance both reject empty rationale, empty evidence,
  and empty scenario_id** with named codes.
- **The integrity hash is byte-stable for equal inputs** (under the
  frozen-environment helper) and **changes when a transition is
  appended**.
- **`advance_scientific_follow_up` does not mutate the source
  bundle**; consumers holding the pre-transition bundle keep seeing
  its original stage, transition log, and hash.

## v1 scope and roadmap

The v1 pipeline is deliberately minimal:

- **Public integration functions, no MCP tool wrap.** Operators
  consume the helpers directly from
  `fate_mcp.integrations.scientific_follow_up`. A future iteration may
  add `fate_enqueue_scientific_follow_up` / `fate_advance_scientific_
  follow_up` MCP tools.
- **Linear-only state machine.** Branching review patterns (e.g., a
  review-board decision that routes back to remediation without
  passing through signoff) are not yet supported. The current contract
  is "any non-linear motion is an error you must justify by opening a
  new follow-up bundle."
- **Caller-supplied stage payloads.** v1 does not enforce stage-
  specific schemas (e.g., "the `OWNER_SIGNOFF` transition must include
  a digest of the remediation actions"). Every transition is recorded
  with `rationale` + `acceptance_evidence` lists; richer stage-specific
  payloads are tracked as a follow-up under R12.
- **No automatic ingest from review previews.** The caller supplies
  the optional `review_outcome_preview_id` at enqueue time. A future
  iteration may automatically thread the preview into the initial
  evidence list.

These follow-up surfaces are tracked separately; the v1 contract
("linear five-stage state machine with auditable transitions and a
content-addressed bundle hash") is sufficient to close `R12`.

## Boundary

The follow-up pipeline is a governance audit trail. It is not:

- a regulatory decision engine,
- a submission dossier producer,
- a claim that any external authority has reviewed or accepted the
  underlying scientific outputs, or
- a substitute for the existing scientific-review preview / packet /
  dossier surfaces (those produce *evidence* the pipeline cites).

Every governance boundary that applies to the bundles cited by the
pipeline (no regulator acceptance, no source-engine equivalence, no
field validation) applies identically to the follow-up bundle.
