# Release Readiness

Environmental Fate MCP public release readiness is gated on reproducible contracts, examples, defaults manifests, benchmark fixtures, and downstream-consumer interoperability.
Released artifacts must remain deterministic across regeneration, and server startup must validate the shipped artifact set without mutating it.
`ready_for_screening_release` is an internal bounded-screening release gate. It is not a statement of regulator acceptance, submission approval, or scientific equivalence to external engines.
`reference_mass_balance` remains the reviewer-grade baseline family. `advective_screening_mass_balance` remains an experimental challenge family and must not drift into promoted baseline language without an explicit later decision.

## Generated artifact maintenance

The generated surface is intentionally large because installed wheels carry the runtime artifact mirror
needed for checkout-free deployments. To keep that surface reviewable:

- the repo-root artifacts remain the authoring source; `src/fate_mcp/package_data` is a generated mirror
- generator changes, source-artifact changes, schemas/examples, release reports, checksums, and package mirrors must be reviewed as one coherent release-surface change
- generated files should not be patched by hand to satisfy CI; update the source data or generator and regenerate
- every release-surface PR should run artifact generation, release bundle generation, the release validator, tests, wheel build, and installed-wheel smoke before merge
- drift checks must remain fail-closed so uncommitted regeneration output blocks the merge instead of becoming an implicit local artifact
- the governed erosion/sediment validation demo pack must remain synthetic, classification-stable, and visible through both `defaults://erosion-sediment-validation-demo-pack` and `release://erosion-sediment-validation-demo-report`
- the governed external benchmark pack must remain deterministic, tolerance-stable, and visible through both `defaults://scientific-external-benchmark-pack` and `release://external-validation-benchmark-report`
- governed default sensitivity profiles must remain deterministic, boundary-limited, and visible through both `defaults://default-sensitivity-profiles` and `release://default-sensitivity-report`

## Required checks

- generated schemas and examples are current
- generated example payloads are deterministic across reruns
- governed erosion/sediment validation demo cases parse, execute through the validation tools, and match their declared expected classifications
- governed external benchmark replay cases parse, execute through public tools, and match declared expected values within tolerance
- governed default sensitivity profiles parse, execute through `fate_build_default_sensitivity_report`, and keep sensitivity interpretation separate from calibration or field validation
- optional probabilistic sample manifest schemas preserve seed, sampled-parameter summaries, iteration health, stable hashes, and capped records when requested
- server startup validates shipped artifacts without regenerating them
- defaults manifest hashes match shipped files
- the shipped default path contains zero `tier_3_internal_screening_assumption` values
- every shipped default has citation-backed source references, derivation metadata, effective date, and manifest traceability
- benchmark fixtures pass within declared tolerances
- benchmark fixtures carry explicit scientific basis, reference type, expected behavior, and tolerance rationale
- every published scientific validation claim is tied to at least one declared benchmark fixture
- every mandatory scientific validation claim satisfies its required validation tier and reference-type coverage
- every published scientific validation claim carries source references, methods-basis lines, and reference-case lines
- every published scientific validation claim carries explicit corroboration status, official source count, jurisdiction breadth, independent evidence families, and a next corroboration action
- mandatory baseline reference-family scientific claims resolve to governed scientific reference-case ids and do not remain single-reference-case only
- mandatory baseline reference-family scientific claims carry at least two independent evidence families with at least one official guidance, official modeling-guidance, or official test-guideline family
- mandatory baseline reference-family scientific claims do not remain single-anchor only or multi-anchor-but-single-tier only
- high- and medium-priority experimental scientific claims resolve to governed scientific reference-case ids
- high- and medium-priority experimental scientific claims carry at least two independent evidence families with official guidance anchoring or remain visibly strengthening-only
- high-priority experimental scientific claims do not remain single-reference-case only
- medium-priority experimental scientific claims do not remain single-reference-case only
- high- and medium-priority experimental scientific claims do not remain single-anchor only
- high- and medium-priority experimental scientific claims do not remain multi-anchor-but-single-tier only when independent sensitivity-style corroboration is part of the governed release bar
- every supported model family has a governed applicability profile
- governed model-family selection profiles exist for published baseline-versus-experimental selection workflows
- governed model-family comparison profiles exist for every published model-family comparison workflow
- every experimental model family published in metadata has a governed applicability profile and scientific review profile
- run parameter manifests remain consistent with scenario parameter records, runtime assumptions, and provenance
- deterministic uncertainty summaries remain machine-readable and limitation-bound
- model-family selection recommendations remain internally consistent with the governed selection profile, fit assessments, and challenge-trigger lines
- model-family selection review previews, packets, and briefs remain internally consistent with the governed selection profile, recommendation artifact, and assessor-facing checklist guidance
- scientific methods dossiers and briefs preserve top-level `promotion_status` plus blocking-versus-strengthening action counts
- blocked scientific methods dossiers and briefs preserve explicit promotion-blocker summaries and blocker-claim ids
- experimental scientific methods dossiers may resolve to `ready` once the governed high- and medium-priority evidence bars are met and the advective transport-authority/transition reference-style bar is satisfied, while weaker experimental evidence still resolves to `strengthening_only` or `blocked` as appropriate
- composed model-family challenge review previews, packets, and briefs remain internally consistent with the governed challenge-review profile plus the embedded governed selection review and optional governed comparison review artifacts
- composed model-family challenge scientific dossiers and briefs remain internally consistent with the governed challenge-review path plus the embedded baseline and optional challenge-family scientific review summaries
- scientific methods dossier highlighted-claim digests preserve external corroboration status, official source counts, and jurisdiction breadth into the brief summary surface
- scientific methods dossier highlighted-claim challenge status remains consistent with external corroboration breadth so thinly corroborated claims do not appear passively well supported
- scientific methods dossier highlighted-claim digests preserve corroboration actions into the brief summary surface so thin external grounding produces an explicit next action
- scientific methods dossier and brief recommended-actions surfaces preserve the leading claim-specific corroboration follow-ups when they are scientifically material
- scientific methods dossier and brief recommended-action summaries preserve promotion impact so blocking follow-up is distinguishable from trust-strengthening follow-up
- run-level scientific review packets and briefs preserve equation-component decomposition lines alongside equation traces so degradation-versus-clearance dominance is reviewable
- run-level scientific review packets and briefs preserve mass-balance component lines alongside equation traces so emitted, retained, degraded, and advected partitions are reviewable with explicit closure error
- run-level scientific review packets and briefs preserve transport-regime lines alongside residence-time trace terms so flow-through, intermediate-turnover, and storage-dominant interpretations are reviewable
- run-level scientific review packets and briefs preserve transport-regime lines with turnover-boundary and finite-plateau context, so bounded transport interpretation is reviewable rather than only described in trace detail
- run-level scientific review packets and briefs preserve post-release recovery lines with release-stop retained, degraded, and advected mass fractions plus flushing-window interpretation, so bucketed recovery semantics stay reviewer-visible
- run-level scientific review packets and briefs preserve post-release regime lines with one-turnover boundary interpretation, so reviewers can distinguish sub-flushing, boundary-sensitive, and flushing-dominant recovery windows directly from the review surface
- run-level scientific review post-release regime lines also preserve retained-mass offset from the one-turnover anchor, so reviewers can see directional progress beyond the recovery boundary rather than only a regime label
- run-level scientific review packets and briefs preserve post-release directionality lines, so reviewer-facing retained-mass progression above, at, and below the one-turnover anchor is release-gated rather than left in raw trace terms
- run-level scientific review packets and briefs preserve post-release pace lines, so reviewer-facing combined-loss half-recovery interpretation is release-gated rather than inferred from the one-turnover flushing boundary alone
- run-level scientific review packets and briefs preserve post-release pace directionality lines, so reviewer-facing retained-mass progression above, at, and materially below the 50% combined-loss recovery anchor is release-gated rather than left in raw trace terms
- mandatory advective loss-dominance claims are benchmark-covered with both edge-condition and sensitivity anchors, so dominance transitions are governed rather than inferred from a single trace example
- mandatory advective mixed-loss transition claims are benchmark-covered with both edge-condition and sensitivity anchors, so near-parity degradation/clearance regimes are release-gated rather than left to reviewer interpretation alone
- advective transition-directionality claims are benchmark-covered with flip-side sensitivity anchors, so small half-life or residence-time shifts across the near-parity boundary are explicitly challenged rather than implied
- mandatory advective cumulative mass-balance closure claims are benchmark-covered across degradation-dominant, clearance-dominant, and mixed-loss anchors, so native trace accounting is release-gated rather than treated as a descriptive add-on
- mandatory advective residence-time turnover-regime claims are benchmark-covered across short-, mixed-, and long-residence anchors, so transport interpretation is release-gated rather than left to reviewer inference
- mandatory advective post-release directionality claims are benchmark-covered across sub-boundary, boundary, and beyond-boundary anchors, so retained-mass progression across the one-turnover recovery boundary is release-gated rather than inferred from a single recovery example
- mandatory advective residence-time turnover-regime claims now also require a reference-style bounded-transport anchor, so turnover interpretation is not released on edge and sensitivity cases alone
- mandatory advective post-release flushing/recovery claims are benchmark-covered with edge-condition, reference-style, and sensitivity anchors, so post-release retained-mass decline is release-gated rather than inferred from concentration decay alone
- mandatory advective post-release half-recovery directionality claims are benchmark-covered with same-chemistry pre-half, boundary, beyond-half, and extended-beyond-half anchors, so retained-mass progression relative to the 50% recovery anchor is release-gated rather than inferred from a single pace crossing
- mandatory advective post-release regime-transition claims are benchmark-covered across sub-boundary, boundary-sensitive, and flushing-dominant anchors, so recovery-window interpretation is release-gated rather than inferred from raw turnover counts alone
- mandatory advective post-release half-recovery pace claims are benchmark-covered across pre-half, half-boundary, and beyond-half anchors, so combined-loss recovery pace is release-gated rather than inferred from one-turnover transport semantics alone
- mandatory advective post-release regime-transition claims now also require an extended beyond-boundary sensitivity anchor, so retained release-stop mass decline remains directionally supported as recovery windows move farther past the one-turnover threshold
- scientific methods dossier highlighted claims now preserve loss-regime stability context, so near-parity transition claims cannot hide inside the same summary posture as stable one-sided loss anchors
- scientific methods dossier highlighted claims now preserve transport-regime stability context, so turnover-boundary claims cannot hide inside the same summary posture as stable storage- or flow-through anchors
- scientific methods dossier highlighted claims now preserve post-release recovery interpretation when the governed advective recovery claim is highlighted, so release-stop flushing context stays reviewer-visible
- near-parity highlighted advective claims now emit regime-transition recommended actions, so transition-zone follow-up is governed rather than left to reviewer memory
- scientific methods dossiers now preserve claim-set external corroboration breadth, so thinly diversified claim sets are visible at the summary level rather than only claim by claim
- scientific review packets and briefs remain internally consistent with fit assessment, parameter manifest, and uncertainty summary artifacts
- probabilistic review packets and briefs remain internally consistent with percentile surface summaries, failed-iteration taxonomy, sampled-driver lines, and scientific-unsuitability context
- scientific methods dossiers and briefs remain internally consistent with governed claims, aggregate and claim-specific source grounding, highlighted claim digests, claim-specific external corroboration, challenge statuses/questions, support-strength summaries, benchmark coverage, and applicability policy
- reviewer-facing trust surfaces remain internally consistent across the scientific trust pack, scientific methods dossier/brief, challenge review brief, and regulatory quick start
- release bundles publish `defaults-rebaseline-report.json`, `external-corroboration-report.json`, `red-team-review-report.json`, and `scientific-trust-pack.md`
- red-team review reports contain zero unresolved blocker-severity findings
- accepted release limitations appear in public reviewer artifacts, not only internal notes
- synthetic validation demos remain explicitly excluded from field validation, calibration evidence, catchment validation, spatial routing evidence, WEPP validation, and regulator acceptance claims
- model-family comparison packets and briefs remain internally consistent with the shared scenario, fit assessments, surface deltas, and equation traces
- model-family comparison review previews, packets, and briefs remain internally consistent with the governed comparison profile, comparison packet, and assessor-facing checklist guidance
- scientific review profiles remain declared for every supported model family, with valid checklist templates and summary templates
- scientific review outcome templates and driver-action templates remain declared for every supported scientific review profile
- scientific review status and outcome previews remain consistent with packet-level status, outcome, governing-rule, and recommended-action lines
- downstream concentration bundles parse without ad hoc mapping
- downstream concentration bundles and regulatory handoff packages carry integrity hashes and concentration-only disclaimers
- regulatory handoff consumer aliases remain conflict-free after normalization
- regulatory handoff preview and export selectors remain consistent
- regulatory handoff target modules remain consistent with governed profile mappings
- regulatory handoff summary artifacts remain consistent with the exported package and governed profile
- regulatory handoff review packets remain internally consistent with preview, package, and summary artifacts
- regulatory handoff review briefs remain consistent with governed review packets and profile-level checklist guidance
- assessor-facing regulatory handoff artifacts preserve applicability, parameter-quality, and uncertainty summary lines when a matched scenario is supplied
- adapter normalization fixtures resolve to the same canonical contract outputs across governed import paths
- known limitations are published explicitly
- failure modes remain machine-readable

## Blocker classes

The release bundle now treats these as named blocker classes:

- `unresolved_default_derivation_gap`
- `uncovered_corroboration_requirement`
- `unresolved_shipped_default_rebaseline_gap`
- `missing_reference_family_official_corroboration`
- `worksheet_or_equation_mismatch`
- `trust_surface_inconsistency`
- `advective_promotion_language_drift`
- `trust_pack_artifact_mismatch`
- `trust_brief_artifact_mismatch`
- `accidental_advective_promotion_language_drift`
- `erosion_sediment_validation_demo_pack_mismatch`
- `unaddressed_red_team_finding`
