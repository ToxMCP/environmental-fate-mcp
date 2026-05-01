# Release Bundle v0.2.0

This directory contains the deterministic public release bundle for Environmental Fate MCP `0.2.0`.
Release status: `ready_for_screening_release`.
This status is an internal bounded-screening release gate, not a statement of regulator acceptance, submission approval, or source-engine scientific equivalence.

## Files
- `metadata-report.json`: Release metadata summary for counts, supported workflows, and governed coverage.
- `readiness-report.json`: Machine-readable release status and the top-level release gate checks.
- `security-provenance-review-report.json`: Security and provenance review posture summary.
- `benchmark-manifest.json`: Benchmark fixture manifest and claim linkage surface.
- `scientific-claim-coverage-report.json`: Scientific validation claim coverage and unresolved-gap report.
- `defaults-rebaseline-report.json`: Governed shipped-default evidence and derivation completeness report.
- `external-corroboration-report.json`: Governed claim-level corroboration posture and stronger evidence-bar report.
- `reference-corroboration-report.json`: Reviewer-grade corroboration matrix for mandatory reference-family claims, official grounding, and worksheet readiness.
- `reference-worksheet-manifest.json`: Deterministic worksheet-pack manifest linking mandatory reference claims to machine-readable worksheet and expected-output artifacts.
- `advective-promotion-bar-report.json`: Experimental-family promotion-bar posture with explicit non-promotable reasons for the advective challenge path.
- `red-team-review-report.json`: Release red-team review cycle summary with blocker accounting and accepted limitations.
- `validation-dossier.json`: Full validation dossier across scientific, interoperability, and release checks.
- `adapter-validation-report.json`: Focused validation report for governed adapter interoperability.
- `erosion-sediment-validation-demo-report.json`: Governed synthetic erosion/sediment validation demo-pack report and classification checks.
- `known-gap-report.json`: Declared known gaps that remain intentionally out of scope for this release.
- `scientific-trust-pack.md`: Reviewer-facing scientific trust pack for the exact release reference.
- `scientific-trust-brief.md`: Compact reviewer-facing trust brief for the exact release reference.
- `reference-proof-brief.md`: Compact reviewer-facing brief for the reviewer-grade reference-family proof surface.
- `advective-promotion-brief.md`: Compact reviewer-facing brief for the experimental advective-family promotion bar.
- `reference-worksheet-pack/`: claim-linked worksheet and expected-output artifacts for mandatory reference-family proof review.
- `release-notes.md`: Human-readable release notes for the exact release reference.
- `README.md`: Index of the release bundle contents.
- `release-bundle-manifest.json`: Bundle manifest with SHA-256 checksums for bundled release files.
- `SHA256SUMS`: SHA-256 checksums for release bundle verification.

This bundle is intended to be attached to or referenced from a tagged GitHub release.
