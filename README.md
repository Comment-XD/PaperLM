# PaperLM — PDF extraction pipeline (stage one)

A parallel PDF-extraction pipeline. Celery workers pull tickets (S3 keys of
PDFs) from Redis. Each worker downloads the PDF, sends it to GROBID, and writes
the returned TEI XML back to S3. This is the first stage of PaperLM, a model
pretrained on CS research papers.

## Stack

Python 3.12 · uv · Celery (Redis broker) · boto3 · requests ·
pydantic-settings · Docker Compose · GROBID (CRF-only) · LocalStack (S3).

## Layout

```
src/paperlm/
  config.py              # Settings + get_settings() — the only place env is read
  storage.py             # cached boto3 S3 client; download / upload_bytes / list_keys
  grobid.py              # extract_tei(pdf) -> TEI XML bytes
  pipeline.py            # process_paper_pdf(key) — pure, no Celery
  celery_app.py          # Celery app + config
  tasks.py               # process_paper task (retry rules), calls the pipeline
  enqueue.py             # enqueue every raw PDF
scripts/
  create_bucket.py       # idempotent bucket creation
  upload_papers.py       # upload local PDFs to the raw prefix
  list_bucket.py         # list bucket contents (optional prefix filter)
  cat_object.py          # print one object (pretty-prints TEI XML)
  download_extracted.py  # download extracted TEI XML to a local folder
docker/
  docker-compose.yml     # redis, grobid, celery (worker)
  worker.Dockerfile
tests/
  test_config.py         # Settings defaults / overrides / validation
  test_pipeline.py       # pipeline with storage + grobid stubbed out
data/                    # local corpus (gitignored)
  pdf/                   # source PDFs
  xml/                   # downloaded TEI XML
Makefile                 # shortcut targets (see below)
pyproject.toml           # uv project + deps
uv.lock
.env.example             # template for the host .env (never commit the real .env)
```

## Local development

```bash
uv sync
uv run pytest
```

Copy `.env.example` to `.env` and adjust for host runs (the Compose stack sets
its own environment using service names).

## Run sequence

LocalStack must already be running on the host (S3 on `:4566`).

First, create your local env file once: `cp .env.example .env`.

The host-run scripts below use `uv run --env-file .env` so the AWS credentials
in `.env` reach boto3. (`pydantic-settings` reads `.env` into `Settings`, but
boto3 only reads credentials from the real process environment — `--env-file`
exports the whole file into it.)

```bash
# 1. Start the stack (scale to as many workers as you like).
docker compose -f docker/docker-compose.yml up -d --build --scale celery=4

# 2. Create the S3 bucket (idempotent; LocalStack has no persistence).
uv run --env-file .env python -m scripts.create_bucket

# 3. Upload some PDFs to the raw prefix.
uv run --env-file .env python -m scripts.upload_papers /path/to/pdfs

# 4. Enqueue a task for every raw PDF.
uv run --env-file .env python -m paperlm.enqueue

# 5. Watch the workers process them.
docker compose -f docker/docker-compose.yml logs -f celery

# Inspect the bucket at any time (optional prefix filter).
uv run --env-file .env python -m scripts.list_bucket
uv run --env-file .env python -m scripts.list_bucket extracted/

# Print one object (pretty-prints TEI XML; add --raw for exact bytes).
uv run --env-file .env python -m scripts.cat_object extracted/<stem>.tei.xml

# Download all extracted TEI XML to a local folder.
uv run --env-file .env python -m scripts.download_extracted data/xml
```

Extracted TEI XML lands under the `extracted/` prefix as `<stem>.tei.xml`.

The `.env` ships with `S3_ENDPOINT_URL=http://localhost:4566` and dummy AWS
credentials for host runs against LocalStack.

## Makefile shortcuts

Common tasks are wrapped in the `Makefile`:

```bash
make up                      # build + start the stack (detached)
make down                    # stop the stack
make logs                    # follow the celery worker logs
make ps                      # show service status
make test                    # uv run pytest
make bucket                  # create the S3 bucket
make upload PAPERS=data/pdf  # upload PDFs to the raw prefix
make enqueue                 # enqueue every raw PDF (runs inside a worker)
make list                    # list the bucket (FOLDER=extracted/ to filter)
make cat KEY=extracted/<stem>.tei.xml   # print one object
make download OUT=data/xml   # download extracted TEI XML locally
```

## Known gaps

- Permanently bad PDFs retry 3 times then fail; no failed-papers queue yet.
- S3 (botocore) errors are not in `autoretry_for`.
- One GROBID per worker vs. a shared pool is still undecided.
