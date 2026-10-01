from __future__ import annotations

import argparse
import os

from fate_mcp.compat import ensure_supported_python_version


REMOTE_TRANSPORTS = {"streamable-http", "sse"}
ALLOW_UNAUTHENTICATED_HTTP_ENV = "FATE_MCP_ALLOW_UNAUTHENTICATED_HTTP"


def validate_transport_security(transport: str) -> None:
    if transport not in REMOTE_TRANSPORTS:
        return
    if os.getenv(ALLOW_UNAUTHENTICATED_HTTP_ENV, "").strip().lower() in {"1", "true", "yes"}:
        return
    raise SystemExit(
        "Refusing to start unauthenticated HTTP/SSE transport. Keep stdio for local use or set "
        f"{ALLOW_UNAUTHENTICATED_HTTP_ENV}=true only behind an authenticated local gateway."
    )


def main() -> None:
    ensure_supported_python_version()
    parser = argparse.ArgumentParser(description="Run Environmental Fate MCP.")
    parser.add_argument(
        "--transport",
        default="stdio",
        choices=["stdio", "streamable-http", "sse"],
        help="MCP transport to use.",
    )
    parser.add_argument("--host", default=os.getenv("FATE_MCP_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("FATE_MCP_PORT", "8000")))
    args = parser.parse_args()
    validate_transport_security(args.transport)
    from fate_mcp.server import create_server

    server = create_server()
    if args.transport == "stdio":
        server.run(transport="stdio")
    else:
        from fate_mcp.transport.http import run_http_server

        run_http_server(server, transport=args.transport, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
