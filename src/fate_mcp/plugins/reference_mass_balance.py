from __future__ import annotations

import math
from datetime import timedelta

from fate_mcp.defaults import DefaultsRegistry
from fate_mcp.errors import FateValidationError
from fate_mcp.models import (
    CalculationTrace,
    CalculationTraceTerm,
    ConcentrationEstimationResult,
    ConcentrationSurface,
    EnvironmentalReleaseScenario,
    FateParameterRecord,
    FateModelRunOptions,
    FateRunSummary,
    LimitationNote,
    Media,
    ModelFamily,
    QualityFlag,
    RunMode,
    Severity,
    TreatmentExecutionMode,
    TimeWindow,
)
from fate_mcp.plugins.base import PluginKey
from fate_mcp.provenance import ProvenanceBuilder
from fate_mcp.result_meta import ResultMetadata


class ReferenceMassBalancePlugin:
    key = PluginKey(
        run_mode=RunMode.STEADY_STATE,
        model_family=ModelFamily.REFERENCE_MASS_BALANCE,
    )
    limitations = [
        "Reference plugin is deterministic and screening-oriented.",
        "Reference plugin does not model spatial gradients or explicit intermedia transfer coefficients.",
    ]

    def __init__(self, defaults_registry: DefaultsRegistry, provenance_builder: ProvenanceBuilder) -> None:
        self.defaults_registry = defaults_registry
        self.provenance_builder = provenance_builder

    @staticmethod
    def _safe_decay_constant(half_life_days: float) -> tuple[float, list[str]]:
        notes: list[str] = []
        if half_life_days <= 0.0:
            raise FateValidationError(
                code="non_positive_half_life",
                message=(
                    f"Half-life must be positive; received {half_life_days} day. "
                    "Screening cannot proceed with a non-physical degradation rate."
                ),
                suggestion="Provide a positive half-life value or remove the override to use the governed default.",
                details={"provided_half_life_days": half_life_days},
            )
        return math.log(2.0) / half_life_days, notes

    def _temperature_adjusted_half_life(
        self,
        medium: Media,
        half_life_days: float,
        scenario_temperature_c: float,
    ) -> tuple[float, float, float, list[str], LimitationNote | None]:
        policy = self.defaults_registry.temperature_correction_policy()
        reference_temperature_c = policy.reference_temperature_c
        effective_temperature_c = policy.clamp_temperature(scenario_temperature_c)
        if abs(scenario_temperature_c - reference_temperature_c) <= 1e-12:
            return half_life_days, 1.0, effective_temperature_c, [], None

        correction_factor = policy.degradation_q10_by_medium[medium] ** (
            (effective_temperature_c - reference_temperature_c) / 10.0
        )
        corrected_half_life_days = half_life_days / correction_factor

        if abs(effective_temperature_c - scenario_temperature_c) > 1e-12:
            message = (
                f"Scenario temperature {scenario_temperature_c:.1f} °C was clamped to "
                f"{effective_temperature_c:.1f} °C before applying the governed "
                f"{medium.value} degradation Q10 correction."
            )
            code = "temperature_correction_clamped_to_governed_range"
        else:
            message = (
                f"Scenario temperature {scenario_temperature_c:.1f} °C was applied to the "
                f"governed {medium.value} degradation Q10 correction from the "
                f"{reference_temperature_c:.1f} °C reference."
            )
            code = "temperature_correction_governed"

        return (
            corrected_half_life_days,
            correction_factor,
            effective_temperature_c,
            [message],
            LimitationNote(code=code, message=message),
        )

    @staticmethod
    def _validated_capacity_value(
        capacity_value: float,
        *,
        parameter_name: str,
        medium: Media,
    ) -> float:
        if not math.isfinite(capacity_value) or capacity_value <= 0.0:
            raise FateValidationError(
                code="non_positive_effective_capacity",
                message=(
                    f"Effective capacity for {medium.value} from parameter {parameter_name} must be "
                    f"finite and positive; received {capacity_value}."
                ),
                suggestion=(
                    "Provide a finite positive capacity override or correct the governed defaults/region "
                    "scalar before execution."
                ),
                details={
                    "medium": medium.value,
                    "parameter": parameter_name,
                    "effectiveCapacity": capacity_value,
                },
            )
        return capacity_value

    @staticmethod
    def _cumulative_mass_time_integral(
        release_rate_mg_per_day: float,
        loss_constant_per_day: float,
        emission_duration_days: float,
        elapsed_days: float,
    ) -> float:
        if elapsed_days <= 0.0:
            return 0.0
        active_emission_duration_days = min(elapsed_days, emission_duration_days)
        if loss_constant_per_day <= 1e-12:
            during_emission_integral = (
                0.5 * release_rate_mg_per_day * active_emission_duration_days**2
            )
            if elapsed_days <= emission_duration_days:
                return during_emission_integral
            release_stop_mass_mg = release_rate_mg_per_day * emission_duration_days
            return during_emission_integral + (
                release_stop_mass_mg * (elapsed_days - emission_duration_days)
            )

        during_emission_integral = (
            release_rate_mg_per_day
            / loss_constant_per_day
            * (
                active_emission_duration_days
                - (
                    1.0
                    - math.exp(-loss_constant_per_day * active_emission_duration_days)
                )
                / loss_constant_per_day
            )
        )
        if elapsed_days <= emission_duration_days:
            return during_emission_integral

        release_stop_mass_mg = (
            release_rate_mg_per_day
            / loss_constant_per_day
            * (1.0 - math.exp(-loss_constant_per_day * emission_duration_days))
        )
        post_release_integral = (
            release_stop_mass_mg
            * (1.0 - math.exp(-loss_constant_per_day * (elapsed_days - emission_duration_days)))
            / loss_constant_per_day
        )
        return during_emission_integral + post_release_integral

    @classmethod
    def _cumulative_first_order_loss(
        cls,
        release_rate_mg_per_day: float,
        total_loss_constant_per_day: float,
        component_loss_constant_per_day: float,
        emission_duration_days: float,
        elapsed_days: float,
    ) -> float:
        return component_loss_constant_per_day * cls._cumulative_mass_time_integral(
            release_rate_mg_per_day=release_rate_mg_per_day,
            loss_constant_per_day=total_loss_constant_per_day,
            emission_duration_days=emission_duration_days,
            elapsed_days=elapsed_days,
        )

    @staticmethod
    def _concentration_at_time(
        release_rate_mg_per_day: float,
        capacity_value: float,
        decay_constant_per_day: float,
        emission_duration_days: float,
        elapsed_days: float,
    ) -> tuple[float, float]:
        if elapsed_days <= 0.0:
            return 0.0, 0.0
        active_emission_duration_days = min(elapsed_days, emission_duration_days)
        if decay_constant_per_day <= 1e-12:
            concentration = (release_rate_mg_per_day * active_emission_duration_days) / capacity_value
        else:
            concentration = (
                release_rate_mg_per_day
                / (capacity_value * decay_constant_per_day)
                * (1.0 - math.exp(-decay_constant_per_day * active_emission_duration_days))
            )
            if elapsed_days > emission_duration_days:
                concentration *= math.exp(
                    -decay_constant_per_day * (elapsed_days - emission_duration_days)
                )
        return concentration, active_emission_duration_days

    def _treatment_adjustment(
        self,
        scenario: EnvironmentalReleaseScenario,
    ) -> tuple[float, list, list[QualityFlag], list[LimitationNote]]:
        executed_assumptions = [
            item
            for item in scenario.treatment_assumptions
            if item.execution_mode == TreatmentExecutionMode.PRE_RELEASE_GLOBAL
        ]
        provenance_only_assumptions = [
            item
            for item in scenario.treatment_assumptions
            if item.execution_mode != TreatmentExecutionMode.PRE_RELEASE_GLOBAL
        ]
        assumptions = []
        warnings: list[QualityFlag] = []
        limitations: list[LimitationNote] = []
        total_removal_fraction = sum(item.removal_fraction for item in executed_assumptions)
        if total_removal_fraction > 1.0 + 1e-12:
            raise FateValidationError(
                code="treatment_removal_fraction_exceeds_unity",
                message="Executable pre-release global treatment assumptions sum to more than 1.0.",
                suggestion="Reduce treatment removal fractions or model treatment steps separately before execution.",
                details={"totalRemovalFraction": total_removal_fraction},
            )
        if executed_assumptions:
            assumptions.append(
                self.provenance_builder.derived(
                    "global_treatment_removal_fraction",
                    round(total_removal_fraction, 12),
                    "fraction",
                    "Executable pre-release global treatment removal applied before release-to-concentration estimation.",
                )
            )
            limitations.append(
                LimitationNote(
                    code="pre_release_global_treatment_applied",
                    message=(
                        "Only treatment assumptions explicitly marked as pre_release_global were numerically "
                        "applied before the screening calculation."
                    ),
                )
            )
            if len(executed_assumptions) > 1:
                limitations.append(
                    LimitationNote(
                        code="pre_release_global_treatment_additive_semantics",
                        message=(
                            "Multiple pre_release_global treatment assumptions are combined additively as one "
                            "global removal fraction, not sequentially as staged treatment steps."
                        ),
                    )
                )
        if provenance_only_assumptions:
            warnings.append(
                QualityFlag(
                    code="unexecuted_treatment_assumption",
                    severity=Severity.WARNING,
                    message=(
                        "One or more treatment assumptions remain provenance-only because they are not "
                        "declared as executable pre-release global removal."
                    ),
                )
            )
            limitations.append(
                LimitationNote(
                    code="unexecuted_treatment_assumptions",
                    message=(
                        "Treatment assumptions without execution_mode=pre_release_global remain provenance-only "
                        "and were not used to reduce release mass."
                    ),
                )
            )
        return max(0.0, 1.0 - total_removal_fraction), assumptions, warnings, limitations

    def _parameter_override(
        self,
        scenario: EnvironmentalReleaseScenario,
        parameter: str,
        expected_unit: str,
    ) -> FateParameterRecord | None:
        for record in scenario.parameter_records:
            if record.parameter != parameter:
                continue
            if record.unit != expected_unit:
                raise FateValidationError(
                    code="parameter_override_unit_mismatch",
                    message=f"Scenario parameter {parameter} uses unit {record.unit}, expected {expected_unit}.",
                    suggestion="Normalize the parameter record to the canonical Environmental Fate MCP unit before execution.",
                    details={"parameter": parameter, "expectedUnit": expected_unit, "providedUnit": record.unit},
                )
            return record
        return None

    def _build_surface(
        self,
        scenario: EnvironmentalReleaseScenario,
        run_options: FateModelRunOptions,
        medium: Media,
        fraction: float,
        effective_total_release_mass_kg: float,
        treatment_limitations: list[LimitationNote],
        bucket_index: int | None = None,
    ) -> tuple[ConcentrationSurface, list]:
        media_defaults = self.defaults_registry.media_defaults(medium)
        region_scalar = self.defaults_registry.region_scalar(
            run_options.region_profile_id,
            media_defaults.compartment,
        )
        capacity_override = self._parameter_override(
            scenario,
            media_defaults.capacity_parameter,
            "m3" if media_defaults.capacity_parameter.endswith("_volume_m3") else "kg",
        )
        half_life_override = self._parameter_override(
            scenario,
            media_defaults.degradation_half_life_parameter,
            "day",
        )
        capacity_value = (
            capacity_override.value
            if capacity_override
            else self.defaults_registry.parameter_value(media_defaults.capacity_parameter)
        ) * region_scalar
        capacity_value = self._validated_capacity_value(
            capacity_value,
            parameter_name=media_defaults.capacity_parameter,
            medium=medium,
        )
        half_life_days = (
            half_life_override.value
            if half_life_override
            else self.defaults_registry.parameter_value(media_defaults.degradation_half_life_parameter)
        )
        temperature_corrected_half_life_days, temperature_correction_factor, effective_temperature_c, temperature_notes, temperature_limitation = self._temperature_adjusted_half_life(
            medium,
            half_life_days,
            scenario.temperature_c,
        )
        release_mass_mg = effective_total_release_mass_kg * 1_000_000.0 * fraction
        release_rate_mg_per_day = release_mass_mg / scenario.duration_days
        decay_constant_per_day, decay_notes = self._safe_decay_constant(temperature_corrected_half_life_days)
        effective_half_life_days: float | str
        loss_characteristic_time_days: float | str
        if decay_constant_per_day <= 1e-12:
            effective_half_life_days = "infinite"
            loss_characteristic_time_days = "infinite"
        else:
            effective_half_life_days = math.log(2.0) / decay_constant_per_day
            loss_characteristic_time_days = 1.0 / decay_constant_per_day
        if run_options.run_mode == RunMode.STEADY_STATE:
            elapsed_days = scenario.duration_days
        else:
            safe_bucket_index = bucket_index or 0
            elapsed_days = run_options.bucket_duration_days * (safe_bucket_index + 1)
        raw_concentration, active_emission_duration_days = self._concentration_at_time(
            release_rate_mg_per_day=release_rate_mg_per_day,
            capacity_value=capacity_value,
            decay_constant_per_day=decay_constant_per_day,
            emission_duration_days=scenario.duration_days,
            elapsed_days=elapsed_days,
        )
        emitted_mass_to_elapsed_mg = release_rate_mg_per_day * active_emission_duration_days
        compartment_mass_at_elapsed_mg = raw_concentration * capacity_value
        cumulative_degraded_mass_mg = self._cumulative_first_order_loss(
            release_rate_mg_per_day=release_rate_mg_per_day,
            total_loss_constant_per_day=decay_constant_per_day,
            component_loss_constant_per_day=decay_constant_per_day,
            emission_duration_days=scenario.duration_days,
            elapsed_days=elapsed_days,
        )
        cumulative_advected_mass_mg = 0.0
        mass_balance_closure_error_mg = (
            emitted_mass_to_elapsed_mg
            - compartment_mass_at_elapsed_mg
            - cumulative_degraded_mass_mg
        )
        post_release_elapsed_days = max(elapsed_days - scenario.duration_days, 0.0)
        if post_release_elapsed_days > 0.0:
            release_stop_concentration, _ = self._concentration_at_time(
                release_rate_mg_per_day=release_rate_mg_per_day,
                capacity_value=capacity_value,
                decay_constant_per_day=decay_constant_per_day,
                emission_duration_days=scenario.duration_days,
                elapsed_days=scenario.duration_days,
            )
            release_stop_compartment_mass_mg = release_stop_concentration * capacity_value
            if release_stop_compartment_mass_mg <= 1e-12:
                post_release_retained_fraction_of_release_stop_mass = 0.0
                post_release_removed_fraction_of_release_stop_mass = 0.0
                post_release_degraded_fraction_of_release_stop_mass = 0.0
                post_release_advected_fraction_of_release_stop_mass = 0.0
            else:
                post_release_retained_fraction_of_release_stop_mass = min(
                    max(
                        compartment_mass_at_elapsed_mg / release_stop_compartment_mass_mg,
                        0.0,
                    ),
                    1.0,
                )
                post_release_removed_fraction_of_release_stop_mass = min(
                    max(
                        1.0 - post_release_retained_fraction_of_release_stop_mass,
                        0.0,
                    ),
                    1.0,
                )
                post_release_degraded_fraction_of_release_stop_mass = (
                    post_release_removed_fraction_of_release_stop_mass
                )
                post_release_advected_fraction_of_release_stop_mass = 0.0
        else:
            release_stop_compartment_mass_mg = "not_applicable"
            post_release_retained_fraction_of_release_stop_mass = "not_applicable"
            post_release_removed_fraction_of_release_stop_mass = "not_applicable"
            post_release_degraded_fraction_of_release_stop_mass = "not_applicable"
            post_release_advected_fraction_of_release_stop_mass = "not_applicable"
        concentration_value = raw_concentration / 1000.0 if medium == Media.WATER else raw_concentration

        assumptions = [
            (
                self.provenance_builder.from_parameter_record(
                    capacity_override,
                    f"User- or evidence-supplied capacity override used for {medium.value} concentration calculation.",
                )
                if capacity_override
                else self.provenance_builder.curated_default(
                    media_defaults.capacity_parameter,
                    f"Capacity used for {medium.value} concentration calculation.",
                )
            ),
            (
                self.provenance_builder.from_parameter_record(
                    half_life_override,
                    f"User- or evidence-supplied half-life override used to attenuate {medium.value} release over the declared scenario duration.",
                )
                if half_life_override
                else self.provenance_builder.curated_default(
                    media_defaults.degradation_half_life_parameter,
                    f"Half-life used to attenuate {medium.value} release over the declared scenario duration.",
                )
            ),
            self.provenance_builder.derived(
                f"{medium.value}_region_scalar",
                region_scalar,
                "scalar",
                "Region profile scalar applied to the default compartment capacity.",
            ),
            self.provenance_builder.derived(
                f"{medium.value}_effective_release_mass_kg",
                effective_total_release_mass_kg * fraction,
                "kg",
                "Medium-specific effective release mass after executable pre-release treatment removal.",
            ),
            self.provenance_builder.derived(
                f"{medium.value}_decay_constant_per_day",
                decay_constant_per_day,
                "1/day",
                "First-order decay constant used in the finite-duration screening calculation.",
            ),
        ]
        if abs(scenario.temperature_c - effective_temperature_c) > 1e-12 or abs(
            temperature_correction_factor - 1.0
        ) > 1e-12:
            assumptions.extend(
                [
                    self.provenance_builder.user_input(
                        f"{medium.value}_scenario_temperature_c",
                        scenario.temperature_c,
                        "degC",
                        "Scenario temperature supplied for governed degradation correction.",
                    ),
                    self.provenance_builder.derived(
                        f"{medium.value}_effective_temperature_c",
                        effective_temperature_c,
                        "degC",
                        "Effective temperature used after applying the governed correction range.",
                    ),
                    self.provenance_builder.derived(
                        f"{medium.value}_temperature_correction_factor",
                        temperature_correction_factor,
                        "scalar",
                        "Medium-specific governed Q10 factor applied to the declared degradation half-life.",
                    ),
                    self.provenance_builder.derived(
                        f"{medium.value}_temperature_corrected_half_life_days",
                        temperature_corrected_half_life_days,
                        "day",
                        "Declared half-life after governed temperature correction.",
                    ),
                ]
            )

        if run_options.run_mode == RunMode.STEADY_STATE:
            time_window = TimeWindow(mode=RunMode.STEADY_STATE)
        else:
            safe_bucket_index = bucket_index or 0
            delta_days = run_options.bucket_duration_days * safe_bucket_index
            bucket_start = scenario.provenance.generated_at + timedelta(days=delta_days)
            bucket_end = bucket_start + timedelta(days=run_options.bucket_duration_days)
            time_window = TimeWindow(
                mode=RunMode.TIME_BUCKET,
                start=bucket_start,
                end=bucket_end,
                bucket_label=f"bucket_{safe_bucket_index + 1}",
            )

        if decay_constant_per_day <= 1e-12:
            equation_id = "finite_duration_release_no_decay_limit"
            equation_text = "C(t) = (R * min(t, T)) / V"
        elif elapsed_days <= scenario.duration_days:
            equation_id = "finite_duration_continuous_release_first_order"
            equation_text = "C(t) = (R / (k * V)) * (1 - exp(-k * t))"
        else:
            equation_id = "post_release_first_order_decay"
            equation_text = "C(t) = (R / (k * V)) * (1 - exp(-k * T)) * exp(-k * (t - T))"
        calculation_trace = CalculationTrace(
            equation_id=equation_id,
            equation_text=equation_text,
            resolved_terms=[
                CalculationTraceTerm(name="release_rate_mg_per_day", value=release_rate_mg_per_day, unit="mg/day"),
                CalculationTraceTerm(
                    name="capacity_value",
                    value=capacity_value,
                    unit="m3" if media_defaults.capacity_parameter.endswith("_volume_m3") else "kg",
                ),
                CalculationTraceTerm(
                    name="declared_temperature_c",
                    value=scenario.temperature_c,
                    unit="degC",
                ),
                CalculationTraceTerm(
                    name="effective_temperature_c",
                    value=effective_temperature_c,
                    unit="degC",
                ),
                CalculationTraceTerm(
                    name="temperature_correction_factor",
                    value=temperature_correction_factor,
                    unit="scalar",
                ),
                CalculationTraceTerm(
                    name="temperature_corrected_half_life_days",
                    value=temperature_corrected_half_life_days,
                    unit="day",
                ),
                CalculationTraceTerm(name="declared_half_life_days", value=half_life_days, unit="day"),
                CalculationTraceTerm(
                    name="effective_half_life_days",
                    value=effective_half_life_days,
                    unit="day",
                ),
                CalculationTraceTerm(name="decay_constant_per_day", value=decay_constant_per_day, unit="1/day"),
                CalculationTraceTerm(
                    name="loss_characteristic_time_days",
                    value=loss_characteristic_time_days,
                    unit="day",
                ),
                CalculationTraceTerm(name="elapsed_days", value=elapsed_days, unit="day"),
                CalculationTraceTerm(name="emission_duration_days", value=scenario.duration_days, unit="day"),
                CalculationTraceTerm(name="active_emission_duration_days", value=active_emission_duration_days, unit="day"),
                CalculationTraceTerm(
                    name="post_release_elapsed_days",
                    value=post_release_elapsed_days,
                    unit="day",
                ),
                CalculationTraceTerm(
                    name="emitted_mass_to_elapsed_mg",
                    value=emitted_mass_to_elapsed_mg,
                    unit="mg",
                ),
                CalculationTraceTerm(
                    name="compartment_mass_at_elapsed_mg",
                    value=compartment_mass_at_elapsed_mg,
                    unit="mg",
                ),
                CalculationTraceTerm(
                    name="cumulative_degraded_mass_mg",
                    value=cumulative_degraded_mass_mg,
                    unit="mg",
                ),
                CalculationTraceTerm(
                    name="cumulative_advected_mass_mg",
                    value=cumulative_advected_mass_mg,
                    unit="mg",
                ),
                CalculationTraceTerm(
                    name="mass_balance_closure_error_mg",
                    value=mass_balance_closure_error_mg,
                    unit="mg",
                ),
                CalculationTraceTerm(
                    name="release_stop_compartment_mass_mg",
                    value=release_stop_compartment_mass_mg,
                    unit="mg",
                ),
                CalculationTraceTerm(
                    name="post_release_retained_fraction_of_release_stop_mass",
                    value=post_release_retained_fraction_of_release_stop_mass,
                    unit="fraction",
                ),
                CalculationTraceTerm(
                    name="post_release_removed_fraction_of_release_stop_mass",
                    value=post_release_removed_fraction_of_release_stop_mass,
                    unit="fraction",
                ),
                CalculationTraceTerm(
                    name="post_release_degraded_fraction_of_release_stop_mass",
                    value=post_release_degraded_fraction_of_release_stop_mass,
                    unit="fraction",
                ),
                CalculationTraceTerm(
                    name="post_release_advected_fraction_of_release_stop_mass",
                    value=post_release_advected_fraction_of_release_stop_mass,
                    unit="fraction",
                ),
                CalculationTraceTerm(name="medium_release_fraction", value=fraction, unit="fraction"),
                CalculationTraceTerm(name="effective_total_release_mass_kg", value=effective_total_release_mass_kg, unit="kg"),
                CalculationTraceTerm(name="region_scalar", value=region_scalar, unit="scalar"),
            ],
            notes=[
                "steady_state outputs represent end-of-duration screening concentration, not an infinite-time equilibrium.",
                *temperature_notes,
                *decay_notes,
                (
                    "Water concentrations are converted from mg/m3 to mg/L by dividing the resolved screening "
                    "concentration by 1000."
                    if medium == Media.WATER
                    else "Air, soil, and sediment concentrations remain in the compartment-native screening unit."
                ),
            ],
        )

        surface = ConcentrationSurface(
            limitations=(
                [LimitationNote(code="screening_model", message=text) for text in self.limitations]
                + [
                    LimitationNote(
                        code="finite_duration_screening_kernel",
                        message=(
                            "Reference_mass_balance uses deterministic finite-duration first-order screening "
                            "math within a single compartment per medium."
                        ),
                    ),
                ]
                + ([temperature_limitation] if temperature_limitation is not None else [])
                + treatment_limitations
            ),
            scenario_id=scenario.scenario_id,
            medium=medium,
            compartment=media_defaults.compartment,
            geographic_scope=scenario.geographic_scope,
            time_window=time_window,
            concentration_value=concentration_value,
            concentration_unit=media_defaults.unit,
            model_family=ModelFamily.REFERENCE_MASS_BALANCE,
            fit_for_purpose=run_options.fit_for_purpose,
            provenance=self.provenance_builder.bundle(scenario.evidence_sources),
            calculation_trace=calculation_trace,
            quality_flags=[
                flag
                for record in (capacity_override, half_life_override)
                if record is not None
                for flag in record.quality_flags
            ],
        )
        return surface, assumptions

    def run(
        self,
        scenario: EnvironmentalReleaseScenario,
        run_options: FateModelRunOptions,
    ) -> ConcentrationEstimationResult:
        surfaces: list[ConcentrationSurface] = []
        assumptions = []
        release_scalar, treatment_assumptions, warnings, treatment_limitations = self._treatment_adjustment(
            scenario
        )
        assumptions.extend(treatment_assumptions)
        effective_total_release_mass_kg = scenario.total_release_mass_kg * release_scalar
        if scenario.treatment_assumptions:
            assumptions.append(
                self.provenance_builder.derived(
                    "effective_total_release_mass_kg",
                    effective_total_release_mass_kg,
                    "kg",
                    "Scenario total release mass after applying executable pre-release global treatment removal.",
                )
            )
        for release_fraction in scenario.release_fractions:
            if run_options.requested_media and release_fraction.medium not in run_options.requested_media:
                continue
            if run_options.run_mode == RunMode.STEADY_STATE:
                surface, applied = self._build_surface(
                    scenario=scenario,
                    run_options=run_options,
                    medium=release_fraction.medium,
                    fraction=release_fraction.fraction,
                    effective_total_release_mass_kg=effective_total_release_mass_kg,
                    treatment_limitations=treatment_limitations,
                )
                surfaces.append(surface)
                assumptions.extend(applied)
            else:
                for bucket_index in range(run_options.bucket_count):
                    surface, applied = self._build_surface(
                        scenario=scenario,
                        run_options=run_options,
                        medium=release_fraction.medium,
                        fraction=release_fraction.fraction,
                        effective_total_release_mass_kg=effective_total_release_mass_kg,
                        treatment_limitations=treatment_limitations,
                        bucket_index=bucket_index,
                    )
                    surfaces.append(surface)
                    assumptions.extend(applied)

        run_summary = FateRunSummary(
            scenario_id=scenario.scenario_id,
            model_family=run_options.model_family,
            run_mode=run_options.run_mode,
            surfaces_emitted=len(surfaces),
            assumptions_applied=assumptions,
            escalation_concerns=run_options.escalation_concerns,
            warnings=warnings,
            result_metadata=ResultMetadata.completed(result_id=f"result-{scenario.scenario_id}"),
        )
        return ConcentrationEstimationResult(
            surfaces=surfaces,
            run_summary=run_summary,
            assumptions=assumptions,
        )
