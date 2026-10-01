"""Test-only launcher with fixed invocation clocks and repeatable UUIDs.

The scientific algorithms generate random scenario identifiers and invocation
timestamps. Fix those in the server process to compare every payload field
across SDK generations without discarding provenance or scientific fields.
Production console entrypoints do not import this module.
"""

from __future__ import annotations

import hashlib
import sys
from datetime import datetime
from itertools import count
from threading import Lock
from uuid import UUID, uuid4

from fate_mcp.server import create_server
from fate_mcp.__main__ import main


class InvocationClock(datetime):
    @classmethod
    def now(cls, tz=None):
        fixed = cls(2026, 10, 1, 12, 0, 0)
        return fixed.replace(tzinfo=tz) if tz is not None else fixed


sequence = count()
lock = Lock()


def invocation_uuid():
    with lock:
        value = next(sequence)
    return UUID(bytes=hashlib.sha256(f"compatibility-{value}".encode()).digest()[:16])


def freeze_invocation_context():
    for name, module in list(sys.modules.items()):
        if name.startswith("fate_mcp."):
            if getattr(module, "uuid4", None) is uuid4:
                module.uuid4 = invocation_uuid
            if getattr(module, "datetime", None) is datetime:
                module.datetime = InvocationClock


if __name__ == "__main__":
    create_server()
    freeze_invocation_context()
    main()
