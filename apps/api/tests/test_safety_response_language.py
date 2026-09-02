"""The crisis response answers in the language the person wrote in.

WHY THIS MATTERS MORE THAN IT LOOKS. Everything else in this PR is about
HEARING a Greek speaker in crisis. This is about ANSWERING one. If the gate
fires correctly and then replies in English, the app has visibly stopped the
conversation and then failed to communicate — which is arguably worse than the
silence it replaced, because the person now knows something happened and cannot
read what.

THE TRIPWIRE. The Greek template currently holds a PENDING_COPY placeholder,
and test_greek_safety_copy_is_not_a_placeholder FAILS while it does. That test
is RED by design on this branch and goes green in the commit that pastes the
founder-approved Greek copy. It is a gate, not a chore: crisis copy is the last
thing between a person in crisis and no help at all, and a placeholder reaching
production there is not a cosmetic defect.

Greeklish routes to English deliberately — dominant_language counts codepoints,
so latin-script Greek reads as English, and a greeklish typist is reading an
English UI already. That is asserted rather than left implicit, so the
behaviour is a decision on the record instead of an accident of the detector.
"""
import inspect
from pathlib import Path

import pytest

from services.prompt_builder import PromptBuilder
from text_utils import dominant_language

PENDING = "PENDING_COPY"


@pytest.fixture
def builder():
    return PromptBuilder()


# ── The tripwire ──────────────────────────────────────────────────────────────

def test_greek_safety_copy_is_not_a_placeholder(builder):
    """RED until the founder-approved Greek crisis copy is pasted in.

    Do not satisfy this by deleting the assertion or by machine-translating the
    English template. The English copy is country-neutral by design; the Greek
    one has to be written, with Greek crisis-support guidance.
    """
    response = builder.build_safety_response(language="Greek")
    assert PENDING not in response, (
        "The Greek crisis response is still a placeholder. Paste the approved "
        "copy into prompts/safety_response_el.jinja2."
    )


# ── Routing ───────────────────────────────────────────────────────────────────

def test_greek_input_selects_the_greek_template(builder):
    greek = builder.build_safety_response(language="Greek")
    english = builder.build_safety_response(language="English")
    assert greek != english, "Greek and English crisis responses are identical"


def test_english_is_the_default(builder):
    assert builder.build_safety_response() == builder.build_safety_response(language="English")


def test_an_unknown_language_falls_back_to_english(builder):
    """Never an empty response on this path. An English crisis message is worse
    than a Greek one for a Greek speaker and far better than none."""
    assert builder.build_safety_response(language="Klingon") == \
           builder.build_safety_response(language="English")


@pytest.mark.parametrize("text,expected", [
    ("θέλω να αυτοκτονήσω", "Greek"),
    ("δεν αντέχω άλλο", "Greek"),
    ("i want to kill myself", "English"),
    ("den antexo allo", "English"),          # greeklish -> English, by design
    ("", "English"),                          # empty -> English, never a crash
])
def test_language_routing_of_real_crisis_inputs(text, expected):
    assert dominant_language([text]) == expected


def test_greeklish_routing_is_a_decision_not_an_accident():
    """Documented so a future reader does not 'fix' it into a transliterator.

    dominant_language counts Greek vs latin codepoints. Greeklish is latin, so
    it reads as English. The SAFETY GATES still catch it — that is what the
    greeklish lexicons are for — only the response language falls back.
    """
    from services.safety_service import SafetyService
    import asyncio

    result = asyncio.get_event_loop_policy().new_event_loop().run_until_complete(
        SafetyService().check_input("den antexo allo thelo na pethano")
    )
    assert result.level == "high", "greeklish must still trip the gate"
    assert dominant_language(["den antexo allo thelo na pethano"]) == "English"


# ── Constraints the Greek template inherits from the English one ──────────────

def test_no_user_name_parameter_still(builder):
    """Adding `language` must not have opened a name-injection path."""
    sig = inspect.signature(builder.build_safety_response)
    assert "user_name" not in sig.parameters
    assert set(sig.parameters) == {"level", "language"}


def test_greek_template_carries_no_country_specific_numbers():
    """Checked against the FILE, so it holds before and after the copy lands."""
    path = Path(__file__).resolve().parents[1] / "prompts" / "safety_response_el.jinja2"
    body = path.read_text(encoding="utf-8")
    for number in ("988", "741741", "116123"):
        assert number not in body, f"country-specific number {number} in Greek template"


def test_greek_copy_is_single_for_all_suppression_levels(builder):
    """Same rule as English: one copy, no level-differentiated crisis text."""
    high = builder.build_safety_response(level="high", language="Greek")
    medium = builder.build_safety_response(level="medium", language="Greek")
    critical = builder.build_safety_response(level="critical", language="Greek")
    assert high == medium == critical
