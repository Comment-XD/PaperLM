# Celery worker image. Build context is the repo root (see docker-compose.yml).
FROM python:3.12-slim

# Bring in the uv binary from Astral's published image (pinned).
COPY --from=ghcr.io/astral-sh/uv:0.13.1 /uv /uvx /bin/

WORKDIR /app

# Install dependencies first so code edits don't bust the layer cache.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

# Then add the project source and install the project itself.
COPY README.md ./
COPY src/ ./src/
RUN uv sync --frozen --no-dev

# Use the project's virtualenv without needing `uv run`.
ENV PATH="/app/.venv/bin:$PATH"

CMD ["celery", "-A", "paperlm.celery_app", "worker", "--loglevel=INFO"]
