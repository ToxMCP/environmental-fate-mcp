# Scientific Hardening Tracker

This tracker converts integrated scientific review findings into concrete
remediation work with one disposition, one implementation task, one owner
lane, one phase, and one acceptance check per item. It is the single
authoritative place where review findings, their dispositions, and their
acceptance evidence live.

The same status discipline applies to every row:

- `implemented` — the remediation work has landed and the acceptance evidence
  is present in the repository.
- `confirmed_intentional` — the finding is real but the disposition is to
  preserve the current posture as a governed product decision; the row exists
  so the rationale and the governance anchor are machine-discoverable.
- `open` — the finding is real, the disposition is to remediate, and the
  remediation has not yet landed.

## Baseline lock

- The v0.5.0 release bundle is byte-stable across reruns; the deterministic
  release-bundle test (`tests/test_release_reports.py::test_write_release_bundle_is_deterministic_and_checksumed`)
  asserts byte equality and SHA-256 hash parity for every file in the bundle.
- The per-run `integrity_hash` on `ConcentrationSurfaceBundle` and
  `RegulatoryHandoffPackage` is byte-stable across reruns under the frozen
  UUID + timestamp context (`tests/test_integrity_hash_stability.py`).
- The pendimethalin public worked-case slice at
  `examples/pendimethalin_public_slice/` is byte-frozen on disk and its
  expected SHA-256 hashes are pinned in `outputs/output_summary.json`. The
  regression at `tests/test_pendimethalin_public_slice.py` asserts byte-
  equal hashes on rerun and numeric tolerance on every key surface value.
- All 5 physical-invariant tests in `tests/test_invariants.py` remain
  enforcing (non-negative concentration, mass-balance closure < 1 µg,
  advection ≤ reference, strict linearity in release mass, half-life
  monotonicity).

## Adjudication matrix

| ID | Review finding | Disposition | Implementation task | Owner | Phase | Acceptance evidence | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `R1` | 20 scientific validation claims (19 advective + 1 external-result adapter) had unset `evidenceFamily`, `worksheetStatus`, `officialSourceIds`, `pluginCodeReferences`, and `toleranceBasis`, so the evidence-quality matrix was visibly incomplete | `confirmed` | Tag all 20 with `public_method_description_plus_internal_oracle` evidence family, derive `officialSourceIds` from the cited reference cases, link plugin code paths, and supply claim-class-specific tolerance basis prose | `claims` | `1` | `defaults/v1/scientific_validation_claims.json` plus `scripts/label_unlabeled_claims.py` (idempotent regenerator) | `implemented` |
| `R2` | Per-bundle `integrity_hash` was only asserted for presence and 64-char length, not for byte equality across reruns, so non-determinism could regress silently | `confirmed` | Add byte-equality regression covering both the concentration surface bundle and the regulatory handoff package, plus a content-sensitivity test that confirms the hash is not a constant | `tests` | `1` | `tests/test_integrity_hash_stability.py` (3 tests) | `implemented` |
| `R3` | 4 of 8 external benchmark cases were tagged `internal_oracle` with fabricated inputs ("External benchmark substance", round-number physchem), giving tautological verification | `confirmed` | Replace 3 of 4 with `open_literature_reference` cases anchored on real-substance physchem from public databases (benzene/Mackay 1992 for Level I air; pendimethalin/FOOTPRINT PPDB for Level I soil; atrazine/FOOTPRINT PPDB for Level II water); keep one renamed as the closed-form self-consistency anchor | `defaults` | `1` | `defaults/v1/scientific_external_benchmark_pack.json` plus `scripts/upgrade_benchmark_pack.py` (idempotent regenerator) | `implemented` |
| `R4` | Temperature correction was tested only at a few discrete points (15 °C, 25 °C, -5 °C clamp), with no parametric sweep across the governed 0-40 °C range and no quantitative anchor against `Q10**((T-25)/10)` | `confirmed` | Add a parametric sweep with 37 cases anchoring the correction factor formula at each T in {0,5,10,15,20,25,30,35,40} °C, exact-boundary semantics, monotonicity, per-medium Q10, strict-mode rejection, and governance audit of the published Q10 values | `tests` | `1` | `tests/test_temperature_correction_sweep.py` | `implemented` |
| `R5` | No frozen public worked-case slice existed for downstream reviewer/regulator inspection comparable to Dietary's PESS glyphosate slice | `confirmed` | Promote the pendimethalin PDF demo into a frozen 21-JSON slice with public source anchors, limitations, and a 7-test regression that asserts byte-equal SHA-256 hashes plus numeric tolerance | `release-artifacts` | `1` | `examples/pendimethalin_public_slice/` plus `tests/test_pendimethalin_public_slice.py` plus `scripts/generate_pendimethalin_slice.py` | `implemented` |
| `R6` | 19 advective-family claims had `worksheetStatus=missing` despite hand-worked machine-readable fixtures already existing in `BENCHMARK_FIXTURES`, so the governed evidence pack was inaccessible to downstream reviewers | `confirmed` | Generalize the worksheet packager to support multiple model families and ship a governed `advective-worksheet-pack/` directory (19 claims × 2 artifacts = 38 files) alongside an `advective-worksheet-manifest.json` that explicitly carries the non-promotable governance flags | `release-artifacts` | `1` | `src/fate_mcp/release_artifacts.py::_build_advective_worksheet_manifest_report` plus `tests/test_advective_worksheet_pack.py` (6 tests) plus the shipped pack at `docs/releases/v0.5.0/advective-worksheet-pack/` | `implemented` |
| `R7` | The `external_adapter_canonical_equivalence_v1` claim remains the only `worksheetStatus=missing` entry; no model-family worksheet pack exists for the adapter family | `confirmed` | Add an adapter-family worksheet pack analogous to the advective one once at least one machine-readable adapter normalization fixture lands; until then track openly | `release-artifacts` | `2` | (pending) | `open` |
| `R8` | The advective family remains tagged `promotable: False`, `remainsExperimental: True`, `promotionStatus: non_promotable_experimental` in `_build_advective_promotion_bar_report` | `confirmed_intentional` | Preserve non-promotable status by governance until a third-party benchmark corpus (e.g., field measurements with calibrated parameters) is curated; the new advective worksheet pack adds reviewability without falsely upgrading the evidence family | `governance` | `n/a` | `src/fate_mcp/release_artifacts.py::_build_advective_promotion_bar_report` plus `docs/releases/v0.5.0/advective-promotion-bar-report.json` plus `docs/releases/v0.5.0/advective-worksheet-manifest.json` | `confirmed_intentional` |
| `R9` | One `internal_oracle` benchmark case remains (`reference_water_closed_form_self_consistency_oracle_v1`) | `confirmed_intentional` | Keep one internal-oracle case as a closed-form self-consistency drift detector; the release validator at `validation.py:2907-2908` requires both `internal_oracle` AND `official_worked_example` classifications to coexist in the manifest, and this is the most defensible role for an internal oracle | `governance` | `n/a` | `defaults/v1/scientific_external_benchmark_pack.json` plus `src/fate_mcp/validation.py:2907-2908` | `confirmed_intentional` |
| `R10` | Evals at `evals/environmental-fate-mcp-read-only.xml` are MCP-surface discovery QA pairs only (10 questions about metadata), with no agent-facing scientific evals (e.g., "given a scenario with log Kow > 5 and Henry's > 1 Pa·m³/mol, the agent should recommend the fugacity challenge family") | `confirmed` | Ship a parallel scientific-decisions eval pack with 15 scenario-based agent questions covering model-family selection, fail-closed error codes, governed policy values, reviewer-grade-vs-experimental posture, hand-off contracts, tamper-evidence fingerprints, suite-boundary discipline, and audit infrastructure | `evals` | `1` | `evals/environmental-fate-mcp-scientific-decisions.xml` plus `tests/test_evals.py::test_scientific_decisions_eval_pack_is_well_formed_and_covers_decision_lanes` plus `docs/agent_evaluations.md` | `implemented` |
| `R11` | No confidentiality/sanitisation lane comparable to Dietary's `confidentiality_bundles.md` + sanitisation pipeline; downstream partners with confidential parameters have no governed scrubbed-bundle export | `confirmed` | Ship a sanitisation helper (`fate_mcp.integrations.sanitise_concentration_surface_bundle_for_public_release`) plus the supporting `SanitisationRecord`, `SanitisationRedactionKind`, and `SanitisedConcentrationSurfaceBundle` models; the helper takes caller-declared confidentiality lists, emits a separate `sanitised_integrity_hash`, logs every redaction, and never mutates the source bundle. v1 is a public integration function (no MCP tool wrap yet); confidentiality is caller-declared (no automatic posture detection yet); scope covers `ConcentrationSurfaceBundle` only (regulatory-handoff sanitisation deferred) | `runtime` | `1` | `src/fate_mcp/models.py::SanitisedConcentrationSurfaceBundle`, `src/fate_mcp/integrations/core.py::sanitise_concentration_surface_bundle_for_public_release`, `tests/test_sanitisation.py` (8 tests), `docs/confidentiality_bundles.md` | `implemented` |
| `R12` | No multi-stage governed workflow (queue → review board → owner handoff → remediation → signoff) analogous to Dietary's owner pipeline; review surfaces stop at the `preview` stage | `confirmed` | Add a multi-stage chain after `fate_preview_scientific_review_outcome` so an assessment moves through queue, review-board, owner handoff, remediation, signoff with explicit acceptance evidence at each stage | `runtime` | `3` | (pending) | `open` |
| `R13` | The probabilistic lane supports lognormal / normal / uniform distributions only; correlated or copula-based multi-parameter distributions are not available, so realistic correlated physchem uncertainty cannot be expressed | `confirmed` | Add correlation support with a governed minimum-iteration count to keep convergence diagnostics meaningful; document the boundary where probabilistic results stop being defensible | `runtime` | `3` | (pending) | `open` |

## Remaining operating rules

- `ready_for_screening_release` remains a governed product-level screening
  readiness status, not regulator acceptance, source-engine equivalence, or
  formal scientific validation. Every release-readiness consumer surfaces
  this boundary explicitly.
- The advective family stays non-promotable until R8 is reopened with a
  third-party validation corpus; until then the family's worksheet pack
  improves reviewability but does not upgrade evidence posture.
- The single remaining `internal_oracle` benchmark case stays as a closed-
  form self-consistency drift detector and must not be promoted to
  `open_literature_reference` (its role is intentionally tautological).
- Adding new scientific validation claims requires the row metadata cluster
  (`evidenceFamily`, `worksheetStatus`, `lastReviewedDate`, `toleranceBasis`,
  `officialSourceIds`, `pluginCodeReferences`) to be populated at submission
  time; `scripts/label_unlabeled_claims.py` is the idempotent helper for
  bulk labelling but is not a substitute for per-claim review.
- The pendimethalin public worked-case slice at
  `examples/pendimethalin_public_slice/` is the canonical regulator-facing
  artifact; any change that alters its frozen SHA-256 hashes must be a
  deliberate slice revision regenerated via
  `scripts/generate_pendimethalin_slice.py`.
