"""Require the released Fate catalog and identical client/transport science."""

from __future__ import annotations

import argparse
import hashlib
import json
from copy import deepcopy
from pathlib import Path


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def comparable_results(results, application_version=None):
    """Check modern envelope fields and compare all application fields unchanged."""
    results = deepcopy(results)
    for result in results.values():
        if "resultType" in result and result.pop("resultType") != "complete":
            raise AssertionError("Unexpected multi-round-trip response")
        if "ttlMs" in result and result.pop("ttlMs") != 0:
            raise AssertionError("Scientific results must not be cached")
        if "cacheScope" in result and result.pop("cacheScope") != "private":
            raise AssertionError("Public scientific result caching is forbidden")
        metadata = result.get("_meta", {})
        identity = metadata.pop("io.modelcontextprotocol/serverInfo", None)
        if identity is not None and identity["name"] != "Environmental Fate MCP":
            raise AssertionError("Unexpected server identity")
        if (
            identity is not None
            and application_version is not None
            and identity["version"] != application_version
        ):
            raise AssertionError("Unexpected server version")
        # SDK2's modern TypedDict serializer omits null optional result metadata.
        metadata = {key: item for key, item in metadata.items() if item is not None}
        if metadata:
            result["_meta"] = metadata
        else:
            result.pop("_meta", None)
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("reports", nargs="+")
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--application-version", required=True)
    args = parser.parse_args()
    baseline = json.loads(Path(args.baseline).read_text())
    reports = [json.loads(Path(path).read_text()) for path in args.reports]
    if {report["clientSDK"] for report in reports} != {"1.30.0", "2.2.0"}:
        raise AssertionError("Both actual SDK generations must be exercised")
    if {report["protocol"] for report in reports} != {"2025-11-25", "2026-07-28"}:
        raise AssertionError("Both protocol generations must be exercised")
    expected_results = comparable_results(reports[0]["results"], args.application_version)
    for report in reports:
        fingerprint = digest(report["catalog"])
        if fingerprint != baseline["catalogSHA256"]:
            raise AssertionError("Released catalog/schema contract drift")
        if comparable_results(report["results"], args.application_version) != expected_results:
            raise AssertionError("Client or transport changed scientific results")
        error = report["results"]["domain-error"]
        if (
            not error["isError"]
            or "Run options region profile must match" not in error["content"][0]["text"]
        ):
            raise AssertionError("Domain error must retain its released message")
    print(
        json.dumps(
            {
                "compatible": True,
                "clients": len(reports),
                "catalogCounts": baseline["counts"],
                "workflows": len(expected_results),
            }
        )
    )


if __name__ == "__main__":
    main()
