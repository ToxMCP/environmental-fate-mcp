# ADR 0002: Deterministic and Bounded First

## Status

Accepted

## Decision

Environmental Fate MCP prioritizes deterministic steady-state or bounded time-bucket workflows. Full Monte Carlo orchestration, GIS dispersion, and unrestricted mechanistic dynamic simulation are deferred.

## Rationale

- transparent validation
- tractable benchmark fixtures
- stable shared contracts
- simpler downstream integration
- cleaner plugin and adapter boundary for later extension
