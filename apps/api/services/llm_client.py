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
        cache_control: dict | None = None,
        _token_sink: dict | None = None,
    ) -> AsyncGenerator[str, None]:
        """Stream tokens from Claude. Yields text chunks. `system` accepts a plain
        string or a list of content blocks (for cache_control) — passed through
        unchanged; a string caller behaves byte-identically.

        `cache_control` is the API's top-level automatic-caching breakpoint: when
        set, the API places a cache breakpoint at the LAST cacheable block of the
        request (i.e. covering the message history) and moves it forward as the
        conversation grows. It is forwarded ONLY when set, so every caller that
        omits it sends a byte-identical request to before. `messages` is never
        rewritten here — the breakpoint is a request-level flag, not content.

        `_token_sink`, when passed, receives the token count under key "total":
        input + cache_creation + cache_read + output, i.e. every billed
        component. The cache fields are NOT optional detail — history caching
        drives cache_read to the large majority of input volume on a deep
        conversation, so omitting them would make the longest (most expensive)
        conversations record the smallest numbers.

        An async generator cannot `return` a value (SyntaxError — PEP 525), so a
        caller-owned dict is the only way to hand the count back alongside the
        yielded chunks. Callers that omit it are byte-identical to before.

        The count ACCUMULATES (`+=`) rather than overwrites, so one sink passed
        to several stream() calls totals them. That is deliberate: a caller that
        retries a failed attempt, or regenerates a correction, is billed for
        every attempt, and the sink is meant to record spend rather than the
        size of whichever text was ultimately kept. Reused across unrelated
        messages it would over-count, so a sink is created per saved message."""
        model = model or config.ANTHROPIC_MODEL
        start = time.monotonic()

        cache_kwargs = {"cache_control": cache_control} if cache_control else {}
        async with _client.messages.stream(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=messages,
            **cache_kwargs,
        ) as stream:
            async for text in stream.text_stream:
                yield text
            # Usage logging only — runs after the last yield, inside the context
            # manager. Does NOT change what/when the generator yields. Guarded so a
            # usage-read failure can never break the stream contract for callers.
            try:
                usage = (await stream.get_final_message()).usage
                _log_usage(usage, model)
                if _token_sink is not None:
                    _token_sink["total"] = _token_sink.get("total", 0) + (
                        getattr(usage, "input_tokens", 0)
                        + getattr(usage, "cache_creation_input_tokens", 0)
                        + getattr(usage, "cache_read_input_tokens", 0)
                        + getattr(usage, "output_tokens", 0)
                    )
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
