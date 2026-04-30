from __future__ import annotations

import pytest

from fate_mcp.__main__ import validate_transport_security


def test_stdio_transport_is_allowed_by_default() -> None:
    validate_transport_security("stdio")


def test_http_transports_fail_closed_without_explicit_gateway(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FATE_MCP_ALLOW_UNAUTHENTICATED_HTTP", raising=False)
    with pytest.raises(SystemExit, match="Refusing to start unauthenticated"):
        validate_transport_security("streamable-http")


def test_http_transports_can_be_overridden_for_authenticated_gateway(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FATE_MCP_ALLOW_UNAUTHENTICATED_HTTP", "true")
    validate_transport_security("sse")
