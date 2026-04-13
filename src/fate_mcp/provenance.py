from __future__ import annotations

from datetime import UTC, datetime

from fate_mcp.defaults import DefaultsRegistry
from fate_mcp.models import (
    FateAssumptionRecord,
    FateParameterRecord,
    QualityFlag,
    Severity,
    SourceClassification,
    SourceReference,
    ProvenanceBundle,
)
from fate_mcp.package_metadata import ALGORITHM_VERSION, DEFAULTS_VERSION, SCHEMA_VERSION


class ProvenanceBuilder:
    def __init__(self, defaults_registry: DefaultsRegistry) -> None:
        self.defaults_registry = defaults_registry

    def bundle(self, source_references: list[SourceReference] | None = None) -> ProvenanceBundle:
        return ProvenanceBundle(
            schema_version=SCHEMA_VERSION,
            defaults_version=DEFAULTS_VERSION,
            algorithm_version=ALGORITHM_VERSION,
            generated_at=datetime.now(UTC),
            source_references=source_references or [],
        )

    def curated_default(self, parameter: str, rationale: str) -> FateAssumptionRecord:
        source_reference = self.defaults_registry.parameter_source_reference(parameter)
        parameter_record = self.defaults_registry.parameter_record(parameter)
        return FateAssumptionRecord(
            parameter=parameter,
            value=float(parameter_record["value"]),
            unit=parameter_record["unit"],
            source_classification=SourceClassification.CURATED_DEFAULT,
            rationale=rationale,
            source_reference=source_reference,
        )

    def derived(self, parameter: str, value: float | str, unit: str | None, rationale: str) -> FateAssumptionRecord:
        return FateAssumptionRecord(
            parameter=parameter,
            value=value,
            unit=unit,
            source_classification=SourceClassification.DERIVED,
            rationale=rationale,
        )

    def user_input(self, parameter: str, value: float | str, unit: str | None, rationale: str) -> FateAssumptionRecord:
        return FateAssumptionRecord(
            parameter=parameter,
            value=value,
            unit=unit,
            source_classification=SourceClassification.USER_INPUT,
            rationale=rationale,
        )

    def from_parameter_record(
        self,
        parameter_record: FateParameterRecord,
        rationale: str,
    ) -> FateAssumptionRecord:
        return FateAssumptionRecord(
            parameter=parameter_record.parameter,
            value=parameter_record.value,
            unit=parameter_record.unit,
            source_classification=parameter_record.source_classification,
            rationale=rationale,
            source_reference=parameter_record.source_reference,
            quality_flags=parameter_record.quality_flags,
        )

    def heuristic(
        self,
        parameter: str,
        value: float | str,
        unit: str | None,
        rationale: str,
        warning: str,
    ) -> FateAssumptionRecord:
        return FateAssumptionRecord(
            parameter=parameter,
            value=value,
            unit=unit,
            source_classification=SourceClassification.HEURISTIC,
            rationale=rationale,
            quality_flags=[
                QualityFlag(
                    code="heuristic_input",
                    severity=Severity.WARNING,
                    message=warning,
                )
            ],
        )
