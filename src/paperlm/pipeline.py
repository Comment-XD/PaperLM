"""Pure extraction pipeline: download a PDF, run GROBID, store the TEI XML.

Deliberately free of Celery so it can be unit-tested without a broker.
"""

import json
import tempfile
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from paperlm import db, grobid, packing, storage, tokenizer, transform
from paperlm.config import get_settings
from paperlm.db_models import stats_to_row


def process_paper_pdf(pdf_key: str) -> str:
    """Extract one PDF (by S3 key) to TEI XML and return the output key."""
    settings = get_settings()
    stem = Path(pdf_key).stem
    output_key = f"{settings.extracted_prefix}{stem}.tei.xml"

    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_path = Path(tmpdir) / f"{stem}.pdf"
        storage.download(pdf_key, pdf_path)
        tei_xml = grobid.extract_tei(pdf_path)
        storage.upload_bytes(output_key, tei_xml)

    return output_key


def process_paper_tei(tei_key: str) -> dict:
    """Transform one TEI XML (by S3 key) into clean text + a stats row.

    Writes the clean text to ``transformed/<stem>.txt`` and upserts a quality
    row into the ``paper_stats`` table (the queryable source of truth). When
    ``write_stats_json`` is set it also writes ``transformed/<stem>.stats.json``
    as a debug artifact. Returns the keys plus the stats row.
    """
    settings = get_settings()
    stem = Path(tei_key).stem
    if stem.endswith(".tei"):
        stem = stem[: -len(".tei")]

    text_key = f"{settings.transformed_prefix}{stem}.txt"
    stats_key = (
        f"{settings.transformed_prefix}{stem}.stats.json"
        if settings.write_stats_json
        else None
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        tei_path = Path(tmpdir) / f"{stem}.tei.xml"
        storage.download(tei_key, tei_path)
        result = transform.transform(tei_path.read_bytes())

    storage.upload_bytes(text_key, result.text.encode("utf-8"))
    if stats_key is not None:
        storage.upload_bytes(
            stats_key,
            json.dumps(asdict(result.stats), ensure_ascii=False, indent=2).encode(
                "utf-8"
            ),
        )

    db.upsert_paper_stats(stats_to_row(stem, result, tei_key, text_key, stats_key))

    return {
        "tei_key": tei_key,
        "text_key": text_key,
        "stats_key": stats_key,
        "stats": asdict(result.stats),
    }


def process_tokenize_shard(
    run_id: str,
    shard_index: int,
    arxiv_ids: list[str],
    *,
    encoder_name: str | None = None,
    backend: str | None = None,
) -> dict:
    """Tokenize the transformed text of ``arxiv_ids`` into one uint16 shard.

    Downloads each ``transformed/<id>.txt``, encodes it, appends an EOT token as
    a document separator, packs the concatenation into a flat uint16 array and
    uploads it to ``tokenized/<run_id>/shard_<index>.bin``. Records per-paper
    token counts in the DB. Pure of Celery so it is unit-testable.
    """
    settings = get_settings()
    encoder_name = encoder_name or settings.tokenizer_name
    backend = backend or settings.tokenizer_backend
    encoder = tokenizer.get_encoder(encoder_name, backend)

    token_ids: list[int] = []
    token_rows: list[dict] = []
    now = datetime.now(timezone.utc)

    with tempfile.TemporaryDirectory() as tmpdir:
        for arxiv_id in arxiv_ids:
            text_key = f"{settings.transformed_prefix}{arxiv_id}.txt"
            dest = Path(tmpdir) / f"{arxiv_id}.txt"
            storage.download(text_key, dest)
            ids = encoder.encode(dest.read_text(encoding="utf-8"))
            ids.append(encoder.eot_token)  # separate documents
            token_ids.extend(ids)
            token_rows.append(
                {
                    "arxiv_id": arxiv_id,
                    "token_count": len(ids),
                    "tokenizer": encoder_name,
                    "tokenized_at": now,
                }
            )

    arr = packing.pack_tokens(token_ids)
    data = packing.shard_bytes(arr)
    shard_key = (
        f"{settings.tokenized_prefix}{run_id}/shard_{shard_index:04d}.bin"
    )
    storage.upload_bytes(shard_key, data)

    if settings.local_tokenized_dir:
        local_dir = Path(settings.local_tokenized_dir) / run_id
        local_dir.mkdir(parents=True, exist_ok=True)
        (local_dir / f"shard_{shard_index:04d}.bin").write_bytes(data)

    db.update_token_counts(token_rows)

    return {
        "shard_key": shard_key,
        "token_count": int(arr.size),
        "paper_count": len(arxiv_ids),
    }