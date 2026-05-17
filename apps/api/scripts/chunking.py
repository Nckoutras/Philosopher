"""
Token-based text chunking for corpus ingestion.

Uses tiktoken (cl100k_base, the encoding used by text-embedding-3-small)
to split text into overlapping windows. Pure functions: deterministic,
no side effects, no I/O.
"""

import tiktoken


def get_encoder(encoding_name: str = "cl100k_base") -> tiktoken.Encoding:
    return tiktoken.get_encoding(encoding_name)


def chunk_text(
    text: str,
    chunk_size_tokens: int = 512,
    overlap_tokens: int = 50,
    encoder: tiktoken.Encoding | None = None,
) -> list[str]:
    """
    Split text into overlapping token-based chunks.

    Returns a list of decoded chunk strings. The final chunk may be shorter
    than chunk_size_tokens. An empty or whitespace-only input returns [].
    """
    if not text or not text.strip():
        return []

    if encoder is None:
        encoder = get_encoder()

    tokens = encoder.encode(text)

    if len(tokens) <= chunk_size_tokens:
        return [encoder.decode(tokens)]

    step = chunk_size_tokens - overlap_tokens
    if step <= 0:
        raise ValueError(f"overlap_tokens ({overlap_tokens}) must be less than chunk_size_tokens ({chunk_size_tokens})")

    chunks: list[str] = []
    start = 0

    while start < len(tokens):
        end = min(start + chunk_size_tokens, len(tokens))
        decoded = encoder.decode(tokens[start:end])
        if decoded.strip():
            chunks.append(decoded)
        if end == len(tokens):
            break
        start += step

    return chunks
