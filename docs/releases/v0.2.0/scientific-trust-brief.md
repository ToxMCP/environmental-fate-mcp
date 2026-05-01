# Scientific Trust Brief v0.2.0

Version: `0.2.0`
Release status: `ready_for_screening_release`
Overall trust posture: bounded screening only, not regulator acceptance, submission approval, or source-engine equivalence.

## One-Shot Readout
- Screening recommendation: Release remains appropriate for bounded screening use when the declared exclusions are respected.
- Default evidence posture: shipped defaults governance passed `True` with `0` tier-3 shipped defaults remaining.
- Shipped-default numeric changes recorded this release: `0`, with `0` marked materially output-affecting.
- Defaults rebaseline review status: `reviewed_no_numeric_default_change`.
- Mandatory claim corroboration: `29` mandatory claims; `28` are `multi_official_multi_jurisdiction`.
- Reviewer-grade reference anchor bar: `10/10` mandatory reference claims pass.
- Worksheet pack readiness: `10/10` claim-linked worksheet artifacts are ready.
- Red-team blocker state: `0` open blockers, `0` unresolved findings, and `18` accepted public limitations.
- Erosion/sediment validation demo pack: `4` synthetic cases, passed `True`.

## Reviewer Signals
- `reference_mass_balance` remains the decision-facing baseline family.
- `advective_screening_mass_balance` remains experimental and should stay in the governed challenge lane.
- The advective family remains non-promotable in this release because: governed_policy_retains_experimental_status, reference_style_anchor_gap.
- Use the full trust pack if you need the mandatory-claim table, reviewer challenge matrix, or the full exclusion list.
- Use `release://erosion-sediment-validation-demo-report` only as a synthetic screening-QA orientation surface, not as field validation or calibration evidence.

## Mandatory Claims Needing Extra Reviewer Attention
- External adapter canonical normalization parity: none.

## Residual Caveats
- No GIS-scale dispersion in v0.2.
- No rainfall-runoff generation, channel routing, deposition-field modelling, or native WEPP execution in v0.2.
- Erosion/sediment validation demos are synthetic screening-QA demonstrations, not curated field benchmark validation.
- No direct human dose calculation in Environmental Fate MCP.
- No dietary intake workflows in Environmental Fate MCP.

## Next Review Step
- Start with this brief, then open `release://reference-corroboration-report`, `release://reference-worksheet-manifest`, and `docs://scientific-trust-pack` if you need the complete reviewer-grade trust surface.
