"""Tests for the council member hand-off framing (UAT A5).

The matter used to reach each member as a bare user turn. When that text was a
quotation — the tester pasted a Machiavelli line and pressed "Ask the Council" —
members read it as "comment on this text" and opened by disowning and attributing
it instead of counselling the person. The matter is now wrapped so the turn ends
on the person, not on the words.

DB, LLM and persona lookups are mocked; only what reaches llm_client.stream is
asserted. Mirrors test_counterview_limit.py in style.

Run: cd apps/api && pytest tests/services/test_council_service.py -v
"""
import sys
import os

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from services.council_service import council_service

USER_ID = "aaaaaaaa-0000-0000-0000-000000000001"

# The tester's case: a bare quotation, the shape that produced the disowning.
QUOTATION = "It is better to be feared than loved, if you cannot be both."


def _make_db():
    """Mock session for stream_council: add/flush/commit are no-ops, and any
    query resolves to an empty result."""
    db = AsyncMock()
    result = MagicMock()
    result.scalar_one.return_value = 0
    result.scalar_one_or_none.return_value = None
    result.scalars.return_value.all.return_value = []
    db.execute = AsyncMock(return_value=result)
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    return db


async def _run_and_capture(matter: str, **kwargs) -> list[dict]:
    """Drive stream_council far enough to capture the messages handed to the first
    member, then stop. Returns the captured `messages` list."""
    captured: dict = {}

    async def capture_stream(*args, **kw):
        captured.setdefault("messages", kw["messages"])
        yield "verdict text"

    mock_llm = MagicMock()
    mock_llm.stream = capture_stream
    mock_llm.complete = AsyncMock(return_value="")

    safety_result = MagicMock()
    safety_result.should_suppress_persona = False
    safety_result.level = "none"

    persona = MagicMock()
    persona.name = "Epictetus"
    persona.slug = "epictetus"

    with (
        patch("services.council_service.safety_service") as mock_safety,
        patch("services.council_service.llm_client", mock_llm),
        patch("services.council_service.prompt_builder") as mock_prompt,
        patch("services.council_service.get_persona", return_value=persona),
    ):
        mock_safety.check_input = AsyncMock(return_value=safety_result)
        mock_safety.check_output = AsyncMock(return_value=safety_result)
        mock_prompt.build_system.return_value = "system"
        mock_prompt.cache_whole_system.side_effect = lambda s: s

        gen = council_service.stream_council(
            db=_make_db(), user_id=USER_ID, matter=matter, **kwargs
        )
        async for _ in gen:
            if "messages" in captured:
                await gen.aclose()
                break

    return captured["messages"]


@pytest.mark.asyncio
async def test_member_receives_the_matter_wrapped_not_bare():
    """The member's user turn frames the matter and ends on the person."""
    messages = await _run_and_capture(QUOTATION)

    assert len(messages) == 1
    assert messages[0]["role"] == "user"
    content = messages[0]["content"]

    # Opens by naming who brought it…
    assert content.startswith("The person brings this before the council:")
    # …and closes on them, not on the words. This is the line that matters:
    # what the model carries into its first sentence is what it read last.
    assert content.rstrip().endswith("This is what they ask you to weigh.")


@pytest.mark.asyncio
async def test_matter_text_is_intact_inside_the_wrapper():
    """Framing must not alter, truncate or re-word the matter itself."""
    content = (await _run_and_capture(QUOTATION))[0]["content"]
    assert QUOTATION in content


@pytest.mark.asyncio
async def test_wrapper_applies_to_direct_source_too():
    """Applied on the shared path — no branch on source."""
    content = (await _run_and_capture("Should I take the job?", source="direct"))[0]["content"]
    assert content.startswith("The person brings this before the council:")
    assert "Should I take the job?" in content
