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

        `_token_sink`, when passed, receives four keys:

            "total"           input + cache_creation + cache_read + output
            "input"           uncached input tokens
            "cache_creation"  tokens written to cache
            "cache_read"      tokens served from cache

        The cache fields are NOT optional detail — history caching drives
        cache_read to the large majority of input volume on a deep conversation,
        so omitting them would make the longest (most expensive) conversations
        record the smallest numbers. They are stored separately because the four
        buckets price differently (input 1.0x, cache_creation 1.25x, cache_read
        0.1x): "total" is a volume figure, and cost needs the split. output is
        not a key — it is total minus the other three.

        An async generator cannot `return` a value (SyntaxError — PEP 525), so a
        caller-owned dict is the only way to hand the counts back alongside the
        yielded chunks. Callers that omit it are byte-identical to before.

        Every key ACCUMULATES (`+=`) rather than overwriting, so one sink passed
        to several stream() calls totals them — which is what keeps the output
        identity true across a multi-call message. In practice the accumulating
        caller is stream_response's post-processing CORRECTION REGENERATION: two
        successful calls, one saved message.

        A FAILED attempt contributes NOTHING. The usage read below sits after the
        text_stream loop, so an exception mid-stream propagates before it runs.
        The sink therefore records the calls that completed, and slightly
        under-counts a request that burned a partial attempt before retrying.
        That is what the code does; a sink reused across unrelated messages would
        over-count, so one is created per saved message."""
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
                    _input    = getattr(usage, "input_tokens", 0)
                    _cache_wr = getattr(usage, "cache_creation_input_tokens", 0)
                    _cache_rd = getattr(usage, "cache_read_input_tokens", 0)
                    _output   = getattr(usage, "output_tokens", 0)
                    # "total" is unchanged in meaning: the sum of all four. The
                    # components are recorded beside it because the buckets price
                    # differently (input 1.0x, cache_creation 1.25x, cache_read
                    # 0.1x), so the sum expresses volume but not cost. Every key
                    # accumulates in lockstep, which is what keeps
                    # output = total - (input + cache_creation + cache_read)
                    # true even when one message spans several calls.
                    _token_sink["total"] = _token_sink.get("total", 0) + (
                        _input + _cache_wr + _cache_rd + _output
                    )
                    _token_sink["input"] = _token_sink.get("input", 0) + _input
                    _token_sink["cache_creation"] = (
                        _token_sink.get("cache_creation", 0) + _cache_wr
                    )
                    _token_sink["cache_read"] = (
                        _token_sink.get("cache_read", 0) + _cache_rd
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
