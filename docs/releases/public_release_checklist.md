# Public Release Checklist

This checklist is the public-facing companion to the deeper release-readiness rules in [`../release_readiness.md`](../release_readiness.md). It is intended for release managers and maintainers preparing a public tag or GitHub release.

## Repository Governance

- [ ] `README.md` matches the current shipped capability and boundary surface
- [ ] `CHANGELOG.md` reflects user-visible and governance-visible changes
- [ ] `LICENSE` is present and correct
- [ ] `SECURITY.md`, `SUPPORT.md`, and `CONTRIBUTING.md` are current
- [ ] `CODEOWNERS` reflects the actual current maintainer or team ownership
- [ ] issue templates and PR template still match the actual release process
- [ ] public docs do not overclaim beyond the declared screening boundary

## Build and Validation

- [ ] `uv sync --extra dev`
- [ ] `uv run fate-mcp-generate-artifacts`
- [ ] generated artifacts are deterministic across reruns
- [ ] `uv run pytest`
- [ ] `uv run environmental-fate-mcp-validate`
- [ ] `uv run python -c "from fate_mcp.server import create_server; create_server()"`
- [ ] generated schemas, examples, and defaults manifests are committed and up to date

## Scientific and Regulatory Trust

- [ ] limitations remain explicit in docs and exported artifacts
- [ ] experimental model families remain clearly marked as non-default challenge paths
- [ ] benchmark and claim coverage remain current
- [ ] downstream handoff packages remain integrity-protected and disclaimer-bearing
- [ ] release notes do not imply final regulatory decision-engine status

## Public Release Packaging

- [ ] create an annotated version tag
- [ ] draft GitHub release notes for the exact tagged commit
- [ ] attach or publish the validation outcome for the tagged release
- [ ] publish checksums for any distributed release artifacts if applicable
- [ ] confirm the release badge and license badge resolve correctly on GitHub

## Repository Settings Outside Git

These controls live in GitHub settings rather than the repository tree, but they still matter for a `10/10` release posture:

- [ ] branch protection is enabled on `main`
- [ ] required CI checks are enforced before merge
- [ ] signed tags are used for public releases
- [ ] dependency and security scanning are enabled
- [ ] artifact attestation / provenance strategy is documented if distribution expands
