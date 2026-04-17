from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from fate_mcp.models import (
    ConcentrationEstimationResult,
    EnvironmentalReleaseScenario,
    FateModelRunOptions,
    ModelFamily,
    RunMode,
)


@dataclass(frozen=True)
class PluginKey:
    run_mode: RunMode
    model_family: ModelFamily


class FatePlugin(Protocol):
    key: PluginKey
    limitations: list[str]

    def run(
        self,
        scenario: EnvironmentalReleaseScenario,
        run_options: FateModelRunOptions,
    ) -> ConcentrationEstimationResult: ...
