# Limitations

This case pack is a public-source slice for demonstrating Environmental Fate MCP screening. It is not a regulatory submission, calibration corpus, or source-engine reproduction.

## Explicit non-claims

- Physchem values are drawn from FOOTPRINT PPDB and are screening-grade inputs, not GLP studies re-extracted at row level.
- The scenario release fractions (95% soil, 5% air) are illustrative spring application allocations, not measured drift fractions for a specific application event.
- The 12 degC scenario temperature is a UK spring soil-temperature anchor; per-day soil temperatures vary and are not modelled in this slice.
- The region profile (`eu_screening_default`) is a regional-screening surrogate. Post-Brexit UK regulatory divergence is not modelled in v1 of this slice.
- The probabilistic lane uses a single lognormal envelope on soil DT50 (range approximately 33-182 d, median 100 d). Real probabilistic assessment would correlate multiple physchem inputs.
- The P95/P50 ratio in the probabilistic soil surface is small (~1.0005). This is correct physics for a single-day release with soil DT50 = 100 d: the loss term `exp(-k*t)` over 1 day is dominated by `t`, not by half-life uncertainty. The slice exercises the probabilistic machinery (200 iterations, seeded reproducibility, sample manifests, integrity hashing) even though the underlying physics says half-life uncertainty has little leverage at this duration; this is itself a useful reviewer-facing finding.
- The RUSLE factors (R, K, LS, C, P) are illustrative UK lowland arable inputs; they are not site-measured.
- The MUSLE design storm (525 m^3 runoff, 0.18 m^3/s peak rate, ~21 mm of runoff across 2.5 ha) is illustrative; real assessment requires basin-specific runoff modelling.
- The sediment-associated chemical-load handoff is a load-only contract. It does not compute a receiving-water concentration. Receiving-water concentration is out of scope and would require a downstream hydrodynamic model.
- The scientific review outcome and recommended actions are produced by the governed review-rubric layer; they are reviewer-facing rule-based outputs, not expert review.
- The regulatory handoff package is a downstream-MCP handoff contract, not a regulatory submission.

## Backlog

- Add a UK-specific region profile when one is curated.
- Add a correlated multi-parameter probabilistic distribution (Koc plus soil DT50 plus water DT50).
- Add a site-specific erosion case pack once an independent UK arable runoff dataset is identified.
- Add a Level III fugacity comparison once that lane reaches reviewer-grade evidence quality.
- Add a paired Direct-Use Exposure MCP handoff demonstration that consumes the regulatory handoff package emitted here.
