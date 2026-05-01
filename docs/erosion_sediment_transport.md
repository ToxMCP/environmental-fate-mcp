# Erosion/Sediment Transport Screening

Environmental Fate MCP includes a bounded scalar screening extension for erosion-mediated transport.
It is intended to answer whether contaminated soil or particle-bound chemical may plausibly move through
erosion and runoff-driven sediment pathways.

## Native v1 Tools

- `fate_screen_erosion_transport_relevance` screens whether particle-bound transport is high, medium, low, or unknown from scenario substance class plus Koc/Kd/logKow parameter records.
- `fate_estimate_soil_loss_rusle` computes scalar RUSLE annual soil loss with `A = R * K * LS * C * P`.
- `fate_estimate_event_sediment_yield_musle` computes scalar MUSLE event sediment yield with caller-supplied runoff volume and peak runoff rate.
- `fate_estimate_sediment_associated_chemical_load` converts sediment yield plus topsoil concentration and explicit delivery/availability fractions into a sediment-associated chemical-load handoff.
- `fate_build_erosion_sediment_validation_case` packages inline observed and predicted scalar erosion/sediment records for reviewer-facing validation QA.
- `fate_assess_erosion_sediment_validation_fit` computes non-calibrating observed-versus-predicted fit diagnostics and classifies the comparison as `good_screening_fit`, `screening_plausible`, `weak_fit`, or `insufficient_evidence`.

The governed method metadata is available at `defaults://erosion-sediment-method-profiles`.
The governed validation-threshold metadata is available at `defaults://erosion-sediment-validation-profiles`.

## Boundary

These tools do not simulate rainfall-runoff generation, hydrologic routing, GIS/raster erosion fields,
channel transport, deposition maps, receiving-water dilution, calibration, exposure, risk, or regulatory acceptance.

RUSLE is used only as an annual erosion-potential screen. MUSLE is used only when runoff volume and peak
runoff rate are supplied by the caller or another model. The chemical-load bridge emits load only, not an
environmental concentration. Validation QA compares caller-provided inline observed/predicted records by
`record_id` only; it does not fit parameters, correct hydrology, tune delivery ratios, or certify model
performance for decision-facing watershed use.

## WEPP

WEPP is documented as a future external adapter path. This release does not run, reimplement, or claim
scientific equivalence to WEPP. Future support should prepare or ingest externally governed WEPP scenarios
and outputs, preserve model/version provenance, and normalize only bounded handoff fields into MCP
contracts.
