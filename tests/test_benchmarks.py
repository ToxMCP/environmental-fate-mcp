from pathlib import Path

from fate_mcp.benchmarks import benchmark_manifest, run_benchmarks


def test_benchmark_fixtures_pass() -> None:
    results = run_benchmarks(Path(__file__).resolve().parents[1])
    assert results["passed"] is True
    assert results["benchmarkCount"] >= 35
    assert results["scientificValidationClaimCoverage"]["uncovered_mandatory_claim_count"] == 0
    by_name = {item["name"]: item for item in results["results"]}
    assert by_name["advective_degradation_dominant_loss_share_anchor_fixture"]["traceTermComparisons"]
    assert by_name["advective_clearance_dominant_loss_share_anchor_fixture"]["traceTermComparisons"]
    assert by_name["advective_mixed_loss_transition_anchor_fixture"]["traceTermComparisons"]
    assert by_name["advective_transition_flip_to_degradation_fixture"]["traceTermComparisons"]
    assert by_name["advective_transition_flip_to_clearance_fixture"]["traceTermComparisons"]
    assert by_name["advective_bounded_transport_reference_fixture"]["traceTermComparisons"]
    assert by_name["advective_flow_through_transport_reference_fixture"]["traceTermComparisons"]
    assert by_name["advective_transition_boundary_reference_fixture"]["traceTermComparisons"]
    assert by_name["advective_storage_dominant_transport_reference_fixture"]["traceTermComparisons"]
    assert by_name["advective_post_release_decay_anchor_fixture"]["traceTermComparisons"]
    assert by_name["advective_post_release_pre_half_recovery_sensitivity_fixture"]["traceTermComparisons"]
    assert by_name["advective_post_release_half_recovery_reference_fixture"]["traceTermComparisons"]
    assert by_name["advective_post_release_boundary_transition_reference_fixture"]["traceTermComparisons"]
    assert by_name["advective_post_release_subboundary_directionality_sensitivity_fixture"]["traceTermComparisons"]
    assert by_name["advective_post_release_recovery_reference_fixture"]["traceTermComparisons"]
    assert by_name["advective_post_release_recovery_sensitivity_fixture"]["traceTermComparisons"]
    assert by_name["advective_post_release_extended_flushing_sensitivity_fixture"]["traceTermComparisons"]
    assert by_name["advective_post_release_late_recovery_reference_fixture"]["traceTermComparisons"]
    assert by_name["advective_post_release_late_recovery_edge_anchor"]["traceTermComparisons"]
    assert by_name["external_adapter_equivalence_fixture"]["comparisons"]
    assert by_name["advective_degradation_dominant_loss_share_anchor_fixture"]["passed"] is True
    assert by_name["advective_clearance_dominant_loss_share_anchor_fixture"]["passed"] is True
    assert by_name["advective_mixed_loss_transition_anchor_fixture"]["passed"] is True
    assert by_name["advective_bounded_transport_reference_fixture"]["passed"] is True
    assert by_name["advective_flow_through_transport_reference_fixture"]["passed"] is True
    assert by_name["advective_transition_boundary_reference_fixture"]["passed"] is True
    assert by_name["advective_storage_dominant_transport_reference_fixture"]["passed"] is True
    assert by_name["advective_post_release_pre_half_recovery_sensitivity_fixture"]["passed"] is True
    assert by_name["advective_post_release_half_recovery_reference_fixture"]["passed"] is True
    assert by_name["advective_post_release_boundary_transition_reference_fixture"]["passed"] is True
    assert by_name["advective_post_release_subboundary_directionality_sensitivity_fixture"]["passed"] is True
    assert by_name["advective_post_release_recovery_reference_fixture"]["passed"] is True
    assert by_name["advective_post_release_extended_flushing_sensitivity_fixture"]["passed"] is True
    assert by_name["advective_post_release_late_recovery_reference_fixture"]["passed"] is True
    assert by_name["advective_post_release_late_recovery_edge_anchor"]["passed"] is True
    assert by_name["external_adapter_equivalence_fixture"]["passed"] is True


def test_benchmark_manifest_includes_metadata_for_all_fixtures() -> None:
    manifest = benchmark_manifest()
    required_fields = {
        "category",
        "validation_tier",
        "scientific_basis",
        "reference_type",
        "expected_behavior",
        "tolerance_rationale",
        "scientific_claim_ids",
    }
    assert manifest["fixtures"]
    assert all(required_fields.issubset(fixture.keys()) for fixture in manifest["fixtures"])
    assert manifest["scientificValidationClaimManifest"]["claim_count"] >= 18
    assert manifest["scientificValidationClaimCoverage"]["uncovered_mandatory_claim_count"] == 0
    coverage = {
        item["claim_id"]: item
        for item in manifest["scientificValidationClaimCoverage"]["coverage"]
    }
    assert coverage["reference_air_finite_duration_first_order_v1"]["support_strength"] == "multi_anchor_multi_tier"
    assert coverage["reference_water_finite_duration_first_order_v1"]["support_strength"] == "multi_anchor_multi_tier"
    assert coverage["reference_soil_finite_duration_first_order_v1"]["support_strength"] == "multi_anchor_multi_tier"
    assert coverage["reference_sediment_finite_duration_first_order_v1"]["support_strength"] == "multi_anchor_multi_tier"
    assert coverage["reference_multi_medium_partition_v1"]["support_strength"] == "multi_anchor_multi_tier"
    assert coverage["reference_time_bucket_elapsed_time_v1"]["support_strength"] == "multi_anchor_multi_tier"
    assert coverage["reference_parameter_override_application_v1"]["support_strength"] == "multi_anchor_multi_tier"
    assert coverage["reference_executable_treatment_reduction_v1"]["support_strength"] == "multi_anchor_multi_tier"
    assert coverage["reference_short_half_life_attenuation_v1"]["support_strength"] == "multi_anchor_multi_tier"
    assert coverage["reference_long_duration_rate_anchor_v1"]["support_strength"] == "multi_anchor_multi_tier"
    assert coverage["advective_water_finite_duration_first_order_v1"]["support_strength"] in {
        "multi_anchor_single_tier",
        "multi_anchor_multi_tier",
    }
    assert coverage["advective_time_bucket_elapsed_time_v1"]["support_strength"] in {
        "multi_anchor_single_tier",
        "multi_anchor_multi_tier",
    }
    assert coverage["advective_post_release_flushing_recovery_v1"]["support_strength"] == "multi_anchor_multi_tier"
    assert "reference_style" in coverage["advective_post_release_flushing_recovery_v1"]["supporting_validation_tiers"]
    assert {
        "hand_worked_advective_post_release_bucket_anchor",
        "hand_worked_advective_post_release_recovery_reference_fixture",
        "hand_worked_advective_post_release_recovery_sensitivity_fixture",
    }.issubset(
        set(coverage["advective_post_release_flushing_recovery_v1"]["supporting_reference_types"])
    )
    assert coverage["advective_post_release_flushing_regime_transition_v1"]["support_strength"] == "multi_anchor_multi_tier"
    assert "reference_style" in coverage["advective_post_release_flushing_regime_transition_v1"]["supporting_validation_tiers"]
    assert {
        "hand_worked_advective_post_release_bucket_anchor",
        "hand_worked_advective_post_release_boundary_transition_reference_fixture",
        "hand_worked_advective_post_release_recovery_reference_fixture",
        "hand_worked_advective_post_release_recovery_sensitivity_fixture",
        "hand_worked_advective_post_release_extended_flushing_sensitivity_fixture",
    }.issubset(
        set(coverage["advective_post_release_flushing_regime_transition_v1"]["supporting_reference_types"])
    )
    assert coverage["advective_post_release_flushing_directionality_v1"]["support_strength"] == "multi_anchor_multi_tier"
    assert "reference_style" in coverage["advective_post_release_flushing_directionality_v1"]["supporting_validation_tiers"]
    assert {
        "hand_worked_advective_post_release_bucket_anchor",
        "hand_worked_advective_post_release_subboundary_sensitivity_fixture",
        "hand_worked_advective_post_release_boundary_transition_reference_fixture",
        "hand_worked_advective_post_release_recovery_reference_fixture",
        "hand_worked_advective_post_release_extended_flushing_sensitivity_fixture",
    }.issubset(
        set(coverage["advective_post_release_flushing_directionality_v1"]["supporting_reference_types"])
    )
    assert coverage["advective_post_release_half_recovery_pace_v1"]["support_strength"] == "multi_anchor_multi_tier"
    assert "reference_style" in coverage["advective_post_release_half_recovery_pace_v1"]["supporting_validation_tiers"]
    assert {
        "hand_worked_advective_post_release_bucket_anchor",
        "hand_worked_advective_post_release_pre_half_recovery_sensitivity_fixture",
        "hand_worked_advective_post_release_half_recovery_reference_fixture",
        "hand_worked_advective_post_release_recovery_reference_fixture",
    }.issubset(
        set(coverage["advective_post_release_half_recovery_pace_v1"]["supporting_reference_types"])
    )
    assert coverage["advective_post_release_half_recovery_directionality_v1"]["support_strength"] == "multi_anchor_multi_tier"
    assert "reference_style" in coverage["advective_post_release_half_recovery_directionality_v1"]["supporting_validation_tiers"]
    assert {
        "hand_worked_advective_post_release_bucket_anchor",
        "hand_worked_advective_post_release_pre_half_recovery_sensitivity_fixture",
        "hand_worked_advective_post_release_half_recovery_reference_fixture",
        "hand_worked_advective_post_release_recovery_reference_fixture",
        "hand_worked_advective_post_release_extended_flushing_sensitivity_fixture",
    }.issubset(
        set(
            coverage["advective_post_release_half_recovery_directionality_v1"][
                "supporting_reference_types"
            ]
        )
    )
    assert coverage["advective_degradation_dominant_loss_share_v1"]["support_strength"] == "multi_anchor_multi_tier"
    assert coverage["advective_clearance_dominant_loss_share_v1"]["support_strength"] == "multi_anchor_multi_tier"
    assert coverage["advective_mixed_loss_transition_margin_v1"]["support_strength"] == "multi_anchor_multi_tier"
    assert "reference_style" in coverage["advective_mixed_loss_transition_margin_v1"]["supporting_validation_tiers"]
    assert (
        "hand_worked_advective_transition_boundary_reference_fixture"
        in coverage["advective_mixed_loss_transition_margin_v1"]["supporting_reference_types"]
    )
    assert coverage["advective_loss_regime_flip_directionality_v1"]["support_strength"] == "multi_anchor_multi_tier"
    assert coverage["advective_cumulative_mass_balance_closure_v1"]["support_strength"] == "multi_anchor_multi_tier"
    assert coverage["advective_residence_time_turnover_regime_v1"]["support_strength"] == "multi_anchor_multi_tier"
    assert "reference_style" in coverage["advective_residence_time_turnover_regime_v1"]["supporting_validation_tiers"]
    assert {
        "hand_worked_advective_bounded_transport_reference_fixture",
        "hand_worked_advective_flow_through_transport_reference_fixture",
        "hand_worked_advective_storage_dominant_transport_reference_fixture",
        "hand_worked_advective_transition_boundary_reference_fixture",
    }.issubset(set(coverage["advective_residence_time_turnover_regime_v1"]["supporting_reference_types"]))
    assert coverage["advective_residence_time_override_application_v1"]["covered"] is True
    assert coverage["advective_short_residence_time_clearance_anchor_v1"]["covered"] is True
    assert coverage["advective_long_duration_combined_loss_plateau_v1"]["covered"] is True
    assert coverage["advective_long_residence_time_accumulation_anchor_v1"]["covered"] is True
    assert coverage["advective_short_residence_time_clearance_anchor_v1"]["support_strength"] in {
        "multi_anchor_single_tier",
        "multi_anchor_multi_tier",
    }
    assert coverage["advective_long_duration_combined_loss_plateau_v1"]["support_strength"] == "multi_anchor_multi_tier"
    assert coverage["advective_long_residence_time_accumulation_anchor_v1"]["support_strength"] in {
        "multi_anchor_single_tier",
        "multi_anchor_multi_tier",
    }
