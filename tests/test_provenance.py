from pathlib import Path

from fate_mcp.runtime import FateRuntime
from fate_mcp.models import (
    BuildEnvironmentalReleaseScenarioRequest,
    Media,
    ReleaseFraction,
)


def test_provenance_timestamp_has_microsecond_precision() -> None:
    runtime = FateRuntime(Path(__file__).resolve().parents[1])
    scenario = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={"preferredName": "Timestamp precision test", "substance_class": "organic chemical"},
            total_release_mass_kg=1.0,
            release_fractions=[ReleaseFraction(medium=Media.WATER, fraction=1.0)],
            duration_days=1.0,
        )
    )
    provenance = scenario.provenance
    # Pydantic isoformat should always include the 'T' separator and microseconds
    iso = provenance.generated_at.isoformat()
    assert "T" in iso
    assert "." in iso or "+" in iso or "Z" in iso
    # Verify that serializing to JSON preserves microsecond component
    import json
    payload = json.loads(provenance.model_dump_json())
    assert "." in payload["generated_at"]
