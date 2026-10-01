"""The stdio handshake identifies this application rather than its SDK."""

from __future__ import annotations

import sys
from pathlib import Path

import anyio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from fate_mcp.package_metadata import PACKAGE_NAME, VERSION


def test_stdio_initialize_declares_application_version(tmp_path: Path) -> None:
    async def check_initialization() -> None:
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "fate_mcp"],
            # Explicitly use the source package for this source-tree gate. A
            # separate release check verifies the non-editable installed wheel.
            env={"PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")},
            cwd=tmp_path,
        )
        with anyio.fail_after(15):
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    result = await session.initialize()
                    assert result.server_info.name == PACKAGE_NAME
                    assert result.server_info.version == VERSION

    anyio.run(check_initialization)
