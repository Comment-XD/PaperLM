"""Unit tests for the pure token-packing helpers."""

import numpy as np
import pytest

from paperlm.packing import pack_tokens, shard_bytes


def test_pack_tokens_dtype_and_values():
    arr = pack_tokens([0, 1, 50256, 100])
    assert arr.dtype == np.uint16
    assert arr.tolist() == [0, 1, 50256, 100]


def test_pack_tokens_empty():
    arr = pack_tokens([])
    assert arr.dtype == np.uint16
    assert arr.size == 0


def test_pack_tokens_rejects_overflow():
    with pytest.raises(ValueError, match="uint16"):
        pack_tokens([1, 2, 70000])


def test_pack_tokens_rejects_negative():
    with pytest.raises(ValueError, match="non-negative"):
        pack_tokens([1, -5])


def test_shard_bytes_roundtrip():
    ids = [1, 2, 3, 65535]
    data = shard_bytes(pack_tokens(ids))
    assert len(data) == len(ids) * 2  # 2 bytes per uint16
    restored = np.frombuffer(data, dtype=np.uint16)
    assert restored.tolist() == ids
