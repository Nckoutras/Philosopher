import time
import logging
from typing import AsyncGenerator
import anthropic
from config import config

logger = logging.getLogger(__name__)

_client = anthropic.AsyncAnthropic(api_key=config.ANTHROPIC_API_KEY)


def _log_usage(usage, model: str) -> None:
    """Log token usage including prompt-cache read/write. The cache fields are
    additive across SDK versions — getattr-default 0 keeps this safe if absent."""
    logger.info(
        "llm_usage model=%s input=%s cache_write=%s cache_read=%s",
        model,
        getattr(usage, "input_tokens", 0),
        getattr(usage, "cache_creation_input_tokens", 0),
        getattr(usage, "cache_read_input_tokens", 0),
    )


class LLMClient:

    async def stream(
        self,
        system: str | list[dict],
        messages: list[dict],
        model: str | None = None,
        max_tokens: int = 1024,
    ) -> AsyncGenerator[str, None]:
        """Stream tokens from Claude. Yields text chunks. `system` accepts a plain
        string or a list of content blocks (for cache_control) — passed through
        unchanged; a string caller behaves byte-identically."""
        model = model or config.ANTHROPIC_MODEL
        start = time.monotonic()

        async with _client.messages.stream(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=messages,
        ) as stream:
            async for text in stream.text_stream:
                yield text
            # Usage logging only — runs after the last yield, inside the context
            # manager. Does NOT change what/when the generator yields. Guarded so a
            # usage-read failure can never break the stream contract for callers.
            try:
                _log_usage((await stream.get_final_message()).usage, model)
            except Exception as e:  # pragma: no cover - observability only
                logger.debug(f"stream usage log skipped: {e}")

        latency_ms = int((time.monotonic() - start) * 1000)
        logger.debug(f"LLM stream complete latency={latency_ms}ms")

    async def complete(
        self,
        system: str | list[dict],
        user: str,
        model: str | None = None,
        max_tokens: int = 512,
    ) -> str:
        """Single completion — for memory extraction, insight generation, etc.
        `system` accepts a plain string or a list of content blocks (for
        cache_control), passed through unchanged."""
        model = model or config.ANTHROPIC_MEMORY_MODEL
        response = await _client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        _log_usage(response.usage, model)
        return response.content[0].text


llm_client = LLMClient()
