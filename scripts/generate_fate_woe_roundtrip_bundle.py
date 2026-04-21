#!/usr/bin/env python3
"""Generate the checked-in Environmental Fate -> WoE round-trip bundle."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tests.fixtures.cross_suite.woe_roundtrip import (  # noqa: E402
    FIXTURE_PATH,
    WOE_SYNC_TARGET_PATH,
    build_fate_woe_roundtrip_bundle,
)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{json.dumps(payload, indent=2, sort_keys=True)}\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--sync-woe-target", action="store_true")
    args = parser.parse_args()

    payload = build_fate_woe_roundtrip_bundle()
    current_text = f"{json.dumps(payload, indent=2, sort_keys=True)}\n"

    if args.write:
        _write_json(FIXTURE_PATH, payload)
        print(f"wrote {FIXTURE_PATH}")
    elif FIXTURE_PATH.exists():
        existing_text = FIXTURE_PATH.read_text(encoding="utf-8")
        if existing_text == current_text:
            print(f"{FIXTURE_PATH} is current")
        else:
            print(f"{FIXTURE_PATH} is stale")
            return 1
    else:
        print(f"{FIXTURE_PATH} is missing")
        return 1

    if args.sync_woe_target:
        _write_json(WOE_SYNC_TARGET_PATH, payload)
        print(f"synced {WOE_SYNC_TARGET_PATH}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

