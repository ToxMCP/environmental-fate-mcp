from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from fate_mcp.benchmarks import benchmark_manifest
from fate_mcp.contracts import build_contract_manifest, generate_contract_artifacts
from fate_mcp.defaults import DefaultsRegistry
from fate_mcp.package_metadata import (
    EXPERIMENTAL_MODEL_FAMILIES,
    SUPPORTED_MODEL_FAMILIES,
    SUPPORTED_WORKFLOWS,
    VERSION,
)
from fate_mcp.plugins.external_result_adapter import build_adapter_import_manifest
from fate_mcp.validation import validation_dossier


KNOWN_GAPS = [
    "No GIS-scale dispersion in v0.1.",
    "No direct human dose calculation in Environmental Fate MCP.",
    "No dietary intake workflows in Environmental Fate MCP.",
    "No PBPK execution in Environmental Fate MCP.",
    "Adapter stub is illustrative and not a validated external engine.",
]

REPORT_FILENAMES = (
    ("metadata-report", "metadata-report.json"),
    ("readiness-report", "readiness-report.json"),
    ("security-provenance-review-report", "security-provenance-review-report.json"),
    ("benchmark-manifest", "benchmark-manifest.json"),
    ("scientific-claim-coverage-report", "scientific-claim-coverage-report.json"),
    ("validation-dossier", "validation-dossier.json"),
    ("adapter-validation-report", "adapter-validation-report.json"),
    ("known-gap-report", "known-gap-report.json"),
)

REPORT_DESCRIPTIONS = {
    "metadata-report.json": "Release metadata summary for counts, supported workflows, and governed coverage.",
    "readiness-report.json": "Machine-readable release status and the top-level release gate checks.",
    "security-provenance-review-report.json": "Security and provenance review posture summary.",
    "benchmark-manifest.json": "Benchmark fixture manifest and claim linkage surface.",
    "scientific-claim-coverage-report.json": "Scientific validation claim coverage and unresolved-gap report.",
    "validation-dossier.json": "Full validation dossier across scientific, interoperability, and release checks.",
    "adapter-validation-report.json": "Focused validation report for governed adapter interoperability.",
    "known-gap-report.json": "Declared known gaps that remain intentionally out of scope for this release.",
    "release-notes.md": "Human-readable release notes draft for the exact release reference.",
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


def _render_release_notes(reports: dict[str, dict], release_ref: str) -> str:
    metadata = reports["metadata-report"]
    readiness = reports["readiness-report"]
    validation = reports["validation-dossier"]
    known_gaps = reports["known-gap-report"]["knownGaps"]
    passed_checks = sum(1 for item in readiness["checks"] if item["passed"])
    total_checks = len(readiness["checks"])
    lines = [
        f"# Environmental Fate MCP {release_ref}",
        "",
        f"Version: `{VERSION}`",
        f"Release status: `{readiness['status']}`",
        "",
        "## Highlights",
        f"- `{metadata['schemaCount']}` JSON schemas and `{metadata['exampleCount']}` generated examples are published for the release surface.",
        f"- `{len(metadata['supportedWorkflows'])}` governed workflows are available across `{len(metadata['supportedModelFamilies'])}` supported model families and `{metadata['experimentalModelFamilyCount']}` experimental model family.",
        f"- `{metadata['scientificValidationClaimCount']}` governed scientific validation claims and `{metadata['scientificReferenceCaseCount']}` governed scientific reference cases are included.",
        f"- `{metadata['regulatoryHandoffProfileCount']}` governed regulatory handoff profiles are published for downstream suite consumers.",
        "",
        "## Verification Summary",
        f"- Release checks passed: `{passed_checks}/{total_checks}`.",
        f"- Mandatory scientific validation claims uncovered: `{metadata['scientificValidationUncoveredMandatoryClaimCount']}`.",
        f"- Benchmarks passed: `{validation['benchmarks']['passed']}`.",
        f"- Downstream interoperability passed: `{validation['downstreamInteroperability']['passed']}`.",
        f"- Regulatory handoff governance passed: `{validation['regulatoryHandoffGovernance']['passed']}`.",
        f"- Scientific review artifacts passed: `{validation['scientificReviewArtifacts']['passed']}`.",
        "",
        "## Known Gaps",
    ]
    lines.extend(f"- {gap}" for gap in known_gaps)
    lines.extend(
        [
            "",
            "## Bundle Contents",
            "- Machine-readable release reports are published alongside this note in the same directory.",
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
        "",
        "## Files",
    ]
    for _, filename in REPORT_FILENAMES:
        lines.append(f"- `{filename}`: {REPORT_DESCRIPTIONS[filename]}")
    lines.extend(
        [
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
    dossier = validation_dossier(repo_root)
    benchmark_info = benchmark_manifest(repo_root)
    scientific_claim_manifest = benchmark_info["scientificValidationClaimManifest"]
    scientific_claim_coverage = benchmark_info["scientificValidationClaimCoverage"]
    metadata_report = {
        "version": VERSION,
        "schemaCount": len(contracts_manifest["schemas"]),
        "exampleCount": len(examples_manifest["examples"]),
        "defaultsVersion": defaults_manifest["defaultsVersion"],
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
        "parameterManifestEntryCount": len(parameter_manifest_example["entries"]),
        "parameterManifestRuntimeConsumedCount": sum(
            1 for entry in parameter_manifest_example["entries"] if entry["runtime_consumed"]
        ),
        "parameterManifestPreservedOnlyCount": sum(
            1 for entry in parameter_manifest_example["entries"] if not entry["runtime_consumed"]
        ),
        "benchmarkMetadataFixtureCount": dossier["scientificReviewArtifacts"]["benchmarkMetadataFixtureCount"],
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
    readiness_report = {
        "version": VERSION,
        "status": "ready_for_screening_release"
        if all(item["status"] == "ok" for item in dossier["artifacts"]["schemas"])
        and all(item["status"] == "ok" for item in dossier["artifacts"]["examples"])
        and dossier["benchmarks"]["passed"]
        and dossier["failureModes"]["passed"]
        and dossier["downstreamInteroperability"]["passed"]
        and dossier["regulatoryHandoffGovernance"]["passed"]
        and dossier["adapterInteroperability"]["passed"]
        and dossier["reconciliationTransparency"]["passed"]
        and dossier["scientificReviewArtifacts"]["passed"]
        and dossier["scientificClaimCoverage"]["passed"]
        and dossier["scientificReviewWorkflow"]["passed"]
        and dossier["scientificMethodsDossierWorkflow"]["passed"]
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
            {"name": "benchmarks-passed", "passed": dossier["benchmarks"]["passed"]},
            {"name": "failure-modes-passed", "passed": dossier["failureModes"]["passed"]},
            {"name": "downstream-interoperability-passed", "passed": dossier["downstreamInteroperability"]["passed"]},
            {"name": "regulatory-handoff-governance-passed", "passed": dossier["regulatoryHandoffGovernance"]["passed"]},
            {"name": "adapter-interoperability-passed", "passed": dossier["adapterInteroperability"]["passed"]},
            {"name": "reconciliation-transparency-passed", "passed": dossier["reconciliationTransparency"]["passed"]},
            {"name": "scientific-review-artifacts-passed", "passed": dossier["scientificReviewArtifacts"]["passed"]},
            {"name": "scientific-claim-coverage-passed", "passed": dossier["scientificClaimCoverage"]["passed"]},
            {"name": "scientific-review-workflow-passed", "passed": dossier["scientificReviewWorkflow"]["passed"]},
            {"name": "scientific-methods-dossier-workflow-passed", "passed": dossier["scientificMethodsDossierWorkflow"]["passed"]},
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
    }
    security_provenance_review = {
        "version": VERSION,
        "status": "provenance_explicit_review_pending",
        "notes": [
            "No secret handling is implemented in v0.1.",
            "Defaults and assumption provenance are explicit and machine-readable.",
            "Quality flags and limitation notes are emitted in normalized outputs.",
        ],
    }
    known_gap_report = {
        "version": VERSION,
        "knownGaps": KNOWN_GAPS,
    }
    return {
        "metadata-report": metadata_report,
        "readiness-report": readiness_report,
        "security-provenance-review-report": security_provenance_review,
        "benchmark-manifest": benchmark_info,
        "scientific-claim-coverage-report": scientific_claim_coverage,
        "validation-dossier": dossier,
        "adapter-validation-report": dossier["adapterInteroperability"],
        "known-gap-report": known_gap_report,
    }


def write_release_bundle(repo_root: Path, output_dir: Path | None = None, release_ref: str | None = None) -> Path:
    reports = build_release_reports(repo_root)
    release_ref = release_ref or f"v{VERSION}"
    bundle_dir = output_dir or repo_root / "docs" / "releases" / f"v{VERSION}"
    bundle_dir.mkdir(parents=True, exist_ok=True)

    bundle_texts: dict[str, str] = {
        filename: _json_text(reports[report_name]) for report_name, filename in REPORT_FILENAMES
    }
    bundle_texts["release-notes.md"] = _render_release_notes(reports, release_ref)
    bundle_texts["README.md"] = _render_release_bundle_readme(reports, release_ref)

    for filename, text in bundle_texts.items():
        (bundle_dir / filename).write_text(text)

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
        help="Release reference label to embed in the generated bundle, for example a tag such as v0.1.0.",
    )
    args = parser.parse_args()
    bundle_dir = write_release_bundle(Path.cwd(), output_dir=args.output_dir, release_ref=args.release_ref)
    print(bundle_dir)
