from __future__ import annotations

import argparse

from fate_mcp.compat import ensure_supported_python_version


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
    server = create_server()
    server.run(transport=args.transport)


if __name__ == "__main__":
    main()
