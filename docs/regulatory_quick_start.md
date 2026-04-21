# Regulatory Quick-Start Checklist

This one-page checklist is the **minimum viable review path** for using the Environmental Fate MCP in a bounded screening submission-support workflow. For the full specification, see [`operator_guide.md`](operator_guide.md).

---

## When Not To Use This MCP

- Do not use it for direct-use product exposure, dietary intake, PBPK execution, or final risk characterization.
- Do not use it as a GIS-resolved plume, hydrodynamic transport, or site-specific dispersion engine.
- Do not use it as a public claim of source-engine equivalence for EUSES, EPA transport engines, or other branded external tools.
- Do not use it for unrestricted probabilistic orchestration outside the governed percentile workflow.
- Do not use it as evidence of regulator acceptance or submission approval.

If any of those are your actual question, this MCP should hand off to the appropriate downstream or higher-fidelity tool instead of being stretched past its boundary.

---

## 1. Before You Run

- [ ] **Confirm scope:** You need a *concentration surface* only. Dose, dietary intake, PBPK, and final risk characterization must be performed downstream.
- [ ] **Select model family:**
  - Simple single-medium screening → `reference_mass_balance` (reviewer-grade baseline)
  - Screening with advective loss (water/soil flushing) → `advective_screening_mass_balance` (experimental challenge path, not the promoted baseline)
  - Time-varying release pattern → use `run_mode = time_bucket` with either `reference_mass_balance` or `advective_screening_mass_balance`
  - Reusing a normalized external payload → `external_result_adapter`
- [ ] **Pick a region profile** that matches your regulatory jurisdiction (e.g., `eu_screening_default`, `us_epa_default`).
- [ ] **Gather release evidence:** total mass (kg), release fractions by medium, and duration (days).
- [ ] **Gather physicochemical data:** at minimum, degradation half-lives for each relevant medium.

## 2. Build the Scenario

Use `fate_build_environmental_release_scenario` with:
- `chemical_identity` (CAS RN or preferred name)
- `total_release_mass_kg` (> 0)
- `release_fractions` (sum ≤ 1.0; unallocated mass triggers a warning)
- `duration_days` (> 0)
- `region_id` and `context_label`
- Optional: `parameter_records` for substance-specific half-lives, advective residence times, or capacities
- Optional: `evidence_sources` for study citations

**Red flags that should stop you:**
- Non-positive half-life → will raise a hard error.
- Release fractions sum > 1.0 → will raise a hard error.
- Unsupported unit in a parameter record → will raise a hard error.

## 3. Run the Model

Use `fate_estimate_multimedia_concentrations` with:
- The scenario from Step 2
- `run_options.model_family` = your chosen family
- `run_options.region_profile_id` = same region as the scenario

**What to expect:**
- A list of `ConcentrationSurface` objects, one per medium/compartment/time window.
- A `FateRunSummary` with `run_id`, `model_family`, and `fit_for_purpose`.
- An `integrity_hash` on the bundle for tamper detection.
- A `regulatory_use_disclaimer` reminding you that these are concentrations, not doses.
- A default-evidence posture in reviewer-facing artifacts showing whether the run relied on shipped source-backed defaults, governed overrides, or any legacy continuity assumptions.

## 4. Check Quality Flags

Inspect `result.quality_flags` on every surface. **If any flag has severity `ERROR`, you must escalate.**

Common warnings to expect (and explain in your submission):
- `unallocated_release_fraction` — fractions sum to < 1.0; some mass is unassigned.
- `region_profile` — you are using a generic regional default.
- `heuristic_default_applied` — a parameter fell back to a curated default with limited evidence.
- `temperature_correction_governed` — a non-25 °C scenario triggered governed half-life correction from the 25 °C reference.
- `temperature_correction_clamped_to_governed_range` — your declared temperature fell outside the governed correction range and was boundary-clamped in non-strict mode.

## 5. Check Mass Balance (Advective Runs Only)

For advective model families, verify that `mass_balance_closure_error_mg` in the surface `calculation_trace` is near zero (< 1 µg). If it is large, the run is numerically unstable and must be escalated.

## 6. Run Scientific Review (Recommended)

Use `fate_preview_scientific_review_outcome` to get:
- A fit assessment (does the scenario fit the model family's scope?)
- An uncertainty summary (what drives the result?)
- A review outcome: `acceptable_screening_use`, `qualified_screening_use`, or `escalate_model_review`
- Reviewer-facing default-evidence and applicability lines, including explicit “when not to use this MCP” exclusions in the governed review surfaces

**Do not submit an `escalate_model_review` outcome without expert review.**

## 7. Build the Regulatory Handoff Package

Use `fate_export_regulatory_handoff_package` with:
- `scenario`, `result`, and `bundle`
- A target profile such as `exposure_scenario_mcp_v1` or `toxclaw_orchestration_v1`

**What the package contains:**
- Concentration surfaces ready for downstream exposure/dietary MCPs
- Crosswalk mappings with `semantic_equivalence` annotations for downstream field matching, not source-engine scientific equivalence
- A `regulatory_use_disclaimer` and `integrity_hash`

## 8. Preserve the Audit Trail

For regulated review or submission-support workflows, retain at minimum:
- The scenario JSON (with all parameter records and evidence sources)
- The concentration bundle (with `integrity_hash`)
- The scientific review packet or outcome preview
- The regulatory handoff package
- The run parameter manifest

**Retention period:** follow the applicable program, sponsor, and jurisdictional record-retention requirement. Environmental Fate MCP does not determine the legally required retention period.

## 9. Common Pitfalls

| Pitfall | Why It Happens | What To Do |
|---------|----------------|------------|
| Treating concentration as dose | Skipping the Direct-Use Exposure MCP | Stop. Add the exposure step. |
| Using a generic region for a site-specific submission | Lazy region selection | Switch to a site-specific extension pack or document the conservative screening intent. |
| Ignoring `ERROR` quality flags | Surface-level flags don't block the tool call | Check every surface. Any `ERROR` forces `escalate_model_review`. |
| Silent half-life clamping | Pre-0.1.0 behavior | Now raises `FateValidationError`. Fix your input. |
| Large mass-balance closure error | Numerical edge case in advective plugin | Escalate to expert review. |

## 10. One-Command Sanity Check

If you are unsure whether your inputs are valid, run:

```bash
uv run environmental-fate-mcp-validate
```

This performs the full release validation dossier across artifacts, benchmarks, contracts, defaults, and interoperability checks.

---

*Last updated: 2026-04-17*
