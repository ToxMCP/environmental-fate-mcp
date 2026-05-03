# Scientific Trust Pack v0.5.0

Version: `0.5.0`
Release status: `ready_for_screening_release`
This pack summarizes bounded-screening trust posture only. It is not regulator acceptance, submission approval, or source-engine scientific equivalence.

## Scope Boundary
- Environmental Fate MCP remains a concentration-only screening module inside the broader ToxMCP suite.
- `reference_mass_balance` is the default reviewer-grade baseline family.
- `advective_screening_mass_balance` remains an experimental challenge family and should be interpreted through the governed baseline-versus-challenge workflow.
- `fugacity_equilibrium_screening` is an experimental non-default Level I/II equilibrium partitioning challenge family; it is not Level III, routed, calibrated, field validated, or regulator accepted.

## What Changed Scientifically In This Release
- Shipped-default delta records are published for `15` parameter(s).
- Numeric shipped-default changes recorded: `0`; materially output-affecting changes flagged: `0`.
- Mandatory reference-family claims meeting the reviewer-grade corroboration bar: `10/10`.
- The reference-family proof surface is treated as reviewer-grade; the advective family remains explicitly non-promotable in this release.
- Public wording remains bounded-screening only and does not imply regulator acceptance or source-engine equivalence.
- The erosion/sediment validation demo pack publishes `4` synthetic screening-QA cases and passed its classification checks.
- The external benchmark pack publishes `8` deterministic replay cases and passed its tolerance checks.
- The default sensitivity surface publishes `11` governed deterministic sensitivity profiles.
- The fugacity screening validation report publishes `2` experimental Level I/II method profiles and passed mass/loss/boundary checks.
- The evidence-quality matrix publishes `34` claim rows and `5` model-family posture rows.

## When Not To Use This MCP
- validated external-engine mapping
- regulatory-facing scientific interpretation
- unrestricted branded desktop model ingestion
- explicit spatial dispersion and gradients
- intermedia transfer coefficient modeling
- probabilistic uncertainty propagation
- transformation-product tracking
- food-chain or dose translation workflows
- free-form ingestion of arbitrary proprietary exports
- scientific endorsement of source-engine methods beyond documented normalization behavior
- dose, exposure, or risk interpretation
- Level III non-equilibrium intermedia transfer
- advection, deposition, or routed transport between media
- hydrology generation, GIS/catchment routing, calibration, WEPP/SWAT/PRZM execution
- field-validation or regulatory-acceptance claims
- No GIS-scale dispersion in v0.5.
- No rainfall-runoff generation, channel routing, deposition-field modelling, SWAT/PRZM execution, or native WEPP execution in v0.5.
- Fugacity equilibrium screening is experimental Level I/II-style partitioning only; no Level III intermedia-transfer, advective export, calibration, field validation, or regulatory acceptance claim is added.
- External benchmark packs are deterministic screening corroboration fixtures, not curated field validation datasets.
- The evidence-quality matrix grades release-review evidence posture only; it does not add field validation, calibration evidence, regulator acceptance, or model promotion.
- Erosion/sediment validation demos remain synthetic screening-QA demonstrations, not curated field benchmark validation.
- No direct human dose calculation in Environmental Fate MCP.
- No dietary intake workflows in Environmental Fate MCP.
- No PBPK execution in Environmental Fate MCP.
- Branded desktop-model ingestion remains limited to governed adapter profiles; only normalized external payload JSON/CSV is a public MCP import contract in this release.

## Defaults Evidence
- Shipped core defaults: `15`.
- Tier-3 shipped defaults remaining: `0`.
- Parameters with recorded numeric shipped-default change: `0`.
- Parameters flagged as materially output-affecting after rebaseline: `0`.
- Rebaseline review status: `reviewed_no_numeric_default_change`.
- Defaults governance passed: `True`.

## Reference Reviewer-Grade Anchor
- Mandatory reference-family claim count: `10`.
- Mandatory reference-family claims passing the reviewer-grade bar: `10/10`.
- Worksheet-ready mandatory reference claims: `10/10`.
- Reference corroboration governance passed: `True`.
- Reviewer flow: `docs://reference-proof-brief` -> `release://reference-corroboration-report` -> `release://reference-worksheet-manifest` -> `docs://scientific-trust-pack`.
| Claim | Official Sources | Guidance Ready | Worksheet Ready | Last Reviewed | Pass |
| --- | ---: | --- | --- | --- | --- |
- No shipped-default numeric changes are recorded in this release; the rebaseline posture is explicitly reviewed and no-change.
| Reference air finite-duration first-order screening equation | 3 | yes | yes | 2026-04-21 | yes |
| Reference executable treatment reduction | 2 | yes | yes | 2026-04-21 | yes |
| Reference long-duration near-plateau anchor | 3 | yes | yes | 2026-04-21 | yes |
| Reference multi-medium partitioned screening output | 3 | yes | yes | 2026-04-21 | yes |
| Reference runtime parameter override application | 3 | yes | yes | 2026-04-21 | yes |
| Reference sediment finite-duration first-order screening equation | 3 | yes | yes | 2026-04-21 | yes |
| Reference short half-life attenuation anchor | 3 | yes | yes | 2026-04-21 | yes |
| Reference soil finite-duration first-order screening equation | 3 | yes | yes | 2026-04-21 | yes |
| Reference time-bucket elapsed-time semantics | 3 | yes | yes | 2026-04-21 | yes |
| Reference water finite-duration first-order screening equation | 3 | yes | yes | 2026-04-21 | yes |

## Experimental Advective Challenge Path
- Advective promotion-bar governance passed: `True`.
- Advective promotable this release: `False`.
- Non-promotable reasons: governed_policy_retains_experimental_status, reference_style_anchor_gap.

## Erosion/Sediment Validation Demo Pack
- Demo-pack validation passed: `True`.
- Synthetic demo cases: `4`.
- Resource: `defaults://erosion-sediment-validation-demo-pack`.
- Report: `release://erosion-sediment-validation-demo-report`.
- These cases demonstrate screening QA interpretation only; they are not field validation, calibration evidence, regulator acceptance, catchment validation, spatial routing evidence, or WEPP validation.

## External Benchmark And Sensitivity Surface
- External benchmark pack passed: `True`.
- External benchmark cases: `8`.
- Resource: `defaults://scientific-external-benchmark-pack`.
- Report: `release://external-validation-benchmark-report`.
- Default sensitivity profiles passed: `True`.
- Default sensitivity profiles: `11`.
- Resource: `defaults://default-sensitivity-profiles`.
- Report: `release://default-sensitivity-report`.
- These artifacts improve deterministic screening corroboration and assumption transparency; they are not field validation, calibration, source-engine equivalence, or regulator acceptance.

## Experimental Fugacity Challenge Path
- Fugacity validation passed: `True`.
- Fugacity method profiles: `2`.
- Resource: `defaults://fugacity-screening-method-profiles`.
- Report: `release://fugacity-screening-validation-report`.
- This path supports experimental Level I and Level II equilibrium screening only; it does not implement Level III intermedia-transfer, advection, spatial routing, calibration, field validation, source-engine equivalence, or regulator acceptance.

## Evidence-Quality Matrix
- Evidence-quality matrix passed: `True`.
- Claim rows: `34`.
- Model-family rows: `5`.
- Resource: `defaults://scientific-evidence-quality-rubric`.
- Report: `release://scientific-evidence-quality-matrix-report`.
- Tiers distinguish reviewer-grade screening, source-grounded screening, internal-oracle screening, synthetic-demo-only, and deferred/gap rows without adding regulatory, calibration, field-validation, or source-engine-equivalence claims.

## Claim Corroboration
- Governed scientific validation claims: `34`.
- Mandatory claims: `29`.
- External corroboration governance passed: `True`.

| Claim | Family | Status | Official Sources | Jurisdiction Breadth | Next Action |
| --- | --- | --- | ---: | --- | --- |
| Advective clearance-dominant loss-share transition | advective_screening_mass_balance | multi_official_multi_jurisdiction | 2 | multi_jurisdiction | Maintain challenge-path wording, preserve at least two independent evidence families with official guidance anchoring, and require non-author review before any promotion beyond experimental screening use. |
| Advective cumulative mass-balance closure | advective_screening_mass_balance | multi_official_multi_jurisdiction | 2 | multi_jurisdiction | Maintain challenge-path wording, preserve at least two independent evidence families with official guidance anchoring, and require non-author review before any promotion beyond experimental screening use. |
| Advective degradation-dominant loss-share transition | advective_screening_mass_balance | multi_official_multi_jurisdiction | 2 | multi_jurisdiction | Maintain challenge-path wording, preserve at least two independent evidence families with official guidance anchoring, and require non-author review before any promotion beyond experimental screening use. |
| Advective extreme-persistence clearance bound | advective_screening_mass_balance | multi_official_multi_jurisdiction | 2 | multi_jurisdiction | Maintain challenge-path wording, preserve at least two independent evidence families with official guidance anchoring, and require non-author review before any promotion beyond experimental screening use. |
| Advective long-duration combined-loss plateau anchor | advective_screening_mass_balance | multi_official_multi_jurisdiction | 2 | multi_jurisdiction | Maintain challenge-path wording, preserve at least two independent evidence families with official guidance anchoring, and require non-author review before any promotion beyond experimental screening use. |
| Advective long-residence-time accumulation anchor | advective_screening_mass_balance | multi_official_multi_jurisdiction | 2 | multi_jurisdiction | Maintain challenge-path wording, preserve at least two independent evidence families with official guidance anchoring, and require non-author review before any promotion beyond experimental screening use. |
| Advective mixed-loss transition margin | advective_screening_mass_balance | multi_official_multi_jurisdiction | 4 | multi_jurisdiction | Maintain challenge-path wording, preserve at least two independent evidence families with official guidance anchoring, and require non-author review before any promotion beyond experimental screening use. |
| Advective post-release flushing directionality | advective_screening_mass_balance | multi_official_multi_jurisdiction | 3 | multi_jurisdiction | Maintain challenge-path wording, preserve at least two independent evidence families with official guidance anchoring, and require non-author review before any promotion beyond experimental screening use. |
| Advective post-release flushing and recovery accounting | advective_screening_mass_balance | multi_official_multi_jurisdiction | 4 | multi_jurisdiction | Maintain challenge-path wording, preserve at least two independent evidence families with official guidance anchoring, and require non-author review before any promotion beyond experimental screening use. |
| Advective post-release flushing regime transition | advective_screening_mass_balance | multi_official_multi_jurisdiction | 3 | multi_jurisdiction | Maintain challenge-path wording, preserve at least two independent evidence families with official guidance anchoring, and require non-author review before any promotion beyond experimental screening use. |
| Advective post-release half-recovery directionality | advective_screening_mass_balance | multi_official_multi_jurisdiction | 3 | multi_jurisdiction | Maintain challenge-path wording, preserve at least two independent evidence families with official guidance anchoring, and require non-author review before any promotion beyond experimental screening use. |
| Advective post-release half-recovery pace | advective_screening_mass_balance | multi_official_multi_jurisdiction | 3 | multi_jurisdiction | Maintain challenge-path wording, preserve at least two independent evidence families with official guidance anchoring, and require non-author review before any promotion beyond experimental screening use. |
| Advective post-release late-recovery regime | advective_screening_mass_balance | multi_official_multi_jurisdiction | 3 | multi_jurisdiction | Maintain challenge-path wording, preserve at least two independent evidence families with official guidance anchoring, and require non-author review before any promotion beyond experimental screening use. |
| Advective residence-time override application | advective_screening_mass_balance | multi_official_multi_jurisdiction | 2 | multi_jurisdiction | Maintain challenge-path wording, preserve at least two independent evidence families with official guidance anchoring, and require non-author review before any promotion beyond experimental screening use. |
| Advective residence-time turnover regime interpretation | advective_screening_mass_balance | multi_official_multi_jurisdiction | 4 | multi_jurisdiction | Maintain challenge-path wording, preserve at least two independent evidence families with official guidance anchoring, and require non-author review before any promotion beyond experimental screening use. |
| Advective short-residence-time clearance anchor | advective_screening_mass_balance | multi_official_multi_jurisdiction | 2 | multi_jurisdiction | Maintain challenge-path wording, preserve at least two independent evidence families with official guidance anchoring, and require non-author review before any promotion beyond experimental screening use. |
| Advective time-bucket elapsed-time semantics | advective_screening_mass_balance | multi_official_multi_jurisdiction | 2 | multi_jurisdiction | Maintain challenge-path wording, preserve at least two independent evidence families with official guidance anchoring, and require non-author review before any promotion beyond experimental screening use. |
| Advective water finite-duration first-order screening equation | advective_screening_mass_balance | multi_official_multi_jurisdiction | 3 | multi_jurisdiction | Maintain challenge-path wording, preserve at least two independent evidence families with official guidance anchoring, and require non-author review before any promotion beyond experimental screening use. |
| External adapter canonical normalization parity | external_result_adapter | none | 0 | none | Keep the adapter claim limited to normalization parity and provenance-preserving import; do not restore source-engine equivalence language without bounded quantitative corroboration. |
| Reference air finite-duration first-order screening equation | reference_mass_balance | multi_official_multi_jurisdiction | 2 | multi_jurisdiction | Maintain dual-jurisdiction official guidance coverage and rerun the governed corroboration worksheet whenever defaults, benchmark anchors, or reference-case mappings change. |
| Reference executable treatment reduction | reference_mass_balance | multi_official_multi_jurisdiction | 2 | multi_jurisdiction | Maintain dual-jurisdiction official guidance coverage and rerun the governed corroboration worksheet whenever defaults, benchmark anchors, or reference-case mappings change. |
| Reference long-duration near-plateau anchor | reference_mass_balance | multi_official_multi_jurisdiction | 2 | multi_jurisdiction | Maintain dual-jurisdiction official guidance coverage and rerun the governed corroboration worksheet whenever defaults, benchmark anchors, or reference-case mappings change. |
| Reference multi-medium partitioned screening output | reference_mass_balance | multi_official_multi_jurisdiction | 2 | multi_jurisdiction | Maintain dual-jurisdiction official guidance coverage and rerun the governed corroboration worksheet whenever defaults, benchmark anchors, or reference-case mappings change. |
| Reference runtime parameter override application | reference_mass_balance | multi_official_multi_jurisdiction | 2 | multi_jurisdiction | Maintain dual-jurisdiction official guidance coverage and rerun the governed corroboration worksheet whenever defaults, benchmark anchors, or reference-case mappings change. |
| Reference sediment finite-duration first-order screening equation | reference_mass_balance | multi_official_multi_jurisdiction | 2 | multi_jurisdiction | Maintain dual-jurisdiction official guidance coverage and rerun the governed corroboration worksheet whenever defaults, benchmark anchors, or reference-case mappings change. |
| Reference short half-life attenuation anchor | reference_mass_balance | multi_official_multi_jurisdiction | 2 | multi_jurisdiction | Maintain dual-jurisdiction official guidance coverage and rerun the governed corroboration worksheet whenever defaults, benchmark anchors, or reference-case mappings change. |
| Reference soil finite-duration first-order screening equation | reference_mass_balance | multi_official_multi_jurisdiction | 2 | multi_jurisdiction | Maintain dual-jurisdiction official guidance coverage and rerun the governed corroboration worksheet whenever defaults, benchmark anchors, or reference-case mappings change. |
| Reference time-bucket elapsed-time semantics | reference_mass_balance | multi_official_multi_jurisdiction | 2 | multi_jurisdiction | Maintain dual-jurisdiction official guidance coverage and rerun the governed corroboration worksheet whenever defaults, benchmark anchors, or reference-case mappings change. |
| Reference water finite-duration first-order screening equation | reference_mass_balance | multi_official_multi_jurisdiction | 2 | multi_jurisdiction | Maintain dual-jurisdiction official guidance coverage and rerun the governed corroboration worksheet whenever defaults, benchmark anchors, or reference-case mappings change. |

## Reviewer Challenge Matrix
| Situation | Reviewer Posture |
| --- | --- |
| Transparent single-medium or bounded multi-medium screening need | Use `reference_mass_balance` as the decision-facing reviewer-grade anchor. |
| Residence-time clearance may materially change interpretation | Keep `reference_mass_balance` as baseline and use `advective_screening_mass_balance` only as a governed challenge path; do not promote it to baseline. |
| GIS dispersion, PBPK, dietary intake, branded desktop ingestion, or unrestricted probabilistic orchestration are needed | Do not use Environmental Fate MCP for the decision-facing output. |

## Reviewer Checklist
- Confirm the requested use remains concentration-only screening within the declared model-family applicability boundary.
- Check the default evidence posture and whether governed overrides changed the run away from the shipped default path.
- Check the corroboration table before treating any claim as broadly transferable across jurisdictions.
- Treat the advective family as an experimental challenge path unless the reviewer explicitly wants the governed comparison context.

## Known Gaps
- No GIS-scale dispersion in v0.5.
- No rainfall-runoff generation, channel routing, deposition-field modelling, SWAT/PRZM execution, or native WEPP execution in v0.5.
- Fugacity equilibrium screening is experimental Level I/II-style partitioning only; no Level III intermedia-transfer, advective export, calibration, field validation, or regulatory acceptance claim is added.
- External benchmark packs are deterministic screening corroboration fixtures, not curated field validation datasets.
- The evidence-quality matrix grades release-review evidence posture only; it does not add field validation, calibration evidence, regulator acceptance, or model promotion.
- Erosion/sediment validation demos remain synthetic screening-QA demonstrations, not curated field benchmark validation.
- No direct human dose calculation in Environmental Fate MCP.
- No dietary intake workflows in Environmental Fate MCP.
- No PBPK execution in Environmental Fate MCP.
- Branded desktop-model ingestion remains limited to governed adapter profiles; only normalized external payload JSON/CSV is a public MCP import contract in this release.
