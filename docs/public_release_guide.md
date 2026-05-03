# Public Release Guide

This guide describes the public `v0.4.0` release-preparation posture for Environmental Fate MCP.

## Release Boundary

Environmental Fate MCP is released as a bounded environmental concentration-screening MCP. It supports deterministic and bounded probabilistic concentration workflows, scientific review artifacts, regulatory handoff packaging, governed external-result normalization, scalar erosion/sediment screening, inline validation QA, governed benchmark replay, deterministic default sensitivity reporting, optional probabilistic sample manifests, and an experimental non-default Level I/II fugacity equilibrium screening challenge family.

The public release does not claim regulator acceptance, submission approval, final exposure or risk assessment, source-engine equivalence, Level III fugacity intermedia transfer, hydrology generation, calibration, spatial routing, catchment validation, SWAT/PRZM execution, or native WEPP execution.

Concentration surfaces expose `reported_time_semantics`. A `steady_state` run mode means end-of-duration screening concentration, not infinite-time equilibrium.
Fugacity surfaces explicitly report `fugacity_equilibrium_partitioning` because that experimental family is an equilibrium partitioning challenge path, not the reference end-of-duration screen.

## Validation Demo Pack

The governed validation demo pack is exposed at `defaults://erosion-sediment-validation-demo-pack`.

It contains synthetic observed-versus-predicted erosion/sediment records for four expected classifications:

- `good_screening_fit`
- `screening_plausible`
- `weak_fit`
- `insufficient_evidence`

These cases demonstrate the mechanics and interpretation of the scalar validation tools. They are not field validation, calibration evidence, watershed model acceptance, regulator acceptance, or WEPP/catchment validation.

## Scientific Trust Diagnostics

The governed external benchmark pack is exposed at `defaults://scientific-external-benchmark-pack`, with release results at `release://external-validation-benchmark-report`.
The governed default sensitivity profiles are exposed at `defaults://default-sensitivity-profiles`, with release results at `release://default-sensitivity-report`.

These artifacts improve deterministic screening corroboration and assumption transparency. They are not field validation, calibration, source-engine equivalence, global sensitivity analysis, or regulator acceptance.

## Fugacity Screening

The governed fugacity screening method profiles are exposed at `defaults://fugacity-screening-method-profiles`, with release validation at `release://fugacity-screening-validation-report`.

This path supports experimental Level I equilibrium mass partitioning and Level II equilibrium persistence/loss-balance screening only. It is not a Level III implementation, routed transport model, calibrated model, CEMC source-engine equivalence claim, field-validation claim, exposure/risk result, or regulator acceptance.

## Artifact Maintenance

Public release changes must treat repo-root artifacts and the packaged runtime mirror as one release surface:

- update source defaults, docs, contracts, or generators first
- regenerate schemas/examples and the release bundle
- review generated repo-root artifacts and `src/fate_mcp/package_data` mirror changes together
- do not hand-edit generated mirror files to satisfy CI
- keep known limitations visible in README, boundary docs, trust artifacts, and release reports
- keep external import hard limits and release-fraction invariants visible in user-facing docs

## Release Provenance

Public releases should use the `Release provenance` workflow after the GitHub release is published.
The workflow builds the wheel and source distribution from the tagged commit, uploads release checksums and reviewer trust assets, and creates GitHub Artifact Attestations for the release assets.

Reviewers can verify downloaded assets with:

```bash
gh attestation verify environmental_fate_mcp-0.4.0-py3-none-any.whl \
  --repo ToxMCP/environmental-fate-mcp
```

Artifact attestations provide build provenance, not scientific validation, regulator acceptance, deployment approval, or vulnerability absence.
See [release_provenance.md](./release_provenance.md).

## Required Local Gate

Run the full public-release gate before tagging or publishing:

```bash
uv run environmental-fate-mcp-generate-artifacts
uv run environmental-fate-mcp-build-release-bundle
uv run --extra dev ruff check .
uv run --extra dev pytest
uv run environmental-fate-mcp-validate
uv run python -c "from fate_mcp.server import create_server; create_server()"
uv build
```

Then install the built wheel into a clean Python 3.12 virtual environment and verify server startup, resource counts, tool annotations, output schemas, release metadata, packaged defaults, and the validation demo-pack resource.

## Tagging Posture

This repository can be prepared for `v0.4.0` without creating the tag in the same change. Tagging and GitHub release publication should happen only after CI, security scanning, release artifact review, and maintainer approval are complete. After publishing the GitHub release, wait for the release-provenance workflow to upload assets and attestations before broad announcement.
