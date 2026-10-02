# Stable MCP SDK2 migration candidate

The v0.6.0 candidate pins Python MCP SDK 2.2.0 and supports the modern
2026-07-28 protocol. The published release remains v0.5.1. This change does
not publish packages or deploy hosted services.

## Existing MCP clients

The catalog remains identical: 60 tools, 32 fixed resources, 18 resource
templates, and 22 prompts. Names, input/output schemas, argument shapes,
annotations and scientific defaults remain unchanged. Existing SDK1 clients
continue to work over stdio, Streamable HTTP and legacy SSE. Four older HTTP
protocol dates are tested: 2024-11-05, 2025-03-26, 2025-06-18 and 2025-11-25.

Modern clients can discover the server and call tools without a persistent
HTTP session. Catalog responses carry private 60-second cache hints;
scientific results are not given reusable cache hints. The modern SDK runs
synchronous calculations in worker threads; the runtime/default registries
remain read-only and logging initialization is protected by a lock.

The reference, advective, fugacity and erosion/sediment calculations, units,
defaults, seeds and qualification limits are unchanged. Experimental model
families retain their existing status. Known scientific limitations remain
explicit in all review artifacts.

## Hosted operators

The existing `FATE_MCP_ALLOW_UNAUTHENTICATED_HTTP=true` guard remains required
for HTTP and SSE, including the new programmatic HTTP app factory. Set it
only when an authenticated gateway protects the service. It does not add
authentication itself.

`FATE_MCP_HOST` and `FATE_MCP_PORT` remain supported. The dedicated HTTP
entrypoint defaults to 0.0.0.0:8000; the general CLI defaults to loopback.
Configure the gateway's actual host and browser origins explicitly:

```sh
FATE_MCP_ALLOWED_HOSTS=fate.example.org
FATE_MCP_ALLOWED_ORIGINS=https://your-client.example.org
FATE_MCP_MAX_REQUEST_BYTES=4194304
```

The default allowlists cover localhost, 127.0.0.1 and IPv6 loopback only.
Empty allowlists and invalid body limits fail during startup. DNS rebinding
and body-size protection also apply to SSE. HTTP uses stateless JSON
responses for both client generations. Legacy SSE remains available.

## Python embeddings and diagnostics

SDK2 renames `FastMCP` to `MCPServer`, moves protocol models to `mcp_types`,
and uses snake_case Python attributes. JSON field names on the wire remain
unchanged. Transport configuration is passed to the public HTTP/SSE app
factories rather than mutating removed SDK settings.

Expected Fate domain failures retain their released `isError` message.
Unexpected implementation exceptions are sanitized by SDK2 rather than
exposing internal diagnostics to clients. Server logs retain the original
exception for operators.

This migration also fixes a pre-existing installed-wheel resource lookup:
seven benchmark-backed review workflows previously looked for defaults in a
checkout-relative location. They now use the existing resource resolver,
including `FATE_MCP_RESOURCE_ROOT` and packaged defaults. Their scientific
results match the released source workflows.

## Review and rollback

The CI gate installs a non-editable wheel and exercises actual SDK1.30 and
SDK2.2 clients over stdio/HTTP, plus SDK1 over SSE. It requires the released
catalog fingerprint and identical application results across all five
combinations. Test-only invocation clocks/UUIDs make the comparison exact;
production entrypoints do not import that launcher.

Review and release the candidate before updating hosted services. Retain
v0.5.1 artifacts and the prior image digest for rollback. Python 3.12+ remains
the supported runtime. SDK2 does not automatically add MCP Apps, multi-round
elicitation workflows, or new scientific capabilities.
