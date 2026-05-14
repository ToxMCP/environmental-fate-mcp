"""Per-bundle SHA-256 integrity_hash byte-equality tests.

The release-bundle test in `test_release_reports.py` already proves that the
top-level release artifact is deterministic and checksummed. This module fills
the gap one level down: it proves that the per-run `integrity_hash` on a
`ConcentrationSurfaceBundle` and on a `RegulatoryHandoffPackage` is also byte-
stable across reruns of the deterministic kernel — and that the hash is
actually content-sensitive (different scenarios produce different hashes).

The `frozen_environment` context manager (shared with the pendimethalin
public slice runner) freezes the three non-deterministic sources the runtime
stamps onto outputs: UUID factories in `fate_mcp.models`, `generated_at`
timestamps in `fate_mcp.provenance`, and `executed_at` timestamps in
`fate_mcp.result_meta`.
"""

from __future__ import annotations

from pathlib import Path

from fate_mcp.integrations import (
    build_concentration_surface_bundle,
    export_regulatory_handoff_package,
)
from fate_mcp.models import (
    BuildEnvironmentalReleaseScenarioRequest,
    ExportRegulatoryHandoffPackageRequest,
    FateModelRunOptions,
    Media,
    ReleaseFraction,
)
from fate_mcp.runtime import FateRuntime

from tests._pendimethalin_slice_runner import frozen_environment as _frozen_environment


def _build_scenario(runtime: FateRuntime, *, total_mass_kg: float = 100.0):
    return runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={
                "preferredName": "Hash-stability test substance",
                "casrn": "100-00-0",
                "substance_class": "organic chemical",
            },
            total_release_mass_kg=total_mass_kg,
            release_fractions=[
                ReleaseFraction(medium=Media.WATER, fraction=0.7),
                ReleaseFraction(medium=Media.SOIL, fraction=0.3),
            ],
            duration_days=14.0,
        )
    )


def _run_pipeline(runtime: FateRuntime, total_mass_kg: float):
    with _frozen_environment():
        scenario = _build_scenario(runtime, total_mass_kg=total_mass_kg)
        run_options = FateModelRunOptions(region_profile_id=scenario.geographic_scope.region_id)
        result = runtime.estimate(scenario, run_options)
        bundle = build_concentration_surface_bundle(result)
        handoff = export_regulatory_handoff_package(
            ExportRegulatoryHandoffPackageRequest(result=result),
            runtime.provenance,
        )
    return bundle, handoff


def test_concentration_bundle_integrity_hash_is_byte_stable_on_rerun() -> None:
    """Two reruns of the deterministic kernel with byte-identical inputs must
    produce byte-identical `integrity_hash` values on the concentration bundle.

    This guards against accidental introduction of non-determinism into the
    bundle payload (e.g. an unfrozen timestamp, a Python `set` ordering leak,
    or a float-repr change).
    """
    runtime = FateRuntime(Path(__file__).resolve().parents[1])

    bundle_a, _ = _run_pipeline(runtime, total_mass_kg=100.0)
    bundle_b, _ = _run_pipeline(runtime, total_mass_kg=100.0)

    assert bundle_a.integrity_hash is not None
    assert bundle_b.integrity_hash is not None
    assert len(bundle_a.integrity_hash) == 64
    assert bundle_a.integrity_hash == bundle_b.integrity_hash, (
        "ConcentrationSurfaceBundle.integrity_hash drifted across two byte-identical "
        f"deterministic runs: {bundle_a.integrity_hash!r} vs {bundle_b.integrity_hash!r}"
    )


def test_regulatory_handoff_integrity_hash_is_byte_stable_on_rerun() -> None:
    """The downstream-handoff hash must satisfy the same byte-stability
    contract as the bundle hash. Regulatory consumers re-verify this hash."""
    runtime = FateRuntime(Path(__file__).resolve().parents[1])

    _, handoff_a = _run_pipeline(runtime, total_mass_kg=100.0)
    _, handoff_b = _run_pipeline(runtime, total_mass_kg=100.0)

    assert handoff_a.integrity_hash is not None
    assert handoff_b.integrity_hash is not None
    assert len(handoff_a.integrity_hash) == 64
    assert handoff_a.integrity_hash == handoff_b.integrity_hash, (
        "RegulatoryHandoffPackage.integrity_hash drifted across two byte-identical "
        f"deterministic runs: {handoff_a.integrity_hash!r} vs {handoff_b.integrity_hash!r}"
    )


def test_integrity_hash_is_content_sensitive() -> None:
    """Two reruns with *different* inputs must produce different hashes.

    Together with the byte-stability tests above, this proves the hash is a
    real fingerprint of the bundle payload and not a constant or a frozen
    placeholder. Two near-identical scenarios that differ only in the total
    release mass (100 kg vs 200 kg) should give different hashes on both
    artifacts.
    """
    runtime = FateRuntime(Path(__file__).resolve().parents[1])

    bundle_a, handoff_a = _run_pipeline(runtime, total_mass_kg=100.0)
    bundle_b, handoff_b = _run_pipeline(runtime, total_mass_kg=200.0)

    assert bundle_a.integrity_hash != bundle_b.integrity_hash, (
        "ConcentrationSurfaceBundle.integrity_hash collided across scenarios with "
        "different total_release_mass_kg; the hash is not content-sensitive."
    )
    assert handoff_a.integrity_hash != handoff_b.integrity_hash, (
        "RegulatoryHandoffPackage.integrity_hash collided across scenarios with "
        "different total_release_mass_kg; the hash is not content-sensitive."
    )
