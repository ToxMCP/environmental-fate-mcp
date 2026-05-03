# Model Applicability Limits

## Native in the current public release

- `reference_mass_balance`
  screening-oriented deterministic concentration kernel with governed applicability profile at `defaults://model-family-applicability-profile/reference_mass_balance`
- `advective_screening_mass_balance`
  experimental non-default screening kernel with first-order degradation plus governed residence-time clearance at `defaults://model-family-applicability-profile/advective_screening_mass_balance`
- `fugacity_equilibrium_screening`
  experimental non-default Level I/II equilibrium partitioning challenge family at `defaults://model-family-applicability-profile/fugacity_equilibrium_screening`; requires explicit molecular weight, Henry law constant, and Koc records; supports `steady_state` only and publishes governed method profiles at `defaults://fugacity-screening-method-profiles`
- `erosion_sediment_transport`
  standalone scalar screening extension, not a concentration `ModelFamily`; supports RUSLE annual soil-loss screening, MUSLE event sediment-yield screening, particle-bound relevance screening, sediment-associated chemical-load handoff, inline observed-versus-predicted validation QA, and synthetic validation demos through governed method profiles at `defaults://erosion-sediment-method-profiles`, validation profiles at `defaults://erosion-sediment-validation-profiles`, and demo metadata at `defaults://erosion-sediment-validation-demo-pack`
- `scientific_trust_diagnostics`
  governed external benchmark replay at `defaults://scientific-external-benchmark-pack`, deterministic default sensitivity profiles at `defaults://default-sensitivity-profiles`, and optional probabilistic sample manifests for auditability; these are reviewer-facing trust diagnostics, not new fate kernels or calibration workflows

## Extension hook in the current public release

- `adapter_stub`
- `external_result_adapter`
  both extension paths now publish inspectable applicability declarations through `defaults://model-family-applicability-profiles`
  and `external_result_adapter` now exposes a stable public normalized JSON/CSV import contract

## Deferred

- branded desktop-model ingestion as a public contract
- GIS-scale dispersion
- watershed hydrology, rainfall-runoff generation, channel routing, deposition-field modelling, native WEPP execution, and automated erosion/sediment calibration
- Level III fugacity intermedia-transfer coefficients, advective export between media, source-engine equivalence to CEMC tools, and fugacity calibration or field validation
- unrestricted probabilistic orchestration
- full mechanistic food-chain transfer

## Internal-only bridge in the current public release

- concrete legacy screening desktop export import inside `external_result_adapter`
- branded adapter-specific parsing beyond the normalized JSON/CSV public contract

## Review expectation

- assessors should check the declared model-family applicability profile before treating outputs as more than concentration-only screening support
- unsupported substance classes and deferred capabilities are explicit parts of the governed defaults surface
- governed baseline-versus-challenge model-family selection is exposed through `defaults://model-family-selection-profiles`
- governed assessor-facing review of baseline-versus-challenge selection recommendations is available before any model-family comparison packet is built
- a composed assessor-facing challenge review preview and artifact are available when reviewers want the governed selection review and the optional governed comparison review bundled together
- governed composed challenge-review policy is exposed separately through `defaults://model-family-challenge-review-profiles`
- a composed scientific dossier and brief are available when reviewers want the governed challenge-review path and the model-family-specific scientific review outcomes bundled together
- scientific review guidance for each supported model family is exposed separately through `defaults://scientific-review-profiles`
- governed scientific review outcomes can be previewed before packet generation through `fate_preview_scientific_review_outcome`
- the advective family is intentionally experimental and should be compared against the default reference family before decision-facing reuse
- the fugacity family is intentionally experimental and should be compared against the default reference family before reviewer-facing reuse; it is equilibrium partitioning only, not Level III transport, routing, calibration, or regulator acceptance
- RUSLE/MUSLE outputs and validation fit classifications should be reviewed as erosion-mediated transport screening QA only; they do not estimate final receiving-water concentration, exposure, risk, calibrated watershed performance, or regulator acceptance
- synthetic erosion/sediment validation demos demonstrate classification behavior only; they are not field validation, calibration evidence, catchment validation, or WEPP validation
- external benchmark replay and default sensitivity reports should be read as deterministic screening corroboration and assumption-transparency artifacts only; they are not field validation, calibrated model performance evidence, source-engine equivalence, or regulator acceptance
