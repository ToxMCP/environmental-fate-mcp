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
    from fate_mcp.server import create_server

    parser = argparse.ArgumentParser(description="Run Environmental Fate MCP.")
    parser.add_argument(
        "--transport",
        default="stdio",
        choices=["stdio", "streamable-http", "sse"],
        help="MCP transport to use.",
    )
    args = parser.parse_args()
    validate_transport_security(args.transport)
    server = create_server()
    server.run(transport=args.transport)


if __name__ == "__main__":
    main()
