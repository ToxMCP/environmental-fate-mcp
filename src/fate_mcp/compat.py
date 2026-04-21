from __future__ import annotations

import sys
from datetime import datetime, timezone

try:
    from datetime import UTC as UTC
except ImportError:  # pragma: no cover - exercised on older runtimes
    UTC = timezone.utc


MIN_SUPPORTED_PYTHON = (3, 12)


def python_version_string(version_info: tuple[int, int, int] | None = None) -> str:
    major, minor, micro = version_info or sys.version_info[:3]
    return f"{major}.{minor}.{micro}"


def ensure_supported_python_version(
    version_info: tuple[int, int, int] | None = None,
) -> None:
    effective_version = version_info or sys.version_info[:3]
    if effective_version < MIN_SUPPORTED_PYTHON:
        required = f"{MIN_SUPPORTED_PYTHON[0]}.{MIN_SUPPORTED_PYTHON[1]}"
        detected = python_version_string(effective_version)
        raise RuntimeError(
            "Environmental Fate MCP requires Python "
            f"{required}+; detected {detected}. "
            "Use `uv run environmental-fate-mcp` or another Python 3.12+ interpreter."
        )


__all__ = ["UTC", "datetime", "ensure_supported_python_version", "python_version_string"]
