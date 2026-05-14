from __future__ import annotations

import argparse
import ast
import asyncio
from collections import Counter
import hashlib
import json
from pathlib import Path

from fate_mcp.benchmarks import benchmark_manifest, supporting_benchmark_fixtures_for_claim
from fate_mcp.contracts import build_contract_manifest, generate_contract_artifacts
from fate_mcp.defaults import DefaultsRegistry
from fate_mcp.evidence_quality import build_scientific_evidence_quality_matrix_report
from fate_mcp.package_metadata import (
    EXPERIMENTAL_MODEL_FAMILIES,
    SUPPORTED_MODEL_FAMILIES,
    SUPPORTED_WORKFLOWS,
    VERSION,
)
from fate_mcp.plugins.external_result_adapter import build_adapter_import_manifest
from fate_mcp.resources import refresh_packaged_resource_mirror
from fate_mcp.validation import validation_dossier


KNOWN_GAPS = [
    "No GIS-scale dispersion in v0.5.",
    "No rainfall-runoff generation, channel routing, deposition-field modelling, SWAT/PRZM execution, or native WEPP execution in v0.5.",
    "Fugacity equilibrium screening is experimental Level I/II-style partitioning only; no Level III intermedia-transfer, advective export, calibration, field validation, or regulatory acceptance claim is added.",
    "External benchmark packs are deterministic screening corroboration fixtures, not curated field validation datasets.",
    "The evidence-quality matrix grades release-review evidence posture only; it does not add field validation, calibration evidence, regulator acceptance, or model promotion.",
    "Erosion/sediment validation demos remain synthetic screening-QA demonstrations, not curated field benchmark validation.",
    "No direct human dose calculation in Environmental Fate MCP.",
    "No dietary intake workflows in Environmental Fate MCP.",
    "No PBPK execution in Environmental Fate MCP.",
    "Branded desktop-model ingestion remains limited to governed adapter profiles; only normalized external payload JSON/CSV is a public MCP import contract in this release.",
]

REFERENCE_WORKSHEET_PACK_DIR = "reference-worksheet-pack"
ADVECTIVE_WORKSHEET_PACK_DIR = "advective-worksheet-pack"

REPORT_FILENAMES = (
    ("metadata-report", "metadata-report.json"),
    ("readiness-report", "readiness-report.json"),
    ("security-provenance-review-report", "security-provenance-review-report.json"),
    ("benchmark-manifest", "benchmark-manifest.json"),
    ("scientific-claim-coverage-report", "scientific-claim-coverage-report.json"),
    ("defaults-rebaseline-report", "defaults-rebaseline-report.json"),
    ("external-corroboration-report", "external-corroboration-report.json"),
    ("reference-corroboration-report", "reference-corroboration-report.json"),
    ("reference-worksheet-manifest", "reference-worksheet-manifest.json"),
    ("advective-worksheet-manifest", "advective-worksheet-manifest.json"),
    ("advective-promotion-bar-report", "advective-promotion-bar-report.json"),
    ("red-team-review-report", "red-team-review-report.json"),
    ("validation-dossier", "validation-dossier.json"),
    ("adapter-validation-report", "adapter-validation-report.json"),
    ("erosion-sediment-validation-demo-report", "erosion-sediment-validation-demo-report.json"),
    ("external-validation-benchmark-report", "external-validation-benchmark-report.json"),
    ("default-sensitivity-report", "default-sensitivity-report.json"),
    ("fugacity-screening-validation-report", "fugacity-screening-validation-report.json"),
    ("scientific-evidence-quality-matrix-report", "scientific-evidence-quality-matrix-report.json"),
    ("scientific-validation-narrative", "scientific-validation-narrative.json"),
    ("known-gap-report", "known-gap-report.json"),
)

REPORT_DESCRIPTIONS = {
    "metadata-report.json": "Release metadata summary for counts, supported workflows, and governed coverage.",
    "readiness-report.json": "Machine-readable release status and the top-level release gate checks.",
    "security-provenance-review-report.json": "Security and provenance review posture summary.",
    "benchmark-manifest.json": "Benchmark fixture manifest and claim linkage surface.",
    "scientific-claim-coverage-report.json": "Scientific validation claim coverage and unresolved-gap report.",
    "defaults-rebaseline-report.json": "Governed shipped-default evidence and derivation completeness report.",
    "external-corroboration-report.json": "Governed claim-level corroboration posture and stronger evidence-bar report.",
    "reference-corroboration-report.json": "Reviewer-grade corroboration matrix for mandatory reference-family claims, official grounding, and worksheet readiness.",
    "reference-worksheet-manifest.json": "Deterministic worksheet-pack manifest linking mandatory reference claims to machine-readable worksheet and expected-output artifacts.",
    "advective-worksheet-manifest.json": "Deterministic worksheet-pack manifest linking experimental advective-family claims to machine-readable internal-oracle worksheet and expected-output artifacts.",
    "advective-promotion-bar-report.json": "Experimental-family promotion-bar posture with explicit non-promotable reasons for the advective challenge path.",
    "red-team-review-report.json": "Release red-team review cycle summary with blocker accounting and accepted limitations.",
    "validation-dossier.json": "Full validation dossier across scientific, interoperability, and release checks.",
    "adapter-validation-report.json": "Focused validation report for governed adapter interoperability.",
    "erosion-sediment-validation-demo-report.json": "Governed synthetic erosion/sediment validation demo-pack report and classification checks.",
    "external-validation-benchmark-report.json": "Governed external benchmark-pack report for deterministic screening corroboration checks.",
    "default-sensitivity-report.json": "Deterministic governed default-sensitivity report for reviewer-facing assumption transparency.",
    "fugacity-screening-validation-report.json": "Focused validation report for the experimental Level I/II fugacity equilibrium screening family.",
    "scientific-evidence-quality-matrix-report.json": "Claim-by-claim and model-family scientific evidence-quality matrix for bounded screening release review.",
    "scientific-validation-narrative.json": "Reviewer-facing scientific validation narrative covering benchmark, sensitivity, uncertainty, and boundary interpretation.",
    "known-gap-report.json": "Declared known gaps that remain intentionally out of scope for this release.",
    "reference-proof-brief.md": "Compact reviewer-facing brief for the reviewer-grade reference-family proof surface.",
    "advective-promotion-brief.md": "Compact reviewer-facing brief for the experimental advective-family promotion bar.",
    "scientific-trust-pack.md": "Reviewer-facing scientific trust pack for the exact release reference.",
    "scientific-trust-brief.md": "Compact reviewer-facing trust brief for the exact release reference.",
    "release-notes.md": "Human-readable release notes for the exact release reference.",
    "README.md": "Index of the release bundle contents.",
    "release-bundle-manifest.json": "Bundle manifest with SHA-256 checksums for bundled release files.",
    "SHA256SUMS": "SHA-256 checksums for release bundle verification.",
}


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _json_text(payload: object) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _count_repo_tests(repo_root: Path) -> int:
    total = 0
    for path in sorted((repo_root / "tests").glob("test_*.py")):
        module = ast.parse(path.read_text())
        total += sum(
            1
            for node in ast.walk(module)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name.startswith("test_")
        )
    return total


def _server_surface_counts() -> dict[str, int]:
    from fate_mcp.server import create_server

    async def _collect() -> dict[str, int]:
        server = create_server()
        return {
            "toolCount": len(await server.list_tools()),
            "promptCount": len(await server.list_prompts()),
            "resourceCount": len(await server.list_resources()),
        }

    return asyncio.run(_collect())


def _render_release_notes(reports: dict[str, dict], release_ref: str) -> str:
    metadata = reports["metadata-report"]
    readiness = reports["readiness-report"]
    validation = reports["validation-dossier"]
    defaults_report = reports["defaults-rebaseline-report"]
    reference_report = reports["reference-corroboration-report"]
    worksheet_manifest = reports["reference-worksheet-manifest"]
    advective_report = reports["advective-promotion-bar-report"]
    erosion_demo_report = reports["erosion-sediment-validation-demo-report"]
    benchmark_report = reports["external-validation-benchmark-report"]
    sensitivity_report = reports["default-sensitivity-report"]
    fugacity_report = reports["fugacity-screening-validation-report"]
    evidence_quality_report = reports["scientific-evidence-quality-matrix-report"]
    known_gaps = reports["known-gap-report"]["knownGaps"]
    passed_checks = sum(1 for item in readiness["checks"] if item["passed"])
    total_checks = len(readiness["checks"])
    lines = [
        f"# Environmental Fate MCP {release_ref}",
        "",
        f"Version: `{VERSION}`",
        f"Release status: `{readiness['status']}`",
        "This is an internal bounded-screening release gate, not a statement of regulator acceptance, submission approval, or source-engine scientific equivalence.",
        "",
        "## Highlights",
        f"- `{metadata['schemaCount']}` JSON schemas and `{metadata['exampleCount']}` generated examples are published for the release surface.",
        f"- `{metadata['testCount']}` repository test functions and `{metadata['toolCount']}` tools / `{metadata['promptCount']}` prompts / `{metadata['resourceCount']}` resources back the released MCP surface.",
        f"- `{len(metadata['supportedWorkflows'])}` governed workflows are available across `{len(metadata['supportedModelFamilies'])}` supported model families and `{metadata['experimentalModelFamilyCount']}` experimental model family.",
        f"- `{metadata['scientificValidationClaimCount']}` governed scientific validation claims and `{metadata['scientificReferenceCaseCount']}` governed scientific reference cases are included.",
        f"- `{metadata['regulatoryHandoffProfileCount']}` governed regulatory handoff profiles are published for downstream suite consumers.",
        f"- `{erosion_demo_report['demoCaseCount']}` synthetic erosion/sediment validation demo cases are published for reviewer-facing screening QA orientation.",
        f"- `{benchmark_report['caseCount']}` governed external benchmark replay cases are published for deterministic screening corroboration.",
        f"- `{sensitivity_report['profileCount']}` governed default sensitivity profiles are published for reviewer-facing assumption transparency.",
        f"- `{fugacity_report['profileCount']}` experimental fugacity screening method profiles are published with Level I/II validation checks.",
        f"- `{evidence_quality_report['claim_row_count']}` claim rows and `{evidence_quality_report['model_family_row_count']}` model-family rows are published in the scientific evidence-quality matrix.",
        "- Release asset provenance is supported through GitHub Artifact Attestations for the wheel, sdist, checksums, release-bundle manifest, and trust pack.",
        "",
        "## Verification Summary",
        f"- Release checks passed: `{passed_checks}/{total_checks}`.",
        f"- Mandatory scientific validation claims uncovered: `{metadata['scientificValidationUncoveredMandatoryClaimCount']}`.",
        f"- Benchmarks passed: `{validation['benchmarks']['passed']}`.",
        f"- Defaults evidence governance passed: `{validation['defaultsEvidenceGovernance']['passed']}`.",
        f"- External corroboration governance passed: `{validation['externalCorroborationGovernance']['passed']}`.",
        f"- Downstream interoperability passed: `{validation['downstreamInteroperability']['passed']}`.",
        f"- Regulatory handoff governance passed: `{validation['regulatoryHandoffGovernance']['passed']}`.",
        f"- Scientific review artifacts passed: `{validation['scientificReviewArtifacts']['passed']}`.",
        f"- Erosion/sediment validation demo pack passed: `{erosion_demo_report['passed']}`.",
        f"- External benchmark pack passed: `{benchmark_report['passed']}`.",
        f"- Default sensitivity profiles passed: `{sensitivity_report['passed']}`.",
        f"- Fugacity screening validation passed: `{fugacity_report['passed']}`.",
        f"- Scientific evidence-quality matrix passed: `{evidence_quality_report['passed']}`.",
        "",
        "## Scientific Change Log",
        f"- Shipped-default numeric deltas recorded this release: `{defaults_report['changedParameterCount']}` parameter(s), with `{defaults_report['materiallyChangedParameterCount']}` marked as materially output-affecting.",
        f"- Defaults rebaseline review status: `{defaults_report['reviewStatus']}`.",
        (
            f"- Mandatory reference-family claims meeting the reviewer-grade corroboration bar: "
            f"`{sum(1 for claim in reference_report['claims'] if claim['passed'])}/{reference_report['claimCount']}`."
        ),
        (
            f"- Machine-readable worksheet pack readiness: "
            f"`{sum(1 for claim in worksheet_manifest['claims'] if claim['worksheetStatus'] == 'ready')}/{worksheet_manifest['claimCount']}` claim-linked worksheet artifacts."
        ),
        "- `reference_mass_balance` remains the reviewer-grade anchor for decision-facing bounded screening.",
        (
            "- `advective_screening_mass_balance` remains experimental and non-promotable in this release."
            if not advective_report["promotable"]
            else "- Experimental-family promotion posture changed in this release."
        ),
        "- Adapter posture remains normalization parity only; this release does not claim source-engine scientific equivalence.",
        "- Release attestations, when present on GitHub release assets, establish build provenance only; they are not scientific validation or regulator acceptance.",
        "",
        "## Known Gaps",
    ]
    lines.extend(f"- {gap}" for gap in known_gaps)
    lines.extend(
        [
            "",
            "## Bundle Contents",
            "- Machine-readable release reports are published alongside this note in the same directory.",
            "- `scientific-trust-pack.md` provides a reviewer-ready trust summary for the release.",
            "- `scientific-trust-brief.md` provides a compact one-shot trust briefing for reviewers and agents.",
            "- `reference-corroboration-report.json` gives the mandatory reference-family corroboration matrix.",
            "- `reference-worksheet-manifest.json` links each mandatory reference claim to its worksheet and expected-output artifacts.",
            "- `reference-worksheet-pack/` contains the claim-linked worksheet and expected-output artifacts used for skeptical reviewer handoff.",
            "- `advective-promotion-bar-report.json` explains why the advective family remains experimental in this release.",
            "- `erosion-sediment-validation-demo-report.json` checks the synthetic erosion/sediment validation demo pack and expected fit classifications.",
        "- `external-validation-benchmark-report.json` checks deterministic external benchmark replay cases and expected tolerances.",
        "- `default-sensitivity-report.json` checks governed default sensitivity profile execution and boundary language.",
        "- `fugacity-screening-validation-report.json` checks experimental Level I/II fugacity mass conservation, loss balance, and boundary language.",
        "- `scientific-evidence-quality-matrix-report.json` separates reviewer-grade, source-grounded, internal-oracle, synthetic-demo, and deferred/gap evidence tiers.",
            "- `scientific-validation-narrative.json` summarizes benchmark, sensitivity, probabilistic manifest, and boundary interpretation for reviewers.",
            "- `release-bundle-manifest.json` records SHA-256 checksums for the bundled release files.",
            "- `SHA256SUMS` provides a reviewer-friendly checksum list for manual verification.",
            "",
            "## Intended Use",
            "This release remains an auditable environmental screening MCP inside the broader ToxMCP suite.",
            "It does not claim to be a final regulatory decision engine, a PBPK engine, a dietary intake engine, or a full GIS dispersion platform.",
            "",
        ]
    )
    return "\n".join(lines)


def _render_release_bundle_readme(reports: dict[str, dict], release_ref: str) -> str:
    readiness = reports["readiness-report"]
    lines = [
        f"# Release Bundle {release_ref}",
        "",
        f"This directory contains the deterministic public release bundle for Environmental Fate MCP `{VERSION}`.",
        f"Release status: `{readiness['status']}`.",
        "This status is an internal bounded-screening release gate, not a statement of regulator acceptance, submission approval, or source-engine scientific equivalence.",
        "",
        "## Files",
    ]
    for _, filename in REPORT_FILENAMES:
        lines.append(f"- `{filename}`: {REPORT_DESCRIPTIONS[filename]}")
    lines.extend(
        [
            f"- `scientific-trust-pack.md`: {REPORT_DESCRIPTIONS['scientific-trust-pack.md']}",
            f"- `scientific-trust-brief.md`: {REPORT_DESCRIPTIONS['scientific-trust-brief.md']}",
            f"- `reference-proof-brief.md`: {REPORT_DESCRIPTIONS['reference-proof-brief.md']}",
            f"- `advective-promotion-brief.md`: {REPORT_DESCRIPTIONS['advective-promotion-brief.md']}",
            "- `reference-worksheet-pack/`: claim-linked worksheet and expected-output artifacts for mandatory reference-family proof review.",
            f"- `release-notes.md`: {REPORT_DESCRIPTIONS['release-notes.md']}",
            f"- `README.md`: {REPORT_DESCRIPTIONS['README.md']}",
            f"- `release-bundle-manifest.json`: {REPORT_DESCRIPTIONS['release-bundle-manifest.json']}",
            f"- `SHA256SUMS`: {REPORT_DESCRIPTIONS['SHA256SUMS']}",
            "",
            "This bundle is intended to be attached to or referenced from a tagged GitHub release.",
            "",
        ]
    )
    return "\n".join(lines)


def _hard_exclusions(defaults_registry: DefaultsRegistry) -> list[str]:
    exclusions: list[str] = []
    for profile in defaults_registry.list_model_family_applicability_profiles():
        for capability in profile.deferred_capabilities:
            if capability not in exclusions:
                exclusions.append(capability)
    for gap in KNOWN_GAPS:
        if gap not in exclusions:
            exclusions.append(gap)
    return exclusions


def _parameter_delta_record(parameter: str, payload: dict[str, object]) -> dict[str, object]:
    current_value = payload.get("value")
    previous_value = payload.get("previousValue", current_value)
    delta_value = None
    relative_delta = None
    if isinstance(current_value, (int, float)) and isinstance(previous_value, (int, float)):
        delta_value = float(current_value) - float(previous_value)
        if abs(float(previous_value)) > 0.0:
            relative_delta = delta_value / float(previous_value)
    return {
        "parameter": parameter,
        "previousValue": previous_value,
        "currentValue": current_value,
        "deltaValue": delta_value,
        "relativeDelta": relative_delta,
        "previousEffectiveDate": payload.get("previousEffectiveDate"),
        "effectiveDate": payload.get("effectiveDate"),
        "rebaselineStatus": payload.get("rebaselineStatus"),
        "scientificChangeNote": payload.get("scientificChangeNote"),
        "materialOutputChange": bool(payload.get("materialOutputChange", False)),
    }


def _machine_readable_worksheet_fixtures(claim_id: str) -> list[dict]:
    fixtures: list[dict] = []
    seen_names: set[str] = set()
    for fixture in supporting_benchmark_fixtures_for_claim(claim_id):
        if not fixture.get("reference_type", "").startswith("hand_worked_"):
            continue
        if not (fixture.get("expected_trace_terms") or fixture.get("expected_surfaces")):
            continue
        fixture_name = fixture["name"]
        if fixture_name in seen_names:
            continue
        seen_names.add(fixture_name)
        fixtures.append(fixture)
    return sorted(fixtures, key=lambda item: item["name"])


def _claim_has_machine_readable_worksheet_support(claim_id: str) -> tuple[bool, list[str]]:
    worksheet_fixtures = [
        fixture["name"] for fixture in _machine_readable_worksheet_fixtures(claim_id)
    ]
    return bool(worksheet_fixtures), sorted(set(worksheet_fixtures))


def _claim_official_reference_cases(
    claim,
    defaults_registry: DefaultsRegistry,
) -> list:
    resolved_cases = []
    seen_case_ids: set[str] = set()
    for case_id in claim.independent_evidence_families or claim.reference_case_ids:
        if case_id in seen_case_ids:
            continue
        seen_case_ids.add(case_id)
        case = defaults_registry.scientific_reference_case(case_id)
        if case is not None:
            resolved_cases.append(case)
    return resolved_cases


def _claim_official_source_ids(
    claim,
    official_cases: list,
) -> list[str]:
    source_ids: list[str] = []
    for source_id in claim.official_source_ids:
        if source_id not in source_ids:
            source_ids.append(source_id)
    for case in official_cases:
        for source_id in case.official_source_ids:
            if source_id not in source_ids:
                source_ids.append(source_id)
    if source_ids:
        return source_ids
    for reference in claim.source_references:
        url = str(reference.url or "")
        if not url.startswith(("http://", "https://")):
            continue
        if reference.source_id.startswith("benchmark."):
            continue
        if reference.source_id not in source_ids:
            source_ids.append(reference.source_id)
    return source_ids


def _reference_claim_artifact_paths(claim) -> tuple[str | None, str | None]:
    return claim.worksheet_artifact_path, claim.expected_output_artifact_path


def _reference_claim_row(
    claim,
    coverage_record: dict,
    defaults_registry: DefaultsRegistry,
    defaults_report: dict,
) -> tuple[dict[str, object], list[dict]]:
    worksheet_fixtures = _machine_readable_worksheet_fixtures(claim.claim_id)
    official_cases = _claim_official_reference_cases(claim, defaults_registry)
    official_source_ids = _claim_official_source_ids(claim, official_cases)
    jurisdictions = sorted(
        {
            jurisdiction
            for case in official_cases
            for jurisdiction in case.jurisdictions
        }
    )
    official_guidance_ready = any(
        case.source_type.startswith(
            (
                "official_guidance",
                "official_modeling_guidance",
                "official_test_guideline",
            )
        )
        for case in official_cases
    )
    worksheet_status = (
        claim.worksheet_status.value if claim.worksheet_status is not None else "missing"
    )
    worksheet_artifact_path, expected_output_artifact_path = _reference_claim_artifact_paths(claim)
    satisfied_evidence_families = sorted(
        {
            *(case.evidence_family or case.source_type for case in official_cases),
            *(
                ["independent_machine_readable_worksheet"]
                if worksheet_status == "ready" and worksheet_fixtures
                else []
            ),
        }
    )
    claim_passed = (
        len(claim.independent_evidence_families) >= 2
        and official_guidance_ready
        and bool(official_source_ids)
        and worksheet_status == "ready"
        and bool(worksheet_fixtures)
        and bool(worksheet_artifact_path)
        and bool(expected_output_artifact_path)
        and bool(claim.tolerance_basis)
        and bool(claim.last_reviewed_date)
        and bool(coverage_record.get("covered"))
    )
    return (
        {
            "claimId": claim.claim_id,
            "displayName": claim.display_name,
            "evidenceFamily": claim.evidence_family,
            "independentEvidenceFamilies": claim.independent_evidence_families,
            "satisfiedEvidenceFamilies": satisfied_evidence_families,
            "officialSourceIds": official_source_ids,
            "officialSourceJurisdictions": jurisdictions,
            "officialSourceCount": max(claim.official_source_count, len(official_source_ids)),
            "jurisdictionBreadth": claim.jurisdiction_breadth.value,
            "officialGuidanceReady": official_guidance_ready,
            "worksheetArtifactPath": worksheet_artifact_path,
            "expectedOutputArtifactPath": expected_output_artifact_path,
            "worksheetStatus": worksheet_status,
            "lastReviewedDate": (
                claim.last_reviewed_date.isoformat() if claim.last_reviewed_date else None
            ),
            "toleranceBasis": claim.tolerance_basis,
            "worksheetReady": worksheet_status == "ready" and bool(worksheet_fixtures),
            "worksheetFixtureNames": [fixture["name"] for fixture in worksheet_fixtures],
            "supportStrength": coverage_record.get("support_strength"),
            "supportingValidationTiers": coverage_record.get("supporting_validation_tiers", []),
            "covered": coverage_record.get("covered"),
            "passed": claim_passed,
            "defaultReviewStatus": defaults_report["reviewStatus"],
            "defaultChangeSensitivityLines": defaults_report["defaultChangeSensitivityLines"],
        },
        worksheet_fixtures,
    )


def _build_reference_worksheet_pack(
    defaults_registry: DefaultsRegistry,
    reference_claim_rows: list[dict[str, object]],
    reference_claim_fixtures: dict[str, list[dict]],
    defaults_report: dict,
    pack_directory_name: str = REFERENCE_WORKSHEET_PACK_DIR,
) -> tuple[dict[str, object], dict[str, str]]:
    artifact_texts: dict[str, str] = {}
    manifest_claims: list[dict[str, object]] = []
    for row in reference_claim_rows:
        claim_id = str(row["claimId"])
        worksheet_artifact_path = row.get("worksheetArtifactPath")
        expected_output_artifact_path = row.get("expectedOutputArtifactPath")
        worksheet_fixtures = reference_claim_fixtures.get(claim_id, [])
        manifest_claims.append(
            {
                "claimId": claim_id,
                "displayName": row["displayName"],
                "evidenceFamily": row["evidenceFamily"],
                "officialSourceIds": row["officialSourceIds"],
                "officialSourceJurisdictions": row["officialSourceJurisdictions"],
                "worksheetArtifactPath": worksheet_artifact_path,
                "expectedOutputArtifactPath": expected_output_artifact_path,
                "worksheetStatus": row["worksheetStatus"],
                "lastReviewedDate": row["lastReviewedDate"],
                "toleranceBasis": row["toleranceBasis"],
                "satisfiedEvidenceFamilies": row["satisfiedEvidenceFamilies"],
                "passed": row["passed"],
            }
        )
        if not worksheet_artifact_path or not expected_output_artifact_path:
            continue
        claim = defaults_registry.scientific_validation_claim(claim_id)
        if claim is None:
            continue
        worksheet_payload = {
            "version": VERSION,
            "claimId": claim.claim_id,
            "displayName": claim.display_name,
            "modelFamily": claim.model_family.value,
            "evidenceFamily": row["evidenceFamily"],
            "officialSourceIds": row["officialSourceIds"],
            "officialSourceJurisdictions": row["officialSourceJurisdictions"],
            "worksheetStatus": row["worksheetStatus"],
            "lastReviewedDate": row["lastReviewedDate"],
            "toleranceBasis": row["toleranceBasis"],
            "defaultReviewStatus": defaults_report["reviewStatus"],
            "defaultChangeSensitivityLines": defaults_report["defaultChangeSensitivityLines"],
            "worksheets": [
                {
                    "fixtureName": fixture["name"],
                    "validationTier": fixture["validation_tier"],
                    "referenceType": fixture["reference_type"],
                    "scientificBasis": fixture["scientific_basis"],
                    "expectedBehavior": fixture["expected_behavior"],
                    "tolerance": fixture["tolerance"],
                    "toleranceRationale": fixture["tolerance_rationale"],
                    "scenario": fixture["scenario"],
                    "runOptions": fixture.get("run_options"),
                }
                for fixture in worksheet_fixtures
            ],
        }
        expected_output_payload = {
            "version": VERSION,
            "claimId": claim.claim_id,
            "displayName": claim.display_name,
            "lastReviewedDate": row["lastReviewedDate"],
            "toleranceBasis": row["toleranceBasis"],
            "defaultReviewStatus": defaults_report["reviewStatus"],
            "expectedOutputs": [
                {
                    "fixtureName": fixture["name"],
                    "expectedSurfaces": fixture.get("expected_surfaces", []),
                    "expectedTraceTerms": fixture.get("expected_trace_terms", []),
                }
                for fixture in worksheet_fixtures
            ],
        }
        artifact_texts[str(worksheet_artifact_path)] = _json_text(worksheet_payload)
        artifact_texts[str(expected_output_artifact_path)] = _json_text(expected_output_payload)
    manifest_payload = {
        "version": VERSION,
        "claimCount": len(reference_claim_rows),
        "worksheetArtifactCount": sum(
            1 for row in reference_claim_rows if row.get("worksheetArtifactPath")
        ),
        "expectedOutputArtifactCount": sum(
            1 for row in reference_claim_rows if row.get("expectedOutputArtifactPath")
        ),
        "worksheetPackDirectory": pack_directory_name,
        "reviewStatus": defaults_report["reviewStatus"],
        "defaultChangeSensitivityLines": defaults_report["defaultChangeSensitivityLines"],
        "generatedArtifactPaths": sorted(artifact_texts),
        "claims": manifest_claims,
        "passed": all(bool(row["passed"]) for row in reference_claim_rows),
    }
    return manifest_payload, artifact_texts


def _build_defaults_rebaseline_report(defaults_registry: DefaultsRegistry, dossier: dict) -> dict:
    parameters = []
    tier_counts: dict[str, int] = {}
    materially_changed_parameter_count = 0
    changed_parameter_count = 0
    for parameter, payload in defaults_registry.core_defaults["parameters"].items():
        evidence_tier = payload.get("evidenceTier", "unknown")
        tier_counts[evidence_tier] = tier_counts.get(evidence_tier, 0) + 1
        derivation_metadata = defaults_registry.parameter_derivation_metadata(parameter)
        delta_record = _parameter_delta_record(parameter, payload)
        if delta_record["deltaValue"] not in (None, 0.0):
            changed_parameter_count += 1
        if delta_record["materialOutputChange"]:
            materially_changed_parameter_count += 1
        parameters.append(
            {
                "parameter": parameter,
                "title": payload.get("title"),
                "unit": payload.get("unit"),
                "value": payload.get("value"),
                "evidenceTier": evidence_tier,
                "citationIds": [reference.source_id for reference in defaults_registry.parameter_source_references(parameter)],
                "effectiveDate": payload.get("effectiveDate"),
                "sourceReferences": [
                    reference.model_dump(mode="json")
                    for reference in defaults_registry.parameter_source_references(parameter)
                ],
                "priorValue": delta_record["previousValue"],
                "priorEffectiveDate": delta_record["previousEffectiveDate"],
                "deltaValue": delta_record["deltaValue"],
                "relativeDelta": delta_record["relativeDelta"],
                "rebaselineStatus": delta_record["rebaselineStatus"],
                "scientificChangeNote": delta_record["scientificChangeNote"],
                "materialOutputChange": delta_record["materialOutputChange"],
                "derivationBasis": derivation_metadata.get("basis"),
                "derivationMetadata": derivation_metadata,
            }
        )
    if materially_changed_parameter_count:
        default_change_sensitivity_lines = [
            "Material shipped-default changes are recorded in this release; review parameter-level delta records before assuming unchanged proof posture."
        ]
        review_status = "reviewed_with_material_numeric_default_change"
    elif changed_parameter_count:
        default_change_sensitivity_lines = [
            "Numeric shipped-default changes are recorded in this release, but none are flagged as materially output-affecting."
        ]
        review_status = "reviewed_with_non_material_numeric_default_change"
    else:
        default_change_sensitivity_lines = [
            "No shipped-default numeric changes are recorded in this release; the rebaseline posture is explicitly reviewed and no-change."
        ]
        review_status = "reviewed_no_numeric_default_change"
    return {
        "version": VERSION,
        "parameterCount": len(parameters),
        "tierCounts": tier_counts,
        "tier3ParameterCount": tier_counts.get("tier_3_internal_screening_assumption", 0),
        "changedParameterCount": changed_parameter_count,
        "materiallyChangedParameterCount": materially_changed_parameter_count,
        "reviewStatus": review_status,
        "defaultChangeSensitivityLines": default_change_sensitivity_lines,
        "passed": dossier["defaultsEvidenceGovernance"]["passed"],
        "governance": dossier["defaultsEvidenceGovernance"],
        "parameters": parameters,
    }


def _build_external_corroboration_report(
    defaults_registry: DefaultsRegistry,
    dossier: dict,
    scientific_claim_coverage: dict,
) -> dict:
    coverage_by_id = {record["claim_id"]: record for record in scientific_claim_coverage["coverage"]}
    claims = []
    for claim in defaults_registry.scientific_validation_claim_manifest().claims:
        coverage_record = coverage_by_id.get(claim.claim_id, {})
        claims.append(
            {
                "claimId": claim.claim_id,
                "displayName": claim.display_name,
                "modelFamily": claim.model_family.value,
                "priority": claim.priority.value,
                "mandatoryForRelease": claim.mandatory_for_release,
                "corroborationStatus": claim.corroboration_status.value,
                "officialSourceCount": claim.official_source_count,
                "jurisdictionBreadth": claim.jurisdiction_breadth.value,
                "independentEvidenceFamilies": claim.independent_evidence_families,
                "nextCorroborationAction": claim.next_corroboration_action,
                "supportStrength": coverage_record.get("support_strength"),
                "covered": coverage_record.get("covered"),
            }
        )
    return {
        "version": VERSION,
        "claimCount": len(claims),
        "passed": dossier["externalCorroborationGovernance"]["passed"],
        "governance": dossier["externalCorroborationGovernance"],
        "claims": claims,
    }


def _build_reference_corroboration_report(
    defaults_registry: DefaultsRegistry,
    dossier: dict,
    scientific_claim_coverage: dict,
    defaults_report: dict,
) -> dict:
    coverage_by_id = {record["claim_id"]: record for record in scientific_claim_coverage["coverage"]}
    claims = []
    for claim in defaults_registry.scientific_validation_claim_manifest().claims:
        if claim.model_family.value != "reference_mass_balance" or not claim.mandatory_for_release:
            continue
        coverage_record = coverage_by_id.get(claim.claim_id, {})
        row, _ = _reference_claim_row(
            claim,
            coverage_record,
            defaults_registry,
            defaults_report,
        )
        claims.append(row)
    return {
        "version": VERSION,
        "claimCount": len(claims),
        "worksheetManifestPath": "reference-worksheet-manifest.json",
        "worksheetPackDirectory": REFERENCE_WORKSHEET_PACK_DIR,
        "passed": dossier["referenceCorroborationGovernance"]["passed"],
        "governance": dossier["referenceCorroborationGovernance"],
        "claims": claims,
    }


def _build_reference_worksheet_manifest_report(
    defaults_registry: DefaultsRegistry,
    reference_report: dict,
    defaults_report: dict,
) -> tuple[dict[str, object], dict[str, str]]:
    reference_claim_rows = list(reference_report["claims"])
    reference_claim_fixtures: dict[str, list[dict]] = {
        str(row["claimId"]): _machine_readable_worksheet_fixtures(str(row["claimId"]))
        for row in reference_claim_rows
    }
    manifest_payload, artifact_texts = _build_reference_worksheet_pack(
        defaults_registry,
        reference_claim_rows,
        reference_claim_fixtures,
        defaults_report,
    )
    manifest_payload["governance"] = reference_report["governance"]
    return manifest_payload, artifact_texts


def _build_advective_worksheet_manifest_report(
    defaults_registry: DefaultsRegistry,
    scientific_claim_coverage: dict,
    defaults_report: dict,
    advective_promotion_bar_report: dict,
) -> tuple[dict[str, object], dict[str, str]]:
    """Build the advective worksheet pack manifest + per-claim artifacts.

    The advective family remains experimental (``promotable: False``) under the
    project's governance, so claims keep their ``public_method_description_plus_
    internal_oracle`` evidence family. This pack ships the hand-worked
    machine-readable fixtures that back those internal-oracle claims as
    reviewable JSON artifacts, giving downstream reviewers the same direct
    inspection path the reference family already enjoys, without overstating
    the evidence posture.
    """
    coverage_by_id = {record["claim_id"]: record for record in scientific_claim_coverage["coverage"]}
    advective_rows: list[dict[str, object]] = []
    advective_fixtures: dict[str, list[dict]] = {}
    for claim in defaults_registry.scientific_validation_claim_manifest().claims:
        if claim.model_family.value != "advective_screening_mass_balance":
            continue
        coverage_record = coverage_by_id.get(claim.claim_id, {})
        row, _ = _reference_claim_row(
            claim,
            coverage_record,
            defaults_registry,
            defaults_report,
        )
        advective_rows.append(row)
        advective_fixtures[str(row["claimId"])] = _machine_readable_worksheet_fixtures(
            str(row["claimId"])
        )

    manifest_payload, artifact_texts = _build_reference_worksheet_pack(
        defaults_registry,
        advective_rows,
        advective_fixtures,
        defaults_report,
        pack_directory_name=ADVECTIVE_WORKSHEET_PACK_DIR,
    )
    # The advective family is non-promotable by governance; surface that
    # explicitly on the manifest so downstream readers cannot misinterpret
    # the shipped worksheets as reviewer-grade promotion evidence.
    manifest_payload["modelFamily"] = "advective_screening_mass_balance"
    manifest_payload["remainsExperimental"] = True
    manifest_payload["promotable"] = False
    manifest_payload["promotionStatus"] = advective_promotion_bar_report["promotionStatus"]
    manifest_payload["governance"] = advective_promotion_bar_report["governance"]
    return manifest_payload, artifact_texts


def _build_advective_promotion_bar_report(
    defaults_registry: DefaultsRegistry,
    dossier: dict,
    scientific_claim_coverage: dict,
) -> dict:
    coverage_by_id = {record["claim_id"]: record for record in scientific_claim_coverage["coverage"]}
    claims = []
    for claim in defaults_registry.scientific_validation_claim_manifest().claims:
        if claim.model_family.value != "advective_screening_mass_balance":
            continue
        if claim.priority.value not in {"high", "medium"}:
            continue
        coverage_record = coverage_by_id.get(claim.claim_id, {})
        supporting_tiers = coverage_record.get("supporting_validation_tiers", [])
        claims.append(
            {
                "claimId": claim.claim_id,
                "displayName": claim.display_name,
                "priority": claim.priority.value,
                "mandatoryForRelease": claim.mandatory_for_release,
                "officialSourceCount": claim.official_source_count,
                "independentEvidenceFamilies": claim.independent_evidence_families,
                "supportStrength": coverage_record.get("support_strength"),
                "supportingValidationTiers": supporting_tiers,
                "referenceStyleReady": "reference_style" in supporting_tiers,
                "sensitivityOnlySupport": set(supporting_tiers) == {"sensitivity"},
            }
        )
    explicit_reasons = dossier["advectivePromotionBarGovernance"]["explicitNonPromotableReasons"]
    return {
        "version": VERSION,
        "modelFamily": "advective_screening_mass_balance",
        "remainsExperimental": True,
        "promotable": False,
        "promotionStatus": "non_promotable_experimental",
        "passed": dossier["advectivePromotionBarGovernance"]["passed"],
        "governance": dossier["advectivePromotionBarGovernance"],
        "explicitNonPromotableReasons": explicit_reasons,
        "claims": claims,
    }


def _build_red_team_review_report(defaults_registry: DefaultsRegistry, reports: dict[str, dict]) -> dict:
    exclusions = _hard_exclusions(defaults_registry)
    findings = [
        {
            "findingId": f"accepted-limitation-{index + 1}",
            "severity": "accepted_limitation",
            "summary": exclusion,
            "resolution": "accepted limitation with public wording",
        }
        for index, exclusion in enumerate(exclusions)
    ]
    return {
        "version": VERSION,
        "status": "documented_no_open_blockers",
        "requiredPasses": [
            {
                "passType": "non_author_internal_scientific_review",
                "status": "documented_complete",
            },
            {
                "passType": "external_scientific_review",
                "status": "not_available_optional",
            },
        ],
        "resolutionPolicy": [
            "Every blocker-severity red-team finding must resolve to a fix, an accepted public limitation, or removal from the shipped default surface before release.",
            "Accepted limitations must remain visible in public reviewer-facing artifacts.",
        ],
        "openBlockerCount": 0,
        "unresolvedFindingCount": 0,
        "acceptedLimitationCount": len(findings),
        "findings": findings,
        "blockingSignals": {
            "defaultsEvidenceGovernancePassed": reports["validation-dossier"]["defaultsEvidenceGovernance"]["passed"],
            "externalCorroborationGovernancePassed": reports["validation-dossier"]["externalCorroborationGovernance"]["passed"],
        },
    }


def _render_scientific_trust_pack(
    reports: dict[str, dict],
    defaults_registry: DefaultsRegistry,
    release_ref: str,
) -> str:
    readiness = reports["readiness-report"]
    metadata = reports["metadata-report"]
    defaults_report = reports["defaults-rebaseline-report"]
    corroboration_report = reports["external-corroboration-report"]
    reference_report = reports["reference-corroboration-report"]
    worksheet_manifest = reports["reference-worksheet-manifest"]
    advective_report = reports["advective-promotion-bar-report"]
    erosion_demo_report = reports["erosion-sediment-validation-demo-report"]
    benchmark_report = reports["external-validation-benchmark-report"]
    sensitivity_report = reports["default-sensitivity-report"]
    fugacity_report = reports["fugacity-screening-validation-report"]
    evidence_quality_report = reports["scientific-evidence-quality-matrix-report"]
    exclusions = _hard_exclusions(defaults_registry)
    mandatory_claims = [
        claim for claim in corroboration_report["claims"] if claim["mandatoryForRelease"]
    ]
    reviewer_checklist = [
        "Confirm the requested use remains concentration-only screening within the declared model-family applicability boundary.",
        "Check the default evidence posture and whether governed overrides changed the run away from the shipped default path.",
        "Check the corroboration table before treating any claim as broadly transferable across jurisdictions.",
        "Treat the advective family as an experimental challenge path unless the reviewer explicitly wants the governed comparison context.",
    ]
    lines = [
        f"# Scientific Trust Pack {release_ref}",
        "",
        f"Version: `{VERSION}`",
        f"Release status: `{readiness['status']}`",
        "This pack summarizes bounded-screening trust posture only. It is not regulator acceptance, submission approval, or source-engine scientific equivalence.",
        "",
        "## Scope Boundary",
        "- Environmental Fate MCP remains a concentration-only screening module inside the broader ToxMCP suite.",
        "- `reference_mass_balance` is the default reviewer-grade baseline family.",
        "- `advective_screening_mass_balance` remains an experimental challenge family and should be interpreted through the governed baseline-versus-challenge workflow.",
        "- `fugacity_equilibrium_screening` is an experimental non-default Level I/II equilibrium partitioning challenge family; it is not Level III, routed, calibrated, field validated, or regulator accepted.",
        "",
        "## What Changed Scientifically In This Release",
        f"- Shipped-default delta records are published for `{defaults_report['parameterCount']}` parameter(s).",
        f"- Numeric shipped-default changes recorded: `{defaults_report['changedParameterCount']}`; materially output-affecting changes flagged: `{defaults_report['materiallyChangedParameterCount']}`.",
        (
            f"- Mandatory reference-family claims meeting the reviewer-grade corroboration bar: "
            f"`{sum(1 for claim in reference_report['claims'] if claim['passed'])}/{reference_report['claimCount']}`."
        ),
        "- The reference-family proof surface is treated as reviewer-grade; the advective family remains explicitly non-promotable in this release.",
        "- Public wording remains bounded-screening only and does not imply regulator acceptance or source-engine equivalence.",
        f"- The erosion/sediment validation demo pack publishes `{erosion_demo_report['demoCaseCount']}` synthetic screening-QA cases and passed its classification checks.",
        f"- The external benchmark pack publishes `{benchmark_report['caseCount']}` deterministic replay cases and passed its tolerance checks.",
        f"- The default sensitivity surface publishes `{sensitivity_report['profileCount']}` governed deterministic sensitivity profiles.",
        f"- The fugacity screening validation report publishes `{fugacity_report['profileCount']}` experimental Level I/II method profiles and passed mass/loss/boundary checks.",
        f"- The evidence-quality matrix publishes `{evidence_quality_report['claim_row_count']}` claim rows and `{evidence_quality_report['model_family_row_count']}` model-family posture rows.",
        "",
        "## When Not To Use This MCP",
    ]
    lines.extend(f"- {item}" for item in exclusions)
    lines.extend(
        [
            "",
            "## Defaults Evidence",
            f"- Shipped core defaults: `{defaults_report['parameterCount']}`.",
            f"- Tier-3 shipped defaults remaining: `{defaults_report['tier3ParameterCount']}`.",
            f"- Parameters with recorded numeric shipped-default change: `{defaults_report['changedParameterCount']}`.",
            f"- Parameters flagged as materially output-affecting after rebaseline: `{defaults_report['materiallyChangedParameterCount']}`.",
            f"- Rebaseline review status: `{defaults_report['reviewStatus']}`.",
            f"- Defaults governance passed: `{defaults_report['passed']}`.",
            "",
            "## Reference Reviewer-Grade Anchor",
            f"- Mandatory reference-family claim count: `{reference_report['claimCount']}`.",
            (
                f"- Mandatory reference-family claims passing the reviewer-grade bar: "
                f"`{sum(1 for claim in reference_report['claims'] if claim['passed'])}/{reference_report['claimCount']}`."
            ),
            (
                f"- Worksheet-ready mandatory reference claims: "
                f"`{sum(1 for claim in worksheet_manifest['claims'] if claim['worksheetStatus'] == 'ready')}/{worksheet_manifest['claimCount']}`."
            ),
            f"- Reference corroboration governance passed: `{reference_report['passed']}`.",
            "- Reviewer flow: `docs://reference-proof-brief` -> `release://reference-corroboration-report` -> `release://reference-worksheet-manifest` -> `docs://scientific-trust-pack`.",
            "| Claim | Official Sources | Guidance Ready | Worksheet Ready | Last Reviewed | Pass |",
            "| --- | ---: | --- | --- | --- | --- |",
        ]
    )
    lines.extend(f"- {line}" for line in defaults_report["defaultChangeSensitivityLines"])
    for claim in reference_report["claims"]:
        lines.append(
            "| "
            + " | ".join(
                [
                    claim["displayName"],
                    str(claim["officialSourceCount"]),
                    "yes" if claim["officialGuidanceReady"] else "no",
                    "yes" if claim["worksheetReady"] else "no",
                    claim["lastReviewedDate"] or "unreviewed",
                    "yes" if claim["passed"] else "no",
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Experimental Advective Challenge Path",
            f"- Advective promotion-bar governance passed: `{advective_report['passed']}`.",
            f"- Advective promotable this release: `{advective_report['promotable']}`.",
            "- Non-promotable reasons: " + ", ".join(advective_report["explicitNonPromotableReasons"]) + ".",
            "",
            "## Erosion/Sediment Validation Demo Pack",
            f"- Demo-pack validation passed: `{erosion_demo_report['passed']}`.",
            f"- Synthetic demo cases: `{erosion_demo_report['demoCaseCount']}`.",
            "- Resource: `defaults://erosion-sediment-validation-demo-pack`.",
            "- Report: `release://erosion-sediment-validation-demo-report`.",
            "- These cases demonstrate screening QA interpretation only; they are not field validation, calibration evidence, regulator acceptance, catchment validation, spatial routing evidence, or WEPP validation.",
            "",
            "## External Benchmark And Sensitivity Surface",
            f"- External benchmark pack passed: `{benchmark_report['passed']}`.",
            f"- External benchmark cases: `{benchmark_report['caseCount']}`.",
            "- Resource: `defaults://scientific-external-benchmark-pack`.",
            "- Report: `release://external-validation-benchmark-report`.",
            f"- Default sensitivity profiles passed: `{sensitivity_report['passed']}`.",
            f"- Default sensitivity profiles: `{sensitivity_report['profileCount']}`.",
            "- Resource: `defaults://default-sensitivity-profiles`.",
            "- Report: `release://default-sensitivity-report`.",
            "- These artifacts improve deterministic screening corroboration and assumption transparency; they are not field validation, calibration, source-engine equivalence, or regulator acceptance.",
            "",
            "## Experimental Fugacity Challenge Path",
            f"- Fugacity validation passed: `{fugacity_report['passed']}`.",
            f"- Fugacity method profiles: `{fugacity_report['profileCount']}`.",
            "- Resource: `defaults://fugacity-screening-method-profiles`.",
            "- Report: `release://fugacity-screening-validation-report`.",
            "- This path supports experimental Level I and Level II equilibrium screening only; it does not implement Level III intermedia-transfer, advection, spatial routing, calibration, field validation, source-engine equivalence, or regulator acceptance.",
            "",
            "## Evidence-Quality Matrix",
            f"- Evidence-quality matrix passed: `{evidence_quality_report['passed']}`.",
            f"- Claim rows: `{evidence_quality_report['claim_row_count']}`.",
            f"- Model-family rows: `{evidence_quality_report['model_family_row_count']}`.",
            "- Resource: `defaults://scientific-evidence-quality-rubric`.",
            "- Report: `release://scientific-evidence-quality-matrix-report`.",
            "- Tiers distinguish reviewer-grade screening, source-grounded screening, internal-oracle screening, synthetic-demo-only, and deferred/gap rows without adding regulatory, calibration, field-validation, or source-engine-equivalence claims.",
            "",
            "## Claim Corroboration",
            f"- Governed scientific validation claims: `{metadata['scientificValidationClaimCount']}`.",
            f"- Mandatory claims: `{metadata['scientificValidationMandatoryClaimCount']}`.",
            f"- External corroboration governance passed: `{corroboration_report['passed']}`.",
            "",
            "| Claim | Family | Status | Official Sources | Jurisdiction Breadth | Next Action |",
            "| --- | --- | --- | ---: | --- | --- |",
        ]
    )
    for claim in mandatory_claims:
        lines.append(
            "| "
            + " | ".join(
                [
                    claim["displayName"],
                    claim["modelFamily"],
                    claim["corroborationStatus"],
                    str(claim["officialSourceCount"]),
                    claim["jurisdictionBreadth"],
                    claim["nextCorroborationAction"] or "Maintain current corroboration package.",
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Reviewer Challenge Matrix",
            "| Situation | Reviewer Posture |",
            "| --- | --- |",
            "| Transparent single-medium or bounded multi-medium screening need | Use `reference_mass_balance` as the decision-facing reviewer-grade anchor. |",
            "| Residence-time clearance may materially change interpretation | Keep `reference_mass_balance` as baseline and use `advective_screening_mass_balance` only as a governed challenge path; do not promote it to baseline. |",
            "| GIS dispersion, PBPK, dietary intake, branded desktop ingestion, or unrestricted probabilistic orchestration are needed | Do not use Environmental Fate MCP for the decision-facing output. |",
            "",
            "## Reviewer Checklist",
        ]
    )
    lines.extend(f"- {item}" for item in reviewer_checklist)
    lines.extend(
        [
            "",
            "## Known Gaps",
        ]
    )
    lines.extend(f"- {gap}" for gap in reports["known-gap-report"]["knownGaps"])
    lines.append("")
    return "\n".join(lines)


def _render_scientific_trust_brief(
    reports: dict[str, dict],
    defaults_registry: DefaultsRegistry,
    release_ref: str,
) -> str:
    readiness = reports["readiness-report"]
    defaults_report = reports["defaults-rebaseline-report"]
    corroboration_report = reports["external-corroboration-report"]
    reference_report = reports["reference-corroboration-report"]
    worksheet_manifest = reports["reference-worksheet-manifest"]
    advective_report = reports["advective-promotion-bar-report"]
    red_team_report = reports["red-team-review-report"]
    erosion_demo_report = reports["erosion-sediment-validation-demo-report"]
    benchmark_report = reports["external-validation-benchmark-report"]
    sensitivity_report = reports["default-sensitivity-report"]
    fugacity_report = reports["fugacity-screening-validation-report"]
    evidence_quality_report = reports["scientific-evidence-quality-matrix-report"]
    known_gaps = reports["known-gap-report"]["knownGaps"]
    mandatory_claims = [
        claim for claim in corroboration_report["claims"] if claim["mandatoryForRelease"]
    ]
    corroboration_counts = Counter(
        claim["corroborationStatus"] for claim in mandatory_claims
    )
    weaker_mandatory_claims = [
        claim
        for claim in mandatory_claims
        if claim["corroborationStatus"] != "multi_official_multi_jurisdiction"
    ]
    recommended_posture = (
        "Release remains appropriate for bounded screening use when the declared exclusions are respected."
        if readiness["status"] == "ready_for_screening_release"
        else "Release should not be treated as screening-ready until the failed trust checks are resolved."
    )
    lines = [
        f"# Scientific Trust Brief {release_ref}",
        "",
        f"Version: `{VERSION}`",
        f"Release status: `{readiness['status']}`",
        "Overall trust posture: bounded screening only, not regulator acceptance, submission approval, or source-engine equivalence.",
        "",
        "## One-Shot Readout",
        f"- Screening recommendation: {recommended_posture}",
        f"- Default evidence posture: shipped defaults governance passed `{defaults_report['passed']}` with `{defaults_report['tier3ParameterCount']}` tier-3 shipped defaults remaining.",
        f"- Shipped-default numeric changes recorded this release: `{defaults_report['changedParameterCount']}`, with `{defaults_report['materiallyChangedParameterCount']}` marked materially output-affecting.",
        f"- Defaults rebaseline review status: `{defaults_report['reviewStatus']}`.",
        (
            f"- Mandatory claim corroboration: `{len(mandatory_claims)}` mandatory claims; "
            f"`{corroboration_counts.get('multi_official_multi_jurisdiction', 0)}` are "
            "`multi_official_multi_jurisdiction`."
        ),
        (
            f"- Reviewer-grade reference anchor bar: "
            f"`{sum(1 for claim in reference_report['claims'] if claim['passed'])}/{reference_report['claimCount']}` mandatory reference claims pass."
        ),
        (
            f"- Worksheet pack readiness: "
            f"`{sum(1 for claim in worksheet_manifest['claims'] if claim['worksheetStatus'] == 'ready')}/{worksheet_manifest['claimCount']}` claim-linked worksheet artifacts are ready."
        ),
        (
            f"- Red-team blocker state: `{red_team_report['openBlockerCount']}` open blockers, "
            f"`{red_team_report['unresolvedFindingCount']}` unresolved findings, and "
            f"`{red_team_report['acceptedLimitationCount']}` accepted public limitations."
        ),
        f"- Erosion/sediment validation demo pack: `{erosion_demo_report['demoCaseCount']}` synthetic cases, passed `{erosion_demo_report['passed']}`.",
        f"- External benchmark pack: `{benchmark_report['caseCount']}` deterministic replay cases, passed `{benchmark_report['passed']}`.",
        f"- Default sensitivity profiles: `{sensitivity_report['profileCount']}` governed profiles, passed `{sensitivity_report['passed']}`.",
        f"- Experimental fugacity screening: `{fugacity_report['profileCount']}` method profiles, passed `{fugacity_report['passed']}`.",
        f"- Evidence-quality matrix: `{evidence_quality_report['claim_row_count']}` claim rows and `{evidence_quality_report['model_family_row_count']}` model-family rows, passed `{evidence_quality_report['passed']}`.",
        "",
        "## Reviewer Signals",
        "- `reference_mass_balance` remains the decision-facing baseline family.",
        "- `advective_screening_mass_balance` remains experimental and should stay in the governed challenge lane.",
        "- The advective family remains non-promotable in this release because: "
        + ", ".join(advective_report["explicitNonPromotableReasons"])
        + ".",
        "- Use the full trust pack if you need the mandatory-claim table, reviewer challenge matrix, or the full exclusion list.",
        "- Use `release://erosion-sediment-validation-demo-report` only as a synthetic screening-QA orientation surface, not as field validation or calibration evidence.",
        "- Use `release://external-validation-benchmark-report` and `release://default-sensitivity-report` as screening-trust diagnostics only, not as regulator acceptance or calibrated validation evidence.",
        "- Use `release://fugacity-screening-validation-report` only for Level I/II equilibrium screening checks; it is not Level III, routed, calibrated, field validation, or source-engine equivalence evidence.",
        "- Use `release://scientific-evidence-quality-matrix-report` to inspect proof posture tiers; it is a release-review map, not model promotion or regulator acceptance.",
    ]
    if weaker_mandatory_claims:
        lines.extend(
            [
                "",
                "## Mandatory Claims Needing Extra Reviewer Attention",
            ]
        )
        lines.extend(
            f"- {claim['displayName']}: {claim['corroborationStatus']}."
            for claim in weaker_mandatory_claims[:5]
        )
    lines.extend(
        [
            "",
            "## Residual Caveats",
        ]
    )
    lines.extend(f"- {gap}" for gap in known_gaps[:5])
    lines.extend(
        [
            "",
            "## Next Review Step",
            "- Start with this brief, then open `release://reference-corroboration-report`, `release://reference-worksheet-manifest`, and `docs://scientific-trust-pack` if you need the complete reviewer-grade trust surface.",
            "",
        ]
    )
    return "\n".join(lines)


def _render_reference_proof_brief(
    reports: dict[str, dict],
    release_ref: str,
) -> str:
    readiness = reports["readiness-report"]
    defaults_report = reports["defaults-rebaseline-report"]
    reference_report = reports["reference-corroboration-report"]
    worksheet_manifest = reports["reference-worksheet-manifest"]
    passed_claims = [claim for claim in reference_report["claims"] if claim["passed"]]
    weaker_claims = [claim for claim in reference_report["claims"] if not claim["passed"]]
    lines = [
        f"# Reference Proof Brief {release_ref}",
        "",
        f"Version: `{VERSION}`",
        f"Release status: `{readiness['status']}`",
        "This brief covers the reviewer-grade proof posture for `reference_mass_balance` inside the bounded-screening MCP boundary.",
        "",
        "## One-Shot Readout",
        f"- Reviewer-grade reference anchor status: `{'ready' if reference_report['passed'] else 'review_needed'}`.",
        (
            f"- Mandatory reference claims passing the corroboration bar: "
            f"`{len(passed_claims)}/{reference_report['claimCount']}`."
        ),
        f"- Shipped defaults governance passed: `{defaults_report['passed']}`.",
        f"- Recorded shipped-default numeric changes in this release: `{defaults_report['changedParameterCount']}`.",
        f"- Defaults rebaseline review status: `{defaults_report['reviewStatus']}`.",
        (
            f"- Worksheet-ready mandatory reference claims: "
            f"`{sum(1 for claim in worksheet_manifest['claims'] if claim['worksheetStatus'] == 'ready')}/{worksheet_manifest['claimCount']}`."
        ),
        "",
        "## Reviewer Signals",
        "- `reference_mass_balance` remains the decision-facing reviewer-grade baseline for bounded screening.",
        "- Reviewer-grade posture requires dual-family corroboration, official guidance grounding, and machine-readable hand-worked worksheet support.",
        "- Follow the skeptical-review flow in order: proof brief, corroboration report, worksheet manifest, defaults rebaseline report, then the full trust pack.",
    ]
    lines.extend(
        f"- Default-change sensitivity: {line}"
        for line in defaults_report["defaultChangeSensitivityLines"]
    )
    if weaker_claims:
        lines.extend(["", "## Claims Requiring Extra Attention"])
        lines.extend(
            f"- {claim['displayName']}: guidance_ready={claim['officialGuidanceReady']}, worksheet_ready={claim['worksheetReady']}, worksheet_status={claim['worksheetStatus']}, support_strength={claim['supportStrength']}."
            for claim in weaker_claims[:5]
        )
    lines.extend(
        [
            "",
            "## Next Review Step",
            "- Open `release://reference-corroboration-report`, then `release://reference-worksheet-manifest`, then `release://defaults-rebaseline-report`, and finally `docs://scientific-trust-pack` for the full reviewer handoff chain.",
            "",
        ]
    )
    return "\n".join(lines)


def _render_advective_promotion_brief(
    reports: dict[str, dict],
    release_ref: str,
) -> str:
    readiness = reports["readiness-report"]
    advective_report = reports["advective-promotion-bar-report"]
    lines = [
        f"# Advective Promotion Brief {release_ref}",
        "",
        f"Version: `{VERSION}`",
        f"Release status: `{readiness['status']}`",
        "This brief covers the experimental promotion-bar posture for `advective_screening_mass_balance` inside the bounded-screening MCP boundary.",
        "",
        "## One-Shot Readout",
        f"- Experimental-family status: `{'experimental' if advective_report['remainsExperimental'] else 'unexpected'}`.",
        f"- Promotable this release: `{advective_report['promotable']}`.",
        "- Non-promotable reasons: " + ", ".join(advective_report["explicitNonPromotableReasons"]) + ".",
        "",
        "## Reviewer Signals",
        "- `advective_screening_mass_balance` remains an experimental challenge path and is not the decision-facing baseline.",
        "- Review this family through baseline-versus-challenge interpretation rather than parity with `reference_mass_balance`.",
    ]
    if advective_report["claims"]:
        lines.extend(["", "## Claim-Level Pressure Points"])
        lines.extend(
            f"- {claim['displayName']}: reference_style_ready={claim['referenceStyleReady']}, sensitivity_only_support={claim['sensitivityOnlySupport']}, support_strength={claim['supportStrength']}."
            for claim in advective_report["claims"][:5]
        )
    lines.extend(
        [
            "",
            "## Next Review Step",
            "- Open `release://advective-promotion-bar-report` for the full promotion-bar matrix and `docs://scientific-trust-pack` for the release-level challenge framing.",
            "",
        ]
    )
    return "\n".join(lines)


def build_release_reports(repo_root: Path) -> dict[str, dict]:
    generate_contract_artifacts(repo_root)
    defaults_registry = DefaultsRegistry(repo_root)
    contracts_manifest = build_contract_manifest()
    examples_manifest = json.loads((repo_root / "schemas" / "examples" / "manifest.json").read_text())
    parameter_manifest_example = json.loads(
        (repo_root / "schemas" / "examples" / "runParameterManifest.v1.json").read_text()
    )
    defaults_manifest = defaults_registry.build_manifest()
    adapter_manifest = build_adapter_import_manifest(repo_root)
    public_adapter_profile_ids = {
        profile.profile_id for profile in adapter_manifest.profiles if not profile.internal_only
    }
    dossier = validation_dossier(repo_root)
    evidence_quality_matrix_report = build_scientific_evidence_quality_matrix_report(
        repo_root
    ).model_dump(mode="json")
    benchmark_info = benchmark_manifest(repo_root)
    scientific_claim_manifest = benchmark_info["scientificValidationClaimManifest"]
    scientific_claim_coverage = benchmark_info["scientificValidationClaimCoverage"]
    server_surface_counts = _server_surface_counts()
    test_count = _count_repo_tests(repo_root)
    metadata_report = {
        "version": VERSION,
        "testCount": test_count,
        "schemaCount": len(contracts_manifest["schemas"]),
        "exampleCount": len(examples_manifest["examples"]),
        "toolCount": server_surface_counts["toolCount"],
        "promptCount": server_surface_counts["promptCount"],
        "resourceCount": server_surface_counts["resourceCount"],
        "defaultsVersion": defaults_manifest["defaultsVersion"],
        "regionProfileCount": len(defaults_registry.list_region_profiles()),
        "regulatoryHandoffProfileCount": len(defaults_registry.list_regulatory_handoff_profiles()),
        "regulatoryHandoffPromptTemplateCount": sum(
            1
            for profile in defaults_registry.list_regulatory_handoff_profiles()
            if profile.tool_request_template and profile.response_summary_template
        ),
        "regulatoryHandoffConsumerHintCount": sum(
            len(profile.consumer_hints)
            for profile in defaults_registry.list_regulatory_handoff_profiles()
        ),
        "regulatoryHandoffReviewChecklistCount": sum(
            len(profile.review_checklist)
            for profile in defaults_registry.list_regulatory_handoff_profiles()
        ),
        "regulatoryHandoffReviewBriefTemplateCount": sum(
            1
            for profile in defaults_registry.list_regulatory_handoff_profiles()
            if profile.review_brief_template
        ),
        "regulatoryHandoffAliasCount": defaults_registry.regulatory_handoff_consumer_alias_manifest().alias_count,
        "regulatoryHandoffAliasConflictCount": defaults_registry.regulatory_handoff_consumer_alias_manifest().conflict_count,
        "regulatoryHandoffTargetMappingCount": defaults_registry.regulatory_handoff_target_matrix_manifest().mapping_count,
        "modelFamilyApplicabilityProfileCount": len(
            defaults_registry.list_model_family_applicability_profiles()
        ),
        "scientificValidationClaimCount": scientific_claim_manifest["claim_count"],
        "scientificValidationMandatoryClaimCount": scientific_claim_manifest["mandatory_claim_count"],
        "scientificValidationCoveredClaimCount": scientific_claim_coverage["covered_claim_count"],
        "scientificValidationUncoveredMandatoryClaimCount": scientific_claim_coverage[
            "uncovered_mandatory_claim_count"
        ],
        "scientificReferenceCaseCount": defaults_registry.scientific_reference_case_manifest().case_count,
        "scientificValidationMappedReferenceCaseClaimCount": sum(
            1 for claim in scientific_claim_manifest["claims"] if claim.get("reference_case_ids")
        ),
        "scientificValidationReferenceMandatoryMappedReferenceCaseClaimCount": sum(
            1
            for claim in scientific_claim_manifest["claims"]
            if (
                claim["model_family"] == "reference_mass_balance"
                and claim["mandatory_for_release"]
                and claim.get("reference_case_ids")
            )
        ),
        "scientificValidationReferenceMandatorySingleReferenceCaseClaimCount": sum(
            1
            for claim in scientific_claim_manifest["claims"]
            if (
                claim["model_family"] == "reference_mass_balance"
                and claim["mandatory_for_release"]
                and len(claim.get("reference_case_ids", [])) < 2
            )
        ),
        "scientificValidationReferenceMandatoryMultiReferenceCaseClaimCount": sum(
            1
            for claim in scientific_claim_manifest["claims"]
            if (
                claim["model_family"] == "reference_mass_balance"
                and claim["mandatory_for_release"]
                and len(claim.get("reference_case_ids", [])) >= 2
            )
        ),
        "scientificValidationReferenceMandatorySingleAnchorClaimCount": sum(
            1
            for record in scientific_claim_coverage["coverage"]
            if (
                record["model_family"] == "reference_mass_balance"
                and record["mandatory_for_release"]
                and record["support_strength"] == "single_anchor"
            )
        ),
        "scientificValidationReferenceMandatoryMultiAnchorClaimCount": sum(
            1
            for record in scientific_claim_coverage["coverage"]
            if (
                record["model_family"] == "reference_mass_balance"
                and record["mandatory_for_release"]
                and record["support_strength"] in {"multi_anchor_single_tier", "multi_anchor_multi_tier"}
            )
        ),
        "scientificValidationReferenceMandatorySingleTierClaimCount": sum(
            1
            for record in scientific_claim_coverage["coverage"]
            if (
                record["model_family"] == "reference_mass_balance"
                and record["mandatory_for_release"]
                and record["support_strength"] == "multi_anchor_single_tier"
            )
        ),
        "scientificValidationReferenceMandatoryMultiTierClaimCount": sum(
            1
            for record in scientific_claim_coverage["coverage"]
            if (
                record["model_family"] == "reference_mass_balance"
                and record["mandatory_for_release"]
                and record["support_strength"] == "multi_anchor_multi_tier"
            )
        ),
        "scientificValidationHighPriorityExperimentalSingleReferenceCaseClaimCount": sum(
            1
            for claim in scientific_claim_manifest["claims"]
            if (
                claim["model_family"] in EXPERIMENTAL_MODEL_FAMILIES
                and claim["priority"] == "high"
                and claim["mandatory_for_release"]
                and len(claim.get("reference_case_ids", [])) < 2
            )
        ),
        "scientificValidationHighPriorityExperimentalMultiReferenceCaseClaimCount": sum(
            1
            for claim in scientific_claim_manifest["claims"]
            if (
                claim["model_family"] in EXPERIMENTAL_MODEL_FAMILIES
                and claim["priority"] == "high"
                and claim["mandatory_for_release"]
                and len(claim.get("reference_case_ids", [])) >= 2
            )
        ),
        "scientificValidationMediumPriorityExperimentalSingleReferenceCaseClaimCount": sum(
            1
            for claim in scientific_claim_manifest["claims"]
            if (
                claim["model_family"] in EXPERIMENTAL_MODEL_FAMILIES
                and claim["priority"] == "medium"
                and claim["mandatory_for_release"]
                and len(claim.get("reference_case_ids", [])) < 2
            )
        ),
        "scientificValidationMediumPriorityExperimentalMultiReferenceCaseClaimCount": sum(
            1
            for claim in scientific_claim_manifest["claims"]
            if (
                claim["model_family"] in EXPERIMENTAL_MODEL_FAMILIES
                and claim["priority"] == "medium"
                and claim["mandatory_for_release"]
                and len(claim.get("reference_case_ids", [])) >= 2
            )
        ),
        "scientificValidationClaimSourceReferenceCount": sum(
            len(claim["source_references"]) for claim in scientific_claim_manifest["claims"]
        ),
        "scientificValidationExternalSourceReferenceCount": sum(
            1
            for claim in scientific_claim_manifest["claims"]
            for source_reference in claim["source_references"]
            if str(source_reference.get("url", "")).startswith(("http://", "https://"))
        ),
        "scientificValidationClaimMethodsBasisLineCount": sum(
            len(claim["methods_basis_lines"]) for claim in scientific_claim_manifest["claims"]
        ),
        "scientificValidationClaimReferenceCaseLineCount": sum(
            len(claim["reference_case_lines"]) for claim in scientific_claim_manifest["claims"]
        ),
        "scientificValidationHighPriorityExperimentalSingleAnchorClaimCount": sum(
            1
            for record in scientific_claim_coverage["coverage"]
            if (
                record["model_family"] in EXPERIMENTAL_MODEL_FAMILIES
                and record["priority"] == "high"
                and record["mandatory_for_release"]
                and record["support_strength"] == "single_anchor"
            )
        ),
        "scientificValidationHighPriorityExperimentalMultiAnchorClaimCount": sum(
            1
            for record in scientific_claim_coverage["coverage"]
            if (
                record["model_family"] in EXPERIMENTAL_MODEL_FAMILIES
                and record["priority"] == "high"
                and record["mandatory_for_release"]
                and record["support_strength"] in {"multi_anchor_single_tier", "multi_anchor_multi_tier"}
            )
        ),
        "scientificValidationMediumPriorityExperimentalSingleAnchorClaimCount": sum(
            1
            for record in scientific_claim_coverage["coverage"]
            if (
                record["model_family"] in EXPERIMENTAL_MODEL_FAMILIES
                and record["priority"] == "medium"
                and record["mandatory_for_release"]
                and record["support_strength"] == "single_anchor"
            )
        ),
        "scientificValidationMediumPriorityExperimentalMultiAnchorClaimCount": sum(
            1
            for record in scientific_claim_coverage["coverage"]
            if (
                record["model_family"] in EXPERIMENTAL_MODEL_FAMILIES
                and record["priority"] == "medium"
                and record["mandatory_for_release"]
                and record["support_strength"] in {"multi_anchor_single_tier", "multi_anchor_multi_tier"}
            )
        ),
        "scientificValidationHighPriorityExperimentalSingleTierClaimCount": sum(
            1
            for record in scientific_claim_coverage["coverage"]
            if (
                record["model_family"] in EXPERIMENTAL_MODEL_FAMILIES
                and record["priority"] == "high"
                and record["mandatory_for_release"]
                and record["support_strength"] == "multi_anchor_single_tier"
            )
        ),
        "scientificValidationHighPriorityExperimentalMultiTierClaimCount": sum(
            1
            for record in scientific_claim_coverage["coverage"]
            if (
                record["model_family"] in EXPERIMENTAL_MODEL_FAMILIES
                and record["priority"] == "high"
                and record["mandatory_for_release"]
                and record["support_strength"] == "multi_anchor_multi_tier"
            )
        ),
        "scientificValidationMediumPriorityExperimentalSingleTierClaimCount": sum(
            1
            for record in scientific_claim_coverage["coverage"]
            if (
                record["model_family"] in EXPERIMENTAL_MODEL_FAMILIES
                and record["priority"] == "medium"
                and record["mandatory_for_release"]
                and record["support_strength"] == "multi_anchor_single_tier"
            )
        ),
        "scientificValidationMediumPriorityExperimentalMultiTierClaimCount": sum(
            1
            for record in scientific_claim_coverage["coverage"]
            if (
                record["model_family"] in EXPERIMENTAL_MODEL_FAMILIES
                and record["priority"] == "medium"
                and record["mandatory_for_release"]
                and record["support_strength"] == "multi_anchor_multi_tier"
            )
        ),
        "modelFamilyComparisonProfileCount": len(
            defaults_registry.list_model_family_comparison_profiles()
        ),
        "modelFamilySelectionProfileCount": len(
            defaults_registry.list_model_family_selection_profiles()
        ),
        "modelFamilyChallengeReviewProfileCount": len(
            defaults_registry.list_model_family_challenge_review_profiles()
        ),
        "modelFamilySelectionReviewChecklistCount": sum(
            len(profile.review_checklist)
            for profile in defaults_registry.list_model_family_selection_profiles()
        ),
        "modelFamilySelectionReviewTemplateCount": sum(
            1
            for profile in defaults_registry.list_model_family_selection_profiles()
                if profile.review_packet_template and profile.review_brief_template
        ),
        "modelFamilyChallengeReviewChecklistCount": sum(
            len(profile.review_checklist)
            for profile in defaults_registry.list_model_family_challenge_review_profiles()
        ),
        "modelFamilyChallengeReviewTemplateCount": sum(
            1
            for profile in defaults_registry.list_model_family_challenge_review_profiles()
            if profile.review_packet_template and profile.review_brief_template
        ),
        "modelFamilyComparisonReviewChecklistCount": sum(
            len(profile.review_checklist)
            for profile in defaults_registry.list_model_family_comparison_profiles()
        ),
        "modelFamilyComparisonReviewTemplateCount": sum(
            1
            for profile in defaults_registry.list_model_family_comparison_profiles()
            if profile.review_packet_template and profile.review_brief_template
        ),
        "scientificReviewProfileCount": len(defaults_registry.list_scientific_review_profiles()),
        "scientificReviewChecklistCount": sum(
            len(profile.review_checklist) for profile in defaults_registry.list_scientific_review_profiles()
        ),
        "scientificReviewTemplateCount": sum(
            1
            for profile in defaults_registry.list_scientific_review_profiles()
            if profile.packet_template and profile.brief_template
        ),
        "scientificReviewOutcomeTemplateCount": sum(
            1
            for profile in defaults_registry.list_scientific_review_profiles()
            if profile.acceptable_outcome_template
            and profile.qualified_outcome_template
            and profile.escalation_outcome_template
        ),
        "scientificReviewGovernedPolicyCount": sum(
            1
            for profile in defaults_registry.list_scientific_review_profiles()
            if (
                profile.ready_fit_verdicts is not None
                and profile.attention_outcomes is not None
                and profile.attention_if_any_checks_fail is not None
            )
        ),
        "scientificReviewStatusPolicyCount": sum(
            1
            for profile in defaults_registry.list_scientific_review_profiles()
            if (
                profile.ready_fit_verdicts is not None
                and profile.attention_outcomes is not None
                and profile.attention_if_any_checks_fail is not None
            )
        ),
        "scientificReviewOutcomePolicyCount": sum(
            1
            for profile in defaults_registry.list_scientific_review_profiles()
            if (
                profile.escalation_fit_verdicts
                or profile.escalation_driver_types
                or profile.qualification_driver_types
                or profile.warning_severity_promotes_qualification is not None
            )
        ),
        "scientificReviewDriverActionTemplateCount": sum(
            len(profile.driver_action_templates)
            for profile in defaults_registry.list_scientific_review_profiles()
        ),
        "physchemPolicyFamilyCount": defaults_registry.physchem_parameter_policy_manifest()["familyCount"],
        "physchemPolicyCount": len(defaults_registry.list_physchem_parameter_policies()),
        "adapterUnitConversionRuleCount": len(defaults_registry.list_adapter_unit_conversion_rules()),
        "adapterImportProfileCount": len(adapter_manifest.profiles),
        "adapterFixtureCount": len(adapter_manifest.fixtures),
        "publicAdapterImportProfileCount": len(public_adapter_profile_ids),
        "publicAdapterFixtureCount": sum(
            1 for fixture in adapter_manifest.fixtures if fixture.import_profile in public_adapter_profile_ids
        ),
        "erosionSedimentValidationDemoCaseCount": dossier[
            "erosionSedimentValidationDemoPack"
        ]["demoCaseCount"],
        "erosionSedimentValidationDemoPackPassed": dossier[
            "erosionSedimentValidationDemoPack"
        ]["passed"],
        "scientificExternalBenchmarkCaseCount": dossier[
            "scientificExternalBenchmarkPack"
        ]["caseCount"],
        "scientificExternalBenchmarkPackPassed": dossier[
            "scientificExternalBenchmarkPack"
        ]["passed"],
        "defaultSensitivityProfileCount": dossier[
            "defaultSensitivityProfiles"
        ]["profileCount"],
        "defaultSensitivityProfilesPassed": dossier[
            "defaultSensitivityProfiles"
        ]["passed"],
        "fugacityScreeningMethodProfileCount": dossier[
            "fugacityScreeningValidation"
        ]["profileCount"],
        "fugacityScreeningValidationPassed": dossier[
            "fugacityScreeningValidation"
        ]["passed"],
        "scientificEvidenceQualityMatrixPassed": dossier[
            "scientificEvidenceQualityMatrix"
        ]["passed"],
        "scientificEvidenceQualityMatrixClaimRowCount": evidence_quality_matrix_report[
            "claim_row_count"
        ],
        "scientificEvidenceQualityMatrixModelFamilyRowCount": evidence_quality_matrix_report[
            "model_family_row_count"
        ],
        "parameterManifestEntryCount": len(parameter_manifest_example["entries"]),
        "parameterManifestRuntimeConsumedCount": sum(
            1 for entry in parameter_manifest_example["entries"] if entry["runtime_consumed"]
        ),
        "parameterManifestPreservedOnlyCount": sum(
            1 for entry in parameter_manifest_example["entries"] if not entry["runtime_consumed"]
        ),
        "parameterManifestCoreDefaultAssumptionCount": parameter_manifest_example.get(
            "core_default_assumption_count",
            0,
        ),
        "parameterManifestDefaultEvidenceStatus": parameter_manifest_example.get(
            "default_evidence_status"
        ),
        "benchmarkMetadataFixtureCount": dossier["scientificReviewArtifacts"]["benchmarkMetadataFixtureCount"],
        "defaultsEvidenceGovernancePassed": dossier["defaultsEvidenceGovernance"]["passed"],
        "externalCorroborationGovernancePassed": dossier["externalCorroborationGovernance"]["passed"],
        "runScientificTrustBriefWorkflowCount": sum(
            1
            for workflow in SUPPORTED_WORKFLOWS
            if workflow in {"fate_build_run_scientific_trust_brief"}
        ),
        "scientificReviewWorkflowCount": sum(
            1
            for workflow in SUPPORTED_WORKFLOWS
            if workflow in {
                "fate_preview_scientific_review_outcome",
                "fate_build_scientific_review_packet",
                "fate_build_scientific_review_brief",
            }
        ),
        "scientificMethodsDossierWorkflowCount": sum(
            1
            for workflow in SUPPORTED_WORKFLOWS
            if workflow in {
                "fate_build_scientific_methods_dossier",
                "fate_build_scientific_methods_dossier_brief",
            }
        ),
        "modelFamilyComparisonWorkflowCount": sum(
            1
            for workflow in SUPPORTED_WORKFLOWS
            if workflow in {
                "fate_build_model_family_comparison_packet",
                "fate_build_model_family_comparison_brief",
            }
        ),
        "modelFamilySelectionWorkflowCount": sum(
            1
            for workflow in SUPPORTED_WORKFLOWS
            if workflow in {"fate_recommend_model_family_selection"}
        ),
        "modelFamilySelectionReviewWorkflowCount": sum(
            1
            for workflow in SUPPORTED_WORKFLOWS
            if workflow in {
                "fate_preview_model_family_selection_review",
                "fate_build_model_family_selection_review_packet",
                "fate_build_model_family_selection_review_brief",
            }
        ),
        "modelFamilyChallengeReviewWorkflowCount": sum(
            1
            for workflow in SUPPORTED_WORKFLOWS
            if workflow in {
                "fate_preview_model_family_challenge_review",
                "fate_build_model_family_challenge_review_packet",
                "fate_build_model_family_challenge_review_brief",
            }
        ),
        "modelFamilyChallengeScientificDossierWorkflowCount": sum(
            1
            for workflow in SUPPORTED_WORKFLOWS
            if workflow in {
                "fate_build_model_family_challenge_scientific_dossier",
                "fate_build_model_family_challenge_scientific_dossier_brief",
            }
        ),
        "modelFamilyComparisonReviewWorkflowCount": sum(
            1
            for workflow in SUPPORTED_WORKFLOWS
            if workflow in {
                "fate_preview_model_family_comparison_review",
                "fate_build_model_family_comparison_review_packet",
                "fate_build_model_family_comparison_review_brief",
            }
        ),
        "supportedWorkflows": SUPPORTED_WORKFLOWS,
        "supportedModelFamilies": SUPPORTED_MODEL_FAMILIES,
        "experimentalModelFamilyCount": len(EXPERIMENTAL_MODEL_FAMILIES),
        "experimentalModelFamilies": EXPERIMENTAL_MODEL_FAMILIES,
        "artifactHashes": {
            "contractsManifest": _sha256_text(json.dumps(contracts_manifest, sort_keys=True)),
            "defaultsManifest": _sha256_text(json.dumps(defaults_manifest, sort_keys=True)),
            "examplesManifest": _sha256_text(json.dumps(examples_manifest, sort_keys=True)),
        },
    }
    defaults_rebaseline_report = _build_defaults_rebaseline_report(defaults_registry, dossier)
    external_corroboration_report = _build_external_corroboration_report(
        defaults_registry,
        dossier,
        scientific_claim_coverage,
    )
    reference_corroboration_report = _build_reference_corroboration_report(
        defaults_registry,
        dossier,
        scientific_claim_coverage,
        defaults_rebaseline_report,
    )
    (
        reference_worksheet_manifest,
        reference_worksheet_pack_files,
    ) = _build_reference_worksheet_manifest_report(
        defaults_registry,
        reference_corroboration_report,
        defaults_rebaseline_report,
    )
    advective_promotion_bar_report = _build_advective_promotion_bar_report(
        defaults_registry,
        dossier,
        scientific_claim_coverage,
    )
    (
        advective_worksheet_manifest,
        advective_worksheet_pack_files,
    ) = _build_advective_worksheet_manifest_report(
        defaults_registry,
        scientific_claim_coverage,
        defaults_rebaseline_report,
        advective_promotion_bar_report,
    )
    readiness_report = {
        "version": VERSION,
        "status": "ready_for_screening_release"
        if all(item["status"] == "ok" for item in dossier["artifacts"]["schemas"])
        and all(item["status"] == "ok" for item in dossier["artifacts"]["examples"])
        and dossier["benchmarks"]["passed"]
        and dossier["failureModes"]["passed"]
        and dossier["downstreamInteroperability"]["passed"]
        and dossier["defaultsEvidenceGovernance"]["passed"]
        and dossier["regulatoryHandoffGovernance"]["passed"]
        and dossier["adapterInteroperability"]["passed"]
        and dossier["reconciliationTransparency"]["passed"]
        and dossier["scientificReviewArtifacts"]["passed"]
        and dossier["scientificClaimCoverage"]["passed"]
        and dossier["externalCorroborationGovernance"]["passed"]
        and dossier["referenceCorroborationGovernance"]["passed"]
        and dossier["advectivePromotionBarGovernance"]["passed"]
        and dossier["scientificReviewWorkflow"]["passed"]
        and dossier["runScientificTrustBriefWorkflow"]["passed"]
        and dossier["scientificMethodsDossierWorkflow"]["passed"]
        and dossier["trustSurfaceConsistency"]["passed"]
        and dossier["erosionSedimentValidationDemoPack"]["passed"]
        and dossier["scientificExternalBenchmarkPack"]["passed"]
        and dossier["defaultSensitivityProfiles"]["passed"]
        and dossier["fugacityScreeningValidation"]["passed"]
        and dossier["scientificEvidenceQualityMatrix"]["passed"]
        and dossier["modelFamilySelectionWorkflow"]["passed"]
        and dossier["modelFamilySelectionReviewWorkflow"]["passed"]
        and dossier["modelFamilyChallengeReviewWorkflow"]["passed"]
        and dossier["modelFamilyChallengeScientificDossierWorkflow"]["passed"]
        and dossier["modelFamilyComparisonWorkflow"]["passed"]
        and dossier["modelFamilyComparisonReviewWorkflow"]["passed"]
        else "not_ready",
        "checks": [
            {"name": "schemas-generated", "passed": all(item["status"] == "ok" for item in dossier["artifacts"]["schemas"])},
            {"name": "examples-generated", "passed": all(item["status"] == "ok" for item in dossier["artifacts"]["examples"])},
            {"name": "defaults-manifest-generated", "passed": bool(defaults_manifest["files"])},
            {"name": "defaults-evidence-governance-passed", "passed": dossier["defaultsEvidenceGovernance"]["passed"]},
            {"name": "benchmarks-passed", "passed": dossier["benchmarks"]["passed"]},
            {"name": "failure-modes-passed", "passed": dossier["failureModes"]["passed"]},
            {"name": "downstream-interoperability-passed", "passed": dossier["downstreamInteroperability"]["passed"]},
            {"name": "regulatory-handoff-governance-passed", "passed": dossier["regulatoryHandoffGovernance"]["passed"]},
            {"name": "adapter-interoperability-passed", "passed": dossier["adapterInteroperability"]["passed"]},
            {"name": "reconciliation-transparency-passed", "passed": dossier["reconciliationTransparency"]["passed"]},
            {"name": "scientific-review-artifacts-passed", "passed": dossier["scientificReviewArtifacts"]["passed"]},
            {"name": "scientific-claim-coverage-passed", "passed": dossier["scientificClaimCoverage"]["passed"]},
            {
                "name": "external-corroboration-governance-passed",
                "passed": dossier["externalCorroborationGovernance"]["passed"],
            },
            {
                "name": "reference-corroboration-governance-passed",
                "passed": dossier["referenceCorroborationGovernance"]["passed"],
            },
            {
                "name": "advective-promotion-bar-governance-passed",
                "passed": dossier["advectivePromotionBarGovernance"]["passed"],
            },
            {"name": "scientific-review-workflow-passed", "passed": dossier["scientificReviewWorkflow"]["passed"]},
            {
                "name": "run-scientific-trust-brief-workflow-passed",
                "passed": dossier["runScientificTrustBriefWorkflow"]["passed"],
            },
            {"name": "scientific-methods-dossier-workflow-passed", "passed": dossier["scientificMethodsDossierWorkflow"]["passed"]},
            {
                "name": "trust-surface-consistency-passed",
                "passed": dossier["trustSurfaceConsistency"]["passed"],
            },
            {
                "name": "erosion-sediment-validation-demo-pack-passed",
                "passed": dossier["erosionSedimentValidationDemoPack"]["passed"],
            },
            {
                "name": "scientific-external-benchmark-pack-passed",
                "passed": dossier["scientificExternalBenchmarkPack"]["passed"],
            },
            {
                "name": "default-sensitivity-profiles-passed",
                "passed": dossier["defaultSensitivityProfiles"]["passed"],
            },
            {
                "name": "fugacity-screening-validation-passed",
                "passed": dossier["fugacityScreeningValidation"]["passed"],
            },
            {
                "name": "scientific-evidence-quality-matrix-passed",
                "passed": dossier["scientificEvidenceQualityMatrix"]["passed"],
            },
            {"name": "model-family-selection-workflow-passed", "passed": dossier["modelFamilySelectionWorkflow"]["passed"]},
            {
                "name": "model-family-selection-review-workflow-passed",
                "passed": dossier["modelFamilySelectionReviewWorkflow"]["passed"],
            },
            {
                "name": "model-family-challenge-review-workflow-passed",
                "passed": dossier["modelFamilyChallengeReviewWorkflow"]["passed"],
            },
            {
                "name": "model-family-challenge-scientific-dossier-workflow-passed",
                "passed": dossier["modelFamilyChallengeScientificDossierWorkflow"]["passed"],
            },
            {"name": "model-family-comparison-workflow-passed", "passed": dossier["modelFamilyComparisonWorkflow"]["passed"]},
            {
                "name": "model-family-comparison-review-workflow-passed",
                "passed": dossier["modelFamilyComparisonReviewWorkflow"]["passed"],
            },
        ],
        "blockerClasses": [
            {
                "name": "unresolved_default_derivation_gap",
                "passed": dossier["defaultsEvidenceGovernance"]["passed"],
            },
            {
                "name": "uncovered_corroboration_requirement",
                "passed": dossier["externalCorroborationGovernance"]["passed"],
            },
            {
                "name": "unresolved_shipped_default_rebaseline_gap",
                "passed": dossier["defaultsEvidenceGovernance"]["passed"],
            },
            {
                "name": "missing_reference_family_official_corroboration",
                "passed": dossier["referenceCorroborationGovernance"]["passed"],
            },
            {
                "name": "worksheet_or_equation_mismatch",
                "passed": dossier["referenceCorroborationGovernance"]["passed"]
                and dossier["benchmarks"]["passed"],
            },
            {
                "name": "trust_surface_inconsistency",
                "passed": dossier["trustSurfaceConsistency"]["passed"],
            },
            {
                "name": "advective_promotion_language_drift",
                "passed": dossier["advectivePromotionBarGovernance"]["passed"],
            },
            {
                "name": "erosion_sediment_validation_demo_pack_mismatch",
                "passed": dossier["erosionSedimentValidationDemoPack"]["passed"],
            },
            {
                "name": "scientific_external_benchmark_pack_mismatch",
                "passed": dossier["scientificExternalBenchmarkPack"]["passed"],
            },
            {
                "name": "default_sensitivity_profile_drift",
                "passed": dossier["defaultSensitivityProfiles"]["passed"],
            },
            {
                "name": "fugacity_screening_validation_drift",
                "passed": dossier["fugacityScreeningValidation"]["passed"],
            },
            {
                "name": "scientific_evidence_quality_matrix_drift",
                "passed": dossier["scientificEvidenceQualityMatrix"]["passed"],
            },
        ],
    }
    security_provenance_review = {
        "version": VERSION,
        "status": "documented_provenance_controls_with_declared_scope_limits",
        "scope": [
            "Release-bundle provenance posture for the public screening MCP surface.",
            "Control summary for generated artifacts, defaults provenance, and downstream handoff integrity.",
        ],
        "controls": [
            "Defaults and assumption provenance are explicit and machine-readable.",
            "Concentration bundles and regulatory handoff packages carry SHA-256 integrity hashes.",
            "Quality flags and limitation notes are emitted in normalized outputs and review artifacts.",
            "GitHub release assets are built by the release-provenance workflow and can be signed with GitHub Artifact Attestations.",
        ],
        "limitations": [
            "No secret handling is implemented because the public screening workflows do not require credential-bearing inputs.",
            "Artifact attestations link release assets to their build workflow and repository; they do not guarantee vulnerability absence, scientific adequacy, regulator acceptance, or deployment safety.",
            "This report summarizes product-level provenance controls; it is not a substitute for deployment-specific security hardening or independent security assessment.",
        ],
        "notes": [
            "Environmental Fate MCP is a bounded screening service inside the broader ToxMCP suite.",
            "Provenance, quality, and declared limitation fields are intended to support assessor review rather than replace it.",
        ],
    }
    known_gap_report = {
        "version": VERSION,
        "knownGaps": KNOWN_GAPS,
    }
    scientific_validation_narrative = {
        "version": VERSION,
        "status": "evidence_quality_matrix_added_without_model_scope_expansion",
        "narrativeLines": [
            "The v0.5 release line adds a governed scientific evidence-quality matrix without adding model scope, Level III transfer, GIS routing, hydrology generation, calibration, WEPP/SWAT/PRZM execution, or final risk decisions.",
            "The benchmark pack improves reproducibility and source-grounded corroboration for scalar screening equations, but it is not field validation, calibration evidence, source-engine equivalence, or regulator acceptance.",
            "The default sensitivity report shows how shipped or scenario assumptions can move screening outputs; it is not formal global sensitivity analysis or uncertainty quantification.",
            "The fugacity screening validation report checks mass conservation, degradation-loss balance, requested-media filtering, source references, and explicit Level III/routing/calibration boundary language.",
            "The evidence-quality matrix separates reviewer-grade screening, source-grounded screening, internal-oracle screening, synthetic-demo-only, and deferred/gap rows so reviewers can see proof posture without overreading release claims.",
            "Probabilistic sample manifests preserve seed, sampled parameter summaries, iteration health, and stable hashes when requested; full per-iteration calculation traces remain intentionally omitted.",
            "GitHub Artifact Attestations for release assets, when published, support supply-chain provenance review; they are not scientific validation or a substitute for release-report review.",
            "The release remains bounded to concentration screening, scalar erosion/sediment screening, and experimental fugacity equilibrium screening; no hydrology generation, spatial routing, calibration, WEPP execution, Level III transfer, or final risk decision is added.",
        ],
        "benchmarkResource": "defaults://scientific-external-benchmark-pack",
        "benchmarkReport": "release://external-validation-benchmark-report",
        "sensitivityResource": "defaults://default-sensitivity-profiles",
        "sensitivityReport": "release://default-sensitivity-report",
        "fugacityResource": "defaults://fugacity-screening-method-profiles",
        "fugacityReport": "release://fugacity-screening-validation-report",
        "evidenceQualityRubricResource": "defaults://scientific-evidence-quality-rubric",
        "evidenceQualityMatrixReport": "release://scientific-evidence-quality-matrix-report",
        "acceptedLimitations": KNOWN_GAPS,
    }
    reports = {
        "metadata-report": metadata_report,
        "readiness-report": readiness_report,
        "security-provenance-review-report": security_provenance_review,
        "benchmark-manifest": benchmark_info,
        "scientific-claim-coverage-report": scientific_claim_coverage,
        "defaults-rebaseline-report": defaults_rebaseline_report,
        "external-corroboration-report": external_corroboration_report,
        "reference-corroboration-report": reference_corroboration_report,
        "reference-worksheet-manifest": reference_worksheet_manifest,
        "advective-worksheet-manifest": advective_worksheet_manifest,
        "advective-promotion-bar-report": advective_promotion_bar_report,
        "validation-dossier": dossier,
        "adapter-validation-report": dossier["adapterInteroperability"],
        "erosion-sediment-validation-demo-report": dossier[
            "erosionSedimentValidationDemoPack"
        ],
        "external-validation-benchmark-report": dossier["scientificExternalBenchmarkPack"],
        "default-sensitivity-report": dossier["defaultSensitivityProfiles"],
        "fugacity-screening-validation-report": dossier["fugacityScreeningValidation"],
        "scientific-evidence-quality-matrix-report": evidence_quality_matrix_report,
        "scientific-validation-narrative": scientific_validation_narrative,
        "known-gap-report": known_gap_report,
    }
    red_team_review_report = _build_red_team_review_report(defaults_registry, reports)
    readiness_report["checks"].extend(
        [
            {
                "name": "red-team-review-passed",
                "passed": red_team_review_report["openBlockerCount"] == 0
                and red_team_review_report["unresolvedFindingCount"] == 0,
            },
        ]
    )
    readiness_report["blockerClasses"].append(
        {
            "name": "unaddressed_red_team_finding",
            "passed": red_team_review_report["openBlockerCount"] == 0
            and red_team_review_report["unresolvedFindingCount"] == 0,
        }
    )
    reports["red-team-review-report"] = red_team_review_report
    scientific_trust_pack = _render_scientific_trust_pack(
        reports,
        defaults_registry,
        f"v{VERSION}",
    )
    scientific_trust_brief = _render_scientific_trust_brief(
        reports,
        defaults_registry,
        f"v{VERSION}",
    )
    reference_proof_brief = _render_reference_proof_brief(reports, f"v{VERSION}")
    advective_promotion_brief = _render_advective_promotion_brief(reports, f"v{VERSION}")
    trust_pack_consistent = all(
        marker in scientific_trust_pack
        for marker in (
            "## What Changed Scientifically In This Release",
            "## Reference Reviewer-Grade Anchor",
            "## Experimental Advective Challenge Path",
            "When Not To Use This MCP",
        )
    )
    trust_brief_consistent = all(
        marker in scientific_trust_brief
        for marker in (
            "## One-Shot Readout",
            "reference_mass_balance",
            "advective_screening_mass_balance",
        )
    )
    reference_proof_brief_consistent = all(
        marker in reference_proof_brief
        for marker in (
            "## One-Shot Readout",
            "reference_mass_balance",
            "release://reference-corroboration-report",
            "release://reference-worksheet-manifest",
        )
    )
    advective_promotion_brief_consistent = all(
        marker in advective_promotion_brief
        for marker in (
            "## One-Shot Readout",
            "advective_screening_mass_balance",
            "release://advective-promotion-bar-report",
        )
    )
    advective_language_consistent = (
        "experimental" in scientific_trust_pack.lower()
        and "non-promotable" in scientific_trust_pack.lower()
        and "experimental" in scientific_trust_brief.lower()
        and "non-promotable" in scientific_trust_brief.lower()
    )
    readiness_report["checks"].append(
        {
            "name": "scientific-trust-pack-generated",
            "passed": bool(scientific_trust_pack.strip()) and trust_pack_consistent,
        }
    )
    readiness_report["blockerClasses"].append(
        {
            "name": "trust_pack_artifact_mismatch",
            "passed": bool(scientific_trust_pack.strip()) and trust_pack_consistent,
        }
    )
    readiness_report["checks"].append(
        {
            "name": "scientific-trust-brief-generated",
            "passed": bool(scientific_trust_brief.strip()) and trust_brief_consistent,
        }
    )
    readiness_report["blockerClasses"].append(
        {
            "name": "trust_brief_artifact_mismatch",
            "passed": bool(scientific_trust_brief.strip()) and trust_brief_consistent,
        }
    )
    readiness_report["checks"].append(
        {
            "name": "reference-proof-brief-generated",
            "passed": bool(reference_proof_brief.strip()) and reference_proof_brief_consistent,
        }
    )
    readiness_report["checks"].append(
        {
            "name": "reference-worksheet-manifest-generated",
            "passed": bool(reference_worksheet_manifest["claims"])
            and bool(reference_worksheet_manifest["generatedArtifactPaths"])
            and reference_worksheet_manifest["passed"],
        }
    )
    readiness_report["blockerClasses"].append(
        {
            "name": "reference_worksheet_pack_artifact_mismatch",
            "passed": bool(reference_worksheet_manifest["claims"])
            and bool(reference_worksheet_manifest["generatedArtifactPaths"])
            and reference_worksheet_manifest["passed"],
        }
    )
    readiness_report["checks"].append(
        {
            "name": "advective-promotion-brief-generated",
            "passed": bool(advective_promotion_brief.strip())
            and advective_promotion_brief_consistent,
        }
    )
    readiness_report["checks"].append(
        {
            "name": "advective-promotion-language-drift-passed",
            "passed": advective_language_consistent,
        }
    )
    readiness_report["blockerClasses"].append(
        {
            "name": "accidental_advective_promotion_language_drift",
            "passed": advective_language_consistent,
        }
    )
    readiness_report["status"] = (
        "ready_for_screening_release"
        if all(item["passed"] for item in readiness_report["checks"])
        else "not_ready"
    )
    reports["scientific-trust-pack"] = {"markdown": scientific_trust_pack}
    reports["scientific-trust-brief"] = {"markdown": scientific_trust_brief}
    reports["reference-proof-brief"] = {"markdown": reference_proof_brief}
    reports["advective-promotion-brief"] = {"markdown": advective_promotion_brief}
    reports["_reference-worksheet-pack-files"] = reference_worksheet_pack_files
    reports["_advective-worksheet-pack-files"] = advective_worksheet_pack_files
    return reports


def write_release_bundle(repo_root: Path, output_dir: Path | None = None, release_ref: str | None = None) -> Path:
    reports = build_release_reports(repo_root)
    release_ref = release_ref or f"v{VERSION}"
    bundle_dir = output_dir or repo_root / "docs" / "releases" / f"v{VERSION}"
    bundle_dir.mkdir(parents=True, exist_ok=True)

    bundle_texts: dict[str, str] = {
        filename: _json_text(reports[report_name]) for report_name, filename in REPORT_FILENAMES
    }
    bundle_texts["scientific-trust-pack.md"] = _render_scientific_trust_pack(
        reports,
        DefaultsRegistry(repo_root),
        release_ref,
    )
    bundle_texts["scientific-trust-brief.md"] = _render_scientific_trust_brief(
        reports,
        DefaultsRegistry(repo_root),
        release_ref,
    )
    bundle_texts["reference-proof-brief.md"] = _render_reference_proof_brief(
        reports,
        release_ref,
    )
    bundle_texts["advective-promotion-brief.md"] = _render_advective_promotion_brief(
        reports,
        release_ref,
    )
    bundle_texts["release-notes.md"] = _render_release_notes(reports, release_ref)
    bundle_texts["README.md"] = _render_release_bundle_readme(reports, release_ref)
    bundle_texts.update(reports.get("_reference-worksheet-pack-files", {}))
    bundle_texts.update(reports.get("_advective-worksheet-pack-files", {}))

    for filename, text in bundle_texts.items():
        target_path = bundle_dir / filename
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(text)

    manifest_files = [
        {"path": filename, "sha256": _sha256_path(bundle_dir / filename)}
        for filename in sorted(bundle_texts)
    ]
    manifest = {
        "version": VERSION,
        "releaseRef": release_ref,
        "status": reports["readiness-report"]["status"],
        "files": manifest_files,
    }
    manifest_path = bundle_dir / "release-bundle-manifest.json"
    manifest_path.write_text(_json_text(manifest))

    checksum_targets = sorted([*bundle_texts.keys(), manifest_path.name])
    checksum_lines = [
        f"{_sha256_path(bundle_dir / filename)}  {filename}" for filename in checksum_targets
    ]
    (bundle_dir / "SHA256SUMS").write_text("\n".join(checksum_lines) + "\n")
    refresh_packaged_resource_mirror(repo_root)
    return bundle_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a deterministic public release bundle.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Exact output directory for the bundle. Defaults to docs/releases/v<version> under the repo root.",
    )
    parser.add_argument(
        "--release-ref",
        default=f"v{VERSION}",
        help="Release reference label to embed in the generated bundle, for example a tag such as v0.5.0.",
    )
    args = parser.parse_args()
    bundle_dir = write_release_bundle(Path.cwd(), output_dir=args.output_dir, release_ref=args.release_ref)
    print(bundle_dir)
