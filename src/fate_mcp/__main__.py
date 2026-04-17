from __future__ import annotations

import argparse

from fate_mcp.server import create_server


def main() -> None:
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
