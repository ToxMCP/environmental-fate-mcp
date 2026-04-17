import re

with open("src/fate_mcp/integrations.py", "r") as f:
    content = f.read()

# Add _scientific_unsuitability_lines helper
helper = """def _scientific_unsuitability_lines(escalation_concerns: list[str]) -> list[str]:
    lines = []
    for concern in escalation_concerns:
        val = getattr(concern, 'value', concern)
        if val == "extreme_persistence":
            lines.append("Scientific unsuitability trigger: extreme persistence requires higher-tier modeling or prolonged clearance anchors.")
        elif val == "strong_spatial_heterogeneity":
            lines.append("Scientific unsuitability trigger: strong spatial heterogeneity requires GIS/routed spatial dispersion.")
        elif val == "point_source_plume_dependence":
            lines.append("Scientific unsuitability trigger: point-source plume dependence requires explicit near-field dispersion models.")
        elif val == "pfas_like_transport":
            lines.append("Scientific unsuitability trigger: PFAS-like transport concerns require specialized multimedia distribution logic.")
        elif val == "jurisdictional_probabilistic_requirement":
            lines.append("Scientific unsuitability trigger: jurisdictional requirement for probabilistic output cannot be satisfied by deterministic screening.")
        else:
            lines.append(f"Scientific unsuitability trigger: flagged for {val}.")
    return sorted(lines)

"""

if "def _scientific_unsuitability_lines" not in content:
    content = content.replace("def _applicability_lines(", helper + "def _applicability_lines(")

with open("src/fate_mcp/integrations.py", "w") as f:
    f.write(content)
print("done")
