from __future__ import annotations

from fate_mcp.models import SourceClassification


EVIDENCE_WEIGHTS = {
    "measured": 1.0,
    "regulatory": 1.0,
    "reference": 0.85,
    "estimated": 0.6,
    "surrogate": 0.35,
    "heuristic": 0.2,
}


def evidence_weight(evidence_quality: str) -> float:
    return EVIDENCE_WEIGHTS.get(evidence_quality.strip().lower(), 0.5)


def is_low_confidence_evidence(evidence_quality: str) -> bool:
    return evidence_weight(evidence_quality) < 0.5


def source_classification_for_evidence(evidence_quality: str) -> SourceClassification:
    if is_low_confidence_evidence(evidence_quality):
        return SourceClassification.HEURISTIC
    return SourceClassification.USER_INPUT
