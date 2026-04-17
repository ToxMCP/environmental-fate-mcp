from __future__ import annotations

from fate_mcp.models import (
    ConcentrationEstimationResult,
    EnvironmentalReleaseScenario,
    FateAssumptionRecord,
    FateModelRunOptions,
    LimitationNote,
    ModelFamily,
    QualityFlag,
    RunMode,
    Severity,
    SourceClassification,
)
from fate_mcp.plugins.base import PluginKey
from fate_mcp.plugins.reference_mass_balance import ReferenceMassBalancePlugin


class AdapterStubPlugin(ReferenceMassBalancePlugin):
    key = PluginKey(
        run_mode=RunMode.STEADY_STATE,
        model_family=ModelFamily.ADAPTER_STUB,
    )
    limitations = [
        "Adapter stub simulates normalization of an external model-family output.",
        "Adapter stub is an extension-hook example and not a scientific engine endorsement.",
    ]

    def run(
        self,
        scenario: EnvironmentalReleaseScenario,
        run_options: FateModelRunOptions,
    ) -> ConcentrationEstimationResult:
        normalized = super().run(scenario, run_options.model_copy(update={"model_family": ModelFamily.REFERENCE_MASS_BALANCE}))
        surfaces = []
        for surface in normalized.surfaces:
            surfaces.append(
                surface.model_copy(
                    update={
                        "model_family": ModelFamily.ADAPTER_STUB,
                        "concentration_value": surface.concentration_value * 1.05,
                        "limitations": surface.limitations
                        + [
                            LimitationNote(
                                code="adapter_stub",
                                message="Surface was normalized from a synthetic external-model-like payload.",
                            )
                        ],
                    }
                )
            )

        assumptions = normalized.assumptions + [
            FateAssumptionRecord(
                parameter="adapter_normalization_factor",
                value=1.05,
                unit="scalar",
                source_classification=SourceClassification.DERIVED,
                rationale="Synthetic normalization factor applied by the adapter stub.",
            )
        ]
        run_summary = normalized.run_summary.model_copy(
            update={
                "model_family": ModelFamily.ADAPTER_STUB,
                "assumptions_applied": assumptions,
                "warnings": normalized.run_summary.warnings
                + [
                    QualityFlag(
                        code="adapter_stub",
                        severity=Severity.INFO,
                        message="Adapter stub path was used to simulate an external model-family normalization.",
                    )
                ],
            }
        )
        return ConcentrationEstimationResult(
            surfaces=surfaces,
            run_summary=run_summary,
            assumptions=assumptions,
        )
