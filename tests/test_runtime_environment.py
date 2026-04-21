import pytest

from fate_mcp.compat import ensure_supported_python_version


def test_supported_python_version_guard_accepts_python_312() -> None:
    ensure_supported_python_version((3, 12, 0))


def test_supported_python_version_guard_rejects_python_311() -> None:
    with pytest.raises(RuntimeError, match="requires Python 3.12\\+"):
        ensure_supported_python_version((3, 11, 9))
