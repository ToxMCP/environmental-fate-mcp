## Summary

Describe the change and the specific problem it addresses.

## Why This Change Belongs Here

Explain why the work fits the Environmental Fate MCP boundary instead of a neighboring ToxMCP module.

## Verification

- [ ] `uv run fate-mcp-generate-artifacts`
- [ ] `uv run pytest`
- [ ] `uv run environmental-fate-mcp-validate`
- [ ] `uv run python -c "from fate_mcp.server import create_server; create_server()"`

## Release Surface Checklist

- [ ] Generated artifacts are committed if they changed
- [ ] Regeneration is deterministic
- [ ] Startup does not mutate shipped artifacts
- [ ] Package-data mirror changes are generated from repo-root sources, not hand-edited
- [ ] Docs were updated for user-visible, scientific, or governance changes
- [ ] Scientific limitations remain explicit
- [ ] Downstream handoff semantics remain auditable if affected

## Risk Notes

Call out any scientific, regulatory, or interoperability risks reviewers should pay attention to.
