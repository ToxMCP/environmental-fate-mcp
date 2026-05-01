from __future__ import annotations

import hashlib
import math

from fate_mcp.errors import FateValidationError
from fate_mcp.models import (
    AssessErosionSedimentValidationFitRequest,
    BuildErosionSedimentValidationCaseRequest,
    CalculationTrace,
    CalculationTraceTerm,
    ErosionSedimentValidationCaseResult,
    ErosionSedimentValidationFitClassification,
    ErosionSedimentValidationFitMetrics,
    ErosionSedimentValidationFitResult,
    ErosionSedimentValidationMatchedRecord,
    ErosionSedimentValidationProfile,
    ErosionTransportRelevanceLevel,
    ErosionTransportRelevanceResult,
    EstimateEventSedimentYieldMusleRequest,
    EstimateSedimentAssociatedChemicalLoadRequest,
    EstimateSoilLossRusleRequest,
    EventSedimentYieldMusleResult,
    FateAssumptionRecord,
    LimitationNote,
    QualityFlag,
    ScreenErosionTransportRelevanceRequest,
    SedimentAssociatedChemicalLoadResult,
    Severity,
    SoilLossRusleResult,
    SourceClassification,
    SourceReference,
)
from fate_mcp.provenance import ProvenanceBuilder


PARTICLE_ASSOCIATED_CLASS_TOKENS = (
    "particle associated",
    "particle-associated",
    "sediment associated",
    "sediment-associated",
    "hydrophobic organic",
    "metal",
    "pah",
    "pcb",
    "dioxin",
    "nanomaterial",
    "microplastic",
)


def _method_sources(provenance_builder: ProvenanceBuilder, method_id: str) -> list[SourceReference]:
    profile = provenance_builder.defaults_registry.erosion_sediment_method_profile(method_id)
    return profile.source_references if profile is not None else []


def _assumption(parameter: str, value: float, unit: str, rationale: str) -> FateAssumptionRecord:
    return FateAssumptionRecord(
        parameter=parameter,
        value=value,
        unit=unit,
        source_classification=SourceClassification.USER_INPUT,
        rationale=rationale,
    )


def _zero_factor_flags(factors: dict[str, float]) -> list[QualityFlag]:
    zero_fields = [name for name, value in factors.items() if value == 0.0]
    if not zero_fields:
        return []
    return [
        QualityFlag(
            code="zero_erosion_transport_factor",
            severity=Severity.INFO,
            message=(
                "At least one erosion/sediment transport input is zero, so the screening "
                f"equation returns zero. Zero inputs: {', '.join(zero_fields)}."
            ),
        )
    ]


def _screening_limitations(*, includes_chemical_load: bool = False) -> list[LimitationNote]:
    limitations = [
        LimitationNote(
            code="erosion_sediment_screening_only",
            message=(
                "This result is a scalar screening estimate for erosion-mediated transport; "
                "it is not a calibrated watershed, GIS, hydrodynamic, exposure, risk, or regulatory decision model."
            ),
        ),
        LimitationNote(
            code="no_explicit_spatial_routing",
            message=(
                "The v1 erosion/sediment tools do not simulate hillslope routing, channel transport, "
                "deposition fields, rainfall-runoff generation, or receiving-water dilution."
            ),
        ),
    ]
    if includes_chemical_load:
        limitations.append(
            LimitationNote(
                code="chemical_load_screening_assumptions",
                message=(
                    "Sediment-associated chemical load is computed from caller-provided soil concentration, "
                    "sediment delivery ratio, and particle-bound availability fraction; it is not a final "
                    "environmental concentration or dose."
                ),
            )
        )
    return limitations


def _validation_profile(
    provenance_builder: ProvenanceBuilder,
    profile_id: str,
) -> ErosionSedimentValidationProfile:
    profile = provenance_builder.defaults_registry.erosion_sediment_validation_profile(profile_id)
    if profile is None:
        raise FateValidationError(
            code="unknown_erosion_sediment_validation_profile",
            message=f"Erosion/sediment validation profile {profile_id} is not governed.",
            suggestion=(
                "Use a profile listed in defaults://erosion-sediment-validation-profiles."
            ),
            details={"validationProfileId": profile_id},
        )
    return profile


def _validation_limitations(profile: ErosionSedimentValidationProfile) -> list[LimitationNote]:
    return [
        LimitationNote(
            code="erosion_sediment_validation_screening_only",
            message=(
                "Validation fit classifications are screening QA diagnostics only; they are not "
                "calibration, parameter fitting, regulatory acceptance, or proof of scientific adequacy."
            ),
        ),
        LimitationNote(
            code="no_validation_parameter_adjustment",
            message=(
                "This workflow compares caller-supplied observed and predicted records without "
                "optimizing RUSLE/MUSLE factors, hydrology, delivery ratios, or availability fractions."
            ),
        ),
        *[
            LimitationNote(code="governed_validation_profile_limit", message=limitation)
            for limitation in profile.limitations
        ],
    ]


def _unsupported_validation_quantities(
    request: BuildErosionSedimentValidationCaseRequest,
    profile: ErosionSedimentValidationProfile,
) -> list[str]:
    supported = set(profile.supported_quantities)
    quantities = {
        *[record.quantity for record in request.observed_records],
        *[record.quantity for record in request.predicted_records],
    }
    return sorted(quantity.value for quantity in quantities if quantity not in supported)


def build_erosion_sediment_validation_case(
    request: BuildErosionSedimentValidationCaseRequest,
    provenance_builder: ProvenanceBuilder,
) -> ErosionSedimentValidationCaseResult:
    profile = _validation_profile(provenance_builder, request.validation_profile_id)
    unsupported_quantities = _unsupported_validation_quantities(request, profile)
    if unsupported_quantities:
        raise FateValidationError(
            code="unsupported_erosion_sediment_validation_quantity",
            message="One or more erosion/sediment validation quantities are not supported.",
            suggestion=(
                "Use only quantities declared by the governed validation profile: "
                f"{', '.join(quantity.value for quantity in profile.supported_quantities)}."
            ),
            details={
                "validationProfileId": profile.profile_id,
                "unsupportedQuantities": unsupported_quantities,
            },
        )

    observed_by_id = {record.record_id: record for record in request.observed_records}
    predicted_by_id = {record.record_id: record for record in request.predicted_records}
    shared_ids = sorted(set(observed_by_id) & set(predicted_by_id))
    quantity_mismatch_record_ids = [
        record_id
        for record_id in shared_ids
        if observed_by_id[record_id].quantity != predicted_by_id[record_id].quantity
    ]
    matched_record_ids = [
        record_id for record_id in shared_ids if record_id not in quantity_mismatch_record_ids
    ]
    unmatched_observed_record_ids = sorted(set(observed_by_id) - set(predicted_by_id))
    unmatched_predicted_record_ids = sorted(set(predicted_by_id) - set(observed_by_id))

    quality_flags: list[QualityFlag] = []
    if unmatched_observed_record_ids or unmatched_predicted_record_ids:
        quality_flags.append(
            QualityFlag(
                code="unmatched_erosion_sediment_validation_records",
                severity=Severity.WARNING,
                message=(
                    "Some observed or predicted validation records do not have a matching "
                    "record_id in the paired collection."
                ),
            )
        )
    if quantity_mismatch_record_ids:
        quality_flags.append(
            QualityFlag(
                code="erosion_sediment_validation_quantity_mismatch",
                severity=Severity.WARNING,
                message=(
                    "Some records share a record_id but declare different validation quantities; "
                    "they are preserved but excluded from fit metrics."
                ),
            )
        )
    if len(matched_record_ids) < profile.screening_plausible.minimum_matched_records:
        quality_flags.append(
            QualityFlag(
                code="limited_erosion_sediment_validation_matches",
                severity=Severity.INFO,
                message=(
                    "Matched record count is below the governed screening-plausible evidence "
                    "threshold for this validation profile."
                ),
            )
        )

    case_fingerprint = "|".join(
        [
            profile.profile_id,
            *[
                f"observed:{record.record_id}:{record.quantity.value}:{record.observed_value:g}"
                for record in request.observed_records
            ],
            *[
                f"predicted:{record.record_id}:{record.quantity.value}:{record.predicted_value:g}"
                for record in request.predicted_records
            ],
        ]
    )
    case_id = f"erosion-validation-{hashlib.sha256(case_fingerprint.encode()).hexdigest()[:12]}"

    return ErosionSedimentValidationCaseResult(
        case_id=case_id,
        validation_profile_id=profile.profile_id,
        observed_records=request.observed_records,
        predicted_records=request.predicted_records,
        matched_record_ids=matched_record_ids,
        unmatched_observed_record_ids=unmatched_observed_record_ids,
        unmatched_predicted_record_ids=unmatched_predicted_record_ids,
        quantity_mismatch_record_ids=quantity_mismatch_record_ids,
        provenance=provenance_builder.bundle(profile.source_references),
        quality_flags=quality_flags,
        limitations=_validation_limitations(profile),
        interpretation_lines=[
            "Observed and predicted erosion/sediment records were paired by record_id only.",
            "Use the fit assessment as a screening QA check, not as calibration or acceptance.",
        ],
    )


def _mean(values: list[float]) -> float:
    return sum(values) / len(values)


def _classify_validation_fit(
    metrics: ErosionSedimentValidationFitMetrics,
    profile: ErosionSedimentValidationProfile,
) -> ErosionSedimentValidationFitClassification:
    if metrics.matched_count < profile.screening_plausible.minimum_matched_records:
        return ErosionSedimentValidationFitClassification.INSUFFICIENT_EVIDENCE
    if (
        metrics.normalized_bias is None
        or metrics.normalized_root_mean_square_error is None
    ):
        return ErosionSedimentValidationFitClassification.INSUFFICIENT_EVIDENCE
    absolute_normalized_bias = abs(metrics.normalized_bias)
    if (
        metrics.matched_count >= profile.good_screening_fit.minimum_matched_records
        and absolute_normalized_bias
        <= profile.good_screening_fit.maximum_absolute_normalized_bias
        and metrics.normalized_root_mean_square_error
        <= profile.good_screening_fit.maximum_normalized_rmse
        and metrics.factor_of_two_fraction
        >= profile.good_screening_fit.minimum_factor_of_two_fraction
    ):
        return ErosionSedimentValidationFitClassification.GOOD_SCREENING_FIT
    if (
        absolute_normalized_bias
        <= profile.screening_plausible.maximum_absolute_normalized_bias
        and metrics.normalized_root_mean_square_error
        <= profile.screening_plausible.maximum_normalized_rmse
        and metrics.factor_of_two_fraction
        >= profile.screening_plausible.minimum_factor_of_two_fraction
    ):
        return ErosionSedimentValidationFitClassification.SCREENING_PLAUSIBLE
    return ErosionSedimentValidationFitClassification.WEAK_FIT


def assess_erosion_sediment_validation_fit(
    request: AssessErosionSedimentValidationFitRequest,
    provenance_builder: ProvenanceBuilder,
) -> ErosionSedimentValidationFitResult:
    validation_case = request.validation_case
    profile_id = request.validation_profile_id or validation_case.validation_profile_id
    profile = _validation_profile(provenance_builder, profile_id)

    observed_by_id = {record.record_id: record for record in validation_case.observed_records}
    predicted_by_id = {record.record_id: record for record in validation_case.predicted_records}
    matched_ids = [
        record_id
        for record_id in sorted(set(observed_by_id) & set(predicted_by_id))
        if observed_by_id[record_id].quantity == predicted_by_id[record_id].quantity
    ]
    if not matched_ids:
        raise FateValidationError(
            code="erosion_sediment_validation_no_matched_records",
            message="No erosion/sediment validation records could be paired for fit assessment.",
            suggestion=(
                "Provide observed and predicted records with matching record_id values and the "
                "same supported validation quantity."
            ),
            details={
                "caseId": validation_case.case_id,
                "unmatchedObservedRecordIds": validation_case.unmatched_observed_record_ids,
                "unmatchedPredictedRecordIds": validation_case.unmatched_predicted_record_ids,
                "quantityMismatchRecordIds": validation_case.quantity_mismatch_record_ids,
            },
        )

    matched_records: list[ErosionSedimentValidationMatchedRecord] = []
    residuals: list[float] = []
    absolute_errors: list[float] = []
    absolute_percentage_errors: list[float] = []
    within_factor_count = 0
    observed_values: list[float] = []
    for record_id in matched_ids:
        observed = observed_by_id[record_id]
        predicted = predicted_by_id[record_id]
        residual = predicted.predicted_value - observed.observed_value
        absolute_error = abs(residual)
        relative_error = (
            absolute_error / observed.observed_value
            if observed.observed_value > 0.0
            else None
        )
        if observed.observed_value == 0.0:
            within_factor = predicted.predicted_value == 0.0
        else:
            ratio = predicted.predicted_value / observed.observed_value
            within_factor = 0.5 <= ratio <= 2.0
        if within_factor:
            within_factor_count += 1
        if relative_error is not None:
            absolute_percentage_errors.append(relative_error)
        residuals.append(residual)
        absolute_errors.append(absolute_error)
        observed_values.append(observed.observed_value)
        matched_records.append(
            ErosionSedimentValidationMatchedRecord(
                record_id=record_id,
                quantity=observed.quantity,
                observed_value=observed.observed_value,
                predicted_value=predicted.predicted_value,
                residual=residual,
                absolute_error=absolute_error,
                relative_error_fraction=relative_error,
                within_factor_of_two=within_factor,
            )
        )

    matched_count = len(matched_records)
    mean_bias = _mean(residuals)
    mean_absolute_error = _mean(absolute_errors)
    root_mean_square_error = math.sqrt(_mean([residual * residual for residual in residuals]))
    mean_observed_value = _mean(observed_values)
    normalized_bias = mean_bias / mean_observed_value if mean_observed_value > 0.0 else None
    normalized_rmse = (
        root_mean_square_error / mean_observed_value
        if mean_observed_value > 0.0
        else None
    )
    mape = _mean(absolute_percentage_errors) if absolute_percentage_errors else None
    metrics = ErosionSedimentValidationFitMetrics(
        matched_count=matched_count,
        mean_bias=mean_bias,
        mean_absolute_error=mean_absolute_error,
        root_mean_square_error=root_mean_square_error,
        normalized_bias=normalized_bias,
        normalized_root_mean_square_error=normalized_rmse,
        mean_absolute_percentage_error_fraction=mape,
        factor_of_two_fraction=within_factor_count / matched_count,
    )
    classification = _classify_validation_fit(metrics, profile)

    quality_flags = [
        *validation_case.quality_flags,
    ]
    if mape is None:
        quality_flags.append(
            QualityFlag(
                code="mape_unavailable_for_zero_observed_records",
                severity=Severity.INFO,
                message=(
                    "Mean absolute percentage error is unavailable because no matched observed "
                    "record has a positive value."
                ),
            )
        )
    if normalized_bias is None or normalized_rmse is None:
        quality_flags.append(
            QualityFlag(
                code="normalized_fit_metrics_unavailable",
                severity=Severity.WARNING,
                message=(
                    "Normalized bias and normalized RMSE are unavailable because the mean "
                    "matched observed value is zero."
                ),
            )
        )
    if classification == ErosionSedimentValidationFitClassification.INSUFFICIENT_EVIDENCE:
        quality_flags.append(
            QualityFlag(
                code="insufficient_erosion_sediment_validation_evidence",
                severity=Severity.WARNING,
                message=(
                    "Matched record count or normalized metric availability is insufficient "
                    "for a screening-plausible validation fit verdict."
                ),
            )
        )
    elif classification == ErosionSedimentValidationFitClassification.WEAK_FIT:
        quality_flags.append(
            QualityFlag(
                code="weak_erosion_sediment_validation_fit",
                severity=Severity.WARNING,
                message=(
                    "Observed-versus-predicted agreement does not meet the governed "
                    "screening-plausible threshold."
                ),
            )
        )

    return ErosionSedimentValidationFitResult(
        case_id=validation_case.case_id,
        validation_profile_id=profile.profile_id,
        classification=classification,
        metrics=metrics,
        matched_records=matched_records,
        unmatched_observed_record_ids=validation_case.unmatched_observed_record_ids,
        unmatched_predicted_record_ids=validation_case.unmatched_predicted_record_ids,
        quantity_mismatch_record_ids=validation_case.quantity_mismatch_record_ids,
        provenance=provenance_builder.bundle(profile.source_references),
        quality_flags=quality_flags,
        limitations=_validation_limitations(profile),
        interpretation_lines=[
            f"Fit classification: {classification.value}.",
            "Do not use this result to adjust model parameters automatically.",
            "Treat weak or insufficient fits as a prompt for external review, not as a final risk result.",
        ],
    )


def estimate_soil_loss_rusle(
    request: EstimateSoilLossRusleRequest,
    provenance_builder: ProvenanceBuilder,
) -> SoilLossRusleResult:
    annual_soil_loss = (
        request.rainfall_erosivity_r
        * request.soil_erodibility_k
        * request.slope_length_steepness_ls
        * request.cover_management_c
        * request.support_practice_p
    )
    total_soil_loss = (
        annual_soil_loss * request.area_ha
        if request.area_ha is not None
        else None
    )
    trace_terms = [
        CalculationTraceTerm(name="rainfall_erosivity_r", value=request.rainfall_erosivity_r),
        CalculationTraceTerm(name="soil_erodibility_k", value=request.soil_erodibility_k),
        CalculationTraceTerm(name="slope_length_steepness_ls", value=request.slope_length_steepness_ls),
        CalculationTraceTerm(name="cover_management_c", value=request.cover_management_c),
        CalculationTraceTerm(name="support_practice_p", value=request.support_practice_p),
        CalculationTraceTerm(name="annual_soil_loss", value=annual_soil_loss, unit="t/ha/yr"),
    ]
    assumptions = [
        _assumption("rainfall_erosivity_r", request.rainfall_erosivity_r, "R factor", "Caller-provided RUSLE rainfall erosivity factor."),
        _assumption("soil_erodibility_k", request.soil_erodibility_k, "K factor", "Caller-provided RUSLE soil erodibility factor."),
        _assumption("slope_length_steepness_ls", request.slope_length_steepness_ls, "dimensionless", "Caller-provided RUSLE topographic factor."),
        _assumption("cover_management_c", request.cover_management_c, "dimensionless", "Caller-provided RUSLE cover-management factor."),
        _assumption("support_practice_p", request.support_practice_p, "dimensionless", "Caller-provided RUSLE support-practice factor."),
    ]
    if request.area_ha is not None:
        trace_terms.append(CalculationTraceTerm(name="area_ha", value=request.area_ha, unit="ha"))
        trace_terms.append(CalculationTraceTerm(name="total_soil_loss", value=total_soil_loss or 0.0, unit="t/yr"))
        assumptions.append(
            _assumption("area_ha", request.area_ha, "ha", "Caller-provided area used to convert RUSLE rate to annual total soil loss.")
        )
    return SoilLossRusleResult(
        annual_soil_loss_t_ha_yr=annual_soil_loss,
        total_soil_loss_t_yr=total_soil_loss,
        calculation_trace=CalculationTrace(
            equation_id="rusle_v1",
            equation_text="A = R * K * LS * C * P",
            resolved_terms=trace_terms,
            notes=[
                "A is a long-term average annual soil-loss screening estimate.",
                "Optional total soil loss multiplies A by area_ha when area_ha is supplied.",
            ],
        ),
        assumptions=assumptions,
        provenance=provenance_builder.bundle(_method_sources(provenance_builder, "rusle")),
        quality_flags=_zero_factor_flags(
            {
                "rainfall_erosivity_r": request.rainfall_erosivity_r,
                "soil_erodibility_k": request.soil_erodibility_k,
                "slope_length_steepness_ls": request.slope_length_steepness_ls,
                "cover_management_c": request.cover_management_c,
                "support_practice_p": request.support_practice_p,
            }
        ),
        limitations=_screening_limitations(),
        handoff_notes=[
            "Use this as an erosion potential or gross soil-loss screen, not as delivered sediment to surface water.",
            "Use MUSLE or an external hydrology/sediment model when event sediment yield is needed.",
        ],
    )


def estimate_event_sediment_yield_musle(
    request: EstimateEventSedimentYieldMusleRequest,
    provenance_builder: ProvenanceBuilder,
) -> EventSedimentYieldMusleResult:
    sediment_yield = (
        11.8
        * (request.runoff_volume_m3 * request.peak_runoff_rate_m3_s) ** 0.56
        * request.soil_erodibility_k
        * request.slope_length_steepness_ls
        * request.cover_management_c
        * request.support_practice_p
    )
    factors = {
        "runoff_volume_m3": request.runoff_volume_m3,
        "peak_runoff_rate_m3_s": request.peak_runoff_rate_m3_s,
        "soil_erodibility_k": request.soil_erodibility_k,
        "slope_length_steepness_ls": request.slope_length_steepness_ls,
        "cover_management_c": request.cover_management_c,
        "support_practice_p": request.support_practice_p,
    }
    return EventSedimentYieldMusleResult(
        sediment_yield_t_event=sediment_yield,
        calculation_trace=CalculationTrace(
            equation_id="musle_metric_v1",
            equation_text="Sed = 11.8 * (Qsurf * qpeak)^0.56 * K * LS * C * P",
            resolved_terms=[
                CalculationTraceTerm(name="runoff_volume_m3", value=request.runoff_volume_m3, unit="m3"),
                CalculationTraceTerm(name="peak_runoff_rate_m3_s", value=request.peak_runoff_rate_m3_s, unit="m3/s"),
                CalculationTraceTerm(name="soil_erodibility_k", value=request.soil_erodibility_k),
                CalculationTraceTerm(name="slope_length_steepness_ls", value=request.slope_length_steepness_ls),
                CalculationTraceTerm(name="cover_management_c", value=request.cover_management_c),
                CalculationTraceTerm(name="support_practice_p", value=request.support_practice_p),
                CalculationTraceTerm(name="sediment_yield", value=sediment_yield, unit="t/event"),
            ],
            notes=[
                "MUSLE uses caller-provided runoff volume and peak runoff rate.",
                "Environmental Fate MCP does not compute rainfall-runoff generation or routing in this v1 tool.",
            ],
        ),
        assumptions=[
            _assumption("runoff_volume_m3", request.runoff_volume_m3, "m3", "Caller-provided event surface runoff volume."),
            _assumption("peak_runoff_rate_m3_s", request.peak_runoff_rate_m3_s, "m3/s", "Caller-provided event peak runoff rate."),
            _assumption("soil_erodibility_k", request.soil_erodibility_k, "K factor", "Caller-provided MUSLE soil erodibility factor."),
            _assumption("slope_length_steepness_ls", request.slope_length_steepness_ls, "dimensionless", "Caller-provided MUSLE topographic factor."),
            _assumption("cover_management_c", request.cover_management_c, "dimensionless", "Caller-provided MUSLE cover-management factor."),
            _assumption("support_practice_p", request.support_practice_p, "dimensionless", "Caller-provided MUSLE support-practice factor."),
        ],
        provenance=provenance_builder.bundle(_method_sources(provenance_builder, "musle")),
        quality_flags=_zero_factor_flags(factors),
        limitations=_screening_limitations(),
        handoff_notes=[
            "Use this event sediment-yield estimate as the sediment input to the chemical-load bridge when topsoil concentration and delivery assumptions are available.",
            "Calibrate runoff and peak-flow inputs externally for decision-facing watershed work.",
        ],
    )


def estimate_sediment_associated_chemical_load(
    request: EstimateSedimentAssociatedChemicalLoadRequest,
    provenance_builder: ProvenanceBuilder,
) -> SedimentAssociatedChemicalLoadResult:
    load_kg = (
        request.soil_concentration_mg_kg
        * request.sediment_yield_t
        * 0.001
        * request.sediment_delivery_ratio
        * request.particle_bound_availability_fraction
    )
    return SedimentAssociatedChemicalLoadResult(
        sediment_associated_load_kg=load_kg,
        calculation_trace=CalculationTrace(
            equation_id="sediment_associated_chemical_load_screening_v1",
            equation_text=(
                "load_kg = soil_concentration_mg_kg * sediment_yield_t * 0.001 "
                "* sediment_delivery_ratio * particle_bound_availability_fraction"
            ),
            resolved_terms=[
                CalculationTraceTerm(name="soil_concentration_mg_kg", value=request.soil_concentration_mg_kg, unit="mg/kg"),
                CalculationTraceTerm(name="sediment_yield_t", value=request.sediment_yield_t, unit="t"),
                CalculationTraceTerm(name="mg_per_kg_t_to_kg_factor", value=0.001, unit="kg per (mg/kg * t)"),
                CalculationTraceTerm(name="sediment_delivery_ratio", value=request.sediment_delivery_ratio),
                CalculationTraceTerm(name="particle_bound_availability_fraction", value=request.particle_bound_availability_fraction),
                CalculationTraceTerm(name="sediment_associated_load", value=load_kg, unit="kg"),
            ],
            notes=[
                "The 0.001 factor converts mg/kg times metric tons of sediment to kg of chemical.",
                "Delivery and availability fractions are explicit caller assumptions in v1.",
            ],
        ),
        assumptions=[
            _assumption("soil_concentration_mg_kg", request.soil_concentration_mg_kg, "mg/kg", "Caller-provided chemical concentration in erodible soil."),
            _assumption("sediment_yield_t", request.sediment_yield_t, "t", "Caller-provided or upstream-estimated sediment yield."),
            _assumption("sediment_delivery_ratio", request.sediment_delivery_ratio, "fraction", "Caller-provided fraction of mobilized sediment delivered to the receiving pathway."),
            _assumption("particle_bound_availability_fraction", request.particle_bound_availability_fraction, "fraction", "Caller-provided particle-bound availability or correction fraction."),
        ],
        provenance=provenance_builder.bundle(
            [
                *_method_sources(provenance_builder, "musle"),
                *_method_sources(provenance_builder, "sediment_associated_chemical_load"),
            ]
        ),
        quality_flags=_zero_factor_flags(
            {
                "soil_concentration_mg_kg": request.soil_concentration_mg_kg,
                "sediment_yield_t": request.sediment_yield_t,
                "sediment_delivery_ratio": request.sediment_delivery_ratio,
                "particle_bound_availability_fraction": request.particle_bound_availability_fraction,
            }
        ),
        limitations=_screening_limitations(includes_chemical_load=True),
        handoff_notes=[
            "This is a sediment-associated load handoff, not a receiving-water concentration.",
            "Downstream exposure or surface-water modules must add receiving-environment dilution, timing, bioavailability, and endpoint-specific assumptions.",
        ],
    )


def _normalized_parameter_name(name: str) -> str:
    return "".join(char for char in name.lower() if char.isalnum())


def screen_erosion_transport_relevance(
    request: ScreenErosionTransportRelevanceRequest,
    provenance_builder: ProvenanceBuilder,
) -> ErosionTransportRelevanceResult:
    scenario = request.scenario
    driver_lines: list[str] = []
    quality_flags: list[QualityFlag] = []
    high_signal = False
    medium_signal = False
    evidence_seen = False

    substance_class = scenario.chemical_identity.get("substance_class", "")
    normalized_class = substance_class.casefold()
    if any(token in normalized_class for token in PARTICLE_ASSOCIATED_CLASS_TOKENS):
        evidence_seen = True
        high_signal = True
        driver_lines.append(
            f"Substance class '{substance_class}' is treated as particle-associated for screening."
        )
    elif substance_class:
        driver_lines.append(
            f"Substance class '{substance_class}' does not by itself trigger particle-bound transport in v1 screening."
        )

    for record in scenario.parameter_records:
        parameter_name = _normalized_parameter_name(record.parameter)
        if parameter_name in {
            "koc",
            "koclkg",
            "kd",
            "kdlkg",
            "organiccarbonpartitioncoefficientlkg",
            "soilwaterpartitioncoefficientlkg",
        }:
            evidence_seen = True
            if record.value >= 1000.0:
                high_signal = True
                driver_lines.append(
                    f"{record.parameter} {record.value:g} {record.unit} is at or above "
                    "the high particle-bound screening threshold."
                )
            elif record.value >= 100.0:
                medium_signal = True
                driver_lines.append(
                    f"{record.parameter} {record.value:g} {record.unit} is in the "
                    "medium particle-bound screening range."
                )
            else:
                driver_lines.append(
                    f"{record.parameter} {record.value:g} {record.unit} is below "
                    "the medium particle-bound screening threshold."
                )
        if parameter_name in {"logkow", "logp"}:
            evidence_seen = True
            if record.value >= 4.0:
                high_signal = True
                driver_lines.append(f"logKow {record.value:g} is at or above the high particle-bound screening threshold.")
            elif record.value >= 3.0:
                medium_signal = True
                driver_lines.append(f"logKow {record.value:g} is in the medium particle-bound screening range.")
            else:
                driver_lines.append(f"logKow {record.value:g} is below the medium particle-bound screening threshold.")

    if high_signal:
        relevance = ErosionTransportRelevanceLevel.HIGH
        plausible = True
        recommended_next_steps = [
            "Use MUSLE for event sediment yield when runoff volume and peak runoff rate are available.",
            "Use the sediment-associated chemical-load bridge when topsoil concentration and delivery assumptions are available.",
        ]
    elif medium_signal:
        relevance = ErosionTransportRelevanceLevel.MEDIUM
        plausible = True
        recommended_next_steps = [
            "Consider MUSLE event sediment-yield screening for rainfall-runoff scenarios.",
            "Check whether site-specific Koc/Kd/logKow or suspended-particle evidence strengthens or weakens the particle-bound pathway.",
        ]
    elif evidence_seen:
        relevance = ErosionTransportRelevanceLevel.LOW
        plausible = False
        recommended_next_steps = [
            "Prioritize dissolved, leaching, volatilization, or degradation pathways unless erosion context is independently important.",
        ]
    else:
        relevance = ErosionTransportRelevanceLevel.UNKNOWN
        plausible = None
        driver_lines.append(
            "No Koc, logKow, or known particle-associated substance class was available for erosion-transport relevance screening."
        )
        recommended_next_steps = [
            "Add Koc, Kd, logKow, or particle-association evidence before relying on erosion-mediated chemical transport screening.",
        ]
        quality_flags.append(
            QualityFlag(
                code="missing_particle_transport_evidence",
                severity=Severity.WARNING,
                message="Particle-bound transport relevance is unknown because no supported sorption or class evidence was present.",
            )
        )

    return ErosionTransportRelevanceResult(
        scenario_id=scenario.scenario_id,
        relevance_level=relevance,
        particle_bound_transport_plausible=plausible,
        driver_lines=driver_lines,
        recommended_next_steps=recommended_next_steps,
        provenance=provenance_builder.bundle(_method_sources(provenance_builder, "erosion_transport_relevance")),
        quality_flags=quality_flags,
        limitations=_screening_limitations(includes_chemical_load=True),
    )
