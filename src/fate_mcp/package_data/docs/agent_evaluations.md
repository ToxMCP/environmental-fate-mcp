# Agent Evaluations

Environmental Fate MCP now ships an agent-facing read-only evaluation pack in `evals/environmental-fate-mcp-read-only.xml`.

## Purpose

The evaluation pack complements the internal validation dossier by testing whether an MCP-aware agent can:
- discover the right tools, prompts, and resources
- inspect governed defaults and release artifacts
- answer stable repository-grounded questions without mutating state

## Contents

- `10` independent read-only QA pairs
- stable answers grounded in shipped defaults, release metadata, and public docs
- questions designed to require multi-step MCP exploration rather than one raw file read

## Recommended Use

1. Start from the MCP server surface.
2. Let the agent inspect tools, prompts, and resources.
3. Run the evaluation questions without write operations.
4. Compare outputs to the XML answers by exact string match where practical.

The evaluation pack is intentionally read-only so it can be reused across CI, manual MCP Inspector sessions, and agent capability checks.
