from pathlib import Path

from fate_mcp.validation import validate_scientific_claim_freshness


def test_scientific_claim_freshness_passes() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    result = validate_scientific_claim_freshness(repo_root)
    assert result["passed"] is True
    assert result["staleClaimCount"] == 0
    assert result["unresolvableReferenceCount"] == 0
    assert result["claimsMissingModelFamilyPluginCount"] == 0
