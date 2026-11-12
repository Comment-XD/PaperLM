"""Tests for the tokenize stage with storage/db/encoder stubbed out."""

from pathlib import Path

import numpy as np
import pytest

from paperlm import db, pipeline, storage, tokenizer
from paperlm.config import get_settings


@pytest.fixture(autouse=True)
def _bucket_env(monkeypatch):
    monkeypatch.setenv("S3_BUCKET", "bucket")
    get_settings.cache_clear()
    db.get_engine.cache_clear()
    db.get_sessionmaker.cache_clear()
    yield
    get_settings.cache_clear()
    db.get_engine.cache_clear()
    db.get_sessionmaker.cache_clear()


class _FakeEncoder:
    """Char-code encoder: deterministic, no tiktoken load, uint16-safe."""

    eot_token = 999
    vocab_size = 1000

    def encode(self, text: str) -> list[int]:
        return [ord(c) % 256 for c in text]


def test_process_tokenize_shard(monkeypatch):
    texts = {
        "transformed/a.txt": "ab",   # -> [97, 98]
        "transformed/b.txt": "c",    # -> [99]
    }
    uploaded: dict[str, bytes] = {}
    token_updates: list[dict] = []

    def fake_download(key: str, dest: Path) -> None:
        Path(dest).write_text(texts[key], encoding="utf-8")

    monkeypatch.setattr(storage, "download", fake_download)
    monkeypatch.setattr(
        storage, "upload_bytes", lambda key, data: uploaded.__setitem__(key, data)
    )
    monkeypatch.setattr(db, "update_token_counts", token_updates.extend)
    monkeypatch.setattr(tokenizer, "get_encoder", lambda *a, **k: _FakeEncoder())

    out = pipeline.process_tokenize_shard("run1", 0, ["a", "b"])

    # Shard key and layout.
    assert out["shard_key"] == "tokenized/run1/shard_0000.bin"
    assert out["paper_count"] == 2
    # Tokens: [97,98,999, 99,999] -> 5 tokens, each paper gets an EOT separator.
    arr = np.frombuffer(uploaded["tokenized/run1/shard_0000.bin"], dtype=np.uint16)
    assert arr.tolist() == [97, 98, 999, 99, 999]
    assert out["token_count"] == 5

    # Per-paper token counts recorded (including the EOT token).
    counts = {r["arxiv_id"]: r["token_count"] for r in token_updates}
    assert counts == {"a": 3, "b": 2}
    assert all(r["tokenizer"] == "gpt2" for r in token_updates)


def test_get_encoder_rejects_unknown_backend():
    with pytest.raises(ValueError, match="backend"):
        tokenizer.get_encoder("gpt2", "nope")
