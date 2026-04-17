from __future__ import annotations

from pathlib import Path


DOC_RESOURCE_MAP = {
    "operator-guide": "docs/operator_guide.md",
    "provenance-policy": "docs/provenance_policy.md",
    "validation-framework": "docs/validation_framework.md",
    "fate-model-boundary-guide": "docs/fate_model_boundary_guide.md",
    "suite-integration-guide": "docs/suite_integration.md",
    "release-readiness": "docs/release_readiness.md",
    "adapter-spi": "docs/adapter_spi.md",
    "model-applicability-limits": "docs/model_applicability_limits.md",
}


def read_doc(repo_root: Path, name: str) -> str:
    if name not in DOC_RESOURCE_MAP:
        raise ValueError(f"Unknown doc name: {name}")
    relative_path = DOC_RESOURCE_MAP[name]
    return (repo_root / relative_path).read_text()
