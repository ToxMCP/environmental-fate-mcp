# Fate Model Boundary Guide

The public abstraction is not "run a branded fate engine." The public abstraction is "build a release scenario, estimate concentration surfaces, or normalize a governed external payload into the same concentration contracts."

Adapters may normalize external model outputs into Environmental Fate MCP contracts, but model-native branded payloads are not the public interface. The stable public adapter contract is the normalized JSON/CSV payload shape.

This boundary does not change for TCM, herbal medicine, or supplement questions. Environmental Fate MCP still
publishes concentration outputs only. Medicinal direct-use regimens remain downstream
Direct-Use Exposure MCP territory, while food-mediated herbal or supplement intake remains
Dietary MCP territory.
