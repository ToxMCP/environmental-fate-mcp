# Suite Integration Guide

Environmental Fate MCP is one bounded module in the broader ToxMCP suite. It exports concentration surfaces and concentration bundles for downstream services rather than trying to absorb dose, intake, PBPK, or final decision responsibilities.
It also publishes governed defaults and region-profile manifests for deterministic scenario construction.
It now also exposes a regulatory handoff crosswalk package and an adapter import manifest for suite-level orchestration.

## Intended consumers

- Direct-Use Exposure MCP
- future environmental intake workflows
- orchestration layers such as ToxClaw
- [Dietary Exposure MCP](https://github.com/ToxMCP/dietary-exposure-mcp) [`v0.1.0`](https://github.com/ToxMCP/dietary-exposure-mcp/releases/tag/v0.1.0) for screening-only food-mediated residue plus consumption workflows

## Handoff rule

Downstream services consume shared contracts, not model-specific blobs.
Regulatory handoff packages keep concentration semantics explicit while leaving route translation and dose calculation to the next module in the suite.
Consumer-specific handoff profiles are exposed through governed defaults so Direct-Use Exposure MCP and orchestration layers can request different downstream field mappings without changing Environmental Fate MCP core contracts.
Environmental Fate MCP also exposes a governed recommendation path so orchestrators can resolve profiles from consumer names like `ToxClaw` before export.
The alias map behind that recommendation path is inspectable through `defaults://regulatory-handoff-consumer-aliases`.
The allowed profile-to-target-module mapping is inspectable through `defaults://regulatory-handoff-target-matrix`.
The tool `fate_preview_regulatory_handoff_resolution` lets an orchestrator preflight whether a requested `consumer_name`, `handoff_profile_id`, or both will resolve cleanly before a handoff package is built.
The exported handoff package preserves how the profile was resolved through explicit `profile_resolution_*` metadata.
When a matched `scenario` is supplied during handoff export, the package also carries a governed run parameter manifest and a deterministic uncertainty summary so downstream reviewers can inspect provenance-heavy inputs without re-running Environmental Fate MCP.
If both a consumer and an explicit profile are supplied and they disagree, export now fails instead of silently preferring one selector.
If `target_modules` disagrees with the governed target module for the resolved profile, preview reports a mismatch and export fails.
The tool `fate_summarize_regulatory_handoff_package` turns a governed handoff package into a deterministic, consumer-specific summary for downstream assessment and orchestration workflows.
The tool `fate_build_regulatory_handoff_review_packet` bundles resolution preview, the governed handoff package, the deterministic summary, and any attached parameter-quality/applicability/uncertainty lines into one assessor-facing artifact for regulatory review workflows.
Review packets now also carry governed profile-specific checklist items, and `fate_build_regulatory_handoff_review_brief` renders those into a stable assessor-facing brief for regulatory review and orchestration records.
When a suite component already has normalized external JSON/CSV concentration payloads rather than native Environmental Fate MCP results, the public MCP import contract `fate_import_external_result_payload` can bring those payloads onto the canonical `external_result_adapter` path before review or handoff export.
For review workflows that do not need a downstream handoff at all, Environmental Fate MCP also exposes `fate_build_scientific_review_packet` and `fate_build_scientific_review_brief` to bundle fit assessment, parameter provenance, uncertainty drivers, benchmark coverage lines, and sampled concentration surfaces directly around a scenario/result pair.
For probabilistic scenario variants, Environmental Fate MCP also exposes `fate_estimate_probabilistic_multimedia_concentrations`, `fate_build_probabilistic_review_packet`, and `fate_build_probabilistic_review_brief` so percentile surfaces, sampled-driver context, failed-iteration reasons, and reproducibility metadata are reviewable without collapsing them back into deterministic artifacts.
That scientific review path is now governed by model-family-specific review profiles exposed through `defaults://scientific-review-profiles`, and prompt templates are available so assessors or orchestrators can request the right scientific review workflow without hard-coding review language.
The tool `fate_preview_scientific_review_outcome` lets an orchestrator or reviewer inspect the governed acceptable/qualified/escalate decision, the governed scientific-review status, triggered driver types, triggered check codes, and the rule lines behind both before a full scientific review packet is built.
Scientific review briefs now also expose a governed outcome and recommended next actions so the workflow can distinguish acceptable screening use from qualified use or escalation needs.
The default native family remains `reference_mass_balance`; the experimental `advective_screening_mass_balance` family is published separately so orchestrators can inspect a residence-time-aware screening path without silently changing the baseline suite handoff behavior.
The tool `fate_recommend_model_family_selection` lets an orchestrator decide whether to keep the reference family only or add the experimental advective family as a governed challenge path, using defaults-backed duration and explicit-parameter triggers rather than hard-coded orchestration heuristics.
That selection path now also exposes `fate_preview_model_family_selection_review`, `fate_build_model_family_selection_review_packet`, and `fate_build_model_family_selection_review_brief` so assessors can review whether the governed baseline-versus-challenge recommendation is itself ready for assessor-facing reuse before any comparison packet is built.
For assessors who want one composed artifact instead of separately handling governed selection review and governed comparison review, Environmental Fate MCP also exposes `fate_preview_model_family_challenge_review`, `fate_build_model_family_challenge_review_packet`, and `fate_build_model_family_challenge_review_brief`.
That composed path is now governed by challenge-review profiles exposed through `defaults://model-family-challenge-review-profiles`, so orchestrators and reviewers can inspect the composed review checklist and status policy separately from the underlying selection and comparison profiles.
For assessors who also want the scientific rationale for both families in one place, Environmental Fate MCP now exposes `fate_build_model_family_challenge_scientific_dossier` and `fate_build_model_family_challenge_scientific_dossier_brief`.
That dossier path reuses the governed challenge-review outcome and pairs it with the baseline and optional challenge-family scientific review briefs, so challenge-review status, benchmark context, and equation traces stay aligned without embedding hidden model-family logic in orchestration code.
For matched-scenario family challenges, Environmental Fate MCP now also exposes `fate_preview_model_family_comparison_review`, `fate_build_model_family_comparison_review_packet`, and `fate_build_model_family_comparison_review_brief` so assessors can review reference-versus-experimental family comparisons with governed checklist cues instead of only raw delta tables.
MCP prompts are available for both profile-specific and consumer-specific request generation so orchestrators do not need to hard-code profile ids.

## Checked-in cross-suite fixtures

- `tests/fixtures/cross_suite/woe_ngra/fate_exposure_handoff.v1.1.0.json`
  freezes the direct `Fate -> WoE` lane as concentration-only environmental
  context.
- That fixture preserves route hints, concentration units, typed upstream refs,
  and explicit `requires_dose_translation` semantics without pretending the
  handoff is already a human intake or dose estimate.
- The same checked-in fixture now also serves as the upstream source of truth
  for the sibling `Fate ambient_air -> Exposure -> WoE` and
  `Fate ambient_air -> Exposure -> IVIVE -> WoE` fixtures.
- Those downstream fixtures prove the suite can translate the `ambient_air`
  concentration surface into a bounded inhalation external dose while keeping
  the original Fate lineage visible.
- The same checked-in fixture also now serves as the upstream source of truth
  for the sibling `Fate surface_water -> Exposure -> WoE` and
  `Fate surface_water -> Exposure -> IVIVE -> WoE` fixtures.
- Those downstream fixtures prove the suite can translate the `surface_water`
  concentration surface into a bounded environmental oral screening dose while
  keeping the original Fate lineage visible and the `environmental_media`
  context explicit.
- The same checked-in fixture now also serves as the upstream source of truth
  for the sibling `Fate agricultural_soil -> Exposure -> WoE` and
  `Fate agricultural_soil -> Exposure -> IVIVE -> WoE` fixtures.
- Those downstream fixtures prove the suite can translate the `agricultural_soil`
  concentration surface into a bounded environmental oral screening dose while
  keeping the original Fate lineage visible, the `environmental_media` context
  explicit, and crop-uptake semantics unresolved.

## Environmental-media oral seam

Environmental-media oral intake from water or soil is intentionally not treated as a native Fate
dose workflow.
Environmental Fate MCP should stop at `concentration_surface` and other concentration-only handoff
packages.
The first bounded downstream oral seam now exists for `surface_water`, where Exposure MCP acts as
an explicit concentration-to-intake consumer with transparent drinking-water screening assumptions.
The second bounded downstream oral seam now exists for `agricultural_soil`, where Exposure MCP acts
as an explicit concentration-to-intake consumer with transparent soil-ingestion screening assumptions.
Crop-uptake translation remains future work, and any later human oral intake calculation still
belongs in a downstream consumer rather than Environmental Fate MCP itself.
The released Dietary Exposure MCP screening service becomes appropriate when food-mediated
consumption semantics apply.

## Herbal and supplement routing

- Environmental Fate MCP does not own TCM, herbal medicine, or supplement dose semantics.
- If a downstream workflow is medicinal or product-centric direct-use dosing, the
  `concentration_surface` handoff should route toward Direct-Use Exposure MCP or another
  concentration-to-dose consumer that preserves direct-use semantics.
- If a downstream workflow is food-mediated herbal intake or nutrition-style supplement
  consumption, the handoff should route toward Dietary Exposure MCP.
