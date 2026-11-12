"""Pack token-id streams into flat uint16 shards (nanoGPT-compatible).

Pure numpy, no I/O -- the unit-test sweet spot. A shard is a flat array of
little-endian uint16 token ids; downstream training reads it with
``np.fromfile(path, dtype=np.uint16)``.
"""

from __future__ import annotations

from collections.abc import Iterable

import numpy as np

UINT16_MAX = 2**16


def pack_tokens(token_ids: Iterable[int]) -> np.ndarray:
    """Pack token ids into a uint16 ndarray, asserting they fit the dtype."""
    arr = np.fromiter(token_ids, dtype=np.int64)
    if arr.size and int(arr.max()) >= UINT16_MAX:
        raise ValueError(
            f"token id {int(arr.max())} exceeds uint16 range; use a smaller vocab"
        )
    if arr.size and int(arr.min()) < 0:
        raise ValueError("token ids must be non-negative")
    return arr.astype(np.uint16)


def shard_bytes(arr: np.ndarray) -> bytes:
    """Serialize a uint16 shard to raw bytes for storage."""
    if arr.dtype != np.uint16:
        raise ValueError("shard must be uint16")
    return arr.tobytes()
