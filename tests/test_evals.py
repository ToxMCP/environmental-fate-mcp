from pathlib import Path
from xml.etree import ElementTree


def test_agent_eval_pack_is_well_formed_and_has_ten_pairs() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    eval_path = repo_root / "evals" / "environmental-fate-mcp-read-only.xml"
    tree = ElementTree.parse(eval_path)
    root = tree.getroot()
    qa_pairs = root.findall("qa_pair")
    assert root.tag == "evaluation"
    assert len(qa_pairs) == 10
    assert all(pair.findtext("question") for pair in qa_pairs)
    assert all(pair.findtext("answer") for pair in qa_pairs)


def test_scientific_decisions_eval_pack_is_well_formed_and_covers_decision_lanes() -> None:
    """The scientific-decisions eval pack must ship 15 scenario-based agent
    decision questions covering: model-family selection (fugacity / advective),
    fail-closed error codes (half-life, temperature, treatment removal),
    governed policy values (Q10, temperature ceiling), reviewer-grade vs
    experimental posture, hand-off contracts, tamper-evidence fingerprints,
    boundary discipline (PBPK routing), and audit / governance infrastructure.

    This is the parallel agent-decision counterpart to the read-only QA
    pack, anchored against R10 in docs/scientific_hardening_tracker.md.
    """
    repo_root = Path(__file__).resolve().parents[1]
    eval_path = repo_root / "evals" / "environmental-fate-mcp-scientific-decisions.xml"
    tree = ElementTree.parse(eval_path)
    root = tree.getroot()
    qa_pairs = root.findall("qa_pair")
    assert root.tag == "evaluation"
    assert len(qa_pairs) == 15
    assert all(pair.findtext("question") for pair in qa_pairs)
    assert all(pair.findtext("answer") for pair in qa_pairs)

    # The eval pack's answers must be drawn from real surfaces of the MCP.
    # If a runtime refactor renames any of these strings, the eval pack and
    # its consumers must be updated together.
    answers = {pair.findtext("answer") for pair in qa_pairs}
    required = {
        # Model-family selection
        "fugacity_equilibrium_screening",
        "advective_screening_mass_balance",
        "reference_mass_balance",
        # Fail-closed error codes
        "non_positive_half_life",
        "temperature_correction_clamped_to_governed_range",
        "treatment_removal_fraction_exceeds_unity",
        # Governed policy values
        "40.0",
        "2.0",
        # Hand-off + audit infrastructure
        "fate_export_regulatory_handoff_package",
        "integrity_hash",
        "fate_screen_erosion_transport_relevance",
        "non_promotable_experimental",
        "PBPK MCP",
        "FATE_MCP_AUDIT_LOG_PATH",
        "advective-worksheet-pack",
    }
    missing = required - answers
    assert not missing, f"Scientific decisions eval pack is missing required answers: {sorted(missing)}"
