from __future__ import annotations

from collections import defaultdict
import json
from pathlib import Path

from fate_mcp.defaults import DefaultsRegistry
from fate_mcp.models import (
    BuildEnvironmentalReleaseScenarioRequest,
    FateModelRunOptions,
    FitForPurpose,
    ModelFamily,
    ScientificValidationClaimCoverageManifest,
    ScientificValidationClaimCoverageRecord,
)
from fate_mcp.plugins.external_result_adapter import load_external_payload, normalize_external_payload
from fate_mcp.runtime import FateRuntime


BENCHMARK_FIXTURES = [
    {
        "name": "air_reference_chemical_style_fixture",
        "category": "reference_chemical_style",
        "validation_tier": "reference_style",
        "scientific_basis": "Hand-worked finite-duration first-order single-medium air screening equation using governed ambient-air volume and half-life defaults.",
        "reference_type": "hand_worked_screening_equation",
        "expected_behavior": "End-of-duration air concentration matches the documented finite-duration first-order screening equation.",
        "tolerance_rationale": "Reference mass-balance kernel is deterministic, so floating-point precision is the only tolerated deviation.",
        "tolerance": 1e-12,
        "scientific_claim_ids": ["reference_air_finite_duration_first_order_v1"],
        "scenario": {
            "chemical_identity": {"preferredName": "Benchmark air"},
            "total_release_mass_kg": 10.0,
            "release_fractions": [{"medium": "air", "fraction": 1.0}],
            "duration_days": 10.0,
        },
        "expected_surfaces": [
            {
                "medium": "air",
                "compartment": "ambient_air",
                "value": 0.0027952216417223663,
                "unit": "mg/m3",
            }
        ],
        "expected_trace_terms": [
            {
                "medium": "air",
                "compartment": "ambient_air",
                "terms": {
                    "decay_constant_per_day": 0.34657359027997264,
                    "emitted_mass_to_elapsed_mg": 10000000.0,
                    "cumulative_degraded_mass_mg": 7204778.358277633,
                    "mass_balance_closure_error_mg": 9.313225746154785e-10,
                },
                "tolerance": 1e-12,
            }
        ],
    },
    {
        "name": "water_reference_chemical_style_fixture",
        "category": "reference_chemical_style",
        "validation_tier": "reference_style",
        "scientific_basis": "Hand-worked finite-duration first-order single-medium water screening equation using governed surface-water volume and half-life defaults.",
        "reference_type": "hand_worked_screening_equation",
        "expected_behavior": "End-of-duration surface-water concentration matches the documented finite-duration first-order screening equation.",
        "tolerance_rationale": "Reference mass-balance kernel is deterministic, so floating-point precision is the only tolerated deviation.",
        "tolerance": 1e-12,
        "scientific_claim_ids": ["reference_water_finite_duration_first_order_v1"],
        "scenario": {
            "chemical_identity": {"preferredName": "Benchmark water"},
            "total_release_mass_kg": 10.0,
            "release_fractions": [{"medium": "water", "fraction": 1.0}],
            "duration_days": 15.0,
        },
        "expected_surfaces": [
            {
                "medium": "water",
                "compartment": "surface_water",
                "value": 1.4426950408889635e-05,
                "unit": "mg/L",
            }
        ],
        "expected_trace_terms": [
            {
                "medium": "water",
                "compartment": "surface_water",
                "terms": {
                    "decay_constant_per_day": 0.046209812037329684,
                    "emitted_mass_to_elapsed_mg": 10000000.0,
                    "cumulative_degraded_mass_mg": 2786524.795555182,
                    "mass_balance_closure_error_mg": 9.313225746154785e-10,
                },
                "tolerance": 1e-12,
            }
        ],
    },
    {
        "name": "soil_reference_chemical_style_fixture",
        "category": "reference_chemical_style",
        "validation_tier": "reference_style",
        "scientific_basis": "Hand-worked finite-duration first-order single-medium soil screening equation using governed soil-mass and half-life defaults.",
        "reference_type": "hand_worked_screening_equation",
        "expected_behavior": "End-of-duration soil concentration matches the documented finite-duration first-order screening equation.",
        "tolerance_rationale": "Reference mass-balance kernel is deterministic, so floating-point precision is the only tolerated deviation.",
        "tolerance": 1e-12,
        "scientific_claim_ids": ["reference_soil_finite_duration_first_order_v1"],
        "scenario": {
            "chemical_identity": {"preferredName": "Benchmark soil"},
            "total_release_mass_kg": 10.0,
            "release_fractions": [{"medium": "soil", "fraction": 1.0}],
            "duration_days": 30.0,
        },
        "expected_surfaces": [
            {
                "medium": "soil",
                "compartment": "agricultural_soil",
                "value": 0.0028853900817779267,
                "unit": "mg/kg",
            }
        ],
        "expected_trace_terms": [
            {
                "medium": "soil",
                "compartment": "agricultural_soil",
                "terms": {
                    "decay_constant_per_day": 0.023104906018664842,
                    "emitted_mass_to_elapsed_mg": 10000000.0,
                    "cumulative_degraded_mass_mg": 2786524.795555182,
                    "mass_balance_closure_error_mg": 1.862645149230957e-09,
                },
                "tolerance": 1e-12,
            }
        ],
    },
    {
        "name": "sediment_reference_chemical_style_fixture",
        "category": "reference_chemical_style",
        "validation_tier": "reference_style",
        "scientific_basis": "Hand-worked finite-duration first-order single-medium sediment screening equation using governed sediment-mass and half-life defaults.",
        "reference_type": "hand_worked_screening_equation",
        "expected_behavior": "End-of-duration sediment concentration matches the documented finite-duration first-order screening equation.",
        "tolerance_rationale": "Reference mass-balance kernel is deterministic, so floating-point precision is the only tolerated deviation.",
        "tolerance": 1e-12,
        "scientific_claim_ids": ["reference_sediment_finite_duration_first_order_v1"],
        "scenario": {
            "chemical_identity": {"preferredName": "Benchmark sediment"},
            "total_release_mass_kg": 10.0,
            "release_fractions": [{"medium": "sediment", "fraction": 1.0}],
            "duration_days": 45.0,
        },
        "expected_surfaces": [
            {
                "medium": "sediment",
                "compartment": "freshwater_sediment",
                "value": 0.009016844005556022,
                "unit": "mg/kg",
            }
        ],
        "expected_trace_terms": [
            {
                "medium": "sediment",
                "compartment": "freshwater_sediment",
                "terms": {
                    "decay_constant_per_day": 0.015403270679109895,
                    "emitted_mass_to_elapsed_mg": 10000000.0,
                    "cumulative_degraded_mass_mg": 2786524.7955551823,
                    "mass_balance_closure_error_mg": -4.656612873077393e-10,
                },
                "tolerance": 1e-12,
            }
        ],
    },
    {
        "name": "reference_water_no_decay_limit_branch_fixture",
        "category": "edge_condition_anchor",
        "validation_tier": "edge_condition",
        "scientific_basis": "Hand-worked reference water screening case with an effectively infinite half-life, anchoring the explicit no-decay-limit branch of the finite-duration kernel.",
        "reference_type": "hand_worked_no_decay_limit_fixture",
        "expected_behavior": "Reference water concentration follows the no-decay linear accumulation limit when the governed half-life is effectively infinite relative to the branch threshold.",
        "tolerance_rationale": "The no-decay branch is deterministic and analytically traceable to the linear accumulation limit of the same finite-duration release equation.",
        "tolerance": 1e-12,
        "scientific_claim_ids": ["reference_water_finite_duration_first_order_v1"],
        "scenario": {
            "chemical_identity": {
                "preferredName": "Benchmark water no-decay branch",
                "substance_class": "organic chemical"
            },
            "total_release_mass_kg": 10.0,
            "release_fractions": [{"medium": "water", "fraction": 1.0}],
            "duration_days": 1.0,
            "parameter_records": [
                {
                    "parameter": "water_half_life_days",
                    "value": 10000000000000.0,
                    "unit": "day",
                    "source_classification": "user_input",
                    "rationale": "Benchmark effective no-decay branch trigger."
                }
            ]
        },
        "expected_surfaces": [
            {
                "medium": "water",
                "compartment": "surface_water",
                "value": 2e-05,
                "unit": "mg/L"
            }
        ],
        "expected_trace_terms": [
            {
                "medium": "water",
                "compartment": "surface_water",
                "terms": {
                    "decay_constant_per_day": 6.931471805599453e-14,
                    "emitted_mass_to_elapsed_mg": 10000000.0,
                    "cumulative_degraded_mass_mg": 3.465735902799726e-07,
                    "mass_balance_closure_error_mg": -3.465735902799726e-07
                },
                "tolerance": 1e-12
            }
        ]
    },
    {
        "name": "reference_water_temperature_correction_reference_fixture",
        "category": "reference_chemical_style",
        "validation_tier": "reference_style",
        "scientific_basis": "Hand-worked reference water screening case at a governed non-reference temperature, anchoring the Q10 temperature-correction branch with explicit corrected half-life tracing.",
        "reference_type": "hand_worked_temperature_correction_fixture",
        "expected_behavior": "Reference water concentration reflects the governed Q10 temperature correction, with a lower scenario temperature lengthening half-life and increasing retained concentration.",
        "tolerance_rationale": "The governed temperature-correction branch remains a deterministic closed-form transformation of the same finite-duration first-order release equation.",
        "tolerance": 1e-12,
        "scientific_claim_ids": ["reference_water_finite_duration_first_order_v1"],
        "scenario": {
            "chemical_identity": {
                "preferredName": "Benchmark water temperature correction",
                "substance_class": "organic chemical"
            },
            "total_release_mass_kg": 10.0,
            "release_fractions": [{"medium": "water", "fraction": 1.0}],
            "duration_days": 15.0,
            "temperature_c": 15.0
        },
        "expected_surfaces": [
            {
                "medium": "water",
                "compartment": "surface_water",
                "value": 1.6902223771686956e-05,
                "unit": "mg/L"
            }
        ],
        "expected_trace_terms": [
            {
                "medium": "water",
                "compartment": "surface_water",
                "terms": {
                    "temperature_correction_factor": 0.5,
                    "temperature_corrected_half_life_days": 30.0,
                    "decay_constant_per_day": 0.023104906018664842,
                    "cumulative_degraded_mass_mg": 1548888.114156522,
                    "mass_balance_closure_error_mg": -2.3283064365386963e-10
                },
                "tolerance": 1e-12
            }
        ]
    },
    {
        "name": "reference_air_capacity_sensitivity_fixture",
        "category": "parameter_override_sensitivity",
        "validation_tier": "sensitivity",
        "scientific_basis": "Hand-worked finite-duration air screening case with an explicit ambient-air-volume override, corroborating inverse scaling against compartment capacity in the baseline reference kernel.",
        "reference_type": "hand_worked_capacity_sensitivity_fixture",
        "expected_behavior": "Air concentration increases proportionally when the governed ambient-air volume is overridden downward under the same finite-duration first-order equation.",
        "tolerance_rationale": "Capacity scaling remains analytically traceable because only the compartment capacity term changes in the deterministic reference equation.",
        "tolerance": 1e-12,
        "scientific_claim_ids": [
            "reference_air_finite_duration_first_order_v1",
            "reference_parameter_override_application_v1",
        ],
        "scenario": {
            "chemical_identity": {"preferredName": "Benchmark air capacity sensitivity"},
            "total_release_mass_kg": 10.0,
            "release_fractions": [{"medium": "air", "fraction": 1.0}],
            "duration_days": 10.0,
            "parameter_records": [
                {
                    "parameter": "ambient_air_volume_m3",
                    "value": 5e8,
                    "unit": "m3",
                    "source_classification": "user_input",
                    "rationale": "Benchmark ambient-air capacity override.",
                }
            ],
        },
        "expected_surfaces": [
            {
                "medium": "air",
                "compartment": "ambient_air",
                "value": 0.005590443283444733,
                "unit": "mg/m3",
            }
        ],
    },
    {
        "name": "reference_water_capacity_sensitivity_fixture",
        "category": "parameter_override_sensitivity",
        "validation_tier": "sensitivity",
        "scientific_basis": "Hand-worked finite-duration water screening case with an explicit surface-water-volume override, corroborating inverse scaling against compartment capacity in the baseline reference kernel.",
        "reference_type": "hand_worked_capacity_sensitivity_fixture",
        "expected_behavior": "Water concentration increases proportionally when the governed surface-water volume is overridden downward under the same finite-duration first-order equation.",
        "tolerance_rationale": "Capacity scaling remains analytically traceable because only the compartment capacity term changes in the deterministic reference equation.",
        "tolerance": 1e-12,
        "scientific_claim_ids": [
            "reference_water_finite_duration_first_order_v1",
            "reference_parameter_override_application_v1",
        ],
        "scenario": {
            "chemical_identity": {"preferredName": "Benchmark water capacity sensitivity"},
            "total_release_mass_kg": 10.0,
            "release_fractions": [{"medium": "water", "fraction": 1.0}],
            "duration_days": 15.0,
            "parameter_records": [
                {
                    "parameter": "surface_water_volume_m3",
                    "value": 2.5e8,
                    "unit": "m3",
                    "source_classification": "user_input",
                    "rationale": "Benchmark surface-water capacity override.",
                }
            ],
        },
        "expected_surfaces": [
            {
                "medium": "water",
                "compartment": "surface_water",
                "value": 2.885390081777927e-05,
                "unit": "mg/L",
            }
        ],
    },
    {
        "name": "reference_soil_capacity_sensitivity_fixture",
        "category": "parameter_override_sensitivity",
        "validation_tier": "sensitivity",
        "scientific_basis": "Hand-worked finite-duration soil screening case with an explicit soil-mass override, corroborating inverse scaling against compartment capacity in the baseline reference kernel.",
        "reference_type": "hand_worked_capacity_sensitivity_fixture",
        "expected_behavior": "Soil concentration increases proportionally when the governed soil mass is overridden downward under the same finite-duration first-order equation.",
        "tolerance_rationale": "Capacity scaling remains analytically traceable because only the compartment capacity term changes in the deterministic reference equation.",
        "tolerance": 1e-12,
        "scientific_claim_ids": [
            "reference_soil_finite_duration_first_order_v1",
            "reference_parameter_override_application_v1",
        ],
        "scenario": {
            "chemical_identity": {"preferredName": "Benchmark soil capacity sensitivity"},
            "total_release_mass_kg": 10.0,
            "release_fractions": [{"medium": "soil", "fraction": 1.0}],
            "duration_days": 30.0,
            "parameter_records": [
                {
                    "parameter": "agricultural_soil_mass_kg",
                    "value": 1e8,
                    "unit": "kg",
                    "source_classification": "user_input",
                    "rationale": "Benchmark soil-mass override.",
                }
            ],
        },
        "expected_surfaces": [
            {
                "medium": "soil",
                "compartment": "agricultural_soil",
                "value": 0.07213475204444818,
                "unit": "mg/kg",
            }
        ],
    },
    {
        "name": "reference_sediment_capacity_sensitivity_fixture",
        "category": "parameter_override_sensitivity",
        "validation_tier": "sensitivity",
        "scientific_basis": "Hand-worked finite-duration sediment screening case with an explicit sediment-mass override, corroborating inverse scaling against compartment capacity in the baseline reference kernel.",
        "reference_type": "hand_worked_capacity_sensitivity_fixture",
        "expected_behavior": "Sediment concentration increases proportionally when the governed sediment mass is overridden downward under the same finite-duration first-order equation.",
        "tolerance_rationale": "Capacity scaling remains analytically traceable because only the compartment capacity term changes in the deterministic reference equation.",
        "tolerance": 1e-12,
        "scientific_claim_ids": [
            "reference_sediment_finite_duration_first_order_v1",
            "reference_parameter_override_application_v1",
        ],
        "scenario": {
            "chemical_identity": {"preferredName": "Benchmark sediment capacity sensitivity"},
            "total_release_mass_kg": 10.0,
            "release_fractions": [{"medium": "sediment", "fraction": 1.0}],
            "duration_days": 45.0,
            "parameter_records": [
                {
                    "parameter": "freshwater_sediment_mass_kg",
                    "value": 5e7,
                    "unit": "kg",
                    "source_classification": "user_input",
                    "rationale": "Benchmark sediment-mass override.",
                }
            ],
        },
        "expected_surfaces": [
            {
                "medium": "sediment",
                "compartment": "freshwater_sediment",
                "value": 0.14426950408889636,
                "unit": "mg/kg",
            }
        ],
    },
    {
        "name": "reference_parameter_override_reference_fixture",
        "category": "parameter_override_reference_case",
        "validation_tier": "reference_style",
        "scientific_basis": "Hand-worked finite-duration air screening case with an explicit ambient-air-volume override, used as a reference-style corroboration of runtime-supported override execution in the baseline kernel.",
        "reference_type": "hand_worked_override_reference_case",
        "expected_behavior": "The baseline kernel applies an explicit capacity override exactly as declared and still matches the hand-worked finite-duration reference equation.",
        "tolerance_rationale": "The override reference case remains closed-form and deterministic even though it replaces a governed default.",
        "tolerance": 1e-12,
        "scientific_claim_ids": ["reference_parameter_override_application_v1"],
        "scenario": {
            "chemical_identity": {"preferredName": "Benchmark override reference"},
            "total_release_mass_kg": 8.0,
            "release_fractions": [{"medium": "air", "fraction": 1.0}],
            "duration_days": 12.0,
            "parameter_records": [
                {
                    "parameter": "ambient_air_volume_m3",
                    "value": 7.5e8,
                    "unit": "m3",
                    "source_classification": "user_input",
                    "rationale": "Benchmark override reference case.",
                }
            ],
        },
        "expected_surfaces": [
            {
                "medium": "air",
                "compartment": "ambient_air",
                "value": 0.002524716321555686,
                "unit": "mg/m3",
            }
        ],
    },
    {
        "name": "advective_water_reference_chemical_style_fixture",
        "category": "advective_reference_chemical_style",
        "validation_tier": "reference_style",
        "scientific_basis": "Hand-worked finite-duration first-order single-medium water screening equation using governed surface-water volume, water half-life, and residence-time defaults.",
        "reference_type": "hand_worked_advective_screening_equation",
        "expected_behavior": "End-of-duration surface-water concentration matches the documented finite-duration first-order screening equation with degradation plus advective clearance.",
        "tolerance_rationale": "Advective screening kernel is deterministic, so floating-point precision is the only tolerated deviation.",
        "tolerance": 1e-12,
        "scientific_claim_ids": ["advective_water_finite_duration_first_order_v1"],
        "scenario": {
            "chemical_identity": {"preferredName": "Benchmark advective water"},
            "total_release_mass_kg": 10.0,
            "release_fractions": [{"medium": "water", "fraction": 1.0}],
            "duration_days": 15.0
        },
        "run_options": {
            "model_family": "advective_screening_mass_balance"
        },
        "expected_surfaces": [
            {
                "medium": "water",
                "compartment": "surface_water",
                "value": 1.0585430701990208e-05,
                "unit": "mg/L"
            }
        ]
    },
    {
        "name": "advective_degradation_dominant_loss_share_anchor_fixture",
        "category": "advective_loss_dominance_anchor",
        "validation_tier": "edge_condition",
        "scientific_basis": "Hand-worked advective water screening case with short half-life and long residence time, anchoring a degradation-dominant combined-loss regime in the trace decomposition.",
        "reference_type": "hand_worked_advective_loss_dominance_anchor",
        "expected_behavior": "The advective trace reports degradation as the dominant loss share when half-life is short relative to residence time.",
        "tolerance_rationale": "The dominance split is analytically traceable because the governed trace exposes the exact degradation, clearance, and total-loss constants.",
        "tolerance": 1e-12,
        "scientific_claim_ids": [
            "advective_degradation_dominant_loss_share_v1",
            "advective_cumulative_mass_balance_closure_v1",
        ],
        "scenario": {
            "chemical_identity": {"preferredName": "Benchmark advective degradation dominance"},
            "total_release_mass_kg": 10.0,
            "release_fractions": [{"medium": "water", "fraction": 1.0}],
            "duration_days": 20.0,
            "parameter_records": [
                {
                    "parameter": "water_half_life_days",
                    "value": 2.0,
                    "unit": "day",
                    "source_classification": "user_input",
                    "rationale": "Benchmark degradation-dominant half-life override."
                },
                {
                    "parameter": "water_residence_time_days",
                    "value": 40.0,
                    "unit": "day",
                    "source_classification": "user_input",
                    "rationale": "Benchmark degradation-dominant residence-time override."
                }
            ]
        },
        "run_options": {
            "model_family": "advective_screening_mass_balance"
        },
        "expected_surfaces": [
            {
                "medium": "water",
                "compartment": "surface_water",
                "value": 2.6896628583037676e-06,
                "unit": "mg/L"
            }
        ],
        "expected_trace_terms": [
            {
                "medium": "water",
                "compartment": "surface_water",
                "terms": {
                    "degradation_loss_share_fraction": 0.9327185767396358,
                    "advective_clearance_share_fraction": 0.06728142326036424,
                    "total_loss_constant_per_day": 0.37157359027997267
                },
                "tolerance": 1e-12
            },
            {
                "medium": "water",
                "compartment": "surface_water",
                "terms": {
                    "emitted_mass_to_elapsed_mg": 10000000.0,
                    "compartment_mass_at_elapsed_mg": 1344831.4291518838,
                    "cumulative_degraded_mass_mg": 8072836.510843082,
                    "cumulative_advected_mass_mg": 582332.060005034,
                    "mass_balance_closure_error_mg": 3.4924596548080444e-10
                },
                "tolerance": 1e-6
            }
        ]
    },
    {
        "name": "advective_degradation_dominant_loss_share_companion_fixture",
        "category": "advective_loss_dominance_sensitivity",
        "validation_tier": "sensitivity",
        "scientific_basis": "Hand-worked advective water screening case with an alternate short half-life and long residence time, corroborating degradation-dominant loss-share behavior under a second governed regime.",
        "reference_type": "hand_worked_advective_loss_dominance_sensitivity_fixture",
        "expected_behavior": "The advective trace continues to report degradation as the dominant loss share under a different short-half-life and long-residence regime.",
        "tolerance_rationale": "The companion dominance case remains analytically traceable because only the declared degradation and residence-time terms change.",
        "tolerance": 1e-12,
        "scientific_claim_ids": [
            "advective_degradation_dominant_loss_share_v1",
            "advective_cumulative_mass_balance_closure_v1",
        ],
        "scenario": {
            "chemical_identity": {"preferredName": "Benchmark advective degradation dominance companion"},
            "total_release_mass_kg": 10.0,
            "release_fractions": [{"medium": "water", "fraction": 1.0}],
            "duration_days": 25.0,
            "parameter_records": [
                {
                    "parameter": "water_half_life_days",
                    "value": 3.0,
                    "unit": "day",
                    "source_classification": "user_input",
                    "rationale": "Benchmark degradation-dominant companion half-life override."
                },
                {
                    "parameter": "water_residence_time_days",
                    "value": 45.0,
                    "unit": "day",
                    "source_classification": "user_input",
                    "rationale": "Benchmark degradation-dominant companion residence-time override."
                }
            ]
        },
        "run_options": {
            "model_family": "advective_screening_mass_balance"
        },
        "expected_surfaces": [
            {
                "medium": "water",
                "compartment": "surface_water",
                "value": 3.1530495825671985e-06,
                "unit": "mg/L"
            }
        ],
        "expected_trace_terms": [
            {
                "medium": "water",
                "compartment": "surface_water",
                "terms": {
                    "degradation_loss_share_fraction": 0.9122592107132478,
                    "advective_clearance_share_fraction": 0.08774078928675218,
                    "total_loss_constant_per_day": 0.25327128240887065
                },
                "tolerance": 1e-12
            },
            {
                "medium": "water",
                "compartment": "surface_water",
                "terms": {
                    "emitted_mass_to_elapsed_mg": 10000000.0,
                    "compartment_mass_at_elapsed_mg": 1576524.791283599,
                    "cumulative_degraded_mass_mg": 7684392.845366233,
                    "cumulative_advected_mass_mg": 739082.3633501665,
                    "mass_balance_closure_error_mg": 4.656612873077393e-10
                },
                "tolerance": 1e-6
            }
        ]
    },
    {
        "name": "advective_clearance_dominant_loss_share_anchor_fixture",
        "category": "advective_loss_dominance_anchor",
        "validation_tier": "edge_condition",
        "scientific_basis": "Hand-worked advective water screening case with effectively persistent degradation and very short residence time, anchoring a clearance-dominant combined-loss regime in the trace decomposition.",
        "reference_type": "hand_worked_advective_loss_dominance_anchor",
        "expected_behavior": "The advective trace reports clearance as the dominant loss share when residence time is short relative to half-life.",
        "tolerance_rationale": "The dominance split is analytically traceable because the governed trace exposes the exact degradation, clearance, and total-loss constants.",
        "tolerance": 1e-12,
        "scientific_claim_ids": [
            "advective_clearance_dominant_loss_share_v1",
            "advective_cumulative_mass_balance_closure_v1",
        ],
        "scenario": {
            "chemical_identity": {"preferredName": "Benchmark advective clearance dominance"},
            "total_release_mass_kg": 10.0,
            "release_fractions": [{"medium": "water", "fraction": 1.0}],
            "duration_days": 10.0,
            "parameter_records": [
                {
                    "parameter": "water_half_life_days",
                    "value": 180.0,
                    "unit": "day",
                    "source_classification": "user_input",
                    "rationale": "Benchmark clearance-dominant half-life override."
                },
                {
                    "parameter": "water_residence_time_days",
                    "value": 0.5,
                    "unit": "day",
                    "source_classification": "user_input",
                    "rationale": "Benchmark clearance-dominant residence-time override."
                }
            ]
        },
        "run_options": {
            "model_family": "advective_screening_mass_balance"
        },
        "expected_surfaces": [
            {
                "medium": "water",
                "compartment": "surface_water",
                "value": 9.980782892606555e-07,
                "unit": "mg/L"
            }
        ],
        "expected_trace_terms": [
            {
                "medium": "water",
                "compartment": "surface_water",
                "terms": {
                    "degradation_loss_share_fraction": 0.0019217087598644108,
                    "advective_clearance_share_fraction": 0.9980782912401356,
                    "total_loss_constant_per_day": 2.0038508176697776
                },
                "tolerance": 1e-12
            },
            {
                "medium": "water",
                "compartment": "surface_water",
                "terms": {
                    "emitted_mass_to_elapsed_mg": 10000000.0,
                    "compartment_mass_at_elapsed_mg": 499039.14463032776,
                    "cumulative_degraded_mass_mg": 18258.079702892763,
                    "cumulative_advected_mass_mg": 9482702.775666779,
                    "mass_balance_closure_error_mg": 0.0
                },
                "tolerance": 1e-6
            }
        ]
    },
    {
        "name": "advective_clearance_dominant_loss_share_companion_fixture",
        "category": "advective_loss_dominance_sensitivity",
        "validation_tier": "sensitivity",
        "scientific_basis": "Hand-worked advective water screening case with an alternate persistent half-life and short residence time, corroborating clearance-dominant loss-share behavior under a second governed regime.",
        "reference_type": "hand_worked_advective_loss_dominance_sensitivity_fixture",
        "expected_behavior": "The advective trace continues to report clearance as the dominant loss share under a second short-residence regime.",
        "tolerance_rationale": "The companion dominance case remains analytically traceable because only the declared degradation and residence-time terms change.",
        "tolerance": 1e-12,
        "scientific_claim_ids": [
            "advective_clearance_dominant_loss_share_v1",
            "advective_cumulative_mass_balance_closure_v1",
        ],
        "scenario": {
            "chemical_identity": {"preferredName": "Benchmark advective clearance dominance companion"},
            "total_release_mass_kg": 10.0,
            "release_fractions": [{"medium": "water", "fraction": 1.0}],
            "duration_days": 12.0,
            "parameter_records": [
                {
                    "parameter": "water_half_life_days",
                    "value": 120.0,
                    "unit": "day",
                    "source_classification": "user_input",
                    "rationale": "Benchmark clearance-dominant companion half-life override."
                },
                {
                    "parameter": "water_residence_time_days",
                    "value": 1.0,
                    "unit": "day",
                    "source_classification": "user_input",
                    "rationale": "Benchmark clearance-dominant companion residence-time override."
                }
            ]
        },
        "run_options": {
            "model_family": "advective_screening_mass_balance"
        },
        "expected_surfaces": [
            {
                "medium": "water",
                "compartment": "surface_water",
                "value": 1.6570854114047607e-06,
                "unit": "mg/L"
            }
        ],
        "expected_trace_terms": [
            {
                "medium": "water",
                "compartment": "surface_water",
                "terms": {
                    "degradation_loss_share_fraction": 0.005743053327816367,
                    "advective_clearance_share_fraction": 0.9942569466721837,
                    "total_loss_constant_per_day": 1.0057762265046661
                },
                "tolerance": 1e-12
            },
            {
                "medium": "water",
                "compartment": "surface_water",
                "terms": {
                    "emitted_mass_to_elapsed_mg": 10000000.0,
                    "compartment_mass_at_elapsed_mg": 828542.7057023804,
                    "cumulative_degraded_mass_mg": 52672.16833494163,
                    "cumulative_advected_mass_mg": 9118785.125962678,
                    "mass_balance_closure_error_mg": -1.862645149230957e-09
                },
                "tolerance": 1e-6
            }
        ]
    },
    {
        "name": "advective_mixed_loss_transition_anchor_fixture",
        "category": "advective_loss_transition_anchor",
        "validation_tier": "edge_condition",
        "scientific_basis": "Hand-worked advective water screening case with nearly equal degradation and clearance terms, anchoring the governed mixed-loss transition regime at near-parity.",
        "reference_type": "hand_worked_advective_loss_transition_anchor",
        "expected_behavior": "The advective trace reports a mixed-loss regime with a near-parity dominance margin when degradation and residence-time clearance are almost equal.",
        "tolerance_rationale": "The transition anchor is analytically traceable because the governed trace exposes both loss shares and the explicit dominance margin.",
        "tolerance": 1e-12,
        "scientific_claim_ids": [
            "advective_mixed_loss_transition_margin_v1",
            "advective_loss_regime_flip_directionality_v1",
            "advective_cumulative_mass_balance_closure_v1",
            "advective_residence_time_turnover_regime_v1",
        ],
        "scenario": {
            "chemical_identity": {"preferredName": "Benchmark advective mixed-loss transition"},
            "total_release_mass_kg": 10.0,
            "release_fractions": [{"medium": "water", "fraction": 1.0}],
            "duration_days": 15.0,
            "parameter_records": [
                {
                    "parameter": "water_half_life_days",
                    "value": 7.0,
                    "unit": "day",
                    "source_classification": "user_input",
                    "rationale": "Benchmark mixed-loss transition half-life override."
                },
                {
                    "parameter": "water_residence_time_days",
                    "value": 10.0,
                    "unit": "day",
                    "source_classification": "user_input",
                    "rationale": "Benchmark mixed-loss transition residence-time override."
                }
            ]
        },
        "run_options": {
            "model_family": "advective_screening_mass_balance"
        },
        "expected_surfaces": [
            {
                "medium": "water",
                "compartment": "surface_water",
                "value": 6.360979061693635e-06,
                "unit": "mg/L"
            }
        ],
        "expected_trace_terms": [
            {
                "medium": "water",
                "compartment": "surface_water",
                "terms": {
                    "degradation_loss_share_fraction": 0.497540525676081,
                    "advective_clearance_share_fraction": 0.5024594743239191,
                    "loss_dominance_margin_fraction": 0.0049189486478381506,
                    "total_loss_constant_per_day": 0.19902102579427788,
                    "elapsed_turnover_count": 1.5,
                    "active_emission_turnover_count": 1.5
                },
                "tolerance": 1e-12
            },
            {
                "medium": "water",
                "compartment": "surface_water",
                "terms": {
                    "emitted_mass_to_elapsed_mg": 10000000.0,
                    "compartment_mass_at_elapsed_mg": 3180489.530846818,
                    "cumulative_degraded_mass_mg": 3392982.823676012,
                    "cumulative_advected_mass_mg": 3426527.645477171,
                    "mass_balance_closure_error_mg": -4.656612873077393e-10
                },
                "tolerance": 1e-6
            }
        ]
    },
    {
        "name": "advective_mixed_loss_transition_companion_fixture",
        "category": "advective_loss_transition_sensitivity",
        "validation_tier": "sensitivity",
        "scientific_basis": "Hand-worked advective water screening case with a second near-parity loss split, corroborating the governed mixed-loss transition regime under an alternate duration and rate pair.",
        "reference_type": "hand_worked_advective_loss_transition_sensitivity_fixture",
        "expected_behavior": "The advective trace continues to report a mixed-loss regime with a small dominance margin under a second near-parity half-life versus residence-time configuration.",
        "tolerance_rationale": "The companion transition case remains analytically traceable because only the declared degradation and residence-time terms change while the near-parity regime is preserved.",
        "tolerance": 1e-12,
        "scientific_claim_ids": [
            "advective_mixed_loss_transition_margin_v1",
            "advective_cumulative_mass_balance_closure_v1",
        ],
        "scenario": {
            "chemical_identity": {"preferredName": "Benchmark advective mixed-loss transition companion"},
            "total_release_mass_kg": 10.0,
            "release_fractions": [{"medium": "water", "fraction": 1.0}],
            "duration_days": 12.0,
            "parameter_records": [
                {
                    "parameter": "water_half_life_days",
                    "value": 5.0,
                    "unit": "day",
                    "source_classification": "user_input",
                    "rationale": "Benchmark mixed-loss companion half-life override."
                },
                {
                    "parameter": "water_residence_time_days",
                    "value": 7.5,
                    "unit": "day",
                    "source_classification": "user_input",
                    "rationale": "Benchmark mixed-loss companion residence-time override."
                }
            ]
        },
        "run_options": {
            "model_family": "advective_screening_mass_balance"
        },
        "expected_surfaces": [
            {
                "medium": "water",
                "compartment": "surface_water",
                "value": 5.893869007823266e-06,
                "unit": "mg/L"
            }
        ],
        "expected_trace_terms": [
            {
                "medium": "water",
                "compartment": "surface_water",
                "terms": {
                    "degradation_loss_share_fraction": 0.5097368157955173,
                    "advective_clearance_share_fraction": 0.4902631842044826,
                    "loss_dominance_margin_fraction": 0.019473631591034712,
                    "total_loss_constant_per_day": 0.2719627694453224
                },
                "tolerance": 1e-12
            },
            {
                "medium": "water",
                "compartment": "surface_water",
                "terms": {
                    "emitted_mass_to_elapsed_mg": 10000000.0,
                    "compartment_mass_at_elapsed_mg": 2946934.5039116335,
                    "cumulative_degraded_mass_mg": 3595207.147573315,
                    "cumulative_advected_mass_mg": 3457858.3485150514,
                    "mass_balance_closure_error_mg": 4.656612873077393e-10
                },
                "tolerance": 1e-6
            }
        ]
    },
    {
        "name": "advective_bounded_transport_reference_fixture",
        "category": "advective_transport_regime_reference",
        "validation_tier": "reference_style",
        "scientific_basis": "Hand-worked advective water screening case expressed directly in bounded-transport terms, using turnover-boundary offsets and retained mass as a fraction of the finite active-emission plateau.",
        "reference_type": "hand_worked_advective_bounded_transport_reference_fixture",
        "expected_behavior": "The advective trace reports intermediate-turnover bounded transport with explicit turnover-boundary offsets and a finite plateau fraction below unity.",
        "tolerance_rationale": "The bounded-transport reference case remains analytically traceable because the plateau fraction and boundary offsets come directly from the same governed combined-loss equation.",
        "tolerance": 1e-12,
        "scientific_claim_ids": [
            "advective_residence_time_turnover_regime_v1",
            "advective_cumulative_mass_balance_closure_v1"
        ],
        "scenario": {
            "chemical_identity": {"preferredName": "Benchmark advective bounded transport reference"},
            "total_release_mass_kg": 10.0,
            "release_fractions": [{"medium": "water", "fraction": 1.0}],
            "duration_days": 10.0,
            "parameter_records": [
                {
                    "parameter": "water_half_life_days",
                    "value": 14.0,
                    "unit": "day",
                    "source_classification": "user_input",
                    "rationale": "Benchmark bounded-transport half-life override."
                },
                {
                    "parameter": "water_residence_time_days",
                    "value": 10.0,
                    "unit": "day",
                    "source_classification": "user_input",
                    "rationale": "Benchmark bounded-transport residence-time override."
                }
            ]
        },
        "run_options": {
            "model_family": "advective_screening_mass_balance"
        },
        "expected_surfaces": [
            {
                "medium": "water",
                "compartment": "surface_water",
                "value": 1.0377530703665923e-05,
                "unit": "mg/L"
            }
        ],
        "expected_trace_terms": [
            {
                "medium": "water",
                "compartment": "surface_water",
                "terms": {
                    "elapsed_turnover_count": 1.0,
                    "active_emission_turnover_count": 1.0,
                    "storage_boundary_offset_turnovers": 0.25,
                    "flow_through_boundary_offset_turnovers": -1.0,
                    "retained_mass_fraction_of_finite_plateau": 0.7757749690554497,
                    "finite_plateau_mass_mg": 6688492.873327144
                },
                "tolerance": 1e-12
            },
            {
                "medium": "water",
                "compartment": "surface_water",
                "terms": {
                    "emitted_mass_to_elapsed_mg": 10000000.0,
                    "compartment_mass_at_elapsed_mg": 5188765.351832962,
                    "cumulative_degraded_mass_mg": 1593243.7825500513,
                    "cumulative_advected_mass_mg": 3217990.8656169865,
                    "mass_balance_closure_error_mg": 4.656612873077393e-10
                },
                "tolerance": 1e-6
            }
        ]
    },
    {
        "name": "advective_flow_through_transport_reference_fixture",
        "category": "advective_transport_regime_reference",
        "validation_tier": "reference_style",
        "scientific_basis": "Hand-worked advective water screening case expressed directly in stable flow-through bounded-transport terms, using large positive flow-through boundary offset and a plateau fraction effectively at unity.",
        "reference_type": "hand_worked_advective_flow_through_transport_reference_fixture",
        "expected_behavior": "The advective trace reports stable flow-through transport with retained mass essentially at the finite active-emission plateau and a large positive flow-through boundary offset.",
        "tolerance_rationale": "The flow-through bounded-transport reference remains analytically traceable because the turnover counts, boundary offsets, plateau fraction, and cumulative mass terms come directly from the governed combined-loss equation.",
        "tolerance": 1e-12,
        "scientific_claim_ids": [
            "advective_residence_time_turnover_regime_v1",
            "advective_cumulative_mass_balance_closure_v1"
        ],
        "scenario": {
            "chemical_identity": {"preferredName": "Benchmark advective flow-through transport reference"},
            "total_release_mass_kg": 10.0,
            "release_fractions": [{"medium": "water", "fraction": 1.0}],
            "duration_days": 15.0,
            "parameter_records": [
                {
                    "parameter": "water_half_life_days",
                    "value": 5.0,
                    "unit": "day",
                    "source_classification": "user_input",
                    "rationale": "Benchmark flow-through transport half-life override."
                },
                {
                    "parameter": "water_residence_time_days",
                    "value": 0.5,
                    "unit": "day",
                    "source_classification": "user_input",
                    "rationale": "Benchmark flow-through transport residence-time override."
                }
            ]
        },
        "run_options": {
            "model_family": "advective_screening_mass_balance"
        },
        "expected_surfaces": [
            {
                "medium": "water",
                "compartment": "surface_water",
                "value": 6.234522497536118e-07,
                "unit": "mg/L"
            }
        ],
        "expected_trace_terms": [
            {
                "medium": "water",
                "compartment": "surface_water",
                "terms": {
                    "elapsed_turnover_count": 30.0,
                    "active_emission_turnover_count": 30.0,
                    "storage_boundary_offset_turnovers": 29.25,
                    "flow_through_boundary_offset_turnovers": 28.0,
                    "retained_mass_fraction_of_finite_plateau": 0.9999999999999885,
                    "finite_plateau_mass_mg": 311726.12487680954
                },
                "tolerance": 1e-12
            },
            {
                "medium": "water",
                "compartment": "surface_water",
                "terms": {
                    "emitted_mass_to_elapsed_mg": 10000000.0,
                    "compartment_mass_at_elapsed_mg": 311726.12487680593,
                    "cumulative_degraded_mass_mg": 628009.6596110412,
                    "cumulative_advected_mass_mg": 9060264.215512153,
                    "mass_balance_closure_error_mg": 0.0
                },
                "tolerance": 1e-6
            }
        ]
    },
    {
        "name": "advective_transition_boundary_reference_fixture",
        "category": "advective_transport_regime_reference",
        "validation_tier": "reference_style",
        "scientific_basis": "Hand-worked advective water screening case expressed directly in near-boundary transport and mixed-loss terms, using an intermediate turnover count and a small degradation-versus-clearance margin.",
        "reference_type": "hand_worked_advective_transition_boundary_reference_fixture",
        "expected_behavior": "The advective trace reports boundary-sensitive intermediate transport together with a small mixed-loss dominance margin and finite bounded-transport plateau fraction.",
        "tolerance_rationale": "The transition-boundary reference remains analytically traceable because the mixed-loss share, turnover-boundary offsets, plateau fraction, and cumulative mass terms all resolve from the same governed combined-loss equation.",
        "tolerance": 1e-12,
        "scientific_claim_ids": [
            "advective_residence_time_turnover_regime_v1",
            "advective_mixed_loss_transition_margin_v1",
            "advective_cumulative_mass_balance_closure_v1"
        ],
        "scenario": {
            "chemical_identity": {"preferredName": "Benchmark advective transition-boundary transport reference"},
            "total_release_mass_kg": 10.0,
            "release_fractions": [{"medium": "water", "fraction": 1.0}],
            "duration_days": 18.0,
            "parameter_records": [
                {
                    "parameter": "water_half_life_days",
                    "value": 8.0,
                    "unit": "day",
                    "source_classification": "user_input",
                    "rationale": "Benchmark transition-boundary half-life override."
                },
                {
                    "parameter": "water_residence_time_days",
                    "value": 10.5,
                    "unit": "day",
                    "source_classification": "user_input",
                    "rationale": "Benchmark transition-boundary residence-time override."
                }
            ]
        },
        "run_options": {
            "model_family": "advective_screening_mass_balance"
        },
        "expected_surfaces": [
            {
                "medium": "water",
                "compartment": "surface_water",
                "value": 5.8776993269409705e-06,
                "unit": "mg/L"
            }
        ],
        "expected_trace_terms": [
            {
                "medium": "water",
                "compartment": "surface_water",
                "terms": {
                    "elapsed_turnover_count": 1.7142857142857142,
                    "active_emission_turnover_count": 1.7142857142857142,
                    "storage_boundary_offset_turnovers": 0.9642857142857142,
                    "flow_through_boundary_offset_turnovers": -0.2857142857142858,
                    "retained_mass_fraction_of_finite_plateau": 0.9621402550750082,
                    "finite_plateau_mass_mg": 3054491.9495561207,
                    "degradation_loss_share_fraction": 0.4763728086475221,
                    "advective_clearance_share_fraction": 0.5236271913524778,
                    "loss_dominance_margin_fraction": 0.047254382704955744
                },
                "tolerance": 1e-12
            },
            {
                "medium": "water",
                "compartment": "surface_water",
                "terms": {
                    "emitted_mass_to_elapsed_mg": 10000000.0,
                    "compartment_mass_at_elapsed_mg": 2938849.6634704852,
                    "cumulative_degraded_mass_mg": 3363740.0180949606,
                    "cumulative_advected_mass_mg": 3697410.318434553,
                    "mass_balance_closure_error_mg": 9.313225746154785e-10
                },
                "tolerance": 1e-6
            }
        ]
    },
    {
        "name": "advective_storage_dominant_transport_reference_fixture",
        "category": "advective_transport_regime_reference",
        "validation_tier": "reference_style",
        "scientific_basis": "Hand-worked advective water screening case expressed directly in stable storage-dominant bounded-transport terms, using a negative storage-boundary offset and a large remaining plateau gap under finite loss.",
        "reference_type": "hand_worked_advective_storage_dominant_transport_reference_fixture",
        "expected_behavior": "The advective trace reports stable storage-dominant transport with retained mass materially below the finite active-emission plateau and a negative storage-boundary offset.",
        "tolerance_rationale": "The storage-dominant bounded-transport reference remains analytically traceable because the turnover counts, boundary offsets, plateau fraction, and cumulative mass terms are all direct outputs of the governed combined-loss equation.",
        "tolerance": 1e-12,
        "scientific_claim_ids": [
            "advective_residence_time_turnover_regime_v1",
            "advective_cumulative_mass_balance_closure_v1"
        ],
        "scenario": {
            "chemical_identity": {"preferredName": "Benchmark advective storage-dominant transport reference"},
            "total_release_mass_kg": 10.0,
            "release_fractions": [{"medium": "water", "fraction": 1.0}],
            "duration_days": 30.0,
            "parameter_records": [
                {
                    "parameter": "water_half_life_days",
                    "value": 12.0,
                    "unit": "day",
                    "source_classification": "user_input",
                    "rationale": "Benchmark storage-dominant transport half-life override."
                },
                {
                    "parameter": "water_residence_time_days",
                    "value": 120.0,
                    "unit": "day",
                    "source_classification": "user_input",
                    "rationale": "Benchmark storage-dominant transport residence-time override."
                }
            ]
        },
        "run_options": {
            "model_family": "advective_screening_mass_balance"
        },
        "expected_surfaces": [
            {
                "medium": "water",
                "compartment": "surface_water",
                "value": 8.697766996187716e-06,
                "unit": "mg/L"
            }
        ],
        "expected_trace_terms": [
            {
                "medium": "water",
                "compartment": "surface_water",
                "terms": {
                    "elapsed_turnover_count": 0.25,
                    "active_emission_turnover_count": 0.25,
                    "storage_boundary_offset_turnovers": -0.5,
                    "flow_through_boundary_offset_turnovers": -1.75,
                    "retained_mass_fraction_of_finite_plateau": 0.8623261712742041,
                    "finite_plateau_mass_mg": 5043200.175251312
                },
                "tolerance": 1e-12
            },
            {
                "medium": "water",
                "compartment": "surface_water",
                "terms": {
                    "emitted_mass_to_elapsed_mg": 10000000.0,
                    "compartment_mass_at_elapsed_mg": 4348883.498093858,
                    "cumulative_degraded_mass_mg": 4938623.708586675,
                    "cumulative_advected_mass_mg": 712492.7933194657,
                    "mass_balance_closure_error_mg": 8.149072527885437e-10
                },
                "tolerance": 1e-6
            }
        ]
    },
    {
        "name": "advective_transition_flip_to_degradation_fixture",
        "category": "advective_loss_transition_sensitivity",
        "validation_tier": "sensitivity",
        "scientific_basis": "Hand-worked advective water screening case with a modest half-life shift away from the near-parity anchor, demonstrating that the governed transition flips toward degradation dominance in the expected direction.",
        "reference_type": "hand_worked_advective_transition_sensitivity_fixture",
        "expected_behavior": "The advective trace reports degradation as the larger resolved loss-share component after a small half-life shift away from the mixed-loss transition anchor.",
        "tolerance_rationale": "The degradation-side transition sensitivity case remains analytically traceable because it modifies only the declared half-life while preserving the same bounded screening equation.",
        "tolerance": 1e-12,
        "scientific_claim_ids": [
            "advective_loss_regime_flip_directionality_v1",
            "advective_degradation_dominant_loss_share_v1",
        ],
        "scenario": {
            "chemical_identity": {"preferredName": "Benchmark advective transition flip to degradation"},
            "total_release_mass_kg": 10.0,
            "release_fractions": [{"medium": "water", "fraction": 1.0}],
            "duration_days": 15.0,
            "parameter_records": [
                {
                    "parameter": "water_half_life_days",
                    "value": 6.5,
                    "unit": "day",
                    "source_classification": "user_input",
                    "rationale": "Benchmark degradation-side transition half-life override."
                },
                {
                    "parameter": "water_residence_time_days",
                    "value": 10.0,
                    "unit": "day",
                    "source_classification": "user_input",
                    "rationale": "Benchmark degradation-side transition residence-time override."
                }
            ]
        },
        "run_options": {
            "model_family": "advective_screening_mass_balance"
        },
        "expected_surfaces": [
            {
                "medium": "water",
                "compartment": "surface_water",
                "value": 6.16170186633071e-06,
                "unit": "mg/L"
            }
        ],
        "expected_trace_terms": [
            {
                "medium": "water",
                "compartment": "surface_water",
                "terms": {
                    "degradation_loss_share_fraction": 0.5160619704171056,
                    "advective_clearance_share_fraction": 0.4839380295828944,
                    "loss_dominance_margin_fraction": 0.03212394083421116,
                    "total_loss_constant_per_day": 0.20663802777845314
                },
                "tolerance": 1e-12
            }
        ]
    },
    {
        "name": "advective_transition_flip_to_clearance_fixture",
        "category": "advective_loss_transition_sensitivity",
        "validation_tier": "sensitivity",
        "scientific_basis": "Hand-worked advective water screening case with a modest residence-time shift away from the near-parity anchor, demonstrating that the governed transition flips toward clearance dominance in the expected direction.",
        "reference_type": "hand_worked_advective_transition_sensitivity_fixture",
        "expected_behavior": "The advective trace reports clearance as the larger resolved loss-share component after a small residence-time shift away from the mixed-loss transition anchor.",
        "tolerance_rationale": "The clearance-side transition sensitivity case remains analytically traceable because it modifies only the declared residence time while preserving the same bounded screening equation.",
        "tolerance": 1e-12,
        "scientific_claim_ids": [
            "advective_loss_regime_flip_directionality_v1",
            "advective_clearance_dominant_loss_share_v1",
        ],
        "scenario": {
            "chemical_identity": {"preferredName": "Benchmark advective transition flip to clearance"},
            "total_release_mass_kg": 10.0,
            "release_fractions": [{"medium": "water", "fraction": 1.0}],
            "duration_days": 15.0,
            "parameter_records": [
                {
                    "parameter": "water_half_life_days",
                    "value": 7.0,
                    "unit": "day",
                    "source_classification": "user_input",
                    "rationale": "Benchmark clearance-side transition half-life override."
                },
                {
                    "parameter": "water_residence_time_days",
                    "value": 9.0,
                    "unit": "day",
                    "source_classification": "user_input",
                    "rationale": "Benchmark clearance-side transition residence-time override."
                }
            ]
        },
        "run_options": {
            "model_family": "advective_screening_mass_balance"
        },
        "expected_surfaces": [
            {
                "medium": "water",
                "compartment": "surface_water",
                "value": 6.073846284368942e-06,
                "unit": "mg/L"
            }
        ],
        "expected_trace_terms": [
            {
                "medium": "water",
                "compartment": "surface_water",
                "terms": {
                    "degradation_loss_share_fraction": 0.4712321839608076,
                    "advective_clearance_share_fraction": 0.5287678160391923,
                    "loss_dominance_margin_fraction": 0.05753563207838469,
                    "total_loss_constant_per_day": 0.210132136905389
                },
                "tolerance": 1e-12
            }
        ]
    },
    {
        "name": "advective_long_duration_plateau_anchor_fixture",
        "category": "edge_condition_anchor",
        "validation_tier": "edge_condition",
        "scientific_basis": "Hand-worked advective water screening case with long finite duration, anchoring approach toward the combined degradation-plus-clearance plateau at a fixed release rate.",
        "reference_type": "hand_worked_advective_duration_edge_anchor",
        "expected_behavior": "Advective water concentration approaches the governed finite-duration combined-loss plateau when duration is long relative to both water half-life and residence time.",
        "tolerance_rationale": "The long-duration advective anchor remains analytically traceable to the same deterministic combined-loss equation.",
        "tolerance": 1e-12,
        "scientific_claim_ids": [
            "advective_water_finite_duration_first_order_v1",
            "advective_long_duration_combined_loss_plateau_v1",
        ],
        "scenario": {
            "chemical_identity": {"preferredName": "Benchmark advective long duration"},
            "total_release_mass_kg": 80.0,
            "release_fractions": [{"medium": "water", "fraction": 1.0}],
            "duration_days": 120.0
        },
        "run_options": {
            "model_family": "advective_screening_mass_balance"
        },
        "expected_surfaces": [
            {
                "medium": "water",
                "compartment": "surface_water",
                "value": 1.3858466147386445e-05,
                "unit": "mg/L"
            }
        ]
    },
    {
        "name": "advective_long_duration_plateau_companion_fixture",
        "category": "edge_condition_anchor",
        "validation_tier": "edge_condition",
        "scientific_basis": "Hand-worked advective water screening case with a longer finite duration at the same release rate, corroborating approach toward the combined degradation-plus-clearance plateau.",
        "reference_type": "hand_worked_advective_duration_edge_anchor",
        "expected_behavior": "Advective water concentration remains close to the governed combined-loss plateau when duration is extended further at the same release rate.",
        "tolerance_rationale": "The companion duration anchor remains analytically traceable to the deterministic combined-loss equation.",
        "tolerance": 1e-12,
        "scientific_claim_ids": [
            "advective_water_finite_duration_first_order_v1",
            "advective_long_duration_combined_loss_plateau_v1",
        ],
        "scenario": {
            "chemical_identity": {"preferredName": "Benchmark advective long duration companion"},
            "total_release_mass_kg": 160.0,
            "release_fractions": [{"medium": "water", "fraction": 1.0}],
            "duration_days": 240.0
        },
        "run_options": {
            "model_family": "advective_screening_mass_balance"
        },
        "expected_surfaces": [
            {
                "medium": "water",
                "compartment": "surface_water",
                "value": 1.385860033372679e-05,
                "unit": "mg/L"
            }
        ]
    },
    {
        "name": "advective_long_duration_plateau_sensitivity_fixture",
        "category": "parameter_override_sensitivity",
        "validation_tier": "sensitivity",
        "scientific_basis": "Hand-worked advective water screening case with long finite duration and a residence-time override, corroborating plateau behavior under an alternate governed clearance regime.",
        "reference_type": "hand_worked_advective_override_fixture",
        "expected_behavior": "Advective water concentration still approaches a bounded combined-loss plateau under long duration when residence time is overridden, while the plateau level shifts consistently with the stronger clearance term.",
        "tolerance_rationale": "The long-duration sensitivity anchor remains analytically traceable to the same deterministic combined-loss equation with a governed residence-time override.",
        "tolerance": 1e-12,
        "scientific_claim_ids": [
            "advective_water_finite_duration_first_order_v1",
            "advective_residence_time_override_application_v1",
            "advective_long_duration_combined_loss_plateau_v1",
        ],
        "scenario": {
            "chemical_identity": {"preferredName": "Benchmark advective long duration sensitivity"},
            "total_release_mass_kg": 120.0,
            "release_fractions": [{"medium": "water", "fraction": 1.0}],
            "duration_days": 180.0,
            "parameter_records": [
                {
                    "parameter": "water_residence_time_days",
                    "value": 10.0,
                    "unit": "day",
                    "source_classification": "user_input",
                    "rationale": "Benchmark long-duration residence-time override."
                }
            ]
        },
        "run_options": {
            "model_family": "advective_screening_mass_balance"
        },
        "expected_surfaces": [
            {
                "medium": "water",
                "compartment": "surface_water",
                "value": 9.119315008680499e-06,
                "unit": "mg/L"
            }
        ]
    },
    {
        "name": "multi_medium_mass_balance_fixture",
        "category": "multi_medium_mass_balance",
        "validation_tier": "reference_style",
        "scientific_basis": "Hand-worked two-medium finite-duration first-order screening calculation across air and water under governed defaults.",
        "reference_type": "hand_worked_partition_fixture",
        "expected_behavior": "Reference runtime emits one air and one water surface matching the documented partitioned first-order screening calculations.",
        "tolerance_rationale": "Each surface is derived from a closed-form deterministic expression with no stochastic terms.",
        "tolerance": 1e-12,
        "scientific_claim_ids": ["reference_multi_medium_partition_v1"],
        "scenario": {
            "chemical_identity": {"preferredName": "Benchmark multi-medium"},
            "total_release_mass_kg": 10.0,
            "release_fractions": [
                {"medium": "air", "fraction": 0.4},
                {"medium": "water", "fraction": 0.6}
            ],
            "duration_days": 10.0,
        },
        "expected_surfaces": [
            {
                "medium": "air",
                "compartment": "ambient_air",
                "value": 0.0011180886566889466,
                "unit": "mg/m3",
            },
            {
                "medium": "water",
                "compartment": "surface_water",
                "value": 9.609374080646793e-06,
                "unit": "mg/L",
            }
        ],
    },
    {
        "name": "reference_multi_medium_fraction_sensitivity_fixture",
        "category": "parameter_override_sensitivity",
        "validation_tier": "sensitivity",
        "scientific_basis": "Hand-worked two-medium finite-duration first-order screening case with a shifted air-water release split, corroborating declared-fraction sensitivity in the baseline reference kernel.",
        "reference_type": "hand_worked_partition_sensitivity_fixture",
        "expected_behavior": "Reference runtime emits air and water surfaces that scale with the declared release fractions while preserving one-surface-per-medium behavior.",
        "tolerance_rationale": "The partition sensitivity case remains analytically traceable because only the declared release fractions change.",
        "tolerance": 1e-12,
        "scientific_claim_ids": ["reference_multi_medium_partition_v1"],
        "scenario": {
            "chemical_identity": {"preferredName": "Benchmark multi-medium sensitivity"},
            "total_release_mass_kg": 10.0,
            "release_fractions": [
                {"medium": "air", "fraction": 0.7},
                {"medium": "water", "fraction": 0.3},
            ],
            "duration_days": 10.0,
        },
        "expected_surfaces": [
            {
                "medium": "air",
                "compartment": "ambient_air",
                "value": 0.001956655149205657,
                "unit": "mg/m3",
            },
            {
                "medium": "water",
                "compartment": "surface_water",
                "value": 4.804687040323397e-06,
                "unit": "mg/L",
            },
        ],
    },
    {
        "name": "time_bucket_invariance_fixture",
        "category": "time_bucket_invariance",
        "validation_tier": "invariance",
        "scientific_basis": "Hand-worked finite-duration first-order time-bucket case evaluated at explicit elapsed bucket end times, including post-release decay.",
        "reference_type": "hand_worked_time_bucket_fixture",
        "expected_behavior": "Time-bucket water surfaces follow physical elapsed time rather than arbitrary bucket-count scaling, and later buckets can decay after release ends.",
        "tolerance_rationale": "The finite-duration first-order bucket calculation is deterministic and analytically traceable to elapsed time.",
        "tolerance": 1e-12,
        "scientific_claim_ids": ["reference_time_bucket_elapsed_time_v1"],
        "scenario": {
            "chemical_identity": {"preferredName": "Benchmark time bucket"},
            "total_release_mass_kg": 10.0,
            "release_fractions": [{"medium": "water", "fraction": 1.0}],
            "duration_days": 15.0,
        },
        "run_options": {
            "run_mode": "time_bucket",
            "bucket_count": 3,
            "bucket_duration_days": 7.5
        },
        "expected_surfaces": [
            {
                "medium": "water",
                "compartment": "surface_water",
                "bucket_label": "bucket_1",
                "value": 8.451111885843478e-06,
                "unit": "mg/L",
            },
            {
                "medium": "water",
                "compartment": "surface_water",
                "bucket_label": "bucket_2",
                "value": 1.4426950408889635e-05,
                "unit": "mg/L",
            },
            {
                "medium": "water",
                "compartment": "surface_water",
                "bucket_label": "bucket_3",
                "value": 1.0201394465967895e-05,
                "unit": "mg/L",
            }
        ],
    },
    {
        "name": "reference_time_bucket_post_release_companion_fixture",
        "category": "time_bucket_decay_anchor",
        "validation_tier": "sensitivity",
        "scientific_basis": "Hand-worked finite-duration first-order time-bucket case with a water half-life override, corroborating elapsed-time and post-release decay behavior under alternate degradation kinetics.",
        "reference_type": "hand_worked_time_bucket_decay_fixture",
        "expected_behavior": "Time-bucket water surfaces continue to reflect elapsed time and post-release decay under a different half-life, rather than arbitrary bucket pagination.",
        "tolerance_rationale": "The alternate bucket-decay case remains analytically traceable because only the first-order degradation constant changes.",
        "tolerance": 1e-12,
        "scientific_claim_ids": ["reference_time_bucket_elapsed_time_v1"],
        "scenario": {
            "chemical_identity": {"preferredName": "Benchmark time bucket companion"},
            "total_release_mass_kg": 10.0,
            "release_fractions": [{"medium": "water", "fraction": 1.0}],
            "duration_days": 10.0,
            "parameter_records": [
                {
                    "parameter": "water_half_life_days",
                    "value": 8.0,
                    "unit": "day",
                    "source_classification": "user_input",
                    "rationale": "Benchmark alternate bucket decay half-life.",
                }
            ],
        },
        "run_options": {
            "run_mode": "time_bucket",
            "bucket_count": 4,
            "bucket_duration_days": 5.0,
        },
        "expected_surfaces": [
            {
                "medium": "water",
                "compartment": "surface_water",
                "bucket_label": "bucket_1",
                "value": 8.115568699634107e-06,
                "unit": "mg/L",
            },
            {
                "medium": "water",
                "compartment": "surface_water",
                "bucket_label": "bucket_2",
                "value": 1.3377863948720692e-05,
                "unit": "mg/L",
            },
            {
                "medium": "water",
                "compartment": "surface_water",
                "bucket_label": "bucket_3",
                "value": 8.67447156272037e-06,
                "unit": "mg/L",
            },
            {
                "medium": "water",
                "compartment": "surface_water",
                "bucket_label": "bucket_4",
                "value": 5.6246989191155655e-06,
                "unit": "mg/L",
            },
        ],
    },
    {
        "name": "parameter_override_sensitivity_fixture",
        "category": "parameter_override_sensitivity",
        "validation_tier": "sensitivity",
        "scientific_basis": "Hand-worked finite-duration override case where a scenario-specific water half-life replaces the governed curated default.",
        "reference_type": "hand_worked_override_fixture",
        "expected_behavior": "Water concentration reflects the scenario half-life override through the finite-duration first-order equation rather than the curated default half-life.",
        "tolerance_rationale": "Override behavior is deterministic and should remain analytically traceable.",
        "tolerance": 1e-12,
        "scientific_claim_ids": ["reference_parameter_override_application_v1"],
        "scenario": {
            "chemical_identity": {"preferredName": "Benchmark override"},
            "total_release_mass_kg": 10.0,
            "release_fractions": [{"medium": "water", "fraction": 1.0}],
            "duration_days": 15.0,
            "parameter_records": [
                {
                    "parameter": "water_half_life_days",
                    "value": 5.0,
                    "unit": "day",
                    "source_classification": "user_input",
                    "rationale": "Benchmark override for water half-life."
                }
            ]
        },
        "expected_surfaces": [
            {
                "medium": "water",
                "compartment": "surface_water",
                "value": 8.415721071852286e-06,
                "unit": "mg/L",
            }
        ],
    },
    {
        "name": "reference_treatment_reduction_anchor_fixture",
        "category": "treatment_reduction_anchor",
        "validation_tier": "edge_condition",
        "scientific_basis": "Hand-worked finite-duration water screening case where executable pre-release treatment reduces the effective release mass before the first-order calculation.",
        "reference_type": "hand_worked_treatment_anchor",
        "expected_behavior": "Water concentration reflects the pre_release_global treatment removal fraction before the finite-duration first-order screening equation is evaluated.",
        "tolerance_rationale": "Treatment execution is a deterministic mass-reduction step before the governed reference equation.",
        "tolerance": 1e-12,
        "scientific_claim_ids": ["reference_executable_treatment_reduction_v1"],
        "scenario": {
            "chemical_identity": {"preferredName": "Benchmark treatment"},
            "total_release_mass_kg": 10.0,
            "release_fractions": [{"medium": "water", "fraction": 1.0}],
            "duration_days": 10.0,
            "treatment_assumptions": [
                {
                    "description": "Executable pre-release treatment",
                    "removal_fraction": 0.9,
                    "execution_mode": "pre_release_global"
                }
            ]
        },
        "expected_surfaces": [
            {
                "medium": "water",
                "compartment": "surface_water",
                "value": 1.6015623467744658e-06,
                "unit": "mg/L"
            }
        ]
    },
    {
        "name": "reference_treatment_proportionality_sensitivity_fixture",
        "category": "parameter_override_sensitivity",
        "validation_tier": "sensitivity",
        "scientific_basis": "Hand-worked finite-duration water screening case with a different executable pre-release treatment fraction, corroborating proportional source-term reduction in the baseline reference kernel.",
        "reference_type": "hand_worked_treatment_sensitivity_fixture",
        "expected_behavior": "Water concentration scales with the effective post-treatment release mass when executable pre_release_global treatment changes.",
        "tolerance_rationale": "Treatment proportionality remains deterministic because the reduction applies before the same finite-duration first-order equation is evaluated.",
        "tolerance": 1e-12,
        "scientific_claim_ids": ["reference_executable_treatment_reduction_v1"],
        "scenario": {
            "chemical_identity": {"preferredName": "Benchmark treatment proportionality"},
            "total_release_mass_kg": 12.0,
            "release_fractions": [{"medium": "water", "fraction": 1.0}],
            "duration_days": 10.0,
            "treatment_assumptions": [
                {
                    "description": "Executable proportionality treatment",
                    "removal_fraction": 0.5,
                    "execution_mode": "pre_release_global",
                }
            ],
        },
        "expected_surfaces": [
            {
                "medium": "water",
                "compartment": "surface_water",
                "value": 9.609374080646793e-06,
                "unit": "mg/L",
            }
        ],
    },
    {
        "name": "reference_short_half_life_attenuation_anchor_fixture",
        "category": "edge_condition_anchor",
        "validation_tier": "edge_condition",
        "scientific_basis": "Hand-worked finite-duration water screening case with a one-day half-life override to anchor strong first-order attenuation behavior.",
        "reference_type": "hand_worked_decay_edge_anchor",
        "expected_behavior": "Water concentration drops sharply when a short scenario half-life override is applied to the finite-duration first-order screening equation.",
        "tolerance_rationale": "The edge-condition anchor is still a closed-form deterministic reference calculation.",
        "tolerance": 1e-12,
        "scientific_claim_ids": ["reference_short_half_life_attenuation_v1"],
        "scenario": {
            "chemical_identity": {"preferredName": "Benchmark short half-life"},
            "total_release_mass_kg": 10.0,
            "release_fractions": [{"medium": "water", "fraction": 1.0}],
            "duration_days": 15.0,
            "parameter_records": [
                {
                    "parameter": "water_half_life_days",
                    "value": 1.0,
                    "unit": "day",
                    "source_classification": "user_input",
                    "rationale": "Benchmark short half-life override."
                }
            ]
        },
        "expected_surfaces": [
            {
                "medium": "water",
                "compartment": "surface_water",
                "value": 1.9235346844404566e-06,
                "unit": "mg/L"
            }
        ]
    },
    {
        "name": "reference_short_half_life_sensitivity_companion_fixture",
        "category": "parameter_override_sensitivity",
        "validation_tier": "sensitivity",
        "scientific_basis": "Hand-worked finite-duration water screening case with a two-day half-life override, corroborating strong attenuation behavior under an alternate short degradation regime.",
        "reference_type": "hand_worked_decay_sensitivity_fixture",
        "expected_behavior": "Water concentration remains strongly attenuated when a short half-life override is applied, while scaling consistently with the alternate first-order rate.",
        "tolerance_rationale": "The alternate short-half-life case remains analytically traceable because only the first-order degradation rate changes.",
        "tolerance": 1e-12,
        "scientific_claim_ids": ["reference_short_half_life_attenuation_v1"],
        "scenario": {
            "chemical_identity": {"preferredName": "Benchmark short half-life companion"},
            "total_release_mass_kg": 10.0,
            "release_fractions": [{"medium": "water", "fraction": 1.0}],
            "duration_days": 20.0,
            "parameter_records": [
                {
                    "parameter": "water_half_life_days",
                    "value": 2.0,
                    "unit": "day",
                    "source_classification": "user_input",
                    "rationale": "Benchmark alternate short half-life override.",
                }
            ],
        },
        "expected_surfaces": [
            {
                "medium": "water",
                "compartment": "surface_water",
                "value": 2.88257231802619e-06,
                "unit": "mg/L",
            }
        ],
    },
    {
        "name": "reference_long_duration_rate_anchor_fixture",
        "category": "edge_condition_anchor",
        "validation_tier": "edge_condition",
        "scientific_basis": "Hand-worked finite-duration water screening case with a long duration and fixed release rate, demonstrating convergence toward the first-order duration-limited plateau.",
        "reference_type": "hand_worked_duration_edge_anchor",
        "expected_behavior": "The end-of-duration water concentration approaches the governed first-order plateau when duration is long relative to the default water half-life at a fixed release rate.",
        "tolerance_rationale": "The long-duration anchor remains analytically traceable to the same deterministic reference equation.",
        "tolerance": 1e-12,
        "scientific_claim_ids": ["reference_long_duration_rate_anchor_v1"],
        "scenario": {
            "chemical_identity": {"preferredName": "Benchmark long duration"},
            "total_release_mass_kg": 80.0,
            "release_fractions": [{"medium": "water", "fraction": 1.0}],
            "duration_days": 120.0
        },
        "expected_surfaces": [
            {
                "medium": "water",
                "compartment": "surface_water",
                "value": 2.874119026770982e-05,
                "unit": "mg/L"
            }
        ]
    },
    {
        "name": "reference_long_duration_plateau_sensitivity_fixture",
        "category": "parameter_override_sensitivity",
        "validation_tier": "sensitivity",
        "scientific_basis": "Hand-worked finite-duration water screening case with a longer duration at the same fixed release rate, corroborating duration-limited plateau behavior under the baseline reference kernel.",
        "reference_type": "hand_worked_duration_sensitivity_fixture",
        "expected_behavior": "Water concentration remains close to the duration-limited plateau when duration is extended further at the same fixed release rate.",
        "tolerance_rationale": "The long-duration sensitivity case remains analytically traceable to the same deterministic first-order reference equation.",
        "tolerance": 1e-12,
        "scientific_claim_ids": ["reference_long_duration_rate_anchor_v1"],
        "scenario": {
            "chemical_identity": {"preferredName": "Benchmark long duration companion"},
            "total_release_mass_kg": 160.0,
            "release_fractions": [{"medium": "water", "fraction": 1.0}],
            "duration_days": 240.0,
        },
        "expected_surfaces": [
            {
                "medium": "water",
                "compartment": "surface_water",
                "value": 2.8853460542193062e-05,
                "unit": "mg/L",
            }
        ],
    },
    {
        "name": "advective_time_bucket_invariance_fixture",
        "category": "time_bucket_invariance",
        "validation_tier": "invariance",
        "scientific_basis": "Hand-worked finite-duration advective water time-bucket case evaluated at explicit elapsed bucket end times with combined degradation and residence-time loss.",
        "reference_type": "hand_worked_advective_time_bucket_fixture",
        "expected_behavior": "Advective time-bucket water surfaces follow elapsed physical time with combined first-order degradation and advective clearance rather than bucket-count scaling.",
        "tolerance_rationale": "The advective bucket anchor is deterministic and analytically traceable to the governed combined-loss equation.",
        "tolerance": 1e-12,
        "scientific_claim_ids": ["advective_time_bucket_elapsed_time_v1"],
        "scenario": {
            "chemical_identity": {"preferredName": "Benchmark advective time bucket"},
            "total_release_mass_kg": 10.0,
            "release_fractions": [{"medium": "water", "fraction": 1.0}],
            "duration_days": 15.0
        },
        "run_options": {
            "run_mode": "time_bucket",
            "bucket_count": 3,
            "bucket_duration_days": 7.5,
            "model_family": "advective_screening_mass_balance"
        },
        "expected_surfaces": [
            {
                "medium": "water",
                "compartment": "surface_water",
                "bucket_label": "bucket_1",
                "value": 7.1235019858564015e-06,
                "unit": "mg/L"
            },
            {
                "medium": "water",
                "compartment": "surface_water",
                "bucket_label": "bucket_2",
                "value": 1.0585430701990208e-05,
                "unit": "mg/L"
            },
            {
                "medium": "water",
                "compartment": "surface_water",
                "bucket_label": "bucket_3",
                "value": 5.144380754385186e-06,
                "unit": "mg/L"
            }
        ]
    },
    {
        "name": "advective_extreme_persistence_clearance_anchor_fixture",
        "category": "edge_condition_anchor",
        "validation_tier": "edge_condition",
        "scientific_basis": "Hand-worked advective water screening case with an effectively non-degrading substance, anchoring the residence-time clearance bound.",
        "reference_type": "hand_worked_advective_edge_anchor",
        "expected_behavior": "The advective screening concentration remains bounded by residence-time clearance when degradation is effectively absent.",
        "tolerance_rationale": "The advective edge-condition anchor is still a deterministic closed-form reference calculation.",
        "tolerance": 1e-12,
        "scientific_claim_ids": ["advective_extreme_persistence_clearance_bound_v1"],
        "scenario": {
            "chemical_identity": {"preferredName": "Benchmark extreme persistence"},
            "total_release_mass_kg": 10.0,
            "release_fractions": [{"medium": "water", "fraction": 1.0}],
            "duration_days": 60.0,
            "parameter_records": [
                {
                    "parameter": "water_half_life_days",
                    "value": 100000.0,
                    "unit": "day",
                    "source_classification": "user_input",
                    "rationale": "Benchmark extreme persistence override."
                }
            ]
        },
        "run_options": {
            "model_family": "advective_screening_mass_balance"
        },
        "expected_surfaces": [
            {
                "medium": "water",
                "compartment": "surface_water",
                "value": 6.334012807287605e-06,
                "unit": "mg/L"
            }
        ]
    },
    {
        "name": "advective_air_transport_reference_fixture",
        "category": "reference_chemical_style",
        "validation_tier": "reference_style",
        "scientific_basis": "Hand-worked finite-duration advective air screening case, broadening the governed proof surface beyond water while retaining explicit degradation-versus-clearance accounting.",
        "reference_type": "hand_worked_advective_air_reference_fixture",
        "expected_behavior": "Advective air concentration follows the same combined-loss equation and trace-level degradation/clearance bookkeeping as the water anchors.",
        "tolerance_rationale": "The air advective reference case remains analytically traceable because only medium-specific governed capacity, half-life, and residence-time parameters differ.",
        "tolerance": 1e-12,
        "scientific_claim_ids": [
            "advective_cumulative_mass_balance_closure_v1",
            "advective_residence_time_turnover_regime_v1",
        ],
        "scenario": {
            "chemical_identity": {
                "preferredName": "Benchmark advective air transport",
                "substance_class": "organic chemical"
            },
            "total_release_mass_kg": 10.0,
            "release_fractions": [{"medium": "air", "fraction": 1.0}],
            "duration_days": 10.0
        },
        "run_options": {
            "model_family": "advective_screening_mass_balance"
        },
        "expected_surfaces": [
            {
                "medium": "air",
                "compartment": "ambient_air",
                "value": 0.0014691498983410997,
                "unit": "mg/m3"
            }
        ],
        "expected_trace_terms": [
            {
                "medium": "air",
                "compartment": "ambient_air",
                "terms": {
                    "degradation_loss_share_fraction": 0.5097368157955173,
                    "advective_clearance_share_fraction": 0.4902631842044826,
                    "elapsed_turnover_count": 3.333333333333333,
                    "active_emission_turnover_count": 3.333333333333333,
                    "retained_mass_fraction_of_finite_plateau": 0.9988851877078984,
                    "cumulative_degraded_mass_mg": 4348488.366848473,
                    "cumulative_advected_mass_mg": 4182361.734810427,
                    "mass_balance_closure_error_mg": -9.313225746154785e-10
                },
                "tolerance": 1e-12
            }
        ]
    },
    {
        "name": "advective_soil_transport_reference_fixture",
        "category": "reference_chemical_style",
        "validation_tier": "reference_style",
        "scientific_basis": "Hand-worked finite-duration advective soil screening case, broadening the governed proof surface into a mass-based medium with long residence time and explicit combined-loss accounting.",
        "reference_type": "hand_worked_advective_soil_reference_fixture",
        "expected_behavior": "Advective soil concentration follows the same combined-loss equation and trace-level degradation/clearance bookkeeping while remaining storage-dominant under the governed soil residence time.",
        "tolerance_rationale": "The soil advective reference case remains analytically traceable because only medium-specific governed capacity, half-life, and residence-time parameters differ.",
        "tolerance": 1e-12,
        "scientific_claim_ids": [
            "advective_cumulative_mass_balance_closure_v1",
            "advective_residence_time_turnover_regime_v1",
        ],
        "scenario": {
            "chemical_identity": {
                "preferredName": "Benchmark advective soil transport",
                "substance_class": "organic chemical"
            },
            "total_release_mass_kg": 10.0,
            "release_fractions": [{"medium": "soil", "fraction": 1.0}],
            "duration_days": 60.0
        },
        "run_options": {
            "model_family": "advective_screening_mass_balance"
        },
        "expected_surfaces": [
            {
                "medium": "soil",
                "compartment": "agricultural_soil",
                "value": 0.0019094067279895887,
                "unit": "mg/kg"
            }
        ],
        "expected_trace_terms": [
            {
                "medium": "soil",
                "compartment": "agricultural_soil",
                "terms": {
                    "degradation_loss_share_fraction": 0.8061595923300592,
                    "advective_clearance_share_fraction": 0.19384040766994082,
                    "elapsed_turnover_count": 0.33333333333333337,
                    "active_emission_turnover_count": 0.33333333333333337,
                    "retained_mass_fraction_of_finite_plateau": 0.8208671723565526,
                    "cumulative_degraded_mass_mg": 4213379.549729694,
                    "cumulative_advected_mass_mg": 1013103.630296334,
                    "mass_balance_closure_error_mg": 1.5133991837501526e-09
                },
                "tolerance": 1e-12
            }
        ]
    },
    {
        "name": "advective_residence_time_override_sensitivity_fixture",
        "category": "parameter_override_sensitivity",
        "validation_tier": "sensitivity",
        "scientific_basis": "Hand-worked finite-duration advective water screening case where a scenario-specific residence-time override replaces the governed curated default before combined-loss calculation.",
        "reference_type": "hand_worked_advective_override_fixture",
        "expected_behavior": "Advective water concentration reflects the scenario residence-time override through the governed degradation-plus-clearance screening equation.",
        "tolerance_rationale": "Advective override behavior remains deterministic and analytically traceable.",
        "tolerance": 1e-12,
        "scientific_claim_ids": ["advective_residence_time_override_application_v1"],
        "scenario": {
            "chemical_identity": {"preferredName": "Benchmark advective residence override"},
            "total_release_mass_kg": 10.0,
            "release_fractions": [{"medium": "water", "fraction": 1.0}],
            "duration_days": 15.0,
            "parameter_records": [
                {
                    "parameter": "water_residence_time_days",
                    "value": 5.0,
                    "unit": "day",
                    "source_classification": "user_input",
                    "rationale": "Benchmark residence-time override."
                }
            ]
        },
        "run_options": {
            "model_family": "advective_screening_mass_balance"
        },
        "expected_surfaces": [
            {
                "medium": "water",
                "compartment": "surface_water",
                "value": 5.280626079290048e-06,
                "unit": "mg/L"
            }
        ]
    },
    {
        "name": "advective_short_residence_time_clearance_anchor_fixture",
        "category": "edge_condition_anchor",
        "validation_tier": "edge_condition",
        "scientific_basis": "Hand-worked advective water screening case with an effectively non-degrading substance and a short residence time, anchoring clearance-dominant concentration suppression.",
        "reference_type": "hand_worked_advective_clearance_edge_anchor",
        "expected_behavior": "Advective water concentration remains low when short residence-time clearance dominates the total loss term even for an effectively persistent substance.",
        "tolerance_rationale": "The clearance-dominant advective edge anchor is a deterministic closed-form reference calculation.",
        "tolerance": 1e-12,
        "scientific_claim_ids": [
            "advective_short_residence_time_clearance_anchor_v1",
            "advective_residence_time_turnover_regime_v1",
        ],
        "scenario": {
            "chemical_identity": {"preferredName": "Benchmark short residence time"},
            "total_release_mass_kg": 10.0,
            "release_fractions": [{"medium": "water", "fraction": 1.0}],
            "duration_days": 30.0,
            "parameter_records": [
                {
                    "parameter": "water_half_life_days",
                    "value": 100000.0,
                    "unit": "day",
                    "source_classification": "user_input",
                    "rationale": "Benchmark extreme persistence override."
                },
                {
                    "parameter": "water_residence_time_days",
                    "value": 2.0,
                    "unit": "day",
                    "source_classification": "user_input",
                    "rationale": "Benchmark short residence-time override."
                }
            ]
        },
        "run_options": {
            "model_family": "advective_screening_mass_balance"
        },
        "expected_surfaces": [
            {
                "medium": "water",
                "compartment": "surface_water",
                "value": 1.333314441885454e-06,
                "unit": "mg/L"
            }
        ],
        "expected_trace_terms": [
            {
                "medium": "water",
                "compartment": "surface_water",
                "terms": {
                    "elapsed_turnover_count": 15.0,
                    "active_emission_turnover_count": 15.0
                },
                "tolerance": 1e-12
            }
        ]
    },
    {
        "name": "advective_short_residence_time_clearance_companion_fixture",
        "category": "parameter_override_sensitivity",
        "validation_tier": "sensitivity",
        "scientific_basis": "Hand-worked advective water screening case with an effectively persistent substance and a very short residence-time override, corroborating clearance-dominant suppression through a second override regime.",
        "reference_type": "hand_worked_advective_override_fixture",
        "expected_behavior": "Advective water concentration is strongly suppressed when a very short residence-time override further strengthens clearance under effectively persistent conditions.",
        "tolerance_rationale": "The short-residence companion remains a deterministic override case under the governed combined-loss equation.",
        "tolerance": 1e-12,
        "scientific_claim_ids": [
            "advective_short_residence_time_clearance_anchor_v1",
            "advective_residence_time_override_application_v1",
            "advective_residence_time_turnover_regime_v1"
        ],
        "scenario": {
            "chemical_identity": {"preferredName": "Benchmark very short residence time"},
            "total_release_mass_kg": 10.0,
            "release_fractions": [{"medium": "water", "fraction": 1.0}],
            "duration_days": 15.0,
            "parameter_records": [
                {
                    "parameter": "water_half_life_days",
                    "value": 100000.0,
                    "unit": "day",
                    "source_classification": "user_input",
                    "rationale": "Benchmark effective persistence override."
                },
                {
                    "parameter": "water_residence_time_days",
                    "value": 0.5,
                    "unit": "day",
                    "source_classification": "user_input",
                    "rationale": "Benchmark very short residence-time override."
                }
            ]
        },
        "run_options": {
            "model_family": "advective_screening_mass_balance"
        },
        "expected_surfaces": [
            {
                "medium": "water",
                "compartment": "surface_water",
                "value": 6.6666435618401e-07,
                "unit": "mg/L"
            }
        ],
        "expected_trace_terms": [
            {
                "medium": "water",
                "compartment": "surface_water",
                "terms": {
                    "elapsed_turnover_count": 30.0,
                    "active_emission_turnover_count": 30.0
                },
                "tolerance": 1e-12
            }
        ]
    },
    {
        "name": "advective_long_residence_time_accumulation_anchor_fixture",
        "category": "edge_condition_anchor",
        "validation_tier": "edge_condition",
        "scientific_basis": "Hand-worked advective water screening case with effectively persistent degradation and a long residence-time override, anchoring accumulation under weak advective clearance.",
        "reference_type": "hand_worked_advective_residence_edge_anchor",
        "expected_behavior": "Advective water concentration rises materially when a long residence-time override weakens advective clearance under effectively persistent conditions.",
        "tolerance_rationale": "The long-residence advective anchor is a deterministic closed-form reference calculation for the governed combined-loss equation.",
        "tolerance": 1e-12,
        "scientific_claim_ids": [
            "advective_extreme_persistence_clearance_bound_v1",
            "advective_residence_time_override_application_v1",
            "advective_long_residence_time_accumulation_anchor_v1",
            "advective_residence_time_turnover_regime_v1"
        ],
        "scenario": {
            "chemical_identity": {"preferredName": "Benchmark long residence time"},
            "total_release_mass_kg": 10.0,
            "release_fractions": [{"medium": "water", "fraction": 1.0}],
            "duration_days": 30.0,
            "parameter_records": [
                {
                    "parameter": "water_half_life_days",
                    "value": 100000.0,
                    "unit": "day",
                    "source_classification": "user_input",
                    "rationale": "Benchmark effective persistence override."
                },
                {
                    "parameter": "water_residence_time_days",
                    "value": 60.0,
                    "unit": "day",
                    "source_classification": "user_input",
                    "rationale": "Benchmark long residence-time override."
                }
            ]
        },
        "run_options": {
            "model_family": "advective_screening_mass_balance"
        },
        "expected_surfaces": [
            {
                "medium": "water",
                "compartment": "surface_water",
                "value": 1.573727311929898e-05,
                "unit": "mg/L"
            }
        ],
        "expected_trace_terms": [
            {
                "medium": "water",
                "compartment": "surface_water",
                "terms": {
                    "elapsed_turnover_count": 0.5,
                    "active_emission_turnover_count": 0.5
                },
                "tolerance": 1e-12
            }
        ]
    },
    {
        "name": "advective_long_residence_time_accumulation_companion_fixture",
        "category": "parameter_override_sensitivity",
        "validation_tier": "sensitivity",
        "scientific_basis": "Hand-worked advective water screening case with effectively persistent degradation and a longer residence-time override, corroborating weak-clearance accumulation through a second override regime.",
        "reference_type": "hand_worked_advective_override_fixture",
        "expected_behavior": "Advective water concentration rises further when a longer residence-time override weakens advective clearance under effectively persistent conditions.",
        "tolerance_rationale": "The long-residence companion remains a deterministic override case under the governed combined-loss equation.",
        "tolerance": 1e-12,
        "scientific_claim_ids": [
            "advective_long_residence_time_accumulation_anchor_v1",
            "advective_residence_time_override_application_v1",
            "advective_extreme_persistence_clearance_bound_v1",
            "advective_residence_time_turnover_regime_v1"
        ],
        "scenario": {
            "chemical_identity": {"preferredName": "Benchmark very long residence time"},
            "total_release_mass_kg": 10.0,
            "release_fractions": [{"medium": "water", "fraction": 1.0}],
            "duration_days": 30.0,
            "parameter_records": [
                {
                    "parameter": "water_half_life_days",
                    "value": 100000.0,
                    "unit": "day",
                    "source_classification": "user_input",
                    "rationale": "Benchmark effective persistence override."
                },
                {
                    "parameter": "water_residence_time_days",
                    "value": 90.0,
                    "unit": "day",
                    "source_classification": "user_input",
                    "rationale": "Benchmark very long residence-time override."
                }
            ]
        },
        "run_options": {
            "model_family": "advective_screening_mass_balance"
        },
        "expected_surfaces": [
            {
                "medium": "water",
                "compartment": "surface_water",
                "value": 1.7006451169663176e-05,
                "unit": "mg/L"
            }
        ],
        "expected_trace_terms": [
            {
                "medium": "water",
                "compartment": "surface_water",
                "terms": {
                    "elapsed_turnover_count": 0.3333333333333333,
                    "active_emission_turnover_count": 0.3333333333333333
                },
                "tolerance": 1e-12
            }
        ]
    },
    {
        "name": "advective_post_release_decay_anchor_fixture",
        "category": "time_bucket_regression_anchor",
        "validation_tier": "edge_condition",
        "scientific_basis": "Hand-worked advective water time-bucket case with buckets extending beyond the release duration, anchoring post-release combined-loss decay.",
        "reference_type": "hand_worked_advective_post_release_bucket_anchor",
        "expected_behavior": "Advective time-bucket outputs decay after release ends according to the governed combined degradation-plus-clearance loss term.",
        "tolerance_rationale": "The post-release bucket anchor is deterministic and directly traceable to the governed advective bucket equation.",
        "tolerance": 1e-12,
        "scientific_claim_ids": [
            "advective_time_bucket_elapsed_time_v1",
            "advective_post_release_flushing_recovery_v1",
            "advective_post_release_flushing_regime_transition_v1",
            "advective_post_release_flushing_directionality_v1",
            "advective_post_release_half_recovery_pace_v1",
            "advective_post_release_half_recovery_directionality_v1",
        ],
        "scenario": {
            "chemical_identity": {"preferredName": "Benchmark advective post-release decay"},
            "total_release_mass_kg": 10.0,
            "release_fractions": [{"medium": "water", "fraction": 1.0}],
            "duration_days": 10.0
        },
        "run_options": {
            "run_mode": "time_bucket",
            "bucket_count": 4,
            "bucket_duration_days": 5.0,
            "model_family": "advective_screening_mass_balance"
        },
        "expected_surfaces": [
            {
                "medium": "water",
                "compartment": "surface_water",
                "bucket_label": "bucket_1",
                "value": 7.93818012431481e-06,
                "unit": "mg/L"
            },
            {
                "medium": "water",
                "compartment": "surface_water",
                "bucket_label": "bucket_2",
                "value": 1.2845043850017369e-05,
                "unit": "mg/L"
            },
            {
                "medium": "water",
                "compartment": "surface_water",
                "bucket_label": "bucket_3",
                "value": 7.939965928670502e-06,
                "unit": "mg/L"
            },
            {
                "medium": "water",
                "compartment": "surface_water",
                "bucket_label": "bucket_4",
                "value": 4.907967593147857e-06,
                "unit": "mg/L"
            }
        ],
        "expected_trace_terms": [
            {
                "medium": "water",
                "compartment": "surface_water",
                "bucket_label": "bucket_4",
                "terms": {
                    "post_release_elapsed_days": 10.0,
                    "post_release_retained_fraction_of_release_stop_mass": 0.38209037278928565,
                    "post_release_removed_fraction_of_release_stop_mass": 0.6179096272107143,
                    "post_release_degraded_fraction_of_release_stop_mass": 0.2967835309602801,
                    "post_release_advected_fraction_of_release_stop_mass": 0.3211260962504342,
                    "post_release_elapsed_turnover_count": 0.5,
                    "post_release_flushing_boundary_offset_turnovers": -0.5,
                    "post_release_transition_margin_turnovers": 0.5,
                    "post_release_boundary_retained_fraction_of_release_stop_mass": 0.1459930529782552,
                    "post_release_retained_fraction_offset_from_boundary": 0.23609731981103044,
                    "post_release_retained_fraction_ratio_to_boundary": 2.6171818795117305,
                    "post_release_half_recovery_days": 7.20453731154783,
                    "post_release_half_recovery_turnovers": 0.36022686557739153,
                    "post_release_half_recovery_offset_turnovers": 0.13977313442260847,
                    "post_release_half_recovery_transition_margin_turnovers": 0.13977313442260847,
                    "post_release_recovery_window_multiple_of_half_recovery": 1.3880141871111482,
                    "post_release_retained_fraction_offset_from_half_recovery_anchor": -0.11790962721071435,
                    "post_release_retained_fraction_ratio_to_half_recovery_anchor": 0.7641807455785713
                },
                "tolerance": 1e-12
            }
        ]
    },
    {
        "name": "advective_post_release_recovery_reference_fixture",
        "category": "reference_chemical_style",
        "validation_tier": "reference_style",
        "scientific_basis": "Hand-worked advective water time-bucket case expressed directly in release-stop mass recovery terms, anchoring post-release retained, degraded, and advected mass fractions under a bounded flowing-water screening regime.",
        "reference_type": "hand_worked_advective_post_release_recovery_reference_fixture",
        "expected_behavior": "Post-release advective bucket outputs preserve release-stop retained-mass decline with explicit degraded-versus-advected recovery accounting under a reference-style bounded-transport case.",
        "tolerance_rationale": "The reference-style post-release recovery case remains analytically traceable because retained mass at release stop and the subsequent combined-loss decay share the same governed closed-form solution.",
        "tolerance": 1e-12,
        "scientific_claim_ids": [
            "advective_time_bucket_elapsed_time_v1",
            "advective_post_release_flushing_recovery_v1",
            "advective_post_release_flushing_regime_transition_v1",
            "advective_post_release_flushing_directionality_v1",
            "advective_post_release_half_recovery_pace_v1",
            "advective_post_release_half_recovery_directionality_v1",
        ],
        "scenario": {
            "chemical_identity": {"preferredName": "Benchmark advective post-release recovery reference"},
            "total_release_mass_kg": 10.0,
            "release_fractions": [{"medium": "water", "fraction": 1.0}],
            "duration_days": 12.0,
            "parameter_records": [
                {
                    "parameter": "water_half_life_days",
                    "value": 8.0,
                    "unit": "day",
                    "source_classification": "user_input",
                    "rationale": "Reference-style post-release half-life override."
                },
                {
                    "parameter": "water_residence_time_days",
                    "value": 6.0,
                    "unit": "day",
                    "source_classification": "user_input",
                    "rationale": "Reference-style post-release residence-time override."
                }
            ]
        },
        "run_options": {
            "run_mode": "time_bucket",
            "bucket_count": 5,
            "bucket_duration_days": 4.0,
            "model_family": "advective_screening_mass_balance"
        },
        "expected_surfaces": [
            {
                "medium": "water",
                "compartment": "surface_water",
                "bucket_label": "bucket_5",
                "value": 8.256826719727065e-07,
                "unit": "mg/L"
            }
        ],
        "expected_trace_terms": [
            {
                "medium": "water",
                "compartment": "surface_water",
                "bucket_label": "bucket_5",
                "terms": {
                    "post_release_elapsed_days": 8.0,
                    "post_release_retained_fraction_of_release_stop_mass": 0.1317985690578634,
                    "post_release_removed_fraction_of_release_stop_mass": 0.8682014309421366,
                    "post_release_degraded_fraction_of_release_stop_mass": 0.296963809861408,
                    "post_release_advected_fraction_of_release_stop_mass": 0.5712376210807286,
                    "post_release_elapsed_turnover_count": 1.3333333333333333,
                    "post_release_flushing_boundary_offset_turnovers": 0.33333333333333326,
                    "post_release_transition_margin_turnovers": 0.33333333333333326,
                    "post_release_boundary_retained_fraction_of_release_stop_mass": 0.2187424244521521,
                    "post_release_retained_fraction_offset_from_boundary": -0.08694385539428871,
                    "post_release_retained_fraction_ratio_to_boundary": 0.6025286104785454,
                    "post_release_half_recovery_days": 2.7363586308689225,
                    "post_release_half_recovery_turnovers": 0.45605977181148705,
                    "post_release_half_recovery_offset_turnovers": 0.8772735615218462,
                    "post_release_half_recovery_transition_margin_turnovers": 0.8772735615218462,
                    "post_release_recovery_window_multiple_of_half_recovery": 2.9235933878519513,
                    "post_release_retained_fraction_offset_from_half_recovery_anchor": -0.3682014309421366,
                    "post_release_retained_fraction_ratio_to_half_recovery_anchor": 0.2635971381157268
                },
                "tolerance": 1e-12
            }
        ]
    },
    {
        "name": "advective_post_release_pre_half_recovery_sensitivity_fixture",
        "category": "parameter_override_sensitivity",
        "validation_tier": "sensitivity",
        "scientific_basis": "Hand-worked advective water time-bucket case with the same bounded transport setup as the half-recovery boundary and beyond-half reference cases, but with a shorter post-release window so retained release-stop mass remains above the combined-loss 50% anchor.",
        "reference_type": "hand_worked_advective_post_release_pre_half_recovery_sensitivity_fixture",
        "expected_behavior": "Post-release retained mass remains above the combined-loss half-recovery anchor while the recovery window is still shorter than the governed half-recovery pace under the same chemistry and residence-time assumptions used by the half-boundary and beyond-half anchors.",
        "tolerance_rationale": "The pre-half companion remains analytically traceable because the governed closed-form recovery solution is evaluated at an earlier post-release window under the same loss constants as the half-boundary and beyond-half reference cases.",
        "tolerance": 1e-12,
        "scientific_claim_ids": [
            "advective_post_release_half_recovery_pace_v1",
            "advective_post_release_half_recovery_directionality_v1"
        ],
        "scenario": {
            "chemical_identity": {"preferredName": "Benchmark advective pre-half post-release recovery pace sensitivity"},
            "total_release_mass_kg": 10.0,
            "release_fractions": [{"medium": "water", "fraction": 1.0}],
            "duration_days": 12.0,
            "parameter_records": [
                {
                    "parameter": "water_half_life_days",
                    "value": 8.0,
                    "unit": "day",
                    "source_classification": "user_input",
                    "rationale": "Pre-half post-release half-life override."
                },
                {
                    "parameter": "water_residence_time_days",
                    "value": 6.0,
                    "unit": "day",
                    "source_classification": "user_input",
                    "rationale": "Pre-half post-release residence-time override."
                }
            ]
        },
        "run_options": {
            "run_mode": "time_bucket",
            "bucket_count": 7,
            "bucket_duration_days": 2.0,
            "model_family": "advective_screening_mass_balance"
        },
        "expected_surfaces": [
            {
                "medium": "water",
                "compartment": "surface_water",
                "bucket_label": "bucket_7",
                "value": 3.7746800788217333e-06,
                "unit": "mg/L"
            }
        ],
        "expected_trace_terms": [
            {
                "medium": "water",
                "compartment": "surface_water",
                "bucket_label": "bucket_7",
                "terms": {
                    "post_release_elapsed_days": 2.0,
                    "post_release_elapsed_turnover_count": 0.3333333333333333,
                    "post_release_retained_fraction_of_release_stop_mass": 0.6025286104785454,
                    "post_release_half_recovery_days": 2.7363586308689225,
                    "post_release_half_recovery_turnovers": 0.45605977181148705,
                    "post_release_half_recovery_offset_turnovers": -0.12272643847815373,
                    "post_release_half_recovery_transition_margin_turnovers": 0.12272643847815373,
                    "post_release_recovery_window_multiple_of_half_recovery": 0.7308983469629878,
                    "post_release_retained_fraction_offset_from_half_recovery_anchor": 0.10252861047854543,
                    "post_release_retained_fraction_ratio_to_half_recovery_anchor": 1.205057220957091
                },
                "tolerance": 1e-12
            }
        ]
    },
    {
        "name": "advective_post_release_half_recovery_reference_fixture",
        "category": "reference_chemical_style",
        "validation_tier": "reference_style",
        "scientific_basis": "Hand-worked advective water time-bucket case positioned exactly at the combined-loss half-recovery boundary under the same bounded transport setup as the companion pre-half and beyond-half recovery anchors.",
        "reference_type": "hand_worked_advective_post_release_half_recovery_reference_fixture",
        "expected_behavior": "Post-release advective bucket outputs preserve a boundary-sensitive recovery-pace interpretation when retained release-stop mass sits at the governed 50% half-recovery anchor.",
        "tolerance_rationale": "The half-recovery boundary case remains analytically traceable because the retained release-stop mass decays under the same governed closed-form solution, here evaluated at exactly one combined-loss half-life after release stop under the same chemistry and residence-time assumptions as the companion recovery anchors.",
        "tolerance": 1e-12,
        "scientific_claim_ids": [
            "advective_post_release_half_recovery_pace_v1",
            "advective_post_release_half_recovery_directionality_v1"
        ],
        "scenario": {
            "chemical_identity": {"preferredName": "Benchmark advective post-release half-recovery boundary"},
            "total_release_mass_kg": 10.0,
            "release_fractions": [{"medium": "water", "fraction": 1.0}],
            "duration_days": 12.0,
            "parameter_records": [
                {
                    "parameter": "water_half_life_days",
                    "value": 8.0,
                    "unit": "day",
                    "source_classification": "user_input",
                    "rationale": "Half-recovery boundary post-release half-life override."
                },
                {
                    "parameter": "water_residence_time_days",
                    "value": 6.0,
                    "unit": "day",
                    "source_classification": "user_input",
                    "rationale": "Half-recovery boundary post-release residence-time override."
                }
            ]
        },
        "run_options": {
            "run_mode": "time_bucket",
            "bucket_count": 6,
            "bucket_duration_days": 2.456059771811487,
            "model_family": "advective_screening_mass_balance"
        },
        "expected_surfaces": [
            {
                "medium": "water",
                "compartment": "surface_water",
                "bucket_label": "bucket_6",
                "value": 3.13236584385908e-06,
                "unit": "mg/L"
            }
        ],
        "expected_trace_terms": [
            {
                "medium": "water",
                "compartment": "surface_water",
                "bucket_label": "bucket_6",
                "terms": {
                    "post_release_elapsed_days": 2.7363586308689207,
                    "post_release_elapsed_turnover_count": 0.45605977181148677,
                    "post_release_retained_fraction_of_release_stop_mass": 0.5000000000000003,
                    "post_release_half_recovery_days": 2.7363586308689225,
                    "post_release_half_recovery_turnovers": 0.45605977181148705,
                    "post_release_half_recovery_offset_turnovers": -2.7755575615628914e-16,
                    "post_release_half_recovery_transition_margin_turnovers": 2.7755575615628914e-16,
                    "post_release_recovery_window_multiple_of_half_recovery": 0.9999999999999994,
                    "post_release_retained_fraction_offset_from_half_recovery_anchor": 3.3306690738754696e-16,
                    "post_release_retained_fraction_ratio_to_half_recovery_anchor": 1.0000000000000007
                },
                "tolerance": 1e-12
            }
        ]
    },
    {
        "name": "advective_post_release_recovery_sensitivity_fixture",
        "category": "parameter_override_sensitivity",
        "validation_tier": "sensitivity",
        "scientific_basis": "Hand-worked advective water time-bucket case with a shorter half-life and shorter residence time, corroborating post-release flushing and retained-mass decline under a second recovery window.",
        "reference_type": "hand_worked_advective_post_release_recovery_sensitivity_fixture",
        "expected_behavior": "Post-release retained mass declines more aggressively when both degradation and advective clearance strengthen under an alternate recovery-window configuration.",
        "tolerance_rationale": "The sensitivity companion remains analytically traceable because only the governed loss constants and elapsed recovery window differ from the anchor case.",
        "tolerance": 1e-12,
        "scientific_claim_ids": [
            "advective_post_release_flushing_recovery_v1",
            "advective_post_release_flushing_regime_transition_v1"
        ],
        "scenario": {
            "chemical_identity": {"preferredName": "Benchmark advective post-release recovery sensitivity"},
            "total_release_mass_kg": 12.0,
            "release_fractions": [{"medium": "water", "fraction": 1.0}],
            "duration_days": 9.0,
            "parameter_records": [
                {
                    "parameter": "water_half_life_days",
                    "value": 6.0,
                    "unit": "day",
                    "source_classification": "user_input",
                    "rationale": "Sensitivity post-release half-life override."
                },
                {
                    "parameter": "water_residence_time_days",
                    "value": 4.0,
                    "unit": "day",
                    "source_classification": "user_input",
                    "rationale": "Sensitivity post-release residence-time override."
                }
            ]
        },
        "run_options": {
            "run_mode": "time_bucket",
            "bucket_count": 4,
            "bucket_duration_days": 4.5,
            "model_family": "advective_screening_mass_balance"
        },
        "expected_surfaces": [
            {
                "medium": "water",
                "compartment": "surface_water",
                "bucket_label": "bucket_4",
                "value": 2.617289269810636e-07,
                "unit": "mg/L"
            }
        ],
        "expected_trace_terms": [
            {
                "medium": "water",
                "compartment": "surface_water",
                "bucket_label": "bucket_4",
                "terms": {
                    "post_release_elapsed_days": 9.0,
                    "post_release_retained_fraction_of_release_stop_mass": 0.03726425320974901,
                    "post_release_removed_fraction_of_release_stop_mass": 0.962735746790251,
                    "post_release_degraded_fraction_of_release_stop_mass": 0.3042739559054851,
                    "post_release_advected_fraction_of_release_stop_mass": 0.6584617908847659,
                    "post_release_elapsed_turnover_count": 2.25,
                    "post_release_flushing_boundary_offset_turnovers": 1.25,
                    "post_release_transition_margin_turnovers": 1.25,
                    "post_release_boundary_retained_fraction_of_release_stop_mass": 0.23174952587773143,
                    "post_release_retained_fraction_offset_from_boundary": -0.19448527266798243,
                    "post_release_retained_fraction_ratio_to_boundary": 0.16079538056707493
                },
                "tolerance": 1e-12
            }
        ]
    },
    {
        "name": "advective_post_release_extended_flushing_sensitivity_fixture",
        "category": "parameter_override_sensitivity",
        "validation_tier": "sensitivity",
        "scientific_basis": "Hand-worked advective water time-bucket case with the same bounded transport setup as the post-release recovery reference, but with a longer post-release window so retained release-stop mass is anchored further beyond both the one-turnover flushing boundary and the combined-loss half-recovery anchor.",
        "reference_type": "hand_worked_advective_post_release_extended_flushing_sensitivity_fixture",
        "expected_behavior": "Post-release retained mass continues to decline in the expected direction as the recovery window extends further beyond both the one-turnover flushing boundary and the 50% combined-loss half-recovery anchor.",
        "tolerance_rationale": "The extended flushing companion remains analytically traceable because the same governed closed-form solution is evaluated at a longer post-release recovery window under the same loss constants.",
        "tolerance": 1e-12,
        "scientific_claim_ids": [
            "advective_post_release_flushing_regime_transition_v1",
            "advective_post_release_flushing_directionality_v1",
            "advective_post_release_half_recovery_directionality_v1",
            "advective_post_release_late_recovery_regime_v1"
        ],
        "scenario": {
            "chemical_identity": {"preferredName": "Benchmark advective extended post-release flushing sensitivity"},
            "total_release_mass_kg": 10.0,
            "release_fractions": [{"medium": "water", "fraction": 1.0}],
            "duration_days": 12.0,
            "parameter_records": [
                {
                    "parameter": "water_half_life_days",
                    "value": 8.0,
                    "unit": "day",
                    "source_classification": "user_input",
                    "rationale": "Extended flushing post-release half-life override."
                },
                {
                    "parameter": "water_residence_time_days",
                    "value": 6.0,
                    "unit": "day",
                    "source_classification": "user_input",
                    "rationale": "Extended flushing post-release residence-time override."
                }
            ]
        },
        "run_options": {
            "run_mode": "time_bucket",
            "bucket_count": 4,
            "bucket_duration_days": 6.0,
            "model_family": "advective_screening_mass_balance"
        },
        "expected_surfaces": [
            {
                "medium": "water",
                "compartment": "surface_water",
                "bucket_label": "bucket_4",
                "value": 2.9975643704619074e-07,
                "unit": "mg/L"
            }
        ],
        "expected_trace_terms": [
            {
                "medium": "water",
                "compartment": "surface_water",
                "bucket_label": "bucket_4",
                "terms": {
                    "post_release_elapsed_days": 12.0,
                    "post_release_retained_fraction_of_release_stop_mass": 0.04784824825520548,
                    "post_release_removed_fraction_of_release_stop_mass": 0.9521517517447945,
                    "post_release_degraded_fraction_of_release_stop_mass": 0.325678582972979,
                    "post_release_advected_fraction_of_release_stop_mass": 0.6264731687718155,
                    "post_release_elapsed_turnover_count": 2.0,
                    "post_release_flushing_boundary_offset_turnovers": 1.0,
                    "post_release_transition_margin_turnovers": 1.0,
                    "post_release_boundary_retained_fraction_of_release_stop_mass": 0.2187424244521521,
                    "post_release_retained_fraction_offset_from_boundary": -0.17089417619694663,
                    "post_release_retained_fraction_ratio_to_boundary": 0.21874242445215214,
                    "post_release_half_recovery_days": 2.7363586308689225,
                    "post_release_half_recovery_turnovers": 0.45605977181148705,
                    "post_release_half_recovery_offset_turnovers": 1.543940228188513,
                    "post_release_half_recovery_transition_margin_turnovers": 1.543940228188513,
                    "post_release_recovery_window_multiple_of_half_recovery": 4.385390081777927,
                    "post_release_retained_fraction_offset_from_half_recovery_anchor": -0.45215175174479454,
                    "post_release_retained_fraction_ratio_to_half_recovery_anchor": 0.09569649651041095
                },
                "tolerance": 1e-12
            }
        ]
    },
    {
        "name": "advective_post_release_subboundary_directionality_sensitivity_fixture",
        "category": "parameter_override_sensitivity",
        "validation_tier": "sensitivity",
        "scientific_basis": "Hand-worked advective water time-bucket case with the same bounded transport setup as the post-release boundary and recovery reference cases, but with a shorter post-release window so retained release-stop mass remains above the one-turnover anchor under the same loss constants.",
        "reference_type": "hand_worked_advective_post_release_subboundary_sensitivity_fixture",
        "expected_behavior": "Post-release retained mass remains above the one-turnover retained-mass anchor while the recovery window is still sub-boundary under the same chemistry and residence-time assumptions used by the boundary and beyond-boundary anchors.",
        "tolerance_rationale": "The sub-boundary companion remains analytically traceable because the governed closed-form recovery solution is evaluated at an earlier post-release window under the same loss constants as the boundary and recovery reference cases.",
        "tolerance": 1e-12,
        "scientific_claim_ids": [
            "advective_post_release_flushing_directionality_v1"
        ],
        "scenario": {
            "chemical_identity": {"preferredName": "Benchmark advective sub-boundary post-release directionality sensitivity"},
            "total_release_mass_kg": 10.0,
            "release_fractions": [{"medium": "water", "fraction": 1.0}],
            "duration_days": 12.0,
            "parameter_records": [
                {
                    "parameter": "water_half_life_days",
                    "value": 8.0,
                    "unit": "day",
                    "source_classification": "user_input",
                    "rationale": "Sub-boundary post-release half-life override."
                },
                {
                    "parameter": "water_residence_time_days",
                    "value": 6.0,
                    "unit": "day",
                    "source_classification": "user_input",
                    "rationale": "Sub-boundary post-release residence-time override."
                }
            ]
        },
        "run_options": {
            "run_mode": "time_bucket",
            "bucket_count": 3,
            "bucket_duration_days": 5.0,
            "model_family": "advective_screening_mass_balance"
        },
        "expected_surfaces": [
            {
                "medium": "water",
                "compartment": "surface_water",
                "bucket_label": "bucket_3",
                "value": 2.9300092134349478e-06,
                "unit": "mg/L"
            }
        ],
        "expected_trace_terms": [
            {
                "medium": "water",
                "compartment": "surface_water",
                "bucket_label": "bucket_3",
                "terms": {
                    "post_release_elapsed_days": 3.0,
                    "post_release_retained_fraction_of_release_stop_mass": 0.4676990746753217,
                    "post_release_removed_fraction_of_release_stop_mass": 0.5323009253246783,
                    "post_release_degraded_fraction_of_release_stop_mass": 0.18207077890396217,
                    "post_release_advected_fraction_of_release_stop_mass": 0.35023014642071615,
                    "post_release_elapsed_turnover_count": 0.5,
                    "post_release_flushing_boundary_offset_turnovers": -0.5,
                    "post_release_transition_margin_turnovers": 0.5,
                    "post_release_boundary_retained_fraction_of_release_stop_mass": 0.2187424244521521,
                    "post_release_retained_fraction_offset_from_boundary": 0.24895665022316957,
                    "post_release_retained_fraction_ratio_to_boundary": 2.138126958438401
                },
                "tolerance": 1e-12
            }
        ]
    },
    {
        "name": "advective_post_release_boundary_transition_reference_fixture",
        "category": "reference_chemical_style",
        "validation_tier": "reference_style",
        "scientific_basis": "Hand-worked advective water time-bucket case positioned exactly at the one-turnover post-release flushing boundary under the same bounded transport setup as the companion sub-boundary and beyond-boundary recovery anchors.",
        "reference_type": "hand_worked_advective_post_release_boundary_transition_reference_fixture",
        "expected_behavior": "Post-release advective bucket outputs preserve a boundary-sensitive recovery interpretation when the elapsed post-release window equals one full residence-time turnover.",
        "tolerance_rationale": "The boundary-transition case remains analytically traceable because the retained release-stop mass decays under the same governed closed-form solution, here evaluated at exactly one turnover after release stop under the same chemistry and residence-time assumptions as the companion recovery anchors.",
        "tolerance": 1e-12,
        "scientific_claim_ids": [
            "advective_post_release_flushing_regime_transition_v1",
            "advective_post_release_flushing_directionality_v1"
        ],
        "scenario": {
            "chemical_identity": {"preferredName": "Benchmark advective post-release boundary transition"},
            "total_release_mass_kg": 10.0,
            "release_fractions": [{"medium": "water", "fraction": 1.0}],
            "duration_days": 12.0,
            "parameter_records": [
                {
                    "parameter": "water_half_life_days",
                    "value": 8.0,
                    "unit": "day",
                    "source_classification": "user_input",
                    "rationale": "Boundary-transition post-release half-life override."
                },
                {
                    "parameter": "water_residence_time_days",
                    "value": 6.0,
                    "unit": "day",
                    "source_classification": "user_input",
                    "rationale": "Boundary-transition post-release residence-time override."
                }
            ]
        },
        "run_options": {
            "run_mode": "time_bucket",
            "bucket_count": 4,
            "bucket_duration_days": 4.5,
            "model_family": "advective_screening_mass_balance"
        },
        "expected_surfaces": [
            {
                "medium": "water",
                "compartment": "surface_water",
                "bucket_label": "bucket_4",
                "value": 1.370362597913692e-06,
                "unit": "mg/L"
            }
        ],
        "expected_trace_terms": [
            {
                "medium": "water",
                "compartment": "surface_water",
                "bucket_label": "bucket_4",
                "terms": {
                    "post_release_elapsed_days": 6.0,
                    "post_release_retained_fraction_of_release_stop_mass": 0.2187424244521521,
                    "post_release_removed_fraction_of_release_stop_mass": 0.7812575755478479,
                    "post_release_degraded_fraction_of_release_stop_mass": 0.26722511372276037,
                    "post_release_advected_fraction_of_release_stop_mass": 0.5140324618250875,
                    "post_release_elapsed_turnover_count": 1.0,
                    "post_release_flushing_boundary_offset_turnovers": 0.0,
                    "post_release_transition_margin_turnovers": 0.0,
                    "post_release_boundary_retained_fraction_of_release_stop_mass": 0.2187424244521521,
                    "post_release_retained_fraction_offset_from_boundary": 0.0,
                    "post_release_retained_fraction_ratio_to_boundary": 1.0
                },
                "tolerance": 1e-12
            }
        ]
    },
    {
        "name": "external_adapter_equivalence_fixture",
        "category": "external_adapter_normalization_parity",
        "validation_tier": "normalization_parity",
        "scientific_basis": "Governed JSON, CSV, and alternate-unit adapter fixtures resolve to the same canonical concentration surfaces after normalization.",
        "reference_type": "governed_fixture_normalization_parity",
        "expected_behavior": "Normalized import paths produce the same canonical concentration-surface signatures at the Fate MCP contract boundary.",
        "tolerance_rationale": "Normalization parity is structural rather than numeric tolerance-based because each fixture should resolve to the same canonical surfaces.",
        "tolerance": 0.0,
        "scientific_claim_ids": ["external_adapter_canonical_equivalence_v1"],
        "scenario": {
            "chemical_identity": {"preferredName": "Benchmark adapter"},
            "total_release_mass_kg": 8.0,
            "release_fractions": [{"medium": "water", "fraction": 1.0}],
            "duration_days": 10.0,
        },
        "run_options": {
            "model_family": "external_result_adapter"
        },
        "adapter_fixture_paths": [
            "config/adapter-fixtures/illustrative_external_engine_payload.json",
            "config/adapter-fixtures/illustrative_external_engine_payload.csv",
            "config/adapter-fixtures/illustrative_external_engine_payload_alt_units.csv"
        ]
    },
    {
    "name": "advective_post_release_late_recovery_reference_fixture",
    "category": "reference_chemical_style",
    "validation_tier": "reference_style",
    "scientific_basis": "Hand-worked advective water time-bucket reference case with an exceptionally long post-release window, anchoring a stable late-recovery regime governed by the far-beyond-half-recovery depletion authority layer.",
    "reference_type": "hand_worked_advective_post_release_late_recovery_reference_fixture",
    "expected_behavior": "Post-release retained mass drops well below 12.5% of the combined-loss 50% anchor, triggering the late-recovery regime directionality in a reference-style context.",
    "tolerance_rationale": "The late-recovery reference case remains analytically traceable because the exact same governed closed-form solution holds far beyond the half-recovery boundary.",
    "tolerance": 1e-12,
    "scientific_claim_ids": [
        "advective_post_release_late_recovery_regime_v1"
    ],
    "scenario": {
        "chemical_identity": {
            "preferredName": "Benchmark advective late-recovery reference"
        },
        "total_release_mass_kg": 10.0,
        "release_fractions": [
            {
                "medium": "water",
                "fraction": 1.0
            }
        ],
        "duration_days": 12.0,
        "parameter_records": [
            {
                "parameter": "water_half_life_days",
                "value": 8.0,
                "unit": "day",
                "source_classification": "user_input",
                "rationale": "Extended flushing post-release half-life override."
            },
            {
                "parameter": "water_residence_time_days",
                "value": 6.0,
                "unit": "day",
                "source_classification": "user_input",
                "rationale": "Extended flushing post-release residence-time override."
            }
        ]
    },
    "run_options": {
        "run_mode": "time_bucket",
        "bucket_count": 4,
        "bucket_duration_days": 6.0,
        "model_family": "advective_screening_mass_balance"
    },
    "expected_surfaces": [
        {
            "medium": "water",
            "compartment": "surface_water",
            "bucket_label": "bucket_4",
            "value": 2.9975643704619074e-07,
            "unit": "mg/L"
        }
    ],
    "expected_trace_terms": [
        {
            "medium": "water",
            "compartment": "surface_water",
            "bucket_label": "bucket_4",
            "terms": {
                "post_release_elapsed_days": 12.0,
                "post_release_retained_fraction_of_release_stop_mass": 0.04784824825520548,
                "post_release_removed_fraction_of_release_stop_mass": 0.9521517517447945,
                "post_release_degraded_fraction_of_release_stop_mass": 0.325678582972979,
                "post_release_advected_fraction_of_release_stop_mass": 0.6264731687718155,
                "post_release_elapsed_turnover_count": 2.0,
                "post_release_flushing_boundary_offset_turnovers": 1.0,
                "post_release_transition_margin_turnovers": 1.0,
                "post_release_boundary_retained_fraction_of_release_stop_mass": 0.2187424244521521,
                "post_release_retained_fraction_offset_from_boundary": -0.17089417619694663,
                "post_release_retained_fraction_ratio_to_boundary": 0.21874242445215214,
                "post_release_half_recovery_days": 2.7363586308689225,
                "post_release_half_recovery_turnovers": 0.45605977181148705,
                "post_release_half_recovery_offset_turnovers": 1.543940228188513,
                "post_release_half_recovery_transition_margin_turnovers": 1.543940228188513,
                "post_release_recovery_window_multiple_of_half_recovery": 4.385390081777927,
                "post_release_retained_fraction_offset_from_half_recovery_anchor": -0.45215175174479455,
                "post_release_retained_fraction_ratio_to_half_recovery_anchor": 0.09569649651041096
            },
            "tolerance": 1e-12
        }
    ]
},
{
    "name": "advective_post_release_late_recovery_edge_anchor",
    "category": "time_bucket_regression_anchor",
    "validation_tier": "edge_condition",
    "scientific_basis": "Hand-worked advective water time-bucket edge case with an exceptionally long post-release window, anchoring a stable late-recovery regime governed by the far-beyond-half-recovery depletion authority layer.",
    "reference_type": "hand_worked_advective_post_release_late_recovery_edge_anchor",
    "expected_behavior": "Post-release retained mass drops well below 12.5% of the combined-loss 50% anchor, triggering the late-recovery regime directionality in an edge-condition context.",
    "tolerance_rationale": "The late-recovery edge anchor remains analytically traceable because the exact same governed closed-form solution holds far beyond the half-recovery boundary.",
    "tolerance": 1e-12,
    "scientific_claim_ids": [
        "advective_post_release_late_recovery_regime_v1"
    ],
    "scenario": {
        "chemical_identity": {
            "preferredName": "Benchmark advective late-recovery edge anchor"
        },
        "total_release_mass_kg": 10.0,
        "release_fractions": [
            {
                "medium": "water",
                "fraction": 1.0
            }
        ],
        "duration_days": 12.0,
        "parameter_records": [
            {
                "parameter": "water_half_life_days",
                "value": 8.0,
                "unit": "day",
                "source_classification": "user_input",
                "rationale": "Extended flushing post-release half-life override."
            },
            {
                "parameter": "water_residence_time_days",
                "value": 6.0,
                "unit": "day",
                "source_classification": "user_input",
                "rationale": "Extended flushing post-release residence-time override."
            }
        ]
    },
    "run_options": {
        "run_mode": "time_bucket",
        "bucket_count": 4,
        "bucket_duration_days": 6.0,
        "model_family": "advective_screening_mass_balance"
    },
    "expected_surfaces": [
        {
            "medium": "water",
            "compartment": "surface_water",
            "bucket_label": "bucket_4",
            "value": 2.9975643704619074e-07,
            "unit": "mg/L"
        }
    ],
    "expected_trace_terms": [
        {
            "medium": "water",
            "compartment": "surface_water",
            "bucket_label": "bucket_4",
            "terms": {
                "post_release_elapsed_days": 12.0,
                "post_release_retained_fraction_of_release_stop_mass": 0.04784824825520548,
                "post_release_removed_fraction_of_release_stop_mass": 0.9521517517447945,
                "post_release_degraded_fraction_of_release_stop_mass": 0.325678582972979,
                "post_release_advected_fraction_of_release_stop_mass": 0.6264731687718155,
                "post_release_elapsed_turnover_count": 2.0,
                "post_release_flushing_boundary_offset_turnovers": 1.0,
                "post_release_transition_margin_turnovers": 1.0,
                "post_release_boundary_retained_fraction_of_release_stop_mass": 0.2187424244521521,
                "post_release_retained_fraction_offset_from_boundary": -0.17089417619694663,
                "post_release_retained_fraction_ratio_to_boundary": 0.21874242445215214,
                "post_release_half_recovery_days": 2.7363586308689225,
                "post_release_half_recovery_turnovers": 0.45605977181148705,
                "post_release_half_recovery_offset_turnovers": 1.543940228188513,
                "post_release_half_recovery_transition_margin_turnovers": 1.543940228188513,
                "post_release_recovery_window_multiple_of_half_recovery": 4.385390081777927,
                "post_release_retained_fraction_offset_from_half_recovery_anchor": -0.45215175174479455,
                "post_release_retained_fraction_ratio_to_half_recovery_anchor": 0.09569649651041096
            },
            "tolerance": 1e-12
        }
    ]
}
]




def _resolve_repo_root(repo_root: Path | None = None) -> Path:
    return repo_root or Path(__file__).resolve().parents[2]


def _support_anchor_fingerprint(fixture: dict) -> str:
    expected_surface_identity = sorted(
        [
            {
                "medium": surface.get("medium"),
                "compartment": surface.get("compartment"),
                "bucket_label": surface.get("bucket_label"),
            }
            for surface in fixture.get("expected_surfaces", [])
        ],
        key=lambda item: (
            str(item["medium"]),
            str(item["compartment"]),
            str(item["bucket_label"]),
        ),
    )
    fingerprint_payload = {
        "scenario": fixture.get("scenario", {}),
        "run_options": fixture.get("run_options", {}),
        "surface_identity": expected_surface_identity,
        "adapter_fixture_paths": sorted(fixture.get("adapter_fixture_paths", [])),
    }
    return json.dumps(fingerprint_payload, sort_keys=True, separators=(",", ":"))


def _deduplicated_supporting_fixtures(
    supporting_fixtures: list[dict],
) -> tuple[list[dict], list[list[str]]]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for fixture in supporting_fixtures:
        grouped[_support_anchor_fingerprint(fixture)].append(fixture)
    unique_fixtures = []
    duplicate_name_groups: list[list[str]] = []
    for fixtures in grouped.values():
        unique_fixtures.append(fixtures[0])
        if len(fixtures) > 1:
            duplicate_name_groups.append(sorted(fixture["name"] for fixture in fixtures))
    return unique_fixtures, sorted(duplicate_name_groups)


def _support_strength(supporting_fixtures: list[dict]) -> str:
    unique_supporting_fixtures, _ = _deduplicated_supporting_fixtures(supporting_fixtures)
    if not unique_supporting_fixtures:
        return "uncovered"
    validation_tier_count = len(
        {fixture["validation_tier"] for fixture in unique_supporting_fixtures}
    )
    if len(unique_supporting_fixtures) == 1:
        return "single_anchor"
    if validation_tier_count > 1:
        return "multi_anchor_multi_tier"
    return "multi_anchor_single_tier"


def supporting_benchmark_fixtures_for_claim(claim_id: str) -> list[dict]:
    return [
        fixture
        for fixture in BENCHMARK_FIXTURES
        if claim_id in fixture.get("scientific_claim_ids", [])
    ]


def _surface_signature(result) -> list[dict[str, object]]:
    return sorted(
        [
            {
                "medium": surface.medium.value,
                "compartment": surface.compartment.value,
                "bucket_label": surface.time_window.bucket_label,
                "unit": surface.concentration_unit,
                "value": round(surface.concentration_value, 12),
            }
            for surface in result.surfaces
        ],
        key=lambda item: (
            str(item["medium"]),
            str(item["compartment"]),
            str(item["bucket_label"]),
        ),
    )


def scientific_validation_claim_coverage_manifest(
    repo_root: Path | None = None,
) -> ScientificValidationClaimCoverageManifest:
    resolved_repo_root = _resolve_repo_root(repo_root)
    defaults_registry = DefaultsRegistry(resolved_repo_root)
    claims = defaults_registry.list_scientific_validation_claims()
    fixtures_by_claim: dict[str, list[dict]] = defaultdict(list)
    for claim in claims:
        fixtures_by_claim[claim.claim_id] = supporting_benchmark_fixtures_for_claim(claim.claim_id)

    coverage = []
    for claim in claims:
        supporting_fixtures = fixtures_by_claim.get(claim.claim_id, [])
        deduplicated_supporting_fixtures, duplicate_fixture_groups = _deduplicated_supporting_fixtures(
            supporting_fixtures
        )
        supporting_reference_types = sorted(
            {fixture["reference_type"] for fixture in deduplicated_supporting_fixtures}
        )
        supporting_validation_tiers = sorted(
            {fixture["validation_tier"] for fixture in deduplicated_supporting_fixtures}
        )
        supporting_fixture_count = len(deduplicated_supporting_fixtures)
        supporting_validation_tier_count = len(supporting_validation_tiers)
        supporting_categories = sorted(
            {fixture["category"] for fixture in deduplicated_supporting_fixtures}
        )
        satisfies_reference_types = all(
            reference_type in supporting_reference_types
            for reference_type in claim.required_reference_types
        )
        satisfies_validation_tiers = all(
            validation_tier in supporting_validation_tiers
            for validation_tier in claim.required_validation_tiers
        )
        gap_lines = []
        if not deduplicated_supporting_fixtures:
            gap_lines.append("No benchmark fixtures currently support this published scientific claim.")
        if duplicate_fixture_groups:
            gap_lines.append(
                "Duplicate support anchors were collapsed before claim-strength scoring: "
                + "; ".join(", ".join(group) for group in duplicate_fixture_groups)
                + "."
            )
        duplicate_anchor_multi_support_failure = (
            len(duplicate_fixture_groups) > 0
            and len(deduplicated_supporting_fixtures) < 2
            and len(supporting_fixtures) >= 2
        )
        if duplicate_anchor_multi_support_failure:
            gap_lines.append(
                "Duplicate fixtures cannot be counted as independent multi-anchor scientific support."
            )
        if not satisfies_reference_types:
            missing_reference_types = sorted(
                set(claim.required_reference_types) - set(supporting_reference_types)
            )
            gap_lines.append(
                "Missing required reference types: " + ", ".join(missing_reference_types) + "."
            )
        if not satisfies_validation_tiers:
            missing_validation_tiers = sorted(
                set(claim.required_validation_tiers) - set(supporting_validation_tiers)
            )
            gap_lines.append(
                "Missing required validation tiers: " + ", ".join(missing_validation_tiers) + "."
            )
        covered = (
            bool(deduplicated_supporting_fixtures)
            and satisfies_reference_types
            and satisfies_validation_tiers
            and not duplicate_anchor_multi_support_failure
        )
        coverage.append(
            ScientificValidationClaimCoverageRecord(
                claim_id=claim.claim_id,
                display_name=claim.display_name,
                model_family=claim.model_family,
                supported_run_modes=claim.supported_run_modes,
                priority=claim.priority,
                mandatory_for_release=claim.mandatory_for_release,
                covered=covered,
                support_strength=_support_strength(deduplicated_supporting_fixtures),
                supporting_fixture_count=supporting_fixture_count,
                supporting_validation_tier_count=supporting_validation_tier_count,
                supporting_fixture_names=[
                    fixture["name"] for fixture in deduplicated_supporting_fixtures
                ],
                supporting_categories=supporting_categories,
                supporting_reference_types=supporting_reference_types,
                supporting_validation_tiers=supporting_validation_tiers,
                satisfies_required_reference_types=satisfies_reference_types,
                satisfies_required_validation_tiers=satisfies_validation_tiers,
                gap_lines=gap_lines,
            )
        )
    return ScientificValidationClaimCoverageManifest(
        claim_count=len(coverage),
        covered_claim_count=sum(1 for record in coverage if record.covered),
        mandatory_claim_count=sum(1 for record in coverage if record.mandatory_for_release),
        uncovered_mandatory_claim_count=sum(
            1 for record in coverage if record.mandatory_for_release and not record.covered
        ),
        coverage=coverage,
    )


def benchmark_manifest(repo_root: Path | None = None) -> dict:
    resolved_repo_root = _resolve_repo_root(repo_root)
    defaults_registry = DefaultsRegistry(resolved_repo_root)
    claim_manifest = defaults_registry.scientific_validation_claim_manifest()
    claim_coverage = scientific_validation_claim_coverage_manifest(resolved_repo_root)
    return {
        "fixtures": BENCHMARK_FIXTURES,
        "scientificValidationClaimManifest": claim_manifest.model_dump(mode="json"),
        "scientificValidationClaimCoverage": claim_coverage.model_dump(mode="json"),
    }


def _run_native_fixture(fixture: dict, runtime: FateRuntime) -> dict:
    scenario = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(**fixture["scenario"])
    )
    run_options = FateModelRunOptions(
        region_profile_id=scenario.geographic_scope.region_id,
        fit_for_purpose=FitForPurpose.BENCHMARK,
        **fixture.get("run_options", {}),
    )
    result = runtime.estimate(scenario=scenario, run_options=run_options)
    actual_by_key = {
        (
            surface.medium.value,
            surface.compartment.value,
            surface.time_window.bucket_label,
        ): surface
        for surface in result.surfaces
    }
    comparisons = []
    for expected_surface in fixture["expected_surfaces"]:
        key = (
            expected_surface["medium"],
            expected_surface["compartment"],
            expected_surface.get("bucket_label"),
        )
        actual_surface = actual_by_key[key]
        absolute_error = abs(actual_surface.concentration_value - expected_surface["value"])
        comparisons.append(
            {
                "medium": expected_surface["medium"],
                "compartment": expected_surface["compartment"],
                "bucketLabel": expected_surface.get("bucket_label"),
                "expected": expected_surface["value"],
                "actual": actual_surface.concentration_value,
                "unit": expected_surface["unit"],
                "absoluteError": absolute_error,
                "passed": (
                    absolute_error <= fixture["tolerance"]
                    and actual_surface.concentration_unit == expected_surface["unit"]
                ),
            }
        )
    trace_term_comparisons = []
    for expected_trace in fixture.get("expected_trace_terms", []):
        key = (
            expected_trace["medium"],
            expected_trace["compartment"],
            expected_trace.get("bucket_label"),
        )
        actual_surface = actual_by_key[key]
        term_map = {
            term.name: term.value
            for term in (actual_surface.calculation_trace.resolved_terms if actual_surface.calculation_trace else [])
        }
        tolerance = expected_trace.get("tolerance", fixture["tolerance"])
        for term_name, expected_value in expected_trace.get("terms", {}).items():
            actual_value = term_map[term_name]
            absolute_error = abs(float(actual_value) - float(expected_value))
            trace_term_comparisons.append(
                {
                    "medium": expected_trace["medium"],
                    "compartment": expected_trace["compartment"],
                    "bucketLabel": expected_trace.get("bucket_label"),
                    "termName": term_name,
                    "expected": expected_value,
                    "actual": actual_value,
                    "absoluteError": absolute_error,
                    "passed": absolute_error <= tolerance,
                }
            )
    return {
        "name": fixture["name"],
        "category": fixture["category"],
        "validationTier": fixture["validation_tier"],
        "scientificBasis": fixture["scientific_basis"],
        "referenceType": fixture["reference_type"],
        "expectedBehavior": fixture["expected_behavior"],
        "toleranceRationale": fixture["tolerance_rationale"],
        "tolerance": fixture["tolerance"],
        "scientificClaimIds": fixture.get("scientific_claim_ids", []),
        "passed": all(item["passed"] for item in comparisons) and all(
            item["passed"] for item in trace_term_comparisons
        ),
        "comparisons": comparisons,
        "traceTermComparisons": trace_term_comparisons,
        "surfaceCount": len(result.surfaces),
    }


def _run_adapter_equivalence_fixture(fixture: dict, runtime: FateRuntime, repo_root: Path) -> dict:
    scenario = runtime.build_environmental_release_scenario(
        BuildEnvironmentalReleaseScenarioRequest(**fixture["scenario"])
    )
    run_options = FateModelRunOptions(
        region_profile_id=scenario.geographic_scope.region_id,
        fit_for_purpose=FitForPurpose.BENCHMARK,
        **fixture.get("run_options", {}),
    )
    signatures = []
    for relative_path in fixture["adapter_fixture_paths"]:
        payload = load_external_payload(repo_root / relative_path)
        result = normalize_external_payload(
            payload,
            scenario,
            run_options,
            runtime.provenance,
        )
        signatures.append(
            {
                "path": relative_path,
                "signature": _surface_signature(result),
            }
        )
    canonical_signature = signatures[0]["signature"]
    passed = all(item["signature"] == canonical_signature for item in signatures[1:])
    return {
        "name": fixture["name"],
        "category": fixture["category"],
        "validationTier": fixture["validation_tier"],
        "scientificBasis": fixture["scientific_basis"],
        "referenceType": fixture["reference_type"],
        "expectedBehavior": fixture["expected_behavior"],
        "toleranceRationale": fixture["tolerance_rationale"],
        "tolerance": fixture["tolerance"],
        "scientificClaimIds": fixture.get("scientific_claim_ids", []),
        "passed": passed,
        "comparisons": [
            {
                "path": item["path"],
                "matchesCanonical": item["signature"] == canonical_signature,
                "signature": item["signature"],
            }
            for item in signatures
        ],
        "surfaceCount": len(canonical_signature),
    }


def run_benchmarks(repo_root: Path) -> dict:
    runtime = FateRuntime(repo_root)
    results = []
    for fixture in BENCHMARK_FIXTURES:
        if fixture["category"] == "external_adapter_normalization_parity":
            results.append(_run_adapter_equivalence_fixture(fixture, runtime, repo_root))
        else:
            results.append(_run_native_fixture(fixture, runtime))
    claim_coverage = scientific_validation_claim_coverage_manifest(repo_root)

    return {
        "benchmarkCount": len(results),
        "passed": all(item["passed"] for item in results),
        "scientificValidationClaimCoverage": claim_coverage.model_dump(mode="json"),
        "results": results,
    }
