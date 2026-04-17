# PRD — Environmental Fate MCP

**Product name:** Environmental Fate MCP  
**Version target:** v0.1.0  
**Product type:** Public MCP server for deterministic environmental release, multimedia fate, and concentration-surface generation  
**Date:** 2026-04-08

## 1. Product summary

Environmental Fate MCP is the ToxMCP service that converts **environmental release assumptions** into **multimedia concentration outputs** that downstream systems can consume. It exists so environmental fate does not get mixed into direct human exposure scenario construction inside Direct-Use Exposure MCP.

In the platform architecture, Environmental Fate MCP owns **source-to-concentration** semantics, not concentration-to-dose semantics.

## 2. Problem statement

The current suite has a strong direct-use and near-field external-dose engine, but no dedicated environmental fate layer that can:

- represent releases to environmental media as first-class typed inputs,
- propagate those releases through bounded multimedia fate models,
- emit auditable concentration surfaces for reuse by downstream human-exposure workflows,
- preserve clear provenance and model assumptions, and
- prevent environmental fate logic from bleeding into Direct-Use Exposure MCP.

Without an Environmental Fate MCP, the platform risks either:
- overloading Direct-Use Exposure MCP with incompatible inputs and semantics, or
- exposing tool-native model wrappers without a stable contract boundary.

## 3. Goals

### Primary goals
1. Represent environmental release scenarios as typed, versioned contracts.
2. Compute deterministic or bounded multimedia concentration outputs suitable for downstream use.
3. Emit auditable concentration surfaces with explicit provenance, defaults, and limitations.
4. Keep model-family details behind stable harmonized outputs.
5. Provide concentration surfaces that Direct-Use Exposure MCP and future environmental-intake workflows can consume.

### Secondary goals
1. Support region-aware defaults and scenario archetypes.
2. Support scenario comparison and refinement between alternative release assumptions.
3. Prepare a stable adapter boundary for model families such as SimpleBox, EUSES, and ChemFate-style engines.
4. Leave room for later probabilistic orchestration without breaking v0.1 contracts.

## 4. Non-goals

Environmental Fate MCP v0.1 does **not** own:

- direct human external dose calculation,
- food-consumption or dietary intake workflows,
- PBPK execution or internal dose interpretation,
- final risk characterization or regulatory decision logic,
- high-resolution GIS dispersion as a required baseline,
- fully dynamic spatiotemporal simulation for every use case,
- automatic ingestion of arbitrary desktop-model files as the public contract.

## 5. Users and consumers

### Primary users
- Exposure scientists needing environmental concentration outputs
- ToxClaw orchestrations that need a dedicated fate line of evidence
- Downstream services that convert concentrations into dose
- Researchers comparing release assumptions across regions or media

### System consumers
- Direct-Use Exposure MCP
- Dietary MCP (future, if residue-generation interfaces are added)
- PBPK MCP indirectly through downstream exposure services
- ToxClaw

## 6. Core product boundary

### Environmental Fate MCP owns
- release to air, water, soil, sediment
- multimedia transfer and degradation
- compartment concentration estimation
- concentration surfaces across medium, region/context, and time bucket
- fate-specific assumptions, provenance, defaults, and validation posture
- comparison of alternative release/fate scenarios

### Environmental Fate MCP does not own
- direct-use consumer tasks
- indoor room-use aerosol scenarios
- diet-mediated intake
- human body-weight normalization
- PBPK handoff unless a downstream service has already converted concentration into dose

## 7. Scientific stance for v0.1

Environmental Fate MCP should follow the same **deterministic-first, auditable-first** philosophy as Direct-Use Exposure MCP.

### v0.1 scientific posture
- deterministic or bounded fate runs
- explicit compartment and time semantics
- explicit parameter defaults and source attribution
- explicit model-family tags
- no Monte Carlo requirement in first release
- no hidden calibration or opaque machine-learning layer

## 8. v0.1 scope

### Included
- typed environmental release scenario inputs
- region/context profiles and compartment definitions
- steady-state or bounded time-bucket multimedia concentration estimation
- concentration surfaces for air, water, soil, sediment, and optionally sludge/dust where scoped
- scenario comparison and assumption deltas
- export bundle for downstream concentration consumers
- schema publication, examples, contract manifest, operator guidance, validation resources

### Deferred
- fully dynamic spatial dispersion
- automatic coupling to proprietary model installations
- probabilistic population variability
- mechanistic food-chain transfer as a first-class requirement
- native ecotoxicity or risk quotient decision logic

## 9. Core user stories

1. As an exposure scientist, I want to define a release scenario and obtain concentration surfaces by medium so I can evaluate downstream exposure pathways.
2. As ToxClaw, I want to compare two fate scenarios and see which assumptions drive the concentration differences.
3. As Direct-Use Exposure MCP, I want a stable concentration-surface contract so I can consume environmental concentrations without knowing which fate engine produced them.
4. As a reviewer, I want to inspect defaults, source citations, and limitations for every concentration output.

## 10. Proposed tool catalog

### Scenario construction
- `fate_build_environmental_release_scenario`
- `fate_estimate_multimedia_concentrations`
- `fate_build_concentration_surface_bundle`
- `fate_compare_fate_scenarios`

### Evidence and utilities
- `fate_apply_physchem_evidence`
- `fate_assess_release_scenario_fit`
- `fate_reconcile_release_evidence`

### Export
- `fate_export_concentration_surface_bundle`
- `fate_export_exposure_consumption_package`

## 11. Proposed resource catalog

### Contracts and examples
- `contracts://manifest`
- `schemas://{schema_name}`
- `examples://{example_name}`
- `defaults://manifest`
- `fate-archetypes://manifest`

### Documentation
- `docs://operator-guide`
- `docs://provenance-policy`
- `docs://validation-framework`
- `docs://fate-model-boundary-guide`
- `docs://suite-integration-guide`
- `docs://release-readiness`

### Release and review
- `release://metadata-report`
- `release://readiness-report`
- `release://security-provenance-review-report`

## 12. Required contracts

### Core shared inputs
- `chemical_identity`
- `environmental_release_scenario`

### Fate-owned contracts
- `fate_region_profile`
- `fate_model_run_options`
- `fate_parameter_record`
- `fate_assumption_record`
- `fate_run_summary`
- `concentration_surface`
- `fate_scenario_comparison_record`

### Export contracts
- `concentration_surface_bundle`
- `exposure_consumption_package`

## 13. Contract semantics

### `environmental_release_scenario`
Must capture:
- source term or emission rate/mass
- release medium/media fractions
- release duration and timing pattern
- site or regional context
- optional treatment/removal assumptions
- evidence provenance

### `concentration_surface`
Must capture:
- medium
- compartment/context
- geographic scope
- start/end or steady-state semantics
- concentration value and unit
- scenario/model family
- provenance and assumptions
- uncertainty/limitation notes
- fit-for-purpose tag

## 14. Methods and runtime design

### Preferred architecture
- thin MCP surface
- model-agnostic runtime kernel
- plugin family by fate model class
- versioned defaults registry
- assumption/provenance kernel
- future-safe result metadata

### Candidate plugin families
- simple steady-state mass-balance kernel
- SimpleBox-aligned adapter
- EUSES-style adapter
- ChemFate-style adapter

### Design rule
The public abstraction is **not** “run SimpleBox”.  
The public abstraction is “build a release scenario and estimate concentration surfaces.”

## 15. Defaults and provenance

Every result must:
- identify model family and algorithm version,
- list all defaults used,
- distinguish user input vs curated default vs derived value,
- carry source IDs / citations / effective dates,
- emit warning-quality flags when heuristics are used.

## 16. Validation strategy

### Minimum v0.1 validation
- benchmark against hand-worked mass-balance fixtures
- benchmark against published/simple reference cases from supported model families
- schema validation for all outputs and examples
- negative-path tests for impossible media/unit combinations
- regression tests for default version drift
- comparison tests that show assumption deltas explicitly

### Validation resources
- benchmark manifest
- validation dossier
- model applicability notes
- known-gap report

## 17. Release gates

A release cannot ship unless:
1. all public schemas validate,
2. examples pass,
3. benchmark suites pass within declared tolerances,
4. defaults manifest and hashes are published,
5. model-family limitations are explicit,
6. exported concentration surfaces are consumable by downstream services,
7. release metadata and artifact integrity checks pass.

## 18. Key decisions for v0.1

### Decision 1 — Deterministic first
No required Monte Carlo in first release.

### Decision 2 — Concentration, not dose
Environmental Fate MCP stops at concentration surfaces.

### Decision 3 — Shared contracts over model-native APIs
Adapters may exist, but the public contracts must remain stable.

### Decision 4 — Region-specific evidence is additive
Regional packs enrich runs; they do not fork the core contract model.

## 19. Risks and open questions

### Risk: boundary bleed into exposure
Mitigation: reject requests that ask for body-weight normalized human dose.

### Risk: model-specific semantics leaking outward
Mitigation: publish harmonized output contracts and preserve model-family tags separately.

### Risk: premature probabilistic complexity
Mitigation: deterministic and bounded envelopes first; orchestration later.

### Open questions
- Which compartments are mandatory in v0.1?
- Is crop-transfer explicitly deferred or represented only as an extension hook?
- Which region profiles are curated at launch?
- Which fate engines are native vs adapter-only in v0.1?

## 20. Implementation phases

### Phase 1
- Publish contracts, schemas, examples, and ADRs
- Implement release scenario ingress and concentration-surface outputs
- Stand up defaults registry and provenance kernel

### Phase 2
- Add deterministic multimedia kernels
- Add comparison tooling
- Add validation fixtures and release artifacts

### Phase 3
- Add adapter boundaries for external model families
- Add richer region packs
- Add bounded scenario envelopes

## 21. Success criteria

Environmental Fate MCP is successful when:
- the suite can ask environmental-release questions without touching Direct-Use Exposure MCP internals,
- downstream services can consume concentration surfaces without bespoke mappings,
- every concentration result is auditable,
- model choice does not destabilize the public contract boundary.
