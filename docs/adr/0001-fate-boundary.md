# ADR 0001: Fate MCP Boundary

## Status

Accepted

## Decision

Fate MCP owns source-to-concentration environmental workflows:

- environmental release scenarios
- multimedia transfer and degradation
- compartment concentration estimation
- concentration surfaces
- fate scenario comparison
- downstream concentration bundles

Fate MCP explicitly excludes:

- direct human dose calculation
- dietary intake workflows
- PBPK execution
- final risk characterization
- arbitrary model-native desktop files as the public contract
- medicinal direct-use oral semantics such as TCM regimens or product-centric supplement dosing

## Rationale

The ToxMCP suite should split by pathway semantics and input grammar, not by route alone. Fate MCP accepts environmental release assumptions and returns auditable concentration outputs that downstream systems can consume without knowing the underlying fate engine.
Traditional Chinese Medicine, herbal medicine, and supplement labels do not change that split:
Fate MCP still stops at concentration outputs, and downstream routing depends on whether the
later intake question is direct-use medicinal or food-mediated dietary consumption.
