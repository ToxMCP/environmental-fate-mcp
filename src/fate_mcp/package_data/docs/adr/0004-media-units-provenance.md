# ADR 0004: Media, Units, and Provenance Policy

## Status

Accepted

## Decision

Canonical media and units for the current defaults set:

- air -> `mg/m3`
- water -> `mg/L`
- soil -> `mg/kg`
- sediment -> `mg/kg`

Every outward-facing result must include:

- schema version
- model family
- provenance bundle
- limitation notes
- quality flags
- fit-for-purpose tag

Every default must be versioned, attributable, and emitted in the assumption ledger when used.

Impossible media or unit combinations are validation errors, not silent coercions.
