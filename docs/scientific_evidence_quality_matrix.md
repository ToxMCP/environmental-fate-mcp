# Scientific Evidence-Quality Matrix

Environmental Fate MCP v0.5.0 adds a governed evidence-quality matrix for public release review. It does not add a new model family, concentration kernel, hydrology workflow, calibration workflow, or regulatory acceptance claim.

The matrix is exposed through:

- `defaults://scientific-evidence-quality-rubric`
- `release://scientific-evidence-quality-matrix-report`

## What It Does

The report maps every governed scientific validation claim and each public model-family lane into one evidence tier:

- `reviewer_grade_screening`
- `source_grounded_screening`
- `internal_oracle_screening`
- `synthetic_demo_only`
- `deferred_or_gap`

This makes the release posture easier to audit. A reviewer can quickly see which claims are reviewer-grade bounded-screening anchors, which claims are source-grounded but experimental, which claims are internal-oracle checks, and which lanes are intentionally deferred.

## What It Does Not Do

The matrix is not field validation, calibration evidence, source-engine equivalence, regulator acceptance, or proof of full multimedia fate realism.

It also does not change the v0.5.0 modeling boundary:

- no GIS or catchment routing
- no rainfall-runoff generation
- no WEPP, SWAT, PRZM, or source-engine execution
- no Level III fugacity intermedia-transfer implementation
- no calibration or optimization workflow
- no receiving-water concentration, dose, risk quotient, or regulatory decision

## How To Interpret It

Use `reviewer_grade_screening` for the strongest bounded-screening evidence posture in this MCP. In v0.5.0, that role belongs to the reference mass-balance family.

Use `source_grounded_screening` for covered, source-backed lanes that remain experimental or below the reviewer-grade reference bar. This includes the advective challenge family and the experimental fugacity equilibrium screening family.

Use `internal_oracle_screening` for deterministic repo-behavior or normalization-parity evidence. This is useful, but it should not be mistaken for external scientific corroboration.

Use `synthetic_demo_only` for workflow demonstrations and QA orientation. Synthetic demos are intentionally separated from benchmark and field evidence.

Use `deferred_or_gap` when the release intentionally documents a boundary instead of pretending capability exists.

## Release Gate

The release validator fails if the matrix is missing, malformed, stale, or if any row implies field validation, calibration adequacy, regulatory acceptance, or source-engine equivalence without a future governed evidence tranche.
