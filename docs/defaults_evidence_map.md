# Defaults Evidence Map

This repository ships curated defaults under `defaults/v1/`.
Extension-ready regional packs can be added under `defaults/extensions/`.
Physicochemical evidence policies are published under `defaults/v1/physchem_parameter_policies.json`.
That policy file supports family-level inheritance plus parameter-level overrides so related screening rules stay versioned but not duplicated.
Adapter unit-conversion rules are published under `defaults/v1/adapter_unit_conversions.json`.
Regulatory handoff profiles are published under `defaults/v1/regulatory_handoff_profiles.json`.
The normalized handoff consumer alias manifest is exposed through `defaults://regulatory-handoff-consumer-aliases`.
The governed profile-to-target-module matrix is exposed through `defaults://regulatory-handoff-target-matrix`.

## Evidence tiers

- `tier_1_curated`: curated and reviewed defaults appropriate for screening
- `tier_2_reference`: external reference values adopted with contextual notes
- `tier_3_heuristic`: placeholder or surrogate values that must emit warning-quality flags

## Update rule

Any change to a curated defaults file requires:

- updated source references
- an updated effective date
- a regenerated `defaults/manifest.json`
- regression checks for defaults drift

Extension packs must also:

- declare a distinct `sourcePack`
- preserve the existing region-profile contract
- avoid introducing unsupported compartments without an explicit contract update

Physicochemical policy updates must also:

- keep family defaults internally coherent
- document any parameter-level overrides that diverge from the inherited family threshold or unit

Adapter conversion updates must also:

- preserve canonical Environmental Fate MCP concentration units
- document every accepted non-canonical import unit and its factor to canonical form
- document any governed dry-weight or wet-weight normalization assumptions for soil and sediment imports

Regulatory handoff profile updates must also:

- keep target-module field names explicit
- preserve a one-to-one governed mapping between each profile and its target module
- keep consumer hint aliases curated and unambiguous for suite consumers
- preserve zero normalized alias conflicts across governed profiles
- preserve selector consistency so consumer-name recommendations never contradict an explicit governed profile
- preserve target-module consistency so export-time `target_modules` never contradict the resolved governed profile
- keep orchestration request and response templates aligned with the declared handoff profile
- avoid introducing downstream dose semantics into Environmental Fate MCP outputs
