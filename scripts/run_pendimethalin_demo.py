"""End-to-end Environmental Fate MCP demo for pendimethalin.

Runs three real workflows through the actual MCP tool functions:
  1. Reference mass-balance screening for a 30-day formulation-plant release
  2. Advective challenge review against the same release scenario
  3. Erosion / RUSLE / MUSLE / sediment-associated chemical-load handoff

Captures every input, every output, every assumption, the SHA-256 integrity
hashes on the concentration bundle and regulatory handoff package, and every
scientific-review packet line. Renders the result as a clean evidence-pack PDF.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# --- MCP tool surface ---------------------------------------------------------
from fate_mcp.server import (
    fate_build_environmental_release_scenario,
    fate_estimate_multimedia_concentrations,
    fate_estimate_probabilistic_multimedia_concentrations,
    fate_build_concentration_surface_bundle,
    fate_preview_scientific_review_outcome,
    fate_export_regulatory_handoff_package,
    fate_recommend_model_family_selection,
    fate_preview_model_family_challenge_review,
    fate_screen_erosion_transport_relevance,
    fate_estimate_soil_loss_rusle,
    fate_estimate_event_sediment_yield_musle,
    fate_estimate_sediment_associated_chemical_load,
)
from fate_mcp.models import (
    BuildConcentrationSurfaceBundleRequest,
    BuildEnvironmentalReleaseScenarioRequest,
    EstimateEventSedimentYieldMusleRequest,
    EstimateMultimediaConcentrationsRequest,
    EstimateProbabilisticMultimediaConcentrationsRequest,
    EstimateSedimentAssociatedChemicalLoadRequest,
    EstimateSoilLossRusleRequest,
    ExportRegulatoryHandoffPackageRequest,
    FateModelRunOptions,
    Media,
    ModelFamily,
    PreviewModelFamilyChallengeReviewRequest,
    PreviewScientificReviewOutcomeRequest,
    RecommendModelFamilySelectionRequest,
    ReleaseFraction,
    ScreenErosionTransportRelevanceRequest,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT = REPO_ROOT / "out"
OUT.mkdir(exist_ok=True)


# --- Chemical of interest -----------------------------------------------------
# Pendimethalin (CAS 40487-42-1) — dinitroaniline herbicide widely used on
# cereals, vegetables, ornamentals across UK arable; subject to UK active-
# substance renewal under Regulation 1107/2009. Strongly sorbed to soil
# (high Koc), low water solubility, moderately persistent. Drainage and
# edge-of-field runoff are the main exposure pathways to surface water.
CHEM_NAME = "Pendimethalin"
CAS = "40487-42-1"
SUBSTANCE_CLASS = "organic chemical"

# Physchem evidence (representative, screening-grade)
LOG_KOW = 5.18           # FOOTPRINT PPDB
KOC_L_KG = 17_491.0      # FOOTPRINT PPDB
MW_G_MOL = 281.31
HENRY_PA_M3_MOL = 2.728  # FOOTPRINT PPDB
WATER_HALF_LIFE_D = 16.0
SOIL_HALF_LIFE_D = 100.0
AIR_HALF_LIFE_D = 0.45   # photolysis-driven; short


# --- Helpers ------------------------------------------------------------------
def dumps(obj):
    return json.dumps(obj, default=str, indent=2)


def model_dump(obj):
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")
    return obj


def write_json(name: str, obj) -> Path:
    p = OUT / name
    p.write_text(dumps(model_dump(obj)))
    return p


# --- Common scenario builder --------------------------------------------------
def build_scenario(
    *,
    total_mass_kg: float,
    duration_days: float,
    release_fractions: list[ReleaseFraction],
    region_id: str = "eu_screening_default",
    context_label: str = "regional_screening",
    extra_params: list[dict] | None = None,
):
    params = [
        {
            "parameter": "water_half_life_days",
            "value": WATER_HALF_LIFE_D,
            "unit": "day",
            "source_classification": "user_input",
            "evidence_quality": "reference",
            "rationale": "Pendimethalin surface-water DT50 (FOOTPRINT PPDB).",
            "distribution": {
                "distribution_type": "lognormal",
                "parameters": {"mu": 2.77, "sigma": 0.35},
                "bounds": [5.0, 50.0],
                "sampling_basis": "PPDB-reported DT50 range; lognormal screening envelope.",
            },
        },
        {
            "parameter": "soil_half_life_days",
            "value": SOIL_HALF_LIFE_D,
            "unit": "day",
            "source_classification": "user_input",
            "evidence_quality": "reference",
            "rationale": "Pendimethalin field soil DT50 (FOOTPRINT PPDB).",
        },
        {
            "parameter": "air_half_life_days",
            "value": AIR_HALF_LIFE_D,
            "unit": "day",
            "source_classification": "user_input",
            "evidence_quality": "reference",
            "rationale": "Tropospheric OH-radical photodegradation estimate.",
        },
        {
            "parameter": "log_kow",
            "value": LOG_KOW,
            "unit": "log10",
            "source_classification": "user_input",
            "evidence_quality": "reference",
            "rationale": "Pendimethalin log Kow (FOOTPRINT PPDB).",
        },
        {
            "parameter": "organic_carbon_partition_coefficient_koc_l_kg",
            "value": KOC_L_KG,
            "unit": "L/kg",
            "source_classification": "user_input",
            "evidence_quality": "reference",
            "rationale": "Pendimethalin Koc (FOOTPRINT PPDB).",
        },
        {
            "parameter": "molecular_weight_g_mol",
            "value": MW_G_MOL,
            "unit": "g/mol",
            "source_classification": "user_input",
            "evidence_quality": "reference",
            "rationale": "Pendimethalin molecular weight.",
        },
        {
            "parameter": "henry_law_constant_pa_m3_mol",
            "value": HENRY_PA_M3_MOL,
            "unit": "Pa*m3/mol",
            "source_classification": "user_input",
            "evidence_quality": "reference",
            "rationale": "Pendimethalin Henry's law constant (FOOTPRINT PPDB).",
        },
    ]
    if extra_params:
        params.extend(extra_params)

    req = BuildEnvironmentalReleaseScenarioRequest(
        chemical_identity={
            "preferredName": CHEM_NAME,
            "casrn": CAS,
            "substance_class": SUBSTANCE_CLASS,
        },
        total_release_mass_kg=total_mass_kg,
        release_fractions=release_fractions,
        duration_days=duration_days,
        region_id=region_id,
        context_label=context_label,
        timing_pattern="continuous",
        treatment_assumptions=[],
        parameter_records=params,
        evidence_sources=[
            {
                "source_id": "footprint.ppdb.pendimethalin",
                "title": "FOOTPRINT Pesticide Properties DataBase — Pendimethalin",
                "effective_date": "2024-06-01",
                "url": "https://sitem.herts.ac.uk/aeru/ppdb/en/Reports/525.htm",
            },
        ],
        temperature_c=12.0,  # UK annual mean surface-water temperature
    )
    return fate_build_environmental_release_scenario(req)


# ============================================================================
# Example 1 — Reference mass-balance screening
# ============================================================================
def example_1():
    scenario = build_scenario(
        total_mass_kg=120.0,           # 30 d * 4 kg/d formulation-plant release
        duration_days=30.0,
        release_fractions=[
            ReleaseFraction(medium=Media.WATER, fraction=0.85),
            ReleaseFraction(medium=Media.AIR, fraction=0.05),
            ReleaseFraction(medium=Media.SOIL, fraction=0.10),
        ],
    )

    run_opts = FateModelRunOptions(
        run_mode="steady_state",
        model_family=ModelFamily.REFERENCE_MASS_BALANCE,
        region_profile_id="eu_screening_default",
        fit_for_purpose="screening",
    )

    det_result = fate_estimate_multimedia_concentrations(
        EstimateMultimediaConcentrationsRequest(scenario=scenario, run_options=run_opts)
    )

    # Bundle (this is where the SHA-256 integrity_hash is computed)
    bundle = fate_build_concentration_surface_bundle(
        BuildConcentrationSurfaceBundleRequest(result=det_result)
    )

    # Probabilistic percentile run
    prob_result = fate_estimate_probabilistic_multimedia_concentrations(
        EstimateProbabilisticMultimediaConcentrationsRequest(
            scenario=scenario,
            run_options=run_opts,
            iterations=200,
            seed=20260514,
        )
    )

    # Scientific review outcome preview
    review = fate_preview_scientific_review_outcome(
        PreviewScientificReviewOutcomeRequest(scenario=scenario, result=det_result)
    )

    # Regulatory handoff package
    handoff = fate_export_regulatory_handoff_package(
        ExportRegulatoryHandoffPackageRequest(
            scenario=scenario,
            result=det_result,
            handoff_profile_id="exposure_scenario_mcp_v1",
            consumer_name="Direct-Use Exposure MCP",
        )
    )

    write_json("ex1_scenario.json", scenario)
    write_json("ex1_deterministic_result.json", det_result)
    write_json("ex1_bundle.json", bundle)
    write_json("ex1_probabilistic_result.json", prob_result)
    write_json("ex1_review.json", review)
    write_json("ex1_handoff.json", handoff)

    return {
        "scenario": scenario,
        "det": det_result,
        "bundle": bundle,
        "prob": prob_result,
        "review": review,
        "handoff": handoff,
    }


# ============================================================================
# Example 2 — Advective challenge review for the same release
# ============================================================================
def example_2(scenario_ex1):
    # Reuse the Ex.1 scenario but add residence-time evidence for water
    scenario = build_scenario(
        total_mass_kg=120.0,
        duration_days=30.0,
        release_fractions=[
            ReleaseFraction(medium=Media.WATER, fraction=0.85),
            ReleaseFraction(medium=Media.AIR, fraction=0.05),
            ReleaseFraction(medium=Media.SOIL, fraction=0.10),
        ],
        extra_params=[
            {
                "parameter": "surface_water_residence_time_days",
                "value": 4.0,
                "unit": "day",
                "source_classification": "user_input",
                "evidence_quality": "reference",
                "rationale": "Approximate residence time for a small UK lowland river reach.",
            },
        ],
    )

    # Step 1: ask the MCP which family to use
    recommendation = fate_recommend_model_family_selection(
        RecommendModelFamilySelectionRequest(
            scenario=scenario,
            run_mode="steady_state",
            fit_for_purpose="screening",
            selection_profile_id="reference_baseline_advective_challenge_v1",
        )
    )

    # Step 2: run the advective challenge family
    adv_opts = FateModelRunOptions(
        run_mode="steady_state",
        model_family=ModelFamily.ADVECTIVE_SCREENING_MASS_BALANCE,
        region_profile_id="eu_screening_default",
        fit_for_purpose="screening",
    )
    adv_result = fate_estimate_multimedia_concentrations(
        EstimateMultimediaConcentrationsRequest(scenario=scenario, run_options=adv_opts)
    )

    # Step 3: also run baseline reference for direct comparison
    ref_opts = FateModelRunOptions(
        run_mode="steady_state",
        model_family=ModelFamily.REFERENCE_MASS_BALANCE,
        region_profile_id="eu_screening_default",
        fit_for_purpose="screening",
    )
    ref_result = fate_estimate_multimedia_concentrations(
        EstimateMultimediaConcentrationsRequest(scenario=scenario, run_options=ref_opts)
    )

    # Step 4: preview the challenge review (the MCP re-runs baseline+challenge inside)
    challenge_preview = fate_preview_model_family_challenge_review(
        PreviewModelFamilyChallengeReviewRequest(
            scenario=scenario,
            selection_profile_id="reference_baseline_advective_challenge_v1",
            run_mode="steady_state",
            fit_for_purpose="screening",
        )
    )

    write_json("ex2_scenario.json", scenario)
    write_json("ex2_recommendation.json", recommendation)
    write_json("ex2_advective_result.json", adv_result)
    write_json("ex2_reference_result.json", ref_result)
    write_json("ex2_challenge_preview.json", challenge_preview)

    return {
        "scenario": scenario,
        "recommendation": recommendation,
        "advective": adv_result,
        "reference": ref_result,
        "challenge_preview": challenge_preview,
    }


# ============================================================================
# Example 3 — Erosion / sediment-bound chemical-load handoff
# ============================================================================
def example_3():
    # Build a soil-applied agricultural release scenario for screening fit
    scenario = build_scenario(
        total_mass_kg=2.5,            # ~1.0 kg a.s./ha * 2.5 ha
        duration_days=1.0,            # single application day
        release_fractions=[
            ReleaseFraction(medium=Media.SOIL, fraction=1.0),
        ],
        context_label="edge_of_field_screening",
    )

    # Step 1: screen whether particle-bound transport is even relevant
    relevance = fate_screen_erosion_transport_relevance(
        ScreenErosionTransportRelevanceRequest(scenario=scenario)
    )

    # Step 2: RUSLE annual soil loss for a typical UK arable field
    rusle = fate_estimate_soil_loss_rusle(
        EstimateSoilLossRusleRequest(
            rainfall_erosivity_r=85.0,       # ~UK lowland MJ mm ha-1 h-1 yr-1
            soil_erodibility_k=0.30,         # silty loam
            slope_length_steepness_ls=1.2,   # gentle slope, ~100 m
            cover_management_c=0.20,         # winter cereal
            support_practice_p=1.0,          # no support practices
            area_ha=2.5,
        )
    )

    # Step 3: MUSLE event sediment yield for a single design storm
    musle = fate_estimate_event_sediment_yield_musle(
        EstimateEventSedimentYieldMusleRequest(
            runoff_volume_m3=525.0,          # 21 mm runoff * 2.5 ha
            peak_runoff_rate_m3_s=0.18,
            soil_erodibility_k=0.30,
            slope_length_steepness_ls=1.2,
            cover_management_c=0.20,
            support_practice_p=1.0,
        )
    )

    # Step 4: convert sediment yield + topsoil concentration into chemical load
    chem_load = fate_estimate_sediment_associated_chemical_load(
        EstimateSedimentAssociatedChemicalLoadRequest(
            soil_concentration_mg_kg=1.0,    # typical topsoil residue after appn
            sediment_yield_t=musle.sediment_yield_t_event,
            sediment_delivery_ratio=0.35,
            particle_bound_availability_fraction=0.95,  # high Koc = mostly bound
        )
    )

    write_json("ex3_scenario.json", scenario)
    write_json("ex3_relevance.json", relevance)
    write_json("ex3_rusle.json", rusle)
    write_json("ex3_musle.json", musle)
    write_json("ex3_chem_load.json", chem_load)

    return {
        "scenario": scenario,
        "relevance": relevance,
        "rusle": rusle,
        "musle": musle,
        "chem_load": chem_load,
    }


# ============================================================================
# PDF rendering
# ============================================================================
def fmt_num(x, sig=4):
    if isinstance(x, str):
        return x
    if x is None:
        return "—"
    if isinstance(x, bool):
        return str(x)
    if isinstance(x, (int,)):
        return f"{x:,}"
    if isinstance(x, float):
        if x == 0.0:
            return "0"
        if abs(x) < 1e-3 or abs(x) >= 1e6:
            return f"{x:.{sig}e}"
        return f"{x:,.{sig}g}"
    return str(x)


def build_pdf(ex1, ex2, ex3, out_path: Path):
    styles = getSampleStyleSheet()
    title_st = ParagraphStyle(
        "Title", parent=styles["Title"], fontSize=20, leading=24, spaceAfter=8
    )
    h1 = ParagraphStyle(
        "H1", parent=styles["Heading1"], fontSize=15, leading=20,
        textColor=colors.HexColor("#0b3d2e"), spaceBefore=16, spaceAfter=8,
    )
    h2 = ParagraphStyle(
        "H2", parent=styles["Heading2"], fontSize=12, leading=16,
        textColor=colors.HexColor("#2e6f55"), spaceBefore=10, spaceAfter=4,
    )
    body = ParagraphStyle(
        "Body", parent=styles["BodyText"], fontSize=9.5, leading=13, alignment=TA_LEFT,
        spaceAfter=4,
    )
    small = ParagraphStyle(
        "Small", parent=styles["BodyText"], fontSize=8, leading=11,
        textColor=colors.HexColor("#555555"),
    )
    code = ParagraphStyle(
        "Code", parent=styles["BodyText"], fontSize=7.8, leading=10,
        fontName="Courier", textColor=colors.HexColor("#222222"),
    )

    doc = SimpleDocTemplate(
        str(out_path),
        pagesize=A4,
        leftMargin=1.6 * cm, rightMargin=1.6 * cm,
        topMargin=1.6 * cm, bottomMargin=1.6 * cm,
        title="Environmental Fate MCP — Pendimethalin Demonstration Pack",
        author="Environmental Fate MCP v0.5.0",
    )

    story = []

    # ---------------- Title page ----------------
    story.append(Paragraph("Environmental Fate MCP", title_st))
    story.append(Paragraph(
        "Worked demonstration pack for ecotoxicologists in regulatory exposure",
        ParagraphStyle("Sub", parent=styles["Heading2"], fontSize=13,
                       textColor=colors.HexColor("#444444"), spaceAfter=12),
    ))
    story.append(Paragraph(
        "Test substance: <b>Pendimethalin</b> (CAS 40487-42-1) — dinitroaniline herbicide.<br/>"
        "Test region: UK arable / lowland surface water, EU regional screening defaults.<br/>"
        f"Run timestamp: {datetime.now(timezone.utc).isoformat(timespec='seconds')}<br/>"
        "Package version: environmental-fate-mcp 0.5.0 (ready_for_screening_release)",
        body,
    ))
    story.append(Spacer(1, 0.4 * cm))
    story.append(Paragraph(
        "This pack was generated by invoking the actual MCP tool functions "
        "(fate_build_environmental_release_scenario, fate_estimate_multimedia_concentrations, "
        "fate_screen_erosion_transport_relevance, etc.) against the deterministic v1 defaults pack "
        "that ships with the server. Every concentration value, every assumption record, every "
        "SHA-256 integrity hash below was emitted by the running server — none of it is fabricated.",
        body,
    ))
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph("<b>What this pack contains</b>", h2))
    story.append(Paragraph(
        "1.  Reference mass-balance screening for a 30-day formulation-plant release<br/>"
        "2.  Advective challenge review for the same release vs. residence-time clearance<br/>"
        "3.  RUSLE / MUSLE / sediment-bound chemical-load screening for an edge-of-field event",
        body,
    ))
    story.append(Paragraph(
        "<b>Regulatory-use disclaimer.</b> This MCP produces concentration surfaces and "
        "downstream handoff packages. It is not a final risk engine, not a dose engine, "
        "and not a regulator-accepted submission tool. The <i>ready_for_screening_release</i> "
        "gate is an internal product status, not regulator acceptance.",
        small,
    ))
    story.append(PageBreak())

    # ============= Pendimethalin context ==========
    story.append(Paragraph("Substance under screening", h1))
    chem_rows = [
        ["Preferred name", CHEM_NAME],
        ["CAS RN", CAS],
        ["Substance class", SUBSTANCE_CLASS],
        ["Molecular weight (g/mol)", fmt_num(MW_G_MOL)],
        ["log Kow", fmt_num(LOG_KOW)],
        ["Koc (L/kg)", fmt_num(KOC_L_KG)],
        ["Henry's law constant (Pa·m³/mol)", fmt_num(HENRY_PA_M3_MOL)],
        ["Water DT50 (days)", fmt_num(WATER_HALF_LIFE_D)],
        ["Soil DT50 (days)", fmt_num(SOIL_HALF_LIFE_D)],
        ["Air DT50 (days)", fmt_num(AIR_HALF_LIFE_D)],
        ["Evidence source", "FOOTPRINT Pesticide Properties DataBase"],
    ]
    t = Table(chem_rows, colWidths=[6 * cm, 10.5 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eef4f0")),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#0b3d2e")),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cccccc")),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph(
        "Pendimethalin is a strongly sorbing, low-volatility, moderately persistent herbicide. "
        "Its dominant environmental exposure pathway to UK surface water is via particle-bound "
        "edge-of-field runoff, with secondary contribution from down-the-drain releases at "
        "formulation/manufacturing sites. We exercise all three pathways below.",
        body,
    ))
    story.append(PageBreak())

    # ============================================================
    # Example 1
    # ============================================================
    story.append(Paragraph("Example 1 — Reference mass-balance screening", h1))
    story.append(Paragraph(
        "<b>Question.</b> A pesticide formulation plant discharges treated effluent to a UK lowland "
        "river for 30 days during the spring application window. Total release across all media is "
        "120 kg, allocated as 85% to surface water, 10% to soil, 5% to air. What concentration surface "
        "should downstream exposure tools work from, and how robust is it?",
        body,
    ))
    story.append(Paragraph("Step 1 — Build the environmental release scenario", h2))
    scen = ex1["scenario"]
    story.append(Paragraph(
        f"Tool: <font face='Courier'>fate_build_environmental_release_scenario</font><br/>"
        f"Returned scenario_id: <b><font face='Courier'>{scen.scenario_id}</font></b><br/>"
        f"Region profile: {scen.geographic_scope.region_id} · "
        f"Temperature: {scen.temperature_c} °C · Duration: {scen.duration_days} d · "
        f"Total mass: {scen.total_release_mass_kg} kg",
        body,
    ))

    rows = [["Medium", "Release fraction"]] + [
        [f.medium.value, fmt_num(f.fraction)] for f in scen.release_fractions
    ]
    story.append(_styled_table(rows, [5.5 * cm, 4 * cm]))

    if scen.quality_flags or scen.limitations:
        story.append(Spacer(1, 0.2 * cm))
        story.append(Paragraph("Quality flags & limitations on the input scenario:", body))
        for lim in scen.limitations:
            story.append(Paragraph(f"• <b>{lim.code}</b>: {lim.message}", small))
        for q in scen.quality_flags:
            story.append(Paragraph(f"• [{q.severity.value}] <b>{q.code}</b>: {q.message}", small))

    story.append(Paragraph("Step 2 — Estimate multimedia concentrations (deterministic)", h2))
    det = ex1["det"]
    story.append(Paragraph(
        f"Tool: <font face='Courier'>fate_estimate_multimedia_concentrations</font> "
        f"(model_family = <b>reference_mass_balance</b>, run_mode = steady_state)<br/>"
        f"run_id: <font face='Courier'>{det.run_summary.run_id}</font> · "
        f"surfaces emitted: {det.run_summary.surfaces_emitted}",
        body,
    ))
    surf_rows = [["Medium", "Compartment", "Concentration", "Unit", "Mass-balance closure (mg)"]]
    for s in det.surfaces:
        closure = next(
            (t.value for t in s.calculation_trace.resolved_terms
             if t.name == "mass_balance_closure_error_mg"),
            "—",
        )
        surf_rows.append([
            s.medium.value, s.compartment.value if hasattr(s.compartment, "value") else str(s.compartment),
            fmt_num(s.concentration_value), s.concentration_unit, fmt_num(closure),
        ])
    story.append(_styled_table(surf_rows, [2.5 * cm, 4 * cm, 3.2 * cm, 2.0 * cm, 4.0 * cm]))

    story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph(
        "Equation used (every surface): <font face='Courier'>"
        "C(t) = (R / (k · V)) · (1 − exp(−k·t))</font> — finite-duration continuous first-order screening.",
        small,
    ))

    story.append(Paragraph("Step 3 — Build the concentration surface bundle (with SHA-256 hash)", h2))
    bundle = ex1["bundle"]
    story.append(Paragraph(
        f"Tool: <font face='Courier'>fate_build_concentration_surface_bundle</font><br/>"
        f"bundle_id: <font face='Courier'>{bundle.bundle_id}</font><br/>"
        f"Tamper-evident SHA-256 <b>integrity_hash</b>:",
        body,
    ))
    story.append(Paragraph(f"<font face='Courier'>{bundle.integrity_hash}</font>", code))
    story.append(Paragraph(
        f"This hash is recomputed from the canonical JSON of every surface, assumption, and run-summary "
        f"field. Any byte-level edit to the bundle invalidates it. The bundle currently carries "
        f"{len(bundle.assumptions)} explicit assumption records.",
        small,
    ))

    story.append(Paragraph("Step 4 — Probabilistic percentile orchestration (P50 / P90 / P95)", h2))
    prob = ex1["prob"]
    # The probabilistic result emits three parallel surface lists; align by (medium, compartment).
    def _key(s):
        return (s.medium.value, str(s.compartment))
    p50_by = {_key(s): s for s in prob.median_surfaces}
    p90_by = {_key(s): s for s in prob.p90_surfaces}
    p95_by = {_key(s): s for s in prob.p95_surfaces}
    prob_rows = [["Medium", "P50", "P90", "P95", "Unit"]]
    for k, s in p50_by.items():
        prob_rows.append([
            s.medium.value,
            fmt_num(s.concentration_value),
            fmt_num(p90_by.get(k).concentration_value if p90_by.get(k) else None),
            fmt_num(p95_by.get(k).concentration_value if p95_by.get(k) else None),
            s.concentration_unit,
        ])
    story.append(_styled_table(prob_rows, [2.5 * cm, 3 * cm, 3 * cm, 3 * cm, 2 * cm]))
    story.append(Paragraph(
        f"Iterations: {prob.iteration_count} requested · "
        f"{prob.completed_iteration_count} successful · "
        f"{prob.failed_iteration_count} failed · "
        f"seed: {prob.sampling_seed} · "
        f"sampled parameters: {prob.sampled_parameter_count}",
        small,
    ))

    story.append(Paragraph("Step 5 — Scientific review preview", h2))
    rev = ex1["review"]
    outcome = rev.review_outcome.value if hasattr(rev.review_outcome, "value") else str(rev.review_outcome)
    status = rev.review_status.value if hasattr(rev.review_status, "value") else str(rev.review_status)
    story.append(Paragraph(
        f"Review outcome: <b>{outcome}</b> · Review status: <b>{status}</b><br/>"
        f"Model family under review: {rev.model_family.value}",
        body,
    ))
    if rev.outcome_lines:
        story.append(Paragraph("Outcome lines emitted by the MCP:", small))
        for line in rev.outcome_lines[:8]:
            story.append(Paragraph(f"• {line}", small))
    if rev.recommended_actions:
        story.append(Paragraph("Recommended next actions:", small))
        for line in rev.recommended_actions[:6]:
            story.append(Paragraph(f"• {line}", small))

    story.append(Paragraph("Step 6 — Regulatory handoff package (hash-stamped, downstream-ready)", h2))
    ho = ex1["handoff"]
    story.append(Paragraph(
        f"Tool: <font face='Courier'>fate_export_regulatory_handoff_package</font><br/>"
        f"Profile: <b>{ho.handoff_profile_id}</b> → consumer: {ho.target_modules or ['Direct-Use Exposure MCP']}<br/>"
        f"package_id: <font face='Courier'>{ho.package_id}</font><br/>"
        f"Tamper-evident SHA-256 <b>integrity_hash</b>:",
        body,
    ))
    story.append(Paragraph(f"<font face='Courier'>{ho.integrity_hash}</font>", code))
    story.append(Paragraph(
        f"Crosswalk entries: {len(ho.crosswalk_entries)} · Limitations attached: {len(ho.limitations)} · "
        f"Blockers: {len(ho.blockers)}",
        small,
    ))
    story.append(Paragraph(
        f"<i>Disclaimer carried in the package:</i> {ho.regulatory_use_disclaimer}",
        small,
    ))
    story.append(PageBreak())

    # ============================================================
    # Example 2
    # ============================================================
    story.append(Paragraph("Example 2 — Advective challenge review", h1))
    story.append(Paragraph(
        "<b>Question.</b> The reference family treats the receiving water as a single well-mixed box "
        "with first-order degradation. For a flowing UK river with ~4-day residence time, advective "
        "clearance may dominate degradation. The MCP exposes this as a <i>governed challenge path</i> "
        "(experimental family) that a reviewer can compare against the baseline.",
        body,
    ))

    story.append(Paragraph("Step 1 — Model-family selection recommendation", h2))
    rec = ex2["recommendation"]
    status = rec.recommendation_status.value if hasattr(rec.recommendation_status, "value") else str(rec.recommendation_status)
    primary = rec.primary_model_family.value if hasattr(rec.primary_model_family, "value") else str(rec.primary_model_family)
    challenge = rec.challenge_model_family.value if hasattr(rec.challenge_model_family, "value") else str(rec.challenge_model_family) if rec.challenge_model_family else "—"
    story.append(Paragraph(
        f"Tool: <font face='Courier'>fate_recommend_model_family_selection</font><br/>"
        f"Status: <b>{status}</b><br/>"
        f"Primary family: <b>{primary}</b> · Challenge family: <b>{challenge}</b>",
        body,
    ))
    if rec.summary_lines:
        story.append(Paragraph("Selection-summary lines emitted by the MCP:", small))
        for line in rec.summary_lines[:6]:
            story.append(Paragraph(f"• {line}", small))
    if rec.recommended_actions:
        story.append(Paragraph("Recommended actions:", small))
        for line in rec.recommended_actions[:4]:
            story.append(Paragraph(f"• {line}", small))

    story.append(Paragraph("Step 2 — Run baseline (reference_mass_balance)", h2))
    ref = ex2["reference"]
    story.append(_surface_table(ref.surfaces, [Media.WATER]))

    story.append(Paragraph("Step 3 — Run challenge family (advective_screening_mass_balance)", h2))
    adv = ex2["advective"]
    story.append(_surface_table(adv.surfaces, [Media.WATER]))

    story.append(Paragraph("Step 4 — Challenge review preview", h2))
    ch = ex2["challenge_preview"]
    rev_status = ch.review_status.value if hasattr(ch.review_status, "value") else str(ch.review_status)
    comp_outcome = ch.comparison_outcome.value if hasattr(ch.comparison_outcome, "value") else str(ch.comparison_outcome)
    story.append(Paragraph(
        f"Tool: <font face='Courier'>fate_preview_model_family_challenge_review</font><br/>"
        f"Review status: <b>{rev_status}</b> · Comparison outcome: <b>{comp_outcome}</b><br/>"
        f"Challenge profile: {ch.challenge_review_profile_id}",
        body,
    ))
    if ch.governing_rule_lines:
        story.append(Paragraph("Governing-rule lines emitted by the MCP:", small))
        for line in ch.governing_rule_lines[:5]:
            story.append(Paragraph(f"• {line}", small))
    if ch.dominant_delta_lines:
        story.append(Paragraph("Baseline-vs-challenge dominant deltas:", small))
        for line in ch.dominant_delta_lines[:6]:
            story.append(Paragraph(f"• {line}", small))
    if ch.recommended_actions:
        story.append(Paragraph("Recommended actions:", small))
        for line in ch.recommended_actions[:4]:
            story.append(Paragraph(f"• {line}", small))
    story.append(PageBreak())

    # ============================================================
    # Example 3
    # ============================================================
    story.append(Paragraph("Example 3 — Erosion / sediment-bound chemical-load handoff", h1))
    story.append(Paragraph(
        "<b>Question.</b> Pendimethalin has Koc ≈ 17 500 L/kg, so the realistic pathway to water is "
        "particle-bound runoff from treated fields, not dissolved transport. We screen the relevance, "
        "estimate event-scale soil loss and sediment yield, and emit a chemical-load handoff that a "
        "downstream water-body model can consume.",
        body,
    ))

    story.append(Paragraph("Step 1 — Particle-bound relevance screen", h2))
    rel = ex3["relevance"]
    rel_level = rel.relevance_level.value if hasattr(rel.relevance_level, "value") else str(rel.relevance_level)
    story.append(Paragraph(
        f"Tool: <font face='Courier'>fate_screen_erosion_transport_relevance</font><br/>"
        f"Relevance level: <b>{rel_level}</b> · "
        f"Particle-bound transport plausible: <b>{rel.particle_bound_transport_plausible}</b>",
        body,
    ))
    if rel.driver_lines:
        story.append(Paragraph("Driver lines emitted by the MCP:", small))
        for line in rel.driver_lines[:5]:
            story.append(Paragraph(f"• {line}", small))
    if rel.recommended_next_steps:
        story.append(Paragraph("Recommended next steps:", small))
        for line in rel.recommended_next_steps[:4]:
            story.append(Paragraph(f"• {line}", small))

    story.append(Paragraph("Step 2 — RUSLE annual soil-loss screen", h2))
    r = ex3["rusle"]
    rusle_rows = [
        ["Equation", "A = R x K x LS x C x P"],
        ["R (MJ mm / ha / h / yr)", fmt_num(85.0)],
        ["K", fmt_num(0.30)],
        ["LS", fmt_num(1.2)],
        ["C", fmt_num(0.20)],
        ["P", fmt_num(1.0)],
        ["Area (ha)", fmt_num(2.5)],
        ["Annual soil loss A (t / ha / yr)", fmt_num(r.annual_soil_loss_t_ha_yr)],
        ["Total annual soil loss (t / yr)", fmt_num(r.total_soil_loss_t_yr)],
    ]
    story.append(_kv_table(rusle_rows))

    story.append(Paragraph("Step 3 — MUSLE event sediment yield", h2))
    m = ex3["musle"]
    musle_rows = [
        ["Equation", "Y = 11.8 x (Q x q_p)^0.56 x K x LS x C x P"],
        ["Runoff volume Q (m3)", fmt_num(525.0)],
        ["Peak rate q_p (m3/s)", fmt_num(0.18)],
        ["K x LS x C x P", "0.30 x 1.2 x 0.20 x 1.0"],
        ["Event sediment yield (t)", fmt_num(m.sediment_yield_t_event)],
    ]
    story.append(_kv_table(musle_rows))

    story.append(Paragraph("Step 4 — Sediment-associated chemical-load handoff", h2))
    cl = ex3["chem_load"]
    cl_rows = [
        ["Topsoil pendimethalin (mg/kg)", fmt_num(1.0)],
        ["Sediment delivery ratio (SDR)", fmt_num(0.35)],
        ["Particle-bound availability fraction", fmt_num(0.95)],
        ["Sediment yield from MUSLE (t)", fmt_num(m.sediment_yield_t_event)],
        ["Sediment-associated chemical load (kg)", fmt_num(cl.sediment_associated_load_kg)],
    ]
    story.append(_kv_table(cl_rows))
    story.append(Paragraph(
        "This load object is what the MCP hands off to a downstream receiving-water model. "
        "Crucially the MCP <b>does not</b> compute the resulting water concentration here — "
        "WEPP, channel routing, and dilution are explicitly out of scope.",
        small,
    ))
    story.append(PageBreak())

    # ============= Audit-trail summary =========
    story.append(Paragraph("Audit-trail summary", h1))
    story.append(Paragraph(
        "Every run above produced explicit run-IDs, assumption records, and tamper-evident "
        "SHA-256 hashes. For a regulatory dossier you would retain the JSON payloads from each "
        "step alongside this PDF. Below are the identifiers an auditor would re-verify.",
        body,
    ))
    audit_rows = [["Artifact", "Identifier / hash"]]
    audit_rows += [
        ["Ex.1 scenario_id", ex1["scenario"].scenario_id],
        ["Ex.1 deterministic run_id", ex1["det"].run_summary.run_id],
        ["Ex.1 bundle_id", ex1["bundle"].bundle_id],
        ["Ex.1 bundle SHA-256", ex1["bundle"].integrity_hash or "—"],
        ["Ex.1 probabilistic run_id", ex1["prob"].run_summary.run_id],
        ["Ex.1 handoff package_id", ex1["handoff"].package_id],
        ["Ex.1 handoff SHA-256", ex1["handoff"].integrity_hash or "—"],
        ["Ex.2 scenario_id", ex2["scenario"].scenario_id],
        ["Ex.2 reference run_id", ex2["reference"].run_summary.run_id],
        ["Ex.2 advective run_id", ex2["advective"].run_summary.run_id],
        ["Ex.3 scenario_id", ex3["scenario"].scenario_id],
    ]
    audit_t = Table(audit_rows, colWidths=[4.3 * cm, 13.2 * cm])
    audit_t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0b3d2e")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (1, 1), (1, -1), "Courier"),
        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cccccc")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(audit_t)
    story.append(Spacer(1, 0.4 * cm))
    story.append(Paragraph(
        "All raw JSON for each step is written next to this PDF "
        "(<font face='Courier'>out/ex1_*.json</font>, <font face='Courier'>ex2_*.json</font>, "
        "<font face='Courier'>ex3_*.json</font>).",
        small,
    ))

    doc.build(story)


def _styled_table(rows, col_widths):
    t = Table(rows, colWidths=col_widths)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2e6f55")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cccccc")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.HexColor("#ffffff"), colors.HexColor("#f4f8f6")]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return t


def _kv_table(rows):
    t = Table(rows, colWidths=[7 * cm, 9 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eef4f0")),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cccccc")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return t


def _surface_table(surfaces, media_filter):
    rows = [["Medium", "Concentration", "Unit", "Decay constant (1/day)", "Loss τ (day)"]]
    for s in surfaces:
        if media_filter and s.medium not in media_filter:
            continue
        terms = {t.name: t.value for t in s.calculation_trace.resolved_terms}
        rows.append([
            s.medium.value,
            fmt_num(s.concentration_value),
            s.concentration_unit,
            fmt_num(terms.get("decay_constant_per_day", "—")),
            fmt_num(terms.get("loss_characteristic_time_days", "—")),
        ])
    return _styled_table(rows, [2.5 * cm, 3.5 * cm, 2 * cm, 4 * cm, 3.5 * cm])


# ============================================================================
def main():
    print("Running Example 1 — reference mass-balance screening …")
    ex1 = example_1()
    print("Running Example 2 — advective challenge …")
    ex2 = example_2(ex1["scenario"])
    print("Running Example 3 — erosion / sediment chemical-load …")
    ex3 = example_3()
    pdf_path = OUT / "Environmental_Fate_MCP_Pendimethalin_Demonstration.pdf"
    print(f"Rendering PDF → {pdf_path}")
    build_pdf(ex1, ex2, ex3, pdf_path)
    print("Done.")


if __name__ == "__main__":
    main()
