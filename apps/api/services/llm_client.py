import time
import logging
from typing import AsyncGenerator
import anthropic
from config import config

logger = logging.getLogger(__name__)

_client = anthropic.AsyncAnthropic(api_key=config.ANTHROPIC_API_KEY)


class LLMClient:

    async def stream(
        self,
        system: str,
        messages: list[dict],
        model: str | None = None,
        max_tokens: int = 1024,
    ) -> AsyncGenerator[str, None]:
        """Stream tokens from Claude. Yields text chunks."""
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

        latency_ms = int((time.monotonic() - start) * 1000)
        logger.debug(f"LLM stream complete latency={latency_ms}ms")

    async def complete(
        self,
        system: str,
        user: str,
        model: str | None = None,
        max_tokens: int = 512,
    ) -> str:
        """Single completion — for memory extraction, insight generation, etc."""
        model = model or config.ANTHROPIC_MEMORY_MODEL
        response = await _client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return response.content[0].text


llm_client = LLMClient()
