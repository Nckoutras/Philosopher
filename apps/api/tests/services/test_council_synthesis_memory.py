"""Council synthesis receives memory; the four members stay cold (Ruling #4).

WHAT WAS WRONG. council_service passed memories=[] to every build_system call and
had no recall of any kind — the code said so itself at the analytics site: "No
used_memory -- this service passes memories=[] unconditionally"
(MEMORY_V2_INVESTIGATION_2026-09-03 §2b). So the surface where a person brings
their hardest question got less of their history than an ordinary chat turn.

THE RULING SPLITS IT. Members meet the matter COLD — deliberately, and because
their prompt is static per (persona, role), which is the whole basis of the
whole-prompt cache across four calls. Memory enters at the SYNTHESIS step only.

These tests pin BOTH halves. A change that gives members memory fails here just as
loudly as one that takes it away from the synthesis, because the boundary is the
ruling — not an implementation detail.

Run: cd apps/api && pytest tests/services/test_council_synthesis_memory.py -v
"""
import os
import sys

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from services.council_service import council_service
from services.prompt_builder import MEMORY_USE_DIRECTIVE

USER_ID = "aaaaaaaa-0000-0000-0000-000000000002"
MATTER = "Should I leave the job that pays for the life I am not living?"


class FakeMemory:
    """A recall row. Plain object, not a MagicMock (C-06): the assertions read
    entry_type and content back out of the composed prompt, and a MagicMock would
    render as a repr and quietly pass a substring check it should fail."""

    def __init__(self, entry_type: str, content: str):
        self.entry_type = entry_type
        self.content = content


RECALLED = [
    FakeMemory("struggle", "User keeps returning to whether security is worth the cost."),
    FakeMemory("value", "User places high importance on doing work that feels honest."),
]


def _make_db():
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


async def _run_council(recall_result=None, recall_raises=None):
    """Drive stream_council to completion with every external edge mocked.

    Returns (member_system_prompts, member_user_turns, synthesis_user_content).
    `source="direct"` with no conversation_id, so _distill_brief never runs and the
    ONLY llm_client.complete call is the synthesis — which is what we capture.
    """
    member_systems: list = []
    member_turns: list = []
    synthesis_calls: list = []

    async def capture_stream(*args, **kw):
        member_systems.append(kw["system"])
        member_turns.append(kw["messages"][0]["content"])
        yield "a verdict"

    async def capture_complete(*args, **kw):
        synthesis_calls.append(kw)
        return ""  # unparseable → synthesis_error branch; the call is what matters

    mock_llm = MagicMock()
    mock_llm.stream = capture_stream
    mock_llm.complete = AsyncMock(side_effect=capture_complete)

    safety_result = MagicMock()
    safety_result.should_suppress_persona = False
    safety_result.should_log = False
    safety_result.level = "none"

    persona = MagicMock()
    persona.name = "Epictetus"
    persona.slug = "epictetus"

    mock_memory = MagicMock()
    if recall_raises is not None:
        mock_memory.recall = AsyncMock(side_effect=recall_raises)
    else:
        mock_memory.recall = AsyncMock(return_value=recall_result or [])

    with (
        patch("services.council_service.safety_service") as mock_safety,
        patch("services.council_service.llm_client", mock_llm),
        patch("services.council_service.get_persona", return_value=persona),
        patch("services.council_service.memory_service", mock_memory),
        patch("services.council_service.analytics_service"),
    ):
        mock_safety.check_input = AsyncMock(return_value=safety_result)
        mock_safety.check_output = AsyncMock(return_value=safety_result)

        gen = council_service.stream_council(
            db=_make_db(), user_id=USER_ID, matter=MATTER, source="direct",
        )
        async for _ in gen:
            pass

    assert synthesis_calls, "the synthesis call never happened"
    return member_systems, member_turns, synthesis_calls[0], mock_memory


# ── (a) The synthesis receives memory ───────────────────────────────────────

@pytest.mark.asyncio
async def test_the_synthesis_carries_the_recalled_memory_content():
    """THE FEATURE. Pre-fix the council had no recall at all, so this fails there."""
    _systems, _turns, synthesis, _mem = await _run_council(recall_result=RECALLED)
    content = synthesis["user"]

    assert "whether security is worth the cost" in content
    assert "work that feels honest" in content
    assert "[STRUGGLE]" in content and "[VALUE]" in content


@pytest.mark.asyncio
async def test_the_synthesis_carries_the_approved_use_directive_verbatim():
    """Founder-approved copy (#597). A THIRD wording may not appear — Ruling #4 is
    explicit — so this asserts the literal, not a paraphrase."""
    _systems, _turns, synthesis, _mem = await _run_council(recall_result=RECALLED)

    assert MEMORY_USE_DIRECTIVE in synthesis["user"]
    assert (
        "These are things you know of this person from earlier conversations. Let them inform "
        "how you meet what they bring today. Never recite them, never list them, never announce "
        "that you remember — familiarity shows in how you speak, not in repeating what was said."
    ) in synthesis["user"]


@pytest.mark.asyncio
async def test_recall_is_the_shared_one_queried_with_the_matter():
    """Reuses the chat paths' recall EXACTLY — flat top-6, its own 0.70 cut. This
    PR must not pre-empt Ruling #5's hybrid recall, so the call shape is pinned."""
    _systems, _turns, _synthesis, mem = await _run_council(recall_result=RECALLED)

    mem.recall.assert_awaited_once()
    args, kwargs = mem.recall.await_args
    assert args[1] == USER_ID
    assert args[2] == MATTER
    assert kwargs == {"top_k": 6}


@pytest.mark.asyncio
async def test_the_matter_and_verdicts_still_lead_the_synthesis_turn():
    """Memory is appended, never substituted: the instrument still reads the matter
    and the four verdicts first."""
    _systems, _turns, synthesis, _mem = await _run_council(recall_result=RECALLED)
    content = synthesis["user"]

    assert content.startswith("The matter:")
    assert MATTER in content
    assert "The four verdicts:" in content
    assert content.index("The four verdicts:") < content.index("WHAT YOU KNOW ABOUT THIS PERSON")


# ── (b) The members stay cold — the ruling's boundary ───────────────────────

@pytest.mark.asyncio
async def test_no_member_prompt_carries_memory_even_when_recall_returns_entries():
    """THE BOUNDARY. Four cold members is the ruling, and it is what keeps the
    member prompt static per (persona, role) for cache_whole_system."""
    systems, turns, _synthesis, _mem = await _run_council(recall_result=RECALLED)

    assert len(systems) == 4, "expected one call per council member"
    for system in systems:
        rendered = system if isinstance(system, str) else str(system)
        assert "WHAT YOU KNOW ABOUT THIS PERSON" not in rendered
        assert MEMORY_USE_DIRECTIVE not in rendered
        assert "whether security is worth the cost" not in rendered
    for turn in turns:
        assert "whether security is worth the cost" not in turn
        assert MEMORY_USE_DIRECTIVE not in turn


@pytest.mark.asyncio
async def test_no_member_prompt_carries_anything_per_user_so_the_cache_holds():
    """The whole-prompt cache needs the member prompt to be static per (persona,
    role) — NOT identical across the four, which it is not: COUNCIL_ROLE_DIRECTIVE
    differs per slug, and that is by design. What the cache actually requires is
    that nothing about THIS user is in there, which is what this asserts."""
    systems, _turns, _synthesis, _mem = await _run_council(recall_result=RECALLED)
    rendered = [s if isinstance(s, str) else str(s) for s in systems]

    for system in rendered:
        assert USER_ID not in system
        assert MATTER not in system
        for memory in RECALLED:
            assert memory.content not in system

    # And they differ only by role, so the per-(persona, role) key is real.
    assert len(set(rendered)) == 4


# ── (c) Recall failure must never break a council ──────────────────────────

@pytest.mark.asyncio
async def test_a_failing_recall_still_produces_a_synthesis_with_no_memory_block():
    """A council must never fail because memory retrieval did."""
    _systems, _turns, synthesis, _mem = await _run_council(
        recall_raises=RuntimeError("pgvector is down"),
    )
    content = synthesis["user"]

    assert content.startswith("The matter:")
    assert "The four verdicts:" in content
    assert "WHAT YOU KNOW ABOUT THIS PERSON" not in content
    assert MEMORY_USE_DIRECTIVE not in content


@pytest.mark.asyncio
async def test_a_failing_recall_raises_nothing_to_the_caller():
    """The generator runs to completion — _run_council drains it, so an exception
    escaping the recall would surface as a test error rather than an assertion."""
    _systems, _turns, synthesis, _mem = await _run_council(
        recall_raises=RuntimeError("pgvector is down"),
    )
    assert synthesis["user"]


# ── (d) Empty recall leaves today's shape untouched ────────────────────────

@pytest.mark.asyncio
async def test_an_empty_recall_composes_exactly_the_pre_change_content():
    """No entries → byte-identical to what the synthesis received before this PR:
    the matter and the verdicts, and nothing appended."""
    _systems, _turns, synthesis, _mem = await _run_council(recall_result=[])
    content = synthesis["user"]

    assert content == f"The matter:\n{MATTER}\n\nThe four verdicts:\n[Epictetus]: a verdict\n\n" \
        f"[Epictetus]: a verdict\n\n[Epictetus]: a verdict\n\n[Epictetus]: a verdict"
    assert "WHAT YOU KNOW ABOUT THIS PERSON" not in content


# ── (e) One wording, in one place ──────────────────────────────────────────

def test_the_directive_constant_and_the_template_have_not_forked():
    """The Jinja template cannot import Python, so the approved copy exists twice:
    as MEMORY_USE_DIRECTIVE and as literal text in system_base.jinja2. THIS is the
    assertion that keeps them one piece of copy rather than two that drift."""
    from pathlib import Path

    from services.prompt_builder import PROMPTS_DIR

    template = (Path(PROMPTS_DIR) / "system_base.jinja2").read_text(encoding="utf-8")
    assert MEMORY_USE_DIRECTIVE in template
