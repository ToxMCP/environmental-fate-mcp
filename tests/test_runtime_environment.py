import pytest

from fate_mcp.compat import ensure_supported_python_version
from fate_mcp.resources import package_data_root, resolve_resource_root


def test_supported_python_version_guard_accepts_python_312() -> None:
    ensure_supported_python_version((3, 12, 0))


def test_supported_python_version_guard_rejects_python_311() -> None:
    with pytest.raises(RuntimeError, match="requires Python 3.12\\+"):
        ensure_supported_python_version((3, 11, 9))


def test_resource_root_resolves_checkout_by_default() -> None:
    repo_root = resolve_resource_root()
    assert (repo_root / "defaults" / "manifest.json").exists()
    assert (repo_root / "docs" / "contracts" / "schemas" / "manifest.json").exists()
    assert (repo_root / "schemas" / "examples" / "manifest.json").exists()


def test_resource_root_honors_env_override(tmp_path, monkeypatch) -> None:
    for path in (
        tmp_path / "defaults",
        tmp_path / "docs" / "contracts" / "schemas",
        tmp_path / "schemas" / "examples",
    ):
        path.mkdir(parents=True)
        (path / "manifest.json").write_text("{}\n")

    monkeypatch.setenv("FATE_MCP_RESOURCE_ROOT", str(tmp_path))
    assert resolve_resource_root() == tmp_path.resolve()


def test_resource_root_falls_back_to_packaged_data(monkeypatch, tmp_path) -> None:
    import fate_mcp.resources as resources

    monkeypatch.delenv("FATE_MCP_RESOURCE_ROOT", raising=False)
    monkeypatch.setattr(resources, "checkout_resource_root", lambda: tmp_path / "missing")
    assert resources.resolve_resource_root() == package_data_root().resolve()
