# Scientific Trust Pack v0.3.1

Version: `0.3.1`
Release status: `ready_for_screening_release`
This pack summarizes bounded-screening trust posture only. It is not regulator acceptance, submission approval, or source-engine scientific equivalence.

## Scope Boundary
- Environmental Fate MCP remains a concentration-only screening module inside the broader ToxMCP suite.
- `reference_mass_balance` is the default reviewer-grade baseline family.
- `advective_screening_mass_balance` remains an experimental challenge family and should be interpreted through the governed baseline-versus-challenge workflow.

## What Changed Scientifically In This Release
- Shipped-default delta records are published for `12` parameter(s).
- Numeric shipped-default changes recorded: `0`; materially output-affecting changes flagged: `0`.
- Mandatory reference-family claims meeting the reviewer-grade corroboration bar: `10/10`.
- The reference-family proof surface is treated as reviewer-grade; the advective family remains explicitly non-promotable in this release.
- Public wording remains bounded-screening only and does not imply regulator acceptance or source-engine equivalence.
- The erosion/sediment validation demo pack publishes `4` synthetic screening-QA cases and passed its classification checks.
- The external benchmark pack publishes `4` deterministic replay cases and passed its tolerance checks.
- The default sensitivity surface publishes `7` governed deterministic sensitivity profiles.

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
- No GIS-scale dispersion in v0.3.
- No rainfall-runoff generation, channel routing, deposition-field modelling, or native WEPP execution in v0.3.
- External benchmark packs are deterministic screening corroboration fixtures, not curated field validation datasets.
- Erosion/sediment validation demos remain synthetic screening-QA demonstrations, not curated field benchmark validation.
- No direct human dose calculation in Environmental Fate MCP.
- No dietary intake workflows in Environmental Fate MCP.
- No PBPK execution in Environmental Fate MCP.
- Branded desktop-model ingestion remains limited to governed adapter profiles; only normalized external payload JSON/CSV is a public MCP import contract in this release.

## Defaults Evidence
- Shipped core defaults: `12`.
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
- External benchmark cases: `4`.
- Resource: `defaults://scientific-external-benchmark-pack`.
- Report: `release://external-validation-benchmark-report`.
- Default sensitivity profiles passed: `True`.
- Default sensitivity profiles: `7`.
- Resource: `defaults://default-sensitivity-profiles`.
- Report: `release://default-sensitivity-report`.
- These artifacts improve deterministic screening corroboration and assumption transparency; they are not field validation, calibration, source-engine equivalence, or regulator acceptance.

## Claim Corroboration
- Governed scientific validation claims: `30`.
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
- No GIS-scale dispersion in v0.3.
- No rainfall-runoff generation, channel routing, deposition-field modelling, or native WEPP execution in v0.3.
- External benchmark packs are deterministic screening corroboration fixtures, not curated field validation datasets.
- Erosion/sediment validation demos remain synthetic screening-QA demonstrations, not curated field benchmark validation.
- No direct human dose calculation in Environmental Fate MCP.
- No dietary intake workflows in Environmental Fate MCP.
- No PBPK execution in Environmental Fate MCP.
- Branded desktop-model ingestion remains limited to governed adapter profiles; only normalized external payload JSON/CSV is a public MCP import contract in this release.
