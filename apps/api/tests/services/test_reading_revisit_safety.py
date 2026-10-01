"""
create_reading_revisit — the post-generation suppression branch.

#589 wrote `language=dominant_language([user_text])` into this branch; #746
renamed it to crisis_language. `user_text` does not exist in this function, so
every revisit opening that the output check suppressed raised NameError instead
of returning the crisis response. No test reached the branch; the static guard
in test_safety_response_language.py only checks the call's TEXT.

crisis_language is deliberately NOT patched: the NameError was raised while
evaluating its argument, so these tests must execute the real expression.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from services.conversation_service import ConversationService, MODEL_PRO


def _letter(payload):
    letter = MagicMock()
    letter.status = "generated"
    letter.payload = payload
    return letter


def _db(letter):
    letter_result = MagicMock()
    letter_result.scalar_one_or_none.return_value = letter
    persona_db = MagicMock()
    persona_db.id = "persona-db-id"
    persona_result = MagicMock()
    persona_result.scalar_one_or_none.return_value = persona_db

    db = MagicMock()
    db.execute = AsyncMock(side_effect=[letter_result, persona_result])
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    return db


def _safety_out(suppress):
    out = MagicMock()
    out.should_suppress_persona = suppress
    out.level = "high" if suppress else "none"
    return out


async def _run(payload, suppress):
    svc = ConversationService()
    svc._log_safety_event = AsyncMock()
    svc._save_message = AsyncMock()
    persona_config = MagicMock()
    persona_config.slug = "seneca"

    with (
        patch("services.conversation_service.get_persona", return_value=persona_config),
        patch("services.conversation_service.is_persona_accessible", return_value=True),
        patch("services.conversation_service.prompt_builder") as mock_prompt,
        patch("services.conversation_service.llm_client") as mock_llm,
        patch("services.conversation_service.safety_service") as mock_safety,
        patch("services.conversation_service.POSTPROCESSING_ENABLED", False),
    ):
        mock_prompt.build_system.return_value = "SYSTEM"
        mock_prompt.build_safety_response.return_value = "SAFE LINE"
        mock_llm.complete = AsyncMock(return_value="the persona's read")
        mock_safety.check_output = AsyncMock(return_value=_safety_out(suppress))

        db = _db(_letter(payload))
        await svc.create_reading_revisit(
            db, "user-1", "letter-1", "seneca", user_plan="pro",
        )
    return svc, mock_prompt, db


@pytest.mark.asyncio
async def test_a_suppressed_revisit_returns_the_crisis_response_in_english():
    svc, mock_prompt, db = await _run(
        {"title": "A week of waiting", "opening": "You kept returning to the same door."},
        suppress=True,
    )
    mock_prompt.build_safety_response.assert_called_once_with(level="high", language="English")
    svc._log_safety_event.assert_awaited_once()
    saved = svc._save_message.await_args
    assert saved.args[3:5] == ("assistant", "SAFE LINE")
    assert saved.kwargs == {
        "safety_level": "high", "persona_override": True, "model_used": MODEL_PRO,
    }
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_a_suppressed_revisit_answers_in_the_letters_language():
    # The worker writes the letter in dominant_language of the week's words, so
    # a Greek letter means a Greek-writing user.
    _, mock_prompt, _ = await _run(
        {"title": "Μια εβδομάδα αναμονής", "opening": "Γύριζες συνέχεια στην ίδια πόρτα."},
        suppress=True,
    )
    mock_prompt.build_safety_response.assert_called_once_with(level="high", language="Greek")


@pytest.mark.asyncio
async def test_an_unsuppressed_revisit_keeps_the_persona_text():
    svc, mock_prompt, _ = await _run({"opening": "You kept returning."}, suppress=False)
    mock_prompt.build_safety_response.assert_not_called()
    svc._log_safety_event.assert_not_awaited()
    saved = svc._save_message.await_args
    assert saved.args[3:5] == ("assistant", "the persona's read")
    assert saved.kwargs["persona_override"] is False
