# Release Provenance

Environmental Fate MCP releases use GitHub Artifact Attestations for release-asset provenance.

The release provenance workflow is a supply-chain trust layer. It does not change the scientific model boundary, does not make regulator acceptance or regulatory-acceptance claims, and does not prove that screening outputs are scientifically adequate for a specific site or decision. It links published assets to the GitHub Actions workflow, source repository, tag, and build instructions that produced them.

## Attested Assets

For each published release, the provenance workflow builds and uploads:

- the Python wheel
- the source distribution
- `RELEASE_ASSET_SHA256SUMS`
- the release-bundle `SHA256SUMS`
- the release-bundle manifest
- the scientific trust pack

The workflow signs these assets with GitHub Artifact Attestations through Sigstore-backed signing. GitHub stores the attestations with the repository; public repositories use the Sigstore public-good instance, while private or internal repositories use GitHub's Sigstore instance.

## Verify A Release Asset

Install the GitHub CLI, download a release asset, then run:

```bash
gh attestation verify environmental_fate_mcp-0.4.0-py3-none-any.whl \
  --repo ToxMCP/environmental-fate-mcp
```

For the source distribution:

```bash
gh attestation verify environmental_fate_mcp-0.4.0.tar.gz \
  --repo ToxMCP/environmental-fate-mcp
```

For the checksum manifest:

```bash
gh attestation verify RELEASE_ASSET_SHA256SUMS \
  --repo ToxMCP/environmental-fate-mcp
```

Verification confirms that the asset has an attestation associated with this repository. Reviewers should still compare hashes, inspect release notes, and apply their own policy checks before trusting a release in a regulated or decision-facing workflow.

## Offline Or Air-Gapped Review

If online verification is not available, use the attached checksum files and release-bundle manifest for deterministic integrity checks. Offline attestation verification requires separately preserving the attestation bundle and applying an offline verification policy; the default public workflow is optimized for online `gh attestation verify` checks.

## Maintainer Checklist

Before publishing a provenance-bearing release:

- merge the release PR to `main`
- create and push the `vX.Y.Z` tag from the release commit
- create the GitHub release from the generated release notes
- wait for the `Release provenance` workflow to finish
- confirm the wheel, sdist, checksum files, release-bundle manifest, and trust pack were uploaded as release assets
- verify at least the wheel, sdist, and `RELEASE_ASSET_SHA256SUMS` with `gh attestation verify`

## Limitations

Artifact attestations are not a guarantee that the release is vulnerability-free, scientifically sufficient, regulator-accepted, or appropriate for a particular use case. They provide cryptographic linkage between an artifact, repository, workflow, and build provenance. Scientific validation and adequacy remain governed by the validation reports, benchmark packs, sensitivity reports, model-boundary docs, and independent reviewer judgment.
