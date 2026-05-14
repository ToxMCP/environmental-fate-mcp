# Agent Evaluations

Environmental Fate MCP ships two agent-facing evaluation packs:

- `evals/environmental-fate-mcp-read-only.xml` — surface-discovery QA pack
- `evals/environmental-fate-mcp-scientific-decisions.xml` — scenario-based scientific-decision pack

## Read-only QA pack

The read-only QA pack tests whether an MCP-aware agent can:
- discover the right tools, prompts, and resources
- inspect governed defaults and release artifacts
- answer stable repository-grounded questions without mutating state

### Contents

- `10` independent read-only QA pairs
- stable answers grounded in shipped defaults, release metadata, and public docs
- questions designed to require multi-step MCP exploration rather than one raw file read

### Recommended use

1. Start from the MCP server surface.
2. Let the agent inspect tools, prompts, and resources.
3. Run the evaluation questions without write operations.
4. Compare outputs to the XML answers by exact string match where practical.

## Scientific-decisions pack

The scientific-decisions pack adds scenario-based agent decision questions that the surface-discovery pack does not exercise. It covers eight decision lanes the agent must get right for any non-trivial scientific use:

1. **Model-family selection** — given physchem (log Kow, Koc) or release-pattern (residence time) cues, the agent picks the right governed challenge family (`fugacity_equilibrium_screening` for equilibrium partitioning, `advective_screening_mass_balance` for flowing-water clearance).
2. **Fail-closed error codes** — the agent recognizes when a scenario violates a physical invariant (non-positive half-life, temperature outside the governed range in strict mode, treatment removal fraction exceeding unity) and surfaces the exact `FateValidationError` code rather than silently substituting a default.
3. **Governed policy values** — the agent reads the published Q10 factors and the supported temperature range from defaults rather than approximating.
4. **Reviewer-grade vs experimental** — the agent knows `reference_mass_balance` is the only reviewer-grade promoted baseline and that `advective_screening_mass_balance` carries `promotionStatus: non_promotable_experimental`.
5. **Hand-off contracts** — the agent uses `fate_export_regulatory_handoff_package` to produce hash-stamped downstream payloads and recognizes the `integrity_hash` field as the tamper-evidence anchor on both the bundle and the package.
6. **Erosion screening** — the agent runs `fate_screen_erosion_transport_relevance` first before committing to RUSLE / MUSLE / chemical-load work.
7. **Suite boundary discipline** — the agent routes internal-dose / toxicokinetic work to PBPK MCP rather than stretching Environmental Fate MCP beyond its concentration-surface boundary.
8. **Audit infrastructure** — the agent knows `FATE_MCP_AUDIT_LOG_PATH` enables durable JSONL audit logging and that `advective-worksheet-pack/` is the governed reviewable home of the experimental advective family's hand-worked fixtures.

### Contents

- `15` scenario-based QA pairs
- stable answers drawn from real model-family identifiers, error codes, and governance strings; the regression test at `tests/test_evals.py` asserts the answer set includes the canonical strings for every decision lane above so the pack cannot silently rot if a runtime refactor renames any of them

### Recommended use

Same loop as the read-only pack: start from the MCP surface, let the agent decide, compare by exact string match. The scientific-decisions pack is intentionally complementary to the read-only pack — passing one does not imply passing the other.

This pack closes row `R10` in [`docs/scientific_hardening_tracker.md`](scientific_hardening_tracker.md).
