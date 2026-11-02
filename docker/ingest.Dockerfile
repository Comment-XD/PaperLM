FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.13.1 /uv /uvx /bin/

WORKDIR /app

# Install dependencies first so code edits don't bust the layer cache.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

COPY ./src ./src
COPY README.md arxiv_paper_ids.txt ./

CMD ["uv", "run", "python", "src/paperlm/ingest/downloader.py"]
