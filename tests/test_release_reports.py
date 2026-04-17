import json
from hashlib import sha256
from pathlib import Path

from fate_mcp.contracts import generate_contract_artifacts
from fate_mcp.release_artifacts import build_release_reports, write_release_bundle


def test_release_reports_include_validation_and_known_gaps() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    generate_contract_artifacts(repo_root)
    reports = build_release_reports(repo_root)
    assert "adapter-validation-report" in reports
    assert "benchmark-manifest" in reports
    assert "scientific-claim-coverage-report" in reports
    assert "validation-dossier" in reports
    assert "known-gap-report" in reports
    assert reports["validation-dossier"]["benchmarks"]["passed"] is True
    assert reports["validation-dossier"]["adapterInteroperability"]["passed"] is True
    assert reports["validation-dossier"]["regulatoryHandoffGovernance"]["passed"] is True
    assert reports["validation-dossier"]["reconciliationTransparency"]["passed"] is True
    assert reports["validation-dossier"]["scientificReviewArtifacts"]["passed"] is True
    assert reports["validation-dossier"]["scientificClaimCoverage"]["passed"] is True
    assert reports["validation-dossier"]["scientificClaimCoverage"][
        "claimsWithUnresolvedReferenceCaseIds"
    ] == []
    assert reports["validation-dossier"]["scientificClaimCoverage"][
        "experimentalPriorityClaimsMissingReferenceCaseIds"
    ] == []
    assert reports["validation-dossier"]["scientificClaimCoverage"][
        "referenceMandatoryClaimsMissingReferenceCaseIds"
    ] == []
    assert reports["validation-dossier"]["scientificClaimCoverage"][
        "referenceMandatorySingleReferenceCaseClaimIds"
    ] == []
    assert reports["validation-dossier"]["scientificClaimCoverage"][
        "referenceMandatorySingleAnchorClaimIds"
    ] == []
    assert reports["validation-dossier"]["scientificClaimCoverage"][
        "referenceMandatorySingleTierClaimIds"
    ] == []
    assert reports["validation-dossier"]["scientificClaimCoverage"][
        "highPriorityExperimentalSingleReferenceCaseClaimIds"
    ] == []
    assert reports["validation-dossier"]["scientificClaimCoverage"][
        "mediumPriorityExperimentalSingleReferenceCaseClaimIds"
    ] == []
    assert reports["validation-dossier"]["scientificClaimCoverage"][
        "highPriorityExperimentalSingleTierClaimIds"
    ] == []
    assert reports["validation-dossier"]["scientificClaimCoverage"][
        "mediumPriorityExperimentalSingleTierClaimIds"
    ] == []
    assert reports["validation-dossier"]["scientificReviewWorkflow"]["passed"] is True
    assert reports["validation-dossier"]["scientificMethodsDossierWorkflow"]["passed"] is True
    assert reports["validation-dossier"]["modelFamilySelectionWorkflow"]["passed"] is True
    assert reports["validation-dossier"]["modelFamilySelectionReviewWorkflow"]["passed"] is True
    assert reports["validation-dossier"]["modelFamilyChallengeReviewWorkflow"]["passed"] is True
    assert reports["validation-dossier"]["modelFamilyChallengeScientificDossierWorkflow"]["passed"] is True
    assert reports["validation-dossier"]["modelFamilyComparisonWorkflow"]["passed"] is True
    assert reports["validation-dossier"]["modelFamilyComparisonReviewWorkflow"]["passed"] is True
    assert reports["validation-dossier"]["downstreamInteroperability"]["surfacesHaveCalculationTraces"] is True
    assert reports["validation-dossier"]["downstreamInteroperability"]["bundleHasIntegrityHash"] is True
    assert reports["validation-dossier"]["downstreamInteroperability"]["bundleHasRegulatoryUseDisclaimer"] is True
    assert reports["validation-dossier"]["downstreamInteroperability"]["regulatoryPackageHasIntegrityHash"] is True
    assert (
        reports["validation-dossier"]["downstreamInteroperability"][
            "regulatoryPackageHasRegulatoryUseDisclaimer"
        ]
        is True
    )
    assert reports["validation-dossier"]["scientificReviewArtifacts"]["surfacesHaveEquationTraces"] is True
    assert reports["validation-dossier"]["downstreamInteroperability"]["regulatoryReviewPacketMatchesPackage"] is True
    assert reports["validation-dossier"]["downstreamInteroperability"]["regulatoryReviewBriefMatchesPacket"] is True
    assert reports["adapter-validation-report"]["passed"] is True
    assert (
        reports["security-provenance-review-report"]["status"]
        == "documented_provenance_controls_with_declared_scope_limits"
    )
    assert reports["security-provenance-review-report"]["scope"]
    assert reports["security-provenance-review-report"]["controls"]
    assert reports["security-provenance-review-report"]["limitations"]
    assert reports["metadata-report"]["regulatoryHandoffProfileCount"] >= 2
    assert reports["metadata-report"]["regulatoryHandoffPromptTemplateCount"] >= 2
    assert reports["metadata-report"]["regulatoryHandoffConsumerHintCount"] >= 4
    assert reports["metadata-report"]["regulatoryHandoffReviewChecklistCount"] >= 2
    assert reports["metadata-report"]["regulatoryHandoffReviewBriefTemplateCount"] >= 2
    assert reports["metadata-report"]["regulatoryHandoffAliasCount"] >= 4
    assert reports["metadata-report"]["regulatoryHandoffAliasConflictCount"] == 0
    assert reports["metadata-report"]["regulatoryHandoffTargetMappingCount"] >= 2
    assert reports["metadata-report"]["modelFamilyApplicabilityProfileCount"] >= 3
    assert reports["metadata-report"]["scientificValidationClaimCount"] >= 10
    assert reports["metadata-report"]["scientificValidationMandatoryClaimCount"] >= 10
    assert reports["metadata-report"]["scientificValidationCoveredClaimCount"] >= 10
    assert reports["metadata-report"]["scientificValidationUncoveredMandatoryClaimCount"] == 0
    assert reports["metadata-report"]["scientificReferenceCaseCount"] >= 13
    assert reports["metadata-report"]["scientificValidationMappedReferenceCaseClaimCount"] >= 16
    assert reports["metadata-report"]["scientificValidationReferenceMandatoryMappedReferenceCaseClaimCount"] >= 10
    assert reports["metadata-report"]["scientificValidationReferenceMandatorySingleReferenceCaseClaimCount"] == 0
    assert reports["metadata-report"]["scientificValidationReferenceMandatoryMultiReferenceCaseClaimCount"] >= 10
    assert reports["metadata-report"]["scientificValidationReferenceMandatorySingleAnchorClaimCount"] == 0
    assert reports["metadata-report"]["scientificValidationReferenceMandatoryMultiAnchorClaimCount"] >= 10
    assert reports["metadata-report"]["scientificValidationReferenceMandatorySingleTierClaimCount"] == 0
    assert reports["metadata-report"]["scientificValidationReferenceMandatoryMultiTierClaimCount"] >= 10
    assert reports["metadata-report"]["scientificValidationHighPriorityExperimentalSingleReferenceCaseClaimCount"] == 0
    assert reports["metadata-report"]["scientificValidationHighPriorityExperimentalMultiReferenceCaseClaimCount"] >= 3
    assert reports["metadata-report"]["scientificValidationMediumPriorityExperimentalSingleReferenceCaseClaimCount"] == 0
    assert reports["metadata-report"]["scientificValidationMediumPriorityExperimentalMultiReferenceCaseClaimCount"] >= 4
    assert reports["metadata-report"]["scientificValidationClaimSourceReferenceCount"] >= 20
    assert reports["metadata-report"]["scientificValidationExternalSourceReferenceCount"] >= 16
    assert reports["metadata-report"]["scientificValidationClaimMethodsBasisLineCount"] >= 20
    assert reports["metadata-report"]["scientificValidationClaimReferenceCaseLineCount"] >= 10
    assert reports["metadata-report"]["scientificValidationHighPriorityExperimentalSingleAnchorClaimCount"] == 0
    assert reports["metadata-report"]["scientificValidationHighPriorityExperimentalMultiAnchorClaimCount"] >= 3
    assert reports["metadata-report"]["scientificValidationMediumPriorityExperimentalSingleAnchorClaimCount"] == 0
    assert reports["metadata-report"]["scientificValidationMediumPriorityExperimentalMultiAnchorClaimCount"] >= 4
    assert reports["metadata-report"]["scientificValidationHighPriorityExperimentalSingleTierClaimCount"] == 0
    assert reports["metadata-report"]["scientificValidationHighPriorityExperimentalMultiTierClaimCount"] >= 3
    assert reports["metadata-report"]["scientificValidationMediumPriorityExperimentalSingleTierClaimCount"] == 0
    assert reports["metadata-report"]["scientificValidationMediumPriorityExperimentalMultiTierClaimCount"] >= 4
    assert reports["metadata-report"]["modelFamilyComparisonProfileCount"] >= 1
    assert reports["metadata-report"]["modelFamilySelectionProfileCount"] >= 1
    assert reports["metadata-report"]["modelFamilyChallengeReviewProfileCount"] >= 1
    assert reports["metadata-report"]["modelFamilySelectionReviewChecklistCount"] >= 1
    assert reports["metadata-report"]["modelFamilySelectionReviewTemplateCount"] >= 1
    assert reports["metadata-report"]["modelFamilyChallengeReviewChecklistCount"] >= 1
    assert reports["metadata-report"]["modelFamilyChallengeReviewTemplateCount"] >= 1
    assert reports["metadata-report"]["modelFamilyComparisonReviewChecklistCount"] >= 1
    assert reports["metadata-report"]["modelFamilyComparisonReviewTemplateCount"] >= 1
    assert reports["metadata-report"]["scientificReviewProfileCount"] >= 3
    assert reports["metadata-report"]["scientificReviewChecklistCount"] >= 3
    assert reports["metadata-report"]["scientificReviewTemplateCount"] >= 3
    assert reports["metadata-report"]["scientificReviewOutcomeTemplateCount"] >= 3
    assert reports["metadata-report"]["scientificReviewGovernedPolicyCount"] >= 3
    assert reports["metadata-report"]["scientificReviewStatusPolicyCount"] >= 3
    assert reports["metadata-report"]["scientificReviewOutcomePolicyCount"] >= 3
    assert reports["metadata-report"]["scientificReviewDriverActionTemplateCount"] >= 8
    assert reports["metadata-report"]["adapterUnitConversionRuleCount"] >= 4
    assert reports["metadata-report"]["adapterImportProfileCount"] >= 3
    assert reports["metadata-report"]["adapterFixtureCount"] >= 5
    assert reports["metadata-report"]["benchmarkMetadataFixtureCount"] >= 9
    assert reports["metadata-report"]["scientificReviewWorkflowCount"] == 3
    assert reports["metadata-report"]["scientificMethodsDossierWorkflowCount"] == 2
    assert reports["metadata-report"]["modelFamilySelectionWorkflowCount"] == 1
    assert reports["metadata-report"]["modelFamilySelectionReviewWorkflowCount"] == 3
    assert reports["metadata-report"]["modelFamilyChallengeReviewWorkflowCount"] == 3
    assert reports["metadata-report"]["modelFamilyChallengeScientificDossierWorkflowCount"] == 2
    assert reports["metadata-report"]["modelFamilyComparisonWorkflowCount"] == 2
    assert reports["metadata-report"]["modelFamilyComparisonReviewWorkflowCount"] == 3
    assert reports["metadata-report"]["experimentalModelFamilyCount"] >= 1
    assert "advective_screening_mass_balance" in reports["metadata-report"]["experimentalModelFamilies"]
    assert reports["metadata-report"]["parameterManifestEntryCount"] >= 5
    assert reports["metadata-report"]["parameterManifestRuntimeConsumedCount"] >= 3
    assert reports["metadata-report"]["parameterManifestPreservedOnlyCount"] >= 1
    assert reports["metadata-report"]["physchemPolicyFamilyCount"] >= 4
    assert reports["metadata-report"]["physchemPolicyCount"] >= 8
    assert "fate_preview_scientific_review_outcome" in reports["metadata-report"]["supportedWorkflows"]
    assert "fate_preview_regulatory_handoff_resolution" in reports["metadata-report"]["supportedWorkflows"]
    assert "fate_summarize_regulatory_handoff_package" in reports["metadata-report"]["supportedWorkflows"]
    assert "fate_build_regulatory_handoff_review_packet" in reports["metadata-report"]["supportedWorkflows"]
    assert "fate_build_regulatory_handoff_review_brief" in reports["metadata-report"]["supportedWorkflows"]
    assert "fate_build_run_parameter_manifest" in reports["metadata-report"]["supportedWorkflows"]
    assert "fate_build_run_uncertainty_summary" in reports["metadata-report"]["supportedWorkflows"]
    assert "fate_estimate_probabilistic_multimedia_concentrations" in reports["metadata-report"]["supportedWorkflows"]
    assert "fate_build_probabilistic_review_packet" in reports["metadata-report"]["supportedWorkflows"]
    assert "fate_build_probabilistic_review_brief" in reports["metadata-report"]["supportedWorkflows"]
    assert "fate_recommend_model_family_selection" in reports["metadata-report"]["supportedWorkflows"]
    assert "fate_preview_model_family_selection_review" in reports["metadata-report"]["supportedWorkflows"]
    assert "fate_build_model_family_selection_review_packet" in reports["metadata-report"]["supportedWorkflows"]
    assert "fate_build_model_family_selection_review_brief" in reports["metadata-report"]["supportedWorkflows"]
    assert "fate_preview_model_family_challenge_review" in reports["metadata-report"]["supportedWorkflows"]
    assert "fate_build_model_family_challenge_review_packet" in reports["metadata-report"]["supportedWorkflows"]
    assert "fate_build_model_family_challenge_review_brief" in reports["metadata-report"]["supportedWorkflows"]
    assert "fate_build_model_family_challenge_scientific_dossier" in reports["metadata-report"]["supportedWorkflows"]
    assert "fate_build_model_family_challenge_scientific_dossier_brief" in reports["metadata-report"]["supportedWorkflows"]
    assert "fate_build_scientific_review_packet" in reports["metadata-report"]["supportedWorkflows"]
    assert "fate_build_scientific_review_brief" in reports["metadata-report"]["supportedWorkflows"]
    assert "fate_build_scientific_methods_dossier" in reports["metadata-report"]["supportedWorkflows"]
    assert "fate_build_scientific_methods_dossier_brief" in reports["metadata-report"]["supportedWorkflows"]
    assert "fate_build_model_family_comparison_packet" in reports["metadata-report"]["supportedWorkflows"]
    assert "fate_build_model_family_comparison_brief" in reports["metadata-report"]["supportedWorkflows"]
    assert "fate_preview_model_family_comparison_review" in reports["metadata-report"]["supportedWorkflows"]
    assert "fate_build_model_family_comparison_review_packet" in reports["metadata-report"]["supportedWorkflows"]
    assert "fate_build_model_family_comparison_review_brief" in reports["metadata-report"]["supportedWorkflows"]


def test_write_release_bundle_is_deterministic_and_checksumed(tmp_path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    generate_contract_artifacts(repo_root)
    bundle_dir = tmp_path / "v0.1.0-test"
    result_dir = write_release_bundle(repo_root, output_dir=bundle_dir, release_ref="v0.1.0-test")
    assert result_dir == bundle_dir

    manifest = json.loads((bundle_dir / "release-bundle-manifest.json").read_text())
    assert manifest["version"] == "0.1.0"
    assert manifest["releaseRef"] == "v0.1.0-test"

    release_notes = (bundle_dir / "release-notes.md").read_text()
    assert "# Environmental Fate MCP v0.1.0-test" in release_notes
    assert "Release status: `ready_for_screening_release`" in release_notes
    assert "Machine-readable release reports are published" in release_notes

    bundle_readme = (bundle_dir / "README.md").read_text()
    assert "deterministic public release bundle" in bundle_readme
    assert "release-bundle-manifest.json" in bundle_readme
    assert "SHA256SUMS" in bundle_readme
    assert "release notes for the exact release reference" in bundle_readme

    for item in manifest["files"]:
        digest = sha256((bundle_dir / item["path"]).read_bytes()).hexdigest()
        assert digest == item["sha256"]

    checksum_entries = {}
    for line in (bundle_dir / "SHA256SUMS").read_text().splitlines():
        digest, _, filename = line.partition("  ")
        checksum_entries[filename] = digest
    assert checksum_entries["release-bundle-manifest.json"] == sha256(
        (bundle_dir / "release-bundle-manifest.json").read_bytes()
    ).hexdigest()
    assert checksum_entries["release-notes.md"] == sha256((bundle_dir / "release-notes.md").read_bytes()).hexdigest()

    first_pass = {path.name: path.read_text() for path in bundle_dir.iterdir() if path.is_file()}
    write_release_bundle(repo_root, output_dir=bundle_dir, release_ref="v0.1.0-test")
    second_pass = {path.name: path.read_text() for path in bundle_dir.iterdir() if path.is_file()}
    assert first_pass == second_pass
