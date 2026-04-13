# Fate MCP

Fate MCP is the ToxMCP module for deterministic environmental release to concentration workflows. It owns source-to-concentration semantics for environmental media and explicitly does not own direct human dose, dietary intake, PBPK execution, or final risk characterization.

## Current scope

- Typed environmental release scenarios
- Deterministic finite-duration concentration estimation
- Bounded time-bucket concentration estimation with physical elapsed-time semantics
- Non-default experimental advective screening family with governed residence-time defaults
- Governed scientific validation claims tied to benchmark fixtures and release gates
- Governed scientific reference-case registry for reviewer-visible mapping between published claims and regulator-recognizable case families
- Mandatory baseline reference-family claims now resolve to multiple governed regulator-recognizable reference-case families rather than only internal hand-worked anchors
- Mandatory baseline reference-family claims are now held to multi-anchor, multi-tier benchmark corroboration rather than single-anchor support
- High-priority experimental advective claims grounded to multiple governed regulator-recognizable reference-case families rather than a single internal case mapping
- Medium-priority experimental advective claims now held to the same multi-case grounding discipline for clearance and duration edge behavior
- Scientific methods dossiers now expose claim-specific reference-case concept lines so reviewers can see which regulator-facing concepts each governed case family is actually corroborating
- Scientific methods dossiers now expose claim-specific source-grounding lines for high-risk claims so reviewers can see which official sources are grounding each published claim instead of only aggregate source counts
- Scientific methods dossiers and briefs now carry highlighted claim digests with support strength, benchmark anchors, source grounding, and reference-case concepts for the highest-risk claims in scope
- Highlighted scientific claim digests now carry challenge status, challenge lines, and reviewer questions so assessors can actively challenge high-risk claims instead of only reading evidence snippets
- Highlighted scientific claim digests now carry claim-specific external corroboration lines so baseline and experimental high-risk claims show which independent official sources are actually backing the claim
- Highlighted scientific claim digests now carry explicit external corroboration status, official source counts, and governed corroboration jurisdictions so assessors can see external support breadth without inferring it from prose
- Highlighted scientific claim challenge status now reacts to thin external corroboration, so a strongly benchmarked claim with weak independent official grounding is still surfaced as challenge-worthy
- Highlighted scientific claim digests now carry claim-specific corroboration actions so the dossier tells the reviewer what would strengthen thin external grounding next
- Scientific methods dossiers now elevate the strongest claim-specific corroboration actions into top-level recommended actions and brief summary lines
- Scientific methods recommended actions now distinguish promotion-blocking follow-up from trust-strengthening follow-up in machine-readable form
- Scientific methods dossiers and briefs now expose a top-level `promotion_status` plus blocking-versus-strengthening action counts so reviewers do not need to infer overall posture from the action list
- Scientific methods dossiers and briefs now expose top-level `promotion_blocker_summaries` and `promotion_blocker_claim_ids` so blocked posture is tied to explicit blocker actions and claim ids
- Run-level scientific review packets and briefs now expose equation-component decomposition lines so reviewers can see whether degradation or advective clearance is dominating the resolved screening loss term
- Run-level scientific review packets and briefs now also expose mass-balance component lines so reviewers can see emitted, retained, degraded, and advected mass partitions with explicit closure error
- Run-level scientific review packets and briefs now also expose transport-regime lines so reviewers can see whether a run is flow-through, intermediate-turnover, or storage-dominant under the governed residence-time semantics
- Run-level scientific review transport-regime lines now also expose turnover-boundary distance and finite-plateau context, so bounded transport interpretation is reviewer-visible rather than hidden in raw trace terms
- Run-level scientific review packets and briefs now also expose post-release recovery lines so reviewers can see release-stop retained mass, removed mass, and flushing-window interpretation after active emission ends
- Run-level scientific review packets and briefs now also expose post-release regime lines so reviewers can see whether a recovery window remains sub-flushing, boundary-sensitive, or flushing-dominant relative to the one-turnover recovery boundary
- Run-level scientific review post-release regime lines now also compare retained release-stop mass against the one-turnover retained-mass anchor, so reviewers can see not just which side of the boundary a run sits on, but how far retained mass has progressed beyond it
- The experimental advective family now carries governed loss-dominance claims backed by trace-term benchmark anchors, so degradation-dominant and clearance-dominant regimes are claim-covered rather than only described in prose
- The experimental advective family now also carries a governed mixed-loss transition claim, so near-parity degradation-versus-clearance regimes are benchmarked and surfaced to reviewers instead of being treated as an ungoverned middle zone
- The experimental advective family now carries a governed transition-directionality claim plus flip-side sensitivity anchors, so reviewers can see that modest half-life or residence-time shifts move the dominant loss term in the expected direction
- The experimental advective family now carries a governed cumulative mass-balance closure claim, so native retained-versus-degraded-versus-advected accounting is benchmark-covered across multiple loss regimes instead of living only in trace detail
- The experimental advective family now carries a governed residence-time turnover-regime claim, so short-, mixed-, and long-residence transport interpretation is benchmark-covered instead of inferred from raw residence times alone
- The experimental advective residence-time turnover-regime claim now carries a reference-style bounded-transport anchor plus broader EPA/OECD case-family grounding, so turnover interpretation is no longer supported only by edge and sensitivity fixtures
- The experimental advective family now carries a governed post-release flushing/recovery claim, so post-release bucket decline is benchmark-covered in retained-versus-degraded-versus-advected terms rather than inferred only from falling concentrations
- Scientific methods dossiers now expose highlighted-claim loss-regime stability, so advective reviewers can see whether a claim is anchored in a stable regime or a near-parity transition zone
- Scientific methods dossiers now also expose highlighted-claim transport-regime stability, so reviewers can see whether an advective claim is anchored in a stable transport regime or close to a turnover boundary
- Scientific methods dossiers now also expose highlighted post-release recovery claims in the advective family, so release-stop flushing interpretation stays visible in the same reviewer-facing surface as transport and transition authority
- Scientific methods dossiers now also expose highlighted post-release regime-transition claims in the advective family, so boundary-sensitive recovery windows do not get flattened into the same posture as stable post-release flushing cases
- The governed post-release regime-transition claim now requires an extended flushing sensitivity anchor, so retained release-stop mass decline remains directionally supported beyond the one-turnover recovery threshold rather than only at it
- Near-parity highlighted advective claims now promote claim-specific boundary-sensitivity follow-up actions, so transition-zone claims trigger concrete reviewer work rather than passive description
- Scientific methods dossiers now expose claim-set external corroboration breadth, so reviewers can see how much of a filtered claim set is backed by multi-official multi-jurisdiction grounding
- The baseline reference-family scientific methods dossier can now resolve to `ready`, and the experimental advective dossier can now also resolve to `ready` once the governed transport-authority, transition-sensitivity, and corroboration bars are all met
- Model-family scientific methods dossiers and briefs that summarize governed claims, official source grounding, benchmark support strength, and applicability policy
- Versioned defaults and region-profile registries
- Governed model-family applicability profiles with inspectable defaults resources
- Governed model-family selection profiles with inspectable defaults resources
- Governed model-family challenge review profiles with inspectable defaults resources
- Governed model-family comparison profiles with inspectable defaults resources
- Physicochemical policy-family inheritance with inspectable defaults resources
- Governed adapter unit conversions, including soil/sediment dry-weight normalization
- Machine-readable run parameter manifests with runtime-consumed versus preserved-only parameter state
- Deterministic run uncertainty summaries that rank reviewer-facing drivers without probabilistic claims
- Benchmark manifests that publish scientific-claim coverage, validation tiers, and supporting reference fixtures
- Experimental advective-family claims strengthened with paired corroboration anchors for long-duration, long-residence, short-residence, and post-release bucket behavior
- Experimental advective-family medium/high-priority claims strengthened to multi-tier corroboration so release gating distinguishes independent support tiers from repeated same-tier anchors
- Deterministic model-family comparison packets and briefs for reference-versus-experimental screening challenges
- Governed model-family selection recommendations for baseline-versus-experimental family choice
- Governed assessor-facing model-family selection review previews, packets, and briefs
- Previewable, composed assessor-facing model-family challenge review artifacts that bundle governed selection review and optional comparison review through a governed challenge-review profile
- Composed model-family challenge scientific dossiers and briefs that pair governed challenge review with baseline and optional challenge-family scientific review summaries
- Governed assessor-facing model-family comparison review previews, packets, and briefs
- Scientific review packets and briefs that bundle fit assessment, parameter provenance, uncertainty drivers, and sampled surfaces
- Scientific methods dossiers and briefs that expose model-family claim statements, methods-basis lines, supporting references, and benchmark-backed edge anchors
- Governed scientific review profiles, checklist templates, and prompts per model family
- Governed scientific review outcomes and recommended-action templates per model family
- Previewable scientific review outcome and status resolution with explicit governing-rule lines before packet assembly
- Consumer-specific handoff profiles with governed consumer-alias recommendation
- Preflight handoff-resolution preview and explicit profile/consumer mismatch checks
- Governed target-module mapping with export-time target consistency enforcement
- Deterministic assessor-facing summaries for governed regulatory handoff packages
- Governed assessor-facing review packets that bundle resolution, package, and summary state
- Governed assessor review checklists and deterministic review briefs per handoff profile
- MCP prompt templates for orchestrators and consumer-aware handoff requests
- Assumption and provenance ledgers
- Applicability, parameter-quality, and uncertainty lines embedded in assessor-facing handoff artifacts
- Concentration-surface bundles for downstream consumers
- Regulatory handoff crosswalk packages for suite consumers
- Internal adapter-harness import of concrete external export shapes
- Machine-readable schemas, examples, and release artifacts

## Repository layout

- `src/fate_mcp/`: package code and MCP server surface
- `defaults/v1/`: curated defaults and region profiles
- `docs/contracts/schemas/`: generated JSON Schema files
- `schemas/examples/`: generated example payloads
- `docs/adr/`: architecture decisions
- `tests/`: validation, runtime, defaults, and integration tests

## Developer commands

```bash
uv sync --extra dev
uv run fate-mcp-generate-artifacts
uv run pytest
uv run fate-mcp
```

## Boundary summary

- Fate MCP owns environmental release scenarios, multimedia transfer, compartment concentration
  estimation, concentration surfaces, and downstream concentration bundles.
- Fate MCP does not own direct human dose calculation, dietary intake, PBPK execution, risk
  characterization, or arbitrary model-native file ingestion as the public contract.
- Environmental-media oral intake from water or soil is not solved inside Fate MCP. Fate MCP
  stops at `concentration_surface`; any future human intake calculation should happen in a
  downstream concentration-to-intake consumer, and only enters Dietary MCP when food-mediated
  consumption semantics apply.
- Traditional Chinese Medicine, herbal medicine, and supplement labels do not change this
  boundary. Fate MCP still stops at concentration outputs; medicinal direct-use regimens route
  downstream to Direct-Use Exposure MCP, while food-mediated herbal or supplement intake routes
  downstream to Dietary MCP.
- `reference_mass_balance` remains the default released native family. `advective_screening_mass_balance`
  is available as an experimental, non-default native family for governed residence-time screening.
