"""Pluggable tokenizer layer. Default: GPT-2 BPE via tiktoken.

The tokenize stage depends only on the :class:`Encoder` protocol, so the vocab
can be swapped (a different BPE, or an HF tokenizer for a specific small model)
by changing ``tokenizer_name`` / ``tokenizer_backend`` in settings -- no pipeline
change. GPT-2's vocab (50257) fits in uint16, which is what the packing stage
assumes.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Protocol, runtime_checkable


@runtime_checkable
class Encoder(Protocol):
    """Minimal encoder interface the tokenize stage relies on."""

    eot_token: int
    vocab_size: int

    def encode(self, text: str) -> list[int]:
        """Encode text into a list of token ids."""
        ...


class _TiktokenEncoder:
    """Adapts a tiktoken encoding to the :class:`Encoder` protocol."""

    def __init__(self, name: str) -> None:
        import tiktoken

        self._enc = tiktoken.get_encoding(name)
        self.vocab_size = self._enc.n_vocab
        self.eot_token = self._enc.eot_token

    def encode(self, text: str) -> list[int]:
        # Plain BPE over the cleaned text; no special-token handling needed.
        return self._enc.encode(text)


class _HFEncoder:
    """Adapts a HuggingFace fast tokenizer to the :class:`Encoder` protocol."""

    def __init__(self, name: str) -> None:
        from transformers import AutoTokenizer

        self._tok = AutoTokenizer.from_pretrained(name)
        self.vocab_size = self._tok.vocab_size
        eot = self._tok.eos_token_id
        if eot is None:
            raise ValueError(f"HF tokenizer {name!r} has no eos_token_id")
        self.eot_token = eot

    def encode(self, text: str) -> list[int]:
        return self._tok.encode(text, add_special_tokens=False)


# tiktoken uses encoding names ("gpt2"); accept the common model alias too.
_TIKTOKEN_ALIASES = {"gpt2": "gpt2", "gpt-2": "gpt2"}


@lru_cache
def get_encoder(name: str = "gpt2", backend: str = "tiktoken") -> Encoder:
    """Return a cached encoder for ``name`` using the given ``backend``.

    ``backend`` is ``"tiktoken"`` (default) or ``"hf"``. tiktoken keeps the
    worker image lean (no torch/transformers); the HF backend is opt-in.
    """
    if backend == "tiktoken":
        return _TiktokenEncoder(_TIKTOKEN_ALIASES.get(name, name))
    if backend == "hf":
        return _HFEncoder(name)
    raise ValueError(f"unknown tokenizer backend: {backend!r}")
