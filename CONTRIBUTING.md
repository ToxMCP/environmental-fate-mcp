# Contributing

Thanks for contributing. This repository has a higher-than-average review bar because it is intended to support auditable scientific screening and downstream regulatory handoff workflows.

## First Principles

Please keep these invariants intact:

- Environmental Fate MCP is a **bounded** ToxMCP module.
- Public artifacts must be **deterministic and reproducible**.
- Server startup must **validate** shipped artifacts, not mutate them.
- Scientific limitations and challenge-path status must stay **explicit**, not implied.
- Changes that affect scientific behavior should strengthen, not weaken, traceability and reviewability.

## Local Setup

```bash
uv sync --extra dev
uv run fate-mcp-generate-artifacts
uv run fate-mcp-build-release-bundle
uv run pytest
uv run environmental-fate-mcp-validate
```

For a lightweight startup smoke check:

```bash
uv run python -c "from fate_mcp.server import create_server; create_server()"
```

## Before You Open a Change

Check whether the change belongs in this repository at all.

Good fits:

- environmental release scenarios
- concentration estimation and governed screening logic
- provenance, validation, schemas, examples, defaults, and review artifacts
- downstream concentration handoff packaging

Poor fits:

- direct-use product exposure semantics
- dietary intake workflows
- PBPK execution
- final regulatory decision logic
- unbounded GIS or hydrodynamic dispersion ambitions hidden behind the current API

## Release-Critical Rules

If your change touches contracts, examples, defaults, or generated artifacts:

1. Regenerate artifacts.
2. Rebuild the public release bundle.
3. Confirm regeneration is deterministic.
4. Confirm `git diff` only reflects intended changes.
5. Run the full validator, not just tests.

If your change touches runtime scientific behavior:

1. Add or update tests.
2. Revisit affected scientific review or methods-dossier surfaces.
3. Update docs when limitations, assumptions, or reviewer interpretation lines change.
4. Preserve or improve benchmark and claim traceability.

## Pull Request Expectations

A good pull request here usually includes:

- a clear problem statement
- boundary-aware scope
- tests or validation evidence
- artifact regeneration when needed
- documentation updates for changed behavior
- explicit notes if the change affects scientific claims, defaults, or downstream handoff semantics

## Review Heuristics

Reviewers will look closely for:

- hidden nondeterminism
- startup side effects
- schema/example drift
- implicit scientific claims that are not benchmarked or documented
- boundary creep into neighboring ToxMCP modules
- changes that make assessor review harder instead of easier

## Contribution License

By contributing, you agree that your contributions are provided under the repository license, Apache License 2.0.
