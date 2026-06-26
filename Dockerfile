# Production image for environmental-fate-mcp (streamable-HTTP transport).
# Mirrors the fleet pattern (ngra-ttc-tier0-mcp / bioactivity-pod-mcp).
#
# Transport: streamable-HTTP via uvicorn, port 8000.
# Stdio entrypoint (environmental-fate-mcp) is preserved in the installed package.
# No secrets or API keys are baked in; pass env vars at runtime.
#
# Security guard: the HTTP transport requires FATE_MCP_ALLOW_UNAUTHENTICATED_HTTP=true
# to be set explicitly, signalling that the operator has placed this service behind
# an authenticated gateway.

ARG PYTHON_IMAGE=python:3.12-slim-bookworm

FROM ${PYTHON_IMAGE}

ARG APP_HOME=/app

# Reproducible, no .pyc noise.
# UV_PYTHON: pin uv to the system Python in the base image (python:3.12-slim-bookworm)
# so the venv symlinks work at runtime — do NOT let uv download its own interpreter.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_PYTHON=/usr/local/bin/python3.12

WORKDIR ${APP_HOME}

# Install uv from PyPI so no external registry pull is required at build time.
RUN pip install --no-cache-dir "uv==0.7.12"

# Copy only the dependency manifest first so Docker cache layers survive
# source-only changes.
COPY pyproject.toml uv.lock ./

# Copy README so hatchling/setuptools can read it during the metadata pass.
COPY README.md ./

# Install all runtime dependencies from the locked file.
# --no-install-project: only deps, not the package itself yet.
# --no-dev: production image does not need pytest/ruff.
RUN uv sync --locked --no-install-project --no-dev

# Copy source tree and data directories, then install the project itself.
COPY src/ src/
COPY defaults/ defaults/
COPY config/ config/
COPY schemas/ schemas/

RUN uv sync --locked --no-dev

# Create a non-root user and hand ownership over.
RUN adduser --disabled-password --gecos "" appuser \
    && chown -R appuser:appuser ${APP_HOME}

USER appuser

# Streamable-HTTP transport port.
EXPOSE 8000

# Confirm the MCP endpoint is live.  A bare GET /mcp may return 406 when the
# MCP Accept header is missing; that still proves the server is up.  Fail only
# when the endpoint is unreachable or returns a server-side error (5xx).
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD /usr/local/bin/python3.12 -c "\
import http.client, sys; \
c = http.client.HTTPConnection('localhost', 8000, timeout=8); \
c.request('GET', '/mcp', headers={'Accept': 'application/json, text/event-stream'}); \
r = c.getresponse(); \
sys.exit(0 if r.status < 500 else 1)" || exit 1

# Run the http console script directly from the venv.
# Host/port tunable via env vars FATE_MCP_HOST and FATE_MCP_PORT.
# The FATE_MCP_ALLOW_UNAUTHENTICATED_HTTP guard must be set by the operator.
CMD ["/app/.venv/bin/environmental-fate-mcp-http"]
