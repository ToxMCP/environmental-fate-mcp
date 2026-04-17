PACKAGE_NAME = "Environmental Fate MCP"
VERSION = "0.1.0"
SCHEMA_VERSION = "v1"
DEFAULTS_VERSION = "v1"
ALGORITHM_VERSION = "reference-mass-balance-0.1.0"
SUPPORTED_WORKFLOWS = [
    "fate_build_environmental_release_scenario",
    "fate_estimate_multimedia_concentrations",
    "fate_estimate_probabilistic_multimedia_concentrations",
    "fate_build_concentration_surface_bundle",
    "fate_compare_fate_scenarios",
    "fate_apply_physchem_evidence",
    "fate_assess_release_scenario_fit",
    "fate_build_run_parameter_manifest",
    "fate_build_run_uncertainty_summary",
    "fate_build_probabilistic_review_packet",
    "fate_build_probabilistic_review_brief",
    "fate_recommend_model_family_selection",
    "fate_preview_model_family_selection_review",
    "fate_build_model_family_selection_review_packet",
    "fate_build_model_family_selection_review_brief",
    "fate_preview_model_family_challenge_review",
    "fate_build_model_family_challenge_review_packet",
    "fate_build_model_family_challenge_review_brief",
    "fate_build_model_family_challenge_scientific_dossier",
    "fate_build_model_family_challenge_scientific_dossier_brief",
    "fate_build_model_family_comparison_packet",
    "fate_build_model_family_comparison_brief",
    "fate_preview_model_family_comparison_review",
    "fate_build_model_family_comparison_review_packet",
    "fate_build_model_family_comparison_review_brief",
    "fate_preview_scientific_review_outcome",
    "fate_build_scientific_review_packet",
    "fate_build_scientific_review_brief",
    "fate_build_scientific_methods_dossier",
    "fate_build_scientific_methods_dossier_brief",
    "fate_reconcile_release_evidence",
    "fate_export_concentration_surface_bundle",
    "fate_export_exposure_consumption_package",
    "fate_recommend_regulatory_handoff_profile",
    "fate_preview_regulatory_handoff_resolution",
    "fate_export_regulatory_handoff_package",
    "fate_summarize_regulatory_handoff_package",
    "fate_build_regulatory_handoff_review_packet",
    "fate_build_regulatory_handoff_review_brief",
]
SUPPORTED_MODEL_FAMILIES = [
    "reference_mass_balance",
    "adapter_stub",
    "external_result_adapter",
]
EXPERIMENTAL_MODEL_FAMILIES = [
    "advective_screening_mass_balance",
]
