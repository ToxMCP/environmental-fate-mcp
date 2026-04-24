# Environmental Fate MCP Operator Guide

Environmental Fate MCP accepts environmental release scenarios and returns concentration surfaces for downstream use. The module is deterministic-first and auditable-first.

## Supported workflows

- build environmental release scenarios
- attach evidence-backed parameter records
- estimate multimedia concentrations
- import normalized external JSON/CSV payloads through the public adapter contract
- assess model-family applicability for a scenario/run pair
- recommend whether to keep the default model-family baseline only or add a governed experimental challenge path
- preview governed assessor-facing model-family selection review status
- build assessor-facing model-family selection review packets
- build assessor-facing model-family selection review briefs
- preview governed assessor-facing model-family challenge review status
- build composed assessor-facing model-family challenge review packets
- build composed assessor-facing model-family challenge review briefs
- build composed model-family challenge scientific dossiers
- build composed model-family challenge scientific dossier briefs
- build run parameter manifests
- build deterministic run uncertainty summaries
- build deterministic model-family comparison packets and briefs for matched-scenario review
- preview governed assessor-facing model-family comparison review status
- build assessor-facing model-family comparison review packets
- build assessor-facing model-family comparison review briefs
- preview governed scientific review outcomes before packet assembly
- build assessor-facing scientific review packets
- build assessor-facing scientific review briefs
- build model-family scientific methods dossiers
- build model-family scientific methods dossier briefs
- build concentration bundles
- compare fate scenarios
- reconcile competing release evidence into a reviewable screening scenario
- export downstream concentration packages
- recommend governed regulatory handoff profiles for named downstream consumers
- preview regulatory handoff resolution before export
- export regulatory handoff crosswalk packages
- summarize regulatory handoff packages for downstream review
- build assessor-facing regulatory handoff review packets
- build deterministic assessor-facing regulatory handoff review briefs
- inspect governed handoff profiles, target matrices, consumer alias manifests, and adapter unit-conversion defaults
- inspect the public normalized external-payload adapter contract through `adapters://public-import-manifest`
- inspect governed model-family applicability profiles
- inspect governed model-family selection profiles
- inspect governed model-family challenge review profiles
- inspect governed model-family comparison profiles
- inspect governed scientific review profiles
- inspect governed scientific validation claims and benchmark claim-coverage manifests
- inspect governed scientific reference cases
- inspect model-family scientific methods through governed dossier workflows, including source-grounding lines, claim-specific highlighted grounding lines, reference-case grounding lines, and benchmark support-strength summaries
- inspect highlighted claim digests in the scientific methods dossier when you need a compact per-claim view of support strength, source grounding, reference-case concepts, and benchmark anchors
- use highlighted claim challenge status, challenge lines, and reviewer questions when you need an assessor-facing prompt for how to challenge a high-risk claim
- use highlighted claim external corroboration lines when you need to show which independent official sources are backing a published high-risk claim
- use highlighted claim external corroboration status and jurisdictions when you need to show whether a claim is backed by one official source or by broader multi-jurisdiction external grounding
- treat a highlighted claim with `single_official_source` or `none` corroboration status as challenge-worthy even when the benchmark matrix is otherwise strong
- use highlighted claim corroboration actions when you need the shortest reviewer-facing answer to “what would strengthen this claim next?”
- use the dossier and brief `recommended_actions` first when you need the shortest prioritized list of scientific follow-up work, because they now lift the strongest claim-specific corroboration actions out of the digest layer
- use `recommended_action_summaries` when you need to separate promotion-blocking follow-up from general scientific hardening work without reading the free-text action wording
- use dossier and brief `promotion_status`, `blocking_action_count`, and `strengthening_action_count` when you need the shortest machine-readable answer to whether the current claim set is blocked, merely being strengthened, or ready
- use `promotion_blocker_summaries` and `promotion_blocker_claim_ids` when you need the shortest machine-readable answer to what is actually blocking promotion and which governed claims those blockers attach to
- interpret `strengthening_only` on an experimental dossier as “the current release gate is met, but the transport-authority or reference-style support bar is still being strengthened,” and interpret `ready` as meaning that the governed experimental-evidence bar has been satisfied for the filtered claim set even though the family remains non-default
- inspect claim-specific reference-case concept lines in the scientific methods dossier when you need to explain what each governed case family is actually corroborating
- inspect claim-specific source-grounding lines in the scientific methods dossier when you need to explain which official sources are grounding a published claim
- inspect scientific review `equation_component_lines` when you need the shortest run-level explanation of whether degradation or advective clearance is dominating the resolved loss term
- inspect scientific review `mass_balance_component_lines` when you need the shortest run-level explanation of how emitted mass partitions into retained, degraded, and advected components
- inspect scientific review `transport_regime_lines` when you need the shortest run-level explanation of whether a residence-time-driven run is flow-through, intermediate-turnover, or storage-dominant
- inspect scientific review `transport_regime_lines` when you need turnover-boundary distance or finite-plateau context for a residence-time-driven run, not just the regime label itself
- inspect scientific review `post_release_recovery_lines` when you need the shortest run-level explanation of how much release-stop mass is still retained after emission ends and how much has been degraded versus flushed
- inspect scientific review `post_release_regime_lines` when you need the shortest run-level explanation of whether a post-release recovery window is still sub-flushing, boundary-sensitive, or already flushing-dominant
- inspect scientific review `post_release_regime_lines` when you need the retained-mass offset from the one-turnover anchor, not just the post-release regime label itself
- inspect scientific review `post_release_directionality_lines` when you need the shortest run-level explanation of whether retained release-stop mass is still above, exactly at, or already below the one-turnover anchor
- inspect scientific review `post_release_pace_lines` when you need the shortest run-level explanation of whether a post-release window is still before, at, or beyond the combined-loss half-recovery pace
- inspect scientific review `post_release_pace_directionality_lines` when you need the shortest run-level explanation of whether retained release-stop mass is still above, exactly at, or materially below the 50% combined-loss recovery anchor
- inspect scientific review `loss_dominance_lines` when you need the shortest run-level answer to whether an advective result is degradation-dominant, clearance-dominant, or mixed-loss
- inspect scientific review `loss_transition_lines` when you need the shortest run-level answer to whether an advective result is near a degradation/clearance flip or safely inside one loss regime
- inspect scientific methods dossier highlighted-claim regime-stability fields when you need the shortest claim-level answer to whether a governed advective claim is anchored in a stable regime or a transition zone
- inspect scientific methods dossier highlighted-claim transport-stability fields when you need the shortest claim-level answer to whether a governed advective claim is anchored in a stable transport regime or close to a turnover boundary
- inspect the advective scientific methods dossier `Post-release recovery support:` line when you need the shortest claim-set answer to whether post-release flushing and retained-mass decline are benchmark-covered beyond a single bucket anchor
- inspect the advective scientific methods dossier `Post-release regime support:` line when you need the shortest claim-set answer to whether post-release recovery interpretation is anchored below, on, and beyond the one-turnover flushing boundary
- inspect the advective scientific methods dossier `Post-release directionality support:` line when you need the shortest claim-set answer to whether retained release-stop mass is benchmark-anchored above, on, and below the one-turnover anchor under governed recovery windows
- inspect the advective scientific methods dossier `Post-release directionality support:` line when you need the shortest claim-set answer to whether retained release-stop mass continues to decline in the expected direction as recovery windows move farther beyond the one-turnover boundary
- inspect the advective scientific methods dossier `Post-release pace support:` line when you need the shortest claim-set answer to whether combined-loss post-release recovery pace is anchored before, at, and beyond the 50% retained-mass boundary under the governed loss constants
- inspect the advective scientific methods dossier `Post-release pace directionality support:` line when you need the shortest claim-set answer to whether retained release-stop mass is anchored above, on, and materially below the 50% combined-loss recovery anchor as the post-release window extends
- treat highlighted claim `regime_transition` recommended actions as the default next step for near-parity advective claims, because those claims are telling you to stress-test the loss-dominance boundary rather than only accept the anchor cases
- inspect the scientific methods dossier `External corroboration breadth:` summary line when you need a fast answer to how much of the filtered claim set is grounded by multi-official multi-jurisdiction support
- treat the governed transition-directionality claim as the quickest diagnostic for whether small half-life or residence-time shifts around the advective near-parity boundary behave in the expected direction
- treat a mandatory baseline reference-family claim without multi-case grounding as a scientific-release concern, not just a documentation gap
- treat a mandatory baseline reference-family claim that is still single-anchor or single-tier as a scientific-release concern as well
- treat single-case grounding on a high-priority experimental claim as a release concern even if benchmark coverage is otherwise green
- treat single-case grounding on a medium-priority experimental edge claim as a release concern as well, especially for clearance and duration challenges
- distinguish multi-anchor support from true multi-tier corroboration when challenging experimental advective claims
- compare the default `reference_mass_balance` family against the experimental `advective_screening_mass_balance` family when residence-time clearance matters
- challenge the experimental advective family with paired long-duration, long-residence, short-residence, and post-release bucket anchors before treating it as more than a governed challenge family
- use MCP prompts to generate profile-specific or consumer-specific handoff request, summary, and review guidance
- use MCP prompts to generate profile-specific model-family comparison request and summary guidance
- use MCP prompts to generate governed model-family selection guidance
- use MCP prompts to generate governed model-family selection review guidance
- use MCP prompts to generate governed model-family challenge review guidance
- use MCP prompts to generate composed model-family challenge scientific dossier guidance
- use MCP prompts to generate model-family-specific scientific review guidance
- use MCP prompts to generate model-family scientific methods dossier guidance
- use MCP prompts to generate governed model-family comparison review guidance
- use scientific review outcomes, review-status rule lines, governing-rule lines, and recommended-action lines to decide whether a run is acceptable, qualified, or should be escalated

## Not supported in v0.1

- direct human dose calculation
- dietary intake workflows
- PBPK execution
- final risk characterization
- full GIS dispersion
- unrestricted probabilistic simulation


## Probabilistic Simulation & Randomness

- The probabilistic orchestration (`fate_estimate_probabilistic_multimedia_concentrations`) uses Python's standard `random.Random` generator (Mersenne Twister) to sample parameter distributions.
- The Mersenne Twister is **not cryptographically secure**. It is used solely for reproducible screening-level uncertainty exploration.
- Seeds guarantee deterministic reproducibility for a given scenario, parameter distribution set, and runtime version. They do **not** provide cryptographic assurance.
- If your regulatory jurisdiction requires cryptographically secure random sampling, you must post-process or audit the sampling externally.
- Supported distributions are `lognormal`, `normal`, and `uniform`. Any sample that falls outside declared bounds is rejected and resampled (up to 100 attempts per parameter per iteration).

## Local Verification

- Run the test suite with `uv run --extra dev pytest` so pytest is resolved from the project environment instead of a global interpreter.
- Run `uv run environmental-fate-mcp-validate` after regenerating schemas, examples, defaults, or release artifacts.
- External payload imports are limited to shipped adapter fixtures plus directories declared in `FATE_MCP_IMPORT_ROOTS`.
- Build and smoke the installable package with `uv build` followed by a clean virtualenv install before publishing. The CI smoke checks startup counts, tool annotations, tool output schemas, packaged release resources, and packaged adapter fixtures.

## Runtime Resource Roots

The server resolves runtime artifacts in this order: `FATE_MCP_RESOURCE_ROOT`, a repository checkout root, then packaged resources under `src/fate_mcp/package_data` after wheel installation. Keep repo-root `defaults`, `docs`, `schemas`, `config`, and `evals` as the authoring source; artifact generation refreshes the packaged mirror.

Use `FATE_MCP_IMPORT_ROOTS` only for operator-managed external payload directories. It is a path-separator list, and symlinks are resolved before validation so links that escape configured roots are rejected.
