# PaperLM — PDF extraction & transform pipeline

A parallel pipeline that turns research PDFs into clean, model-ready text.
Celery workers pull tickets (S3 keys) from Redis and process each paper through
two chained stages — **extract** (PDF → TEI XML via GROBID) and **transform**
(TEI XML → clean reading text + a quality-stats row). A separate **ingest**
step downloads arXiv PDFs into the pipeline. This is the data stage of PaperLM,
a model pretrained on CS research papers.

## Stack

Python 3.12 · uv · Celery (Redis broker) · boto3 · requests · lxml ·
pydantic-settings · Docker Compose · GROBID (CRF-only) · LocalStack (S3).

## How it works

Three stages, each writing to its own S3 prefix so every stage is replayable
from the artifacts of the one before it:

```
arXiv ──ingest──▶ raw/papers/<id>.pdf
                        │
                   enqueue.py  (one Celery chain per PDF)
                        │
          ┌─────────────┴──────────── chain ────────────────┐
          ▼                                                  ▼
  process_paper (extract)                        transform_paper (transform)
  download PDF → GROBID → TEI                     download TEI → parse → clean
          │                                                  │
          ▼                                                  ▼
  extracted/<id>.tei.xml  ───(key passed down the chain)──▶  transformed/<id>.txt
                                                             transformed/<id>.stats.json
```

**Ingest** (`paperlm.ingest`) reads `arxiv_paper_ids.txt`, downloads each PDF
from arXiv, and uploads it under the `raw/papers/` prefix.

**Enqueue** (`paperlm.enqueue`) lists every `raw/papers/*.pdf` key and dispatches
a Celery `chain(process_paper.s(key), transform_paper.s())` for each. The two
tasks run per paper: the extract task's return value (the TEI key) is fed
straight into the transform task by the chain — no glue code.

**Extract** (`process_paper` → `pipeline.process_paper_pdf`) downloads the PDF to
a temp dir, sends it to GROBID, and uploads the returned TEI XML to
`extracted/<id>.tei.xml`. Retries up to 3× with backoff on transient GROBID/HTTP
errors (`requests.RequestException`).

**Transform** (`transform_paper` → `pipeline.process_paper_tei`) downloads the
TEI XML and runs `transform.transform()` over the bytes, producing a
`TransformResult(title, abstract, text, stats)`. It uploads the clean text to
`transformed/<id>.txt` and the stats row (JSON) to `transformed/<id>.stats.json`.
Retries only on transient S3 I/O (`botocore.BotoCoreError`); XML parse errors are
deterministic and fail fast instead of looping.

### What `transform.transform()` does

- **Parses safely.** `parse_tei()` disables entity resolution, DTD loading, and
  network access — the TEI derives from untrusted PDFs, so this blocks XXE and
  entity-expansion attacks.
- **Pulls title & abstract** from the TEI header.
- **Walks the body in document order**, keeping paragraphs and figure/table
  captions and tagging each block with its section heading.
- **Drops noise sections** whose heading matches `BLOCKED_HEADINGS` (references,
  acknowledgements, funding, appendices, ethics, …).
- **Strips inline citations** (`<ref type="bibr">`) from the prose.
- **Replaces math** (inline and display `<formula>`) with a `[FORMULA]` marker so
  raw equations never pollute the text; consecutive formulas collapse to one.
- **Keeps table captions, drops the grid** — the `<table>` cell matrix flattens
  into unreadable noise, so only the `<figDesc>` caption survives.
- **Emits a stats row** (`models.Stats`): word/char counts, alphabetic ratio,
  section count, repeated-line fraction, dropped headings, and missing
  title/abstract flags — a cheap quality signal for downstream filtering.

> **Results are the S3 objects**, not the task return value. No Celery result
> backend is configured, so the chain's return dict is discarded in the worker;
> the durable output is the pair of objects under `transformed/`. Add
> `backend=settings.redis_url` to `celery_app.py` only if you need `.get()`,
> chords, or progress tracking.

### Reprocessing transform alone

Because TEI XML persists in `extracted/`, you can re-run the transform stage
(e.g. after changing `transform.py`) without re-running GROBID.
`pipeline.process_all_tei()` transforms every `extracted/*.tei.xml` in parallel
with a thread pool, independent of Celery.

## Layout

```
src/paperlm/
  config.py              # Settings + get_settings() — the only place env is read
  constants.py           # static domain constants (TEI namespace, [FORMULA],
                         #   blocked headings, skipped figure children)
  models.py              # dataclasses: Block, Stats, TransformResult
  storage.py             # cached boto3 S3 client; download / upload_bytes / list_keys
  grobid.py              # extract_tei(pdf) -> TEI XML bytes
  transform.py           # transform(tei_bytes) -> TransformResult (parse + clean + stats)
  pipeline.py            # pure stage logic, no Celery:
                         #   process_paper_pdf  (extract)
                         #   process_paper_tei  (transform)
                         #   process_all_tei    (parallel transform reprocess)
  celery_app.py          # Celery app + config (broker only; no result backend)
  tasks.py               # process_paper + transform_paper tasks (retry rules)
  enqueue.py             # dispatch the extract->transform chain per raw PDF
  ingest/
    extractor.py         # arxiv_extractor() — download arXiv PDFs -> S3 raw prefix
    downloader.py        # entrypoint: run the extractor over arxiv_paper_ids.txt
scripts/
  create_bucket.py       # idempotent bucket creation
  upload_papers.py       # upload local PDFs to the raw prefix
  list_bucket.py         # list bucket contents (optional prefix filter)
  cat_object.py          # print one object (pretty-prints TEI XML)
  download_extracted.py  # download extracted TEI XML to a local folder
docker/
  docker-compose.yml     # redis, grobid, celery (worker)
  worker.Dockerfile      # celery worker image
  ingest.Dockerfile      # arXiv ingest image (runs ingest/downloader.py)
tests/
  test_config.py         # Settings defaults / overrides / validation
  test_pipeline.py       # pipeline with storage + grobid stubbed out
  test_transform.py      # TEI -> text rules (formulas, tables, citations, stats)
data/                    # local corpus (gitignored)
  pdf/                   # source PDFs
  xml/                   # downloaded TEI XML
  transformed/           # downloaded clean text / stats (when pulled locally)
arxiv_paper_ids.txt      # one arXiv id per line (ingest input)
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

**LocalStack must be running on the host** (S3 on `:4566`). It is *not* part of
`docker/docker-compose.yml`, so start it separately. Note the public `latest`
image now requires a paid Pro token — use the free community image:

```bash
docker run -d --name localstack -p 4566:4566 localstack/localstack:3
```

First, create your local env file once: `cp .env.example .env`.

The host-run scripts below use `uv run --env-file .env` so the AWS credentials
in `.env` reach boto3. (`pydantic-settings` reads `.env` into `Settings`, but
boto3 only reads credentials from the real process environment — `--env-file`
exports the whole file into it.)

```bash
# 1. Start the app stack (scale to as many workers as you like).
docker compose -f docker/docker-compose.yml up -d --build --scale celery=4

# 2. Create the S3 bucket (idempotent; LocalStack has no persistence).
uv run --env-file .env python -m scripts.create_bucket

# 3a. Upload local PDFs to the raw prefix ...
uv run --env-file .env python -m scripts.upload_papers /path/to/pdfs
# 3b. ... or ingest PDFs straight from arXiv (reads arxiv_paper_ids.txt).
uv run --env-file .env python -m paperlm.ingest.downloader

# 4. Enqueue the extract->transform chain for every raw PDF.
uv run --env-file .env python -m paperlm.enqueue

# 5. Watch the workers process them.
docker compose -f docker/docker-compose.yml logs -f celery

# Inspect the bucket at any time (optional prefix filter).
uv run --env-file .env python -m scripts.list_bucket
uv run --env-file .env python -m scripts.list_bucket transformed/

# Print one object (pretty-prints TEI XML; add --raw for exact bytes).
uv run --env-file .env python -m scripts.cat_object transformed/<id>.txt
uv run --env-file .env python -m scripts.cat_object transformed/<id>.stats.json

# Download all extracted TEI XML to a local folder.
uv run --env-file .env python -m scripts.download_extracted data/xml
```

Artifacts by prefix: raw PDFs under `raw/papers/`, extracted TEI under
`extracted/` as `<id>.tei.xml`, and transformed output under `transformed/` as
`<id>.txt` + `<id>.stats.json`.

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
make enqueue                 # enqueue the chain for every raw PDF (runs in a worker)
make list                    # list the bucket (FOLDER=transformed/ to filter)
make cat KEY=transformed/<id>.txt       # print one object
make download OUT=data/xml   # download extracted TEI XML locally
```

## Known gaps

- Permanently bad PDFs retry 3 times then fail; no failed-papers queue yet.
- No Celery result backend — the chain's return value is discarded; `transformed/`
  in S3 is the source of truth for results.
- GROBID `<formula>`-less inline math (equations GROBID leaves as plain `<p>`
  text) still leaks into the clean text; only tagged formulas become `[FORMULA]`.
- One GROBID per worker vs. a shared pool is still undecided.
- LocalStack is not in the compose stack and must be started manually.
