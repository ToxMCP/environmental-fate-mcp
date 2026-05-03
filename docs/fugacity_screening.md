# Fugacity Equilibrium Screening

Environmental Fate MCP v0.4.0 adds `fugacity_equilibrium_screening` as an experimental, non-default concentration `ModelFamily`.

This family is intended for reviewer-facing multimedia partitioning challenges against the reference mass-balance baseline. It is not a general multimedia fate model, not a Level III implementation, not source-engine equivalence to CEMC tools, not calibration evidence, and not regulator acceptance.

## Supported Scope

- Level I equilibrium screening: partitions a scoped total release mass across air, water, soil, and sediment.
- Level II equilibrium persistence screening: partitions a continuous input rate across the same active media and balances it against scalar first-order degradation losses.
- Active denominator media are fixed to air, water, soil, and sediment.
- `requested_media` filters returned surfaces only; it does not change the equilibrium denominator.
- `run_mode` must be `steady_state`; `time_bucket` is rejected.
- Canonical outputs remain `mg/m3` for air/water and `mg/kg` for soil/sediment.

## Required Inputs

Caller-provided scenario parameter records are required for:

- `molecular_weight_g_mol` in `g/mol`
- `henry_law_constant_pa_m3_mol` in `Pa m3/mol`
- `organic_carbon_partition_coefficient_koc_l_kg` in `L/kg`

Scenario temperature is used in the `R * T` air-capacity term. Henry-law temperature correction is not applied in v0.4.0.

## Equations

Level I:

```text
f = total_scoped_moles / sum(Z_i * V_i)
mass_i = f * Z_i * V_i
```

Level II:

```text
f = input_rate_mol_day / sum(k_i * Z_i * V_i)
mass_i = f * Z_i * V_i
loss_i = k_i * mass_i
```

For soil and sediment, the scalar capacity term uses `Z_water * Kd * mass_kg`, with `Kd = Koc * organic_carbon_fraction * 0.001`.

## Boundary

The fugacity path does not implement:

- Level III non-equilibrium intermedia transfer
- advection or deposition between media
- hydrologic routing, GIS routing, catchment routing, SWAT, PRZM, WEPP, or other external model execution
- calibration, parameter fitting, or field validation
- exposure, dose, risk quotient, regulatory decision, or regulator acceptance

Use `reference_mass_balance` as the default reviewer-grade baseline, then run `fugacity_equilibrium_screening` only as an experimental challenge path when equilibrium partitioning is scientifically useful.
