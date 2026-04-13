# Provenance Policy

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
