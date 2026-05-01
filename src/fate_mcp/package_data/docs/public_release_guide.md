# Public Release Guide

This guide describes the public `v0.2.1` release-preparation posture for Environmental Fate MCP.

## Release Boundary

Environmental Fate MCP is released as a bounded environmental concentration-screening MCP. It supports deterministic and bounded probabilistic concentration workflows, scientific review artifacts, regulatory handoff packaging, governed external-result normalization, scalar erosion/sediment screening, and inline validation QA.

The public release does not claim regulator acceptance, submission approval, final exposure or risk assessment, source-engine equivalence, hydrology generation, calibration, spatial routing, catchment validation, or native WEPP execution.

Concentration surfaces expose `reported_time_semantics`. A `steady_state` run mode means end-of-duration screening concentration, not infinite-time equilibrium.

## Validation Demo Pack

The governed validation demo pack is exposed at `defaults://erosion-sediment-validation-demo-pack`.

It contains synthetic observed-versus-predicted erosion/sediment records for four expected classifications:

- `good_screening_fit`
- `screening_plausible`
- `weak_fit`
- `insufficient_evidence`

These cases demonstrate the mechanics and interpretation of the scalar validation tools. They are not field validation, calibration evidence, watershed model acceptance, regulator acceptance, or WEPP/catchment validation.

## Artifact Maintenance

Public release changes must treat repo-root artifacts and the packaged runtime mirror as one release surface:

- update source defaults, docs, contracts, or generators first
- regenerate schemas/examples and the release bundle
- review generated repo-root artifacts and `src/fate_mcp/package_data` mirror changes together
- do not hand-edit generated mirror files to satisfy CI
- keep known limitations visible in README, boundary docs, trust artifacts, and release reports
- keep external import hard limits and release-fraction invariants visible in user-facing docs

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

This repository can be prepared for `v0.2.1` without creating the tag in the same change. Tagging and GitHub release publication should happen only after CI, security scanning, release artifact review, and maintainer approval are complete.
