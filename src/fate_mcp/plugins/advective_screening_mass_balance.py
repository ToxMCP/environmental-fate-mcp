from __future__ import annotations

import math
from datetime import timedelta

from fate_mcp.errors import FateValidationError
from fate_mcp.models import (
    CalculationTrace,
    CalculationTraceTerm,
    ConcentrationSurface,
    EnvironmentalReleaseScenario,
    FateModelRunOptions,
    LimitationNote,
    Media,
    ModelFamily,
    RunMode,
    TimeWindow,
)
from fate_mcp.plugins.base import PluginKey
from fate_mcp.plugins.reference_mass_balance import ReferenceMassBalancePlugin


class AdvectiveScreeningMassBalancePlugin(ReferenceMassBalancePlugin):
    key = PluginKey(
        run_mode=RunMode.STEADY_STATE,
        model_family=ModelFamily.ADVECTIVE_SCREENING_MASS_BALANCE,
    )
    limitations = [
        "Advective screening plugin is deterministic and screening-oriented.",
        "Advective screening plugin adds first-order advective clearance but does not model spatial gradients or explicit intermedia transfer coefficients.",
    ]

    @staticmethod
    def _safe_advective_constant(residence_time_days: float) -> tuple[float, list[str]]:
        notes: list[str] = []
        effective_residence_time_days = residence_time_days
        if residence_time_days <= 0.0:
            effective_residence_time_days = 0.1
            notes.append(
                "Residence time was non-positive and was clamped to 0.1 day before advective-clearance calculation."
            )
        return 1.0 / effective_residence_time_days, notes

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
        if media_defaults.advective_residence_time_parameter is None:
            raise FateValidationError(
                code="missing_advective_residence_time_parameter",
                message=f"No advective residence-time parameter is declared for medium {medium.value}.",
                suggestion="Declare advectiveResidenceTimeParameter in defaults/v1/core_defaults.json.",
            )
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
        residence_time_override = self._parameter_override(
            scenario,
            media_defaults.advective_residence_time_parameter,
            "day",
        )
        capacity_value = (
            capacity_override.value
            if capacity_override
            else self.defaults_registry.parameter_value(media_defaults.capacity_parameter)
        ) * region_scalar
        half_life_days = (
            half_life_override.value
            if half_life_override
            else self.defaults_registry.parameter_value(media_defaults.degradation_half_life_parameter)
        )
        residence_time_days = (
            residence_time_override.value
            if residence_time_override
            else self.defaults_registry.parameter_value(media_defaults.advective_residence_time_parameter)
        )
        release_mass_mg = effective_total_release_mass_kg * 1_000_000.0 * fraction
        release_rate_mg_per_day = release_mass_mg / scenario.duration_days
        decay_constant_per_day, decay_notes = self._safe_decay_constant(half_life_days)
        advective_constant_per_day, advective_notes = self._safe_advective_constant(residence_time_days)
        total_loss_constant_per_day = decay_constant_per_day + advective_constant_per_day
        effective_half_life_days: float | str
        combined_loss_characteristic_time_days: float | str
        combined_loss_half_life_days: float | str
        degradation_loss_share_fraction: float
        advective_clearance_share_fraction: float
        loss_dominance_margin_fraction: float
        if decay_constant_per_day <= 1e-12:
            effective_half_life_days = "infinite"
        else:
            effective_half_life_days = math.log(2.0) / decay_constant_per_day
        if total_loss_constant_per_day <= 1e-12:
            combined_loss_characteristic_time_days = "infinite"
            combined_loss_half_life_days = "infinite"
            degradation_loss_share_fraction = 0.0
            advective_clearance_share_fraction = 0.0
            loss_dominance_margin_fraction = 0.0
        else:
            combined_loss_characteristic_time_days = 1.0 / total_loss_constant_per_day
            combined_loss_half_life_days = math.log(2.0) / total_loss_constant_per_day
            degradation_loss_share_fraction = decay_constant_per_day / total_loss_constant_per_day
            advective_clearance_share_fraction = (
                advective_constant_per_day / total_loss_constant_per_day
            )
            loss_dominance_margin_fraction = abs(
                degradation_loss_share_fraction - advective_clearance_share_fraction
            )
        if run_options.run_mode == RunMode.STEADY_STATE:
            elapsed_days = scenario.duration_days
        else:
            safe_bucket_index = bucket_index or 0
            elapsed_days = run_options.bucket_duration_days * (safe_bucket_index + 1)
        raw_concentration, active_emission_duration_days = self._concentration_at_time(
            release_rate_mg_per_day=release_rate_mg_per_day,
            capacity_value=capacity_value,
            decay_constant_per_day=total_loss_constant_per_day,
            emission_duration_days=scenario.duration_days,
            elapsed_days=elapsed_days,
        )
        emitted_mass_to_elapsed_mg = release_rate_mg_per_day * active_emission_duration_days
        compartment_mass_at_elapsed_mg = raw_concentration * capacity_value
        cumulative_removed_mass_mg = max(
            emitted_mass_to_elapsed_mg - compartment_mass_at_elapsed_mg,
            0.0,
        )
        cumulative_degraded_mass_mg = (
            cumulative_removed_mass_mg * degradation_loss_share_fraction
        )
        cumulative_advected_mass_mg = (
            cumulative_removed_mass_mg * advective_clearance_share_fraction
        )
        mass_balance_closure_error_mg = (
            emitted_mass_to_elapsed_mg
            - compartment_mass_at_elapsed_mg
            - cumulative_degraded_mass_mg
            - cumulative_advected_mass_mg
        )
        if emitted_mass_to_elapsed_mg <= 1e-12:
            compartment_retention_fraction_of_emitted = 0.0
            cumulative_loss_fraction_of_emitted = 0.0
        else:
            compartment_retention_fraction_of_emitted = (
                compartment_mass_at_elapsed_mg / emitted_mass_to_elapsed_mg
            )
            cumulative_loss_fraction_of_emitted = (
                cumulative_removed_mass_mg / emitted_mass_to_elapsed_mg
            )
        elapsed_turnover_count = elapsed_days * advective_constant_per_day
        active_emission_turnover_count = active_emission_duration_days * advective_constant_per_day
        storage_boundary_offset_turnovers = elapsed_turnover_count - 0.75
        flow_through_boundary_offset_turnovers = elapsed_turnover_count - 2.0
        post_release_elapsed_days = max(elapsed_days - scenario.duration_days, 0.0)
        post_release_elapsed_turnover_count: float | str
        post_release_flushing_boundary_offset_turnovers: float | str
        post_release_transition_margin_turnovers: float | str
        post_release_boundary_retained_fraction_of_release_stop_mass: float | str
        post_release_retained_fraction_offset_from_boundary: float | str
        post_release_retained_fraction_ratio_to_boundary: float | str
        post_release_half_recovery_days: float | str
        post_release_half_recovery_turnovers: float | str
        post_release_half_recovery_offset_turnovers: float | str
        post_release_half_recovery_transition_margin_turnovers: float | str
        post_release_recovery_window_multiple_of_half_recovery: float | str
        post_release_retained_fraction_offset_from_half_recovery_anchor: float | str
        post_release_retained_fraction_ratio_to_half_recovery_anchor: float | str
        if post_release_elapsed_days > 0.0:
            release_stop_concentration, _ = self._concentration_at_time(
                release_rate_mg_per_day=release_rate_mg_per_day,
                capacity_value=capacity_value,
                decay_constant_per_day=total_loss_constant_per_day,
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
                    * degradation_loss_share_fraction
                )
                post_release_advected_fraction_of_release_stop_mass = (
                    post_release_removed_fraction_of_release_stop_mass
                    * advective_clearance_share_fraction
                )
            post_release_elapsed_turnover_count = (
                post_release_elapsed_days * advective_constant_per_day
            )
            post_release_flushing_boundary_offset_turnovers = (
                post_release_elapsed_turnover_count - 1.0
            )
            post_release_transition_margin_turnovers = abs(
                post_release_flushing_boundary_offset_turnovers
            )
            post_release_boundary_retained_fraction_of_release_stop_mass = math.exp(
                -total_loss_constant_per_day * residence_time_days
            )
            post_release_retained_fraction_offset_from_boundary = (
                post_release_retained_fraction_of_release_stop_mass
                - post_release_boundary_retained_fraction_of_release_stop_mass
            )
            if post_release_boundary_retained_fraction_of_release_stop_mass <= 1e-12:
                post_release_retained_fraction_ratio_to_boundary = "not_applicable"
            else:
                post_release_retained_fraction_ratio_to_boundary = (
                    post_release_retained_fraction_of_release_stop_mass
                    / post_release_boundary_retained_fraction_of_release_stop_mass
                )
            if total_loss_constant_per_day <= 1e-12:
                post_release_half_recovery_days = "infinite"
                post_release_half_recovery_turnovers = "infinite"
                post_release_half_recovery_offset_turnovers = "not_applicable"
                post_release_recovery_window_multiple_of_half_recovery = "not_applicable"
            else:
                post_release_half_recovery_days = math.log(2.0) / total_loss_constant_per_day
                post_release_half_recovery_turnovers = (
                    post_release_half_recovery_days * advective_constant_per_day
                )
                post_release_half_recovery_offset_turnovers = (
                    post_release_elapsed_turnover_count - post_release_half_recovery_turnovers
                )
                post_release_half_recovery_transition_margin_turnovers = abs(
                    post_release_half_recovery_offset_turnovers
                )
                post_release_recovery_window_multiple_of_half_recovery = (
                    post_release_elapsed_turnover_count / post_release_half_recovery_turnovers
                    if abs(post_release_half_recovery_turnovers) > 1e-12
                    else "not_applicable"
                )
            post_release_retained_fraction_offset_from_half_recovery_anchor = (
                post_release_retained_fraction_of_release_stop_mass - 0.5
            )
            post_release_retained_fraction_ratio_to_half_recovery_anchor = (
                post_release_retained_fraction_of_release_stop_mass / 0.5
            )
        else:
            release_stop_compartment_mass_mg = "not_applicable"
            post_release_retained_fraction_of_release_stop_mass = "not_applicable"
            post_release_removed_fraction_of_release_stop_mass = "not_applicable"
            post_release_degraded_fraction_of_release_stop_mass = "not_applicable"
            post_release_advected_fraction_of_release_stop_mass = "not_applicable"
            post_release_elapsed_turnover_count = "not_applicable"
            post_release_flushing_boundary_offset_turnovers = "not_applicable"
            post_release_transition_margin_turnovers = "not_applicable"
            post_release_boundary_retained_fraction_of_release_stop_mass = "not_applicable"
            post_release_retained_fraction_offset_from_boundary = "not_applicable"
            post_release_retained_fraction_ratio_to_boundary = "not_applicable"
            post_release_half_recovery_days = "not_applicable"
            post_release_half_recovery_turnovers = "not_applicable"
            post_release_half_recovery_offset_turnovers = "not_applicable"
            post_release_half_recovery_transition_margin_turnovers = "not_applicable"
            post_release_recovery_window_multiple_of_half_recovery = "not_applicable"
            post_release_retained_fraction_offset_from_half_recovery_anchor = "not_applicable"
            post_release_retained_fraction_ratio_to_half_recovery_anchor = "not_applicable"
        finite_plateau_mass_mg: float | str
        retained_mass_fraction_of_finite_plateau: float | str
        if total_loss_constant_per_day <= 1e-12:
            finite_plateau_mass_mg = "infinite"
            retained_mass_fraction_of_finite_plateau = "not_applicable"
        else:
            finite_plateau_mass_mg = release_rate_mg_per_day / total_loss_constant_per_day
            retained_mass_fraction_of_finite_plateau = min(
                max(compartment_mass_at_elapsed_mg / finite_plateau_mass_mg, 0.0),
                1.0,
            )
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
                    f"User- or evidence-supplied half-life override used for {medium.value} degradation loss.",
                )
                if half_life_override
                else self.provenance_builder.curated_default(
                    media_defaults.degradation_half_life_parameter,
                    f"Half-life used for {medium.value} degradation loss.",
                )
            ),
            (
                self.provenance_builder.from_parameter_record(
                    residence_time_override,
                    f"User- or evidence-supplied residence time override used for {medium.value} advective clearance.",
                )
                if residence_time_override
                else self.provenance_builder.curated_default(
                    media_defaults.advective_residence_time_parameter,
                    f"Residence time used for {medium.value} advective clearance.",
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
                "First-order degradation constant used in the advective screening calculation.",
            ),
            self.provenance_builder.derived(
                f"{medium.value}_advective_clearance_constant_per_day",
                advective_constant_per_day,
                "1/day",
                "First-order advective clearance constant used in the advective screening calculation.",
            ),
            self.provenance_builder.derived(
                f"{medium.value}_total_loss_constant_per_day",
                total_loss_constant_per_day,
                "1/day",
                "Combined first-order loss constant used in the advective screening calculation.",
            ),
        ]

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

        if total_loss_constant_per_day <= 1e-12:
            equation_id = "advective_screening_no_loss_limit"
            equation_text = "C(t) = (R * min(t, T)) / V"
        elif elapsed_days <= scenario.duration_days:
            equation_id = "advective_screening_continuous_release_first_order"
            equation_text = "C(t) = (R / ((k_deg + k_adv) * V)) * (1 - exp(-(k_deg + k_adv) * t))"
        else:
            equation_id = "advective_screening_post_release_first_order_decay"
            equation_text = (
                "C(t) = (R / ((k_deg + k_adv) * V)) * (1 - exp(-(k_deg + k_adv) * T)) * "
                "exp(-(k_deg + k_adv) * (t - T))"
            )
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
                CalculationTraceTerm(name="declared_half_life_days", value=half_life_days, unit="day"),
                CalculationTraceTerm(
                    name="effective_half_life_days",
                    value=effective_half_life_days,
                    unit="day",
                ),
                CalculationTraceTerm(name="decay_constant_per_day", value=decay_constant_per_day, unit="1/day"),
                CalculationTraceTerm(
                    name="advective_clearance_constant_per_day",
                    value=advective_constant_per_day,
                    unit="1/day",
                ),
                CalculationTraceTerm(
                    name="total_loss_constant_per_day",
                    value=total_loss_constant_per_day,
                    unit="1/day",
                ),
                CalculationTraceTerm(
                    name="degradation_loss_share_fraction",
                    value=degradation_loss_share_fraction,
                    unit="fraction",
                ),
                CalculationTraceTerm(
                    name="advective_clearance_share_fraction",
                    value=advective_clearance_share_fraction,
                    unit="fraction",
                ),
                CalculationTraceTerm(
                    name="loss_dominance_margin_fraction",
                    value=loss_dominance_margin_fraction,
                    unit="fraction",
                ),
                CalculationTraceTerm(
                    name="combined_loss_characteristic_time_days",
                    value=combined_loss_characteristic_time_days,
                    unit="day",
                ),
                CalculationTraceTerm(
                    name="combined_loss_half_life_days",
                    value=combined_loss_half_life_days,
                    unit="day",
                ),
                CalculationTraceTerm(name="residence_time_days", value=residence_time_days, unit="day"),
                CalculationTraceTerm(
                    name="elapsed_turnover_count",
                    value=elapsed_turnover_count,
                    unit="turnovers",
                ),
                CalculationTraceTerm(
                    name="active_emission_turnover_count",
                    value=active_emission_turnover_count,
                    unit="turnovers",
                ),
                CalculationTraceTerm(
                    name="storage_boundary_offset_turnovers",
                    value=storage_boundary_offset_turnovers,
                    unit="turnovers",
                ),
                CalculationTraceTerm(
                    name="flow_through_boundary_offset_turnovers",
                    value=flow_through_boundary_offset_turnovers,
                    unit="turnovers",
                ),
                CalculationTraceTerm(
                    name="finite_plateau_mass_mg",
                    value=finite_plateau_mass_mg,
                    unit="mg",
                ),
                CalculationTraceTerm(
                    name="retained_mass_fraction_of_finite_plateau",
                    value=retained_mass_fraction_of_finite_plateau,
                    unit="fraction",
                ),
                CalculationTraceTerm(name="elapsed_days", value=elapsed_days, unit="day"),
                CalculationTraceTerm(name="emission_duration_days", value=scenario.duration_days, unit="day"),
                CalculationTraceTerm(
                    name="active_emission_duration_days",
                    value=active_emission_duration_days,
                    unit="day",
                ),
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
                    name="cumulative_removed_mass_mg",
                    value=cumulative_removed_mass_mg,
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
                    name="compartment_retention_fraction_of_emitted",
                    value=compartment_retention_fraction_of_emitted,
                    unit="fraction",
                ),
                CalculationTraceTerm(
                    name="cumulative_loss_fraction_of_emitted",
                    value=cumulative_loss_fraction_of_emitted,
                    unit="fraction",
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
                CalculationTraceTerm(
                    name="post_release_elapsed_turnover_count",
                    value=post_release_elapsed_turnover_count,
                    unit="turnovers",
                ),
                CalculationTraceTerm(
                    name="post_release_flushing_boundary_offset_turnovers",
                    value=post_release_flushing_boundary_offset_turnovers,
                    unit="turnovers",
                ),
                CalculationTraceTerm(
                    name="post_release_transition_margin_turnovers",
                    value=post_release_transition_margin_turnovers,
                    unit="turnovers",
                ),
                CalculationTraceTerm(
                    name="post_release_boundary_retained_fraction_of_release_stop_mass",
                    value=post_release_boundary_retained_fraction_of_release_stop_mass,
                    unit="fraction",
                ),
                CalculationTraceTerm(
                    name="post_release_retained_fraction_offset_from_boundary",
                    value=post_release_retained_fraction_offset_from_boundary,
                    unit="fraction",
                ),
                CalculationTraceTerm(
                    name="post_release_retained_fraction_ratio_to_boundary",
                    value=post_release_retained_fraction_ratio_to_boundary,
                    unit="ratio",
                ),
                CalculationTraceTerm(
                    name="post_release_half_recovery_days",
                    value=post_release_half_recovery_days,
                    unit="day",
                ),
                CalculationTraceTerm(
                    name="post_release_half_recovery_turnovers",
                    value=post_release_half_recovery_turnovers,
                    unit="turnovers",
                ),
                CalculationTraceTerm(
                    name="post_release_half_recovery_offset_turnovers",
                    value=post_release_half_recovery_offset_turnovers,
                    unit="turnovers",
                ),
                CalculationTraceTerm(
                    name="post_release_half_recovery_transition_margin_turnovers",
                    value=post_release_half_recovery_transition_margin_turnovers,
                    unit="turnovers",
                ),
                CalculationTraceTerm(
                    name="post_release_recovery_window_multiple_of_half_recovery",
                    value=post_release_recovery_window_multiple_of_half_recovery,
                    unit="multiple",
                ),
                CalculationTraceTerm(
                    name="post_release_retained_fraction_offset_from_half_recovery_anchor",
                    value=post_release_retained_fraction_offset_from_half_recovery_anchor,
                    unit="fraction",
                ),
                CalculationTraceTerm(
                    name="post_release_retained_fraction_ratio_to_half_recovery_anchor",
                    value=post_release_retained_fraction_ratio_to_half_recovery_anchor,
                    unit="ratio",
                ),
                CalculationTraceTerm(name="medium_release_fraction", value=fraction, unit="fraction"),
                CalculationTraceTerm(
                    name="effective_total_release_mass_kg",
                    value=effective_total_release_mass_kg,
                    unit="kg",
                ),
                CalculationTraceTerm(name="region_scalar", value=region_scalar, unit="scalar"),
            ],
            notes=[
                "steady_state outputs represent end-of-duration screening concentration, not an infinite-time equilibrium.",
                "Advective screening combines first-order degradation and first-order residence-time clearance within one compartment per medium.",
                *decay_notes,
                *advective_notes,
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
                        code="advective_screening_kernel",
                        message=(
                            "Advective_screening_mass_balance uses deterministic finite-duration first-order "
                            "screening math with degradation plus advective clearance within one compartment per medium."
                        ),
                    ),
                ]
                + treatment_limitations
            ),
            scenario_id=scenario.scenario_id,
            medium=medium,
            compartment=media_defaults.compartment,
            geographic_scope=scenario.geographic_scope,
            time_window=time_window,
            concentration_value=concentration_value,
            concentration_unit=media_defaults.unit,
            model_family=ModelFamily.ADVECTIVE_SCREENING_MASS_BALANCE,
            fit_for_purpose=run_options.fit_for_purpose,
            provenance=self.provenance_builder.bundle(scenario.evidence_sources),
            calculation_trace=calculation_trace,
            quality_flags=[
                flag
                for record in (capacity_override, half_life_override, residence_time_override)
                if record is not None
                for flag in record.quality_flags
            ],
        )
        return surface, assumptions


class AdvectiveTimeBucketMassBalancePlugin(AdvectiveScreeningMassBalancePlugin):
    key = PluginKey(
        run_mode=RunMode.TIME_BUCKET,
        model_family=ModelFamily.ADVECTIVE_SCREENING_MASS_BALANCE,
    )
