from pathlib import Path

from fate_mcp.evidence_quality import build_scientific_evidence_quality_matrix_report


def test_scientific_evidence_quality_matrix_covers_claims_and_families() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    report = build_scientific_evidence_quality_matrix_report(repo_root)
    assert report.passed is True
    assert report.claim_row_count == 34
    assert report.model_family_row_count == 5
    family_rows = {row.model_family.value: row for row in report.model_family_rows}
    assert {
        "adapter_stub",
        "advective_screening_mass_balance",
        "external_result_adapter",
        "fugacity_equilibrium_screening",
        "reference_mass_balance",
    } == set(family_rows)
    assert family_rows["reference_mass_balance"].trust_tier.value == "reviewer_grade_screening"
    assert family_rows["advective_screening_mass_balance"].trust_tier.value == (
        "source_grounded_screening"
    )
    assert family_rows["fugacity_equilibrium_screening"].trust_tier.value == (
        "source_grounded_screening"
    )
    assert family_rows["adapter_stub"].trust_tier.value == "deferred_or_gap"


def test_scientific_evidence_quality_matrix_blocks_false_claim_flags() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    report = build_scientific_evidence_quality_matrix_report(repo_root)
    all_rows = [*report.claim_rows, *report.model_family_rows]
    assert all(not row.field_validation_present for row in all_rows)
    assert all(not row.calibration_claim_present for row in all_rows)
    assert all(not row.regulatory_acceptance_claim_present for row in all_rows)
    assert all(not row.source_engine_equivalence_claim_present for row in all_rows)
    assert all(row.limitations for row in all_rows)
    assert all(row.next_corroboration_action for row in all_rows)


def test_experimental_families_are_not_promoted_to_reviewer_grade() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    report = build_scientific_evidence_quality_matrix_report(repo_root)
    experimental_rows = [row for row in report.model_family_rows if row.experimental]
    assert experimental_rows
    assert all(row.trust_tier.value != "reviewer_grade_screening" for row in experimental_rows)
    assert all("experimental" in " ".join(row.limitations).lower() for row in experimental_rows)
