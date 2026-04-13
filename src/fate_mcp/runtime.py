from __future__ import annotations

import math
from pathlib import Path

from fate_mcp.defaults import DefaultsRegistry
from fate_mcp.evidence import evidence_weight, is_low_confidence_evidence
from fate_mcp.errors import FateValidationError
from fate_mcp.models import (
    BuildEnvironmentalReleaseScenarioRequest,
    ConcentrationEstimationResult,
    EnvironmentalReleaseScenario,
    FateModelRunOptions,
    GeographicScope,
    LimitationNote,
    Media,
    ModelFamily,
    QualityFlag,
    ReconciledReleaseFraction,
    ReconciledScalarValue,
    ReconcileReleaseEvidenceRequest,
    ReleaseEvidenceConflict,
    ReleaseEvidenceObservation,
    ReleaseEvidenceReconciliationResult,
    ReleaseVectorConflict,
    ReleaseFraction,
    RunMode,
    Severity,
)
from fate_mcp.plugins import (
    AdapterStubPlugin,
    AdvectiveScreeningMassBalancePlugin,
    AdvectiveTimeBucketMassBalancePlugin,
    ExternalResultAdapterHarnessPlugin,
    ReferenceMassBalancePlugin,
)
from fate_mcp.plugins.base import FatePlugin, PluginKey
from fate_mcp.provenance import ProvenanceBuilder

MASS_RELATIVE_SPREAD_THRESHOLD = 0.25
FRACTION_ABSOLUTE_SPREAD_THRESHOLD = 0.15
VECTOR_COSINE_SIMILARITY_THRESHOLD = 0.5


class PluginRegistry:
    def __init__(self) -> None:
        self._plugins: dict[PluginKey, FatePlugin] = {}

    def register(self, plugin: FatePlugin) -> None:
        if plugin.key in self._plugins:
            raise FateValidationError(
                code="duplicate_plugin_registration",
                message=f"Plugin already registered for {plugin.key}",
                suggestion="Register each workflow and model family only once.",
            )
        self._plugins[plugin.key] = plugin

    def resolve(self, run_mode: RunMode, model_family: ModelFamily) -> FatePlugin:
        key = PluginKey(run_mode=run_mode, model_family=model_family)
        try:
            return self._plugins[key]
        except KeyError as exc:
            raise FateValidationError(
                code="unsupported_plugin_selection",
                message=f"No plugin registered for {run_mode.value}/{model_family.value}",
                suggestion="Choose a supported workflow or register a compatible adapter.",
            ) from exc


class FateRuntime:
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root
        self.defaults = DefaultsRegistry(repo_root)
        self.provenance = ProvenanceBuilder(self.defaults)
        self.plugins = PluginRegistry()
        self.plugins.register(ReferenceMassBalancePlugin(self.defaults, self.provenance))
        self.plugins.register(TimeBucketMassBalancePlugin(self.defaults, self.provenance))
        self.plugins.register(AdvectiveScreeningMassBalancePlugin(self.defaults, self.provenance))
        self.plugins.register(AdvectiveTimeBucketMassBalancePlugin(self.defaults, self.provenance))
        self.plugins.register(AdapterStubPlugin(self.defaults, self.provenance))
        self.plugins.register(ExternalResultAdapterHarnessPlugin(self.defaults, self.provenance))

    def build_environmental_release_scenario(
        self,
        request: BuildEnvironmentalReleaseScenarioRequest,
    ) -> EnvironmentalReleaseScenario:
        region_profile = self.defaults.get_region_profile(request.region_id)
        quality_flags = []
        limitations = [
            LimitationNote(
                code="region_profile",
                message=f"Scenario uses region profile {region_profile['displayName']}.",
            )
        ]
        if sum(item.fraction for item in request.release_fractions) < 1.0:
            quality_flags.append(
                QualityFlag(
                    code="unallocated_release_fraction",
                    severity=Severity.WARNING,
                    message="Release fractions sum to less than 1.0; unallocated mass is intentionally left outside scoped media.",
                )
            )
        return EnvironmentalReleaseScenario(
            chemical_identity=request.chemical_identity,
            total_release_mass_kg=request.total_release_mass_kg,
            release_fractions=request.release_fractions,
            duration_days=request.duration_days,
            timing_pattern=request.timing_pattern,
            geographic_scope=GeographicScope(
                region_id=request.region_id,
                context_label=request.context_label,
            ),
            treatment_assumptions=request.treatment_assumptions,
            parameter_records=request.parameter_records,
            evidence_sources=request.evidence_sources,
            provenance=self.provenance.bundle(request.evidence_sources),
            quality_flags=quality_flags,
            limitations=limitations,
        )

    def estimate(
        self,
        scenario: EnvironmentalReleaseScenario,
        run_options: FateModelRunOptions,
    ) -> ConcentrationEstimationResult:
        if scenario.geographic_scope.region_id != run_options.region_profile_id:
            raise FateValidationError(
                code="region_profile_mismatch",
                message="Run options region profile must match the scenario geographic scope.",
                suggestion="Align the scenario region and run options region_profile_id.",
            )
        plugin = self.plugins.resolve(run_options.run_mode, run_options.model_family)
        return plugin.run(scenario, run_options)

    def reconcile_release_evidence(
        self,
        request: ReconcileReleaseEvidenceRequest,
    ) -> ReleaseEvidenceReconciliationResult:
        evidence_inputs = request.evidence_inputs
        observations = [
            ReleaseEvidenceObservation(
                label=item.label,
                source_reference=item.source_reference,
                evidence_quality=item.evidence_quality,
                evidence_weight=evidence_weight(item.evidence_quality),
                total_release_mass_kg=item.total_release_mass_kg,
                release_fractions=item.release_fractions,
            )
            for item in evidence_inputs
        ]
        labels = [item.label for item in evidence_inputs]
        weights = [evidence_weight(item.evidence_quality) for item in evidence_inputs]
        masses = [item.total_release_mass_kg for item in evidence_inputs]
        total_weight = sum(weights)
        average_mass = sum(weight * mass for weight, mass in zip(weights, masses, strict=True)) / total_weight
        min_mass = min(masses)
        max_mass = max(masses)
        relative_spread = (max_mass - min_mass) / average_mass if average_mass else 0.0

        reconciled_scalars = [
            ReconciledScalarValue(
                field="total_release_mass_kg",
                reconciled_value=average_mass,
                unit="kg",
                weighting_strategy="evidence_quality_weighted_mean",
                total_weight=total_weight,
                min_value=min_mass,
                max_value=max_mass,
                relative_spread=relative_spread,
                status="agreed" if relative_spread <= MASS_RELATIVE_SPREAD_THRESHOLD else "conflict",
                contributing_labels=labels,
            )
        ]

        conflicts: list[ReleaseEvidenceConflict] = []
        quality_flags = []
        limitations = []
        agreed_values: dict[str, float] = {}
        low_confidence_labels = [
            item.label
            for item in evidence_inputs
            if is_low_confidence_evidence(item.evidence_quality)
        ]
        if relative_spread <= MASS_RELATIVE_SPREAD_THRESHOLD:
            agreed_values["total_release_mass_kg"] = average_mass
        else:
            conflicts.append(
                ReleaseEvidenceConflict(
                    field="total_release_mass_kg",
                    conflict_type="spread_exceeds_threshold",
                    description="Release mass evidence differs by more than the allowed relative spread threshold after evidence-quality weighting.",
                    observed_values=[
                        f"{item.label}: {item.total_release_mass_kg} kg (quality={item.evidence_quality}, weight={evidence_weight(item.evidence_quality):.2f})"
                        for item in evidence_inputs
                    ],
                    contributing_labels=labels,
                )
            )

        present_media = {
            release_fraction.medium
            for evidence_input in evidence_inputs
            for release_fraction in evidence_input.release_fractions
        }
        ordered_media = [medium for medium in Media if medium in present_media]
        vector_conflicts: list[ReleaseVectorConflict] = []
        vector_maps = {
            evidence_input.label: {
                fraction.medium: fraction.fraction for fraction in evidence_input.release_fractions
            }
            for evidence_input in evidence_inputs
        }
        for index, left in enumerate(evidence_inputs):
            left_vector = [vector_maps[left.label].get(medium, 0.0) for medium in ordered_media]
            left_norm = math.sqrt(sum(value * value for value in left_vector))
            for right in evidence_inputs[index + 1 :]:
                right_vector = [vector_maps[right.label].get(medium, 0.0) for medium in ordered_media]
                right_norm = math.sqrt(sum(value * value for value in right_vector))
                if left_norm <= 1e-12 or right_norm <= 1e-12:
                    cosine_similarity = 1.0 if left_vector == right_vector else 0.0
                else:
                    cosine_similarity = sum(
                        left_value * right_value
                        for left_value, right_value in zip(left_vector, right_vector, strict=True)
                    ) / (left_norm * right_norm)
                if cosine_similarity < VECTOR_COSINE_SIMILARITY_THRESHOLD:
                    vector_conflicts.append(
                        ReleaseVectorConflict(
                            labels=[left.label, right.label],
                            cosine_similarity=cosine_similarity,
                            threshold=VECTOR_COSINE_SIMILARITY_THRESHOLD,
                            description=(
                                "Release-fraction vectors are too dissimilar to reconcile into a single "
                                "screening scenario without destroying source scenario coherence."
                            ),
                            observed_vectors=[
                                f"{left.label}: "
                                + ", ".join(
                                    f"{medium.value}={vector_maps[left.label].get(medium, 0.0):.3f}"
                                    for medium in ordered_media
                                ),
                                f"{right.label}: "
                                + ", ".join(
                                    f"{medium.value}={vector_maps[right.label].get(medium, 0.0):.3f}"
                                    for medium in ordered_media
                                ),
                            ],
                        )
                    )
        reconciled_release_fractions = []
        consensus_release_fractions = []
        for medium in ordered_media:
            values = []
            for evidence_input in evidence_inputs:
                medium_map = {fraction.medium: fraction.fraction for fraction in evidence_input.release_fractions}
                values.append(medium_map.get(medium, 0.0))
            average_fraction = (
                sum(weight * value for weight, value in zip(weights, values, strict=True)) / total_weight
            )
            min_fraction = min(values)
            max_fraction = max(values)
            absolute_spread = max_fraction - min_fraction
            status = "agreed" if absolute_spread <= FRACTION_ABSOLUTE_SPREAD_THRESHOLD else "conflict"
            reconciled_release_fractions.append(
                ReconciledReleaseFraction(
                    medium=medium,
                    reconciled_fraction=average_fraction,
                    weighting_strategy="evidence_quality_weighted_mean",
                    total_weight=total_weight,
                    min_fraction=min_fraction,
                    max_fraction=max_fraction,
                    absolute_spread=absolute_spread,
                    status=status,
                    contributing_labels=labels,
                )
            )
            if status == "agreed":
                agreed_values[f"release_fraction_{medium.value}"] = average_fraction
            else:
                conflicts.append(
                    ReleaseEvidenceConflict(
                        field=f"release_fraction_{medium.value}",
                        conflict_type="spread_exceeds_threshold",
                        description=f"Release fraction evidence for {medium.value} differs by more than the allowed absolute spread threshold after evidence-quality weighting.",
                        observed_values=[
                            f"{evidence_input.label}: "
                            f"{next((fraction.fraction for fraction in evidence_input.release_fractions if fraction.medium == medium), 0.0)} "
                            f"(quality={evidence_input.evidence_quality}, weight={evidence_weight(evidence_input.evidence_quality):.2f})"
                            for evidence_input in evidence_inputs
                        ],
                        contributing_labels=labels,
                    )
                )
            if average_fraction > 0.0:
                consensus_release_fractions.append(
                    ReleaseFraction(medium=medium, fraction=average_fraction)
                )

        total_consensus_fraction = sum(item.fraction for item in consensus_release_fractions)
        if total_consensus_fraction > 1.0:
            consensus_release_fractions = [
                ReleaseFraction(
                    medium=item.medium,
                    fraction=item.fraction / total_consensus_fraction,
                )
                for item in consensus_release_fractions
            ]
            limitations.append(
                LimitationNote(
                    code="reconciliation_normalized_release_fractions",
                    message="Consensus release fractions were normalized to sum to 1.0 after averaging evidence inputs.",
                )
            )

        if conflicts:
            quality_flags.append(
                QualityFlag(
                    code="release_evidence_conflict",
                    severity=Severity.WARNING,
                    message="One or more release evidence fields remain in conflict after reconciliation.",
                )
            )
            limitations.append(
                LimitationNote(
                    code="reconciliation_uses_means",
                    message="The reconciled screening scenario uses evidence-quality-weighted means across conflicting evidence inputs.",
                )
            )
        if low_confidence_labels:
            quality_flags.append(
                QualityFlag(
                    code="low_confidence_release_evidence",
                    severity=Severity.WARNING,
                    message="Low-confidence release evidence contributed to reconciliation: "
                    + ", ".join(sorted(low_confidence_labels)),
                )
            )
            limitations.append(
                LimitationNote(
                    code="weighted_by_evidence_quality",
                    message="Reconciliation used evidence-quality weighting to reduce the influence of surrogate or heuristic inputs.",
                )
            )
        if vector_conflicts:
            quality_flags.append(
                QualityFlag(
                    code="release_vector_conflict",
                    severity=Severity.WARNING,
                    message="Release-media vectors are too dissimilar for automatic blended-scenario reconciliation.",
                )
            )
            limitations.append(
                LimitationNote(
                    code="vector_reconciliation_blocked",
                    message=(
                        "Automatic reconciled_scenario generation was blocked because release-media vectors "
                        "were not sufficiently coherent."
                    ),
                )
            )

        scenario = None
        if not vector_conflicts:
            scenario = self.build_environmental_release_scenario(
                BuildEnvironmentalReleaseScenarioRequest(
                    chemical_identity=request.chemical_identity,
                    total_release_mass_kg=average_mass,
                    release_fractions=consensus_release_fractions,
                    duration_days=request.duration_days,
                    region_id=request.region_id,
                    context_label=request.context_label,
                    evidence_sources=[item.source_reference for item in evidence_inputs],
                )
            )
            scenario = scenario.model_copy(
                update={
                    "quality_flags": scenario.quality_flags + quality_flags,
                    "limitations": scenario.limitations + limitations,
                }
            )
        recommended_next_actions = []
        if any(conflict.field == "total_release_mass_kg" for conflict in conflicts):
            recommended_next_actions.append(
                "Resolve competing release-mass estimates before higher-confidence or regulatory use."
            )
        fraction_conflicts = [
            conflict.field.replace("release_fraction_", "")
            for conflict in conflicts
            if conflict.field.startswith("release_fraction_")
        ]
        if fraction_conflicts:
            recommended_next_actions.append(
                "Resolve conflicting release-media allocations for: " + ", ".join(sorted(fraction_conflicts)) + "."
            )
        if low_confidence_labels:
            recommended_next_actions.append(
                "Replace low-confidence release evidence where possible: " + ", ".join(sorted(low_confidence_labels)) + "."
            )
        if vector_conflicts:
            recommended_next_actions.append(
                "Do not synthesize a blended screening scenario until release-vector conflicts are resolved."
            )
        if not conflicts and not vector_conflicts:
            recommended_next_actions.append("Evidence is internally consistent for screening use.")

        return ReleaseEvidenceReconciliationResult(
            reconciled_scenario=scenario,
            evidence_observations=observations,
            reconciled_scalars=reconciled_scalars,
            reconciled_release_fractions=reconciled_release_fractions,
            agreed_values=agreed_values,
            conflicts=conflicts,
            vector_conflicts=vector_conflicts,
            unresolved_conflict_count=len(conflicts) + len(vector_conflicts),
            recommended_next_actions=recommended_next_actions,
            provenance=self.provenance.bundle([item.source_reference for item in evidence_inputs]),
            quality_flags=quality_flags,
            limitations=limitations,
        )


class TimeBucketMassBalancePlugin(ReferenceMassBalancePlugin):
    key = PluginKey(
        run_mode=RunMode.TIME_BUCKET,
        model_family=ModelFamily.REFERENCE_MASS_BALANCE,
    )
