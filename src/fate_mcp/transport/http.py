"""Bounded HTTP/SSE transports behind the existing authenticated-gateway guard."""

from __future__ import annotations

import os

import uvicorn
from mcp.server import MCPServer
from mcp.server.transport_security import TransportSecuritySettings
from starlette.applications import Starlette


def _allowlist(name: str, default: str) -> list[str]:
    values = [item.strip() for item in os.environ.get(name, default).split(",") if item.strip()]
    if not values:
        raise ValueError(f"{name} must contain at least one allowlisted value.")
    return values


def create_http_app(
    server: MCPServer | None = None, *, transport: str = "streamable-http", host: str | None = None
) -> Starlette:
    from fate_mcp.__main__ import validate_transport_security

    if transport not in {"streamable-http", "sse"}:
        raise ValueError("Expected an HTTP or SSE transport.")
    validate_transport_security(transport)
    limit = int(os.environ.get("FATE_MCP_MAX_REQUEST_BYTES", "4194304"))
    if limit <= 0:
        raise ValueError("FATE_MCP_MAX_REQUEST_BYTES must be a positive integer.")
    security = TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=_allowlist("FATE_MCP_ALLOWED_HOSTS", "localhost:*,127.0.0.1:*,[::1]:*"),
        allowed_origins=_allowlist(
            "FATE_MCP_ALLOWED_ORIGINS", "http://localhost:*,http://127.0.0.1:*,http://[::1]:*"
        ),
    )
    if server is None:
        from fate_mcp.server import create_server

        server = create_server()
    # Hosted binding is intentional; the authenticated-gateway guard ran above.
    bind_host = host or os.environ.get("FATE_MCP_HOST", "0.0.0.0")  # nosec B104
    options = dict(
        max_request_body_size=limit,
        transport_security=security,
        host=bind_host,
    )
    if transport == "sse":
        return server.sse_app(**options)
    return server.streamable_http_app(json_response=True, stateless_http=True, **options)


def run_http_server(
    server: MCPServer | None = None, *, transport: str = "streamable-http", host: str, port: int
) -> None:
    uvicorn.run(create_http_app(server, transport=transport, host=host), host=host, port=port)


def main() -> None:
    # The factory checks the guard before importing or constructing the server.
    host = os.environ.get("FATE_MCP_HOST", "0.0.0.0")  # nosec B104
    port = int(os.environ.get("FATE_MCP_PORT", "8000"))
    run_http_server(host=host, port=port)


if __name__ == "__main__":
    main()
