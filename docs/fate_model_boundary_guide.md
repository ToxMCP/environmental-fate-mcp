# Fate Model Boundary Guide

The public abstraction is not "run a branded fate engine." The public abstraction is "build a release scenario, estimate concentration surfaces, screen bounded erosion/sediment transport, or normalize a governed external payload into the same concentration contracts."

Adapters may normalize external model outputs into Environmental Fate MCP contracts, but model-native branded payloads are not the public interface. The stable public adapter contract is the normalized JSON/CSV payload shape.

The erosion/sediment transport extension follows the same boundary. RUSLE and MUSLE tools emit scalar
screening estimates and sediment-associated chemical-load handoffs. The validation QA tools compare inline
observed and predicted scalar records without fitting or correcting model inputs. They do not turn
Environmental Fate MCP into a GIS erosion model, hydrologic routing engine, calibration workflow, WEPP
executor, receiving-water concentration model, or final exposure/risk engine.

This boundary does not change for TCM, herbal medicine, or supplement questions. Environmental Fate MCP still
publishes concentration outputs only. Medicinal direct-use regimens remain downstream
Direct-Use Exposure MCP territory, while food-mediated herbal or supplement intake remains
Dietary MCP territory.
