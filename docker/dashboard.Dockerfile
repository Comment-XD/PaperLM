# Plotly Dash dashboard image. Build context is the repo root (see compose).
FROM python:3.12-slim

# Bring in the uv binary from Astral's published image (pinned).
COPY --from=ghcr.io/astral-sh/uv:0.13.1 /uv /uvx /bin/

WORKDIR /app

# Install deps first (incl. the dashboard group) so code edits don't bust cache.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev --group dashboard

# Then add source and install the project itself (editable; serves assets/).
COPY README.md ./
COPY src/ ./src/
RUN uv sync --frozen --no-dev --group dashboard

# Use the project's virtualenv without needing `uv run`.
ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8050
CMD ["gunicorn", "-b", "0.0.0.0:8050", "--workers", "2", "paperlm.dashboard.app:server"]
