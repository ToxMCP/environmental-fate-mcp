# Migration Guide

This document describes how to migrate between major and minor versions of the Environmental Fate MCP.

## General Principles

1. **Schema version compatibility:** The MCP uses a `schema_version` field (currently `v0.1`) on all major models. Breaking schema changes will increment this version.
2. **Defaults versioning:** Curated defaults are versioned under `defaults/vX/`. Old defaults remain available for the lifetime of any run that references them.
3. **Backward-compatible tool surface:** New tools and optional fields are added without removing existing ones. Deprecated tools are preserved for at least one minor release with a `WARNING` quality flag.
4. **Contract artifacts:** Schemas and examples in `docs/contracts/` and `schemas/examples/` are regenerated automatically. Do not hand-edit generated files.

## Upgrading to a New Version

### Step 1: Review the Changelog
Read `CHANGELOG.md` for the target version to understand new features, deprecations, and breaking changes.

### Step 2: Regenerate Contract Artifacts
Run the artifact generator to update schemas and examples:

```bash
uv run environmental-fate-mcp-generate-artifacts
```

Commit any changes to tracked files.

### Step 3: Run the Full Test Suite
```bash
uv run pytest
```

### Step 4: Validate Against Your Integration Tests
If you are a downstream consumer (orchestrator, exposure MCP, regulatory handoff target), verify that:
- Your request payloads still validate against the updated JSON schemas.
- Your response parsers handle any newly added fields gracefully.
- Your regulatory handoff profiles are still supported in the target matrix.

### Step 5: Update Defaults Manifest Hashes
If you modify any defaults JSON file, the CI will fail unless the `defaults/manifest.json` SHA-256 hashes are updated. The manifest is updated automatically when you run the artifact generator, but you must commit the change.

## Version-Specific Notes

### 0.1.0 → Unreleased (current development)
- **Behavioral change:** Non-positive half-lives now raise `FateValidationError` instead of being clamped. If your workflows previously relied on the clamping behavior, you must validate half-life inputs upstream.
- **New required fields (with defaults):** `ConcentrationSurfaceBundle` now includes `regulatory_use_disclaimer` and `integrity_hash`. These are populated automatically; no migration action is needed for consumers that ignore unknown fields.
- **New defaults file:** `defaults/v1/reconciliation_thresholds.json` has been added. If you maintain a custom defaults manifest, include this file and its hash.
- **New schema field:** `BuildEnvironmentalReleaseScenarioRequest` and `EnvironmentalReleaseScenario` now include `temperature_c` (default `25.0`). Existing requests without this field will continue to work.

## Deprecation Policy

- **Minor versions (0.x.0):** May add new tools, fields, and defaults. Deprecated items receive a `WARNING` quality flag but continue to function.
- **Major versions (x.0.0):** May remove deprecated tools, change schema contracts, or restructure defaults. A major release will include a minimum 30-day advance notice in the changelog.
- **Defaults obsolescence:** Defaults marked `supersededBy` emit a `WARNING` flag but remain usable. Defaults past their `expirationDate` are downgraded to `heuristic` source classification.

## Getting Help

If you encounter an unexpected breaking change, please:
1. Check that contract artifacts are up to date.
2. Verify your request payload against the generated JSON schema.
3. Open an issue with the `scenario_id`, `run_id`, and the exact error payload.
