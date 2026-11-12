"""Dispatch tokenize tasks for a selection manifest, then write a run manifest.

Usage::

    python -m paperlm.tokenize_enqueue selections/<name>.json

The selection manifest (written by the dashboard) lists the ``arxiv_ids`` to
tokenize. Papers are chunked ``tokenize_chunk_size`` at a time -- one Celery
``tokenize_shard`` task, and one ``shard_<i>.bin``, per chunk.
"""

import json
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from paperlm.config import get_settings
from paperlm.storage import download, upload_bytes
from paperlm.tasks import tokenize_shard


def _slug(name: str) -> str:
    """Make a filesystem/S3-safe run id fragment from a selection name."""
    return re.sub(r"[^A-Za-z0-9._-]+", "-", name).strip("-") or "selection"


def _chunks(items: list[str], size: int):
    for i in range(0, len(items), size):
        yield items[i : i + size]


def load_selection(selection_key: str) -> dict:
    """Download and parse the selection manifest at ``selection_key``."""
    with tempfile.TemporaryDirectory() as tmpdir:
        dest = Path(tmpdir) / "selection.json"
        download(selection_key, dest)
        return json.loads(dest.read_text(encoding="utf-8"))


def main(selection_key: str) -> None:
    """Dispatch a tokenize_shard task per chunk of the selection's arxiv_ids."""
    settings = get_settings()
    selection = load_selection(selection_key)
    arxiv_ids = selection.get("arxiv_ids", [])
    if not arxiv_ids:
        sys.exit(f"selection {selection_key} has no arxiv_ids")

    name = selection.get("name", "selection")
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_id = f"{_slug(name)}-{timestamp}"

    chunks = list(_chunks(arxiv_ids, settings.tokenize_chunk_size))
    for index, chunk in enumerate(chunks):
        tokenize_shard.delay(run_id, index, chunk)

    run_manifest = {
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "tokenizer": settings.tokenizer_name,
        "tokenizer_backend": settings.tokenizer_backend,
        "source_selection": selection_key,
        "paper_count": len(arxiv_ids),
        "shard_count": len(chunks),
        "shards": [f"shard_{i:04d}.bin" for i in range(len(chunks))],
        "dtype": "uint16",
        # Per-paper token counts land in paper_stats as shards complete; sum
        # them there for an authoritative total token count for this run.
    }
    manifest_key = f"{settings.tokenized_prefix}{run_id}/manifest.json"
    upload_bytes(
        manifest_key,
        json.dumps(run_manifest, ensure_ascii=False, indent=2).encode("utf-8"),
    )
    print(
        f"Dispatched {len(chunks)} shard task(s) for {len(arxiv_ids)} paper(s); "
        f"run_id={run_id}; manifest={manifest_key}"
    )


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: python -m paperlm.tokenize_enqueue <selection_key>")
    main(sys.argv[1])
