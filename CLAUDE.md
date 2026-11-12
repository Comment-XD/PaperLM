# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

PaperLM's data stage: a parallel pipeline that turns research PDFs into clean, model-ready text. Celery workers pull S3 keys off a Redis broker and run each paper through two chained stages — **extract** (PDF → TEI XML via GROBID) and **transform** (TEI XML → clean text + a quality-stats JSON row). A separate **ingest** step downloads arXiv PDFs into the pipeline. See `README.md` for the full narrative and run sequence.

## Commands

Package/deps are managed with **uv** (Python 3.12). Do not use pip/venv directly.

```bash
uv sync                              # install deps (incl. dev group)
uv run pytest                        # run all tests (also: make test)
uv run pytest tests/test_transform.py::test_name   # run one test
```

Stack lifecycle (Makefile wraps `docker compose -f docker/docker-compose.yml`):

```bash
make up            # build + start redis/grobid/celery, detached
make down          # stop
make logs          # follow celery worker logs
make enqueue       # dispatch the extract->transform chain for every raw PDF (runs inside a worker)
```

Host-run scripts (bucket/upload/list/cat/download) go through `uv run --env-file .env` — see "Environment gotcha" below. The Makefile targets `bucket`, `upload PAPERS=…`, `list [FOLDER=…]`, `cat KEY=…`, `download OUT=…` wrap these.

## Architecture essentials

- **`enqueue.py`** lists every `*.pdf` under the raw prefix and dispatches one `chain(process_paper.s(key), transform_paper.s())` per paper. The extract task returns the TEI S3 key, which Celery feeds straight into the transform task — there is no glue code passing keys between stages.
- **`pipeline.py` is deliberately Celery-free** (`process_paper_pdf`, `process_paper_tei`) so the stage logic is unit-testable without a broker. `tasks.py` is the thin Celery wrapper that adds retry policy. Put new stage logic in `pipeline.py`/`transform.py`, not in `tasks.py`.
- **Stages communicate only through S3 prefixes**, each replayable from the prior stage's artifacts: `raw/<id>.pdf` → `extracted/<id>.tei.xml` → `transformed/<id>.txt` + `<id>.stats.json`. (Note: the README diagram shows `raw/papers/`, but the code's `raw_prefix` is `raw/` and `ingest/extractor.py` uploads to `raw/<id>.pdf`.)
- **No Celery result backend.** The chain's return dict is discarded by the worker — the durable output is the objects under `transformed/`. Add `backend=settings.redis_url` to `celery_app.py` only if you need `.get()`/chords/progress.
- **Retry policy is asymmetric and intentional:** `process_paper` retries on `requests.RequestException` (transient GROBID/HTTP), `transform_paper` retries only on `botocore.BotoCoreError` (transient S3). XML parse errors are deterministic and must fail fast, not loop.

## Config and environment

- **`config.py` is the only place the environment is read.** Access settings via `get_settings()` everywhere; never read `os.environ` elsewhere.
- **`get_settings()` and `storage.get_client()` are `@lru_cache`d.** Tests that monkeypatch env vars must call `get_settings.cache_clear()` after patching and again on teardown (see the `_bucket_env` fixture in `test_pipeline.py`). Forgetting this is the main footgun.
- **`constants.py` vs `config.py`:** domain facts about the TEI format / transform policy (TEI namespace, `[FORMULA]` marker, `BLOCKED_HEADINGS`, skipped figure children) live in `constants.py`; only runtime/deployment config belongs in `Settings`.

### Environment gotcha (host runs)

**LocalStack provides S3 and is *not* in `docker/docker-compose.yml`** — start it separately (`docker run -d --name localstack -p 4566:4566 localstack/localstack:3`). Host scripts must run under `uv run --env-file .env`: `pydantic-settings` reads `.env` into `Settings`, but **boto3 only reads AWS credentials from the real process environment**, which `--env-file` populates. Running a storage-touching script with a bare `uv run` will fail to authenticate.

## Transform output contract

When changing `transform.py`, preserve these rules (covered by `test_transform.py`): `parse_tei()` keeps XXE protections on (entities/DTD/network disabled — TEI derives from untrusted PDFs); inline `<ref type="bibr">` citations are dropped; inline and display `<formula>` become the `[FORMULA]` marker and consecutive formulas collapse to one; `BLOCKED_HEADINGS` sections (references, acknowledgements, funding, appendices, …) are skipped; table captions are kept but the `<table>` grid is dropped. Because `extracted/` persists, you can re-run transform without re-running GROBID.
