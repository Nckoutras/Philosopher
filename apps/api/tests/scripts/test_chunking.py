"""Unit tests for scripts/chunking.py.

All tests are pure-function; no I/O, no DB, no network.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest
import tiktoken

from scripts.chunking import chunk_text, get_encoder


@pytest.fixture(scope="module")
def encoder():
    return get_encoder()


# ── Basic contract ─────────────────────────────────────────────────────────────

def test_empty_string_returns_empty_list(encoder):
    assert chunk_text("", encoder=encoder) == []


def test_whitespace_only_returns_empty_list(encoder):
    assert chunk_text("   \n\t  ", encoder=encoder) == []


def test_short_text_returns_single_chunk(encoder):
    text = "The unexamined life is not worth living."
    result = chunk_text(text, chunk_size_tokens=512, encoder=encoder)
    assert len(result) == 1
    assert result[0].strip() == text.strip()


def test_long_text_returns_multiple_chunks(encoder):
    # Generate text that is clearly longer than one chunk
    word = "philosophy " * 60          # ~60 tokens per repeat
    text = word * 20                   # ~1200 tokens total
    result = chunk_text(text, chunk_size_tokens=512, overlap_tokens=50, encoder=encoder)
    assert len(result) > 1


def test_each_chunk_within_token_limit(encoder):
    word = "stoicism " * 60
    text = word * 20
    result = chunk_text(text, chunk_size_tokens=256, overlap_tokens=32, encoder=encoder)
    assert result, "Expected at least one chunk"
    for chunk in result:
        token_count = len(encoder.encode(chunk))
        assert token_count <= 256, f"Chunk has {token_count} tokens, expected <= 256"


def test_deterministic_same_input_same_output(encoder):
    text = "The soul of man under capitalism. " * 100
    first = chunk_text(text, encoder=encoder)
    second = chunk_text(text, encoder=encoder)
    assert first == second


def test_overlap_tokens_appear_in_consecutive_chunks(encoder):
    # Build text long enough to produce 3+ chunks
    word = "virtue " * 80
    text = word * 10
    chunks = chunk_text(text, chunk_size_tokens=256, overlap_tokens=32, encoder=encoder)
    assert len(chunks) >= 2

    # The last 32 tokens of chunk N should be the first 32 tokens of chunk N+1
    for i in range(len(chunks) - 1):
        tail_tokens = encoder.encode(chunks[i])[-32:]
        head_tokens = encoder.encode(chunks[i + 1])[:32]
        assert tail_tokens == head_tokens, (
            f"Overlap mismatch between chunk {i} and {i+1}"
        )


def test_text_exactly_at_chunk_size_returns_one_chunk(encoder):
    # Construct text of exactly 512 tokens
    tokens = encoder.encode("word ") * 102     # 102 * 5 tokens ~ 510+
    tokens = tokens[:512]
    text = encoder.decode(tokens)
    result = chunk_text(text, chunk_size_tokens=512, encoder=encoder)
    assert len(result) == 1


def test_invalid_overlap_raises():
    with pytest.raises(ValueError, match="overlap_tokens"):
        chunk_text("hello world " * 200, chunk_size_tokens=50, overlap_tokens=50)
