# ToxMCP Platform Boundary — Direct-Use Exposure MCP, Fate MCP, Dietary MCP

**Date:** 2026-04-08  
**Source basis:** Direct-Use Exposure MCP repository snapshot reviewed on 2026-04-08 (commit `506df226ec7f0a62af70dbb46ba31f74535aace5`).

## Executive recommendation

Create **Fate MCP** and **Dietary MCP** as **sibling MCPs** to Direct-Use Exposure MCP, not as submodules inside it.

The clean split is:

- **Direct-Use Exposure MCP** = human **direct-use / near-field concentration-to-dose**
- **Fate MCP** = environmental **source-to-concentration**
- **Dietary MCP** = **food-residue / food-consumption to oral intake**
- **PBPK MCP** = **external-dose-to-internal-dose**
- **ToxClaw** = orchestration, evidence handling, refinement choice, reporting

## Critical boundary rule

**Do not split by route alone. Split by pathway semantics and input grammar.**

That means:

- **Direct-use oral** stays in **Direct-Use Exposure MCP**
  - Example: mouthing, incidental oral intake from product-use context, direct-use product ingestion assumptions.
- **Diet-mediated oral** goes to **Dietary MCP**
  - Example: commodity residues, food baskets, diet surveys, acute/chronic dietary intake.
- **Environmental release and multimedia fate** go to **Fate MCP**
  - Example: release to air/water/soil/sediment, partitioning, persistence, transport, concentration surfaces.
- **Internal dose and TK translation** remain in **PBPK MCP**

## Ownership matrix

| Service | Owns | Explicitly does not own | Primary outputs |
|---|---|---|---|
| Direct-Use Exposure MCP | Consumer direct-use scenarios, dermal/oral direct-use, indoor/near-field inhalation, aggregate summaries, evidence reconciliation, worker routing while task/use abstractions hold | Multimedia fate, food-residue intake workflows, PBPK execution, WoE, final risk conclusions | `exposure_scenario`, `aggregate_exposure_summary`, `route_dose_estimate`, `pbpk_external_import_bundle` |
| Fate MCP | Environmental release scenarios, multimedia fate/transfer, compartment concentrations, concentration surfaces for downstream use | Direct human dose calculation, dietary intake, PBPK, final risk conclusions | `environmental_release_scenario`, `concentration_surface`, `fate_run_summary`, `fate_assumption_record` |
| Dietary MCP | Commodity residue inputs, consumption mappings, population-specific oral intake, contribution summaries, dietary oral PBPK handoff | Direct-use oral scenarios, generic environmental oral ingestion, PBPK execution, final risk conclusions | `dietary_intake_scenario`, `dietary_intake_summary`, `route_dose_estimate`, `pbpk_external_import_bundle` |
| PBPK MCP | TK simulation, internal dose, tissue concentration time courses | Exposure scenario generation, multimedia fate, food-consumption modeling, final risk conclusions | `pbpk_run`, `internal_dose_summary` |
| ToxClaw | Orchestration, line of evidence, refinement selection, reporting | Exposure math, multimedia fate math, PBPK simulation math | Evidence bundles, refinement workflows, reports |

## Routing rules

| Question pattern | Owning MCP |
|---|---|
| “What dose results from consumer product use or near-field inhalation?” | Direct-Use Exposure MCP |
| “What environmental concentrations result from releases to media?” | Fate MCP |
| “What oral intake results from residues in food for a population?” | Dietary MCP |
| “What internal concentration follows a dose regimen?” | PBPK MCP |
| “How should multiple evidence lines be combined into a decision workflow?” | ToxClaw |

## Edge-case policy

### Oral exposure
- **Direct-use oral** = Direct-Use Exposure MCP
- **Medicinal TCM regimens and product-centric supplement dosing** = Direct-Use Exposure MCP
- **Dietary oral** = Dietary MCP
- **Food-mediated herbal intake and nutrition-style supplement intake** = Dietary MCP
- **Environmental oral from water or soil** = not Dietary by default; treat as a future
  concentration-to-intake workflow that starts from Fate MCP `concentration_surface`
  outputs rather than forcing oral intake into Fate MCP itself

### Inhalation
- **Indoor / near-field / room-use inhalation** = Direct-Use Exposure MCP
- **Regional outdoor air concentration due to emissions and transport** = Fate MCP
- **Human dose from environmental air concentration** = downstream concentration-to-dose layer, not Fate core

### Crop / food residue generation
- **Measured or curated commodity residue inputs** = Dietary MCP input
- **Mechanistic environmental release-to-food-chain transfer** = future extension; do not force into Dietary MCP v0.1 unless a clear contract is defined

## Shared cross-MCP contracts

### Preserve from current architecture
- `chemical_identity`
- `product_use_evidence_record`
- `exposure_scenario_definition`
- `environmental_release_scenario`
- `concentration_surface`
- `route_dose_estimate`
- `pbpk_external_import_bundle`

### Add for the sibling MCPs
- `fate_region_profile`
- `fate_model_run_options`
- `fate_assumption_record`
- `dietary_commodity_residue_record`
- `dietary_consumption_profile`
- `dietary_intake_scenario_definition`
- `dietary_contribution_record`

## Cross-MCP handoff rules

1. **Adapters translate into shared contracts, not tool-native schemas.**
2. **Defaults remain versioned, attributable, and easy to override.**
3. **Heuristic factors emit warning-quality flags and limitation notes.**
4. **PBPK receives stable dose semantics, never product narratives or model-native blobs.**
5. **Probabilistic modes later reuse deterministic kernels instead of replacing them.**

## Recommended build order

1. Keep strengthening Direct-Use Exposure MCP as the direct-use / near-field backbone.
2. Add **Fate MCP** next because it creates reusable concentration surfaces for downstream workflows.
3. Add **Dietary MCP** after Fate MCP, with a sharp focus on food-mediated oral intake rather than “all oral”.
4. Add cross-MCP probabilistic orchestration only after the shared contracts are stable.
