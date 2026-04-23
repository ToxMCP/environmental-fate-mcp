# ADR 0003: Scenario Taxonomy and Time Semantics

## Status

Accepted

## Decision

Environmental Fate MCP v0.1 supports two run classes:

- `steady_state`: a single concentration interpretation with no explicit start or end
- `time_bucket`: one or more bounded windows with explicit `start` and `end`

Mandatory result semantics:

- every concentration surface declares `medium`
- every concentration surface declares `compartment`
- every concentration surface declares `geographicScope`
- every concentration surface declares either `steady_state` or a bounded time window

Canonical compartments for v0.1:

- `ambient_air`
- `surface_water`
- `agricultural_soil`
- `freshwater_sediment`

Deferred compartments remain out of scope unless they are backed by a declared defaults pack and schema extension.
