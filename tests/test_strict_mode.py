from pathlib import Path

import pytest

from fate_mcp.errors import FateValidationError
from fate_mcp.models import (
    BuildEnvironmentalReleaseScenarioRequest,
    Media,
    ReleaseFraction,
)
from fate_mcp.runtime import FateRuntime

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_strict_mode_allows_in_range_temperature_correction() -> None:
    runtime = FateRuntime(REPO_ROOT, strict_mode=True)
    scenario = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={"preferredName": "Strict temp test", "substance_class": "organic chemical"},
            total_release_mass_kg=1.0,
            release_fractions=[ReleaseFraction(medium=Media.WATER, fraction=1.0)],
            duration_days=1.0,
            temperature_c=15.0,
        )
    )
    assert scenario.temperature_c == 15.0


def test_strict_mode_rejects_temperature_outside_governed_range() -> None:
    runtime = FateRuntime(REPO_ROOT, strict_mode=True)
    with pytest.raises(FateValidationError) as exc_info:
        runtime.build_environmental_release_scenario(
            BuildEnvironmentalReleaseScenarioRequest(
                chemical_identity={"preferredName": "Strict out-of-range temp test", "substance_class": "organic chemical"},
                total_release_mass_kg=1.0,
                release_fractions=[ReleaseFraction(medium=Media.WATER, fraction=1.0)],
                duration_days=1.0,
                temperature_c=-5.0,
            )
        )
    assert exc_info.value.payload.code == "temperature_correction_clamped_to_governed_range"


def test_non_strict_mode_allows_non_default_temperature_with_limitation() -> None:
    runtime = FateRuntime(REPO_ROOT, strict_mode=False)
    scenario = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={"preferredName": "Non-strict temp test", "substance_class": "organic chemical"},
            total_release_mass_kg=1.0,
            release_fractions=[ReleaseFraction(medium=Media.WATER, fraction=1.0)],
            duration_days=1.0,
            temperature_c=15.0,
        )
    )
    assert scenario.temperature_c == 15.0
    codes = [lim.code for lim in scenario.limitations]
    assert "temperature_correction_governed" in codes
