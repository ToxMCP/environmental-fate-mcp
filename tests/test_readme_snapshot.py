from pathlib import Path

from fate_mcp.release_artifacts import build_release_reports


def test_readme_release_snapshot_counts_are_current() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    reports = build_release_reports(repo_root)
    metadata = reports["metadata-report"]
    readme = (repo_root / "README.md").read_text()

    expected_lines = [
        f"- `{metadata['testCount']}` repository tests",
        f"- `{metadata['schemaCount']}` JSON schemas",
        f"- `{metadata['exampleCount']}` generated examples",
        (
            f"- `{len(metadata['supportedWorkflows'])}` supported workflows surfaced through "
            f"`{metadata['toolCount']}` tools, `{metadata['promptCount']}` prompts, and "
            f"`{metadata['resourceCount']}` resources"
        ),
        f"- `{metadata['scientificValidationClaimCount']}` governed scientific validation claims with plugin-code traceability",
        f"- `{metadata['scientificReferenceCaseCount']}` governed scientific reference cases",
        f"- `{metadata['regulatoryHandoffProfileCount']}` governed regulatory handoff profiles with downstream acknowledgement schema URLs",
        (
            f"- `{len(metadata['supportedModelFamilies'])}` supported model families and "
            f"`{metadata['experimentalModelFamilyCount']}` experimental model family"
        ),
    ]

    for line in expected_lines:
        assert line in readme
