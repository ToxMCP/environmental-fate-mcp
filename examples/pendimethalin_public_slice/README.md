# Pendimethalin Public Worked-Case Slice (UK arable screening)

This example is the canonical public worked-case slice for the Environmental Fate MCP. It demonstrates the deterministic, probabilistic, scientific review, and erosion / sediment lanes on a single coherent UK-arable pendimethalin scenario, with every input, every output, and every SHA-256 integrity hash frozen on disk.

Pendimethalin (CAS 40487-42-1) is a dinitroaniline herbicide widely used on UK arable crops. Its strong sorption to soil (Koc approximately 17 491 L/kg) and moderate persistence make it a useful screening anchor for the multimedia, probabilistic, and particle-bound transport lanes of the MCP at the same time.

## What it shows

- Single-day, 2.5 kg total release of pendimethalin to a 2.5 ha UK winter cereal field (95% to soil, 5% to air).
- Deterministic multimedia concentration surface (soil + air).
- Concentration surface bundle with a frozen SHA-256 `integrity_hash`.
- Probabilistic percentile lane (P50/P90/P95 from a 200-iteration lognormal water DT50 distribution, seed 20260514).
- Scientific review outcome preview.
- Regulatory handoff package with a frozen SHA-256 `integrity_hash`, ready for downstream consumption by Direct-Use Exposure MCP.
- Erosion relevance screen (high, as expected for Koc ~ 17 491 L/kg).
- RUSLE annual soil-loss screen.
- MUSLE event sediment-yield screen.
- Sediment-associated chemical-load handoff for the receiving water step.

## Files

- `source_lock.json`: public source anchors (FOOTPRINT PPDB, ECHA, OECD, RUSLE/MUSLE) and explicit non-claims.
- `inputs/01_release_scenario_request.json`: the canonical scenario build request.
- `inputs/02_run_options_deterministic.json`: deterministic run options.
- `inputs/03_run_options_probabilistic.json`: probabilistic run options.
- `inputs/04_probabilistic_overlay.json`: iteration count, seed, and sample-manifest mode.
- `inputs/05_rusle_request.json`: RUSLE factors for the 2.5 ha field.
- `inputs/06_musle_request.json`: MUSLE event inputs (525 m^3 runoff, 0.18 m^3/s peak rate).
- `inputs/07_chemical_load_request.json`: sediment-bound chemical-load handoff inputs.
  The erosion-relevance screen is driven directly by the scenario built from `01_release_scenario_request.json`; no separate input file is needed.
- `outputs/01_deterministic_result.json` through `outputs/09_sediment_chemical_load_result.json`: frozen Pydantic-dumped outputs.
- `outputs/output_summary.json`: stable numeric checkpoints and expected SHA-256 integrity hashes.
- `limitations.md`: reviewer-facing limitations and backlog.

## How to rebuild

The slice is regenerated and re-verified deterministically:

```bash
.venv/bin/python scripts/generate_pendimethalin_slice.py
.venv/bin/pytest tests/test_pendimethalin_public_slice.py -v
```

The generator script and the regression test share the same pipeline runner at `tests/_pendimethalin_slice_runner.py`, executed inside the `frozen_environment` context manager that freezes UUID factories and `datetime.now()` so the outputs are byte-identical across runs. Any drift between the generator and the test implies a non-determinism regression in the runtime.

## Boundary

This slice is public-source screening evidence. It is **not** a regulatory submission, **not** a site-calibrated UK assessment, and **not** a claim of source-engine equivalence to EUSES / SimpleBox / WEPP. See `limitations.md` and `source_lock.json` non-claims.
