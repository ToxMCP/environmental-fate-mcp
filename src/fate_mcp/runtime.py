from __future__ import annotations
import random
import statistics

import math
from pathlib import Path

from fate_mcp.defaults import DefaultsRegistry
from fate_mcp.evidence import evidence_weight, is_low_confidence_evidence
from fate_mcp.errors import FateValidationError, FateRegistryError
from fate_mcp.models import (
    ProbabilisticConcentrationResult,
    ProbabilisticSurfaceSummary,
    ProbabilisticRunSummary,
    BuildEnvironmentalReleaseScenarioRequest,
    ConcentrationEstimationResult,
    EnvironmentalReleaseScenario,
    FateAssumptionRecord,
    ResultMetadata,
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

MAX_DISTRIBUTION_SAMPLE_ATTEMPTS = 100


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
    def __init__(
        self,
        repo_root: Path,
        strict_mode: bool = False,
        verify_defaults_manifest: bool = True,
    ) -> None:
        self.repo_root = repo_root
        self.strict_mode = strict_mode
        self.defaults = DefaultsRegistry(
            repo_root,
            verify_defaults_manifest=verify_defaults_manifest,
        )
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
        temperature_policy = self.defaults.temperature_correction_policy()
        quality_flags = []
        limitations = [
            LimitationNote(
                code="region_profile",
                message=f"Scenario uses region profile {region_profile['displayName']}.",
            )
        ]
        if "substance_class" not in request.chemical_identity:
            limitations.append(
                LimitationNote(
                    code="missing_substance_class",
                    message=(
                        "Scenario chemical_identity does not declare substance_class; scientific "
                        "applicability will remain review-needed until substance scope is explicit."
                    ),
                )
            )
        if sum(item.fraction for item in request.release_fractions) < 1.0:
            quality_flags.append(
                QualityFlag(
                    code="unallocated_release_fraction",
                    severity=Severity.WARNING,
                    message="Release fractions sum to less than 1.0; unallocated mass is intentionally left outside scoped media.",
                )
            )
        if request.temperature_c != temperature_policy.reference_temperature_c:
            if (
                request.temperature_c < temperature_policy.minimum_supported_temperature_c
                or request.temperature_c > temperature_policy.maximum_supported_temperature_c
            ):
                temp_message = (
                    f"Scenario temperature is {request.temperature_c} °C, which falls outside the governed "
                    f"{temperature_policy.minimum_supported_temperature_c:.1f} to "
                    f"{temperature_policy.maximum_supported_temperature_c:.1f} °C correction range. "
                    "Non-strict execution clamps degradation correction to the nearest supported boundary."
                )
                limitation_code = "temperature_correction_clamped_to_governed_range"
            else:
                temp_message = (
                    f"Scenario temperature is {request.temperature_c} °C. Degradation half-lives will be "
                    f"corrected from the governed {temperature_policy.reference_temperature_c:.1f} °C "
                    "reference during execution using medium-specific Q10 factors."
                )
                limitation_code = "temperature_correction_governed"
            if self.strict_mode and limitation_code == "temperature_correction_clamped_to_governed_range":
                raise FateValidationError(
                    code=limitation_code,
                    message=temp_message,
                    suggestion=(
                        "Use a temperature inside the governed correction range or disable strict_mode "
                        "for boundary-clamped screening."
                    ),
                )
            limitations.append(
                LimitationNote(
                    code=limitation_code,
                    message=temp_message,
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
            temperature_c=request.temperature_c,
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

    def estimate_probabilistic(
        self,
        scenario: EnvironmentalReleaseScenario,
        run_options: FateModelRunOptions,
        iterations: int = 100,
        seed: int | None = None,
    ) -> ProbabilisticConcentrationResult:
        if scenario.geographic_scope.region_id != run_options.region_profile_id:
            raise FateValidationError(
                code="region_profile_mismatch",
                message="Run options region profile must match the scenario geographic scope.",
                suggestion="Align the scenario region and run options region_profile_id.",
            )
        if iterations < 1:
            raise FateValidationError(
                code="probabilistic_orchestration_invalid_iteration_count",
                message="Probabilistic orchestration requires at least one iteration.",
                suggestion="Set iterations to a positive integer.",
            )
        probabilistic_policy = self.defaults.probabilistic_review_policy()
        plugin = self.plugins.resolve(run_options.run_mode, run_options.model_family)
        
        rng = random.Random(seed) if seed is not None else random.Random()  # nosec B311
        
        # Identify parameters with distributions
        dist_params = [p for p in scenario.parameter_records if p.distribution is not None]
        
        if not dist_params:
            raise FateValidationError(
                code="probabilistic_orchestration_missing_distributions",
                message="No parameter distributions found in scenario.",
                suggestion="Provide ParameterDistribution entries for uncertain parameters.",
            )
            
        completed_iterations = 0
        failed_iterations = 0
        iteration_surfaces = {}  # (medium, compartment, bucket) -> list of surfaces
        expected_surface_keys: set[tuple[str, str, str | None]] | None = None
        
        aggregated_assumptions_by_parameter: dict[str, set[str]] = {}
        aggregated_warnings = set()
        failed_iteration_reasons = {}
        
        for _ in range(iterations):
            # Sample parameters
            sampled_records = []
            for p in scenario.parameter_records:
                if p.distribution:
                    val = self._sample_distribution_value(
                        parameter_name=p.parameter,
                        distribution=p.distribution,
                        rng=rng,
                    )
                    new_p = p.model_copy(update={"value": val})
                    sampled_records.append(new_p)
                else:
                    sampled_records.append(p)
                    
            scenario_copy = scenario.model_copy(update={"parameter_records": sampled_records})
            
            try:
                res = plugin.run(scenario_copy, run_options)
                completed_iterations += 1
                for a in res.assumptions:
                    aggregated_assumptions_by_parameter.setdefault(a.parameter, set()).add(
                        a.model_dump_json()
                    )
                for w in res.run_summary.warnings:
                    aggregated_warnings.add(w.model_dump_json())

                current_surface_keys = {
                    (s.medium.value, s.compartment.value, s.time_window.bucket_label)
                    for s in res.surfaces
                }
                if expected_surface_keys is None:
                    expected_surface_keys = current_surface_keys
                elif current_surface_keys != expected_surface_keys:
                    raise FateValidationError(
                        code="probabilistic_orchestration_inconsistent_surface_set",
                        message=(
                            "Probabilistic iterations produced inconsistent concentration surface identities "
                            "across successful runs."
                        ),
                        suggestion=(
                            "Use a stable scenario/run configuration so every probabilistic iteration emits "
                            "the same surface set."
                        ),
                        details={
                            "expectedSurfaceKeys": sorted(expected_surface_keys),
                            "observedSurfaceKeys": sorted(current_surface_keys),
                        },
                    )

                for s in res.surfaces:
                    key = (s.medium.value, s.compartment.value, s.time_window.bucket_label)
                    if key not in iteration_surfaces:
                        iteration_surfaces[key] = []
                    iteration_surfaces[key].append(s)
            except (FateValidationError, FateRegistryError) as exc:
                failed_iterations += 1
                reason = exc.payload.code if hasattr(exc, 'payload') else str(exc)
                failed_iteration_reasons[reason] = failed_iteration_reasons.get(reason, 0) + 1
                
        if completed_iterations == 0:
            raise FateValidationError(
                code="probabilistic_orchestration_failed",
                message="All iterations failed.",
                suggestion="Check parameter bounds and run options.",
            )
            
        # Aggregate
        percentiles_available = (
            completed_iterations
            >= probabilistic_policy.minimum_completed_iterations_for_percentiles
        )
        median_surfaces = []
        p90_surfaces = []
        p95_surfaces = []
        surface_summaries = []
        
        for key in sorted(iteration_surfaces):
            surfaces = iteration_surfaces[key]
            vals = [s.concentration_value for s in surfaces]
            vals.sort()
            
            med_val = statistics.median(vals)
            if percentiles_available and len(vals) >= 2:
                quantiles = statistics.quantiles(vals, n=100, method='inclusive')
                p90_val = quantiles[89]
                p95_val = quantiles[94]
            elif percentiles_available:
                p90_val = vals[0]
                p95_val = vals[0]
            else:
                p90_val = None
                p95_val = None
            
            base = surfaces[0]
            median_surfaces.append(
                self._build_aggregated_surface_copy(
                    base=base,
                    concentration_value=med_val,
                    percentile_label="median",
                )
            )
            if p90_val is not None:
                p90_surfaces.append(
                    self._build_aggregated_surface_copy(
                        base=base,
                        concentration_value=p90_val,
                        percentile_label="p90",
                    )
                )
            if p95_val is not None:
                p95_surfaces.append(
                    self._build_aggregated_surface_copy(
                        base=base,
                        concentration_value=p95_val,
                        percentile_label="p95",
                    )
                )
            
            surface_summaries.append(
                ProbabilisticSurfaceSummary(
                    surface_id=base.surface_id,
                    medium=base.medium,
                    compartment=base.compartment,
                    concentration_unit=base.concentration_unit,
                    median_value=med_val,
                    p90_value=p90_val,
                    p95_value=p95_val,
                    absolute_p95_minus_median=(
                        None if p95_val is None else p95_val - med_val
                    ),
                )
            )

        invariant_assumption_records = [
            FateAssumptionRecord.model_validate_json(next(iter(serialized_records)))
            for _, serialized_records in sorted(aggregated_assumptions_by_parameter.items())
            if len(serialized_records) == 1
        ]

        failed_iteration_fraction = failed_iterations / iterations if iterations else 0.0
        runtime_warnings = [
            QualityFlag.model_validate_json(w)
            for w in sorted(aggregated_warnings)
        ]
        uncertainty_limitation_lines = [
            "Probabilistic orchestration completed with governed distribution sampling and percentile aggregation.",
            "dominant_uncertainty_drivers enumerates sampled parameters only; formal sensitivity ranking is not yet implemented.",
            "run_summary.assumptions_applied preserves invariant assumptions only; iteration-varying sampled and derived assumptions are not expanded verbatim.",
        ]
        if failed_iterations > 0:
            runtime_warnings.append(
                QualityFlag(
                    code="probabilistic_iteration_failures_present",
                    severity=Severity.WARNING,
                    message=(
                        f"{failed_iterations} of {iterations} probabilistic iterations failed; "
                        "review packets must treat percentile outputs as truncated-to-successful-runs."
                    ),
                )
            )
            uncertainty_limitation_lines.append(
                f"{failed_iterations} of {iterations} iterations failed; completed iterations only were used for any percentile aggregation."
            )
        if not percentiles_available:
            runtime_warnings.append(
                QualityFlag(
                    code="probabilistic_percentiles_suppressed",
                    severity=Severity.WARNING,
                    message=(
                        f"P90/P95 were suppressed because only {completed_iterations} completed iterations "
                        f"were available, below the governed minimum of "
                        f"{probabilistic_policy.minimum_completed_iterations_for_percentiles}."
                    ),
                )
            )
            uncertainty_limitation_lines.append(
                f"P90/P95 were suppressed because completed iterations ({completed_iterations}) remained below the governed minimum ({probabilistic_policy.minimum_completed_iterations_for_percentiles})."
            )
        if (
            failed_iteration_fraction
            > probabilistic_policy.max_failed_iteration_fraction_for_ready_review
        ):
            runtime_warnings.append(
                QualityFlag(
                    code="probabilistic_failed_iteration_fraction_exceeds_ready_threshold",
                    severity=Severity.WARNING,
                    message=(
                        f"Failed iteration fraction {failed_iteration_fraction:.1%} exceeds the governed "
                        f"ready-review threshold of "
                        f"{probabilistic_policy.max_failed_iteration_fraction_for_ready_review:.0%}."
                    ),
                )
            )
            uncertainty_limitation_lines.append(
                f"Failed iteration fraction {failed_iteration_fraction:.1%} exceeds the governed ready-review threshold of {probabilistic_policy.max_failed_iteration_fraction_for_ready_review:.0%}."
            )

        return ProbabilisticConcentrationResult(
            median_surfaces=median_surfaces,
            p90_surfaces=p90_surfaces,
            p95_surfaces=p95_surfaces,
            surface_summaries=surface_summaries,
            iteration_count=iterations,
            completed_iteration_count=completed_iterations,
            failed_iteration_count=failed_iterations,
            sampling_seed=seed,
            sampled_parameter_count=len(dist_params),
            dominant_uncertainty_drivers=sorted(p.parameter for p in dist_params),
            uncertainty_limitation_lines=uncertainty_limitation_lines,
            run_summary=ProbabilisticRunSummary(
                scenario_id=scenario.scenario_id,
                model_family=run_options.model_family,
                run_mode=run_options.run_mode,
                surfaces_emitted=len(surface_summaries),
                assumptions_applied=invariant_assumption_records,
                escalation_concerns=run_options.escalation_concerns,
                warnings=runtime_warnings,
                failed_iteration_reasons=dict(sorted(failed_iteration_reasons.items())),
                result_metadata=ResultMetadata.completed(result_id=f"result-{scenario.scenario_id}-prob"),
            )
        )

    def _build_aggregated_surface_copy(
        self,
        *,
        base,
        concentration_value: float,
        percentile_label: str,
    ):
        limitations = list(base.limitations)
        limitations.append(
            LimitationNote(
                code="probabilistic_surface_aggregation",
                message=(
                    f"{percentile_label} probabilistic surface is an aggregated percentile summary; "
                    "iteration-specific closed-form calculation_trace terms are intentionally omitted."
                ),
            )
        )
        return base.model_copy(
            update={
                "surface_id": f"{base.surface_id}-{percentile_label}",
                "concentration_value": concentration_value,
                "calculation_trace": None,
                "limitations": limitations,
            }
        )

    def _sample_distribution_value(
        self,
        parameter_name: str,
        distribution,
        rng: random.Random,
    ) -> float:
        lower_bound: float | None = None
        upper_bound: float | None = None
        if distribution.bounds is not None:
            lower_bound, upper_bound = distribution.bounds

        for _ in range(MAX_DISTRIBUTION_SAMPLE_ATTEMPTS):
            if distribution.distribution_type == "lognormal":
                sampled_value = rng.lognormvariate(
                    distribution.parameters["mu"],
                    distribution.parameters["sigma"],
                )
            elif distribution.distribution_type == "normal":
                sampled_value = rng.gauss(
                    distribution.parameters["mu"],
                    distribution.parameters["sigma"],
                )
            elif distribution.distribution_type == "uniform":
                sampled_value = rng.uniform(
                    distribution.parameters["low"],
                    distribution.parameters["high"],
                )
            else:
                raise FateValidationError(
                    code="unsupported_parameter_distribution_type",
                    message=(
                        f"Parameter {parameter_name} requested unsupported distribution type "
                        f"{distribution.distribution_type}."
                    ),
                    suggestion="Use a supported distribution type declared in the governed probabilistic tier.",
                )

            if lower_bound is not None and sampled_value < lower_bound:
                continue
            if upper_bound is not None and sampled_value > upper_bound:
                continue
            return sampled_value

        raise FateValidationError(
            code="parameter_distribution_sampling_out_of_bounds",
            message=(
                f"Parameter {parameter_name} could not be sampled within declared bounds after "
                f"{MAX_DISTRIBUTION_SAMPLE_ATTEMPTS} attempts."
            ),
            suggestion="Relax the distribution bounds or reconcile them with the declared distribution parameters.",
        )

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
                status="agreed" if relative_spread <= self.defaults.reconciliation_threshold("mass_relative_spread") else "conflict",
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
        if relative_spread <= self.defaults.reconciliation_threshold("mass_relative_spread"):
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
                if cosine_similarity < self.defaults.reconciliation_threshold("vector_cosine_similarity"):
                    vector_conflicts.append(
                        ReleaseVectorConflict(
                            labels=[left.label, right.label],
                            cosine_similarity=cosine_similarity,
                            threshold=self.defaults.reconciliation_threshold("vector_cosine_similarity"),
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
            status = "agreed" if absolute_spread <= self.defaults.reconciliation_threshold("fraction_absolute_spread") else "conflict"
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
