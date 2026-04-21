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
