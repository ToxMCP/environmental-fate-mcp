# Security Policy

Environmental Fate MCP is a scientific screening MCP with explicit release gates, typed contracts, and assessor-facing artifacts. Security issues still matter here because a compromise can undermine auditability, provenance, reproducibility, or downstream trust.

## Supported Versions

The project currently supports security fixes on:

| Version / Branch | Status |
| --- | --- |
| `main` | Supported |
| latest `v0.1.x` release line | Supported |
| older unreleased branches and historical snapshots | Not supported |

## Reporting a Vulnerability

Please do **not** open public GitHub issues for security vulnerabilities.

Preferred path:

1. Use GitHub private vulnerability reporting for this repository if it is enabled.
2. If private vulnerability reporting is unavailable, contact the repository maintainers through a private channel before any public disclosure.

When reporting, include:

- affected version, branch, or commit
- attack preconditions
- exact reproduction steps or proof of concept
- expected impact on confidentiality, integrity, availability, or auditability
- whether generated artifacts, defaults, schemas, or downstream handoff outputs are affected

## Response Targets

Current target service levels:

- initial acknowledgement within `5` business days
- initial triage within `10` business days
- remediation plan or disposition within `30` calendar days for confirmed issues

These are targets, not guarantees, but they set the expected maintenance bar for public release.

## Scope Notes

The following are in scope for responsible disclosure:

- remote code execution or command-injection paths
- path traversal or arbitrary file access
- authentication or authorization flaws if auth surfaces are added
- artifact tampering or integrity-bypass paths
- provenance, audit-log, or validation-bypass issues
- schema/resource handlers that expose unintended local files

The following are usually **not** security vulnerabilities by themselves, though they may still be important bugs:

- model boundary limitations that are already declared in docs
- disagreements with screening assumptions or scientific applicability
- expected fail-closed validation errors on unsupported use cases

Scientific or regulatory concerns that are not security issues should go through the standard contribution/support flow instead of private disclosure.

## Confidential Data

Do not include confidential study data, regulated substance dossiers, proprietary customer data, or personally identifying information in public issues or vulnerability reports unless you have permission to share them.
