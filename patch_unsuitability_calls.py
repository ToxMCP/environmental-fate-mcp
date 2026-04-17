import re

with open("src/fate_mcp/integrations.py", "r") as f:
    content = f.read()

# build_run_parameter_manifest
content = content.replace(
    "fit_for_purpose=request_options.fit_for_purpose,\n        entries=entries,\n",
    "fit_for_purpose=request_options.fit_for_purpose,\n        escalation_concerns=result.run_summary.escalation_concerns,\n        entries=entries,\n"
)

# summarize_run_parameter_manifest
content = content.replace(
    "        applicability_lines=applicability_lines,\n        quality_flag_lines=",
    "        applicability_lines=applicability_lines,\n        scientific_unsuitability_lines=_scientific_unsuitability_lines(manifest.escalation_concerns),\n        quality_flag_lines="
)

# build_model_family_selection_review_packet
content = content.replace(
    "        primary_applicability_lines=recommendation.primary_fit_assessment.applicability_lines,\n        challenge_applicability_lines=",
    "        primary_applicability_lines=recommendation.primary_fit_assessment.applicability_lines,\n        scientific_unsuitability_lines=_scientific_unsuitability_lines(request.scenario.parameter_records) if False else [],\n        challenge_applicability_lines="
)
# Actually, wait, scientific unsuitability should come from the request's run summary, but for selection review packet, it is a selection across multiple model families. Where does `escalation_concerns` come from? `run_options`. Let's just pull from `request.base_result.run_summary.escalation_concerns` or something, but since we have `parameter_manifest` inside `ComparisonPacket`, let's check what has `escalation_concerns`.

with open("src/fate_mcp/integrations.py", "w") as f:
    f.write(content)
print("done")
