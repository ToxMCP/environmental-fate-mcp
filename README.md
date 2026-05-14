# Environmental Fate MCP

[![CI](https://github.com/ToxMCP/environmental-fate-mcp/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/ToxMCP/environmental-fate-mcp/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://www.apache.org/licenses/LICENSE-2.0)
[![Release](https://img.shields.io/github/v/release/ToxMCP/environmental-fate-mcp?sort=semver)](https://github.com/ToxMCP/environmental-fate-mcp/releases)
[![Status](https://img.shields.io/badge/Status-Ready%20for%20Screening-2E8B57)](./docs/release_readiness.md)
[![Python](https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![MCP](https://img.shields.io/badge/MCP-JSON--RPC-informational)](https://modelcontextprotocol.io/)

> Part of **ToxMCP** Suite -> https://github.com/ToxMCP/toxmcp

**Governed MCP server for auditable environmental release-to-concentration screening, scientific review, and downstream regulatory handoff packaging.**
Environmental Fate MCP is one bounded module inside the broader ToxMCP suite. It turns environmental release assumptions into deterministic and bounded probabilistic concentration surfaces, scientific review packets, scientific methods dossiers, and downstream handoff artifacts without taking over direct human dose, dietary intake, PBPK execution, final risk characterization, or model-native external engine execution as the public contract.

## Architecture

```mermaid
flowchart LR
    subgraph Clients["Clients and Orchestrators"]
        Codex["Codex CLI / Desktop"]
        Scripts["Scripts / notebooks"]
        Other["Other MCP-aware agents"]
    end

    subgraph MCP["FastMCP Service"]
        Server["Tool and resource surface"]
        Contracts["Schemas, examples,\ncontract manifest"]
        Docs["Operator, boundary,\nand validation docs"]
    end

    subgraph Engine["Environmental Fate Engine"]
        Runtime["Deterministic runtime"]
        Reference["Reference mass-balance\nscreening family"]
        Advective["Advective challenge\nscreening family"]
        Probabilistic["Probabilistic percentile\norchestration"]
    end

    subgraph Governance["Scientific Control Layer"]
        Defaults["Versioned defaults packs"]
        Provenance["Assumption ledger,\nquality flags, provenance"]
        Review["Scientific review,\ndossier, release metadata"]
    end

    subgraph Downstream["Suite Handoffs"]
        Exposure["Direct-Use Exposure MCP"]
        Dietary["Dietary Exposure MCP"]
        ReviewBundle["Regulatory handoff and\nreview artifacts"]
    end

    Clients --> Server
    Server --> Contracts
    Server --> Docs
    Server --> Runtime
    Runtime --> Reference
    Runtime --> Advective
    Runtime --> Probabilistic
    Runtime --> Defaults
    Runtime --> Provenance
    Server --> Review
    Server --> Exposure
    Server --> Dietary
    Server --> ReviewBundle
```

The released server is broader than a simple concentration calculator, but the boundary is still strict:

- `Environmental Fate MCP` owns environmental release scenarios, multimedia concentration estimation, scientific review, scientific methods dossiers, and downstream concentration handoff packaging.
- It also owns bounded scalar erosion/sediment transport screening for RUSLE, MUSLE, sediment-associated chemical-load handoffs, and inline validation QA when particle-bound soil transport is relevant.
- It now includes experimental non-default Level I/II fugacity equilibrium screening for multimedia partitioning challenge review; this is not Level III intermedia transfer, routing, calibration, source-engine equivalence, or regulator acceptance.
- It now publishes a governed evidence-quality matrix so reviewers can distinguish reviewer-grade, source-grounded, internal-oracle, synthetic-demo, and deferred/gap evidence without treating that posture as field validation or regulatory acceptance.
- `Direct-Use Exposure MCP` owns direct-use product scenarios, near-field external exposure construction, and PBPK-ready direct-use handoffs.
- `Dietary Exposure MCP` owns food-mediated oral intake, commodity-consumption mappings, and dietary PBPK-ready oral handoffs.
- `PBPK MCP` owns internal dose / toxicokinetic simulation after an external concentration or exposure object is already defined.
- The server is deterministic-first, with an additive probabilistic percentile lane, governed external-result normalization, scalar erosion/sediment transport screening, experimental fugacity equilibrium screening, and reviewer-facing validation fit diagnostics; it is not a general-purpose GIS dispersion or hydrologic routing engine, final-risk engine, calibration engine, Level III engine, or public wrapper around branded external model payloads.

## What's in v0.5.0

- Deterministic `reference_mass_balance` screening with finite-duration and bounded time-bucket concentration estimation
- Governed medium-specific temperature correction for degradation half-lives, anchored to a 25 °C reference with bounded screening-range behavior
- Governed experimental `advective_screening_mass_balance` challenge family with residence-time, bounded-transport, loss-dominance, transition, mass-balance, and post-release authority layers
- Experimental non-default `fugacity_equilibrium_screening` challenge family for Level I mass-conserving equilibrium partitioning and Level II equilibrium persistence/loss-balance screening
- Bounded scalar erosion/sediment transport tools for RUSLE annual soil-loss screening, MUSLE event sediment-yield screening, particle-bound relevance screening, and sediment-associated chemical-load handoff
- Inline erosion/sediment validation QA for observed-versus-predicted scalar screening records, with governed non-calibrating fit classifications
- Governed synthetic erosion/sediment validation demo pack for public screening-QA orientation without field-validation, calibration, routing, or WEPP claims
- Governed external benchmark replay pack for deterministic screening corroboration against official/public equation and reference scenarios, without claiming field validation or regulator acceptance
- Deterministic default sensitivity reporting for soil/sediment mass, degradation half-life, temperature/Q10, residence-time, release-duration, and release-fraction assumptions
- Governed scientific evidence-quality rubric and release matrix mapping every validation claim and model-family lane to reviewer-grade, source-grounded, internal-oracle, synthetic-demo, or deferred/gap posture
- Additive probabilistic percentile orchestration with median, P90, and P95 concentration surfaces plus failed-iteration taxonomy and reproducibility metadata
- Optional probabilistic sample manifests with seed, sampled-parameter summaries, iteration health, stable hashes, and capped row-level records when explicitly requested
- Scientific review packets and briefs with equation, mass-balance, transport-regime, loss-transition, and post-release interpretation lines
- Scientific methods dossiers and briefs with governed claims, benchmark support, source grounding, highlighted claim digests, promotion status, and blocker/action posture
- Model-family selection, challenge, and comparison review workflows so experimental families remain challenge-path review surfaces rather than silent defaults
- Governed external-result adapter lane with semantic-loss classification, fail-closed blocking for non-equivalent imports, provenance-preserving normalization, and a stable public normalized JSON/CSV import contract
- Regulatory handoff packages, summaries, packets, and briefs for downstream suite consumers
- Published JSON schemas, examples, contract manifest, release metadata, validation artifacts, and defaults manifests
- Self-contained wheel/sdist packaging with mirrored runtime artifacts for installed deployments
- GitHub release asset provenance workflow for Sigstore-backed artifact attestations on wheel, sdist, checksums, release-bundle manifest, and trust-pack assets

## Release snapshot

Current local release verification and generated `v0.5.0` artifacts report:

- `247` repository test functions
- `143` JSON schemas
- `139` generated examples
- `48` supported workflows surfaced through `57` tools, `22` prompts, and `32` resources
- `64` benchmark fixtures with claim-coverage enforcement
- `8` governed external benchmark replay cases
- `11` governed default sensitivity profiles
- `34` scientific evidence-quality claim rows and `5` model-family posture rows
- `34` governed scientific validation claims with plugin-code traceability
- `28` governed scientific reference cases
- `4` governed regulatory handoff profiles with downstream acknowledgement schema URLs
- `3` supported model families and `2` experimental model families
- `ready_for_screening_release` release status

The machine-readable source of truth for these counts is generated from the release metadata and validation-report builders in the repository.
Live `pytest` totals can be higher than the raw repository test-function count because parametrized tests expand into multiple collected cases at runtime.
`ready_for_screening_release` is an internal screening-release gate for the bounded MCP surface, not a statement of regulator acceptance, submission approval, or scientific equivalence to external engines.

## Why this project exists

Environmental fate is often the least auditable layer in early NGRA orchestration: release assumptions may be implicit, concentration math may be hidden inside spreadsheets or notebooks, and downstream reviewers often receive conclusions without a machine-readable record of defaults, limitations, and governing claims.

Environmental Fate MCP gives the suite a dedicated environmental-fate layer that is:

- **deterministic-first** for transparent screening and reviewer-facing challenge use
- **governed** through versioned defaults packs, applicability profiles, validation claims, reference cases, and explicit limitations
- **auditable** with structured correlation-ID logging (optional JSONL file output via `FATE_MCP_AUDIT_LOG_PATH`) and tamper-evident SHA-256 integrity hashes on every concentration bundle and regulatory handoff package
- **MCP-native** with typed tools, resources, prompts, schemas, examples, request skeletons, and release artifacts
- **bounded** so it complements Direct-Use Exposure MCP, Dietary Exposure MCP, PBPK MCP, and downstream review services instead of claiming their responsibilities
- **fail-closed** on non-physical inputs (non-positive half-lives and residence times raise hard errors rather than being silently clamped)

## Feature snapshot

| Capability | Description |
| --- | --- |
| `🌍 Environmental release screening` | Builds typed environmental release scenarios and deterministic concentration surfaces for multimedia screening use cases. |
| `🌊 Advective challenge family` | Publishes a governed experimental residence-time and bounded-transport challenge path with explicit comparison and challenge review workflows. |
| `⚖️ Fugacity equilibrium challenge` | Publishes an experimental non-default Level I/II multimedia partitioning challenge path with mass-conservation and degradation-loss validation, while explicitly excluding Level III transfer, routing, calibration, and acceptance claims. |
| `🌱 Erosion/sediment transport bridge` | Screens particle-bound transport relevance, computes scalar RUSLE soil loss and MUSLE event sediment yield, emits sediment-associated chemical-load handoff objects, and compares inline observed/predicted scalar records without claiming calibration, hydrologic routing, or final exposure. |
| `📊 Probabilistic percentile reporting` | Runs an additive percentile orchestration layer over the deterministic kernels and emits reviewable median, P90, and P95 surfaces plus iteration-health context. |
| `🔬 Scientific trust diagnostics` | Publishes governed external benchmark replay, deterministic default sensitivity reporting, and optional probabilistic sample manifests for reviewer-facing scientific transparency without adding calibration or routing scope. |
| `🧪 Scientific review surface` | Exports assessor-facing review packets and briefs with equation traces, mass-balance partitions, transport-regime lines, loss-transition cues, and post-release recovery interpretation. |
| `🧾 Scientific methods dossiers` | Publishes governed claim sets, source-grounding lines, benchmark support, highlighted claim digests, challenge posture, and promotion/blocker summaries for each model family. |
| `🔌 External adapter normalization` | Normalizes governed external-engine exports into canonical concentration contracts with normalization-parity checks, semantic-loss disclosure, and fail-closed blocking for non-equivalent mappings. |
| `🧭 Model-family challenge governance` | Exposes model-family selection, challenge, and comparison workflows so reference and experimental families remain reviewable under governed assessor logic. |
| `🔒 Installation and security hardening` | Ships wheel/sdist runtime artifacts, locked import-root validation, HTTP transport safety defaults, installed-wheel smoke coverage, dependency audit, Bandit, SBOM generation, Gitleaks secret scanning, and release-asset attestation support. |
| `📦 Regulatory handoff packaging` | Exports concentration bundles, regulatory handoff packages, summaries, packets, and briefs for downstream suite consumers without claiming final risk decisions. |
| `✅ Validation and release surface` | Ships defaults manifests, schemas, examples, benchmark manifests, scientific-claim coverage and freshness reports, validation dossiers, and release-readiness reports as first-class outputs. |

## Release verification

Current validation artifacts report:

- `ready_for_screening_release` release status
- `0` uncovered mandatory scientific validation claims
- `0` shipped tier-3 internal screening assumptions in the default execution path
- `0` stale claims without benchmark or code traceability
- deterministic example generation enforced for committed release artifacts
- server startup validates shipped artifacts without regenerating them
- deterministic and probabilistic review workflow parity enforced through validation
- governed synthetic erosion/sediment validation demos execute through the validation tools and match declared fit classifications
- governed external benchmark replay cases execute through the public tools and match declared tolerances
- default sensitivity profiles execute deterministically and keep calibration/routing/field-validation boundaries explicit
- experimental fugacity screening profiles validate Level I mass conservation, requested-media filtering, Level II degradation-loss balance, and explicit no-Level-III/no-routing/no-calibration boundary language
- probabilistic sample manifests are opt-in, capped, and hash stable when requested
- shipped defaults evidence governance, external corroboration governance, red-team review accounting, and reviewer trust-pack generation included in release gating
- adapter normalization, scientific review, scientific methods dossier, model-family challenge, and regulatory handoff workflows included in release gating
- scientific invariant tests proving mass-balance closure, advection bounds, mass linearity, and half-life monotonicity
- CI fails if generated artifacts or defaults manifest hashes drift from committed state, if the full release validator fails, or if startup validation cannot load the shipped artifacts
- CI builds the wheel and installs it into a clean Python 3.12 environment before checking server startup, packaged release resources, public tool annotations/output schemas, validation demo-pack loading, and shipped adapter-fixture access
- external payload imports are confined to shipped adapter fixtures unless operators opt in additional roots through `FATE_MCP_IMPORT_ROOTS`; symlink escapes are rejected after path resolution
- external payload imports are capped by default at 5 MB and 5,000 surface rows, with explicit operator overrides for controlled local imports
- concentration surfaces report `reported_time_semantics`; `steady_state` is end-of-duration screening, not an infinite-time equilibrium claim
- fugacity concentration surfaces report `reported_time_semantics=fugacity_equilibrium_partitioning` so the experimental equilibrium path is not confused with the reference end-of-duration screen
- release fractions are invariant-checked at `0 < sum(release_fractions) <= 1.0`; unallocated mass remains outside scoped media and is surfaced as a warning
- supply-chain checks run Ruff, tests, Bandit, `pip-audit`, SBOM generation, and checksum-verified Gitleaks CLI secret scanning
- GitHub releases can publish wheel/sdist/checksum assets with Sigstore-backed GitHub Artifact Attestations; verify them with `gh attestation verify`

This release gate remains a product-level screening-readiness status rather than a claim of formal regulatory acceptance, legal sufficiency, or source-engine scientific equivalence.

See:

- [docs/release_readiness.md](./docs/release_readiness.md)
- [docs/defaults_evidence_map.md](./docs/defaults_evidence_map.md)
- [docs/validation_framework.md](./docs/validation_framework.md)
- [docs/suite_integration.md](./docs/suite_integration.md)
- [docs/workflow_cookbook.md](./docs/workflow_cookbook.md)
- [docs/external_payload_contract.md](./docs/external_payload_contract.md)
- [docs/erosion_sediment_transport.md](./docs/erosion_sediment_transport.md)
- [docs/fugacity_screening.md](./docs/fugacity_screening.md)
- [docs/scientific_evidence_quality_matrix.md](./docs/scientific_evidence_quality_matrix.md)
- [docs/scientific_hardening_tracker.md](./docs/scientific_hardening_tracker.md)
- [docs/confidentiality_bundles.md](./docs/confidentiality_bundles.md)
- [docs/agent_evaluations.md](./docs/agent_evaluations.md)
- [docs/public_release_guide.md](./docs/public_release_guide.md)
- [docs/releases/v0.5.0/scientific-trust-pack.md](./docs/releases/v0.5.0/scientific-trust-pack.md)
- [docs/release_provenance.md](./docs/release_provenance.md)
- [CHANGELOG.md](./CHANGELOG.md)
- [MIGRATION.md](./MIGRATION.md)
- [docs/regulatory_quick_start.md](./docs/regulatory_quick_start.md)
- [docs/releases/v0.5.0/release-notes.md](./docs/releases/v0.5.0/release-notes.md)

## Governance

- [CONTRIBUTING.md](./CONTRIBUTING.md)
- [SECURITY.md](./SECURITY.md)
- [SUPPORT.md](./SUPPORT.md)
- [docs/releases/public_release_checklist.md](./docs/releases/public_release_checklist.md)

## Quick start

```bash
uv sync --extra dev
uv run environmental-fate-mcp-generate-artifacts
uv run environmental-fate-mcp-build-release-bundle
uv run --extra dev ruff check .
uv run --extra dev pytest
uv run environmental-fate-mcp-validate
uv build
uv run environmental-fate-mcp
```

The package is also designed to run from an installed wheel without a git checkout. `FATE_MCP_RESOURCE_ROOT` can override the runtime artifact root for controlled deployments; otherwise the server prefers the checkout resources during development and packaged resources after installation.

For regulatory deployments, enable durable JSONL audit logging:

```bash
export FATE_MCP_AUDIT_LOG_PATH="/var/log/fate-mcp/audit.jsonl"
uv run environmental-fate-mcp
```

Legacy CLI aliases remain available:

- `uv run fate-mcp`
- `uv run fate-mcp-generate-artifacts`
- `uv run fate-mcp-validate`

## Repository layout

- `src/fate_mcp/`: package code and MCP server surface
- `src/fate_mcp/package_data/`: generated runtime artifact mirror included in wheels and sdists
- `src/fate_mcp/integrations/`: review artifact builders (scientific review, model-family comparison/challenge, regulatory handoff)
- `defaults/v1/`: curated defaults, applicability profiles, scientific validation claims, and reference cases
- `docs/contracts/schemas/`: generated JSON Schema files
- `schemas/examples/`: generated example payloads
- `docs/releases/`: generated release bundles and release-documentation surface
- `docs/adr/`: architecture decisions
- `tests/`: runtime, defaults, validation, adapter, integration, invariants, and manifest-hash regression coverage

## Current limitations

- Not a direct-use product exposure engine
- Not a dietary intake engine
- Not a PBPK execution engine
- Not a GIS-resolved plume or hydrodynamic dispersion engine
- Not a watershed hydrology, rainfall-runoff generation, channel-routing, deposition-field, or WEPP execution engine
- Not a general-purpose unrestricted probabilistic fate platform outside the governed percentile workflow
- Not a final regulatory decision engine or a claim of formal equivalence to submission portals

The detailed boundary and limitation notes are in [docs/fate_model_boundary_guide.md](./docs/fate_model_boundary_guide.md) and [docs/model_applicability_limits.md](./docs/model_applicability_limits.md).

## License

Apache License 2.0.
