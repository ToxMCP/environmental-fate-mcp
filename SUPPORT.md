# Support Policy

Environmental Fate MCP is maintained as a bounded ToxMCP component for auditable environmental screening and downstream handoff support. Support is strongest for the current public release line and `main`.

## What To Use For What

- **Bug report**: open a GitHub issue with the bug template.
- **Scientific-method or applicability question**: open a GitHub issue with the scientific governance template.
- **Release blocker or release-readiness concern**: open a GitHub issue with the release-readiness template.
- **Security issue**: follow [SECURITY.md](./SECURITY.md) and do not open a public issue.

## What Maintainers Can Usually Help With

- reproducibility problems
- schema or example drift
- validator failures
- startup or packaging regressions
- scientific review artifact inconsistencies
- declared boundary and applicability interpretation
- downstream handoff contract mismatches

## What This Repository Does Not Promise

- private consulting
- custom regulatory submissions
- site-specific model calibration
- undisclosed support for out-of-boundary use cases
- direct ownership of PBPK, dietary intake, direct-use exposure, or final risk characterization

## Maintenance Posture

- `main` is the primary supported development line.
- Public release quality depends on passing the governed validation path, not only unit tests.
- Experimental model families may be supported as challenge-path review surfaces without being recommended as default production choices.

If you need a feature that would cross the declared Environmental Fate MCP boundary, the right answer may be a neighboring ToxMCP module rather than expanding this one.
