import asyncio

from fate_mcp.server import create_server


def test_server_exposes_governed_regulatory_handoff_prompts() -> None:
    async def _run() -> None:
        server = create_server()
        prompts = await server.list_prompts()
        names = {prompt.name for prompt in prompts}
        assert "fate_request_model_family_selection_for_profile" in names
        assert "fate_review_model_family_selection_for_profile" in names
        assert "fate_review_model_family_challenge_for_profile" in names
        assert "fate_review_model_family_challenge_scientifically" in names
        assert "fate_request_model_family_comparison_for_profile" in names
        assert "fate_summarize_model_family_comparison_for_profile" in names
        assert "fate_review_model_family_comparison_for_profile" in names
        assert "fate_request_scientific_review_for_model_family" in names
        assert "fate_summarize_scientific_review_for_model_family" in names
        assert "fate_review_scientific_methods_for_model_family" in names
        assert "fate_request_regulatory_handoff_for_profile" in names
        assert "fate_request_regulatory_handoff_for_consumer" in names
        assert "fate_summarize_regulatory_handoff_for_profile" in names
        assert "fate_review_regulatory_handoff_for_profile" in names

        selection_request_prompt = await server.get_prompt(
            "fate_request_model_family_selection_for_profile",
            {
                "profile_id": "reference_baseline_advective_challenge_v1",
                "selection_goal": "screening family selection",
            },
        )
        selection_request_text = selection_request_prompt.messages[0].content.text
        assert "reference_baseline_advective_challenge_v1" in selection_request_text
        assert "fate_recommend_model_family_selection" in selection_request_text
        assert "\"selection_profile_id\": \"reference_baseline_advective_challenge_v1\"" in selection_request_text

        selection_review_prompt = await server.get_prompt(
            "fate_review_model_family_selection_for_profile",
            {"profile_id": "reference_baseline_advective_challenge_v1"},
        )
        selection_review_text = selection_review_prompt.messages[0].content.text
        assert "selection_scope_confirmed" in selection_review_text
        assert "fate_preview_model_family_selection_review" in selection_review_text
        assert "fate_build_model_family_selection_review_packet" in selection_review_text
        assert "fate_build_model_family_selection_review_brief" in selection_review_text

        challenge_review_prompt = await server.get_prompt(
            "fate_review_model_family_challenge_for_profile",
            {"profile_id": "reference_baseline_advective_challenge_review_v1"},
        )
        challenge_review_text = challenge_review_prompt.messages[0].content.text
        assert "reference_baseline_advective_challenge_review_v1" in challenge_review_text
        assert "reference_baseline_advective_challenge_v1" in challenge_review_text
        assert "reference_vs_advective_screening_v1" in challenge_review_text
        assert "selection_review_status_confirmed" in challenge_review_text
        assert "fate_preview_model_family_challenge_review" in challenge_review_text
        assert "fate_build_model_family_challenge_review_packet" in challenge_review_text
        assert "fate_build_model_family_challenge_review_brief" in challenge_review_text

        challenge_scientific_prompt = await server.get_prompt(
            "fate_review_model_family_challenge_scientifically",
            {"profile_id": "reference_baseline_advective_challenge_review_v1"},
        )
        challenge_scientific_text = challenge_scientific_prompt.messages[0].content.text
        assert "reference_baseline_advective_challenge_review_v1" in challenge_scientific_text
        assert "reference_baseline_advective_challenge_v1" in challenge_scientific_text
        assert "reference_vs_advective_screening_v1" in challenge_scientific_text
        assert "fate_build_model_family_challenge_scientific_dossier" in challenge_scientific_text
        assert "fate_build_model_family_challenge_scientific_dossier_brief" in challenge_scientific_text

        comparison_request_prompt = await server.get_prompt(
            "fate_request_model_family_comparison_for_profile",
            {
                "profile_id": "reference_vs_advective_screening_v1",
                "comparison_goal": "advective challenge review",
            },
        )
        comparison_request_text = comparison_request_prompt.messages[0].content.text
        assert "reference_vs_advective_screening_v1" in comparison_request_text
        assert "fate_build_model_family_comparison_packet" in comparison_request_text
        assert "\"comparison_profile_id\": \"reference_vs_advective_screening_v1\"" in comparison_request_text

        comparison_summary_prompt = await server.get_prompt(
            "fate_summarize_model_family_comparison_for_profile",
            {"profile_id": "reference_vs_advective_screening_v1"},
        )
        comparison_summary_text = comparison_summary_prompt.messages[0].content.text
        assert "advective_screening_mass_balance" in comparison_summary_text
        assert "fate_build_model_family_comparison_brief" in comparison_summary_text

        comparison_review_prompt = await server.get_prompt(
            "fate_review_model_family_comparison_for_profile",
            {"profile_id": "reference_vs_advective_screening_v1"},
        )
        comparison_review_text = comparison_review_prompt.messages[0].content.text
        assert "comparison_scope_confirmed" in comparison_review_text
        assert "fate_preview_model_family_comparison_review" in comparison_review_text
        assert "fate_build_model_family_comparison_review_packet" in comparison_review_text
        assert "fate_build_model_family_comparison_review_brief" in comparison_review_text

        scientific_request_prompt = await server.get_prompt(
            "fate_request_scientific_review_for_model_family",
            {
                "model_family": "reference_mass_balance",
                "review_goal": "assessor screening review",
            },
        )
        scientific_request_text = scientific_request_prompt.messages[0].content.text
        assert "reference_mass_balance" in scientific_request_text
        assert "fate_build_scientific_review_packet" in scientific_request_text

        scientific_summary_prompt = await server.get_prompt(
            "fate_summarize_scientific_review_for_model_family",
            {"model_family": "external_result_adapter"},
        )
        scientific_summary_text = scientific_summary_prompt.messages[0].content.text
        assert "external_result_adapter" in scientific_summary_text
        assert "fate_build_scientific_review_brief" in scientific_summary_text

        scientific_methods_prompt = await server.get_prompt(
            "fate_review_scientific_methods_for_model_family",
            {"model_family": "advective_screening_mass_balance"},
        )
        scientific_methods_text = scientific_methods_prompt.messages[0].content.text
        assert "advective_screening_mass_balance" in scientific_methods_text
        assert "fate_build_scientific_methods_dossier" in scientific_methods_text
        assert "fate_build_scientific_methods_dossier_brief" in scientific_methods_text

        request_prompt = await server.get_prompt(
            "fate_request_regulatory_handoff_for_profile",
            {
                "profile_id": "toxclaw_orchestration_v1",
                "downstream_goal": "suite orchestration",
            },
        )
        request_text = request_prompt.messages[0].content.text
        assert "toxclaw_orchestration_v1" in request_text
        assert "fate_export_regulatory_handoff_package" in request_text
        assert "\"target_modules\": [" in request_text

        consumer_prompt = await server.get_prompt(
            "fate_request_regulatory_handoff_for_consumer",
            {
                "consumer_name": "workflow orchestrator",
                "downstream_goal": "suite orchestration",
            },
        )
        consumer_text = consumer_prompt.messages[0].content.text
        assert "Recommended profile: toxclaw_orchestration_v1" in consumer_text
        assert "\"consumer_name\": \"workflow orchestrator\"" in consumer_text

        summary_prompt = await server.get_prompt(
            "fate_summarize_regulatory_handoff_for_profile",
            {"profile_id": "exposure_scenario_mcp_v1"},
        )
        summary_text = summary_prompt.messages[0].content.text
        assert "route_hint" in summary_text
        assert "Direct-Use Exposure MCP" in summary_text

        review_prompt = await server.get_prompt(
            "fate_review_regulatory_handoff_for_profile",
            {"profile_id": "toxclaw_orchestration_v1"},
        )
        review_text = review_prompt.messages[0].content.text
        assert "field_mapping_stable" in review_text
        assert "fate_build_regulatory_handoff_review_packet" in review_text
        assert "fate_build_regulatory_handoff_review_brief" in review_text

    asyncio.run(_run())
