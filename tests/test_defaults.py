from pathlib import Path

from fate_mcp.defaults import DefaultsRegistry
from fate_mcp.models import Media


def test_defaults_manifest_contains_versioned_files() -> None:
    registry = DefaultsRegistry(Path(__file__).resolve().parents[1])
    manifest = registry.build_manifest()
    assert manifest["defaultsVersion"] == "v1"
    assert any(item["path"].endswith("adapter_unit_conversions.json") for item in manifest["files"])
    assert any(item["path"].endswith("core_defaults.json") for item in manifest["files"])
    assert any(item["path"].endswith("model_family_applicability_profiles.json") for item in manifest["files"])
    assert any(item["path"].endswith("model_family_comparison_profiles.json") for item in manifest["files"])
    assert any(item["path"].endswith("model_family_selection_profiles.json") for item in manifest["files"])
    assert any(item["path"].endswith("model_family_challenge_review_profiles.json") for item in manifest["files"])
    assert any(item["path"].endswith("scientific_reference_cases.json") for item in manifest["files"])
    assert any(item["path"].endswith("scientific_validation_claims.json") for item in manifest["files"])
    assert any(item["path"].endswith("scientific_review_profiles.json") for item in manifest["files"])
    assert any(item["path"].endswith("nordic_screening_pack.json") for item in manifest["files"])
    assert any(item["path"].endswith("regulatory_handoff_profiles.json") for item in manifest["files"])


def test_region_profile_manifest_includes_extension_pack() -> None:
    registry = DefaultsRegistry(Path(__file__).resolve().parents[1])
    manifest = registry.region_profile_manifest()
    ids = {profile["region_id"] for profile in manifest["profiles"]}
    assert "eu_screening_default" in ids
    assert "us_epa_default" in ids
    assert "nordic_screening_extension" in ids


def test_temperature_correction_policy_is_governed() -> None:
    registry = DefaultsRegistry(Path(__file__).resolve().parents[1])
    policy = registry.temperature_correction_policy()
    assert policy.reference_temperature_c == 25.0
    assert policy.minimum_supported_temperature_c == 0.0
    assert policy.maximum_supported_temperature_c == 40.0
    assert policy.degradation_q10_by_medium[Media.WATER] == 2.0


def test_core_defaults_are_source_backed_and_free_of_shipped_tier3_assumptions() -> None:
    registry = DefaultsRegistry(Path(__file__).resolve().parents[1])
    parameters = registry.core_defaults["parameters"]
    assert parameters
    assert not any(
        payload.get("evidenceTier") == "tier_3_internal_screening_assumption"
        for payload in parameters.values()
    )
    for parameter in parameters:
        assert registry.parameter_source_references(parameter)
        derivation_metadata = registry.parameter_derivation_metadata(parameter)
        assert derivation_metadata.get("jurisdiction")
        assert derivation_metadata.get("basis")
        assert derivation_metadata.get("calculationMethod")
        assert derivation_metadata.get("validityNote")


def test_model_family_applicability_profiles_cover_supported_model_families() -> None:
    registry = DefaultsRegistry(Path(__file__).resolve().parents[1])
    manifest = registry.model_family_applicability_manifest()
    profiles = {profile["model_family"]: profile for profile in manifest["profiles"]}
    assert manifest["profileCount"] >= 4
    assert "advective_screening_mass_balance" in profiles
    assert "reference_mass_balance" in profiles
    assert "external_result_adapter" in profiles
    assert "adapter_stub" in profiles
    assert profiles["reference_mass_balance"]["required_inputs"]
    assert profiles["reference_mass_balance"]["core_assumptions"]
    assert profiles["reference_mass_balance"]["review_notes"]
    assert profiles["advective_screening_mass_balance"]["required_inputs"]
    assert profiles["advective_screening_mass_balance"]["core_assumptions"]
    assert registry.model_family_applicability_profile("missing_model_family") is None


def test_scientific_validation_claims_are_governed_and_cover_primary_families() -> None:
    registry = DefaultsRegistry(Path(__file__).resolve().parents[1])
    manifest = registry.scientific_validation_claim_manifest()
    claims = {claim.claim_id: claim for claim in manifest.claims}
    assert manifest.claim_count >= 26
    assert manifest.mandatory_claim_count >= 17
    assert claims["reference_water_finite_duration_first_order_v1"].model_family.value == "reference_mass_balance"
    assert [mode.value for mode in claims["reference_time_bucket_elapsed_time_v1"].supported_run_modes] == [
        "time_bucket"
    ]
    assert claims["advective_water_finite_duration_first_order_v1"].model_family.value == "advective_screening_mass_balance"
    assert claims["advective_residence_time_override_application_v1"].required_validation_tiers == ["sensitivity"]
    assert claims["advective_short_residence_time_clearance_anchor_v1"].required_reference_types == [
        "hand_worked_advective_clearance_edge_anchor"
    ]
    assert claims["advective_degradation_dominant_loss_share_v1"].required_validation_tiers == [
        "edge_condition",
        "sensitivity",
    ]
    assert claims["advective_clearance_dominant_loss_share_v1"].required_validation_tiers == [
        "edge_condition",
        "sensitivity",
    ]
    assert claims["advective_mixed_loss_transition_margin_v1"].required_validation_tiers == [
        "edge_condition",
        "reference_style",
        "sensitivity",
    ]
    assert claims["advective_mixed_loss_transition_margin_v1"].required_reference_types == [
        "hand_worked_advective_loss_transition_anchor",
        "hand_worked_advective_transition_boundary_reference_fixture",
    ]
    assert claims["advective_loss_regime_flip_directionality_v1"].required_validation_tiers == [
        "edge_condition",
        "sensitivity",
    ]
    assert claims["advective_cumulative_mass_balance_closure_v1"].required_validation_tiers == [
        "edge_condition",
        "sensitivity",
    ]
    assert claims["advective_cumulative_mass_balance_closure_v1"].required_reference_types == [
        "hand_worked_advective_loss_dominance_anchor",
        "hand_worked_advective_loss_transition_anchor",
    ]
    assert claims["advective_residence_time_turnover_regime_v1"].required_validation_tiers == [
        "edge_condition",
        "reference_style",
        "sensitivity",
    ]
    assert claims["advective_residence_time_turnover_regime_v1"].required_reference_types == [
        "hand_worked_advective_clearance_edge_anchor",
        "hand_worked_advective_residence_edge_anchor",
        "hand_worked_advective_loss_transition_anchor",
        "hand_worked_advective_bounded_transport_reference_fixture",
        "hand_worked_advective_flow_through_transport_reference_fixture",
        "hand_worked_advective_storage_dominant_transport_reference_fixture",
        "hand_worked_advective_transition_boundary_reference_fixture",
    ]
    assert claims["advective_long_duration_combined_loss_plateau_v1"].required_reference_types == [
        "hand_worked_advective_duration_edge_anchor"
    ]
    assert claims["advective_long_residence_time_accumulation_anchor_v1"].required_reference_types == [
        "hand_worked_advective_residence_edge_anchor"
    ]
    assert claims["external_adapter_canonical_equivalence_v1"].model_family.value == "external_result_adapter"
    assert (
        claims["reference_water_finite_duration_first_order_v1"].corroboration_status.value
        == "multi_official_multi_jurisdiction"
    )
    assert claims["reference_water_finite_duration_first_order_v1"].official_source_count >= 2
    assert (
        claims["reference_water_finite_duration_first_order_v1"].jurisdiction_breadth.value
        == "multi_jurisdiction"
    )
    assert (
        claims["reference_water_finite_duration_first_order_v1"].evidence_family
        == "official_guidance_plus_independent_machine_readable_worksheet"
    )
    assert claims["reference_water_finite_duration_first_order_v1"].official_source_ids == [
        "oecd.test_guidelines.section3",
        "epa.environmental_models_guidance",
    ]
    assert (
        claims["reference_water_finite_duration_first_order_v1"].worksheet_artifact_path
        == "reference-worksheet-pack/reference_water_finite_duration_first_order_v1.worksheet.json"
    )
    assert (
        claims["reference_water_finite_duration_first_order_v1"].expected_output_artifact_path
        == "reference-worksheet-pack/reference_water_finite_duration_first_order_v1.expected-outputs.json"
    )
    assert claims["reference_water_finite_duration_first_order_v1"].worksheet_status.value == "ready"
    assert str(claims["reference_water_finite_duration_first_order_v1"].last_reviewed_date) == "2026-04-21"
    assert claims["reference_water_finite_duration_first_order_v1"].tolerance_basis
    assert claims["reference_water_finite_duration_first_order_v1"].independent_evidence_families == [
        "oecd_single_medium_first_order_screening_case_family_v1",
        "epa_single_compartment_environmental_screening_case_family_v1",
    ]
    assert claims["reference_water_finite_duration_first_order_v1"].next_corroboration_action
    assert claims["external_adapter_canonical_equivalence_v1"].corroboration_status.value == "none"
    assert claims["external_adapter_canonical_equivalence_v1"].official_source_count == 0
    assert claims["external_adapter_canonical_equivalence_v1"].jurisdiction_breadth.value == "none"
    assert claims["external_adapter_canonical_equivalence_v1"].independent_evidence_families == []
    assert claims["external_adapter_canonical_equivalence_v1"].next_corroboration_action
    assert claims["reference_executable_treatment_reduction_v1"].required_validation_tiers == ["edge_condition"]
    assert claims["reference_water_finite_duration_first_order_v1"].source_references
    assert claims["reference_water_finite_duration_first_order_v1"].methods_basis_lines
    assert claims["reference_water_finite_duration_first_order_v1"].reference_case_lines
    assert claims["reference_water_finite_duration_first_order_v1"].reference_case_ids == [
        "oecd_single_medium_first_order_screening_case_family_v1",
        "epa_single_compartment_environmental_screening_case_family_v1",
    ]
    assert claims["reference_time_bucket_elapsed_time_v1"].reference_case_ids == [
        "epa_elapsed_time_bucket_screening_case_family_v1",
        "oecd_single_medium_first_order_screening_case_family_v1",
    ]
    assert claims["reference_executable_treatment_reduction_v1"].reference_case_ids == [
        "echa_source_term_reduction_screening_case_family_v1",
        "epa_single_compartment_environmental_screening_case_family_v1",
    ]
    assert claims["reference_parameter_override_application_v1"].reference_case_ids == [
        "echa_parameter_transparency_screening_case_family_v1",
        "epa_parameterization_override_screening_case_family_v1",
        "epa_single_compartment_environmental_screening_case_family_v1",
    ]
    assert len(claims["advective_short_residence_time_clearance_anchor_v1"].reference_case_lines) >= 2
    assert len(claims["advective_long_duration_combined_loss_plateau_v1"].reference_case_lines) >= 2
    assert len(claims["advective_long_residence_time_accumulation_anchor_v1"].reference_case_lines) >= 2
    assert claims["advective_water_finite_duration_first_order_v1"].reference_case_ids == [
        "echa_euses_water_screening_case_family_v1",
        "epa_flow_through_water_screening_case_family_v1",
    ]
    assert claims["advective_time_bucket_elapsed_time_v1"].reference_case_ids == [
        "epa_environmental_models_elapsed_time_case_family_v1",
        "epa_post_release_decay_bucket_case_family_v1",
        "echa_elapsed_time_flowing_water_screening_case_family_v1",
    ]
    assert claims["advective_post_release_flushing_recovery_v1"].required_validation_tiers == [
        "edge_condition",
        "reference_style",
        "sensitivity",
    ]
    assert claims["advective_post_release_flushing_recovery_v1"].required_reference_types == [
        "hand_worked_advective_post_release_bucket_anchor",
        "hand_worked_advective_post_release_recovery_reference_fixture",
        "hand_worked_advective_post_release_recovery_sensitivity_fixture",
    ]
    assert claims["advective_post_release_flushing_recovery_v1"].reference_case_ids == [
        "epa_environmental_models_elapsed_time_case_family_v1",
        "epa_post_release_decay_bucket_case_family_v1",
        "epa_post_release_flushing_screening_case_family_v1",
        "oecd_post_release_recovery_screening_case_family_v1",
        "echa_post_release_flushing_boundary_case_family_v1",
    ]
    assert claims["advective_post_release_flushing_regime_transition_v1"].required_validation_tiers == [
        "edge_condition",
        "reference_style",
        "sensitivity",
    ]
    assert claims["advective_post_release_flushing_regime_transition_v1"].required_reference_types == [
        "hand_worked_advective_post_release_bucket_anchor",
        "hand_worked_advective_post_release_boundary_transition_reference_fixture",
        "hand_worked_advective_post_release_recovery_reference_fixture",
        "hand_worked_advective_post_release_recovery_sensitivity_fixture",
        "hand_worked_advective_post_release_extended_flushing_sensitivity_fixture",
    ]
    assert claims["advective_post_release_flushing_regime_transition_v1"].reference_case_ids == [
        "epa_post_release_decay_bucket_case_family_v1",
        "epa_post_release_flushing_screening_case_family_v1",
        "oecd_post_release_recovery_screening_case_family_v1",
        "echa_post_release_flushing_boundary_case_family_v1",
    ]
    assert claims["advective_post_release_flushing_directionality_v1"].required_validation_tiers == [
        "edge_condition",
        "reference_style",
        "sensitivity",
    ]
    assert claims["advective_post_release_flushing_directionality_v1"].required_reference_types == [
        "hand_worked_advective_post_release_bucket_anchor",
        "hand_worked_advective_post_release_subboundary_sensitivity_fixture",
        "hand_worked_advective_post_release_boundary_transition_reference_fixture",
        "hand_worked_advective_post_release_recovery_reference_fixture",
        "hand_worked_advective_post_release_extended_flushing_sensitivity_fixture",
    ]
    assert claims["advective_post_release_flushing_directionality_v1"].reference_case_ids == [
        "epa_post_release_decay_bucket_case_family_v1",
        "epa_post_release_flushing_screening_case_family_v1",
        "oecd_post_release_recovery_screening_case_family_v1",
        "echa_post_release_flushing_boundary_case_family_v1",
        "epa_post_release_directionality_case_family_v1",
    ]
    assert claims["advective_post_release_half_recovery_pace_v1"].required_validation_tiers == [
        "edge_condition",
        "reference_style",
        "sensitivity",
    ]
    assert claims["advective_post_release_half_recovery_pace_v1"].required_reference_types == [
        "hand_worked_advective_post_release_bucket_anchor",
        "hand_worked_advective_post_release_pre_half_recovery_sensitivity_fixture",
        "hand_worked_advective_post_release_half_recovery_reference_fixture",
        "hand_worked_advective_post_release_recovery_reference_fixture",
    ]
    assert claims["advective_post_release_half_recovery_pace_v1"].reference_case_ids == [
        "epa_post_release_decay_bucket_case_family_v1",
        "epa_post_release_flushing_screening_case_family_v1",
        "oecd_post_release_recovery_screening_case_family_v1",
        "echa_post_release_flushing_boundary_case_family_v1",
        "epa_post_release_recovery_pace_case_family_v1",
    ]
    assert claims["advective_post_release_half_recovery_directionality_v1"].required_validation_tiers == [
        "edge_condition",
        "reference_style",
        "sensitivity",
    ]
    assert claims["advective_post_release_half_recovery_directionality_v1"].required_reference_types == [
        "hand_worked_advective_post_release_bucket_anchor",
        "hand_worked_advective_post_release_pre_half_recovery_sensitivity_fixture",
        "hand_worked_advective_post_release_half_recovery_reference_fixture",
        "hand_worked_advective_post_release_recovery_reference_fixture",
        "hand_worked_advective_post_release_extended_flushing_sensitivity_fixture",
    ]
    assert claims["advective_post_release_half_recovery_directionality_v1"].reference_case_ids == [
        "epa_post_release_decay_bucket_case_family_v1",
        "epa_post_release_flushing_screening_case_family_v1",
        "oecd_post_release_recovery_screening_case_family_v1",
        "echa_post_release_flushing_boundary_case_family_v1",
        "epa_post_release_recovery_pace_case_family_v1",
        "oecd_post_release_half_recovery_directionality_case_family_v1",
    ]
    assert set(claims["advective_post_release_late_recovery_regime_v1"].required_validation_tiers) == {
        "sensitivity",
        "reference_style",
        "edge_condition",
    }
    assert set(claims["advective_post_release_late_recovery_regime_v1"].required_reference_types) == {
        "hand_worked_advective_post_release_extended_flushing_sensitivity_fixture",
        "hand_worked_advective_post_release_late_recovery_reference_fixture",
        "hand_worked_advective_post_release_late_recovery_edge_anchor",
    }
    assert claims["advective_extreme_persistence_clearance_bound_v1"].reference_case_ids == [
        "advective_clearance_edge_case_family_v1",
        "echa_bounded_clearance_edge_case_family_v1",
    ]
    assert claims["advective_residence_time_override_application_v1"].reference_case_ids == [
        "echa_euses_water_screening_case_family_v1",
        "advective_clearance_edge_case_family_v1",
        "echa_transition_boundary_screening_case_family_v1",
        "epa_transition_boundary_screening_case_family_v1",
    ]
    assert claims["advective_degradation_dominant_loss_share_v1"].reference_case_ids == [
        "echa_euses_water_screening_case_family_v1",
        "epa_flow_through_water_screening_case_family_v1",
    ]
    assert claims["advective_clearance_dominant_loss_share_v1"].reference_case_ids == [
        "advective_clearance_edge_case_family_v1",
        "echa_bounded_clearance_edge_case_family_v1",
    ]
    assert claims["advective_mixed_loss_transition_margin_v1"].reference_case_ids == [
        "echa_euses_water_screening_case_family_v1",
        "epa_flow_through_water_screening_case_family_v1",
        "echa_transition_boundary_screening_case_family_v1",
        "epa_transition_boundary_screening_case_family_v1",
        "epa_turnover_boundary_screening_case_family_v1",
        "oecd_bounded_transport_screening_case_family_v1",
    ]
    assert claims["advective_cumulative_mass_balance_closure_v1"].reference_case_ids == [
        "echa_euses_water_screening_case_family_v1",
        "epa_flow_through_water_screening_case_family_v1",
        "advective_clearance_edge_case_family_v1",
    ]
    assert claims["advective_residence_time_turnover_regime_v1"].reference_case_ids == [
        "echa_euses_water_screening_case_family_v1",
        "advective_clearance_edge_case_family_v1",
        "echa_transition_boundary_screening_case_family_v1",
        "epa_turnover_boundary_screening_case_family_v1",
        "oecd_bounded_transport_screening_case_family_v1",
    ]
    assert claims["advective_loss_regime_flip_directionality_v1"].reference_case_ids == [
        "echa_transition_boundary_screening_case_family_v1",
        "epa_transition_boundary_screening_case_family_v1",
        "epa_turnover_boundary_screening_case_family_v1",
        "oecd_bounded_transport_screening_case_family_v1",
    ]
    assert claims["advective_short_residence_time_clearance_anchor_v1"].reference_case_ids == [
        "advective_clearance_edge_case_family_v1",
        "echa_bounded_clearance_edge_case_family_v1",
    ]
    assert claims["advective_long_duration_combined_loss_plateau_v1"].reference_case_ids == [
        "advective_duration_plateau_case_family_v1",
        "epa_flow_through_water_screening_case_family_v1",
    ]
    assert claims["advective_long_residence_time_accumulation_anchor_v1"].reference_case_ids == [
        "advective_clearance_edge_case_family_v1",
        "echa_bounded_clearance_edge_case_family_v1",
    ]
    assert any(
        str(reference.url).startswith("https://")
        for reference in claims["reference_water_finite_duration_first_order_v1"].source_references
    )
    assert any(
        str(reference.url).startswith("https://")
        for reference in claims["advective_water_finite_duration_first_order_v1"].source_references
    )
    assert registry.scientific_validation_claim("missing_claim") is None


def test_scientific_reference_cases_are_governed_and_resolvable() -> None:
    registry = DefaultsRegistry(Path(__file__).resolve().parents[1])
    manifest = registry.scientific_reference_case_manifest()
    cases = {case.case_id: case for case in manifest.cases}
    assert manifest.case_count >= 22
    assert [item.value for item in cases["echa_euses_water_screening_case_family_v1"].model_families] == [
        "advective_screening_mass_balance"
    ]
    assert [item.value for item in cases["oecd_single_medium_first_order_screening_case_family_v1"].model_families] == [
        "reference_mass_balance"
    ]
    assert cases["epa_flow_through_water_screening_case_family_v1"].jurisdictions == ["US"]
    assert (
        cases["oecd_single_medium_first_order_screening_case_family_v1"].evidence_family
        == "official_test_guideline_case_family"
    )
    assert cases["oecd_single_medium_first_order_screening_case_family_v1"].official_source_ids
    assert str(cases["oecd_single_medium_first_order_screening_case_family_v1"].last_reviewed_date) == "2026-04-21"
    assert cases["epa_post_release_decay_bucket_case_family_v1"].source_references
    assert cases["epa_post_release_flushing_screening_case_family_v1"].source_references
    assert cases["oecd_post_release_recovery_screening_case_family_v1"].review_notes
    assert cases["echa_post_release_flushing_boundary_case_family_v1"].source_references
    assert cases["epa_post_release_directionality_case_family_v1"].source_references
    assert cases["epa_post_release_recovery_pace_case_family_v1"].source_references
    assert cases["epa_single_compartment_environmental_screening_case_family_v1"].source_references
    assert cases["echa_source_term_reduction_screening_case_family_v1"].review_notes
    assert cases["echa_bounded_clearance_edge_case_family_v1"].review_notes
    assert cases["epa_environmental_models_elapsed_time_case_family_v1"].jurisdictions == ["US"]
    assert cases["advective_clearance_edge_case_family_v1"].source_references
    assert cases["advective_duration_plateau_case_family_v1"].review_notes
    assert cases["epa_transition_boundary_screening_case_family_v1"].source_references
    assert cases["echa_transition_boundary_screening_case_family_v1"].review_notes
    assert cases["epa_turnover_boundary_screening_case_family_v1"].source_references
    assert cases["oecd_bounded_transport_screening_case_family_v1"].review_notes
    advective_cases = registry.list_scientific_reference_cases(model_family="advective_screening_mass_balance")
    assert len(advective_cases) >= 12
    reference_cases = registry.list_scientific_reference_cases(model_family="reference_mass_balance")
    assert len(reference_cases) >= 6
    assert registry.scientific_reference_case("missing_case") is None


def test_model_family_comparison_profiles_are_governed() -> None:
    registry = DefaultsRegistry(Path(__file__).resolve().parents[1])
    manifest = registry.model_family_comparison_profile_manifest()
    profiles = {profile.profile_id: profile for profile in manifest.profiles}
    assert manifest.profile_count >= 1
    profile = profiles["reference_vs_advective_screening_v1"]
    assert profile.base_model_family.value == "reference_mass_balance"
    assert profile.candidate_model_family.value == "advective_screening_mass_balance"
    assert profile.material_relative_delta_threshold == 0.2
    assert profile.material_absolute_delta_floor == 1e-12
    assert profile.packet_template is not None
    assert profile.brief_template is not None
    assert profile.review_checklist
    assert profile.review_packet_template is not None
    assert profile.review_brief_template is not None
    assert profile.ready_comparison_outcomes
    assert profile.attention_outcomes
    assert profile.attention_if_any_checks_fail is True
    assert profile.attention_if_candidate_experimental is True
    assert registry.resolve_model_family_comparison_profile(
        "reference_mass_balance",
        "advective_screening_mass_balance",
    ) is not None
    assert registry.model_family_comparison_profile("missing_profile") is None


def test_model_family_selection_profiles_are_governed() -> None:
    registry = DefaultsRegistry(Path(__file__).resolve().parents[1])
    manifest = registry.model_family_selection_profile_manifest()
    profiles = {profile.profile_id: profile for profile in manifest.profiles}
    assert manifest.profile_count >= 1
    profile = profiles["reference_baseline_advective_challenge_v1"]
    assert profile.default_model_family.value == "reference_mass_balance"
    assert profile.challenge_model_family.value == "advective_screening_mass_balance"
    assert profile.comparison_profile_id == "reference_vs_advective_screening_v1"
    assert profile.minimum_duration_days_for_challenge == 30.0
    assert profile.trigger_parameter_names
    assert profile.default_recommendation_template is not None
    assert profile.challenge_recommendation_template is not None
    assert profile.review_needed_template is not None
    assert profile.review_checklist
    assert profile.review_packet_template is not None
    assert profile.review_brief_template is not None
    assert profile.ready_recommendation_statuses
    assert profile.attention_statuses
    assert profile.attention_if_any_checks_fail is True
    assert profile.attention_if_challenge_experimental is True
    assert registry.model_family_selection_profile("missing_profile") is None


def test_model_family_challenge_review_profiles_are_governed() -> None:
    registry = DefaultsRegistry(Path(__file__).resolve().parents[1])
    manifest = registry.model_family_challenge_review_profile_manifest()
    profiles = {profile.profile_id: profile for profile in manifest.profiles}
    assert manifest.profile_count >= 1
    profile = profiles["reference_baseline_advective_challenge_review_v1"]
    assert profile.selection_profile_id == "reference_baseline_advective_challenge_v1"
    assert profile.comparison_profile_id == "reference_vs_advective_screening_v1"
    assert profile.review_checklist
    assert profile.review_packet_template is not None
    assert profile.review_brief_template is not None
    assert profile.ready_selection_review_statuses == ["ready_for_model_family_selection_review"]
    assert profile.ready_comparison_review_statuses == ["ready_for_model_family_comparison_review"]
    assert profile.attention_if_any_checks_fail is True
    assert profile.attention_if_comparison_missing_when_challenge_recommended is True
    assert profile.ready_action_template is not None
    assert profile.attention_action_template is not None
    assert registry.resolve_model_family_challenge_review_profile(
        "reference_baseline_advective_challenge_v1",
        "reference_vs_advective_screening_v1",
    ) is not None
    assert registry.model_family_challenge_review_profile("missing_profile") is None


def test_scientific_review_profiles_cover_supported_model_families() -> None:
    registry = DefaultsRegistry(Path(__file__).resolve().parents[1])
    manifest = registry.scientific_review_profile_manifest()
    profiles = {profile.model_family.value: profile for profile in manifest.profiles}
    assert manifest.profile_count >= 4
    assert "advective_screening_mass_balance" in profiles
    assert "reference_mass_balance" in profiles
    assert "external_result_adapter" in profiles
    assert profiles["reference_mass_balance"].review_checklist
    assert profiles["advective_screening_mass_balance"].review_checklist
    assert profiles["reference_mass_balance"].packet_template is not None
    assert profiles["reference_mass_balance"].brief_template is not None
    assert profiles["reference_mass_balance"].ready_fit_verdicts == ["good_fit"]
    assert profiles["reference_mass_balance"].attention_outcomes
    assert profiles["reference_mass_balance"].attention_if_any_checks_fail is True
    assert profiles["reference_mass_balance"].acceptable_outcome_template is not None
    assert profiles["reference_mass_balance"].qualified_outcome_template is not None
    assert profiles["reference_mass_balance"].escalation_outcome_template is not None
    assert profiles["reference_mass_balance"].escalation_fit_verdicts
    assert profiles["reference_mass_balance"].escalation_driver_types
    assert profiles["reference_mass_balance"].qualification_driver_types
    assert profiles["adapter_stub"].warning_severity_promotes_qualification is False
    assert profiles["reference_mass_balance"].driver_action_templates
    assert profiles["advective_screening_mass_balance"].driver_action_templates
    assert registry.scientific_review_profile("missing_model_family") is None


def test_physchem_parameter_policy_manifest_is_loaded() -> None:
    registry = DefaultsRegistry(Path(__file__).resolve().parents[1])
    manifest = registry.physchem_parameter_policy_manifest()
    assert manifest["policyCount"] >= 8
    assert manifest["familyCount"] >= 6
    policies = {policy["parameter"]: policy for policy in manifest["policies"]}
    assert policies["water_half_life_days"]["expected_unit"] == "day"
    assert policies["water_half_life_days"]["family"] == "screening_half_life"
    assert policies["water_half_life_days"]["reconciliation_domain"] == "inverse_rate"
    assert policies["water_residence_time_days"]["family"] == "screening_residence_time"
    assert policies["log_kow"]["runtime_supported"] is False
    assert policies["log_kow"]["conflict_metric"] == "absolute_log_spread"


def test_parameter_policy_family_inheritance_supports_overrides() -> None:
    registry = DefaultsRegistry(Path(__file__).resolve().parents[1])
    ambient_air_policy = registry.parameter_policy("ambient_air_volume_m3")
    soil_half_life_policy = registry.parameter_policy("soil_half_life_days")
    assert ambient_air_policy is not None
    assert soil_half_life_policy is not None
    assert ambient_air_policy.family == "screening_capacity_volume"
    assert ambient_air_policy.expected_unit == "m3"
    assert soil_half_life_policy.family == "screening_half_life"
    assert soil_half_life_policy.conflict_relative_spread_threshold == 0.4


def test_physchem_parameter_policy_family_manifest_is_loaded() -> None:
    registry = DefaultsRegistry(Path(__file__).resolve().parents[1])
    manifest = registry.physchem_parameter_policy_family_manifest()
    families = {family["family"]: family for family in manifest["families"]}
    assert manifest["familyCount"] >= 6
    assert families["screening_half_life"]["expected_unit"] == "day"
    assert families["screening_residence_time"]["expected_unit"] == "day"
    assert "water_half_life_days" in families["screening_half_life"]["parameter_names"]
    assert "water_residence_time_days" in families["screening_residence_time"]["parameter_names"]
    assert families["screening_half_life"]["reconciliation_domain"] == "inverse_rate"


def test_adapter_unit_conversion_manifest_is_loaded() -> None:
    registry = DefaultsRegistry(Path(__file__).resolve().parents[1])
    manifest = registry.adapter_unit_conversion_manifest()
    rules = {rule["compartment_code"]: rule for rule in manifest["rules"]}
    assert manifest["ruleCount"] >= 4
    assert rules["WATER_SURFACE"]["canonical_unit"] == "mg/L"
    assert "ug/L" in rules["WATER_SURFACE"]["supported_units"]
    assert rules["SOIL_TOP"]["canonical_basis"] == "dry_weight"
    assert rules["SEDIMENT_FRESH"]["unit_basis_labels"]["mg/kg ww"] == "wet_weight"


def test_regulatory_handoff_profile_manifest_is_loaded() -> None:
    registry = DefaultsRegistry(Path(__file__).resolve().parents[1])
    manifest = registry.regulatory_handoff_profile_manifest()
    profiles = {profile["profile_id"]: profile for profile in manifest["profiles"]}
    assert manifest["profileCount"] >= 2
    assert profiles["exposure_scenario_mcp_v1"]["target_module"] == "Direct-Use Exposure MCP"
    assert profiles["toxclaw_orchestration_v1"]["downstream_field"] == "upstream_concentration_surface"
    assert "direct-use exposure mcp" in profiles["exposure_scenario_mcp_v1"]["consumer_hints"]
    assert profiles["exposure_scenario_mcp_v1"]["review_checklist"]
    assert "fate_export_regulatory_handoff_package" in profiles["exposure_scenario_mcp_v1"]["tool_request_template"]
    assert profiles["toxclaw_orchestration_v1"]["response_summary_template"]
    assert profiles["toxclaw_orchestration_v1"]["review_brief_template"]


def test_regulatory_handoff_profile_recommendation_matches_known_consumer() -> None:
    registry = DefaultsRegistry(Path(__file__).resolve().parents[1])
    recommendation = registry.recommend_regulatory_handoff_profile("suite orchestration")
    assert recommendation is not None
    assert recommendation.resolved_profile_id == "toxclaw_orchestration_v1"
    assert recommendation.target_module == "ToxClaw"
    assert recommendation.confidence >= 0.8


def test_regulatory_handoff_consumer_alias_manifest_is_conflict_free() -> None:
    registry = DefaultsRegistry(Path(__file__).resolve().parents[1])
    manifest = registry.regulatory_handoff_consumer_alias_manifest()
    assert manifest.alias_count >= 4
    assert manifest.conflict_count == 0
    normalized_aliases = {alias.normalized_alias for alias in manifest.aliases}
    assert "toxclaw" in normalized_aliases
    assert "exposure scenario mcp" in normalized_aliases


def test_regulatory_handoff_profile_recommendation_rejects_conflicting_aliases() -> None:
    registry = DefaultsRegistry(Path(__file__).resolve().parents[1])
    registry.regulatory_handoff_profiles["profiles"]["exposure_scenario_mcp_v1"]["consumerHints"].append(
        "ToxClaw"
    )
    manifest = registry.regulatory_handoff_consumer_alias_manifest()
    assert manifest.conflict_count == 1
    assert manifest.conflicts[0].normalized_alias == "toxclaw"
    assert registry.recommend_regulatory_handoff_profile("ToxClaw") is None


def test_regulatory_handoff_target_matrix_manifest_is_loaded() -> None:
    registry = DefaultsRegistry(Path(__file__).resolve().parents[1])
    manifest = registry.regulatory_handoff_target_matrix_manifest()
    assert manifest.mapping_count >= 2
    mappings = {mapping.profile_id: mapping for mapping in manifest.mappings}
    assert mappings["exposure_scenario_mcp_v1"].target_module == "Direct-Use Exposure MCP"
    assert "toxclaw" in [hint.lower() for hint in mappings["toxclaw_orchestration_v1"].consumer_hints]

def test_regulatory_handoff_profiles_for_jurisdictions() -> None:
    from pathlib import Path
    from fate_mcp.defaults import DefaultsRegistry
    registry = DefaultsRegistry(Path(__file__).resolve().parents[1])
    
    # ECHA REACH CSR
    echa_profile = registry.regulatory_handoff_profile("echa_csr_v1")
    assert echa_profile is not None
    assert echa_profile.target_module == "ECHA REACH Submission"
    assert "echa" in echa_profile.consumer_hints
    assert any(check.code == "csr_compartments_complete" for check in echa_profile.review_checklist)
    
    # EPA PMN
    epa_profile = registry.regulatory_handoff_profile("epa_pmn_v1")
    assert epa_profile is not None
    assert epa_profile.target_module == "EPA PMN Submission"
    assert "epa" in epa_profile.consumer_hints
    assert any(check.code == "pmn_release_context_preserved" for check in epa_profile.review_checklist)
