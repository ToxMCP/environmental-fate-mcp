import asyncio
import json
from pathlib import Path

import pytest

from fate_mcp.server import (
    create_server,
    defaults_erosion_sediment_method_profiles,
    defaults_erosion_sediment_validation_demo_pack,
    defaults_erosion_sediment_validation_profiles,
    docs_manifest_resource,
    docs_resource,
    example_resource,
    release_resource_manifest,
    schema_resource,
)


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
        assert "fate_summarize_run_trust_for_model_family" in names
        assert "fate_review_scientific_methods_for_model_family" in names
        assert "fate_review_release_trust_for_screening" in names
        assert "fate_review_reference_family_proof_for_screening" in names
        assert "fate_review_advective_promotion_bar" in names
        assert "fate_request_external_result_import" in names
        assert "fate_request_erosion_sediment_transport_screening" in names
        assert "fate_request_erosion_sediment_validation_case" in names
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

        run_trust_prompt = await server.get_prompt(
            "fate_summarize_run_trust_for_model_family",
            {
                "model_family": "reference_mass_balance",
                "review_goal": "compact run-level trust check",
            },
        )
        run_trust_text = run_trust_prompt.messages[0].content.text
        assert "compact run-level trust check" in run_trust_text
        assert "reference_mass_balance" in run_trust_text
        assert "fate_build_run_scientific_trust_brief" in run_trust_text
        assert "\"scenario\": \"<EnvironmentalReleaseScenario>\"" in run_trust_text
        assert "\"result\": \"<ConcentrationEstimationResult>\"" in run_trust_text
        assert "fate_build_scientific_review_packet" in run_trust_text
        assert "fate_build_scientific_review_brief" in run_trust_text

        scientific_methods_prompt = await server.get_prompt(
            "fate_review_scientific_methods_for_model_family",
            {"model_family": "advective_screening_mass_balance"},
        )
        scientific_methods_text = scientific_methods_prompt.messages[0].content.text
        assert "advective_screening_mass_balance" in scientific_methods_text
        assert "fate_build_scientific_methods_dossier" in scientific_methods_text
        assert "fate_build_scientific_methods_dossier_brief" in scientific_methods_text

        release_trust_prompt = await server.get_prompt(
            "fate_review_release_trust_for_screening",
            {"review_goal": "external reviewer trust check"},
        )
        release_trust_text = release_trust_prompt.messages[0].content.text
        assert "external reviewer trust check" in release_trust_text
        assert "docs://scientific-trust-brief" in release_trust_text
        assert "docs://scientific-trust-pack" in release_trust_text
        assert "release://defaults-rebaseline-report" in release_trust_text
        assert "release://reference-corroboration-report" in release_trust_text
        assert "release://reference-worksheet-manifest" in release_trust_text
        assert "release://advective-promotion-bar-report" in release_trust_text
        assert "release://external-corroboration-report" in release_trust_text
        assert "release://erosion-sediment-validation-demo-report" in release_trust_text
        assert "release://red-team-review-report" in release_trust_text
        assert "release://readiness-report" in release_trust_text
        assert "release://resource-manifest" in release_trust_text
        assert "docs://manifest" in release_trust_text
        assert "bounded screening" in release_trust_text

        reference_proof_prompt = await server.get_prompt(
            "fate_review_reference_family_proof_for_screening",
            {"review_goal": "reference proof deep dive"},
        )
        reference_proof_text = reference_proof_prompt.messages[0].content.text
        assert "reference proof deep dive" in reference_proof_text
        assert "reference_mass_balance" in reference_proof_text
        assert "docs://reference-proof-brief" in reference_proof_text
        assert "release://reference-corroboration-report" in reference_proof_text
        assert "release://reference-worksheet-manifest" in reference_proof_text
        assert "release://defaults-rebaseline-report" in reference_proof_text
        assert "fate_build_scientific_methods_dossier" in reference_proof_text
        assert "bounded screening" in reference_proof_text

        advective_bar_prompt = await server.get_prompt(
            "fate_review_advective_promotion_bar",
            {"review_goal": "advective challenge governance review"},
        )
        advective_bar_text = advective_bar_prompt.messages[0].content.text
        assert "advective challenge governance review" in advective_bar_text
        assert "advective_screening_mass_balance" in advective_bar_text
        assert "docs://advective-promotion-brief" in advective_bar_text
        assert "release://advective-promotion-bar-report" in advective_bar_text
        assert "release://reference-corroboration-report" in advective_bar_text
        assert "fate_build_scientific_methods_dossier" in advective_bar_text
        assert "experimental" in advective_bar_text

        external_import_prompt = await server.get_prompt(
            "fate_request_external_result_import",
            {
                "import_profile_id": "normalized_external_payload_json",
                "import_goal": "external fixture normalization",
            },
        )
        external_import_text = external_import_prompt.messages[0].content.text
        assert "normalized_external_payload_json" in external_import_text
        assert "fate_import_external_result_payload" in external_import_text

        erosion_prompt = await server.get_prompt(
            "fate_request_erosion_sediment_transport_screening",
            {"screening_goal": "runoff event sediment handoff"},
        )
        erosion_text = erosion_prompt.messages[0].content.text
        assert "runoff event sediment handoff" in erosion_text
        assert "defaults://erosion-sediment-method-profiles" in erosion_text
        assert "fate_screen_erosion_transport_relevance" in erosion_text
        assert "fate_estimate_soil_loss_rusle" in erosion_text
        assert "fate_estimate_event_sediment_yield_musle" in erosion_text
        assert "fate_estimate_sediment_associated_chemical_load" in erosion_text

        erosion_validation_prompt = await server.get_prompt(
            "fate_request_erosion_sediment_validation_case",
            {"validation_goal": "storm-event validation QA"},
        )
        erosion_validation_text = erosion_validation_prompt.messages[0].content.text
        assert "defaults://erosion-sediment-validation-profiles" in erosion_validation_text
        assert "fate_build_erosion_sediment_validation_case" in erosion_validation_text
        assert "fate_assess_erosion_sediment_validation_fit" in erosion_validation_text

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


def test_server_tools_expose_annotations_and_output_schemas() -> None:
    async def _run() -> None:
        server = create_server()
        tools = await server.list_tools()
        assert len(tools) == 57
        for tool in tools:
            assert tool.annotations is not None, tool.name
            assert tool.annotations.readOnlyHint is True, tool.name
            assert tool.annotations.destructiveHint is False, tool.name
            assert tool.outputSchema is not None, tool.name

        by_name = {tool.name: tool for tool in tools}
        assert by_name["fate_import_external_result_payload"].annotations.openWorldHint is True
        for tool_name in {
            "fate_screen_erosion_transport_relevance",
            "fate_estimate_soil_loss_rusle",
            "fate_estimate_event_sediment_yield_musle",
            "fate_estimate_sediment_associated_chemical_load",
            "fate_build_erosion_sediment_validation_case",
            "fate_assess_erosion_sediment_validation_fit",
            "fate_build_default_sensitivity_report",
        }:
            assert by_name[tool_name].annotations.openWorldHint is False
            assert by_name[tool_name].annotations.idempotentHint is True
        assert (
            by_name["fate_estimate_probabilistic_multimedia_concentrations"]
            .annotations
            .idempotentHint
            is False
        )
        assert by_name["fate_estimate_multimedia_concentrations"].annotations.idempotentHint is True

    asyncio.run(_run())


def test_release_resource_can_be_read_inside_async_server_context() -> None:
    async def _run() -> None:
        server = create_server()
        contents = await server.read_resource("release://metadata-report")
        metadata = json.loads(contents[0].content)
        assert metadata["toolCount"] == 57
        assert metadata["promptCount"] == 21
        assert metadata["resourceCount"] == 29
        demo_contents = await server.read_resource(
            "release://erosion-sediment-validation-demo-report"
        )
        demo_report = json.loads(demo_contents[0].content)
        assert demo_report["passed"] is True
        assert demo_report["demoCaseCount"] == 4
        benchmark_contents = await server.read_resource(
            "release://external-validation-benchmark-report"
        )
        benchmark_report = json.loads(benchmark_contents[0].content)
        assert benchmark_report["passed"] is True
        assert benchmark_report["caseCount"] == 4
        sensitivity_contents = await server.read_resource("release://default-sensitivity-report")
        sensitivity_report = json.loads(sensitivity_contents[0].content)
        assert sensitivity_report["passed"] is True
        assert sensitivity_report["profileCount"] == 7
        notes_contents = await server.read_resource("release://release-notes")
        notes = json.loads(notes_contents[0].content)
        assert "Environmental Fate MCP v0.3.0" in notes["markdown"]
        assert "public MCP import contract in this release" in notes["markdown"]
        manifest_contents = await server.read_resource("release://resource-manifest")
        manifest = json.loads(manifest_contents[0].content)
        assert "release-notes" in {item["name"] for item in manifest["resources"]}

    asyncio.run(_run())



def test_schema_resource_rejects_path_traversal() -> None:
    with pytest.raises(ValueError, match="Invalid resource name"):
        schema_resource("../../../etc/passwd")


def test_example_resource_rejects_path_traversal() -> None:
    with pytest.raises(ValueError, match="Invalid resource name"):
        example_resource("../secrets")


def test_docs_resource_rejects_unknown_name() -> None:
    with pytest.raises(ValueError, match="Unknown doc name"):
        docs_resource("../../../etc/passwd")


def test_new_docs_resources_are_available() -> None:
    cookbook = docs_resource("workflow-cookbook")
    assert "Basic Deterministic Screening" in cookbook
    external_contract = docs_resource("external-payload-contract")
    assert "normalized external payload import" in external_contract
    agent_evals = docs_resource("agent-evaluations")
    assert "read-only evaluation pack" in agent_evals
    public_release = docs_resource("public-release-guide")
    assert "Public Release Guide" in public_release
    defaults_evidence = docs_resource("defaults-evidence-map")
    assert "Defaults Evidence Map" in defaults_evidence
    quick_start = docs_resource("regulatory-quick-start")
    assert "When Not To Use This MCP" in quick_start
    trust_brief = docs_resource("scientific-trust-brief")
    assert "Scientific Trust Brief" in trust_brief
    trust_pack = docs_resource("scientific-trust-pack")
    assert "Scientific Trust Pack" in trust_pack
    reference_proof = docs_resource("reference-proof-brief")
    assert "Reference Proof Brief" in reference_proof
    advective_promotion = docs_resource("advective-promotion-brief")
    assert "Advective Promotion Brief" in advective_promotion
    erosion_transport = docs_resource("erosion-sediment-transport")
    assert "Erosion/Sediment Transport Screening" in erosion_transport


def test_docs_and_release_resource_manifests_expose_trust_surfaces() -> None:
    docs_manifest = json.loads(docs_manifest_resource())
    doc_names = {item["name"] for item in docs_manifest["docs"]}
    assert "erosion-sediment-transport" in doc_names
    assert "defaults-evidence-map" in doc_names
    assert "regulatory-quick-start" in doc_names
    assert "scientific-trust-brief" in doc_names
    assert "scientific-trust-pack" in doc_names
    assert "reference-proof-brief" in doc_names
    assert "advective-promotion-brief" in doc_names
    assert "public-release-guide" in doc_names

    release_manifest = json.loads(release_resource_manifest())
    release_names = {item["name"] for item in release_manifest["resources"]}
    assert "defaults-rebaseline-report" in release_names
    assert "external-corroboration-report" in release_names
    assert "reference-corroboration-report" in release_names
    assert "reference-worksheet-manifest" in release_names
    assert "advective-promotion-bar-report" in release_names
    assert "erosion-sediment-validation-demo-report" in release_names
    assert "red-team-review-report" in release_names
    assert "scientific-trust-brief" in release_names
    assert "scientific-trust-pack" in release_names
    assert "reference-proof-brief" in release_names
    assert "advective-promotion-brief" in release_names
    assert "docs://scientific-trust-brief" in release_names
    assert "docs://scientific-trust-pack" in release_names
    assert "docs://reference-proof-brief" in release_names
    assert "docs://advective-promotion-brief" in release_names


def test_erosion_sediment_method_profiles_resource() -> None:
    manifest = json.loads(defaults_erosion_sediment_method_profiles())
    profile_ids = {profile["method_id"] for profile in manifest["profiles"]}
    assert manifest["profile_count"] == 5
    assert {
        "erosion_transport_relevance",
        "rusle",
        "musle",
        "sediment_associated_chemical_load",
        "wepp_deferred_adapter",
    } <= profile_ids


def test_erosion_sediment_validation_profiles_resource() -> None:
    manifest = json.loads(defaults_erosion_sediment_validation_profiles())
    assert manifest["profile_count"] == 1
    profile = manifest["profiles"][0]
    assert profile["profile_id"] == "erosion_sediment_screening_validation_v1"
    assert "event_sediment_yield_t" in profile["supported_quantities"]


def test_erosion_sediment_validation_demo_pack_resource() -> None:
    manifest = json.loads(defaults_erosion_sediment_validation_demo_pack())
    assert manifest["demo_case_count"] == 4
    assert {case["demo_case_id"] for case in manifest["demo_cases"]} == {
        "perfect_fit",
        "screening_plausible",
        "weak_fit",
        "insufficient_evidence",
    }
    assert "synthetic" in " ".join(manifest["limitations"]).lower()
    assert "not field validation" in " ".join(manifest["limitations"]).lower()


def test_create_server_does_not_mutate_generated_examples() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    example_path = repo_root / "schemas" / "examples" / "environmentalReleaseScenario.v1.json"
    before = example_path.read_text()
    create_server()
    after = example_path.read_text()
    assert after == before


def test_skeleton_tools_return_valid_json() -> None:
    from fate_mcp.server import (
        fate_build_environmental_release_scenario_skeleton,
        fate_estimate_multimedia_concentrations_skeleton,
        fate_import_external_result_payload_skeleton,
    )
    import json

    scenario_json = fate_build_environmental_release_scenario_skeleton()
    scenario_data = json.loads(scenario_json)
    assert scenario_data["chemical_identity"]["preferredName"] == "Example substance"
    assert scenario_data["total_release_mass_kg"] == 10.0

    estimate_json = fate_estimate_multimedia_concentrations_skeleton()
    estimate_data = json.loads(estimate_json)
    assert "scenario" in estimate_data
    assert "run_options" in estimate_data
    assert estimate_data["run_options"]["model_family"] == "reference_mass_balance"

    import_json = fate_import_external_result_payload_skeleton()
    import_data = json.loads(import_json)
    assert import_data["import_profile_id"] == "normalized_external_payload_json"
    assert import_data["run_options"]["model_family"] == "external_result_adapter"
    assert import_data["payload_path"].endswith("illustrative_external_engine_payload.json")


def test_probabilistic_skeleton_returns_valid_json() -> None:
    from fate_mcp.server import fate_estimate_probabilistic_multimedia_concentrations_skeleton
    import json

    json_text = fate_estimate_probabilistic_multimedia_concentrations_skeleton()
    data = json.loads(json_text)
    assert data["iterations"] == 100
    assert data["seed"] == 42
    assert data["run_options"]["model_family"] == "reference_mass_balance"


def test_handoff_package_skeleton_returns_valid_json() -> None:
    from fate_mcp.server import fate_export_regulatory_handoff_package_skeleton
    import json

    json_text = fate_export_regulatory_handoff_package_skeleton()
    data = json.loads(json_text)
    assert data["handoff_profile_id"] == "exposure_scenario_mcp_v1"
    assert data["target_modules"] == ["exposure_scenario_mcp_v1"]
    assert "result" in data
    assert "scenario" in data


def test_audit_log_file_is_written_when_env_var_set(tmp_path, monkeypatch) -> None:
    import json

    log_file = tmp_path / "audit.jsonl"
    monkeypatch.setenv("FATE_MCP_AUDIT_LOG_PATH", str(log_file))

    # Re-import to pick up the env var and fresh logger state
    import importlib
    import fate_mcp.server as server_module

    # Clear handlers so _configure_logging runs again
    server_module.logger.handlers.clear()
    importlib.reload(server_module)

    # Call a tool that should be logged
    result_json = server_module.fate_build_environmental_release_scenario_skeleton()
    assert "Example substance" in result_json

    # Force flush by closing handlers
    for handler in server_module.logger.handlers:
        handler.close()
    server_module.logger.handlers.clear()

    assert log_file.exists()
    lines = log_file.read_text().strip().split("\n")
    assert len(lines) >= 1
    record = json.loads(lines[0])
    assert record["tool_name"] == "fate_build_environmental_release_scenario_skeleton"
    assert "correlation_id" in record
    assert "duration_ms" in record


def test_comparison_packet_skeleton_returns_valid_json() -> None:
    from fate_mcp.server import fate_build_model_family_comparison_packet_skeleton
    import json

    json_text = fate_build_model_family_comparison_packet_skeleton()
    data = json.loads(json_text)
    assert "scenario" in data
    assert data["base_model_family"] == "reference_mass_balance"
    assert data["candidate_model_family"] == "advective_screening_mass_balance"


def test_scientific_review_packet_skeleton_returns_valid_json() -> None:
    from fate_mcp.server import fate_build_scientific_review_packet_skeleton
    import json

    json_text = fate_build_scientific_review_packet_skeleton()
    data = json.loads(json_text)
    assert "scenario" in data
    assert "result" in data
    assert data["result"]["run_summary"]["model_family"] == "reference_mass_balance"


def test_challenge_dossier_skeleton_returns_valid_json() -> None:
    from fate_mcp.server import fate_build_model_family_challenge_scientific_dossier_skeleton
    import json

    json_text = fate_build_model_family_challenge_scientific_dossier_skeleton()
    data = json.loads(json_text)
    assert "scenario" in data
    assert data["bucket_count"] == 4
    assert data["bucket_duration_days"] == 7.0
