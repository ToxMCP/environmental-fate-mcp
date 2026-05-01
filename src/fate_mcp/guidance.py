from __future__ import annotations

import re
from pathlib import Path


DOC_RESOURCE_MAP = {
    "operator-guide": "docs/operator_guide.md",
    "provenance-policy": "docs/provenance_policy.md",
    "validation-framework": "docs/validation_framework.md",
    "fate-model-boundary-guide": "docs/fate_model_boundary_guide.md",
    "suite-integration-guide": "docs/suite_integration.md",
    "release-readiness": "docs/release_readiness.md",
    "defaults-evidence-map": "docs/defaults_evidence_map.md",
    "adapter-spi": "docs/adapter_spi.md",
    "model-applicability-limits": "docs/model_applicability_limits.md",
    "regulatory-quick-start": "docs/regulatory_quick_start.md",
    "public-release-guide": "docs/public_release_guide.md",
    "workflow-cookbook": "docs/workflow_cookbook.md",
    "external-payload-contract": "docs/external_payload_contract.md",
    "erosion-sediment-transport": "docs/erosion_sediment_transport.md",
    "agent-evaluations": "docs/agent_evaluations.md",
    "scientific-trust-pack": "docs/releases/v0.2.1/scientific-trust-pack.md",
    "scientific-trust-brief": "docs/releases/v0.2.1/scientific-trust-brief.md",
    "reference-proof-brief": "docs/releases/v0.2.1/reference-proof-brief.md",
    "advective-promotion-brief": "docs/releases/v0.2.1/advective-promotion-brief.md",
}


def read_doc(repo_root: Path, name: str) -> str:
    if name not in DOC_RESOURCE_MAP:
        raise ValueError(f"Unknown doc name: {name}")
    relative_path = DOC_RESOURCE_MAP[name]
    return (repo_root / relative_path).read_text()


def build_doc_manifest(repo_root: Path) -> dict[str, object]:
    docs = []
    for name, relative_path in sorted(DOC_RESOURCE_MAP.items()):
        text = (repo_root / relative_path).read_text()
        title_match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
        docs.append(
            {
                "name": name,
                "path": relative_path,
                "title": title_match.group(1).strip() if title_match else name,
            }
        )
    return {"docCount": len(docs), "docs": docs}
