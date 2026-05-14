# Confidentiality-Aware Bundles

Environmental Fate MCP v0.5.x ships a sanitisation lane for producing
public-facing projections of internal `ConcentrationSurfaceBundle`
objects with confidential parameter values and source references
removed. It closes row `R11` in
[`scientific_hardening_tracker.md`](scientific_hardening_tracker.md)
and is the Fate analogue of the Dietary MCP confidentiality-bundle
posture documented at `Dietary_MCP/docs/confidentiality_bundles.md`.

## Why the sanitisation lane exists

A typical regulatory exchange involves three classes of data inside a
single `ConcentrationSurfaceBundle`:

1. **Public defaults and equations.** Governed surface-water volumes,
   half-life defaults, Q10 factors, and the closed-form first-order
   screening equation are all public infrastructure. Reviewers should
   always see these.
2. **Public physchem.** Substance properties drawn from FOOTPRINT
   PPDB, EPA CompTox, Mackay's handbook, ECHA's published dossiers,
   and similar public databases are public-by-construction.
3. **Confidential physchem or unpublished evidence.** A sponsor may
   supply a confidential DT50 from an unpublished GLP study, an
   internal company measurement of Koc, or a yet-to-be-published
   evidence document. These records have legitimate confidentiality
   constraints during the pre-publication or pre-submission window.

Without a sanitisation lane, the only options for the third class are
to (a) refuse to put the value in the bundle at all (which forfeits
its scientific use) or (b) ship the bundle wholesale to a public
recipient (which leaks the value). The sanitisation lane gives
operators a third option: ship a public projection that retains the
public structure and equations, redacts only the confidential payload,
and is independently hash-verifiable.

## Public contract

The lane is implemented by the integration helper
`fate_mcp.integrations.sanitise_concentration_surface_bundle_for_public_release`
and surfaced through three Pydantic models:

- `SanitisationRedactionKind` (enum) — the kind of redaction applied
  (`parameter_value_redacted_to_placeholder` or
  `source_reference_removed`).
- `SanitisationRecord` — a single machine-readable redaction entry.
- `SanitisedConcentrationSurfaceBundle` — the public projection
  itself.

The helper signature:

```python
def sanitise_concentration_surface_bundle_for_public_release(
    bundle: ConcentrationSurfaceBundle,
    *,
    redact_parameter_names: list[str],
    remove_source_ids: list[str],
    sanitisation_rationale: str | None = None,
) -> SanitisedConcentrationSurfaceBundle: ...
```

For every `FateAssumptionRecord` in `bundle.assumptions`:

- If `record.parameter` is in `redact_parameter_names`, the
  assumption's `value` is replaced with the `[REDACTED]` placeholder
  and any embedded `source_reference` is dropped. A
  `parameter_value_redacted_to_placeholder` record is appended, and a
  paired `source_reference_removed` record is appended if a source was
  present.
- If `record.source_reference.source_id` is in `remove_source_ids`,
  the `source_reference` is set to `None` and a
  `source_reference_removed` record is appended.

The sanitised bundle pins the source bundle's identity and hash:

- `source_bundle_id` — the source's `bundle_id`
- `source_bundle_integrity_hash` — the source's `integrity_hash`

And carries its own tamper-evidence anchor:

- `sanitised_integrity_hash` — a content-addressed SHA-256 over the
  sanitised payload, computed exactly as the source bundle's hash is
  computed (canonical JSON, sort_keys, compact separators).

## Reviewer-grade properties

The regression test at
[`tests/test_sanitisation.py`](../tests/test_sanitisation.py)
asserts each of the following contract properties:

- **Non-confidential structure is byte-preserved.** Surfaces, run
  summary, dependencies, and scenario_id pass through verbatim. A
  reviewer comparing the public projection to a re-run of the
  deterministic kernel can re-derive every public surface value.
- **Confidential values are redacted, not removed.** The assumption
  record survives — only its `value` is replaced. This keeps the
  public bundle reviewable ("a confidential value was applied to
  water_half_life_days here") without exposing the value.
- **Every redaction is logged.** Every change to the public payload
  appears in `sanitisation_records` with `field_path`,
  `redaction_kind`, `parameter_or_source_id`, and free-text
  `rationale`. There are no silent edits.
- **Sanitised hash is byte-stable across reruns.** Under the same
  inputs (and the same frozen environment used by the integrity-hash
  stability tests), two reruns of the sanitisation lane produce
  byte-identical `sanitised_integrity_hash` values.
- **Sanitised hash is distinct from the source bundle's hash.** A
  consumer can always tell a sanitised public projection apart from
  the raw internal bundle.
- **The source bundle is never mutated.** Operators who hold both
  the raw bundle and the sanitised projection in memory see the raw
  bundle's original `integrity_hash` and original assumption values.

## Recommended use

1. Build an internal `ConcentrationSurfaceBundle` exactly as usual
   via `fate_build_concentration_surface_bundle`.
2. Identify which parameters or source IDs are confidential. This is
   a caller-side declaration: the lane does not infer confidentiality
   from any quality-flag or evidence-tier signal in v1.
3. Call `sanitise_concentration_surface_bundle_for_public_release`
   with the two confidential lists and an optional rationale string.
4. Publish only the `SanitisedConcentrationSurfaceBundle` and its
   `sanitised_integrity_hash` to the public recipient. The recipient
   can independently verify the hash by re-serialising the sanitised
   bundle and recomputing the SHA-256, without ever needing the raw
   bundle.

## Current v1 scope and roadmap

The v1 sanitisation lane is intentionally minimal:

- The helper is a public integration function but is **not** yet
  wrapped in an MCP tool. Operators consume it directly from
  `fate_mcp.integrations`.
- Confidentiality is **caller-declared** via the
  `redact_parameter_names` and `remove_source_ids` arguments. A
  future iteration may add a `confidentiality_posture` field to
  `FateParameterRecord` and `SourceReference` so the lane can detect
  redaction targets automatically.
- The lane currently operates on `ConcentrationSurfaceBundle` only.
  A future iteration should add an equivalent sanitised projection
  for `RegulatoryHandoffPackage` and the various review packets.

These follow-up surfaces are tracked separately; the v1 lane is
sufficient to close `R11` because the core capability ("ship a
publicly-verifiable hash-stamped scrubbed projection of a bundle")
is now available.

## Boundary

Sanitised public bundles are packaging artifacts for public-facing
review exchange. They are not:

- complete internal review records,
- submission dossiers,
- regulatory decisions,
- or claims that the underlying physics or defaults have been
  reviewed and approved by any external authority.

The sanitisation lane only adjusts visibility; it does not adjust
scientific posture. Every governance boundary that applies to the
source bundle (no regulator acceptance, no source-engine equivalence,
no field validation) applies identically to the sanitised projection.
