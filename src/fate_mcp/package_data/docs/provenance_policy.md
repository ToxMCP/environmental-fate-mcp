# Provenance Policy

## Source Classification

Every result must distinguish:

- `user_input`
- `curated_default`
- `derived`
- `heuristic`

Assumption records must preserve:

- parameter name
- resolved value
- unit
- source classification
- source citation or derivation note
- effective date when applicable

Parameter records captured on scenarios preserve evidence-backed overrides before runtime execution. When the reference runtime consumes a parameter record, it is mirrored into the run assumption ledger.
Run parameter manifests now make that distinction explicit by labeling each resolved parameter as runtime-consumed or preserved-only.
Deterministic uncertainty summaries rank reviewer-facing drivers from the same governed provenance state without adding a second evidence taxonomy.

Release-evidence reconciliation outputs preserve source observations, structured conflict records, and the reconciliation method used to build any screening scenario.
Physicochemical evidence reconciliation uses evidence-quality weighting and preserves both the raw observations and the weighted resolved parameter state.

Heuristic pathways must emit warning-quality flags and limitation notes.

## Retention Rules

- **Curated defaults** must be retained for the lifetime of any scenario that references them, even if the defaults file is later updated.
- **User inputs** must be retained in immutable form (original values, units, and timestamps) alongside any runtime-normalized representations.
- **Derived and heuristic values** must retain the complete derivation trace, including intermediate values and the algorithm version used.
- **External adapter imports** must retain the original payload (or a cryptographic hash thereof) in addition to the normalized surface.
- **Run artifacts** (concentration bundles, review packets, handoff profiles) must be retained for a minimum of **10 years** in regulatory-submission contexts or until the associated substance registration is withdrawn, whichever is longer.

## Conflict Resolution Hierarchy

When multiple evidence sources conflict for the same parameter:

1. **Regulatory study (GLP) > peer-reviewed literature > industry study report > QSAR/model prediction > expert judgment > heuristic default.**
2. If quality tiers are equal, the **more recent effective date** prevails.
3. If dates are equal, the **consensus mean** is used and a `conflict` quality flag is emitted.
4. Explicit user overrides always take precedence, but must be flagged with a `user_override` provenance note.

## Expiration and Obsolescence of Curated Defaults

- Every curated default must declare an `effectiveDate`. Defaults without an effective date are treated as **permanent but reviewable**.
- A default may be marked `supersededBy` in the defaults manifest. The runtime will emit a `WARNING` quality flag if a superseded default is used, but will not block execution.
- Defaults that reach a declared `expirationDate` are treated as **heuristic** (not curated) and automatically downgrade in evidence-quality weighting.
- At least once per calendar year, the defaults steward must review all curated defaults with effective dates older than 5 years and either reaffirm, update, or mark them superseded.

## Audit-Trail Integrity

- Every run must produce a `run_id` that is content-addressed with a tamper-evident SHA-256 `integrity_hash` over the scenario, model family, and runtime version payload.
- Any modification of a run artifact after generation invalidates the integrity hash and must be treated as a new run with a new `run_id`.
- Adapter-normalized surfaces must include an `adapter_trace_disclaimer` stating that the native engine calculation trace is unavailable.
