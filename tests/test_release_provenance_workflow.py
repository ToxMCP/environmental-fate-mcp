from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "release-provenance.yml"
PROVENANCE_DOC_PATH = REPO_ROOT / "docs" / "release_provenance.md"


def test_release_provenance_workflow_has_required_triggers_and_permissions() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "release:" in workflow
    assert "types: [published]" in workflow
    assert "workflow_dispatch:" in workflow
    assert "contents: write" in workflow
    assert "id-token: write" in workflow
    assert "attestations: write" in workflow
    assert "artifact-metadata: write" not in workflow


def test_release_provenance_workflow_attests_and_uploads_expected_assets() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "uses: actions/attest@v4" in workflow
    assert "subject-path: release-assets/*" in workflow
    assert "gh attestation verify" in workflow
    assert "gh release upload" in workflow
    assert "environmental_fate_mcp-${{ steps.release.outputs.version }}-py3-none-any.whl" in workflow
    assert "environmental_fate_mcp-${{ steps.release.outputs.version }}.tar.gz" in workflow
    assert "RELEASE_ASSET_SHA256SUMS" in workflow
    assert "scientific-trust-pack.md" in workflow


def test_release_provenance_doc_includes_verification_and_boundary_language() -> None:
    doc = PROVENANCE_DOC_PATH.read_text(encoding="utf-8")

    assert "gh attestation verify" in doc
    assert "ToxMCP/environmental-fate-mcp" in doc
    lower_doc = doc.lower()
    assert "scientific validation" in lower_doc
    assert "regulator acceptance" in lower_doc
    assert "Sigstore" in doc
