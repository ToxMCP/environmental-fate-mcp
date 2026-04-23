from __future__ import annotations

import os
import shutil
from pathlib import Path


RESOURCE_ROOT_ENV = "FATE_MCP_RESOURCE_ROOT"
IMPORT_ROOTS_ENV = "FATE_MCP_IMPORT_ROOTS"
PACKAGE_DATA_DIR_NAME = "package_data"
RESOURCE_SENTINELS = (
    Path("defaults") / "manifest.json",
    Path("docs") / "contracts" / "schemas" / "manifest.json",
    Path("schemas") / "examples" / "manifest.json",
)
MIRRORED_RESOURCE_DIRS = ("defaults", "docs", "schemas", "config", "evals")


def package_data_root() -> Path:
    return Path(__file__).resolve().parent / PACKAGE_DATA_DIR_NAME


def checkout_resource_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _valid_resource_root(path: Path) -> bool:
    return path.is_dir() and all((path / sentinel).exists() for sentinel in RESOURCE_SENTINELS)


def _resolve_existing_resource_root(path: Path, *, source: str) -> Path:
    resolved = path.expanduser().resolve()
    if not _valid_resource_root(resolved):
        sentinels = ", ".join(str(item) for item in RESOURCE_SENTINELS)
        raise RuntimeError(
            f"{source} does not point at a valid Environmental Fate MCP resource root: "
            f"{resolved}. Expected {sentinels}."
        )
    return resolved


def resolve_resource_root() -> Path:
    override = os.environ.get(RESOURCE_ROOT_ENV)
    if override:
        return _resolve_existing_resource_root(Path(override), source=RESOURCE_ROOT_ENV)

    checkout_root = checkout_resource_root()
    if _valid_resource_root(checkout_root):
        return checkout_root

    packaged_root = package_data_root()
    if _valid_resource_root(packaged_root):
        return packaged_root.resolve()

    raise RuntimeError(
        "Could not locate Environmental Fate MCP resources. Set "
        f"{RESOURCE_ROOT_ENV} to a directory containing defaults/, docs/, and schemas/."
    )


def is_packaged_resource_root(resource_root: Path) -> bool:
    try:
        return resource_root.resolve() == package_data_root().resolve()
    except FileNotFoundError:
        return False


def refresh_packaged_resource_mirror(repo_root: Path) -> Path:
    package_root = repo_root / "src" / "fate_mcp" / PACKAGE_DATA_DIR_NAME
    package_root.mkdir(parents=True, exist_ok=True)
    for directory in MIRRORED_RESOURCE_DIRS:
        source = repo_root / directory
        target = package_root / directory
        if target.exists():
            shutil.rmtree(target)
        if source.exists():
            shutil.copytree(source, target)
    return package_root


def configured_import_roots(resource_root: Path) -> list[Path]:
    roots = [resource_root / "config" / "adapter-fixtures"]
    extra_roots = os.environ.get(IMPORT_ROOTS_ENV)
    if extra_roots:
        roots.extend(Path(item) for item in extra_roots.split(os.pathsep) if item)
    resolved_roots = []
    for root in roots:
        resolved = root.expanduser().resolve()
        if resolved.exists():
            resolved_roots.append(resolved)
    return resolved_roots


def path_is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True
