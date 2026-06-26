"""Streamable-HTTP transport entrypoint for environmental-fate-mcp.

Run with the ``environmental-fate-mcp-http`` console script (hosted mode).
Host and port are controlled by env vars:

    FATE_MCP_HOST   (default: 0.0.0.0)
    FATE_MCP_PORT   (default: 8000)

The same FastMCP server object is used here as for the stdio entrypoint —
the MCP tool surface is identical on both transports.

Security posture:

The existing fail-closed remote-transport guard from ``fate_mcp.__main__`` is
enforced here before the server starts.  The guard requires that the env var
``FATE_MCP_ALLOW_UNAUTHENTICATED_HTTP=true`` is explicitly set, signalling that
the operator has placed this service behind an authenticated gateway.  Do NOT
set that env var on an internet-facing host without an authenticating proxy in
front.
"""

from __future__ import annotations

import os
import sys


def main() -> None:
    """HTTP entrypoint: wrap the MCP server with streamable-http and run uvicorn."""
    # Enforce the same fail-closed remote-transport security guard as the stdio
    # entrypoint.  This must run before the server is created / imported.
    from fate_mcp.__main__ import validate_transport_security

    validate_transport_security("streamable-http")

    try:
        import uvicorn
    except ImportError:
        print(
            "uvicorn is required for the HTTP transport.  "
            "Install it with:  pip install 'uvicorn[standard]'",
            file=sys.stderr,
        )
        sys.exit(1)

    from fate_mcp.server import create_server

    host = os.environ.get("FATE_MCP_HOST", "0.0.0.0")  # nosec B104 – bind addr is intentional for hosted mode
    port = int(os.environ.get("FATE_MCP_PORT", "8000"))

    mcp = create_server()
    # streamable_http_app() returns a Starlette ASGI app that speaks the
    # MCP streamable-HTTP protocol (same tool surface as the stdio server).
    app = mcp.streamable_http_app()

    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
