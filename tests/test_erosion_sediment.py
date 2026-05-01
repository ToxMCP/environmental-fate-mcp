from pathlib import Path

import pytest

from fate_mcp.errors import FateValidationError
from fate_mcp.integrations import (
    assess_erosion_sediment_validation_fit,
    build_erosion_sediment_validation_case,
    estimate_event_sediment_yield_musle,
    estimate_sediment_associated_chemical_load,
    estimate_soil_loss_rusle,
    screen_erosion_transport_relevance,
)
from fate_mcp.models import (
    AssessErosionSedimentValidationFitRequest,
    BuildErosionSedimentValidationCaseRequest,
    BuildEnvironmentalReleaseScenarioRequest,
    ErosionSedimentValidationFitClassification,
    EstimateEventSedimentYieldMusleRequest,
    EstimateSedimentAssociatedChemicalLoadRequest,
    EstimateSoilLossRusleRequest,
    FateParameterRecord,
    Media,
    ObservedErosionSedimentValidationRecord,
    PredictedErosionSedimentValidationRecord,
    ReleaseFraction,
    ScreenErosionTransportRelevanceRequest,
    SourceClassification,
)
from fate_mcp.runtime import FateRuntime


REPO_ROOT = Path(__file__).resolve().parents[1]


def _runtime() -> FateRuntime:
    return FateRuntime(REPO_ROOT)


def _scenario_with_parameter(parameter: str | None = None, value: float | None = None):
    parameter_records = []
    if parameter is not None and value is not None:
        parameter_records.append(
            FateParameterRecord(
                parameter=parameter,
                value=value,
                unit="L/kg" if parameter.lower().startswith(("koc", "kd")) else "log10",
                source_classification=SourceClassification.USER_INPUT,
                rationale="Test particle-bound transport descriptor.",
            )
        )
    return _runtime().build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(
            chemical_identity={
                "preferredName": "Example substance",
                "substance_class": "organic chemical",
            },
            total_release_mass_kg=1.0,
            release_fractions=[ReleaseFraction(medium=Media.SOIL, fraction=1.0)],
            duration_days=1.0,
            parameter_records=parameter_records,
        )
    )


def _observed_record(
    record_id: str,
    value: float,
    quantity: str = "event_sediment_yield_t",
) -> ObservedErosionSedimentValidationRecord:
    return ObservedErosionSedimentValidationRecord(
        record_id=record_id,
        quantity=quantity,
        observed_value=value,
        unit="t/event" if quantity == "event_sediment_yield_t" else "kg",
        context_label="test validation record",
    )


def _predicted_record(
    record_id: str,
    value: float,
    quantity: str = "event_sediment_yield_t",
) -> PredictedErosionSedimentValidationRecord:
    return PredictedErosionSedimentValidationRecord(
        record_id=record_id,
        quantity=quantity,
        predicted_value=value,
        unit="t/event" if quantity == "event_sediment_yield_t" else "kg",
        method_id="musle",
    )


def _validation_case(
    observed_values: list[float],
    predicted_values: list[float],
):
    runtime = _runtime()
    request = BuildErosionSedimentValidationCaseRequest(
        observed_records=[
            _observed_record(f"record-{index}", value)
            for index, value in enumerate(observed_values, start=1)
        ],
        predicted_records=[
            _predicted_record(f"record-{index}", value)
            for index, value in enumerate(predicted_values, start=1)
        ],
    )
    return build_erosion_sediment_validation_case(request, runtime.provenance)


def test_rusle_calculation_returns_rate_and_area_total() -> None:
    runtime = _runtime()
    request = EstimateSoilLossRusleRequest(
        rainfall_erosivity_r=150.0,
        soil_erodibility_k=0.28,
        slope_length_steepness_ls=1.6,
        cover_management_c=0.12,
        support_practice_p=0.8,
        area_ha=2.5,
    )
    result = estimate_soil_loss_rusle(request, runtime.provenance)

    assert result.annual_soil_loss_t_ha_yr == pytest.approx(6.4512)
    assert result.total_soil_loss_t_yr == pytest.approx(16.128)
    assert result.calculation_trace.equation_id == "rusle_v1"
    assert result.provenance.source_references[0].source_id == "usda.nrcs.rusle.efotg"


def test_musle_calculation_uses_caller_supplied_hydrology() -> None:
    runtime = _runtime()
    request = EstimateEventSedimentYieldMusleRequest(
        runoff_volume_m3=1200.0,
        peak_runoff_rate_m3_s=2.4,
        soil_erodibility_k=0.28,
        slope_length_steepness_ls=1.6,
        cover_management_c=0.12,
        support_practice_p=0.8,
    )
    result = estimate_event_sediment_yield_musle(request, runtime.provenance)
    expected = 11.8 * (1200.0 * 2.4) ** 0.56 * 0.28 * 1.6 * 0.12 * 0.8

    assert result.sediment_yield_t_event == pytest.approx(expected)
    assert result.calculation_trace.equation_id == "musle_metric_v1"
    assert any("does not compute rainfall-runoff" in note for note in result.calculation_trace.notes)


def test_sediment_associated_chemical_load_conversion() -> None:
    runtime = _runtime()
    request = EstimateSedimentAssociatedChemicalLoadRequest(
        soil_concentration_mg_kg=2.5,
        sediment_yield_t=40.0,
        sediment_delivery_ratio=0.35,
        particle_bound_availability_fraction=0.75,
    )
    result = estimate_sediment_associated_chemical_load(request, runtime.provenance)

    assert result.sediment_associated_load_kg == pytest.approx(0.02625)
    assert result.calculation_trace.equation_id == "sediment_associated_chemical_load_screening_v1"
    assert any("not a receiving-water concentration" in note for note in result.handoff_notes)


def test_zero_inputs_return_zero_with_quality_flag() -> None:
    runtime = _runtime()
    rusle = estimate_soil_loss_rusle(
        EstimateSoilLossRusleRequest(
            rainfall_erosivity_r=0.0,
            soil_erodibility_k=0.28,
            slope_length_steepness_ls=1.6,
            cover_management_c=0.12,
            support_practice_p=0.8,
        ),
        runtime.provenance,
    )
    musle = estimate_event_sediment_yield_musle(
        EstimateEventSedimentYieldMusleRequest(
            runoff_volume_m3=0.0,
            peak_runoff_rate_m3_s=2.4,
            soil_erodibility_k=0.28,
            slope_length_steepness_ls=1.6,
            cover_management_c=0.12,
            support_practice_p=0.8,
        ),
        runtime.provenance,
    )

    assert rusle.annual_soil_loss_t_ha_yr == 0.0
    assert musle.sediment_yield_t_event == 0.0
    assert rusle.quality_flags[0].code == "zero_erosion_transport_factor"
    assert musle.quality_flags[0].code == "zero_erosion_transport_factor"


def test_input_validation_rejects_nonfinite_and_out_of_range_values() -> None:
    with pytest.raises(ValueError, match="must be finite"):
        EstimateSoilLossRusleRequest(
            rainfall_erosivity_r=float("inf"),
            soil_erodibility_k=0.28,
            slope_length_steepness_ls=1.6,
            cover_management_c=0.12,
            support_practice_p=0.8,
        )
    with pytest.raises(ValueError):
        EstimateSedimentAssociatedChemicalLoadRequest(
            soil_concentration_mg_kg=2.5,
            sediment_yield_t=40.0,
            sediment_delivery_ratio=1.1,
            particle_bound_availability_fraction=0.75,
        )


def test_erosion_transport_relevance_thresholds() -> None:
    runtime = _runtime()
    high = screen_erosion_transport_relevance(
        ScreenErosionTransportRelevanceRequest(scenario=_scenario_with_parameter("koc", 1200.0)),
        runtime.provenance,
    )
    medium = screen_erosion_transport_relevance(
        ScreenErosionTransportRelevanceRequest(scenario=_scenario_with_parameter("log_kow", 3.4)),
        runtime.provenance,
    )
    low = screen_erosion_transport_relevance(
        ScreenErosionTransportRelevanceRequest(scenario=_scenario_with_parameter("log_kow", 2.2)),
        runtime.provenance,
    )
    unknown = screen_erosion_transport_relevance(
        ScreenErosionTransportRelevanceRequest(scenario=_scenario_with_parameter()),
        runtime.provenance,
    )

    assert high.relevance_level.value == "high"
    assert medium.relevance_level.value == "medium"
    assert low.relevance_level.value == "low"
    assert unknown.relevance_level.value == "unknown"
    assert unknown.particle_bound_transport_plausible is None
    assert unknown.quality_flags[0].code == "missing_particle_transport_evidence"


def test_validation_case_construction_preserves_pairing_and_boundaries() -> None:
    runtime = _runtime()
    request = BuildErosionSedimentValidationCaseRequest(
        observed_records=[
            _observed_record("event-1", 10.0),
            _observed_record("event-2", 20.0),
            _observed_record("event-3", 30.0),
        ],
        predicted_records=[
            _predicted_record("event-1", 11.0),
            _predicted_record("event-2", 18.0),
            _predicted_record("event-extra", 30.0),
        ],
    )

    result = build_erosion_sediment_validation_case(request, runtime.provenance)

    assert result.validation_profile_id == "erosion_sediment_screening_validation_v1"
    assert result.matched_record_ids == ["event-1", "event-2"]
    assert result.unmatched_observed_record_ids == ["event-3"]
    assert result.unmatched_predicted_record_ids == ["event-extra"]
    assert result.provenance.source_references[0].source_id.startswith("fate_mcp.")
    assert any(note.code == "no_validation_parameter_adjustment" for note in result.limitations)
    assert result.quality_flags[0].code == "unmatched_erosion_sediment_validation_records"


def test_validation_case_flags_quantity_mismatch() -> None:
    runtime = _runtime()
    request = BuildErosionSedimentValidationCaseRequest(
        observed_records=[_observed_record("event-1", 10.0)],
        predicted_records=[
            _predicted_record("event-1", 0.02, quantity="sediment_associated_load_kg")
        ],
    )

    result = build_erosion_sediment_validation_case(request, runtime.provenance)

    assert result.matched_record_ids == []
    assert result.quantity_mismatch_record_ids == ["event-1"]
    assert any(
        flag.code == "erosion_sediment_validation_quantity_mismatch"
        for flag in result.quality_flags
    )


def test_validation_fit_classifies_good_plausible_weak_and_insufficient_cases() -> None:
    runtime = _runtime()
    good = assess_erosion_sediment_validation_fit(
        AssessErosionSedimentValidationFitRequest(
            validation_case=_validation_case([10.0, 20.0, 30.0, 40.0, 50.0], [10.0, 20.0, 30.0, 40.0, 50.0])
        ),
        runtime.provenance,
    )
    plausible = assess_erosion_sediment_validation_fit(
        AssessErosionSedimentValidationFitRequest(
            validation_case=_validation_case([10.0, 20.0, 30.0], [14.0, 28.0, 42.0])
        ),
        runtime.provenance,
    )
    weak = assess_erosion_sediment_validation_fit(
        AssessErosionSedimentValidationFitRequest(
            validation_case=_validation_case([10.0, 20.0, 30.0], [30.0, 60.0, 90.0])
        ),
        runtime.provenance,
    )
    insufficient = assess_erosion_sediment_validation_fit(
        AssessErosionSedimentValidationFitRequest(
            validation_case=_validation_case([10.0, 20.0], [10.0, 20.0])
        ),
        runtime.provenance,
    )

    assert good.classification == ErosionSedimentValidationFitClassification.GOOD_SCREENING_FIT
    assert good.metrics.matched_count == 5
    assert good.metrics.mean_bias == pytest.approx(0.0)
    assert good.metrics.factor_of_two_fraction == pytest.approx(1.0)
    assert plausible.classification == ErosionSedimentValidationFitClassification.SCREENING_PLAUSIBLE
    assert weak.classification == ErosionSedimentValidationFitClassification.WEAK_FIT
    assert insufficient.classification == ErosionSedimentValidationFitClassification.INSUFFICIENT_EVIDENCE


def test_validation_fit_handles_zero_observed_mape_without_division_error() -> None:
    runtime = _runtime()
    result = assess_erosion_sediment_validation_fit(
        AssessErosionSedimentValidationFitRequest(
            validation_case=_validation_case([0.0, 0.0, 0.0], [0.0, 0.0, 0.0])
        ),
        runtime.provenance,
    )

    assert result.metrics.mean_absolute_percentage_error_fraction is None
    assert result.metrics.normalized_bias is None
    assert result.metrics.factor_of_two_fraction == pytest.approx(1.0)
    assert result.classification == ErosionSedimentValidationFitClassification.INSUFFICIENT_EVIDENCE
    assert any(flag.code == "mape_unavailable_for_zero_observed_records" for flag in result.quality_flags)


def test_validation_fit_rejects_zero_matched_records() -> None:
    runtime = _runtime()
    validation_case = build_erosion_sediment_validation_case(
        BuildErosionSedimentValidationCaseRequest(
            observed_records=[_observed_record("observed-only", 10.0)],
            predicted_records=[_predicted_record("predicted-only", 10.0)],
        ),
        runtime.provenance,
    )

    with pytest.raises(FateValidationError) as exc_info:
        assess_erosion_sediment_validation_fit(
            AssessErosionSedimentValidationFitRequest(validation_case=validation_case),
            runtime.provenance,
        )

    assert exc_info.value.payload.code == "erosion_sediment_validation_no_matched_records"


def test_validation_records_reject_nonfinite_and_out_of_range_values() -> None:
    with pytest.raises(ValueError, match="must be finite"):
        ObservedErosionSedimentValidationRecord(
            record_id="event-1",
            quantity="event_sediment_yield_t",
            observed_value=float("nan"),
            unit="t/event",
        )


def test_validation_demo_pack_cases_match_expected_classifications() -> None:
    runtime = _runtime()
    manifest = runtime.defaults.erosion_sediment_validation_demo_pack_manifest()

    assert manifest.demo_case_count == 4
    assert "synthetic" in " ".join(manifest.limitations).lower()
    assert "not field validation" in " ".join(manifest.limitations).lower()

    results = {}
    for demo_case in manifest.demo_cases:
        validation_case = build_erosion_sediment_validation_case(
            BuildErosionSedimentValidationCaseRequest(
                observed_records=demo_case.observed_records,
                predicted_records=demo_case.predicted_records,
                validation_profile_id=demo_case.validation_profile_id,
            ),
            runtime.provenance,
        )
        fit = assess_erosion_sediment_validation_fit(
            AssessErosionSedimentValidationFitRequest(validation_case=validation_case),
            runtime.provenance,
        )
        results[demo_case.demo_case_id] = fit.classification

    assert results == {
        "perfect_fit": ErosionSedimentValidationFitClassification.GOOD_SCREENING_FIT,
        "screening_plausible": ErosionSedimentValidationFitClassification.SCREENING_PLAUSIBLE,
        "weak_fit": ErosionSedimentValidationFitClassification.WEAK_FIT,
        "insufficient_evidence": ErosionSedimentValidationFitClassification.INSUFFICIENT_EVIDENCE,
    }
    with pytest.raises(ValueError):
        PredictedErosionSedimentValidationRecord(
            record_id="event-1",
            quantity="event_sediment_yield_t",
            predicted_value=-1.0,
            unit="t/event",
        )
