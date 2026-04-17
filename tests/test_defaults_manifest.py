import hashlib
import json
from pathlib import Path

import pytest


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_defaults_manifest_hashes_are_current() -> None:
    """Every file listed in defaults/manifest.json must have a correct SHA-256 hash."""
    repo_root = Path(__file__).resolve().parents[1]
    manifest_path = repo_root / "defaults" / "manifest.json"
    manifest = json.loads(manifest_path.read_text())

    errors = []
    for entry in manifest.get("files", []):
        file_path = repo_root / entry["path"]
        if not file_path.exists():
            errors.append(f"Missing file: {entry['path']}")
            continue
        actual_hash = _sha256(file_path)
        expected_hash = entry["sha256"]
        if actual_hash != expected_hash:
            errors.append(
                f"Hash mismatch for {entry['path']}: expected {expected_hash}, got {actual_hash}"
            )

    assert not errors, "Defaults manifest hash validation failed:\n" + "\n".join(errors)


def test_defaults_manifest_covers_all_json_files() -> None:
    """Every .json file under defaults/v1/ and defaults/extensions/ must be listed in the manifest."""
    repo_root = Path(__file__).resolve().parents[1]
    manifest_path = repo_root / "defaults" / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest_paths = {entry["path"] for entry in manifest.get("files", [])}

    json_files = set()
    for directory in [repo_root / "defaults" / "v1", repo_root / "defaults" / "extensions"]:
        if directory.exists():
            for file_path in directory.glob("*.json"):
                relative = str(file_path.relative_to(repo_root))
                json_files.add(relative)

    missing_from_manifest = sorted(json_files - manifest_paths)
    assert not missing_from_manifest, (
        f"Defaults JSON files missing from manifest: {missing_from_manifest}"
    )


def test_defaults_manifest_has_consistent_version() -> None:
    """All entries in the manifest must declare the same defaultsVersion."""
    repo_root = Path(__file__).resolve().parents[1]
    manifest_path = repo_root / "defaults" / "manifest.json"
    manifest = json.loads(manifest_path.read_text())

    top_version = manifest.get("defaultsVersion")
    assert top_version is not None, "manifest.json missing top-level defaultsVersion"

    version_mismatches = []
    for entry in manifest.get("files", []):
        entry_version = entry.get("defaultsVersion")
        if entry_version != top_version:
            version_mismatches.append(
                f"{entry['path']}: defaultsVersion={entry_version} (expected {top_version})"
            )

    assert not version_mismatches, (
        "Defaults manifest version consistency failed:\n" + "\n".join(version_mismatches)
    )
