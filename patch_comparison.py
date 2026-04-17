import re

with open("src/fate_mcp/integrations.py", "r") as f:
    content = f.read()

# In `compare_fate_scenarios`:
# Find where limitations and quality_flags are created.
# Wait, let's just replace the end of compare_fate_scenarios.

end_of_func = """    return FateScenarioComparisonRecord(
        base_scenario_id=request.base_scenario.scenario_id,
        candidate_scenario_id=request.candidate_scenario.scenario_id,
        surface_deltas=deltas,
        changed_assumptions=list(changed_assumptions),
        dominant_drivers=list(dominant_drivers),
        provenance=provenance_builder.bundle(
            [
                *request.base_scenario.evidence_sources,
                *request.candidate_scenario.evidence_sources,
            ]
        ),
        limitations=list(limitations),
        quality_flags=list(quality_flags),
    )"""

new_end_of_func = """    # Lift adapter limitations and cross-family flags
    if request.base_result.run_summary.model_family != request.candidate_result.run_summary.model_family:
        quality_flags.add(
            QualityFlag(
                code="cross_family_comparison",
                severity=Severity.INFO,
                message=f"Comparison spans different model families: {request.base_result.run_summary.model_family.value} vs {request.candidate_result.run_summary.model_family.value}.",
            )
        )
        for result in (request.base_result, request.candidate_result):
            if result.run_summary.model_family.value == "external_result_adapter":
                for surface in result.surfaces:
                    for limit in surface.limitations:
                        limitations.add(limit)
                for warning in result.run_summary.warnings:
                    quality_flags.add(warning)

    # Sort to ensure deterministic output
    sorted_limitations = sorted(list(limitations), key=lambda x: x.code)
    sorted_quality_flags = sorted(list(quality_flags), key=lambda x: x.code)

    return FateScenarioComparisonRecord(
        base_scenario_id=request.base_scenario.scenario_id,
        candidate_scenario_id=request.candidate_scenario.scenario_id,
        surface_deltas=deltas,
        changed_assumptions=sorted(list(changed_assumptions)),
        dominant_drivers=sorted(list(dominant_drivers)),
        provenance=provenance_builder.bundle(
            [
                *request.base_scenario.evidence_sources,
                *request.candidate_scenario.evidence_sources,
            ]
        ),
        limitations=sorted_limitations,
        quality_flags=sorted_quality_flags,
    )"""

content = content.replace(end_of_func, new_end_of_func)

with open("src/fate_mcp/integrations.py", "w") as f:
    f.write(content)
print("done")
