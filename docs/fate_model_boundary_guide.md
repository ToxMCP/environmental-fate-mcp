# Fate Model Boundary Guide

The public abstraction is not "run a branded fate engine." The public abstraction is "build a release scenario, estimate concentration surfaces, screen bounded erosion/sediment transport, or normalize a governed external payload into the same concentration contracts."

Adapters may normalize external model outputs into Environmental Fate MCP contracts, but model-native branded payloads are not the public interface. The stable public adapter contract is the normalized JSON/CSV payload shape.

The erosion/sediment transport extension follows the same boundary. RUSLE and MUSLE tools emit scalar
screening estimates and sediment-associated chemical-load handoffs. The validation QA tools compare inline
observed and predicted scalar records without fitting or correcting model inputs. They do not turn
Environmental Fate MCP into a GIS erosion model, hydrologic routing engine, calibration workflow, WEPP
executor, receiving-water concentration model, or final exposure/risk engine.
The governed validation demo pack is synthetic and demonstrates QA classification behavior only; it is not
field validation, calibration evidence, catchment validation, regulator acceptance, or WEPP validation.

The experimental fugacity screening extension follows the same boundary. It runs native Level I/II-style
equilibrium partitioning checks over fixed air, water, soil, and sediment media, with `requested_media`
filtering returned surfaces only. It does not implement Level III non-equilibrium intermedia transfer,
advective export between media, deposition, hydrologic routing, GIS routing, calibration, source-engine
equivalence, field validation, or regulator acceptance.

The v0.4 release-line scientific trust diagnostics follow the same boundary. The external benchmark pack replays
deterministic screening cases through public tools, the default sensitivity report perturbs governed scalar
assumptions, the fugacity screening validation report checks the experimental equilibrium family, and
probabilistic sample manifests preserve audit hashes and sampled inputs when requested. None of these artifacts
creates a calibrated model, a field-validation corpus, a Level III implementation, a source-engine equivalence
claim, a spatial routing engine, or a regulator-acceptance decision.

This boundary does not change for TCM, herbal medicine, or supplement questions. Environmental Fate MCP still
publishes concentration outputs only. Medicinal direct-use regimens remain downstream
Direct-Use Exposure MCP territory, while food-mediated herbal or supplement intake remains
Dietary MCP territory.
