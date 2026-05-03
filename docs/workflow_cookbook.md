# Workflow Cookbook

This cookbook gives the shortest reliable path through the Environmental Fate MCP for the workflows most teams actually run.

## 1. Basic Deterministic Screening

Use this when you have a release scenario and need concentration surfaces.

1. Call `fate_build_environmental_release_scenario`.
2. Call `fate_estimate_multimedia_concentrations`.
3. Call `fate_build_concentration_surface_bundle` if the result will be handed downstream.

Use this path for:
- early multimedia screening
- concentration-only scenario comparison
- reviewer-visible deterministic runs

## 2. Advective Challenge Review

Use this when residence-time clearance might matter and you want the default family plus a governed challenge path.

1. Call `fate_build_environmental_release_scenario`.
2. Call `fate_recommend_model_family_selection`.
3. Call `fate_preview_model_family_selection_review`.
4. Call `fate_preview_model_family_challenge_review` if the challenge path is triggered.
5. Call `fate_build_model_family_challenge_review_packet` and `fate_build_model_family_challenge_review_brief`.

Use this path for:
- flowing-water screening
- long-duration releases with clearance questions
- assessor-facing baseline vs challenge review

## 3. Public External Payload Import

## 3. Fugacity Partitioning Challenge

Use this when equilibrium multimedia partitioning may materially change the reviewer story and you want a non-default experimental challenge against the reference baseline.

1. Build a scenario with explicit `molecular_weight_g_mol`, `henry_law_constant_pa_m3_mol`, and `organic_carbon_partition_coefficient_koc_l_kg` parameter records.
2. Run the baseline `reference_mass_balance` family with `fate_estimate_multimedia_concentrations`.
3. Run `fugacity_equilibrium_screening` with `fugacity_screening_level` set to `level_i_equilibrium` or `level_ii_equilibrium_persistence`.
4. Compare the baseline and fugacity challenge with the governed model-family comparison tools.
5. Build the review packet or trust brief, keeping the experimental boundary explicit.

Use this path for:
- equilibrium partitioning challenge review
- hydrophobic or particle-associated chemicals where multimedia distribution assumptions matter
- reviewer-visible comparison against the default reference family

Do not use this path for Level III intermedia transfer, hydrologic routing, calibration, field validation, source-engine equivalence, or regulator acceptance.

## 4. Public External Payload Import

Use this when an external tool has already produced normalized payload data and you want canonical Environmental Fate MCP outputs.

1. Inspect `adapters://public-import-manifest`.
2. Build a matched Environmental Fate scenario with `fate_build_environmental_release_scenario`.
3. Call `fate_import_external_result_payload`.
4. Continue with scientific review or downstream handoff tools, but keep adapter provenance, normalization scope, and source-engine limitations explicit rather than treating the result as a native physics run.

Public import profiles in the current public screening release:
- `normalized_external_payload_json`
- `normalized_external_payload_csv`

Keep in mind:
- public MCP import currently covers normalized JSON/CSV only
- branded legacy/EUSES/EPI paths remain governed adapter details, not the stable public API
- normalization parity across governed import paths is a contract-level check, not a claim of scientific equivalence to the source engine

## 5. Probabilistic Review

Use this when you want bounded percentile output rather than a single deterministic line.

1. Build the scenario.
2. Add parameter distributions to `parameter_records`.
3. Call `fate_estimate_probabilistic_multimedia_concentrations`.
4. Call `fate_build_probabilistic_review_packet`.
5. Call `fate_build_probabilistic_review_brief`.

Use this path for:
- reviewer-visible uncertainty exploration
- percentile handoff inputs
- sensitivity framing without leaving the governed MCP surface

## 6. Regulatory Handoff Export

Use this when another module needs concentration outputs in a governed downstream format.

1. Build or import the result.
2. Call `fate_preview_regulatory_handoff_resolution`.
3. Call `fate_export_regulatory_handoff_package`.
4. Call `fate_summarize_regulatory_handoff_package`.
5. Call `fate_build_regulatory_handoff_review_packet` if assessor-facing review is required.

Use this path for:
- Direct-Use Exposure MCP handoff
- orchestration-layer packaging
- concentration-only downstream review records
