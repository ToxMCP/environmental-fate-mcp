from __future__ import annotations

import math

from fate_mcp.defaults import DefaultsRegistry
from fate_mcp.errors import FateValidationError
from fate_mcp.models import (
    CalculationTrace,
    CalculationTraceTerm,
    ConcentrationEstimationResult,
    ConcentrationSurface,
    EnvironmentalReleaseScenario,
    FateAssumptionRecord,
    FateModelRunOptions,
    FateParameterRecord,
    FateRunSummary,
    FugacityScreeningLevel,
    LimitationNote,
    Media,
    ModelFamily,
    QualityFlag,
    ReportedTimeSemantics,
    RunMode,
    Severity,
    TimeWindow,
    TreatmentExecutionMode,
)
from fate_mcp.plugins.base import PluginKey
from fate_mcp.provenance import ProvenanceBuilder
from fate_mcp.result_meta import ResultMetadata


ACTIVE_MEDIA = (Media.AIR, Media.WATER, Media.SOIL, Media.SEDIMENT)
GAS_CONSTANT_PA_M3_MOL_K = 8.31446261815324
KELVIN_OFFSET = 273.15

MOLECULAR_WEIGHT_PARAMETER = "molecular_weight_g_mol"
HENRY_PARAMETER = "henry_law_constant_pa_m3_mol"
KOC_PARAMETER = "organic_carbon_partition_coefficient_koc_l_kg"

OUTPUT_UNITS = {
    Media.AIR: "mg/m3",
    Media.WATER: "mg/m3",
    Media.SOIL: "mg/kg",
    Media.SEDIMENT: "mg/kg",
}


class FugacityEquilibriumScreeningPlugin:
    key = PluginKey(
        run_mode=RunMode.STEADY_STATE,
        model_family=ModelFamily.FUGACITY_EQUILIBRIUM_SCREENING,
    )
    limitations = [
        "Fugacity equilibrium screening is experimental and non-default.",
        "Level I assumes equilibrium partitioning among active media with no loss processes.",
        "Level II assumes equilibrium partitioning with first-order degradation losses only.",
        "This family does not implement Level III non-equilibrium intermedia transfer.",
        "This family does not model GIS routing, hydrology, calibration, WEPP, SWAT, PRZM, exposure, risk, or regulator acceptance.",
    ]

    def __init__(self, defaults_registry: DefaultsRegistry, provenance_builder: ProvenanceBuilder) -> None:
        self.defaults_registry = defaults_registry
        self.provenance_builder = provenance_builder

    @staticmethod
    def _ensure_positive(value: float, *, parameter: str) -> float:
        if not math.isfinite(value) or value <= 0.0:
            raise FateValidationError(
                code="fugacity_screening_non_positive_parameter",
                message=f"Fugacity screening parameter {parameter} must be finite and positive; received {value}.",
                suggestion="Provide a finite positive parameter record before running fugacity screening.",
                details={"parameter": parameter, "value": value},
            )
        return value

    @staticmethod
    def _scenario_record(
        scenario: EnvironmentalReleaseScenario,
        parameter: str,
        expected_unit: str,
        *,
        required: bool,
    ) -> FateParameterRecord | None:
        for record in scenario.parameter_records:
            if record.parameter != parameter:
                continue
            if record.unit != expected_unit:
                raise FateValidationError(
                    code="fugacity_screening_parameter_unit_mismatch",
                    message=(
                        f"Fugacity screening parameter {parameter} uses unit {record.unit}, "
                        f"expected {expected_unit}."
                    ),
                    suggestion="Normalize the parameter record to the canonical Environmental Fate MCP unit.",
                    details={
                        "parameter": parameter,
                        "expectedUnit": expected_unit,
                        "providedUnit": record.unit,
                    },
                )
            return record
        if required:
            raise FateValidationError(
                code="missing_fugacity_screening_parameter",
                message=f"Fugacity screening requires scenario parameter {parameter}.",
                suggestion=(
                    "Add explicit FateParameterRecord entries for molecular weight, Henry law constant, "
                    "and Koc before selecting fugacity_equilibrium_screening."
                ),
                details={"parameter": parameter, "expectedUnit": expected_unit},
            )
        return None

    def _scenario_or_default_parameter(
        self,
        scenario: EnvironmentalReleaseScenario,
        parameter: str,
        expected_unit: str,
    ) -> tuple[float, FateParameterRecord | None, FateAssumptionRecord]:
        record = self._scenario_record(
            scenario,
            parameter,
            expected_unit,
            required=False,
        )
        if record is not None:
            self._ensure_positive(record.value, parameter=parameter)
            return (
                record.value,
                record,
                self.provenance_builder.from_parameter_record(
                    record,
                    f"Scenario parameter {parameter} used by fugacity equilibrium screening.",
                ),
            )
        default_value = self._ensure_positive(
            float(self.defaults_registry.parameter_record(parameter)["value"]),
            parameter=parameter,
        )
        return (
            default_value,
            None,
            self.provenance_builder.curated_default(
                parameter,
                f"Governed default {parameter} used by fugacity equilibrium screening.",
            ),
        )

    def _required_physchem_parameters(
        self,
        scenario: EnvironmentalReleaseScenario,
    ) -> tuple[float, float, float, list[FateAssumptionRecord], list[QualityFlag]]:
        molecular_weight = self._scenario_record(
            scenario,
            MOLECULAR_WEIGHT_PARAMETER,
            "g/mol",
            required=True,
        )
        henry = self._scenario_record(
            scenario,
            HENRY_PARAMETER,
            "Pa m3/mol",
            required=True,
        )
        koc = self._scenario_record(
            scenario,
            KOC_PARAMETER,
            "L/kg",
            required=True,
        )
        assert molecular_weight is not None
        assert henry is not None
        assert koc is not None
        for record in (molecular_weight, henry, koc):
            self._ensure_positive(record.value, parameter=record.parameter)
        return (
            molecular_weight.value,
            henry.value,
            koc.value,
            [
                self.provenance_builder.from_parameter_record(
                    molecular_weight,
                    "Explicit molecular weight used to convert fugacity-screening moles to mass.",
                ),
                self.provenance_builder.from_parameter_record(
                    henry,
                    "Explicit Henry law constant used to resolve air/water fugacity capacities.",
                ),
                self.provenance_builder.from_parameter_record(
                    koc,
                    "Explicit organic-carbon partition coefficient used for soil/sediment capacity terms.",
                ),
            ],
            [
                flag
                for record in (molecular_weight, henry, koc)
                for flag in record.quality_flags
            ],
        )

    def _treatment_adjustment(
        self,
        scenario: EnvironmentalReleaseScenario,
    ) -> tuple[float, list[FateAssumptionRecord], list[QualityFlag], list[LimitationNote]]:
        executable_removal = 0.0
        assumptions: list[FateAssumptionRecord] = []
        warnings: list[QualityFlag] = []
        limitations: list[LimitationNote] = []
        provenance_only = False
        for treatment in scenario.treatment_assumptions:
            if treatment.execution_mode == TreatmentExecutionMode.PRE_RELEASE_GLOBAL:
                executable_removal += treatment.removal_fraction
                assumptions.append(
                    self.provenance_builder.user_input(
                        "pre_release_global_treatment_removal_fraction",
                        treatment.removal_fraction,
                        "fraction",
                        (
                            f"Applied treatment assumption {treatment.treatment_type} before "
                            "fugacity screening release mass allocation."
                        ),
                    )
                )
            else:
                provenance_only = True
        if executable_removal > 1.0:
            raise FateValidationError(
                code="treatment_removal_fraction_exceeds_one",
                message="Executable treatment removal fractions cannot exceed 1.0 in aggregate.",
                suggestion="Reduce treatment removal fractions or leave non-executable assumptions as provenance-only.",
            )
        if provenance_only:
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
                        "and were not used to reduce fugacity-screening release mass."
                    ),
                )
            )
        return max(0.0, 1.0 - executable_removal), assumptions, warnings, limitations

    def _media_capacity_terms(
        self,
        scenario: EnvironmentalReleaseScenario,
        henry_law_constant: float,
        koc_l_kg: float,
    ) -> tuple[dict[Media, dict[str, float]], list[FateAssumptionRecord]]:
        temperature_k = scenario.temperature_c + KELVIN_OFFSET
        self._ensure_positive(temperature_k, parameter="scenario_temperature_k")
        profile = self.defaults_registry.fugacity_screening_method_profile(
            "fugacity_level_i_equilibrium_v1"
        )
        if profile is None:
            raise FateValidationError(
                code="missing_fugacity_screening_method_profile",
                message="Fugacity screening method profile fugacity_level_i_equilibrium_v1 is missing.",
                suggestion="Regenerate or repair defaults/v1/fugacity_screening_method_profiles.json.",
            )
        soil_foc = self._ensure_positive(
            profile.constants["soil_organic_carbon_fraction"],
            parameter="soil_organic_carbon_fraction",
        )
        sediment_foc = self._ensure_positive(
            profile.constants["sediment_organic_carbon_fraction"],
            parameter="sediment_organic_carbon_fraction",
        )
        z_air = 1.0 / (GAS_CONSTANT_PA_M3_MOL_K * temperature_k)
        z_water = 1.0 / henry_law_constant
        kd_soil_m3_kg = koc_l_kg * soil_foc * 0.001
        kd_sediment_m3_kg = koc_l_kg * sediment_foc * 0.001
        assumptions: list[FateAssumptionRecord] = [
            self.provenance_builder.derived(
                "scenario_temperature_k",
                temperature_k,
                "K",
                "Scenario temperature converted to Kelvin for R*T fugacity capacity terms.",
            ),
            self.provenance_builder.derived(
                "soil_organic_carbon_fraction",
                soil_foc,
                "fraction",
                "Governed v0.4.0 fugacity screening soil organic-carbon fraction.",
            ),
            self.provenance_builder.derived(
                "sediment_organic_carbon_fraction",
                sediment_foc,
                "fraction",
                "Governed v0.4.0 fugacity screening sediment organic-carbon fraction.",
            ),
        ]
        terms: dict[Media, dict[str, float]] = {}
        for medium in ACTIVE_MEDIA:
            media_defaults = self.defaults_registry.media_defaults(medium)
            capacity_value, _, capacity_assumption = self._scenario_or_default_parameter(
                scenario,
                media_defaults.capacity_parameter,
                "m3" if medium in {Media.AIR, Media.WATER} else "kg",
            )
            assumptions.append(capacity_assumption)
            region_scalar = self.defaults_registry.region_scalar(
                scenario.geographic_scope.region_id,
                media_defaults.compartment,
            )
            effective_capacity = capacity_value * region_scalar
            if medium == Media.AIR:
                capacity_term = z_air * effective_capacity
                z_or_kd = z_air
            elif medium == Media.WATER:
                capacity_term = z_water * effective_capacity
                z_or_kd = z_water
            elif medium == Media.SOIL:
                capacity_term = z_water * kd_soil_m3_kg * effective_capacity
                z_or_kd = kd_soil_m3_kg
            else:
                capacity_term = z_water * kd_sediment_m3_kg * effective_capacity
                z_or_kd = kd_sediment_m3_kg
            self._ensure_positive(capacity_term, parameter=f"{medium.value}_fugacity_capacity_term")
            terms[medium] = {
                "effective_capacity": effective_capacity,
                "region_scalar": region_scalar,
                "z_or_kd": z_or_kd,
                "capacity_term_mol_per_pa": capacity_term,
            }
        return terms, assumptions

    def _loss_constants(
        self,
        scenario: EnvironmentalReleaseScenario,
    ) -> tuple[dict[Media, float], list[FateAssumptionRecord], list[QualityFlag]]:
        loss_constants = {}
        assumptions: list[FateAssumptionRecord] = []
        quality_flags: list[QualityFlag] = []
        for medium in ACTIVE_MEDIA:
            media_defaults = self.defaults_registry.media_defaults(medium)
            half_life_days, half_life_override, assumption = self._scenario_or_default_parameter(
                scenario,
                media_defaults.degradation_half_life_parameter,
                "day",
            )
            assumptions.append(assumption)
            if half_life_override is not None:
                quality_flags.extend(half_life_override.quality_flags)
            loss_constants[medium] = math.log(2.0) / half_life_days
        return loss_constants, assumptions, quality_flags

    def _build_surface(
        self,
        *,
        scenario: EnvironmentalReleaseScenario,
        run_options: FateModelRunOptions,
        medium: Media,
        fugacity_pa: float,
        medium_mass_mol: float,
        medium_mass_mg: float,
        partition_fraction: float,
        capacity_terms: dict[Media, dict[str, float]],
        denominator: float,
        loss_constant_per_day: float | None,
        degradation_loss_mol_day: float | None,
        total_scoped_moles_or_rate: float,
        quality_flags: list[QualityFlag],
        treatment_limitations: list[LimitationNote],
    ) -> ConcentrationSurface:
        media_defaults = self.defaults_registry.media_defaults(medium)
        if medium in {Media.AIR, Media.WATER}:
            concentration_value = medium_mass_mg / capacity_terms[medium]["effective_capacity"]
        else:
            concentration_value = medium_mass_mg / capacity_terms[medium]["effective_capacity"]
        calculation_trace_terms = [
            CalculationTraceTerm(name="screening_level", value=run_options.fugacity_screening_level.value),
            CalculationTraceTerm(name="fugacity", value=fugacity_pa, unit="Pa"),
            CalculationTraceTerm(name="total_capacity_denominator", value=denominator),
            CalculationTraceTerm(
                name="total_scoped_moles_or_rate",
                value=total_scoped_moles_or_rate,
                unit=(
                    "mol"
                    if run_options.fugacity_screening_level == FugacityScreeningLevel.LEVEL_I_EQUILIBRIUM
                    else "mol/day"
                ),
            ),
            CalculationTraceTerm(
                name="medium_capacity_term",
                value=capacity_terms[medium]["capacity_term_mol_per_pa"],
                unit="mol/Pa",
            ),
            CalculationTraceTerm(
                name="medium_effective_capacity",
                value=capacity_terms[medium]["effective_capacity"],
                unit="m3" if medium in {Media.AIR, Media.WATER} else "kg",
            ),
            CalculationTraceTerm(name="medium_mass_mol", value=medium_mass_mol, unit="mol"),
            CalculationTraceTerm(name="medium_mass_mg", value=medium_mass_mg, unit="mg"),
            CalculationTraceTerm(name="medium_partition_fraction", value=partition_fraction, unit="fraction"),
        ]
        if loss_constant_per_day is not None and degradation_loss_mol_day is not None:
            calculation_trace_terms.extend(
                [
                    CalculationTraceTerm(
                        name="medium_degradation_loss_constant",
                        value=loss_constant_per_day,
                        unit="1/day",
                    ),
                    CalculationTraceTerm(
                        name="medium_degradation_loss_rate",
                        value=degradation_loss_mol_day,
                        unit="mol/day",
                    ),
                ]
            )
        if medium in {Media.SOIL, Media.SEDIMENT}:
            calculation_trace_terms.append(
                CalculationTraceTerm(
                    name="medium_kd_capacity_term",
                    value=capacity_terms[medium]["z_or_kd"],
                    unit="m3/kg",
                )
            )
        else:
            calculation_trace_terms.append(
                CalculationTraceTerm(
                    name="medium_z_value",
                    value=capacity_terms[medium]["z_or_kd"],
                    unit="mol/(m3 Pa)",
                )
            )
        calculation_trace = CalculationTrace(
            equation_id=f"fugacity-{run_options.fugacity_screening_level.value}-0.4.0",
            equation_text=(
                "Level I: f = total_scoped_moles / sum(Z_i * V_i); mass_i = f * Z_i * V_i."
                if run_options.fugacity_screening_level == FugacityScreeningLevel.LEVEL_I_EQUILIBRIUM
                else "Level II: f = input_rate_mol_day / sum(k_i * Z_i * V_i); mass_i = f * Z_i * V_i."
            ),
            resolved_terms=calculation_trace_terms,
            notes=[
                "Fugacity screening uses all four active media in the partition denominator.",
                "requested_media filters returned surfaces only and does not alter equilibrium partitioning.",
                "Scenario temperature is used in R*T; Henry law temperature correction is not applied in v0.4.0.",
                "Release entry medium does not affect equilibrium partitioning in this experimental family.",
            ],
        )
        return ConcentrationSurface(
            scenario_id=scenario.scenario_id,
            medium=medium,
            compartment=media_defaults.compartment,
            geographic_scope=scenario.geographic_scope,
            time_window=TimeWindow(mode=RunMode.STEADY_STATE),
            reported_time_semantics=ReportedTimeSemantics.FUGACITY_EQUILIBRIUM_PARTITIONING,
            concentration_value=concentration_value,
            concentration_unit=OUTPUT_UNITS[medium],
            model_family=ModelFamily.FUGACITY_EQUILIBRIUM_SCREENING,
            fit_for_purpose=run_options.fit_for_purpose,
            provenance=self.provenance_builder.bundle(scenario.evidence_sources),
            calculation_trace=calculation_trace,
            quality_flags=quality_flags,
            limitations=[
                LimitationNote(code="experimental_fugacity_screening", message=text)
                for text in self.limitations
            ]
            + [
                LimitationNote(
                    code="equilibrium_entry_route_ignored",
                    message=(
                        "Release fractions determine scoped released mass/rate only; entry-medium route "
                        "does not affect equilibrium partitioning in this family."
                    ),
                ),
                LimitationNote(
                    code="henry_temperature_correction_not_applied",
                    message=(
                        "Scenario temperature is used in R*T, but Henry law temperature correction is not "
                        "applied in v0.4.0."
                    ),
                ),
            ]
            + treatment_limitations,
        )

    def run(
        self,
        scenario: EnvironmentalReleaseScenario,
        run_options: FateModelRunOptions,
    ) -> ConcentrationEstimationResult:
        if run_options.run_mode != RunMode.STEADY_STATE:
            raise FateValidationError(
                code="fugacity_screening_time_bucket_unsupported",
                message="Fugacity equilibrium screening supports steady_state mode only in v0.4.0.",
                suggestion="Use run_mode=steady_state, or keep the reference family for time-bucket screening.",
            )
        molecular_weight, henry, koc, physchem_assumptions, parameter_quality_flags = (
            self._required_physchem_parameters(scenario)
        )
        treatment_scalar, treatment_assumptions, treatment_warnings, treatment_limitations = (
            self._treatment_adjustment(scenario)
        )
        scoped_fraction = sum(item.fraction for item in scenario.release_fractions)
        effective_total_release_mass_kg = scenario.total_release_mass_kg * scoped_fraction * treatment_scalar
        total_scoped_moles = effective_total_release_mass_kg * 1000.0 / molecular_weight
        capacity_terms, capacity_assumptions = self._media_capacity_terms(scenario, henry, koc)
        denominator: float
        fugacity_pa: float
        loss_constants: dict[Media, float] = {}
        loss_assumptions: list[FateAssumptionRecord] = []
        loss_quality_flags: list[QualityFlag] = []
        degradation_loss_rates: dict[Media, float] = {}
        if run_options.fugacity_screening_level == FugacityScreeningLevel.LEVEL_I_EQUILIBRIUM:
            denominator = sum(item["capacity_term_mol_per_pa"] for item in capacity_terms.values())
            fugacity_pa = total_scoped_moles / denominator
            total_scoped_moles_or_rate = total_scoped_moles
        else:
            loss_constants, loss_assumptions, loss_quality_flags = self._loss_constants(scenario)
            denominator = sum(
                loss_constants[medium] * capacity_terms[medium]["capacity_term_mol_per_pa"]
                for medium in ACTIVE_MEDIA
            )
            input_rate_mol_day = total_scoped_moles / scenario.duration_days
            fugacity_pa = input_rate_mol_day / denominator
            total_scoped_moles_or_rate = input_rate_mol_day
        self._ensure_positive(denominator, parameter="fugacity_capacity_denominator")
        returned_media = set(run_options.requested_media or ACTIVE_MEDIA)
        surfaces: list[ConcentrationSurface] = []
        total_mass_mol = 0.0
        for medium in ACTIVE_MEDIA:
            medium_mass_mol = fugacity_pa * capacity_terms[medium]["capacity_term_mol_per_pa"]
            medium_mass_mg = medium_mass_mol * molecular_weight * 1000.0
            partition_fraction = (
                medium_mass_mol / total_scoped_moles if total_scoped_moles > 0.0 else 0.0
            )
            total_mass_mol += medium_mass_mol
            degradation_loss_rate = None
            loss_constant = None
            if run_options.fugacity_screening_level == FugacityScreeningLevel.LEVEL_II_EQUILIBRIUM_PERSISTENCE:
                loss_constant = loss_constants[medium]
                degradation_loss_rate = loss_constant * medium_mass_mol
                degradation_loss_rates[medium] = degradation_loss_rate
            if medium not in returned_media:
                continue
            surfaces.append(
                self._build_surface(
                    scenario=scenario,
                    run_options=run_options,
                    medium=medium,
                    fugacity_pa=fugacity_pa,
                    medium_mass_mol=medium_mass_mol,
                    medium_mass_mg=medium_mass_mg,
                    partition_fraction=partition_fraction,
                    capacity_terms=capacity_terms,
                    denominator=denominator,
                    loss_constant_per_day=loss_constant,
                    degradation_loss_mol_day=degradation_loss_rate,
                    total_scoped_moles_or_rate=total_scoped_moles_or_rate,
                    quality_flags=parameter_quality_flags + loss_quality_flags + treatment_warnings,
                    treatment_limitations=treatment_limitations,
                )
            )
        assumptions = [
            *physchem_assumptions,
            *capacity_assumptions,
            *loss_assumptions,
            *treatment_assumptions,
            self.provenance_builder.derived(
                "fugacity_scoped_release_fraction",
                scoped_fraction,
                "fraction",
                "Sum of declared release fractions used to scope fugacity screening mass/rate.",
            ),
            self.provenance_builder.derived(
                "fugacity_effective_total_release_mass_kg",
                effective_total_release_mass_kg,
                "kg",
                "Scoped release mass after declared release fractions and executable treatment removal.",
            ),
            self.provenance_builder.derived(
                "fugacity_total_mass_mol",
                total_mass_mol,
                "mol",
                "Total partitioned mass across all active fugacity media.",
            ),
        ]
        if degradation_loss_rates:
            assumptions.append(
                self.provenance_builder.derived(
                    "fugacity_total_degradation_loss_rate_mol_day",
                    sum(degradation_loss_rates.values()),
                    "mol/day",
                    "Summed Level II degradation loss rate across active fugacity media.",
                )
            )
        run_summary = FateRunSummary(
            scenario_id=scenario.scenario_id,
            model_family=run_options.model_family,
            run_mode=run_options.run_mode,
            surfaces_emitted=len(surfaces),
            assumptions_applied=assumptions,
            escalation_concerns=run_options.escalation_concerns,
            warnings=treatment_warnings,
            result_metadata=ResultMetadata.completed(result_id=f"result-{scenario.scenario_id}"),
        )
        return ConcentrationEstimationResult(
            surfaces=surfaces,
            run_summary=run_summary,
            assumptions=assumptions,
        )
